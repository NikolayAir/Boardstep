from dataclasses import FrozenInstanceError

import pytest

from boardstep.game import STARTING_FEN, board_from_uci_history
from boardstep.game_record import (
    GAME_RECORD_SCHEMA_VERSION,
    create_game_record,
)


def test_create_game_record_derives_normalized_ongoing_game() -> None:
    record = create_game_record(
        move_uci_history=[" E2E4 ", "E7E5"],
    )

    expected_board = board_from_uci_history(
        STARTING_FEN,
        ("e2e4", "e7e5"),
    )

    assert record.schema_version == GAME_RECORD_SCHEMA_VERSION
    assert record.start_fen == STARTING_FEN
    assert record.move_uci_history == ("e2e4", "e7e5")
    assert record.move_san_history == ("e4", "e5")
    assert record.final_fen == expected_board.fen()
    assert record.result == "*"
    assert record.termination_reason is None
    assert record.claimed_draw_reason is None


def test_game_record_is_immutable() -> None:
    record = create_game_record()

    with pytest.raises(FrozenInstanceError):
        record.result = "1-0"  # type: ignore[misc]


def test_create_game_record_rejects_invalid_start_fen() -> None:
    with pytest.raises(ValueError, match="valid FEN"):
        create_game_record(start_fen="not-a-fen")


def test_create_game_record_rejects_malformed_uci_history() -> None:
    with pytest.raises(ValueError, match="entry 1 is not valid UCI"):
        create_game_record(move_uci_history=["not-a-move"])


def test_create_game_record_rejects_illegal_uci_history() -> None:
    with pytest.raises(ValueError, match="entry 2 is illegal"):
        create_game_record(
            move_uci_history=["e2e4", "e2e3"],
        )


def test_create_game_record_derives_checkmate_result() -> None:
    record = create_game_record(
        move_uci_history=[
            "f2f3",
            "e7e5",
            "g2g4",
            "d8h4",
        ],
    )

    assert record.move_san_history == (
        "f3",
        "e5",
        "g4",
        "Qh4#",
    )
    assert record.result == "0-1"
    assert record.termination_reason == "checkmate"
    assert record.claimed_draw_reason is None


def test_create_game_record_supports_completed_custom_fen() -> None:
    stalemate_fen = "7k/5Q2/6K1/8/8/8/8/8 b - - 0 1"

    record = create_game_record(start_fen=stalemate_fen)

    assert record.start_fen == stalemate_fen
    assert record.move_uci_history == ()
    assert record.move_san_history == ()
    assert record.final_fen == stalemate_fen
    assert record.result == "1/2-1/2"
    assert record.termination_reason == "stalemate"


def test_create_game_record_accepts_valid_threefold_claim() -> None:
    repetition_cycle = (
        "g1f3",
        "g8f6",
        "f3g1",
        "f6g8",
    )

    record = create_game_record(
        move_uci_history=repetition_cycle * 2,
        claimed_draw_reason=" THREEFOLD_REPETITION ",
    )

    assert record.result == "1/2-1/2"
    assert record.termination_reason == "threefold_repetition"
    assert record.claimed_draw_reason == "threefold_repetition"


def test_create_game_record_rejects_invalid_threefold_claim() -> None:
    with pytest.raises(
        ValueError,
        match="Threefold repetition cannot be claimed",
    ):
        create_game_record(
            move_uci_history=["e2e4", "e7e5"],
            claimed_draw_reason="threefold_repetition",
        )


def test_create_game_record_rejects_unsupported_claim_reason() -> None:
    with pytest.raises(
        ValueError,
        match="must be threefold_repetition",
    ):
        create_game_record(claimed_draw_reason="stalemate")


def test_create_game_record_derives_automatic_fivefold_draw() -> None:
    repetition_cycle = (
        "g1f3",
        "g8f6",
        "f3g1",
        "f6g8",
    )

    record = create_game_record(
        move_uci_history=repetition_cycle * 4,
    )

    assert record.result == "1/2-1/2"
    assert record.termination_reason == "fivefold_repetition"
    assert record.claimed_draw_reason is None


def test_create_game_record_replays_moves_from_custom_fen() -> None:
    start_fen = "7k/8/8/8/8/8/4K3/R7 w - - 0 1"

    record = create_game_record(
        start_fen=start_fen,
        move_uci_history=[" A1A2 "],
    )

    expected_board = board_from_uci_history(
        start_fen,
        ("a1a2",),
    )

    assert record.start_fen == start_fen
    assert record.move_uci_history == ("a1a2",)
    assert record.move_san_history == ("Ra2",)
    assert record.final_fen == expected_board.fen()
    assert record.result == "*"
    assert record.termination_reason is None


def test_create_game_record_derives_insufficient_material_draw() -> None:
    insufficient_material_fen = (
        "8/8/8/8/8/8/4K3/7k w - - 0 1"
    )

    record = create_game_record(
        start_fen=insufficient_material_fen,
    )

    assert record.result == "1/2-1/2"
    assert record.termination_reason == "insufficient_material"
    assert record.claimed_draw_reason is None


def test_create_game_record_derives_seventy_five_move_draw() -> None:
    seventy_five_move_fen = (
        "rnbqkbnr/pppppppp/8/8/8/8/"
        "PPPPPPPP/RNBQKBNR w KQkq - 150 76"
    )

    record = create_game_record(
        start_fen=seventy_five_move_fen,
    )

    assert record.result == "1/2-1/2"
    assert record.termination_reason == "seventy_five_move_rule"
    assert record.claimed_draw_reason is None
