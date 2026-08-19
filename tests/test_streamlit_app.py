from types import SimpleNamespace
from typing import Any

import pytest

from app import streamlit_app
from boardstep.game import (
    STARTING_FEN,
    apply_uci_move,
    board_from_uci_history,
)
from boardstep.shared_game import create_shared_game_state
from boardstep.supabase_rest_storage import SharedGameStorageConflictError


def set_session_state(monkeypatch: Any, **values: object) -> SimpleNamespace:
    state = SimpleNamespace(**values)
    monkeypatch.setattr(streamlit_app.st, "session_state", state)
    return state


def fail_if_called(*args: object, **kwargs: object) -> None:
    raise AssertionError("This function should not have been called.")


class FakeSessionState(dict[str, object]):
    def __getattr__(self, name: str) -> object:
        return self[name]

    def __setattr__(self, name: str, value: object) -> None:
        self[name] = value


def set_shared_game_session(
    monkeypatch: Any,
    **overrides: object,
) -> SimpleNamespace:
    values: dict[str, object] = {
        "fen": STARTING_FEN,
        "game_start_fen": STARTING_FEN,
        "move_uci_history": [],
        "move_history": [],
        "claimed_draw_reason": None,
        "selected_square": None,
        "click_move_error": None,
        "shared_game_id": "game-recovery",
        "shared_game_creator_side": "white",
        "shared_game_last_move_number": 0,
        "shared_game_recovery_required": False,
        "shared_game_status": None,
        "shared_game_last_synced_at": None,
        "shared_game_auto_refresh_enabled": False,
        "shared_game_role": "white",
        "shared_game_assigned_side": "white",
        "shared_game_pending_assigned_side": None,
        "game_mode": "shared",
        "last_computer_move": None,
        "computer_move_pending": False,
    }
    values.update(overrides)
    return set_session_state(monkeypatch, **values)


def threefold_repetition_state_values() -> dict[str, object]:
    move_uci_history = list(
        (
            "g1f3",
            "g8f6",
            "f3g1",
            "f6g8",
        )
        * 2
    )
    board = board_from_uci_history(STARTING_FEN, move_uci_history)
    return {
        "fen": board.fen(),
        "move_uci_history": move_uci_history,
        "move_history": list(move_uci_history),
        "shared_game_last_move_number": len(move_uci_history),
    }


def test_clear_computer_practice_session_clears_transient_state(
    monkeypatch: Any,
) -> None:
    state = set_session_state(
        monkeypatch,
        last_computer_move="e7e5 (e5)",
        computer_move_pending=True,
    )

    streamlit_app.clear_computer_practice_session()

    assert state.last_computer_move is None
    assert state.computer_move_pending is False


def test_initialise_game_state_defaults_shared_recovery_to_false(
    monkeypatch: Any,
) -> None:
    state = FakeSessionState()
    monkeypatch.setattr(streamlit_app.st, "session_state", state)

    streamlit_app.initialize_game_state()

    assert state.shared_game_recovery_required is False

    state.shared_game_recovery_required = True
    streamlit_app.initialize_game_state()

    assert state.shared_game_recovery_required is True


@pytest.mark.parametrize(
    "transition",
    ("clear", "leave", "reset", "load_fen"),
)
def test_shared_session_transitions_clear_recovery(
    monkeypatch: Any,
    transition: str,
) -> None:
    state = set_shared_game_session(
        monkeypatch,
        shared_game_recovery_required=True,
    )

    if transition == "clear":
        streamlit_app.clear_shared_game_session()
    elif transition == "leave":
        streamlit_app.leave_shared_game_session()
    elif transition == "reset":
        streamlit_app.reset_game()
    else:
        streamlit_app.load_fen_position(STARTING_FEN)

    assert state.shared_game_id == ""
    assert state.shared_game_recovery_required is False


def test_computer_reply_is_skipped_without_pending_state(
    monkeypatch: Any,
) -> None:
    state = set_session_state(
        monkeypatch,
        computer_move_pending=False,
    )
    monkeypatch.setattr(
        streamlit_app,
        "is_computer_practice_turn",
        fail_if_called,
    )
    monkeypatch.setattr(
        streamlit_app,
        "choose_computer_move",
        fail_if_called,
    )

    streamlit_app.apply_computer_reply_if_needed()

    assert state.computer_move_pending is False


