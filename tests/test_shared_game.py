from datetime import datetime, timezone

import pytest

from boardstep.game import STARTING_FEN
from boardstep.shared_game import (
    SHARED_GAME_ID_ALPHABET,
    create_shared_game_state,
    generate_shared_game_id,
)


def test_create_shared_game_state_uses_starting_position() -> None:
    state = create_shared_game_state("game-001")

    assert state.game_id == "game-001"
    assert state.fen == STARTING_FEN
    assert state.move_history == ()
    assert state.last_move_number == 0


def test_create_shared_game_state_strips_game_id() -> None:
    state = create_shared_game_state("  game-001  ")

    assert state.game_id == "game-001"


def test_create_shared_game_state_stores_move_history() -> None:
    state = create_shared_game_state(
        "game-002",
        move_history=["e2e4", "e7e5"],
    )

    assert state.move_history == ("e2e4", "e7e5")
    assert state.last_move_number == 2


def test_create_shared_game_state_accepts_explicit_timestamps() -> None:
    created_at = datetime(2026, 6, 22, 12, 0, tzinfo=timezone.utc)
    updated_at = datetime(2026, 6, 22, 12, 5, tzinfo=timezone.utc)

    state = create_shared_game_state(
        "game-003",
        created_at=created_at,
        updated_at=updated_at,
    )

    assert state.created_at == created_at
    assert state.updated_at == updated_at


def test_create_shared_game_state_rejects_empty_game_id() -> None:
    with pytest.raises(ValueError, match="game_id"):
        create_shared_game_state("   ")


def test_create_shared_game_state_rejects_invalid_fen_text() -> None:
    with pytest.raises(ValueError, match="valid FEN position"):
        create_shared_game_state("game-004", fen="not a fen")


def test_create_shared_game_state_rejects_invalid_fen_position() -> None:
    with pytest.raises(ValueError, match="valid FEN position"):
        create_shared_game_state("game-005", fen="8/8/8/8/8/8/8/8 w - - 0 1")


def test_generate_shared_game_id_uses_expected_length_and_alphabet() -> None:
    game_id = generate_shared_game_id(length=12)

    assert len(game_id) == 12
    assert set(game_id).issubset(set(SHARED_GAME_ID_ALPHABET))


def test_generate_shared_game_id_rejects_non_positive_length() -> None:
    with pytest.raises(ValueError, match="length"):
        generate_shared_game_id(length=0)
