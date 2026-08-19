"""Simple computer move selection helpers for Boardstep."""

import random
from typing import Literal, Sequence, cast

import chess

from boardstep.game import board_from_uci_history

ComputerLevel = Literal["beginner", "easy", "basic", "intermediate", "hard"]

_VALID_LEVELS = {"beginner", "easy", "basic", "intermediate", "hard"}

_PIECE_VALUES = {
    chess.PAWN: 1,
    chess.KNIGHT: 3,
    chess.BISHOP: 3,
    chess.ROOK: 5,
    chess.QUEEN: 9,
    chess.KING: 0,
}

_CENTER_SQUARES = {
    chess.D4,
    chess.E4,
    chess.D5,
    chess.E5,
}

_EXTENDED_CENTER_SQUARES = {
    chess.C3,
    chess.D3,
    chess.E3,
    chess.F3,
    chess.C4,
    chess.F4,
    chess.C5,
    chess.F5,
    chess.C6,
    chess.D6,
    chess.E6,
    chess.F6,
}

_STARTING_MINOR_PIECE_SQUARES = {
    chess.B1,
    chess.C1,
    chess.F1,
    chess.G1,
    chess.B8,
    chess.C8,
    chess.F8,
    chess.G8,
}

_OPENING_FULLMOVE_LIMIT = 10
# Allows variety among reasonable opening moves instead of forcing one fixed opening.
_OPENING_VARIETY_SCORE_MARGIN = 95

_HARD_SEARCH_DEPTH = 3
_HARD_QUIESCENCE_DEPTH = 2
_SEARCH_INFINITY = 1_000_000


def choose_computer_move(
    fen: str,
    level: ComputerLevel,
    rng: random.Random | None = None,
    *,
    game_start_fen: str | None = None,
    move_uci_history: Sequence[str] | None = None,
) -> str | None:
    """Return a legal UCI move for the selected practice level.

    The helper is UI-independent. Optional move history is supplied explicitly
    so repetition outcomes can be evaluated without reading session state.
    """
    board = _computer_board_from_state(
        fen,
        game_start_fen=game_start_fen,
        move_uci_history=move_uci_history,
    )
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

    if normalized_level == "basic":
        return _choose_basic_move(board, legal_moves, random_source).uci()

    if normalized_level == "intermediate":
        return _choose_intermediate_move(
            board,
            legal_moves,
            random_source,
        ).uci()

    return _choose_hard_move(board, legal_moves).uci()


def _computer_board_from_state(
    fen: str,
    *,
    game_start_fen: str | None,
    move_uci_history: Sequence[str] | None,
) -> chess.Board:
    """Return the current board with optional repetition history."""
    current_board = chess.Board(fen)

    if game_start_fen is None and move_uci_history is None:
        return current_board

    if game_start_fen is None or move_uci_history is None:
        raise ValueError(
            "game_start_fen and move_uci_history must be provided together"
        )

    history_board = board_from_uci_history(
        game_start_fen,
        move_uci_history,
    )

    if history_board.fen() != current_board.fen():
        raise ValueError(
            "Computer move history does not reconstruct the current FEN."
        )

    return history_board


def _normalize_level(level: str) -> ComputerLevel:
    normalized_level = level.strip().lower()

    if normalized_level not in _VALID_LEVELS:
        raise ValueError(
            "Computer level must be beginner, easy, basic, intermediate, or hard."
        )

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


def _choose_intermediate_move(
    board: chess.Board,
    moves: list[chess.Move],
    rng: random.Random,
) -> chess.Move:
    checkmate_moves = [
        move
        for move in moves
        if _is_checkmate_move(board, move)
    ]

    if checkmate_moves:
        return _choose_random_move(checkmate_moves, rng)

    opening_move = _choose_intermediate_opening_move(board, moves, rng)

    if opening_move is not None:
        return opening_move

    perspective_color = board.turn
    scored_moves = [
        (_intermediate_move_score(board, move, perspective_color), move)
        for move in moves
    ]
    best_score = max(score for score, _move in scored_moves)
    best_moves = [
        move
        for score, move in scored_moves
        if score == best_score
    ]

    return _choose_random_move(best_moves, rng)


