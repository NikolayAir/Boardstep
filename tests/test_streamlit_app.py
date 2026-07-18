from types import SimpleNamespace
from typing import Any

from app import streamlit_app


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
