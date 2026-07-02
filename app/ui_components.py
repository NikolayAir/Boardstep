"""Reusable Streamlit UI components for Boardstep."""

from collections.abc import Callable
from pathlib import Path

import streamlit as st

from boardstep.game import (
    build_uci_move,
    game_status,
    legal_move_count,
    legal_target_squares,
)

_COMPONENTS_DIR = Path(__file__).parent / "components"


def _read_component_asset(filename: str) -> str:
    return (_COMPONENTS_DIR / filename).read_text(encoding="utf-8")


_CLICKABLE_BOARD_HTML = _read_component_asset("clickable_board.html")
_CLICKABLE_BOARD_CSS = _read_component_asset("clickable_board.css")
_CLICKABLE_BOARD_JS = _read_component_asset("clickable_board.js")

clickable_board_component = st.components.v2.component(
    name="boardstep_clickable_board",
    html=_CLICKABLE_BOARD_HTML,
    css=_CLICKABLE_BOARD_CSS,
    js=_CLICKABLE_BOARD_JS,
)

ApplyMove = Callable[[str], None]
ResetGame = Callable[[], None]
RenderControls = Callable[[], None]


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
    files: tuple[str, ...],
    apply_move: ApplyMove,
) -> None:
    """Render click-move feedback and optional coordinate-practice controls."""
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

    show_coordinate_controls = st.toggle(
        "Coordinate practice controls",
        value=False,
        key="show_coordinate_practice_controls",
    )

    if show_coordinate_controls:
        st.caption(
            "Use these controls to practice square names or as a fallback for making moves."
        )

        for row in rows:
            columns = st.columns(len(files))

            for column, file_name in zip(columns, files):
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


def render_clickable_board(
    rows: list[dict[str, str]],
    files: tuple[str, ...],
    apply_move: ApplyMove,
) -> None:
    """Render the clickable main chessboard."""
    selected_square = st.session_state.selected_square
    legal_targets = (
        legal_target_squares(st.session_state.fen, selected_square)
        if selected_square
        else []
    )

    result = clickable_board_component(
        data={
            "rows": rows,
            "files": list(files),
            "selectedSquare": selected_square,
            "legalTargets": legal_targets,
        },
        key="main_clickable_board",
        height=590,
        on_square_change=lambda: None,
    )

    clicked_square = result.square

    if clicked_square:
        handle_square_click(clicked_square, apply_move)
        st.rerun()


def render_board_area(
    rows: list[dict[str, str]],
    files: tuple[str, ...],
    apply_move: ApplyMove,
) -> None:
    """Render the visual board and playable square controls."""
    render_clickable_board(rows, files, apply_move)

    render_click_move_controls(rows, files, apply_move)


def render_move_history(move_history: list[str]) -> None:
    """Render the current move history."""
    if move_history:
        st.subheader("Move history")
        st.text(" ".join(move_history))
    else:
        st.caption("No moves played yet.")


def render_typed_move_form(
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
            submitted = st.form_submit_button("Play move")

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
    fen: str,
    move_history: list[str],
    apply_move: ApplyMove,
    reset_game: ResetGame,
    render_fen_load_controls: RenderControls,
) -> None:
    """Render game status, move history, typed input, and position tools."""
    st.subheader("Current game")

    st.markdown(f"**Status:** {game_status(fen)}")
    st.markdown(f"**Legal moves:** {legal_move_count(fen)}")

    render_move_history(move_history)
    render_typed_move_form(apply_move)
    render_position_tools(fen, render_fen_load_controls)
    render_game_actions(reset_game)
