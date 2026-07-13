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
SHARED_GAME_SIDES = ("white", "black")
SHARED_GAME_ROLES = ("white", "black", "observer")
CREATOR_SIDE_OPTIONS = ("white", "black", "random")
SharedGameSide = Literal["white", "black"]
SharedGameRole = Literal["white", "black", "observer"]


def normalize_shared_game_side(side: str) -> SharedGameSide:
    """Normalize and validate a playable shared-game side."""
    normalized_side = side.strip().lower()

    if normalized_side not in SHARED_GAME_SIDES:
        raise ValueError("Shared game side must be white or black.")

    return cast(SharedGameSide, normalized_side)


def resolve_creator_side(selection: str) -> SharedGameSide:
    """Resolve White, Black, or Random to one stored creator side."""
    normalized_selection = selection.strip().lower()

    if normalized_selection not in CREATOR_SIDE_OPTIONS:
        raise ValueError("Creator side must be white, black, or random.")

    if normalized_selection == "random":
        return cast(SharedGameSide, secrets.choice(SHARED_GAME_SIDES))

    return cast(SharedGameSide, normalized_selection)


def opposite_shared_game_side(side: str) -> SharedGameSide:
    """Return the playable side opposite the supplied shared-game side."""
    normalized_side = normalize_shared_game_side(side)
    return "black" if normalized_side == "white" else "white"


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
    creator_side: SharedGameSide
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
    creator_side: str = "white",
    created_at: datetime | None = None,
    updated_at: datetime | None = None,
) -> SharedGameState:
    """Create a validated shared game state object."""

    normalized_game_id = game_id.strip()
    if not normalized_game_id:
        raise ValueError("game_id must not be empty")

    validated_fen = validate_fen_position(fen)
    normalized_creator_side = normalize_shared_game_side(creator_side)

    timestamp = datetime.now(timezone.utc)
    created = created_at or timestamp
    updated = updated_at or created

    return SharedGameState(
        game_id=normalized_game_id,
        fen=validated_fen,
        move_history=tuple(move_history or ()),
        creator_side=normalized_creator_side,
        created_at=created,
        updated_at=updated,
    )
