"""Simple computer move selection helpers for Boardstep."""

import random
from typing import Literal, cast

import chess

ComputerLevel = Literal["beginner", "easy", "basic"]

_VALID_LEVELS = {"beginner", "easy", "basic"}

_PIECE_VALUES = {
    chess.PAWN: 1,
    chess.KNIGHT: 3,
    chess.BISHOP: 3,
    chess.ROOK: 5,
    chess.QUEEN: 9,
    chess.KING: 0,
}


def choose_computer_move(
    fen: str,
    level: ComputerLevel,
    rng: random.Random | None = None,
) -> str | None:
    """Return a legal UCI move for the selected practice level.

    The helper is intentionally UI-independent. It does not read or modify
    Streamlit session state, shared-game state, or move history.
    """
    board = chess.Board(fen)
    normalized_level = _normalize_level(level)

    if board.is_game_over():
        return None

    legal_moves = list(board.legal_moves)

    if not legal_moves:
        return None

    random_source = rng if rng is not None else random.Random()

    if normalized_level == "beginner":
        return _choose_random_move(legal_moves, random_source).uci()

    if normalized_level == "easy":
        return _choose_easy_move(board, legal_moves, random_source).uci()

    return _choose_basic_move(board, legal_moves, random_source).uci()


def _normalize_level(level: str) -> ComputerLevel:
    normalized_level = level.strip().lower()

    if normalized_level not in _VALID_LEVELS:
        raise ValueError("Computer level must be beginner, easy, or basic.")

    return cast(ComputerLevel, normalized_level)


def _choose_random_move(
    moves: list[chess.Move],
    rng: random.Random,
) -> chess.Move:
    return rng.choice(moves)


def _choose_easy_move(
    board: chess.Board,
    moves: list[chess.Move],
    rng: random.Random,
) -> chess.Move:
    for priority_filter in (
        _is_checkmate_move,
        _is_capture_move,
        _is_check_move,
        _is_promotion_move,
    ):
        candidates = [move for move in moves if priority_filter(board, move)]

        if candidates:
            return _choose_random_move(candidates, rng)

    return _choose_random_move(moves, rng)


def _is_checkmate_move(board: chess.Board, move: chess.Move) -> bool:
    board.push(move)

    try:
        return board.is_checkmate()
    finally:
        board.pop()


def _is_capture_move(board: chess.Board, move: chess.Move) -> bool:
    return board.is_capture(move)


def _is_check_move(board: chess.Board, move: chess.Move) -> bool:
    return board.gives_check(move)


def _is_promotion_move(_board: chess.Board, move: chess.Move) -> bool:
    return move.promotion is not None


def _choose_basic_move(
    board: chess.Board,
    moves: list[chess.Move],
    rng: random.Random,
) -> chess.Move:
    perspective_color = board.turn
    scored_moves = [
        (_material_score_after_move(board, move, perspective_color), move)
        for move in moves
    ]
    best_score = max(score for score, _move in scored_moves)
    best_moves = [
        move
        for score, move in scored_moves
        if score == best_score
    ]

    return _choose_random_move(best_moves, rng)


def _material_score_after_move(
    board: chess.Board,
    move: chess.Move,
    perspective_color: chess.Color,
) -> int:
    board.push(move)

    try:
        return _material_score(board, perspective_color)
    finally:
        board.pop()


def _material_score(
    board: chess.Board,
    perspective_color: chess.Color,
) -> int:
    score = 0

    for piece in board.piece_map().values():
        piece_value = _PIECE_VALUES[piece.piece_type]

        if piece.color == perspective_color:
            score += piece_value
        else:
            score -= piece_value

    return score