def _choose_intermediate_opening_move(
    board: chess.Board,
    moves: list[chess.Move],
    rng: random.Random,
) -> chess.Move | None:
    if board.fullmove_number > _OPENING_FULLMOVE_LIMIT:
        return None

    if board.is_check():
        return None

    if any(board.is_capture(move) for move in moves):
        return None

    legal_moves_by_uci = {move.uci(): move for move in moves}
    candidate_move_texts = {
        move_text
        for move_group in _opening_move_groups(board.turn)
        for move_text in move_group
    }
    candidates = [
        legal_moves_by_uci[move_text]
        for move_text in candidate_move_texts
        if move_text in legal_moves_by_uci
    ]

    if not candidates:
        return None

    perspective_color = board.turn
    scored_candidates = [
        (_intermediate_move_score(board, move, perspective_color), move)
        for move in candidates
    ]
    best_score = max(score for score, _move in scored_candidates)
    good_scored_candidates = [
        (score, move)
        for score, move in scored_candidates
        if score >= best_score - _OPENING_VARIETY_SCORE_MARGIN
    ]

    return _choose_weighted_scored_move(good_scored_candidates, rng)


def _choose_hard_move(
    board: chess.Board,
    moves: list[chess.Move],
) -> chess.Move:
    """Choose a move using bounded alpha-beta search."""
    perspective_color = board.turn
    ordered_moves = _ordered_hard_moves(board, moves)
    best_move = ordered_moves[0]
    best_score = -_SEARCH_INFINITY
    alpha = -_SEARCH_INFINITY
    beta = _SEARCH_INFINITY

    for move in ordered_moves:
        board.push(move)

        try:
            score = _alpha_beta_score(
                board,
                depth=_HARD_SEARCH_DEPTH - 1,
                alpha=alpha,
                beta=beta,
                perspective_color=perspective_color,
            )
        finally:
            board.pop()

        if score > best_score:
            best_score = score
            best_move = move

        alpha = max(alpha, best_score)

    return best_move


def _is_automatic_repetition_draw(board: chess.Board) -> bool:
    """Return whether repetition automatically ends the current game."""
    return board.is_fivefold_repetition()


def _opponent_can_claim_threefold(
    board: chess.Board,
    perspective_color: chess.Color,
) -> bool:
    """Return whether the human opponent can claim the current position."""
    return (
        board.turn != perspective_color
        and board.is_repetition(3)
    )


def _search_position_score(
    board: chess.Board,
    perspective_color: chess.Color,
) -> int:
    """Return a search score, treating supported automatic draws as zero."""
    if (
        _is_automatic_repetition_draw(board)
        or board.is_seventyfive_moves()
    ):
        return 0

    return _position_score(board, perspective_color)


def _alpha_beta_score(
    board: chess.Board,
    depth: int,
    alpha: int,
    beta: int,
    perspective_color: chess.Color,
) -> int:
    """Return a bounded minimax score using alpha-beta pruning."""
    if board.is_game_over():
        return _search_position_score(board, perspective_color)

    if depth <= 0:
        return _quiescence_score(
            board,
            depth=_HARD_QUIESCENCE_DEPTH,
            alpha=alpha,
            beta=beta,
            perspective_color=perspective_color,
        )

    moves = _ordered_hard_moves(board, list(board.legal_moves))

    if board.turn == perspective_color:
        best_score = -_SEARCH_INFINITY

        for move in moves:
            board.push(move)

            try:
                score = _alpha_beta_score(
                    board,
                    depth=depth - 1,
                    alpha=alpha,
                    beta=beta,
                    perspective_color=perspective_color,
                )
            finally:
                board.pop()

            best_score = max(best_score, score)
            alpha = max(alpha, best_score)

            if alpha >= beta:
                break

        return best_score

    best_score = (
        0
        if _opponent_can_claim_threefold(board, perspective_color)
        else _SEARCH_INFINITY
    )
    beta = min(beta, best_score)

    if alpha >= beta:
        return best_score

    for move in moves:
        board.push(move)

        try:
            score = _alpha_beta_score(
                board,
                depth=depth - 1,
                alpha=alpha,
                beta=beta,
                perspective_color=perspective_color,
            )
        finally:
            board.pop()

        best_score = min(best_score, score)
        beta = min(beta, best_score)

        if alpha >= beta:
            break

    return best_score


