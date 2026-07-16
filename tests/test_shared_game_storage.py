from datetime import datetime, timezone

import pytest

from boardstep.game import STARTING_FEN, apply_uci_move
from boardstep.shared_game import create_shared_game_state
from boardstep.shared_game_storage import (
    record_has_expected_last_move_number,
    shared_game_state_from_record,
    shared_game_state_to_record,
)


def test_shared_game_state_to_record_uses_database_shape() -> None:
    created_at = datetime(2026, 6, 22, 12, 0, tzinfo=timezone.utc)
    updated_at = datetime(2026, 6, 22, 12, 5, tzinfo=timezone.utc)
    state = create_shared_game_state(
        "game-001",
        move_history=["e2e4", "e7e5"],
        creator_side="black",
        created_at=created_at,
        updated_at=updated_at,
    )

    record = shared_game_state_to_record(state)

    assert record == {
        "game_id": "game-001",
        "fen": STARTING_FEN,
        "game_start_fen": STARTING_FEN,
        "move_uci_history": [],
        "move_history": ["e2e4", "e7e5"],
        "claimed_draw_reason": None,
        "creator_side": "black",
        "created_at": "2026-06-22T12:00:00+00:00",
        "updated_at": "2026-06-22T12:05:00+00:00",
        "last_move_number": 2,
    }


def test_shared_game_state_from_record_restores_state() -> None:
    record = {
        "game_id": "game-002",
        "fen": STARTING_FEN,
        "move_history": ["e2e4"],
        "creator_side": "black",
        "created_at": "2026-06-22T12:00:00Z",
        "updated_at": "2026-06-22T12:01:00Z",
        "last_move_number": 1,
    }

    state = shared_game_state_from_record(record)

    assert state.game_id == "game-002"
    assert state.fen == STARTING_FEN
    assert state.move_history == ("e2e4",)
    assert state.creator_side == "black"
    assert state.created_at == datetime(2026, 6, 22, 12, 0, tzinfo=timezone.utc)
    assert state.updated_at == datetime(2026, 6, 22, 12, 1, tzinfo=timezone.utc)
    assert state.last_move_number == 1


def test_shared_game_state_from_record_rejects_missing_field() -> None:
    record = {
        "game_id": "game-003",
        "fen": STARTING_FEN,
        "move_history": [],
        "created_at": "2026-06-22T12:00:00Z",
        "updated_at": "2026-06-22T12:00:00Z",
    }

    with pytest.raises(ValueError, match="last_move_number"):
        shared_game_state_from_record(record)


def test_shared_game_state_from_record_rejects_text_move_history() -> None:
    record = {
        "game_id": "game-004",
        "fen": STARTING_FEN,
        "move_history": "e2e4",
        "created_at": "2026-06-22T12:00:00Z",
        "updated_at": "2026-06-22T12:00:00Z",
        "last_move_number": 1,
    }

    with pytest.raises(ValueError, match="move_history"):
        shared_game_state_from_record(record)


def test_shared_game_state_from_record_rejects_mismatched_move_number() -> None:
    record = {
        "game_id": "game-005",
        "fen": STARTING_FEN,
        "move_history": ["e2e4"],
        "created_at": "2026-06-22T12:00:00Z",
        "updated_at": "2026-06-22T12:00:00Z",
        "last_move_number": 2,
    }

    with pytest.raises(ValueError, match="last_move_number"):
        shared_game_state_from_record(record)


def test_record_has_expected_last_move_number() -> None:
    record = {
        "last_move_number": 2,
    }

    assert record_has_expected_last_move_number(record, 2) is True
    assert record_has_expected_last_move_number(record, 1) is False


def test_record_has_expected_last_move_number_rejects_negative_expected_value() -> None:
    with pytest.raises(ValueError, match="must not be negative"):
        record_has_expected_last_move_number({"last_move_number": 0}, -1)


def test_shared_game_state_from_legacy_record_defaults_creator_side() -> None:
    record = {
        "game_id": "game-legacy",
        "fen": STARTING_FEN,
        "move_history": [],
        "created_at": "2026-06-22T12:00:00Z",
        "updated_at": "2026-06-22T12:00:00Z",
        "last_move_number": 0,
    }

    state = shared_game_state_from_record(record)

    assert state.creator_side == "white"


def test_shared_game_state_from_record_rejects_invalid_creator_side() -> None:
    record = {
        "game_id": "game-invalid-side",
        "fen": STARTING_FEN,
        "move_history": [],
        "creator_side": "observer",
        "created_at": "2026-06-22T12:00:00Z",
        "updated_at": "2026-06-22T12:00:00Z",
        "last_move_number": 0,
    }

    with pytest.raises(ValueError, match="white or black"):
        shared_game_state_from_record(record)

def test_shared_game_state_round_trip_preserves_legacy_history_baseline() -> None:
    fen = STARTING_FEN

    for move_text in ("e2e4", "e7e5"):
        fen, _ = apply_uci_move(fen, move_text)

    state = create_shared_game_state(
        "game-legacy-round-trip",
        fen=fen,
        move_history=[
            "1. e2e4 (e4)",
            "2. e7e5 (e5)",
        ],
    )

    restored_state = shared_game_state_from_record(
        shared_game_state_to_record(state)
    )

    assert restored_state.fen == fen
    assert restored_state.game_start_fen == fen
    assert restored_state.move_uci_history == ()
    assert restored_state.move_history == state.move_history
    assert restored_state.last_move_number == 2

def test_shared_game_state_from_record_restores_claimed_draw_reason() -> None:
    repetition_cycle = (
        "g1f3",
        "g8f6",
        "f3g1",
        "f6g8",
    )
    record = {
        "game_id": "game-claimed-draw",
        "fen": (
            "rnbqkbnr/pppppppp/8/8/8/8/"
            "PPPPPPPP/RNBQKBNR w KQkq - 8 5"
        ),
        "game_start_fen": STARTING_FEN,
        "move_uci_history": list(repetition_cycle * 2),
        "move_history": list(repetition_cycle * 2),
        "claimed_draw_reason": "threefold_repetition",
        "creator_side": "white",
        "created_at": "2026-06-22T12:00:00Z",
        "updated_at": "2026-06-22T12:01:00Z",
        "last_move_number": 8,
    }

    state = shared_game_state_from_record(record)

    assert state.claimed_draw_reason == "threefold_repetition"
