"""Concise summaries for validated Boardstep game records."""

from dataclasses import dataclass
from typing import Literal

from boardstep.game import STARTING_FEN
from boardstep.game_record import GameRecord

GameSummaryOutcome = Literal[
    "ongoing",
    "white_win",
    "black_win",
    "draw",
]

GameStartPosition = Literal[
    "standard",
    "custom",
]


_DRAW_STATUS_TEXT = {
    "stalemate": "Draw by stalemate.",
    "insufficient_material": "Draw by insufficient material.",
    "seventy_five_move_rule": (
        "Draw by the seventy-five-move rule."
    ),
    "fivefold_repetition": "Draw by fivefold repetition.",
    "threefold_repetition": (
        "Draw claimed by threefold repetition."
    ),
}


@dataclass(frozen=True)
class GameRecordSummary:
    """Immutable summary derived from a validated game record."""

    outcome: GameSummaryOutcome
    move_count: int
    latest_san_move: str | None
    start_position: GameStartPosition
    text: str


def create_game_record_summary(
    record: GameRecord,
) -> GameRecordSummary:
    """Create deterministic summary data and text for a game record."""
    outcome = _derive_outcome(record)
    move_count = len(record.move_uci_history)
    latest_san_move = (
        record.move_san_history[-1]
        if record.move_san_history
        else None
    )
    start_position: GameStartPosition = (
        "standard"
        if record.start_fen == STARTING_FEN
        else "custom"
    )

    text = _build_summary_text(
        record=record,
        outcome=outcome,
        move_count=move_count,
        latest_san_move=latest_san_move,
        start_position=start_position,
    )

    return GameRecordSummary(
        outcome=outcome,
        move_count=move_count,
        latest_san_move=latest_san_move,
        start_position=start_position,
        text=text,
    )


def _derive_outcome(record: GameRecord) -> GameSummaryOutcome:
    """Map a validated game result to a summary outcome."""
    if record.result == "*":
        return "ongoing"

    if record.result == "1-0":
        return "white_win"

    if record.result == "0-1":
        return "black_win"

    return "draw"


def _build_summary_text(
    *,
    record: GameRecord,
    outcome: GameSummaryOutcome,
    move_count: int,
    latest_san_move: str | None,
    start_position: GameStartPosition,
) -> str:
    """Build concise human-readable summary text."""
    parts = [
        _status_text(record, outcome),
        _move_count_text(move_count),
    ]

    if latest_san_move is not None:
        parts.append(f"Latest move: {latest_san_move}.")

    if start_position == "standard":
        parts.append("Standard starting position.")
    else:
        parts.append("Custom starting position.")

    return " ".join(parts)


def _status_text(
    record: GameRecord,
    outcome: GameSummaryOutcome,
) -> str:
    """Return the user-facing status portion of a summary."""
    if outcome == "ongoing":
        return "Game in progress."

    if outcome == "white_win":
        if record.termination_reason == "checkmate":
            return "White won by checkmate."

        return "White won."

    if outcome == "black_win":
        if record.termination_reason == "checkmate":
            return "Black won by checkmate."

        return "Black won."

    return _DRAW_STATUS_TEXT.get(
        record.termination_reason,
        "Draw.",
    )


def _move_count_text(move_count: int) -> str:
    """Format the number of individual recorded moves."""
    noun = "move" if move_count == 1 else "moves"
    return f"{move_count} {noun}."
