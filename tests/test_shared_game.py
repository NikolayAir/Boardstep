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
    shared_game_state_has_update,
    shared_game_turn_guidance,
)


def test_create_shared_game_state_uses_starting_position() -> None:
    state = create_shared_game_state("game-001")

    assert state.game_id == "game-001"
    assert state.fen == STARTING_FEN
    assert state.game_start_fen == STARTING_FEN
    assert state.move_uci_history == ()
    assert state.move_history == ()
    assert state.claimed_draw_reason is None
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

    assert shared_game_turn_guidance("white", STARTING_FEN) == "Your turn."
    assert shared_game_turn_guidance("black", STARTING_FEN) == (
        "Waiting for opponent — White to move."
    )
    assert shared_game_turn_guidance("black", black_to_move_fen) == "Your turn."
    assert shared_game_turn_guidance("white", black_to_move_fen) == (
        "Waiting for opponent — Black to move."
    )
    assert shared_game_turn_guidance("observer", STARTING_FEN) == (
        "Observer mode — moves are disabled."
    )


def test_shared_game_state_update_detects_move_or_draw_changes() -> None:
    unchanged_state = create_shared_game_state("game-update")
    moved_state = create_shared_game_state(
        "game-update",
        move_history=["e2e4"],
    )

    repetition_cycle = (
        "g1f3",
        "g8f6",
        "f3g1",
        "f6g8",
    )
    move_uci_history = repetition_cycle * 2
    fen = STARTING_FEN

    for move_text in move_uci_history:
        fen, _ = apply_uci_move(fen, move_text)

    claimed_state = create_shared_game_state(
        "game-update",
        fen=fen,
        game_start_fen=STARTING_FEN,
        move_uci_history=move_uci_history,
        move_history=move_uci_history,
        claimed_draw_reason="threefold_repetition",
    )

    assert not shared_game_state_has_update(
        previous_last_move_number=0,
        previous_claimed_draw_reason=None,
        refreshed_state=unchanged_state,
    )
    assert shared_game_state_has_update(
        previous_last_move_number=0,
        previous_claimed_draw_reason=None,
        refreshed_state=moved_state,
    )
    assert shared_game_state_has_update(
        previous_last_move_number=claimed_state.last_move_number,
        previous_claimed_draw_reason=None,
        refreshed_state=claimed_state,
    )
    assert not shared_game_state_has_update(
        previous_last_move_number=claimed_state.last_move_number,
        previous_claimed_draw_reason="threefold_repetition",
        refreshed_state=claimed_state,
    )


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

def test_create_shared_game_state_stores_structured_move_history() -> None:
    fen = STARTING_FEN

    for move_text in ("e2e4", "e7e5"):
        fen, _ = apply_uci_move(fen, move_text)

    state = create_shared_game_state(
        "game-history-001",
        fen=fen,
        game_start_fen=STARTING_FEN,
        move_uci_history=[" E2E4 ", "E7E5"],
        move_history=["1. e2e4 (e4)", "2. e7e5 (e5)"],
    )

    assert state.game_start_fen == STARTING_FEN
    assert state.move_uci_history == ("e2e4", "e7e5")
    assert state.move_history == (
        "1. e2e4 (e4)",
        "2. e7e5 (e5)",
    )
    assert state.last_move_number == 2


def test_create_shared_game_state_rejects_mismatched_structured_fen() -> None:
    with pytest.raises(ValueError, match="does not reconstruct"):
        create_shared_game_state(
            "game-history-002",
            fen=STARTING_FEN,
            game_start_fen=STARTING_FEN,
            move_uci_history=["e2e4"],
            move_history=["1. e2e4 (e4)"],
        )


def test_create_shared_game_state_rejects_uci_history_longer_than_display_history() -> None:
    fen, _ = apply_uci_move(STARTING_FEN, "e2e4")

    with pytest.raises(ValueError, match="cannot be longer"):
        create_shared_game_state(
            "game-history-003",
            fen=fen,
            game_start_fen=STARTING_FEN,
            move_uci_history=["e2e4"],
            move_history=[],
        )


def test_create_shared_game_state_requires_start_fen_for_uci_history() -> None:
    with pytest.raises(ValueError, match="game_start_fen is required"):
        create_shared_game_state(
            "game-history-004",
            move_uci_history=["e2e4"],
        )

def test_create_shared_game_state_allows_structured_history_suffix() -> None:
    baseline_fen = STARTING_FEN

    for move_text in ("e2e4", "e7e5"):
        baseline_fen, _ = apply_uci_move(baseline_fen, move_text)

    current_fen, _ = apply_uci_move(baseline_fen, "g1f3")

    state = create_shared_game_state(
        "game-history-suffix",
        fen=current_fen,
        game_start_fen=baseline_fen,
        move_uci_history=["g1f3"],
        move_history=[
            "1. e2e4 (e4)",
            "2. e7e5 (e5)",
            "3. g1f3 (Nf3)",
        ],
    )

    assert state.game_start_fen == baseline_fen
    assert state.move_uci_history == ("g1f3",)
    assert state.last_move_number == 3

def test_create_shared_game_state_normalizes_claimed_draw_reason() -> None:
    repetition_cycle = (
        "g1f3",
        "g8f6",
        "f3g1",
        "f6g8",
    )
    state = create_shared_game_state(
        "game-draw-001",
        fen=(
            "rnbqkbnr/pppppppp/8/8/8/8/"
            "PPPPPPPP/RNBQKBNR w KQkq - 8 5"
        ),
        game_start_fen=STARTING_FEN,
        move_uci_history=repetition_cycle * 2,
        move_history=repetition_cycle * 2,
        claimed_draw_reason=" THREEFOLD_REPETITION ",
    )

    assert state.claimed_draw_reason == "threefold_repetition"


def test_create_shared_game_state_rejects_invalid_claimed_draw_reason() -> None:
    with pytest.raises(ValueError, match="Claimed draw reason"):
        create_shared_game_state(
            "game-draw-002",
            claimed_draw_reason="stalemate",
        )

def test_create_shared_game_state_rejects_unavailable_threefold_claim() -> None:
    with pytest.raises(
        ValueError,
        match="Threefold repetition cannot be claimed",
    ):
        create_shared_game_state(
            "game-draw-003",
            claimed_draw_reason="threefold_repetition",
        )
