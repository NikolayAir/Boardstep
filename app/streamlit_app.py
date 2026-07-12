import sys
from pathlib import Path

import time

import streamlit as st

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from boardstep.computer_player import choose_computer_move

from boardstep.game import (
    STARTING_FEN,
    apply_uci_move,
    board_files,
    board_rows,
    side_to_move,
    validate_fen_position,
)

from boardstep.shared_game import (
    SharedGameState,
    create_shared_game_state,
    generate_shared_game_id,
)

from boardstep.supabase_rest_storage import (
    SUPABASE_KEY_SECRET,
    SUPABASE_URL_SECRET,
    SharedGameStorageConflictError,
    SupabaseRestConfig,
    create_shared_game,
    create_supabase_rest_config,
    load_shared_game,
    save_shared_game_after_move,
)

from app.ui_components import (
    render_board_area,
    render_game_panel,
)


PLAY_MODE_OPTIONS = ("local", "computer", "shared")
PLAY_MODE_LABELS = {
    "local": "Local practice",
    "computer": "Computer practice",
    "shared": "Shared game",
}

COMPUTER_LEVEL_OPTIONS = ("beginner", "easy", "basic", "intermediate")
COMPUTER_LEVEL_LABELS = {
    "beginner": "Beginner",
    "easy": "Easy",
    "basic": "Basic",
    "intermediate": "Intermediate",
}

PLAYER_SIDE_OPTIONS = ("white", "black")
PLAYER_SIDE_LABELS = {
    "white": "White",
    "black": "Black",
}


def initialize_game_state() -> None:
    """Create the Streamlit session state used by the current chess game."""
    if "fen" not in st.session_state:
        st.session_state.fen = STARTING_FEN

    if "move_history" not in st.session_state:
        st.session_state.move_history = []

    if "selected_square" not in st.session_state:
        st.session_state.selected_square = None

    if "click_move_error" not in st.session_state:
        st.session_state.click_move_error = None

    if "board_orientation" not in st.session_state:
        st.session_state.board_orientation = "white"

    if "shared_game_id" not in st.session_state:
        st.session_state.shared_game_id = ""

    if "shared_game_last_move_number" not in st.session_state:
        st.session_state.shared_game_last_move_number = None

    if "shared_game_status" not in st.session_state:
        st.session_state.shared_game_status = None

    if "shared_game_auto_refresh_enabled" not in st.session_state:
        st.session_state.shared_game_auto_refresh_enabled = False

    if "shared_game_last_synced_at" not in st.session_state:
        st.session_state.shared_game_last_synced_at = None

    if "game_mode" not in st.session_state:
        st.session_state.game_mode = "local"

    if "computer_level" not in st.session_state:
        st.session_state.computer_level = "beginner"

    if "player_side" not in st.session_state:
        st.session_state.player_side = "white"

    if "last_computer_move" not in st.session_state:
        st.session_state.last_computer_move = None


def clear_shared_game_session() -> None:
    """Clear shared-game session metadata."""
    st.session_state.shared_game_id = ""
    st.session_state.shared_game_last_move_number = None
    st.session_state.shared_game_status = None
    st.session_state.shared_game_auto_refresh_enabled = False
    st.session_state.shared_game_last_synced_at = None


def mark_shared_game_synced() -> None:
    """Record the local time of the latest successful shared-game sync."""
    st.session_state.shared_game_last_synced_at = time.strftime("%H:%M:%S")


def leave_shared_game_session() -> None:
    """Return to local practice without deleting the saved shared game."""
    clear_shared_game_session()
    st.session_state.game_mode = "local"
    st.session_state.shared_game_status = (
        "Returned to local practice. The saved shared game was not deleted."
    )


def shared_game_auto_refresh_is_paused() -> bool:
    """Return whether auto-refresh should pause to avoid interrupting a local move."""
    return st.session_state.selected_square is not None


def clear_computer_practice_session() -> None:
    """Clear computer-practice transient metadata."""
    st.session_state.last_computer_move = None


