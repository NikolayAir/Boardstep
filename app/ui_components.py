"""Reusable Streamlit UI components for Boardstep."""

from collections.abc import Callable
import html

import streamlit as st

from boardstep.game import (
    build_uci_move,
    game_status,
    legal_move_count,
    legal_target_squares,
)

FILES = tuple("abcdefgh")

TEXT_PRESENTATION_SELECTOR = "\ufe0e"

WHITE_TO_FILLED_SYMBOL = {
    "♔": "♚",
    "♕": "♛",
    "♖": "♜",
    "♗": "♝",
    "♘": "♞",
    "♙": "♟",
}

BLACK_SYMBOLS = {"♚", "♛", "♜", "♝", "♞", "♟"}

ApplyMove = Callable[[str], None]
ResetGame = Callable[[], None]
RenderControls = Callable[[], None]


def render_board_html(rows: list[dict[str, str]]) -> str:
    """Render board rows as a styled HTML chessboard."""
    cells = [
        """
        <style>
            .boardstep-board {
                display: grid;
                grid-template-columns: 30px repeat(8, 64px);
                justify-content: center;
                align-items: center;
                margin: 1.25rem auto 1rem auto;
                width: fit-content;
                border: 1px solid #8e6d4a;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.18);
            }

            .boardstep-square {
                width: 64px;
                height: 64px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 40px;
                line-height: 1;
                font-family: "Apple Symbols", "Segoe UI Symbol", "Noto Sans Symbols 2", "DejaVu Sans", serif;
            }

            .boardstep-piece-white {
                color: #f7f0df;
                text-shadow: 0 1px 2px rgba(0, 0, 0, 0.45);
                font-variant-emoji: text;
            }

            .boardstep-piece-black {
                color: #20232a;
                text-shadow: 0 1px 2px rgba(255, 255, 255, 0.15);
                font-variant-emoji: text;
            }

            .boardstep-light {
                background: #e3cfad;
            }

            .boardstep-dark {
                background: #ab7c58;
            }

            .boardstep-rank-label,
            .boardstep-file-label {
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 0.85rem;
                font-weight: 600;
                color: #4b3927;
                background: #dbc7a4;
            }

            .boardstep-rank-label {
                height: 64px;
            }

            .boardstep-file-label {
                height: 30px;
            }
        </style>
        <div class="boardstep-board">
        """
    ]

    for row_index, row in enumerate(rows):
        cells.append(f'<div class="boardstep-rank-label">{html.escape(row["rank"])}</div>')

        for file_index, file_name in enumerate(FILES):
            square_color = (
                "boardstep-light"
                if (row_index + file_index) % 2 == 0
                else "boardstep-dark"
            )
            raw_piece = row[file_name]

            if raw_piece in WHITE_TO_FILLED_SYMBOL:
                piece_symbol = html.escape(
                    WHITE_TO_FILLED_SYMBOL[raw_piece] + TEXT_PRESENTATION_SELECTOR
                )
                piece = f'<span class="boardstep-piece-white">{piece_symbol}</span>'
            elif raw_piece in BLACK_SYMBOLS:
                piece_symbol = html.escape(raw_piece + TEXT_PRESENTATION_SELECTOR)
                piece = f'<span class="boardstep-piece-black">{piece_symbol}</span>'
            else:
                piece = "&nbsp;"

            cells.append(
                f'<div class="boardstep-square {square_color}">{piece}</div>'
            )

    cells.append('<div class="boardstep-file-label"></div>')

    for file_name in FILES:
        cells.append(f'<div class="boardstep-file-label">{file_name}</div>')

    cells.append("</div>")
    return "".join(cells)


def handle_square_click(square_name: str, apply_move: ApplyMove) -> None:
    """Handle click-based source and target square selection."""
    selected_square = st.session_state.selected_square

    if selected_square is None:
        st.session_state.selected_square = square_name
        st.session_state.click_move_error = None
        return

    try:
        move_text = build_uci_move(selected_square, square_name)
        apply_move(move_text)
    except ValueError as exc:
        st.session_state.click_move_error = f"Move not accepted: {exc}"
        st.session_state.selected_square = None


def render_click_move_controls(
    rows: list[dict[str, str]],
    apply_move: ApplyMove,
) -> None:
    """Render square buttons for click-based move input."""
    st.subheader("Move controls")
    st.caption(
        "Use these square buttons to make moves on the board above. "
        "Select a source square, then a target square."
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
            label = f"{piece} {square_name}" if piece else square_name

            if square_name in legal_targets:
                label = f"● {label}"

            if selected_square == square_name:
                label = f"▶ {label}"

            if column.button(
                label,
                key=f"square-{square_name}",
                use_container_width=True,
            ):
                handle_square_click(square_name, apply_move)
                st.rerun()


def render_board_area(
    rows: list[dict[str, str]],
    apply_move: ApplyMove,
) -> None:
    """Render the visual board and playable square controls."""
    st.markdown(
        render_board_html(rows),
        unsafe_allow_html=True,
    )

    render_click_move_controls(rows, apply_move)


def render_move_history(move_history: list[str]) -> None:
    """Render the current move history."""
    if move_history:
        st.subheader("Move history")
        st.text(" ".join(move_history))
    else:
        st.caption("No moves played yet.")


def render_typed_move_form(
    current_turn: str,
    apply_move: ApplyMove,
) -> None:
    """Render optional typed move input."""
    with st.expander("Typed move input"):
        with st.form("move_form", clear_on_submit=True):
            move_text = st.text_input(
                "Move",
                placeholder="e2e4",
                help=(
                    "Type the start square and target square, for example e2e4 or g1f3. "
                    "For promotion, add the new piece, for example e7e8q."
                ),
            )
            st.caption("Examples: e2e4, g1f3, b8c6, e7e8q for promotion.")
            submitted = st.form_submit_button(f"Play {current_turn} move")

        if submitted:
            try:
                apply_move(move_text)
                st.rerun()
            except ValueError as exc:
                st.error(f"Move not accepted: {exc}")
                st.caption(
                    "Check that it is the correct side to move and that the move is legal "
                    "in the current position."
                )


def render_position_tools(
    fen: str,
    render_fen_load_controls: RenderControls,
) -> None:
    """Render current-position tools and FEN loading controls."""
    with st.expander("Current position (FEN)"):
        st.caption(
            "Advanced: FEN is a compact text code for the current chess position. "
            "You can copy it for use in chess tools."
        )
        st.code(fen)

    render_fen_load_controls()


def render_game_actions(reset_game: ResetGame) -> None:
    """Render secondary game management actions."""
    with st.expander("Game actions"):
        st.caption("Reset starts a new local game and clears the current move history.")

        if st.button("Reset game"):
            reset_game()
            st.rerun()


def render_game_panel(
    *,
    current_turn: str,
    fen: str,
    move_history: list[str],
    apply_move: ApplyMove,
    reset_game: ResetGame,
    render_fen_load_controls: RenderControls,
) -> None:
    """Render game status, move history, typed input, and position tools."""
    st.subheader("Current game")

    st.markdown(f"**Turn:** {current_turn}")
    st.markdown(f"**Status:** {game_status(fen)}")
    st.markdown(f"**Legal moves:** {legal_move_count(fen)}")
    st.caption("Use the board controls to play. Typed input is available below.")

    render_move_history(move_history)
    render_typed_move_form(current_turn, apply_move)
    render_position_tools(fen, render_fen_load_controls)
    render_game_actions(reset_game)