def _quiescence_score(
    board: chess.Board,
    depth: int,
    alpha: int,
    beta: int,
    perspective_color: chess.Color,
) -> int:
    """Extend leaf evaluation through bounded tactical continuations."""
    if board.is_game_over():
        return _search_position_score(board, perspective_color)

    stand_pat = _position_score(board, perspective_color)
    in_check = board.is_check()
    opponent_can_claim_threefold = _opponent_can_claim_threefold(
        board,
        perspective_color,
    )
    claim_adjusted_stand_pat = (
        min(stand_pat, 0)
        if opponent_can_claim_threefold
        else stand_pat
    )

    if depth < 0:
        return claim_adjusted_stand_pat

    if in_check:
        candidate_moves = list(board.legal_moves)
    else:
        if depth <= 0:
            return claim_adjusted_stand_pat

        candidate_moves = [
            move
            for move in board.legal_moves
            if board.is_capture(move) or move.promotion is not None
        ]

        if not candidate_moves:
            return claim_adjusted_stand_pat

    moves = _ordered_hard_moves(board, candidate_moves)
    maximizing = board.turn == perspective_color

    if maximizing:
        best_score = -_SEARCH_INFINITY if in_check else stand_pat

        if not in_check:
            if best_score >= beta:
                return best_score

            alpha = max(alpha, best_score)

        for move in moves:
            board.push(move)

            try:
                score = _quiescence_score(
                    board,
                    depth=depth - 1,
                    alpha=alpha,
                    beta=beta,
                    perspective_color=perspective_color,
                )
            finally:
                board.pop()

            best_score = max(best_score, score)
            alpha = max(alpha, best_score)

            if alpha >= beta:
                break

        return best_score

    best_score = _SEARCH_INFINITY if in_check else stand_pat

    if opponent_can_claim_threefold:
        best_score = min(best_score, 0)

    if best_score <= alpha:
        return best_score

    beta = min(beta, best_score)

    for move in moves:
        board.push(move)

        try:
            score = _quiescence_score(
                board,
                depth=depth - 1,
                alpha=alpha,
                beta=beta,
                perspective_color=perspective_color,
            )
        finally:
            board.pop()

        best_score = min(best_score, score)
        beta = min(beta, best_score)

        if alpha >= beta:
            break

    return best_score


def _ordered_hard_moves(
    board: chess.Board,
    moves: list[chess.Move],
) -> list[chess.Move]:
    """Order tactical moves first and use UCI text for stable tie-breaking."""
    return sorted(
        moves,
        key=lambda move: _hard_move_order_key(board, move),
    )


def _hard_move_order_key(
    board: chess.Board,
    move: chess.Move,
) -> tuple[int, int, int, int, int, int, str]:
    is_capture = board.is_capture(move)
    gives_check = board.gives_check(move)
    is_checkmate = False

    if gives_check:
        board.push(move)

        try:
            is_checkmate = board.is_checkmate()
        finally:
            board.pop()

    promotion_value = (
        _PIECE_VALUES[move.promotion]
        if move.promotion is not None
        else 0
    )
    captured_value, attacker_value = _capture_order_values(board, move)

    return (
        -int(is_checkmate),
        -promotion_value,
        -int(is_capture),
        -captured_value,
        attacker_value,
        -int(gives_check),
        move.uci(),
    )


def _capture_order_values(
    board: chess.Board,
    move: chess.Move,
) -> tuple[int, int]:
    """Return captured and moving piece values for capture ordering."""
    if not board.is_capture(move):
        return 0, 0

    moving_piece = board.piece_at(move.from_square)
    attacker_value = (
        _PIECE_VALUES[moving_piece.piece_type]
        if moving_piece is not None
        else 0
    )

    if board.is_en_passant(move):
        return _PIECE_VALUES[chess.PAWN], attacker_value

    captured_piece = board.piece_at(move.to_square)
    captured_value = (
        _PIECE_VALUES[captured_piece.piece_type]
        if captured_piece is not None
        else 0
    )

    return captured_value, attacker_value


def _choose_weighted_scored_move(
    scored_moves: list[tuple[int, chess.Move]],
    rng: random.Random,
) -> chess.Move:
    lowest_score = min(score for score, _move in scored_moves)
    weighted_moves = [
        (move, max(1, score - lowest_score + 1))
        for score, move in scored_moves
    ]
    moves = [move for move, _weight in weighted_moves]
    weights = [weight for _move, weight in weighted_moves]

    return rng.choices(moves, weights=weights, k=1)[0]