def test_stale_pending_state_is_cleared_when_computer_turn_has_ended(
    monkeypatch: Any,
) -> None:
    state = set_session_state(
        monkeypatch,
        computer_move_pending=True,
    )
    monkeypatch.setattr(
        streamlit_app,
        "is_computer_practice_turn",
        lambda: False,
    )
    monkeypatch.setattr(
        streamlit_app,
        "choose_computer_move",
        fail_if_called,
    )

    streamlit_app.apply_computer_reply_if_needed()

    assert state.computer_move_pending is False


def test_pending_computer_reply_is_applied_exactly_once(
    monkeypatch: Any,
) -> None:
    state = set_session_state(
        monkeypatch,
        fen="current-fen",
        game_start_fen="start-fen",
        move_uci_history=["e2e4"],
        computer_level="hard",
        last_computer_move=None,
        computer_move_pending=True,
    )
    chosen_moves: list[tuple[object, ...]] = []
    applied_moves: list[str] = []

    def choose_move(
        fen: str,
        level: str,
        *,
        game_start_fen: str,
        move_uci_history: list[str],
    ) -> str:
        chosen_moves.append(
            (fen, level, game_start_fen, tuple(move_uci_history))
        )
        return "e7e5"

    def apply_move(move_text: str) -> str:
        applied_moves.append(move_text)
        return "e5"

    monkeypatch.setattr(
        streamlit_app,
        "is_computer_practice_turn",
        lambda: True,
    )
    monkeypatch.setattr(
        streamlit_app,
        "choose_computer_move",
        choose_move,
    )
    monkeypatch.setattr(
        streamlit_app,
        "apply_legal_move_to_session",
        apply_move,
    )

    streamlit_app.apply_computer_reply_if_needed()
    streamlit_app.apply_computer_reply_if_needed()

    assert chosen_moves == [
        ("current-fen", "hard", "start-fen", ("e2e4",))
    ]
    assert applied_moves == ["e7e5"]
    assert state.last_computer_move == "e7e5 (e5)"
    assert state.computer_move_pending is False


def test_pending_state_is_cleared_when_no_computer_move_is_available(
    monkeypatch: Any,
) -> None:
    state = set_session_state(
        monkeypatch,
        fen="current-fen",
        game_start_fen="start-fen",
        move_uci_history=[],
        computer_level="beginner",
        computer_move_pending=True,
    )
    monkeypatch.setattr(
        streamlit_app,
        "is_computer_practice_turn",
        lambda: True,
    )
    monkeypatch.setattr(
        streamlit_app,
        "choose_computer_move",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        streamlit_app,
        "apply_legal_move_to_session",
        fail_if_called,
    )

    streamlit_app.apply_computer_reply_if_needed()

    assert state.computer_move_pending is False


def test_move_input_is_disabled_during_pending_computer_turn(
    monkeypatch: Any,
) -> None:
    set_session_state(
        monkeypatch,
        computer_move_pending=True,
        shared_game_id="",
        shared_game_role="white",
        fen=STARTING_FEN,
    )

    assert streamlit_app.current_move_input_is_disabled()


def test_move_input_respects_shared_game_role(
    monkeypatch: Any,
) -> None:
    state = set_session_state(
        monkeypatch,
        computer_move_pending=False,
        shared_game_id="game-role",
        shared_game_role="black",
        fen=STARTING_FEN,
        game_start_fen=STARTING_FEN,
        move_uci_history=[],
        claimed_draw_reason=None,
        shared_game_recovery_required=False,
    )

    assert streamlit_app.current_move_input_is_disabled()

    state.shared_game_role = "white"
    assert not streamlit_app.current_move_input_is_disabled()

    state.shared_game_role = "observer"
    assert streamlit_app.current_move_input_is_disabled()

    state.shared_game_id = ""
    assert not streamlit_app.current_move_input_is_disabled()


def test_move_input_is_disabled_during_shared_recovery(
    monkeypatch: Any,
) -> None:
    set_shared_game_session(
        monkeypatch,
        shared_game_recovery_required=True,
    )

    assert streamlit_app.current_move_input_is_disabled()


def test_move_input_is_disabled_after_automatic_game_termination(
    monkeypatch: Any,
) -> None:
    seventy_five_move_fen = (
        "7k/8/8/8/8/8/4K3/R7 w - - 150 76"
    )
    set_session_state(
        monkeypatch,
        computer_move_pending=False,
        shared_game_id="",
        shared_game_role="white",
        fen=seventy_five_move_fen,
        game_start_fen=seventy_five_move_fen,
        move_uci_history=[],
        claimed_draw_reason=None,
    )

    assert streamlit_app.current_game_is_over()
    assert streamlit_app.current_move_input_is_disabled()


def test_move_input_is_disabled_after_valid_claimed_threefold_draw(
    monkeypatch: Any,
) -> None:
    repetition_cycle = (
        "g1f3",
        "g8f6",
        "f3g1",
        "f6g8",
    )
    move_uci_history = repetition_cycle * 2
    board = board_from_uci_history(STARTING_FEN, move_uci_history)
    set_session_state(
        monkeypatch,
        computer_move_pending=False,
        shared_game_id="",
        shared_game_role="white",
        fen=board.fen(),
        game_start_fen=STARTING_FEN,
        move_uci_history=list(move_uci_history),
        claimed_draw_reason="threefold_repetition",
    )

    assert board.is_repetition(3)
    assert streamlit_app.current_game_is_over()
    assert streamlit_app.current_move_input_is_disabled()


def test_unavailable_shared_storage_enters_recovery_after_local_move(
    monkeypatch: Any,
) -> None:
    state = set_shared_game_session(monkeypatch)
    monkeypatch.setattr(
        streamlit_app,
        "read_shared_game_storage_config",
        lambda: (None, "Shared games are unavailable."),
    )

    streamlit_app.apply_move_text("e2e4")

    assert state.fen != STARTING_FEN
    assert state.move_uci_history == ["e2e4"]
    assert state.shared_game_last_move_number == 0
    assert state.shared_game_recovery_required is True


def test_unknown_expected_move_number_enters_recovery_after_local_move(
    monkeypatch: Any,
) -> None:
    state = set_shared_game_session(
        monkeypatch,
        shared_game_last_move_number=None,
    )
    monkeypatch.setattr(
        streamlit_app,
        "read_shared_game_storage_config",
        lambda: (object(), "Shared games are available."),
    )
    monkeypatch.setattr(
        streamlit_app,
        "save_shared_game_after_move",
        fail_if_called,
    )

    streamlit_app.apply_move_text("e2e4")

    assert state.move_uci_history == ["e2e4"]
    assert state.shared_game_recovery_required is True


@pytest.mark.parametrize(
    "save_error",
    (
        RuntimeError("storage unavailable"),
        SharedGameStorageConflictError("stored game changed"),
    ),
    ids=("generic-storage-error", "stale-state-conflict"),
)
def test_move_save_failure_enters_recovery(
    monkeypatch: Any,
    save_error: Exception,
) -> None:
    state = set_shared_game_session(monkeypatch)
    monkeypatch.setattr(
        streamlit_app,
        "read_shared_game_storage_config",
        lambda: (object(), "Shared games are available."),
    )

    def fail_save(*args: object, **kwargs: object) -> None:
        raise save_error

    monkeypatch.setattr(
        streamlit_app,
        "save_shared_game_after_move",
        fail_save,
    )

    streamlit_app.apply_move_text("e2e4")

    assert state.move_uci_history == ["e2e4"]
    assert state.shared_game_last_move_number == 0
    assert state.shared_game_recovery_required is True


def test_successful_shared_move_save_does_not_enter_recovery(
    monkeypatch: Any,
) -> None:
    state = set_shared_game_session(monkeypatch)
    monkeypatch.setattr(
        streamlit_app,
        "read_shared_game_storage_config",
        lambda: (object(), "Shared games are available."),
    )
    monkeypatch.setattr(
        streamlit_app,
        "save_shared_game_after_move",
        lambda config, shared_state, **kwargs: shared_state,
    )
    monkeypatch.setattr(
        streamlit_app.time,
        "strftime",
        lambda format_text: "12:30:00",
    )

    streamlit_app.apply_move_text("e2e4")

    assert state.move_uci_history == ["e2e4"]
    assert state.shared_game_last_move_number == 1
    assert state.shared_game_recovery_required is False
    assert state.shared_game_last_synced_at == "12:30:00"


def test_application_move_submission_rejects_shared_recovery(
    monkeypatch: Any,
) -> None:
    state = set_shared_game_session(
        monkeypatch,
        shared_game_recovery_required=True,
    )
    monkeypatch.setattr(
        streamlit_app,
        "read_shared_game_storage_config",
        fail_if_called,
    )

    with pytest.raises(ValueError, match="recovery"):
        streamlit_app.apply_move_text("e2e4")

    assert state.fen == STARTING_FEN
    assert state.move_uci_history == []


def test_shared_draw_claim_rejects_recovery_before_persistence(
    monkeypatch: Any,
) -> None:
    state = set_shared_game_session(
        monkeypatch,
        shared_game_recovery_required=True,
        **threefold_repetition_state_values(),
    )
    monkeypatch.setattr(
        streamlit_app,
        "save_shared_game_draw_claim",
        fail_if_called,
    )

    assert not streamlit_app.current_game_can_claim_threefold()
    with pytest.raises(ValueError, match="recovery"):
        streamlit_app.claim_threefold_draw()

    assert state.claimed_draw_reason is None


def test_successful_shared_draw_claim_still_applies_saved_state(
    monkeypatch: Any,
) -> None:
    state = set_shared_game_session(
        monkeypatch,
        **threefold_repetition_state_values(),
    )
    monkeypatch.setattr(
        streamlit_app,
        "read_shared_game_storage_config",
        lambda: (object(), "Shared games are available."),
    )
    monkeypatch.setattr(
        streamlit_app,
        "save_shared_game_draw_claim",
        lambda config, claimed_state, **kwargs: claimed_state,
    )

    streamlit_app.claim_threefold_draw()

    assert state.claimed_draw_reason == "threefold_repetition"
    assert state.shared_game_recovery_required is False


def test_unchanged_shared_refresh_preserves_local_move_selection(
    monkeypatch: Any,
) -> None:
    state = set_session_state(
        monkeypatch,
        shared_game_id="game-unchanged",
        shared_game_last_move_number=0,
        shared_game_recovery_required=False,
        claimed_draw_reason=None,
        selected_square="e2",
        click_move_error="keep this feedback",
        shared_game_status=None,
        shared_game_last_synced_at=None,
    )
    refreshed_state = create_shared_game_state("game-unchanged")

    monkeypatch.setattr(
        streamlit_app,
        "load_shared_game",
        lambda config, game_id: refreshed_state,
    )
    monkeypatch.setattr(
        streamlit_app,
        "apply_shared_game_state_to_session",
        fail_if_called,
    )
    monkeypatch.setattr(
        streamlit_app.time,
        "strftime",
        lambda format_text: "12:34:56",
    )

    has_update = streamlit_app.refresh_current_shared_game(object())

    assert has_update is False
    assert state.selected_square == "e2"
    assert state.click_move_error == "keep this feedback"
    assert state.shared_game_status == (
        "No new move or game result found yet."
    )
    assert state.shared_game_last_synced_at == "12:34:56"
    assert state.shared_game_recovery_required is False


def test_recovery_refresh_reapplies_unchanged_persisted_position(
    monkeypatch: Any,
) -> None:
    failed_local_fen, _san = apply_uci_move(STARTING_FEN, "e2e4")
    state = set_shared_game_session(
        monkeypatch,
        fen=failed_local_fen,
        move_uci_history=["e2e4"],
        move_history=["1. e2e4 (e4)"],
        shared_game_recovery_required=True,
    )
    persisted_state = create_shared_game_state("game-recovery")

    monkeypatch.setattr(
        streamlit_app,
        "load_shared_game",
        lambda config, game_id: persisted_state,
    )
    monkeypatch.setattr(
        streamlit_app.time,
        "strftime",
        lambda format_text: "12:40:00",
    )

    has_update = streamlit_app.refresh_current_shared_game(object())

    assert has_update is True
    assert state.fen == STARTING_FEN
    assert state.move_uci_history == []
    assert state.move_history == []
    assert state.shared_game_recovery_required is False
    assert state.shared_game_last_move_number == 0
    assert state.shared_game_last_synced_at == "12:40:00"


def test_recovery_refresh_prefers_newer_remote_position(
    monkeypatch: Any,
) -> None:
    failed_local_fen, _san = apply_uci_move(STARTING_FEN, "e2e4")
    remote_fen, _san = apply_uci_move(STARTING_FEN, "d2d4")
    remote_state = create_shared_game_state(
        "game-recovery",
        fen=remote_fen,
        game_start_fen=STARTING_FEN,
        move_uci_history=["d2d4"],
        move_history=["1. d2d4 (d4)"],
    )
    state = set_shared_game_session(
        monkeypatch,
        fen=failed_local_fen,
        move_uci_history=["e2e4"],
        move_history=["1. e2e4 (e4)"],
        shared_game_recovery_required=True,
    )
    monkeypatch.setattr(
        streamlit_app,
        "load_shared_game",
        lambda config, game_id: remote_state,
    )

    has_update = streamlit_app.refresh_current_shared_game(object())

    assert has_update is True
    assert state.fen == remote_fen
    assert state.move_uci_history == ["d2d4"]
    assert state.shared_game_last_move_number == 1
    assert state.shared_game_recovery_required is False


@pytest.mark.parametrize("refresh_result", ("error", "missing"))
def test_failed_recovery_refresh_preserves_unsynchronised_state(
    monkeypatch: Any,
    refresh_result: str,
) -> None:
    failed_local_fen, _san = apply_uci_move(STARTING_FEN, "e2e4")
    state = set_shared_game_session(
        monkeypatch,
        fen=failed_local_fen,
        move_uci_history=["e2e4"],
        move_history=["1. e2e4 (e4)"],
        shared_game_recovery_required=True,
        shared_game_last_synced_at="12:00:00",
    )

    def load_state(config: object, game_id: str) -> object | None:
        if refresh_result == "error":
            raise RuntimeError("storage unavailable")
        return None

    monkeypatch.setattr(streamlit_app, "load_shared_game", load_state)

    has_update = streamlit_app.refresh_current_shared_game(object())

    assert has_update is False
    assert state.fen == failed_local_fen
    assert state.shared_game_recovery_required is True
    assert state.shared_game_last_synced_at == "12:00:00"


def test_authoritative_state_application_clears_stale_recovery(
    monkeypatch: Any,
) -> None:
    state = set_shared_game_session(
        monkeypatch,
        shared_game_id="old-game",
        shared_game_recovery_required=True,
    )
    replacement_state = create_shared_game_state("replacement-game")

    streamlit_app.apply_shared_game_state_to_session(
        replacement_state,
        status_message="Shared game loaded.",
    )

    assert state.shared_game_id == "replacement-game"
    assert state.shared_game_recovery_required is False


def test_manual_refresh_restores_authoritative_recovery_state(
    monkeypatch: Any,
) -> None:
    failed_local_fen, _san = apply_uci_move(STARTING_FEN, "e2e4")
    state = set_shared_game_session(
        monkeypatch,
        fen=failed_local_fen,
        move_uci_history=["e2e4"],
        move_history=["1. e2e4 (e4)"],
        shared_game_recovery_required=True,
    )
    persisted_state = create_shared_game_state("game-recovery")
    reruns: list[bool] = []
    monkeypatch.setattr(
        streamlit_app,
        "read_shared_game_storage_config",
        lambda: (object(), "Shared games are available."),
    )
    monkeypatch.setattr(
        streamlit_app,
        "load_shared_game",
        lambda config, game_id: persisted_state,
    )
    monkeypatch.setattr(streamlit_app.st, "write", lambda *args, **kwargs: None)
    monkeypatch.setattr(streamlit_app.st, "markdown", lambda *args, **kwargs: None)
    monkeypatch.setattr(streamlit_app.st, "success", lambda *args, **kwargs: None)
    monkeypatch.setattr(streamlit_app.st, "info", lambda *args, **kwargs: None)
    monkeypatch.setattr(streamlit_app.st, "caption", lambda *args, **kwargs: None)
    monkeypatch.setattr(streamlit_app.st, "button", lambda *args, **kwargs: True)
    monkeypatch.setattr(streamlit_app.st, "rerun", lambda: reruns.append(True))
    monkeypatch.setattr(
        streamlit_app,
        "render_shared_game_auto_refresh",
        lambda config: None,
    )

    streamlit_app.render_shared_game_refresh_shortcut()

    assert state.fen == STARTING_FEN
    assert state.shared_game_recovery_required is False
    assert reruns == [True]


