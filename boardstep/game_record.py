"""Validated, storage-independent game records for Boardstep."""

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Literal, cast

import chess

from boardstep.game import (
    STARTING_FEN,
    ClaimedDrawReason,
    board_from_uci_history,
    threefold_draw_can_be_claimed,
    validate_fen_position,
)

GAME_RECORD_SCHEMA_VERSION = 1

GameResult = Literal[
    "1-0",
    "0-1",
    "1/2-1/2",
    "*",
]

GameTerminationReason = Literal[
    "checkmate",
    "stalemate",
    "insufficient_material",
    "seventy_five_move_rule",
    "fivefold_repetition",
    "threefold_repetition",
]


_AUTOMATIC_TERMINATION_REASONS: dict[
    chess.Termination,
    GameTerminationReason,
] = {
    chess.Termination.CHECKMATE: "checkmate",
    chess.Termination.STALEMATE: "stalemate",
    chess.Termination.INSUFFICIENT_MATERIAL: "insufficient_material",
    chess.Termination.SEVENTYFIVE_MOVES: "seventy_five_move_rule",
    chess.Termination.FIVEFOLD_REPETITION: "fivefold_repetition",
}

_VALID_RESULTS = {
    "1-0",
    "0-1",
    "1/2-1/2",
    "*",
}


@dataclass(frozen=True)
class GameRecord:
    """Validated record derived from canonical FEN and UCI move history."""

    start_fen: str
    move_uci_history: tuple[str, ...]
    move_san_history: tuple[str, ...]
    final_fen: str
    result: GameResult
    termination_reason: GameTerminationReason | None
    claimed_draw_reason: ClaimedDrawReason | None
    schema_version: int = field(
        default=GAME_RECORD_SCHEMA_VERSION,
        init=False,
    )


def create_game_record(
    *,
    start_fen: str = STARTING_FEN,
    move_uci_history: Sequence[str] = (),
    claimed_draw_reason: str | None = None,
) -> GameRecord:
    """Build a validated record from canonical game-history inputs."""
    validated_start_fen = validate_fen_position(start_fen)
    normalized_uci_history = tuple(
        move.strip().lower()
        for move in move_uci_history
    )

    reconstructed_board = board_from_uci_history(
        validated_start_fen,
        normalized_uci_history,
    )
    normalized_claimed_draw_reason = _normalize_claimed_draw_reason(
        claimed_draw_reason
    )
    move_san_history = _derive_san_history(
        validated_start_fen,
        reconstructed_board,
    )
    result, termination_reason = _derive_result(
        reconstructed_board,
        normalized_claimed_draw_reason,
    )

    return GameRecord(
        start_fen=validated_start_fen,
        move_uci_history=normalized_uci_history,
        move_san_history=move_san_history,
        final_fen=reconstructed_board.fen(),
        result=result,
        termination_reason=termination_reason,
        claimed_draw_reason=normalized_claimed_draw_reason,
    )


def _normalize_claimed_draw_reason(
    claimed_draw_reason: str | None,
) -> ClaimedDrawReason | None:
    """Normalize and validate an optional supported draw claim."""
    if claimed_draw_reason is None:
        return None

    normalized_reason = claimed_draw_reason.strip().lower()

    if normalized_reason != "threefold_repetition":
        raise ValueError(
            "Claimed draw reason must be threefold_repetition."
        )

    return cast(ClaimedDrawReason, normalized_reason)


def _derive_san_history(
    start_fen: str,
    reconstructed_board: chess.Board,
) -> tuple[str, ...]:
    """Derive SAN notation from the validated canonical move stack."""
    replay_board = chess.Board(start_fen)
    san_history: list[str] = []

    for move in reconstructed_board.move_stack:
        san_history.append(replay_board.san(move))
        replay_board.push(move)

    return tuple(san_history)


def _derive_result(
    board: chess.Board,
    claimed_draw_reason: ClaimedDrawReason | None,
) -> tuple[GameResult, GameTerminationReason | None]:
    """Derive the formal result and normalized termination reason."""
    if claimed_draw_reason == "threefold_repetition":
        if not threefold_draw_can_be_claimed(board):
            raise ValueError(
                "Threefold repetition cannot be claimed "
                "for this game history."
            )

        return "1/2-1/2", "threefold_repetition"

    outcome = board.outcome(claim_draw=False)

    if outcome is None:
        return "*", None

    termination_reason = _AUTOMATIC_TERMINATION_REASONS.get(
        outcome.termination
    )

    if termination_reason is None:
        raise ValueError(
            "The reconstructed game has an unsupported "
            "termination reason."
        )

    result_text = board.result(claim_draw=False)

    if result_text not in _VALID_RESULTS:
        raise ValueError(
            "The reconstructed game has an unsupported result."
        )

    return cast(GameResult, result_text), termination_reason
