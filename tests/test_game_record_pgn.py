import io

import chess
import chess.pgn

from boardstep.game import STARTING_FEN
from boardstep.game_record import create_game_record
from boardstep.game_record_pgn import game_record_to_pgn


def _parse_pgn(pgn_text: str) -> chess.pgn.Game:
    game = chess.pgn.read_game(io.StringIO(pgn_text))

    assert game is not None
    assert game.errors == []

    return game


def test_game_record_to_pgn_has_stable_empty_game_output() -> None:
    record = create_game_record()

    assert game_record_to_pgn(record) == (
        '[Result "*"]\n'
        "\n"
        "*\n"
    )


def test_game_record_to_pgn_serializes_standard_start_game() -> None:
    record = create_game_record(
        move_uci_history=("e2e4", "e7e5"),
    )

    pgn_text = game_record_to_pgn(record)
    parsed_game = _parse_pgn(pgn_text)

    assert '[Result "*"]' in pgn_text
    assert '[FEN "' not in pgn_text
    assert '[SetUp "' not in pgn_text
    assert pgn_text.endswith("1. e4 e5 *\n")
    assert parsed_game.headers["Result"] == "*"
    assert parsed_game.board().fen() == STARTING_FEN
    assert tuple(
        move.uci()
        for move in parsed_game.mainline_moves()
    ) == ("e2e4", "e7e5")


def test_game_record_to_pgn_serializes_completed_game() -> None:
    record = create_game_record(
        move_uci_history=(
            "f2f3",
            "e7e5",
            "g2g4",
            "d8h4",
        ),
    )

    pgn_text = game_record_to_pgn(record)
    parsed_game = _parse_pgn(pgn_text)

    assert '[Result "0-1"]' in pgn_text
    assert pgn_text.endswith(
        "1. f3 e5 2. g4 Qh4# 0-1\n"
    )
    assert parsed_game.headers["Result"] == "0-1"
    assert tuple(
        move.uci()
        for move in parsed_game.mainline_moves()
    ) == (
        "f2f3",
        "e7e5",
        "g2g4",
        "d8h4",
    )


def test_game_record_to_pgn_serializes_claimed_draw() -> None:
    repetition_cycle = (
        "g1f3",
        "g8f6",
        "f3g1",
        "f6g8",
    )
    record = create_game_record(
        move_uci_history=repetition_cycle * 2,
        claimed_draw_reason="threefold_repetition",
    )

    pgn_text = game_record_to_pgn(record)
    parsed_game = _parse_pgn(pgn_text)

    assert '[Result "1/2-1/2"]' in pgn_text
    assert pgn_text.rstrip().endswith("1/2-1/2")
    assert parsed_game.headers["Result"] == "1/2-1/2"
    assert tuple(
        move.uci()
        for move in parsed_game.mainline_moves()
    ) == repetition_cycle * 2


def test_game_record_to_pgn_serializes_custom_fen_game() -> None:
    start_fen = "7k/8/8/8/8/8/4K3/R7 w - - 0 1"
    record = create_game_record(
        start_fen=start_fen,
        move_uci_history=("a1a2",),
    )

    pgn_text = game_record_to_pgn(record)
    parsed_game = _parse_pgn(pgn_text)

    assert '[Result "*"]' in pgn_text
    assert f'[FEN "{start_fen}"]' in pgn_text
    assert '[SetUp "1"]' in pgn_text
    assert pgn_text.endswith("1. Ra2 *\n")
    assert parsed_game.headers["Result"] == "*"
    assert parsed_game.headers["FEN"] == start_fen
    assert parsed_game.headers["SetUp"] == "1"
    assert parsed_game.board().fen() == start_fen
    assert tuple(
        move.uci()
        for move in parsed_game.mainline_moves()
    ) == ("a1a2",)


def test_game_record_to_pgn_is_deterministic() -> None:
    record = create_game_record(
        move_uci_history=("e2e4", "e7e5"),
    )

    first_export = game_record_to_pgn(record)
    second_export = game_record_to_pgn(record)

    assert first_export == second_export
    assert first_export.endswith("\n")


def test_game_record_to_pgn_preserves_custom_black_turn() -> None:
    start_fen = "7k/8/8/8/8/8/4K3/R7 b - - 0 12"
    record = create_game_record(
        start_fen=start_fen,
        move_uci_history=("h8g8",),
    )

    pgn_text = game_record_to_pgn(record)
    parsed_game = _parse_pgn(pgn_text)
    final_board = parsed_game.board()

    for move in parsed_game.mainline_moves():
        final_board.push(move)

    assert f'[FEN "{start_fen}"]' in pgn_text
    assert '[SetUp "1"]' in pgn_text
    assert "12... Kg8 *" in pgn_text
    assert parsed_game.board().turn == chess.BLACK
    assert parsed_game.board().fullmove_number == 12
    assert final_board.fen() == record.final_fen