def current_side_to_move_key() -> str:
    """Return the current side to move as a session-state key."""
    return side_to_move(st.session_state.fen).lower()


def is_computer_practice_turn() -> bool:
    """Return whether the local computer should move now."""
    return (
        st.session_state.game_mode == "computer"
        and not st.session_state.shared_game_id
        and current_side_to_move_key() != st.session_state.player_side
    )


def should_start_computer_as_white() -> bool:
    """Return whether the computer should make the opening move."""
    return (
        st.session_state.game_mode == "computer"
        and st.session_state.player_side == "black"
        and st.session_state.fen == STARTING_FEN
        and not st.session_state.move_history
        and current_side_to_move_key() == "white"
    )


def reset_game() -> None:
    """Reset the current chess game to the starting position."""
    st.session_state.fen = STARTING_FEN
    st.session_state.move_history = []
    st.session_state.selected_square = None
    st.session_state.click_move_error = None
    clear_computer_practice_session()

    if st.session_state.game_mode == "shared":
        st.session_state.game_mode = "local"

    clear_shared_game_session()
    apply_computer_reply_if_needed()


def save_current_shared_game_position(config: SupabaseRestConfig) -> None:
    """Save the current session position to shared storage."""
    if not st.session_state.shared_game_id:
        return

    expected_last_move_number = st.session_state.shared_game_last_move_number

    if expected_last_move_number is None:
        st.session_state.shared_game_status = (
            "This move was kept locally, but the shared game move number is unknown. "
            "Refresh the shared game before playing another move."
        )
        return

    state = create_shared_game_state(
        st.session_state.shared_game_id,
        fen=st.session_state.fen,
        move_history=st.session_state.move_history,
    )

    try:
        saved_state = save_shared_game_after_move(
            config,
            state,
            expected_last_move_number=expected_last_move_number,
        )
    except SharedGameStorageConflictError:
        st.session_state.shared_game_status = (
            "This move was kept locally, but the shared game changed before it could be saved. "
            "Refresh the shared game to load the latest saved position before playing again."
        )
    except Exception:
        st.session_state.shared_game_status = (
            "This move was kept locally, but it could not be saved to shared storage. "
            "Check the shared-game storage settings, table setup, or whether the storage service is paused."
        )
    else:
        st.session_state.shared_game_last_move_number = saved_state.last_move_number
        mark_shared_game_synced()
        st.session_state.shared_game_status = (
            "Move saved. The other player can refresh manually or use auto-refresh to see it."
        )


def apply_legal_move_to_session(move_text: str) -> str:
    """Apply a legal move to the current session and return SAN notation."""
    recorded_move_text = move_text.strip()

    try:
        new_fen, san = apply_uci_move(st.session_state.fen, recorded_move_text)
    except ValueError:
        if len(recorded_move_text) != 4:
            raise

        promoted_move_text = f"{recorded_move_text}q"
        new_fen, san = apply_uci_move(st.session_state.fen, promoted_move_text)
        recorded_move_text = promoted_move_text

    st.session_state.fen = new_fen
    move_number = len(st.session_state.move_history) + 1
    st.session_state.move_history.append(
        f"{move_number}. {recorded_move_text} ({san})"
    )

    return san


def apply_computer_reply_if_needed() -> None:
    """Apply a local computer reply when it is the computer's turn."""
    if not is_computer_practice_turn():
        return

    computer_move = choose_computer_move(
        st.session_state.fen,
        st.session_state.computer_level,
    )

    if computer_move is None:
        return

    computer_san = apply_legal_move_to_session(computer_move)
    st.session_state.last_computer_move = f"{computer_move} ({computer_san})"


def apply_move_text(move_text: str) -> None:
    """Apply a user move and update Streamlit session state."""
    if is_computer_practice_turn():
        raise ValueError("It is the computer's turn in computer practice.")

    clear_computer_practice_session()
    apply_legal_move_to_session(move_text)

    if st.session_state.shared_game_id:
        config, _ = read_shared_game_storage_config()

        if config is None:
            st.session_state.shared_game_status = (
                "This move was kept locally, but shared storage is not configured. "
                "Local practice still works."
            )
        else:
            save_current_shared_game_position(config)

        return

    apply_computer_reply_if_needed()


