"""Reusable Streamlit UI components for Boardstep."""

from collections.abc import Callable
import streamlit as st

from boardstep.game import (
    build_uci_move,
    game_status,
    legal_move_count,
    legal_target_squares,
)

FILES = tuple("abcdefgh")

CLICKABLE_BOARD_HTML = """
<div id="boardstep-clickable-board" class="boardstep-clickable-board"></div>
"""

CLICKABLE_BOARD_CSS = """
.boardstep-clickable-board {
    display: grid;
    grid-template-columns: 30px repeat(8, 64px);
    justify-content: center;
    align-items: center;
    margin: 1.25rem auto 1rem auto;
    width: fit-content;
    border: 1px solid #8e6d4a;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.18);
}

.boardstep-square,
.boardstep-rank-label,
.boardstep-file-label {
    box-sizing: border-box;
}

.boardstep-square {
    width: 64px;
    height: 64px;
    border: 0;
    padding: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 40px;
    line-height: 1;
    font-family: "Apple Symbols", "Segoe UI Symbol", "Noto Sans Symbols 2", "DejaVu Sans", serif;
    cursor: pointer;
}

.boardstep-square:hover {
    outline: 3px solid rgba(255, 255, 255, 0.6);
    outline-offset: -3px;
}

.boardstep-selected {
    outline: 3px solid #2f80ed;
    outline-offset: -3px;
}

.boardstep-legal-target {
    box-shadow: inset 0 0 0 4px rgba(40, 160, 80, 0.65);
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
"""

CLICKABLE_BOARD_JS = """
export default function(component) {
    const { data, parentElement, setTriggerValue } = component;
    const root = parentElement.querySelector("#boardstep-clickable-board");

    const files = ["a", "b", "c", "d", "e", "f", "g", "h"];
    const whiteToFilledSymbol = {
        "♔": "♚",
        "♕": "♛",
        "♖": "♜",
        "♗": "♝",
        "♘": "♞",
        "♙": "♟"
    };
    const blackSymbols = new Set(["♚", "♛", "♜", "♝", "♞", "♟"]);

    function makeLabel(text, className) {
        const label = document.createElement("div");
        label.className = className;
        label.textContent = text;
        return label;
    }

    function makeSquare(row, fileName, rowIndex, fileIndex) {
        const squareName = `${fileName}${row.rank}`;
        const button = document.createElement("button");
        const isLight = (rowIndex + fileIndex) % 2 === 0;

        button.type = "button";
        button.className = `boardstep-square ${isLight ? "boardstep-light" : "boardstep-dark"}`;
        button.setAttribute("aria-label", `Select ${squareName}`);
        button.dataset.square = squareName;

        if (data?.selectedSquare === squareName) {
            button.classList.add("boardstep-selected");
        }

        if ((data?.legalTargets || []).includes(squareName)) {
            button.classList.add("boardstep-legal-target");
        }

        const rawPiece = row[fileName] || "";
        const piece = whiteToFilledSymbol[rawPiece] || rawPiece;

        if (piece) {
            const pieceSpan = document.createElement("span");
            pieceSpan.textContent = piece + "\\ufe0e";

            if (whiteToFilledSymbol[rawPiece]) {
                pieceSpan.className = "boardstep-piece-white";
            } else if (blackSymbols.has(rawPiece)) {
                pieceSpan.className = "boardstep-piece-black";
            }

            button.appendChild(pieceSpan);
        }

        button.onclick = () => {
            setTriggerValue("square", squareName);
        };

        return button;
    }

    root.replaceChildren();

    (data?.rows || []).forEach((row, rowIndex) => {
        root.appendChild(makeLabel(row.rank, "boardstep-rank-label"));

        files.forEach((fileName, fileIndex) => {
            root.appendChild(makeSquare(row, fileName, rowIndex, fileIndex));
        });
    });

    root.appendChild(makeLabel("", "boardstep-file-label"));

    files.forEach((fileName) => {
        root.appendChild(makeLabel(fileName, "boardstep-file-label"));
    });
}
"""

clickable_board_component = st.components.v2.component(
    name="boardstep_clickable_board",
    html=CLICKABLE_BOARD_HTML,
    css=CLICKABLE_BOARD_CSS,
    js=CLICKABLE_BOARD_JS,
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

def render_clickable_board(
    rows: list[dict[str, str]],
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
    apply_move: ApplyMove,
) -> None:
    """Render the visual board and playable square controls."""
    render_clickable_board(rows, apply_move)

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