def _opening_move_groups(
    color: chess.Color,
) -> tuple[tuple[str, ...], ...]:
    if color == chess.WHITE:
        return (
            ("e2e4", "d2d4", "c2c4"),
            ("g1f3", "b1c3"),
            ("e2e3", "d2d3", "c2c3"),
            ("f1c4", "f1b5", "c1f4", "c1g5"),
            ("e1g1",),
        )

    return (
        ("e7e5", "d7d5", "c7c5"),
        ("g8f6", "b8c6"),
        ("e7e6", "d7d6", "c7c6"),
        ("f8c5", "f8b4", "c8f5", "c8g4"),
        ("e8g8",),
    )


def _intermediate_move_score(
    board: chess.Board,
    move: chess.Move,
    perspective_color: chess.Color,
) -> int:
    move_adjustment = _intermediate_move_adjustment(board, move)

    board.push(move)

    try:
        if board.is_checkmate():
            return 100_000 + move_adjustment

        if (
            _is_automatic_repetition_draw(board)
            or board.is_seventyfive_moves()
        ):
            return 0

        if board.is_game_over():
            return _position_score(board, perspective_color) + move_adjustment

        opponent_reply_scores = (
            [0]
            if board.is_repetition(3)
            else []
        )

        for opponent_move in board.legal_moves:
            board.push(opponent_move)

            try:
                opponent_reply_scores.append(
                    _search_position_score(board, perspective_color)
                )
            finally:
                board.pop()

        if not opponent_reply_scores:
            reply_score = _search_position_score(
                board,
                perspective_color,
            )
        else:
            reply_score = min(opponent_reply_scores)

        return reply_score + move_adjustment
    finally:
        board.pop()


def _intermediate_move_adjustment(
    board: chess.Board,
    move: chess.Move,
) -> int:
    moving_piece = board.piece_at(move.from_square)

    if moving_piece is None:
        return 0

    score = 0
    is_opening = board.fullmove_number <= _OPENING_FULLMOVE_LIMIT

    if board.is_castling(move):
        score += 55

    if board.gives_check(move):
        score += 12

    if move.promotion is not None:
        score += _PIECE_VALUES[move.promotion] * 35

    if move.to_square in _CENTER_SQUARES:
        score += 22
    elif move.to_square in _EXTENDED_CENTER_SQUARES:
        score += 8

    if moving_piece.piece_type == chess.PAWN:
        score += _pawn_move_adjustment(board, move, moving_piece, is_opening)

    if moving_piece.piece_type in {chess.KNIGHT, chess.BISHOP}:
        score += _minor_piece_move_adjustment(move, moving_piece, is_opening)

    if moving_piece.piece_type == chess.QUEEN:
        score += _queen_move_adjustment(board, move, is_opening)

    if moving_piece.piece_type == chess.KING and is_opening and not board.is_castling(move):
        score -= 45

    return score


def _pawn_move_adjustment(
    board: chess.Board,
    move: chess.Move,
    moving_piece: chess.Piece,
    is_opening: bool,
) -> int:
    score = 0

    if move.to_square in _CENTER_SQUARES:
        score += 26

    if is_opening and _is_two_square_central_pawn_push(move, moving_piece.color):
        score += 70

    if is_opening and _is_one_square_central_pawn_setup(move, moving_piece.color):
        score += 38

    if not is_opening:
        return score

    from_file = chess.square_file(move.from_square)

    if from_file in {chess.FILE_NAMES.index("f"), chess.FILE_NAMES.index("g")}:
        if _king_on_starting_square(board, moving_piece.color):
            score -= 38

    if from_file == chess.FILE_NAMES.index("h"):
        if _king_on_starting_square(board, moving_piece.color):
            score -= 30

    if from_file == chess.FILE_NAMES.index("a"):
        score -= 12

    return score


def _is_one_square_central_pawn_setup(
    move: chess.Move,
    color: chess.Color,
) -> bool:
    from_file = chess.square_file(move.from_square)
    from_rank = chess.square_rank(move.from_square)
    to_rank = chess.square_rank(move.to_square)

    if from_file not in {
        chess.FILE_NAMES.index("c"),
        chess.FILE_NAMES.index("d"),
        chess.FILE_NAMES.index("e"),
    }:
        return False

    if color == chess.WHITE:
        return from_rank == 1 and to_rank == 2

    return from_rank == 6 and to_rank == 5


