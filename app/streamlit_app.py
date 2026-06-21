import pandas as pd
import streamlit as st

from boardstep.game import (
    STARTING_FEN,
    apply_uci_move,
    board_rows,
    game_status,
    legal_move_count,
)


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


def main() -> None:
    st.set_page_config(page_title="Boardstep", layout="centered")
    initialize_game_state()

    st.title("Boardstep")
    st.caption("Chess practice.")

    st.write(
        "Enter moves for both White and Black manually using UCI notation, "
        "for example e2e4, g1f3, or e7e8q for promotion."
    )

    board_data = board_rows(st.session_state.fen)
    board_frame = pd.DataFrame(board_data).set_index("rank")

    st.table(board_frame)

    st.write(f"**Status:** {game_status(st.session_state.fen)}")
    st.write(f"**Legal moves:** {legal_move_count(st.session_state.fen)}")

    with st.form("move_form", clear_on_submit=True):
        move_text = st.text_input("Move", placeholder="e2e4")
        submitted = st.form_submit_button("Play move")

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
            st.error(str(exc))

    if st.button("Reset game"):
        reset_game()
        st.rerun()

    if st.session_state.move_history:
        st.subheader("Move history")
        st.write(" ".join(st.session_state.move_history))

    with st.expander("Current FEN"):
        st.code(st.session_state.fen)


if __name__ == "__main__":
    main()
