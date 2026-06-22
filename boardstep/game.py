"""Core chess-state helpers for the Boardstep Streamlit app."""

import chess

STARTING_FEN = chess.STARTING_FEN
FILES = tuple("abcdefgh")


def board_rows(fen: str) -> list[dict[str, str]]:
    """Return the board as rank-indexed rows suitable for table display."""
    board = chess.Board(fen)
    rows = []

    # Display ranks from White's perspective: rank 8 at the top, rank 1 at the bottom.
    for rank in range(8, 0, -1):
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


def legal_move_count(fen: str) -> int:
    """Return the number of legal moves available in the current position."""
    board = chess.Board(fen)
    return len(list(board.legal_moves))


def game_status(fen: str) -> str:
    """Return a short human-readable status for the current position."""
    board = chess.Board(fen)

    if board.is_checkmate():
        winner = "Black" if board.turn == chess.WHITE else "White"
        return f"Checkmate. {winner} wins."

    if board.is_stalemate():
        return "Stalemate."

    if board.is_insufficient_material():
        return "Draw by insufficient material."

    if board.is_check():
        return f"{side_to_move(fen)} to move. Check."

    return f"{side_to_move(fen)} to move."


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