def _is_two_square_central_pawn_push(
    move: chess.Move,
    color: chess.Color,
) -> bool:
    from_file = chess.square_file(move.from_square)
    from_rank = chess.square_rank(move.from_square)
    to_rank = chess.square_rank(move.to_square)

    if from_file not in {chess.FILE_NAMES.index("d"), chess.FILE_NAMES.index("e")}:
        return False

    if color == chess.WHITE:
        return from_rank == 1 and to_rank == 3

    return from_rank == 6 and to_rank == 4


def _minor_piece_move_adjustment(
    move: chess.Move,
    moving_piece: chess.Piece,
    is_opening: bool,
) -> int:
    score = 0
    target_file = chess.square_file(move.to_square)

    if moving_piece.piece_type == chess.KNIGHT and target_file in {0, 7}:
        score -= 65

    if move.from_square in _STARTING_MINOR_PIECE_SQUARES:
        score += 34
    elif is_opening:
        score -= 24

    return score


def _queen_move_adjustment(
    board: chess.Board,
    move: chess.Move,
    is_opening: bool,
) -> int:
    if not is_opening:
        return 0

    if board.is_capture(move) or board.gives_check(move):
        return -8

    return -34


def _king_on_starting_square(
    board: chess.Board,
    color: chess.Color,
) -> bool:
    starting_square = chess.E1 if color == chess.WHITE else chess.E8
    return board.king(color) == starting_square


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


def _position_score(
    board: chess.Board,
    perspective_color: chess.Color,
) -> int:
    if board.is_checkmate():
        return -100_000 if board.turn == perspective_color else 100_000

    if board.is_stalemate():
        material_score = _material_score(board, perspective_color)
        return -500 if material_score > 0 else 0

    if board.is_insufficient_material():
        return 0

    score = _material_score(board, perspective_color) * 100
    score += _positional_score(board, perspective_color)

    if board.is_check():
        if board.turn == perspective_color:
            score -= 25
        else:
            score += 25

    return score


def _positional_score(
    board: chess.Board,
    perspective_color: chess.Color,
) -> int:
    return (
        _piece_activity_score(board, perspective_color)
        + _castling_score(board, perspective_color)
        + _king_shelter_score(board, perspective_color)
        + _early_queen_score(board, perspective_color)
        + _passed_pawn_score(board, perspective_color)
        + _endgame_king_activity_score(board, perspective_color)
    )


def _piece_activity_score(
    board: chess.Board,
    perspective_color: chess.Color,
) -> int:
    score = 0

    for square, piece in board.piece_map().items():
        piece_score = 0

        if square in _CENTER_SQUARES:
            piece_score += 12
        elif square in _EXTENDED_CENTER_SQUARES:
            piece_score += 5

        if (
            piece.piece_type in {chess.KNIGHT, chess.BISHOP}
            and square not in _STARTING_MINOR_PIECE_SQUARES
        ):
            piece_score += 14

        if piece.piece_type == chess.KNIGHT and chess.square_file(square) in {0, 7}:
            piece_score -= 38

        if piece.color == perspective_color:
            score += piece_score
        else:
            score -= piece_score

    return score


def _castling_score(
    board: chess.Board,
    perspective_color: chess.Color,
) -> int:
    score = 0

    if board.king(chess.WHITE) in {chess.G1, chess.C1}:
        score += 18 if perspective_color == chess.WHITE else -18

    if board.king(chess.BLACK) in {chess.G8, chess.C8}:
        score += 18 if perspective_color == chess.BLACK else -18

    return score


def _king_shelter_score(
    board: chess.Board,
    perspective_color: chess.Color,
) -> int:
    score = 0

    for color in (chess.WHITE, chess.BLACK):
        king_square = board.king(color)

        if color == chess.WHITE and king_square == chess.E1:
            penalty = _missing_pawn_penalty(
                board,
                color,
                (chess.F2, chess.G2, chess.H2),
            )
        elif color == chess.BLACK and king_square == chess.E8:
            penalty = _missing_pawn_penalty(
                board,
                color,
                (chess.F7, chess.G7, chess.H7),
            )
        else:
            penalty = 0

        if color == perspective_color:
            score -= penalty
        else:
            score += penalty

    return score


def _missing_pawn_penalty(
    board: chess.Board,
    color: chess.Color,
    pawn_squares: tuple[chess.Square, ...],
) -> int:
    penalty = 0

    for square in pawn_squares:
        piece = board.piece_at(square)

        if piece is None or piece.color != color or piece.piece_type != chess.PAWN:
            penalty += 12

    return penalty


def _early_queen_score(
    board: chess.Board,
    perspective_color: chess.Color,
) -> int:
    score = 0

    for color, starting_square in (
        (chess.WHITE, chess.D1),
        (chess.BLACK, chess.D8),
    ):
        queen_square = _queen_square(board, color)

        if queen_square is None:
            continue

        moved_early = (
            queen_square != starting_square
            and board.fullmove_number <= 8
            and not _minor_pieces_developed(board, color)
        )

        if not moved_early:
            continue

        if color == perspective_color:
            score -= 12
        else:
            score += 12

    return score


def _queen_square(
    board: chess.Board,
    color: chess.Color,
) -> chess.Square | None:
    for square, piece in board.piece_map().items():
        if piece.color == color and piece.piece_type == chess.QUEEN:
            return square

    return None


def _minor_pieces_developed(
    board: chess.Board,
    color: chess.Color,
) -> bool:
    starting_squares = (
        (chess.B1, chess.C1, chess.F1, chess.G1)
        if color == chess.WHITE
        else (chess.B8, chess.C8, chess.F8, chess.G8)
    )

    developed_count = 0

    for square in starting_squares:
        piece = board.piece_at(square)

        if piece is None or piece.color != color:
            developed_count += 1

    return developed_count >= 2


def _passed_pawn_score(
    board: chess.Board,
    perspective_color: chess.Color,
) -> int:
    score = 0

    for square, piece in board.piece_map().items():
        if piece.piece_type != chess.PAWN:
            continue

        advancement = _pawn_advancement(square, piece.color)
        pawn_score = advancement * 6

        if _is_passed_pawn(board, square, piece.color):
            pawn_score += 18 + advancement * 12

        if piece.color == perspective_color:
            score += pawn_score
        else:
            score -= pawn_score

    return score


def _pawn_advancement(
    square: chess.Square,
    color: chess.Color,
) -> int:
    rank = chess.square_rank(square)

    if color == chess.WHITE:
        return rank

    return 7 - rank


def _is_passed_pawn(
    board: chess.Board,
    square: chess.Square,
    color: chess.Color,
) -> bool:
    file_index = chess.square_file(square)
    rank = chess.square_rank(square)
    enemy_color = not color

    for enemy_square, piece in board.piece_map().items():
        if piece.color != enemy_color or piece.piece_type != chess.PAWN:
            continue

        enemy_file = chess.square_file(enemy_square)
        enemy_rank = chess.square_rank(enemy_square)

        if abs(enemy_file - file_index) > 1:
            continue

        if color == chess.WHITE and enemy_rank > rank:
            return False

        if color == chess.BLACK and enemy_rank < rank:
            return False

    return True


def _endgame_king_activity_score(
    board: chess.Board,
    perspective_color: chess.Color,
) -> int:
    if not _is_endgame(board):
        return 0

    score = 0

    for color in (chess.WHITE, chess.BLACK):
        king_square = board.king(color)

        if king_square is None:
            continue

        king_score = _king_center_activity_score(king_square)

        if color == perspective_color:
            score += king_score
        else:
            score -= king_score

    return score


def _is_endgame(board: chess.Board) -> bool:
    return _non_pawn_material(board) <= 14


def _non_pawn_material(board: chess.Board) -> int:
    material = 0

    for piece in board.piece_map().values():
        if piece.piece_type in {chess.PAWN, chess.KING}:
            continue

        material += _PIECE_VALUES[piece.piece_type]

    return material


def _king_center_activity_score(square: chess.Square) -> int:
    file_index = chess.square_file(square)
    rank = chess.square_rank(square)
    center_distance = min(
        abs(file_index - chess.square_file(center_square))
        + abs(rank - chess.square_rank(center_square))
        for center_square in _CENTER_SQUARES
    )

    return max(0, 6 - center_distance) * 6


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
