import html

import streamlit as st

from boardstep.game import (
    STARTING_FEN,
    apply_uci_move,
    board_rows,
    game_status,
    legal_move_count,
)

FILES = tuple("abcdefgh")


def initialize_game_state() -> None:
    """Create the Streamlit session state used by the current chess game."""
    if "fen" not in st.session_state:
        st.session_state.fen = STARTING_FEN

    if "move_history" not in st.session_state:
        st.session_state.move_history = []


def reset_game() -> None:
    """Reset the current chess game to the starting position."""
    st.session_state.fen = STARTING_FEN
    st.session_state.move_history = []


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


def main() -> None:
    st.set_page_config(page_title="Boardstep", layout="centered")
    initialize_game_state()

    st.title("Boardstep")
    st.caption("Chess practice.")

    st.write(
        "Enter moves for both White and Black manually using UCI notation, "
        "for example e2e4, g1f3, or e7e8q for promotion."
    )

    st.markdown(
        render_board_html(board_rows(st.session_state.fen)),
        unsafe_allow_html=True,
    )

    current_turn = current_turn_label(st.session_state.fen)

    st.info(f"{current_turn} to move. Enter one legal move in UCI format.")
    st.write(f"**Game status:** {game_status(st.session_state.fen)}")
    st.write(f"**Legal moves for {current_turn}:** {legal_move_count(st.session_state.fen)}")

    with st.form("move_form", clear_on_submit=True):
        move_text = st.text_input(
            "Move in UCI notation",
            placeholder="e2e4",
            help=(
                "Use source square + target square, for example e2e4 or g1f3. "
                "For promotion, add the promotion piece, for example e7e8q."
            ),
        )
        st.caption("Examples: e2e4, g1f3, b8c6, e7e8q.")
        submitted = st.form_submit_button(f"Play {current_turn} move")

    if submitted:
        try:
            new_fen, san = apply_uci_move(st.session_state.fen, move_text)
            ply_number = len(st.session_state.move_history) + 1

            st.session_state.fen = new_fen
            st.session_state.move_history.append(
                f"{ply_number}. {move_text.strip().lower()} ({san})"
            )
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

    with st.expander("Current FEN"):
        st.code(st.session_state.fen)


if __name__ == "__main__":
    main()
