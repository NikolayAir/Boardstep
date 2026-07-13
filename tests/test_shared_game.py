from datetime import datetime, timezone

import pytest

from boardstep.game import STARTING_FEN, apply_uci_move
from boardstep.shared_game import (
    SHARED_GAME_ID_ALPHABET,
    create_shared_game_state,
    generate_shared_game_id,
    normalize_shared_game_side,
    opposite_shared_game_side,
    resolve_creator_side,
    normalize_shared_game_role,
    shared_game_move_restriction_message,
    shared_game_role_can_move,
    shared_game_turn_guidance,
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


def test_normalize_shared_game_role_accepts_known_roles() -> None:
    assert normalize_shared_game_role(" White ") == "white"
    assert normalize_shared_game_role("BLACK") == "black"
    assert normalize_shared_game_role("observer") == "observer"


def test_normalize_shared_game_role_rejects_unknown_role() -> None:
    with pytest.raises(ValueError, match="white, black, or observer"):
        normalize_shared_game_role("red")


def test_shared_game_role_can_move_for_matching_side() -> None:
    black_to_move_fen, _ = apply_uci_move(STARTING_FEN, "e2e4")

    assert shared_game_role_can_move("white", STARTING_FEN)
    assert not shared_game_role_can_move("black", STARTING_FEN)
    assert shared_game_role_can_move("black", black_to_move_fen)
    assert not shared_game_role_can_move("white", black_to_move_fen)


def test_shared_game_observer_cannot_move() -> None:
    assert not shared_game_role_can_move("observer", STARTING_FEN)
    assert (
        shared_game_move_restriction_message("observer", STARTING_FEN)
        == "Observer mode does not allow moves."
    )


def test_shared_game_move_restriction_message_allows_matching_side() -> None:
    assert shared_game_move_restriction_message("white", STARTING_FEN) is None


def test_shared_game_move_restriction_message_explains_wrong_side() -> None:
    assert (
        shared_game_move_restriction_message("black", STARTING_FEN)
        == "You selected Black for this session. It is White to move."
    )


def test_shared_game_turn_guidance_reports_current_role_state() -> None:
    black_to_move_fen, _ = apply_uci_move(STARTING_FEN, "e2e4")

    assert shared_game_turn_guidance("white", STARTING_FEN) == "Your move."
    assert shared_game_turn_guidance("black", STARTING_FEN) == "Waiting for White."
    assert shared_game_turn_guidance("black", black_to_move_fen) == "Your move."
    assert shared_game_turn_guidance("white", black_to_move_fen) == "Waiting for Black."
    assert shared_game_turn_guidance("observer", STARTING_FEN) == "Observer mode."


def test_create_shared_game_state_defaults_creator_side_to_white() -> None:
    state = create_shared_game_state("game-side-001")

    assert state.creator_side == "white"


def test_create_shared_game_state_normalizes_creator_side() -> None:
    state = create_shared_game_state(
        "game-side-002",
        creator_side=" Black ",
    )

    assert state.creator_side == "black"


def test_create_shared_game_state_rejects_invalid_creator_side() -> None:
    with pytest.raises(ValueError, match="white or black"):
        create_shared_game_state(
            "game-side-003",
            creator_side="observer",
        )


def test_normalize_shared_game_side_accepts_playable_sides() -> None:
    assert normalize_shared_game_side(" White ") == "white"
    assert normalize_shared_game_side("BLACK") == "black"


def test_opposite_shared_game_side_returns_other_color() -> None:
    assert opposite_shared_game_side("white") == "black"
    assert opposite_shared_game_side("black") == "white"


def test_resolve_creator_side_accepts_explicit_color() -> None:
    assert resolve_creator_side(" White ") == "white"
    assert resolve_creator_side("BLACK") == "black"


def test_resolve_creator_side_uses_random_choice(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "boardstep.shared_game.secrets.choice",
        lambda options: "black",
    )

    assert resolve_creator_side("random") == "black"


def test_resolve_creator_side_rejects_invalid_selection() -> None:
    with pytest.raises(ValueError, match="white, black, or random"):
        resolve_creator_side("observer")
