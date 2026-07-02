import sys
from pathlib import Path

import streamlit as st

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from boardstep.game import (
    STARTING_FEN,
    apply_uci_move,
    board_files,
    board_rows,
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


def clear_shared_game_session() -> None:
    """Clear shared-game session metadata."""
    st.session_state.shared_game_id = ""
    st.session_state.shared_game_last_move_number = None
    st.session_state.shared_game_status = None


def reset_game() -> None:
    """Reset the current chess game to the starting position."""
    st.session_state.fen = STARTING_FEN
    st.session_state.move_history = []
    st.session_state.selected_square = None
    st.session_state.click_move_error = None
    clear_shared_game_session()


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
        st.session_state.shared_game_status = (
            "Move saved. The other player needs to press Refresh shared game to see it."
        )


def apply_move_text(move_text: str) -> None:
    """Apply a move and update Streamlit session state."""
    new_fen, san = apply_uci_move(st.session_state.fen, move_text)
    ply_number = len(st.session_state.move_history) + 1

    st.session_state.fen = new_fen
    st.session_state.move_history.append(
        f"{ply_number}. {move_text.strip().lower()} ({san})"
    )
    st.session_state.selected_square = None
    st.session_state.click_move_error = None

    if st.session_state.shared_game_id:
        config, _ = read_shared_game_storage_config()

        if config is None:
            st.session_state.shared_game_status = (
                "This move was kept locally, but shared storage is not configured. "
                "Local practice still works."
            )
        else:
            save_current_shared_game_position(config)


def load_fen_position(fen_text: str) -> None:
    """Load a validated FEN position into the current session."""
    st.session_state.fen = validate_fen_position(fen_text)
    st.session_state.move_history = []
    st.session_state.selected_square = None
    st.session_state.click_move_error = None
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
                "After either player moves, the other browser needs to press "
                "Refresh shared game to see the latest board."
            )
        else:
            st.caption(
                "Create a shared game ID or load one from another player. "
                "Each browser updates only when Refresh shared game is pressed."
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
                if st.button(
                    "Leave shared game",
                    help="Return to local practice without deleting the saved shared game.",
                    use_container_width=True,
                ):
                    clear_shared_game_session()
                    st.session_state.shared_game_status = (
                        "Returned to local practice. The saved shared game was not deleted."
                    )
                    st.rerun()

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
                                "Shared game loaded. Press Refresh shared game to check for moves from the other player."
                            ),
                        )
                        st.rerun()


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


def render_app_header() -> None:
    """Render the compact application heading."""
    st.title("Boardstep")
    st.caption(
        "Click-to-move chess practice with optional manual-refresh shared games."
    )


def main() -> None:
    st.set_page_config(page_title="Boardstep", layout="wide")
    initialize_game_state()

    render_app_header()
    render_shared_game_controls()

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
            )


if __name__ == "__main__":
    main()