def load_fen_position(fen_text: str) -> None:
    """Load a validated FEN position into the current session."""
    st.session_state.fen = validate_fen_position(fen_text)
    st.session_state.move_history = []
    st.session_state.selected_square = None
    st.session_state.click_move_error = None
    clear_computer_practice_session()
    clear_shared_game_session()


def render_fen_load_controls() -> None:
    """Render controls for loading a position from FEN."""
    with st.expander("Load position from FEN"):
        st.caption(
            "Paste a FEN position to restore a board state. "
            "Move history will be cleared."
        )

        with st.form("fen_form"):
            fen_text = st.text_input(
                "FEN position",
                placeholder=STARTING_FEN,
            )
            fen_submitted = st.form_submit_button("Load position")

        if fen_submitted:
            try:
                load_fen_position(fen_text)
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))


def read_shared_game_storage_config() -> tuple[SupabaseRestConfig | None, str]:
    """Read shared game storage settings from Streamlit secrets."""
    try:
        url = st.secrets.get(SUPABASE_URL_SECRET)
        key = st.secrets.get(SUPABASE_KEY_SECRET)
    except Exception:
        return None, "Shared game storage is not configured for this session."

    try:
        config = create_supabase_rest_config(url, key)
    except ValueError:
        return None, "Shared game storage secrets are missing or invalid."

    return config, "Shared games are available."


def apply_shared_game_state_to_session(
    state: SharedGameState,
    *,
    status_message: str,
) -> None:
    """Load shared game state into the current Streamlit session."""
    st.session_state.fen = state.fen
    st.session_state.move_history = list(state.move_history)
    st.session_state.selected_square = None
    st.session_state.click_move_error = None
    st.session_state.shared_game_id = state.game_id
    st.session_state.shared_game_last_move_number = state.last_move_number
    st.session_state.shared_game_status = status_message
    mark_shared_game_synced()
    clear_computer_practice_session()


def create_shared_game_from_current_session(
    config: SupabaseRestConfig,
) -> SharedGameState:
    """Create a shared game from the current local session state."""
    game_id = generate_shared_game_id()
    state = create_shared_game_state(
        game_id,
        fen=st.session_state.fen,
        move_history=st.session_state.move_history,
    )

    return create_shared_game(config, state)


def refresh_current_shared_game(config: SupabaseRestConfig) -> None:
    """Refresh the current shared game from shared storage."""
    active_game_id = st.session_state.shared_game_id

    if not active_game_id:
        return

    try:
        refreshed_state = load_shared_game(config, active_game_id)
    except Exception:
        st.session_state.shared_game_status = (
            "Shared game could not be refreshed. "
            "Check the shared-game storage settings, table setup, or whether the storage service is paused."
        )
        return

    if refreshed_state is None:
        st.session_state.shared_game_status = (
            "The active shared game ID was not found. "
            "Check that the ID was copied correctly."
        )
        return

    previous_move_number = st.session_state.shared_game_last_move_number

    if refreshed_state.last_move_number == previous_move_number:
        status_message = "No new move found yet."
    else:
        status_message = "Updated to the latest saved position."

    apply_shared_game_state_to_session(
        refreshed_state,
        status_message=status_message,
    )


