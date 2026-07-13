"""Helpers for planned shared turn-based game state.

This module does not add storage, networking, or Streamlit UI behavior.
It only defines a small pure-Python representation that can be tested
before a future shared-game storage layer is added.
"""

from __future__ import annotations

import secrets

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal, Sequence, cast

from boardstep.game import STARTING_FEN, side_to_move, validate_fen_position


SHARED_GAME_ID_ALPHABET = "abcdefghijkmnopqrstuvwxyz23456789"
DEFAULT_SHARED_GAME_ID_LENGTH = 10
DEFAULT_SHARED_GAME_ROLE = "observer"
SHARED_GAME_ROLES = ("white", "black", "observer")
SharedGameRole = Literal["white", "black", "observer"]


def normalize_shared_game_role(role: str) -> SharedGameRole:
    """Normalize and validate a browser-local shared-game role."""
    normalized_role = role.strip().lower()

    if normalized_role not in SHARED_GAME_ROLES:
        raise ValueError("Shared game role must be white, black, or observer.")

    return cast(SharedGameRole, normalized_role)


def shared_game_role_can_move(role: str, fen: str) -> bool:
    """Return whether the browser-local shared-game role can move now."""
    normalized_role = normalize_shared_game_role(role)

    if normalized_role == "observer":
        return False

    return normalized_role == side_to_move(fen).lower()


def shared_game_move_restriction_message(role: str, fen: str) -> str | None:
    """Return a move restriction message for the role, or None if moving is allowed."""
    normalized_role = normalize_shared_game_role(role)

    if normalized_role == "observer":
        return "Observer mode does not allow moves."

    current_side = side_to_move(fen)

    if normalized_role != current_side.lower():
        selected_side = "White" if normalized_role == "white" else "Black"
        return f"You selected {selected_side} for this session. It is {current_side} to move."

    return None


def shared_game_turn_guidance(role: str, fen: str) -> str:
    """Return browser-local turn guidance for a shared game."""
    normalized_role = normalize_shared_game_role(role)

    if normalized_role == "observer":
        return "Observer mode."

    current_side = side_to_move(fen)

    if normalized_role == current_side.lower():
        return "Your move."

    return f"Waiting for {current_side}."



@dataclass(frozen=True)
class SharedGameState:
    """Minimal state needed to represent a planned shared chess game."""

    game_id: str
    fen: str
    move_history: tuple[str, ...]
    created_at: datetime
    updated_at: datetime

    @property
    def last_move_number(self) -> int:
        """Return the number of moves stored for the shared game."""

        return len(self.move_history)


def generate_shared_game_id(length: int = DEFAULT_SHARED_GAME_ID_LENGTH) -> str:
    """Generate a compact random ID for a shared game."""

    if length <= 0:
        raise ValueError("length must be positive")

    return "".join(
        secrets.choice(SHARED_GAME_ID_ALPHABET)
        for _ in range(length)
    )


def create_shared_game_state(
    game_id: str,
    fen: str = STARTING_FEN,
    move_history: Sequence[str] | None = None,
    created_at: datetime | None = None,
    updated_at: datetime | None = None,
) -> SharedGameState:
    """Create a validated shared game state object."""

    normalized_game_id = game_id.strip()
    if not normalized_game_id:
        raise ValueError("game_id must not be empty")

    validated_fen = validate_fen_position(fen)

    timestamp = datetime.now(timezone.utc)
    created = created_at or timestamp
    updated = updated_at or created

    return SharedGameState(
        game_id=normalized_game_id,
        fen=validated_fen,
        move_history=tuple(move_history or ()),
        created_at=created,
        updated_at=updated,
    )
