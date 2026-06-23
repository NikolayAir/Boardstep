import html
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
    build_uci_move,
    game_status,
    legal_move_count,
    legal_target_squares,
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

FILES = tuple("abcdefgh")


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


def render_board_html(rows: list[dict[str, str]]) -> str:
    """Render board rows as a styled HTML chessboard."""
    cells = [
        """
        <style>
            .boardstep-board {
                display: grid;
                grid-template-columns: 28px repeat(8, 58px);
                justify-content: center;
                align-items: center;
                margin: 1.25rem auto 1rem auto;
                width: fit-content;
                border: 1px solid #8a7354;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.18);
            }

            .boardstep-square {
                width: 58px;
                height: 58px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 36px;
                line-height: 1;
                font-family: "Apple Color Emoji", "Segoe UI Symbol", "Noto Color Emoji", serif;
            }

            .boardstep-light {
                background: #f0d9b5;
            }

            .boardstep-dark {
                background: #b58863;
            }

            .boardstep-rank-label,
            .boardstep-file-label {
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 0.85rem;
                font-weight: 600;
                color: #4c3a27;
                background: #e6d3b1;
            }

            .boardstep-rank-label {
                height: 58px;
            }

            .boardstep-file-label {
                height: 28px;
            }
        </style>
        <div class="boardstep-board">
        """
    ]

    for row_index, row in enumerate(rows):
        cells.append(f'<div class="boardstep-rank-label">{html.escape(row["rank"])}</div>')

        for file_index, file_name in enumerate(FILES):
            square_color = "boardstep-light" if (row_index + file_index) % 2 == 0 else "boardstep-dark"
            piece = html.escape(row[file_name]) if row[file_name] else "&nbsp;"

            cells.append(
                f'<div class="boardstep-square {square_color}">{piece}</div>'
            )

    cells.append('<div class="boardstep-file-label"></div>')

    for file_name in FILES:
        cells.append(f'<div class="boardstep-file-label">{file_name}</div>')

    cells.append("</div>")
    return "".join(cells)


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
            "Shared game save was skipped because the saved move number is unknown. "
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
            "Shared game changed before this move was saved. "
            "Refresh the shared game before playing another move."
        )
    except Exception:
        st.session_state.shared_game_status = (
            "Move was played locally, but it could not be saved to shared storage. "
            "Check storage configuration and table setup."
        )
    else:
        st.session_state.shared_game_last_move_number = saved_state.last_move_number
        st.session_state.shared_game_status = (
            f"Saved latest move to shared game `{saved_state.game_id}`."
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
                "Move was played locally, but shared storage is not configured."
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


def handle_square_click(square_name: str) -> None:
    """Handle click-based source and target square selection."""
    selected_square = st.session_state.selected_square

    if selected_square is None:
        st.session_state.selected_square = square_name
        st.session_state.click_move_error = None
        return

    try:
        move_text = build_uci_move(selected_square, square_name)
        apply_move_text(move_text)
    except ValueError as exc:
        st.session_state.click_move_error = f"Move not accepted: {exc}"
        st.session_state.selected_square = None


def render_click_move_controls(rows: list[dict[str, str]]) -> None:
    """Render square buttons for click-based move input."""
    st.subheader("Click to move")
    st.caption(
        "Click a piece, then click where it should move. "
        "Use the typed move field only when needed, for example for promotion."
    )

    selected_square = st.session_state.selected_square
    legal_targets = (
        legal_target_squares(st.session_state.fen, selected_square)
        if selected_square
        else []
    )

    if selected_square and legal_targets:
        targets_text = ", ".join(legal_targets)
        st.info(
            f"Selected source square: {selected_square}. "
            f"Legal targets: {targets_text}."
        )

    if selected_square and not legal_targets:
        st.warning(
            f"Selected source square: {selected_square}. "
            "This square has no legal moves."
        )

    if st.session_state.click_move_error:
        st.error(st.session_state.click_move_error)

    for row in rows:
        columns = st.columns(8)

        for column, file_name in zip(columns, FILES):
            square_name = f"{file_name}{row['rank']}"
            piece = row[file_name]
            label = f"{piece or '·'} {square_name}"

            if square_name in legal_targets:
                label = f"● {label}"

            if selected_square == square_name:
                label = f"▶ {label}"

            if column.button(label, key=f"square-{square_name}"):
                handle_square_click(square_name)
                st.rerun()



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
    with st.expander("Shared game (manual refresh)"):
        st.caption(
            "Create or load a shared game ID. "
            "This uses manual refresh and is not real-time multiplayer."
        )

        config, status_message = read_shared_game_storage_config()

        if config is None:
            st.info(status_message)
            st.caption(
                "Local practice still works without shared storage. "
                "To enable this prototype, configure SUPABASE_URL and "
                "SUPABASE_KEY in Streamlit secrets."
            )
        else:
            st.success(status_message)

        if st.session_state.shared_game_id:
            st.write(f"Current shared game ID: `{st.session_state.shared_game_id}`")
            st.caption(
                "Moves played after creating or loading this ID are saved to shared storage. "
                "Use manual refresh on another device to load the latest saved position."
            )

            if st.button(
                "Refresh shared game",
                disabled=config is None,
                help="Reload the latest saved position for the current shared game ID.",
            ):
                if config is not None:
                    try:
                        refreshed_state = load_shared_game(
                            config,
                            st.session_state.shared_game_id,
                        )
                    except Exception:
                        st.error(
                            "Shared game could not be refreshed. "
                            "Check storage configuration and table setup."
                        )
                    else:
                        if refreshed_state is None:
                            st.warning("The current shared game ID was not found.")
                        else:
                            apply_shared_game_state_to_session(
                                refreshed_state,
                                status_message=(
                                    f"Refreshed shared game `{refreshed_state.game_id}`."
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
                        "Check storage configuration and table setup."
                    )
                else:
                    apply_shared_game_state_to_session(
                        state,
                        status_message=f"Created shared game `{state.game_id}`.",
                    )
                    st.rerun()

        with st.form("shared_game_load_form"):
            requested_game_id = st.text_input(
                "Shared game ID",
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
                    "Check storage configuration and table setup."
                )
            else:
                if loaded_state is None:
                    st.warning("No shared game was found for that ID.")
                else:
                    apply_shared_game_state_to_session(
                        loaded_state,
                        status_message=f"Loaded shared game `{loaded_state.game_id}`.",
                    )
                    st.rerun()


def main() -> None:
    st.set_page_config(page_title="Boardstep", layout="centered")
    initialize_game_state()

    st.title("Boardstep")
    st.caption("Chess practice.")

    st.write(
        "Click a piece, then click where it should move. Typed moves are optional."
    )

    render_fen_load_controls()
    render_shared_game_controls()

    rows = board_rows(st.session_state.fen)

    st.markdown(
        render_board_html(rows),
        unsafe_allow_html=True,
    )

    render_click_move_controls(rows)

    current_turn = current_turn_label(st.session_state.fen)

    st.info(f"{current_turn} to move. Click a piece or type one legal move.")
    st.write(f"**Game status:** {game_status(st.session_state.fen)}")
    st.write(f"**Legal moves for {current_turn}:** {legal_move_count(st.session_state.fen)}")

    with st.form("move_form", clear_on_submit=True):
        move_text = st.text_input(
            "Optional typed move",
            placeholder="e2e4",
            help=(
                "Type the start square and target square, for example e2e4 or g1f3. "
                "For promotion, add the new piece, for example e7e8q."
            ),
        )
        st.caption("Typed examples: e2e4, g1f3, b8c6, e7e8q for promotion.")
        submitted = st.form_submit_button(f"Play {current_turn} move")

    if submitted:
        try:
            apply_move_text(move_text)
            st.rerun()
        except ValueError as exc:
            st.error(f"Move not accepted: {exc}")
            st.caption(
                "Check that it is the correct side to move and that the move is legal "
                "in the current position."
            )

    if st.button("Reset game"):
        reset_game()
        st.rerun()

    if st.session_state.move_history:
        st.subheader("Move history")
        st.text(" ".join(st.session_state.move_history))

    with st.expander("Current position (FEN)"):
        st.caption(
            "Advanced: FEN is a compact text code for the current chess position. "
            "You can copy it for use in chess tools."
        )
        st.code(st.session_state.fen)


if __name__ == "__main__":
    main()