def render_shared_game_controls() -> None:
    """Render shared game create/load controls."""
    active_game_id = st.session_state.shared_game_id

    with st.expander("Shared game"):
        if active_game_id:
            st.markdown("**Mode:** Shared game mode")
        else:
            st.markdown("**Mode:** Local practice mode")

        if active_game_id:
            st.caption(
                "Send the game ID to the other player. "
                "After either player moves, the other browser can refresh manually "
                "or enable auto-refresh to check for the latest board."
            )
        else:
            st.caption(
                "Create a shared game ID or load one from another player. "
                "Each browser can refresh manually or enable auto-refresh "
                "after loading a shared game."
            )

        config, _ = read_shared_game_storage_config()

        if config is None:
            st.info("Shared games are not available in this session.")
            st.caption(
                "Local practice still works. Shared games need storage settings "
                "to be configured first."
            )
        elif not active_game_id:
            st.success("Shared games are available.")

        if active_game_id:
            st.markdown("**Active shared game ID**")
            st.code(active_game_id, language="text")

            leave_col, _ = st.columns([1.3, 5.7])

            with leave_col:
                st.button(
                    "Leave shared game",
                    help="Return to local practice without deleting the saved shared game.",
                    use_container_width=True,
                    on_click=leave_shared_game_session,
                )

        if st.session_state.shared_game_status:
            st.info(st.session_state.shared_game_status)

        if not active_game_id:
            create_disabled = config is None

            if st.button(
                "Create shared game",
                disabled=create_disabled,
                help="Save the current board as a new shared game.",
            ):
                if config is not None:
                    try:
                        state = create_shared_game_from_current_session(config)
                    except Exception:
                        st.error(
                            "Shared game could not be created. "
                            "Check the shared-game storage settings, table setup, or whether the storage service is paused."
                        )
                    else:
                        apply_shared_game_state_to_session(
                            state,
                            status_message=(
                                "Shared game created. Send the ID above to the other player."
                            ),
                        )
                        st.rerun()

        load_container = (
            st.expander("Switch to an existing shared game")
            if active_game_id
            else st.container()
        )

        with load_container:
            with st.form("shared_game_load_form"):
                requested_game_id = st.text_input(
                    "Load shared game by ID",
                    placeholder="Paste a shared game ID.",
                    disabled=config is None,
                )

                load_submitted = st.form_submit_button(
                    "Load shared game",
                    disabled=config is None,
                )

        if load_submitted and config is not None:
            normalized_game_id = requested_game_id.strip()

            if not normalized_game_id:
                st.warning("Enter a shared game ID before loading a shared game.")
            else:
                try:
                    loaded_state = load_shared_game(config, normalized_game_id)
                except ValueError:
                    st.error("Enter a valid shared game ID.")
                except Exception:
                    st.error(
                        "Shared game could not be loaded. "
                        "Check the shared-game storage settings, table setup, or whether the storage service is paused."
                    )
                else:
                    if loaded_state is None:
                        st.warning(
                            "No shared game was found for that ID. "
                            "Check that the ID was copied correctly."
                        )
                    else:
                        apply_shared_game_state_to_session(
                            loaded_state,
                            status_message=(
                                "Shared game loaded. Use Refresh shared game or enable auto-refresh to check for moves from the other player."
                            ),
                        )
                        st.rerun()


@st.fragment(run_every="3s")
def render_shared_game_auto_refresh(config: SupabaseRestConfig | None) -> None:
    """Render and run optional polling-based shared-game auto-refresh."""
    if not st.session_state.shared_game_id:
        return

    auto_refresh_enabled = st.toggle(
        "Auto-refresh shared game",
        key="shared_game_auto_refresh_enabled",
        disabled=config is None,
        help="Poll shared storage every few seconds while this browser is in shared game mode.",
    )

    last_synced_at = st.session_state.shared_game_last_synced_at or "not yet"
    status_text = "on" if auto_refresh_enabled else "off"
    st.caption(f"Auto-refresh: {status_text}. Last synced: {last_synced_at}.")

    if config is None:
        st.caption("Shared-game storage is not configured for this session.")
        return

    if not auto_refresh_enabled:
        return

    if shared_game_auto_refresh_is_paused():
        st.caption("Auto-refresh paused while you are choosing a move.")
        return

    refreshed_has_new_move = refresh_current_shared_game(config)

    if refreshed_has_new_move:
        st.rerun()

    st.caption("Waiting for opponent move...")


