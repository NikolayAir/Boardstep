"""Helpers for planned shared turn-based game state.

This module does not add storage, networking, or Streamlit UI behavior.
It only defines a small pure-Python representation that can be tested
before a future shared-game storage layer is added.
"""

from __future__ import annotations

import secrets

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Sequence

from boardstep.game import STARTING_FEN, validate_fen_position


SHARED_GAME_ID_ALPHABET = "abcdefghijkmnopqrstuvwxyz23456789"
DEFAULT_SHARED_GAME_ID_LENGTH = 10


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
