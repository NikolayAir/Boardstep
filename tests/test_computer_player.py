import random

import chess
import pytest

from boardstep.computer_player import (
    _SEARCH_INFINITY,
    _alpha_beta_score,
    _intermediate_move_score,
    _is_endgame,
    _ordered_hard_moves,
    _position_score,
    _quiescence_score,
    choose_computer_move,
)
from boardstep.game import STARTING_FEN, board_from_uci_history


def test_beginner_returns_legal_move_from_starting_position():
    move_text = choose_computer_move(
        STARTING_FEN,
        "beginner",
        rng=random.Random(1),
    )

    board = chess.Board(STARTING_FEN)

    assert move_text is not None
    assert chess.Move.from_uci(move_text) in board.legal_moves


def test_beginner_can_be_made_deterministic_with_injected_rng():
    first_move = choose_computer_move(
        STARTING_FEN,
        "beginner",
        rng=random.Random(7),
    )
    second_move = choose_computer_move(
        STARTING_FEN,
        "beginner",
        rng=random.Random(7),
    )

    assert first_move == second_move


@pytest.mark.parametrize(
    "level",
    ("beginner", "easy", "basic", "intermediate", "hard"),
)
def test_computer_move_returns_none_for_finished_game(level: str):
    fools_mate_fen = (
        "rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR "
        "w KQkq - 1 3"
    )

    assert choose_computer_move(fools_mate_fen, level) is None


def test_easy_prefers_immediate_checkmate():
    before_fools_mate_fen = (
        "rnbqkbnr/pppp1ppp/8/4p3/6P1/5P2/PPPPP2P/RNBQKBNR "
        "b KQkq g3 0 2"
    )

    assert choose_computer_move(
        before_fools_mate_fen,
        "easy",
        rng=random.Random(1),
    ) == "d8h4"


def test_easy_prefers_capture_when_no_immediate_mate_exists():
    fen = "4k3/8/8/8/3p4/4P3/8/4K3 b - - 0 1"

    assert choose_computer_move(
        fen,
        "easy",
        rng=random.Random(1),
    ) == "d4e3"


def test_basic_prefers_higher_material_gain():
    fen = "4k3/8/8/8/8/2q5/1P1Q4/4K3 b - - 0 1"

    assert choose_computer_move(
        fen,
        "basic",
        rng=random.Random(1),
    ) == "c3d2"


def test_intermediate_returns_legal_move_from_starting_position():
    move_text = choose_computer_move(
        STARTING_FEN,
        "intermediate",
        rng=random.Random(1),
    )

    board = chess.Board(STARTING_FEN)

    assert move_text is not None
    assert chess.Move.from_uci(move_text) in board.legal_moves


def test_intermediate_prefers_reasonable_opening_move_from_starting_position():
    assert choose_computer_move(
        STARTING_FEN,
        "intermediate",
        rng=random.Random(1),
    ) in {"c2c3", "c2c4", "d2d3", "d2d4", "e2e3", "e2e4", "g1f3", "b1c3"}


def test_intermediate_avoids_edge_knight_opening_move():
    assert choose_computer_move(
        STARTING_FEN,
        "intermediate",
        rng=random.Random(1),
    ) not in {"b1a3", "g1h3"}


def test_intermediate_opening_move_has_some_variety():
    opening_moves = {
        choose_computer_move(
            STARTING_FEN,
            "intermediate",
            rng=random.Random(seed),
        )
        for seed in range(30)
    }

    assert len(opening_moves) >= 2
    assert opening_moves <= {"c2c3", "c2c4", "d2d3", "d2d4", "e2e3", "e2e4", "g1f3", "b1c3"}


def test_intermediate_prefers_immediate_checkmate():
    before_fools_mate_fen = (
        "rnbqkbnr/pppp1ppp/8/4p3/6P1/5P2/PPPPP2P/RNBQKBNR "
        "b KQkq g3 0 2"
    )

    assert choose_computer_move(
        before_fools_mate_fen,
        "intermediate",
        rng=random.Random(1),
    ) == "d8h4"


def test_intermediate_prefers_queen_promotion():
    fen = "8/P6k/8/8/8/8/8/K7 w - - 0 1"

    assert choose_computer_move(
        fen,
        "intermediate",
        rng=random.Random(1),
    ) == "a7a8q"


def test_intermediate_prefers_safe_higher_material_gain():
    fen = "4k3/8/8/8/8/2q5/1P1Q4/K7 b - - 0 1"

    assert choose_computer_move(
        fen,
        "intermediate",
        rng=random.Random(1),
    ) == "c3d2"


def test_hard_returns_legal_move_from_starting_position():
    move_text = choose_computer_move(
        STARTING_FEN,
        "hard",
        rng=random.Random(1),
    )

    board = chess.Board(STARTING_FEN)

    assert move_text is not None
    assert chess.Move.from_uci(move_text) in board.legal_moves


def test_hard_prefers_immediate_checkmate():
    before_fools_mate_fen = (
        "rnbqkbnr/pppp1ppp/8/4p3/6P1/5P2/PPPPP2P/RNBQKBNR "
        "b KQkq g3 0 2"
    )

    assert choose_computer_move(
        before_fools_mate_fen,
        "hard",
        rng=random.Random(1),
    ) == "d8h4"


def test_hard_finds_forced_mate_in_two():
    fen = "8/k7/3K4/8/8/8/8/3Q4 w - - 0 11"

    assert choose_computer_move(
        fen,
        "hard",
        rng=random.Random(1),
    ) == "d6c7"


def test_hard_leaf_search_resolves_check_evasion():
    board = chess.Board(
        "7k/8/8/7Q/2K5/8/8/8 b - - 0 1"
    )
    evasion_scores = []

    for move in list(board.legal_moves):
        board.push(move)

        try:
            evasion_scores.append(
                _position_score(board, chess.WHITE)
            )
        finally:
            board.pop()

    score = _alpha_beta_score(
        board,
        depth=0,
        alpha=-_SEARCH_INFINITY,
        beta=_SEARCH_INFINITY,
        perspective_color=chess.WHITE,
    )

    assert score == min(evasion_scores)


def test_hard_leaf_search_resolves_immediate_capture_sequence():
    board = chess.Board(
        "3r3k/8/8/3Q4/2K5/8/8/8 b - - 0 1"
    )

    score = _alpha_beta_score(
        board,
        depth=0,
        alpha=-_SEARCH_INFINITY,
        beta=_SEARCH_INFINITY,
        perspective_color=chess.WHITE,
    )

    assert score == 0


def test_hard_search_scores_seventy_five_move_draw_as_zero():
    board = chess.Board(
        "7k/8/8/8/8/8/4K3/R7 w - - 150 76"
    )

    score = _alpha_beta_score(
        board,
        depth=1,
        alpha=-_SEARCH_INFINITY,
        beta=_SEARCH_INFINITY,
        perspective_color=chess.WHITE,
    )

    assert score == 0


def test_intermediate_scores_move_causing_seventy_five_move_draw_as_zero():
    board = chess.Board(
        "7k/8/8/8/8/8/4K3/R7 w - - 149 76"
    )

    score = _intermediate_move_score(
        board,
        chess.Move.from_uci("a1a2"),
        chess.WHITE,
    )

    assert score == 0


def test_hard_search_preserves_stalemate_penalty_when_ahead():
    board = chess.Board(
        "7k/5Q2/6K1/8/8/8/8/8 b - - 0 1"
    )

    score = _alpha_beta_score(
        board,
        depth=1,
        alpha=-_SEARCH_INFINITY,
        beta=_SEARCH_INFINITY,
        perspective_color=chess.WHITE,
    )

    assert score == -500


def test_hard_orders_more_valuable_capture_first():
    board = chess.Board(
        "2k5/p7/8/6q1/Q6P/8/8/1K6 w - - 0 1"
    )
    moves = [
        chess.Move.from_uci("a4a7"),
        chess.Move.from_uci("h4g5"),
    ]

    ordered_moves = _ordered_hard_moves(board, moves)

    assert [move.uci() for move in ordered_moves] == [
        "h4g5",
        "a4a7",
    ]


def test_hard_orders_quiet_check_before_quiet_move():
    board = chess.Board(
        "7k/8/8/8/2K5/8/P7/3Q4 w - - 0 1"
    )
    moves = [
        chess.Move.from_uci("a2a3"),
        chess.Move.from_uci("d1h5"),
    ]

    ordered_moves = _ordered_hard_moves(board, moves)

    assert [move.uci() for move in ordered_moves] == [
        "d1h5",
        "a2a3",
    ]


def test_queenless_position_with_major_pieces_is_not_endgame():
    board = chess.Board(
        "r5k1/p2nrppp/1p6/3P4/8/8/PP3PPP/R3K1NR w KQ - 0 17"
    )

    assert not _is_endgame(board)


def test_low_non_pawn_material_position_is_endgame():
    board = chess.Board(
        "8/8/8/3k4/8/3K4/4P3/8 w - - 0 1"
    )

    assert _is_endgame(board)


def test_hard_is_deterministic_for_equal_input():
    first_move = choose_computer_move(
        STARTING_FEN,
        "hard",
        rng=random.Random(7),
    )
    second_move = choose_computer_move(
        STARTING_FEN,
        "hard",
        rng=random.Random(7),
    )

    assert first_move == second_move


@pytest.mark.parametrize(
    "level",
    ("beginner", "easy", "basic", "intermediate", "hard"),
)
def test_computer_move_returns_none_for_automatic_fivefold_repetition(
    level: str,
):
    repetition_cycle = (
        "g1f3",
        "g8f6",
        "f3g1",
        "f6g8",
    )
    move_uci_history = repetition_cycle * 4
    board = board_from_uci_history(
        STARTING_FEN,
        move_uci_history,
    )

    assert choose_computer_move(
        board.fen(),
        level,
        game_start_fen=STARTING_FEN,
        move_uci_history=move_uci_history,
    ) is None


def test_computer_move_rejects_history_that_does_not_match_current_fen():
    with pytest.raises(ValueError, match="does not reconstruct"):
        choose_computer_move(
            STARTING_FEN,
            "beginner",
            game_start_fen=STARTING_FEN,
            move_uci_history=("e2e4",),
        )


def test_computer_move_requires_complete_history_arguments():
    with pytest.raises(ValueError, match="provided together"):
        choose_computer_move(
            STARTING_FEN,
            "beginner",
            game_start_fen=STARTING_FEN,
        )


def test_hard_search_allows_opponent_to_claim_threefold_draw():
    game_start_fen = (
        "6nk/8/8/8/8/8/Q7/KN6 b - - 0 1"
    )
    repetition_cycle = (
        "g8f6",
        "b1c3",
        "f6g8",
        "c3b1",
    )
    board = board_from_uci_history(
        game_start_fen,
        repetition_cycle * 2,
    )

    assert board.turn == chess.BLACK
    assert board.is_repetition(3)
    assert _position_score(board, chess.WHITE) > 0

    score = _alpha_beta_score(
        board,
        depth=0,
        alpha=-_SEARCH_INFINITY,
        beta=_SEARCH_INFINITY,
        perspective_color=chess.WHITE,
    )

    assert score == 0


def test_hard_search_does_not_force_computer_to_claim_threefold_draw():
    game_start_fen = (
        "6nk/8/8/8/8/8/Q7/KN6 w - - 0 1"
    )
    repetition_cycle = (
        "b1c3",
        "g8f6",
        "c3b1",
        "f6g8",
    )
    board = board_from_uci_history(
        game_start_fen,
        repetition_cycle * 2,
    )

    assert board.turn == chess.WHITE
    assert board.is_repetition(3)

    score = _alpha_beta_score(
        board,
        depth=0,
        alpha=-_SEARCH_INFINITY,
        beta=_SEARCH_INFINITY,
        perspective_color=chess.WHITE,
    )

    assert score > 0


@pytest.mark.parametrize("depth", (0, -1))
def test_hard_quiescence_allows_threefold_claim_at_depth_boundary(
    depth: int,
):
    game_start_fen = (
        "6nk/8/8/8/8/8/Q7/KN6 b - - 0 1"
    )
    repetition_cycle = (
        "g8f6",
        "b1c3",
        "f6g8",
        "c3b1",
    )
    board = board_from_uci_history(
        game_start_fen,
        repetition_cycle * 2,
    )

    assert board.turn == chess.BLACK
    assert board.is_repetition(3)
    assert _position_score(board, chess.WHITE) > 0

    score = _quiescence_score(
        board,
        depth=depth,
        alpha=-_SEARCH_INFINITY,
        beta=_SEARCH_INFINITY,
        perspective_color=chess.WHITE,
    )

    assert score == 0


def test_invalid_computer_level_is_rejected():
    with pytest.raises(ValueError, match="Computer level"):
        choose_computer_move(STARTING_FEN, "expert")