def render_shared_game_refresh_shortcut() -> None:
    """Render a board-side refresh shortcut for active shared games."""
    if not st.session_state.shared_game_id:
        return

    config, _ = read_shared_game_storage_config()

    st.write("")
    st.markdown("**Shared game**")

    if st.button(
        "Refresh shared game",
        disabled=config is None,
        help="Reload the latest saved position for the active shared game ID.",
    ):
        if config is not None:
            refresh_current_shared_game(config)
            st.rerun()

    st.caption("Check for the other player’s latest move.")
    render_shared_game_auto_refresh(config)


def render_app_header() -> None:
    """Render the compact application heading."""
    st.title("Boardstep")
    st.caption(
        "Click-to-move chess practice with local, computer, and shared game modes."
    )


def render_game_setup() -> None:
    """Render play-mode controls for local, computer, and shared practice."""
    with st.container(border=True):
        st.subheader("Game setup")

        selected_mode = st.radio(
            "Play mode",
            options=PLAY_MODE_OPTIONS,
            format_func=lambda value: PLAY_MODE_LABELS[value],
            horizontal=True,
            key="game_mode",
        )

        if selected_mode != "shared" and st.session_state.shared_game_id:
            clear_shared_game_session()

        if selected_mode == "local":
            st.caption("Practice locally in this browser session.")
            return

        if selected_mode == "computer":
            st.caption(
                "Choose a side. The computer replies when it is its turn."
            )
            st.radio(
                "You play",
                options=PLAYER_SIDE_OPTIONS,
                format_func=lambda value: PLAYER_SIDE_LABELS[value],
                horizontal=True,
                key="player_side",
                on_change=reset_game,
            )

            if st.session_state.board_orientation != st.session_state.player_side:
                st.session_state.board_orientation = st.session_state.player_side

            st.radio(
                "Practice level",
                options=COMPUTER_LEVEL_OPTIONS,
                format_func=lambda value: COMPUTER_LEVEL_LABELS[value],
                horizontal=True,
                key="computer_level",
                on_change=reset_game,
            )

            with st.expander("What do the levels mean?"):
                st.markdown(
                    "- **Beginner:** random legal moves.\n"
                    "- **Easy:** prefers immediate mates, captures, checks, and promotions.\n"
                    "- **Basic:** chooses moves using simple material scoring.\n"
                    "- **Intermediate:** looks one reply ahead and uses lightweight positional scoring."
                )

            st.caption("Changing side or level starts a new game.")

            if should_start_computer_as_white():
                apply_computer_reply_if_needed()
                st.rerun()

            if is_computer_practice_turn():
                st.info(
                    "It is the computer's turn. Reset the game if you changed sides mid-game."
                )

            return

        render_shared_game_controls()


def main() -> None:
    st.set_page_config(page_title="Boardstep", layout="wide")
    initialize_game_state()

    render_app_header()
    render_game_setup()

    board_col, game_col = st.columns([1.65, 1], gap="large")

    with board_col:
        with st.container(border=True):
            _, orientation_col, _ = st.columns([0.85, 1.9, 0.25], gap="small")

            with orientation_col:
                board_orientation = st.radio(
                    "Board orientation",
                    options=("white", "black"),
                    format_func=lambda value: (
                        "White at bottom" if value == "white" else "Black at bottom"
                    ),
                    horizontal=True,
                    key="board_orientation",
                    label_visibility="collapsed",
                    help=(
                        "This changes only your local board view. "
                        "It is not saved to shared games."
                    ),
                )

            rows = board_rows(st.session_state.fen, orientation=board_orientation)
            files = board_files(board_orientation)
            render_board_area(rows, files, apply_move_text)

    with game_col:
        with st.container(border=True):
            render_shared_game_refresh_shortcut()

            render_game_panel(
                fen=st.session_state.fen,
                move_history=st.session_state.move_history,
                apply_move=apply_move_text,
                reset_game=reset_game,
                render_fen_load_controls=render_fen_load_controls,
                game_mode=st.session_state.game_mode,
                computer_level=st.session_state.computer_level,
                player_side=st.session_state.player_side,
                last_computer_move=st.session_state.last_computer_move,
            )


if __name__ == "__main__":
    main()
