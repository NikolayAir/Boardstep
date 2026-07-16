"""Core chess-state helpers for the Boardstep Streamlit app."""

from collections.abc import Sequence
from typing import Literal

import chess


STARTING_FEN = chess.STARTING_FEN
FILES = tuple("abcdefgh")
BoardOrientation = Literal["white", "black"]
RepetitionDrawState = Literal[
    "claimable_threefold",
    "automatic_fivefold",
]
ClaimedDrawReason = Literal["threefold_repetition"]


def board_files(orientation: BoardOrientation = "white") -> tuple[str, ...]:
    """Return file labels in display order for the selected board orientation."""
    if orientation == "white":
        return FILES

    if orientation == "black":
        return tuple(reversed(FILES))

    raise ValueError("Board orientation must be 'white' or 'black'.")


def board_ranks(orientation: BoardOrientation = "white") -> tuple[int, ...]:
    """Return ranks in display order for the selected board orientation."""
    if orientation == "white":
        return tuple(range(8, 0, -1))

    if orientation == "black":
        return tuple(range(1, 9))

    raise ValueError("Board orientation must be 'white' or 'black'.")


def validate_fen_position(fen: str) -> str:
    """Validate a pasted FEN string and return a normalized FEN string."""
    normalized_fen = fen.strip()

    if not normalized_fen:
        raise ValueError("Enter a FEN position to load.")

    try:
        board = chess.Board(normalized_fen)
    except ValueError as exc:
        raise ValueError("Enter a valid FEN position.") from exc

    if not board.is_valid():
        raise ValueError("Enter a valid FEN position.")

    return board.fen()


def board_from_uci_history(
    start_fen: str,
    move_uci_history: Sequence[str],
) -> chess.Board:
    """Reconstruct a board with move-stack history from legal UCI moves."""
    board = chess.Board(validate_fen_position(start_fen))

    for move_number, move_text in enumerate(move_uci_history, start=1):
        normalized_move = move_text.strip().lower()

        try:
            move = chess.Move.from_uci(normalized_move)
        except ValueError as exc:
            raise ValueError(
                f"Move history entry {move_number} is not valid UCI."
            ) from exc

        if move not in board.legal_moves:
            raise ValueError(
                f"Move history entry {move_number} is illegal for its position."
            )

        board.push(move)

    return board


def repetition_draw_state(
    board: chess.Board,
) -> RepetitionDrawState | None:
    """Return the current repetition-draw state for a board with history."""
    if board.is_fivefold_repetition():
        return "automatic_fivefold"

    if board.is_repetition(3):
        return "claimable_threefold"

    return None


def threefold_draw_can_be_claimed(board: chess.Board) -> bool:
    """Return whether the current position has occurred at least three times."""
    return (
        not board.is_game_over(claim_draw=False)
        and board.is_repetition(3)
    )


def game_is_over(
    board: chess.Board,
    claimed_draw_reason: ClaimedDrawReason | None = None,
) -> bool:
    """Return whether no further moves may be played."""
    return (
        claimed_draw_reason is not None
        or board.is_game_over(claim_draw=False)
    )


def board_rows(
    fen: str,
    orientation: BoardOrientation = "white",
) -> list[dict[str, str]]:
    """Return the board as rank-indexed rows suitable for table display."""
    board = chess.Board(fen)
    rows = []

    for rank in board_ranks(orientation):
        row = {"rank": str(rank)}

        for file_index, file_name in enumerate(FILES):
            square = chess.square(file_index, rank - 1)
            piece = board.piece_at(square)
            row[file_name] = piece.unicode_symbol() if piece else ""

        rows.append(row)

    return rows


def side_to_move(fen: str) -> str:
    """Return the side whose turn it is in a human-readable form."""
    board = chess.Board(fen)
    return "White" if board.turn == chess.WHITE else "Black"


def build_uci_move(source_square: str, target_square: str) -> str:
    """Build a UCI move from selected source and target squares."""
    source = source_square.strip().lower()
    target = target_square.strip().lower()

    try:
        chess.parse_square(source)
        chess.parse_square(target)
    except ValueError as exc:
        raise ValueError(
            "Select valid source and target squares, for example e2 and e4."
        ) from exc

    return f"{source}{target}"


def legal_target_squares(fen: str, source_square: str) -> list[str]:
    """Return legal destination squares for moves from a selected source square."""
    board = chess.Board(fen)
    normalized_source = source_square.strip().lower()

    try:
        source = chess.parse_square(normalized_source)
    except ValueError:
        return []

    return sorted(
        chess.square_name(move.to_square)
        for move in board.legal_moves
        if move.from_square == source
    )


def legal_move_count(fen: str) -> int:
    """Return the number of legal moves available in the current position."""
    board = chess.Board(fen)
    return len(list(board.legal_moves))


def game_status_from_board(
    board: chess.Board,
    claimed_draw_reason: ClaimedDrawReason | None = None,
) -> str:
    """Return a short human-readable status for a board with history."""
    if claimed_draw_reason == "threefold_repetition":
        return "Draw claimed by threefold repetition."

    if board.is_checkmate():
        winner = "Black" if board.turn == chess.WHITE else "White"
        return f"Checkmate. {winner} wins."

    if board.is_stalemate():
        return "Stalemate."

    if board.is_insufficient_material():
        return "Draw by insufficient material."

    repetition_state = repetition_draw_state(board)

    if repetition_state == "automatic_fivefold":
        return "Draw by fivefold repetition."

    side = "White" if board.turn == chess.WHITE else "Black"

    if board.is_check():
        status = f"{side} to move. Check."
    else:
        status = f"{side} to move."

    if threefold_draw_can_be_claimed(board):
        return f"{status} Draw can be claimed by threefold repetition."

    return status


def game_status(fen: str) -> str:
    """Return a short human-readable status for a FEN-only position."""
    return game_status_from_board(chess.Board(fen))


def apply_uci_move(fen: str, move_text: str) -> tuple[str, str]:
    """Apply a legal UCI move and return the updated FEN plus SAN notation."""
    board = chess.Board(fen)
    normalized_move = move_text.strip().lower()

    try:
        move = chess.Move.from_uci(normalized_move)
    except ValueError as exc:
        raise ValueError("Use UCI format, for example e2e4, g1f3, or e7e8q.") from exc

    if move not in board.legal_moves:
        raise ValueError("Illegal move for the current position.")

    # SAN is useful for readable move history, while FEN keeps the full board state.
    san = board.san(move)
    board.push(move)

    return board.fen(), san
