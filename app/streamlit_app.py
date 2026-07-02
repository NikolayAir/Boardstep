import sys
from pathlib import Path

import streamlit as st

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from boardstep.game import (
    STARTING_FEN,
    apply_uci_move,
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


def current_turn_label(fen: str) -> str:
    """Return the side to move from the current FEN string."""
    return "White" if fen.split()[1] == "w" else "Black"


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
            f"Saved this move to shared game `{saved_state.game_id}`. "
            "Other players need to refresh manually to see it."
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

    return config, "Shared game storage is configured."


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


def render_shared_game_controls() -> None:
    """Render shared game create/load controls."""
    active_game_id = st.session_state.shared_game_id

    with st.expander("Shared game (manual refresh)"):
        if active_game_id:
            st.markdown("**Mode:** Shared game mode")
        else:
            st.markdown("**Mode:** Local practice mode")

        st.caption(
            "Create or load a shared game ID to play from two browser sessions. "
            "This prototype uses manual refresh, not real-time multiplayer."
        )

        config, status_message = read_shared_game_storage_config()

        if config is None:
            st.info(status_message)
            st.caption(
                "Local practice still works without shared storage. "
                "Shared games are disabled until SUPABASE_URL and SUPABASE_KEY "
                "are configured in Streamlit secrets."
            )
        else:
            st.success(status_message)

        if active_game_id:
            st.markdown("**Active shared game ID**")
            st.code(active_game_id, language="text")
            st.caption(
                "Share this ID with the other player. Moves are saved after each legal move, "
                "but the other browser session must use manual refresh to see the latest position."
            )

            if st.button(
                "Refresh shared game",
                disabled=config is None,
                help="Reload the latest saved position for the active shared game ID.",
            ):
                if config is not None:
                    try:
                        refreshed_state = load_shared_game(
                            config,
                            active_game_id,
                        )
                    except Exception:
                        st.error(
                            "Shared game could not be refreshed. "
                            "Check the shared-game storage settings, table setup, or whether the storage service is paused."
                        )
                    else:
                        if refreshed_state is None:
                            st.warning(
                                "The active shared game ID was not found. "
                                "Check that the ID was copied correctly."
                            )
                        else:
                            apply_shared_game_state_to_session(
                                refreshed_state,
                                status_message=(
                                    f"Refreshed shared game `{refreshed_state.game_id}`. "
                                    "The board now shows the latest saved position."
                                ),
                            )
                            st.rerun()

        if st.session_state.shared_game_status:
            st.info(st.session_state.shared_game_status)

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
                            f"Created shared game `{state.game_id}`. "
                            "Share this ID with the other player."
                        ),
                    )
                    st.rerun()

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
            try:
                loaded_state = load_shared_game(config, requested_game_id)
            except ValueError as exc:
                st.error(str(exc))
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
                            f"Loaded shared game `{loaded_state.game_id}`. "
                            "Use manual refresh to check for later moves from the other player."
                        ),
                    )
                    st.rerun()


def main() -> None:
    st.set_page_config(page_title="Boardstep", layout="wide")
    initialize_game_state()

    st.title("Boardstep")
    st.caption("Chess practice.")

    st.write(
        "Click a piece, then click where it should move. Typed moves are optional."
    )

    render_shared_game_controls()

    rows = board_rows(st.session_state.fen)
    current_turn = current_turn_label(st.session_state.fen)

    board_col, game_col = st.columns([2, 1])

    with board_col:
        render_board_area(rows, apply_move_text)

    with game_col:
        render_game_panel(
            current_turn=current_turn,
            fen=st.session_state.fen,
            move_history=st.session_state.move_history,
            apply_move=apply_move_text,
            reset_game=reset_game,
            render_fen_load_controls=render_fen_load_controls,
        )


if __name__ == "__main__":
    main()
