from datetime import datetime, timezone

import pytest

from boardstep.shared_game import create_shared_game_state
from boardstep.supabase_rest_storage import (
    SUPABASE_KEY_SECRET,
    SUPABASE_URL_SECRET,
    SharedGameStorageConflictError,
    SupabaseRestConfig,
    create_shared_game,
    create_supabase_rest_config,
    load_shared_game,
    save_shared_game_after_move,
)


class FakeResponse:
    def __init__(self, payload, status_code: int = 200) -> None:
        self.payload = payload
        self.status_code = status_code

    def json(self):
        return self.payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeSession:
    def __init__(self, response: FakeResponse) -> None:
        self.response = response
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append(("post", url, kwargs))
        return self.response

    def get(self, url, **kwargs):
        self.calls.append(("get", url, kwargs))
        return self.response

    def patch(self, url, **kwargs):
        self.calls.append(("patch", url, kwargs))
        return self.response


def test_create_supabase_rest_config_strips_values() -> None:
    config = create_supabase_rest_config(
        "  https://example.supabase.co/  ",
        "  test-key  ",
    )

    assert config == SupabaseRestConfig(
        url="https://example.supabase.co",
        key="test-key",
    )


def test_create_supabase_rest_config_rejects_missing_url() -> None:
    with pytest.raises(ValueError, match=SUPABASE_URL_SECRET):
        create_supabase_rest_config("", "test-key")


def test_create_supabase_rest_config_rejects_missing_key() -> None:
    with pytest.raises(ValueError, match=SUPABASE_KEY_SECRET):
        create_supabase_rest_config("https://example.supabase.co", "  ")


def test_create_supabase_rest_config_rejects_non_url_value() -> None:
    with pytest.raises(ValueError, match=SUPABASE_URL_SECRET):
        create_supabase_rest_config("example.supabase.co", "test-key")


def test_create_shared_game_posts_record() -> None:
    created_at = datetime(2026, 6, 22, 12, 0, tzinfo=timezone.utc)
    state = create_shared_game_state(
        "game-001",
        created_at=created_at,
        updated_at=created_at,
    )
    response_record = {
        "game_id": "game-001",
        "fen": state.fen,
        "move_history": [],
        "created_at": "2026-06-22T12:00:00Z",
        "updated_at": "2026-06-22T12:00:00Z",
        "last_move_number": 0,
    }
    session = FakeSession(FakeResponse([response_record]))

    saved_state = create_shared_game(
        _config(),
        state,
        session=session,
    )

    assert saved_state.game_id == "game-001"
    assert len(session.calls) == 1

    method, url, kwargs = session.calls[0]
    assert method == "post"
    assert url == "https://example.supabase.co/rest/v1/shared_games"
    assert kwargs["headers"]["Prefer"] == "return=representation"
    assert kwargs["json"]["game_id"] == "game-001"
    assert kwargs["json"]["last_move_number"] == 0


def test_load_shared_game_returns_state() -> None:
    response_record = {
        "game_id": "game-002",
        "fen": create_shared_game_state("game-002").fen,
        "move_history": ["e2e4"],
        "created_at": "2026-06-22T12:00:00Z",
        "updated_at": "2026-06-22T12:01:00Z",
        "last_move_number": 1,
    }
    session = FakeSession(FakeResponse([response_record]))

    state = load_shared_game(
        _config(),
        "game-002",
        session=session,
    )

    assert state is not None
    assert state.game_id == "game-002"
    assert state.move_history == ("e2e4",)

    method, _, kwargs = session.calls[0]
    assert method == "get"
    assert kwargs["params"] == {
        "game_id": "eq.game-002",
        "limit": "1",
    }


def test_load_shared_game_returns_none_when_missing() -> None:
    session = FakeSession(FakeResponse([]))

    state = load_shared_game(
        _config(),
        "missing-game",
        session=session,
    )

    assert state is None


def test_save_shared_game_after_move_patches_with_stale_state_guard() -> None:
    updated_at = datetime(2026, 6, 22, 12, 1, tzinfo=timezone.utc)
    state = create_shared_game_state(
        "game-003",
        move_history=["e2e4"],
        created_at=datetime(2026, 6, 22, 12, 0, tzinfo=timezone.utc),
        updated_at=updated_at,
    )
    response_record = {
        "game_id": "game-003",
        "fen": state.fen,
        "move_history": ["e2e4"],
        "created_at": "2026-06-22T12:00:00Z",
        "updated_at": "2026-06-22T12:01:00Z",
        "last_move_number": 1,
    }
    session = FakeSession(FakeResponse([response_record]))

    saved_state = save_shared_game_after_move(
        _config(),
        state,
        expected_last_move_number=0,
        session=session,
    )

    assert saved_state.last_move_number == 1

    method, _, kwargs = session.calls[0]
    assert method == "patch"
    assert kwargs["params"] == {
        "game_id": "eq.game-003",
        "last_move_number": "eq.0",
    }


def test_save_shared_game_after_move_raises_when_record_changed() -> None:
    state = create_shared_game_state("game-004")
    session = FakeSession(FakeResponse([]))

    with pytest.raises(SharedGameStorageConflictError, match="changed"):
        save_shared_game_after_move(
            _config(),
            state,
            expected_last_move_number=0,
            session=session,
        )


def test_save_shared_game_after_move_rejects_negative_expected_move_number() -> None:
    state = create_shared_game_state("game-005")

    with pytest.raises(ValueError, match="must not be negative"):
        save_shared_game_after_move(
            _config(),
            state,
            expected_last_move_number=-1,
            session=FakeSession(FakeResponse([])),
        )


def _config() -> SupabaseRestConfig:
    return create_supabase_rest_config(
        "https://example.supabase.co",
        "test-key",
    )