def test_polling_recovery_reports_update_and_requests_full_rerun(
    monkeypatch: Any,
) -> None:
    failed_local_fen, _san = apply_uci_move(STARTING_FEN, "e2e4")
    state = set_shared_game_session(
        monkeypatch,
        fen=failed_local_fen,
        move_uci_history=["e2e4"],
        move_history=["1. e2e4 (e4)"],
        selected_square="e2",
        shared_game_recovery_required=True,
        shared_game_auto_refresh_enabled=True,
    )
    persisted_state = create_shared_game_state("game-recovery")
    reruns: list[bool] = []
    monkeypatch.setattr(
        streamlit_app,
        "load_shared_game",
        lambda config, game_id: persisted_state,
    )
    monkeypatch.setattr(streamlit_app.st, "toggle", lambda *args, **kwargs: True)
    monkeypatch.setattr(streamlit_app.st, "caption", lambda *args, **kwargs: None)
    monkeypatch.setattr(streamlit_app.st, "rerun", lambda: reruns.append(True))

    streamlit_app.render_shared_game_auto_refresh.__wrapped__(object())

    assert state.fen == STARTING_FEN
    assert state.shared_game_recovery_required is False
    assert reruns == [True]


def test_updated_shared_refresh_applies_new_position(
    monkeypatch: Any,
) -> None:
    updated_fen, _san = apply_uci_move(STARTING_FEN, "e2e4")
    refreshed_state = create_shared_game_state(
        "game-updated",
        fen=updated_fen,
        game_start_fen=STARTING_FEN,
        move_uci_history=["e2e4"],
        move_history=["1. e2e4 (e4)"],
    )
    state = set_session_state(
        monkeypatch,
        fen=STARTING_FEN,
        game_start_fen=STARTING_FEN,
        move_uci_history=[],
        move_history=[],
        claimed_draw_reason=None,
        selected_square="e2",
        click_move_error="old feedback",
        shared_game_id="game-updated",
        shared_game_creator_side="white",
        shared_game_last_move_number=0,
        shared_game_recovery_required=False,
        shared_game_status=None,
        shared_game_last_synced_at=None,
        last_computer_move="old move",
        computer_move_pending=True,
    )

    monkeypatch.setattr(
        streamlit_app,
        "load_shared_game",
        lambda config, game_id: refreshed_state,
    )
    monkeypatch.setattr(
        streamlit_app.time,
        "strftime",
        lambda format_text: "12:35:00",
    )

    has_update = streamlit_app.refresh_current_shared_game(object())

    assert has_update is True
    assert state.fen == updated_fen
    assert state.move_uci_history == ["e2e4"]
    assert state.move_history == ["1. e2e4 (e4)"]
    assert state.shared_game_last_move_number == 1
    assert state.selected_square is None
    assert state.click_move_error is None
    assert state.shared_game_status == (
        "Updated to the latest saved game state."
    )
    assert state.shared_game_last_synced_at == "12:35:00"
    assert state.last_computer_move is None
    assert state.computer_move_pending is False


def test_remote_claimed_draw_refresh_still_applies_saved_result(
    monkeypatch: Any,
) -> None:
    repetition_values = threefold_repetition_state_values()
    claimed_state = create_shared_game_state(
        "game-recovery",
        fen=str(repetition_values["fen"]),
        game_start_fen=STARTING_FEN,
        move_uci_history=repetition_values["move_uci_history"],
        move_history=repetition_values["move_history"],
        claimed_draw_reason="threefold_repetition",
    )
    state = set_shared_game_session(
        monkeypatch,
        **repetition_values,
    )
    monkeypatch.setattr(
        streamlit_app,
        "load_shared_game",
        lambda config, game_id: claimed_state,
    )

    has_update = streamlit_app.refresh_current_shared_game(object())

    assert has_update is True
    assert state.claimed_draw_reason == "threefold_repetition"
    assert state.shared_game_recovery_required is False
