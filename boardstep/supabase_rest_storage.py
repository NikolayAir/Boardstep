"""Supabase REST helpers for shared game storage.

This module uses Supabase's generated REST API instead of the full Supabase
Python client. It does not read Streamlit secrets directly and does not perform
network calls at import time.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from boardstep.shared_game import SharedGameState
from boardstep.shared_game_storage import (
    SHARED_GAMES_TABLE,
    shared_game_state_from_record,
    shared_game_state_to_record,
)

SUPABASE_URL_SECRET = "SUPABASE_URL"
SUPABASE_KEY_SECRET = "SUPABASE_KEY"


@dataclass(frozen=True)
class SupabaseRestConfig:
    """Validated Supabase REST API configuration."""

    url: str
    key: str
    table: str = SHARED_GAMES_TABLE
    timeout_seconds: float = 10.0


class SharedGameStorageConflictError(RuntimeError):
    """Raised when a stored game changed before an update was saved."""


def create_supabase_rest_config(
    url: str | None,
    key: str | None,
    *,
    table: str = SHARED_GAMES_TABLE,
    timeout_seconds: float = 10.0,
) -> SupabaseRestConfig:
    """Create validated Supabase REST configuration from secret values."""

    normalized_url = _required_secret(url, SUPABASE_URL_SECRET).rstrip("/")
    normalized_key = _required_secret(key, SUPABASE_KEY_SECRET)

    if not normalized_url.startswith(("https://", "http://")):
        raise ValueError(f"{SUPABASE_URL_SECRET} must be a URL")

    if not table.strip():
        raise ValueError("table must not be empty")

    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")

    return SupabaseRestConfig(
        url=normalized_url,
        key=normalized_key,
        table=table.strip(),
        timeout_seconds=timeout_seconds,
    )


def create_shared_game(
    config: SupabaseRestConfig,
    state: SharedGameState,
    *,
    session: Any | None = None,
) -> SharedGameState:
    """Create a shared game record through the Supabase REST API."""

    response = _request_session(session).post(
        _table_url(config),
        headers=_headers(config, prefer="return=representation"),
        json=shared_game_state_to_record(state),
        timeout=config.timeout_seconds,
    )
    _raise_for_status(response)

    records = _response_records(response)
    return shared_game_state_from_record(records[0]) if records else state


def load_shared_game(
    config: SupabaseRestConfig,
    game_id: str,
    *,
    session: Any | None = None,
) -> SharedGameState | None:
    """Load a shared game by game ID through the Supabase REST API."""

    normalized_game_id = game_id.strip()
    if not normalized_game_id:
        raise ValueError("game_id must not be empty")

    response = _request_session(session).get(
        _table_url(config),
        headers=_headers(config),
        params={
            "game_id": f"eq.{normalized_game_id}",
            "limit": "1",
        },
        timeout=config.timeout_seconds,
    )
    _raise_for_status(response)

    records = _response_records(response)
    if not records:
        return None

    return shared_game_state_from_record(records[0])


def save_shared_game_after_move(
    config: SupabaseRestConfig,
    state: SharedGameState,
    *,
    expected_last_move_number: int,
    session: Any | None = None,
) -> SharedGameState:
    """Save a move if the stored game is unchanged and has no claimed draw."""

    return _save_shared_game_state_if_unclaimed(
        config,
        state,
        expected_last_move_number=expected_last_move_number,
        session=session,
    )


def save_shared_game_draw_claim(
    config: SupabaseRestConfig,
    state: SharedGameState,
    *,
    expected_last_move_number: int,
    session: Any | None = None,
) -> SharedGameState:
    """Save a threefold draw claim if the stored game is still unclaimed."""

    if state.claimed_draw_reason != "threefold_repetition":
        raise ValueError(
            "state must contain a threefold-repetition draw claim"
        )

    return _save_shared_game_state_if_unclaimed(
        config,
        state,
        expected_last_move_number=expected_last_move_number,
        session=session,
    )


def _save_shared_game_state_if_unclaimed(
    config: SupabaseRestConfig,
    state: SharedGameState,
    *,
    expected_last_move_number: int,
    session: Any | None,
) -> SharedGameState:
    """Patch a shared game guarded by its move number and unclaimed state."""

    if expected_last_move_number < 0:
        raise ValueError("expected_last_move_number must not be negative")

    response = _request_session(session).patch(
        _table_url(config),
        headers=_headers(config, prefer="return=representation"),
        params={
            "game_id": f"eq.{state.game_id}",
            "last_move_number": f"eq.{expected_last_move_number}",
            "claimed_draw_reason": "is.null",
        },
        json=shared_game_state_to_record(state),
        timeout=config.timeout_seconds,
    )
    _raise_for_status(response)

    records = _response_records(response)
    if not records:
        raise SharedGameStorageConflictError(
            "shared game was changed before the update was saved"
        )

    return shared_game_state_from_record(records[0])


def _headers(
    config: SupabaseRestConfig,
    *,
    prefer: str | None = None,
) -> dict[str, str]:
    headers = {
        "apikey": config.key,
        "Authorization": f"Bearer {config.key}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    if prefer:
        headers["Prefer"] = prefer

    return headers


def _table_url(config: SupabaseRestConfig) -> str:
    return f"{config.url}/rest/v1/{config.table}"


def _response_records(response: Any) -> list[dict[str, Any]]:
    payload = response.json()

    if not isinstance(payload, list):
        raise ValueError("Supabase response must be a list of records")

    return payload


def _raise_for_status(response: Any) -> None:
    response.raise_for_status()


def _request_session(session: Any | None) -> Any:
    if session is not None:
        return session

    import requests

    return requests


def _required_secret(value: str | None, name: str) -> str:
    if value is None or not value.strip():
        raise ValueError(f"{name} is required")

    return value.strip()
