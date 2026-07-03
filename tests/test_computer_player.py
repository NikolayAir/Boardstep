import random

import chess
import pytest

from boardstep.computer_player import choose_computer_move
from boardstep.game import STARTING_FEN


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


def test_computer_move_returns_none_for_finished_game():
    fools_mate_fen = (
        "rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR "
        "w KQkq - 1 3"
    )

    assert choose_computer_move(fools_mate_fen, "beginner") is None


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


def test_intermediate_prefers_higher_material_gain():
    fen = "4k3/8/8/8/8/2q5/1P1Q4/4K3 b - - 0 1"

    assert choose_computer_move(
        fen,
        "intermediate",
        rng=random.Random(1),
    ) == "c3d2"


def test_invalid_computer_level_is_rejected():
    with pytest.raises(ValueError, match="Computer level"):
        choose_computer_move(STARTING_FEN, "expert")
