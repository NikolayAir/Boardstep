"""Deterministic JSON export for validated Boardstep game records."""

import json
from typing import TypedDict

from boardstep.game import ClaimedDrawReason
from boardstep.game_record import (
    GameRecord,
    GameResult,
    GameTerminationReason,
)


class GameRecordJson(TypedDict):
    """JSON-compatible representation of a validated game record."""

    schema_version: int
    start_fen: str
    move_uci_history: list[str]
    move_san_history: list[str]
    final_fen: str
    result: GameResult
    termination_reason: GameTerminationReason | None
    claimed_draw_reason: ClaimedDrawReason | None


def game_record_to_json_data(
    record: GameRecord,
) -> GameRecordJson:
    """Return a JSON-compatible representation of a game record."""
    return {
        "schema_version": record.schema_version,
        "start_fen": record.start_fen,
        "move_uci_history": list(record.move_uci_history),
        "move_san_history": list(record.move_san_history),
        "final_fen": record.final_fen,
        "result": record.result,
        "termination_reason": record.termination_reason,
        "claimed_draw_reason": record.claimed_draw_reason,
    }


def game_record_to_json(record: GameRecord) -> str:
    """Return deterministic, formatted JSON text for a game record."""
    return (
        json.dumps(
            game_record_to_json_data(record),
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )
