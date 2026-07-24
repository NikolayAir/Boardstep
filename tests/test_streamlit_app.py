from types import SimpleNamespace
from typing import Any

from app import streamlit_app
from boardstep.game import STARTING_FEN, apply_uci_move
from boardstep.shared_game import create_shared_game_state


def set_session_state(monkeypatch: Any, **values: object) -> SimpleNamespace:
    state = SimpleNamespace(**values)
    monkeypatch.setattr(streamlit_app.st, "session_state", state)
    return state


def fail_if_called(*args: object, **kwargs: object) -> None:
    raise AssertionError("This function should not have been called.")


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
    )

    assert streamlit_app.current_move_input_is_disabled()

    state.shared_game_role = "white"
    assert not streamlit_app.current_move_input_is_disabled()

    state.shared_game_role = "observer"
    assert streamlit_app.current_move_input_is_disabled()

    state.shared_game_id = ""
    assert not streamlit_app.current_move_input_is_disabled()


def test_unchanged_shared_refresh_preserves_local_move_selection(
    monkeypatch: Any,
) -> None:
    state = set_session_state(
        monkeypatch,
        shared_game_id="game-unchanged",
        shared_game_last_move_number=0,
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
