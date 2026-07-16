"""Storage-facing helpers for shared game records.

This module prepares shared game state for a future external storage layer.
It does not open network connections, read credentials, or depend on Streamlit.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from typing import Any

from boardstep.shared_game import SharedGameState, create_shared_game_state

SHARED_GAMES_TABLE = "shared_games"

REQUIRED_RECORD_FIELDS = (
    "game_id",
    "fen",
    "move_history",
    "created_at",
    "updated_at",
    "last_move_number",
)


def shared_game_state_to_record(state: SharedGameState) -> dict[str, Any]:
    """Convert shared game state to a database-shaped record."""

    return {
        "game_id": state.game_id,
        "fen": state.fen,
        "game_start_fen": state.game_start_fen,
        "move_uci_history": list(state.move_uci_history),
        "move_history": list(state.move_history),
        "claimed_draw_reason": state.claimed_draw_reason,
        "creator_side": state.creator_side,
        "created_at": _format_timestamp(state.created_at),
        "updated_at": _format_timestamp(state.updated_at),
        "last_move_number": state.last_move_number,
    }


def shared_game_state_from_record(record: Mapping[str, Any]) -> SharedGameState:
    """Create shared game state from a database-shaped record."""

    _validate_required_fields(record)

    game_id = _required_text(record, "game_id")
    fen = _required_text(record, "fen")
    move_history = _move_history_from_record(record["move_history"])
    game_start_fen = _optional_text(record, "game_start_fen")

    if game_start_fen is None:
        move_uci_history = None
    elif "move_uci_history" not in record:
        raise ValueError(
            "shared game record is missing: move_uci_history"
        )
    else:
        move_uci_history = _move_history_from_record(
            record["move_uci_history"]
        )

    claimed_draw_reason = _optional_text(
        record,
        "claimed_draw_reason",
    )
    creator_side = _text_with_default(
        record,
        "creator_side",
        default="white",
    )
    created_at = _parse_timestamp(record["created_at"], field_name="created_at")
    updated_at = _parse_timestamp(record["updated_at"], field_name="updated_at")

    state = create_shared_game_state(
        game_id=game_id,
        fen=fen,
        move_history=move_history,
        game_start_fen=game_start_fen,
        move_uci_history=move_uci_history,
        claimed_draw_reason=claimed_draw_reason,
        creator_side=creator_side,
        created_at=created_at,
        updated_at=updated_at,
    )

    expected_last_move_number = _record_last_move_number(record)
    if expected_last_move_number != state.last_move_number:
        raise ValueError("last_move_number does not match move_history")

    return state


def record_has_expected_last_move_number(
    record: Mapping[str, Any],
    expected_last_move_number: int,
) -> bool:
    """Return whether a stored record still has the expected move number."""

    if expected_last_move_number < 0:
        raise ValueError("expected_last_move_number must not be negative")

    return _record_last_move_number(record) == expected_last_move_number


def _validate_required_fields(record: Mapping[str, Any]) -> None:
    missing_fields = [
        field_name
        for field_name in REQUIRED_RECORD_FIELDS
        if field_name not in record
    ]

    if missing_fields:
        missing_text = ", ".join(missing_fields)
        raise ValueError(f"shared game record is missing: {missing_text}")


def _required_text(record: Mapping[str, Any], field_name: str) -> str:
    value = record[field_name]

    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")

    return value.strip()


def _optional_text(
    record: Mapping[str, Any],
    field_name: str,
) -> str | None:
    value = record.get(field_name)

    if value is None:
        return None

    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")

    return value.strip()


def _text_with_default(
    record: Mapping[str, Any],
    field_name: str,
    *,
    default: str,
) -> str:
    if field_name not in record:
        return default

    return _required_text(record, field_name)


def _move_history_from_record(value: Any) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise ValueError("move_history must be a sequence of strings")

    moves = tuple(str(move) for move in value)

    if any(not move.strip() for move in moves):
        raise ValueError("move_history must not contain empty moves")

    return moves


def _record_last_move_number(record: Mapping[str, Any]) -> int:
    try:
        last_move_number = int(record["last_move_number"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("last_move_number must be an integer") from exc

    if last_move_number < 0:
        raise ValueError("last_move_number must not be negative")

    return last_move_number


def _format_timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc).isoformat()


def _parse_timestamp(value: Any, *, field_name: str) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and value.strip():
        normalized = value.strip().replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError as exc:
            raise ValueError(f"{field_name} must be an ISO timestamp") from exc
    else:
        raise ValueError(f"{field_name} must be an ISO timestamp")

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(timezone.utc)
