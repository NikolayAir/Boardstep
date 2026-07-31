"""Deterministic PGN export for validated Boardstep game records."""

import chess
import chess.pgn

from boardstep.game import STARTING_FEN
from boardstep.game_record import GameRecord


def game_record_to_pgn(record: GameRecord) -> str:
    """Return deterministic PGN text for a validated game record."""
    game = chess.pgn.Game()
    game.headers.clear()

    if record.start_fen != STARTING_FEN:
        game.setup(record.start_fen)

    game.headers["Result"] = record.result

    node: chess.pgn.GameNode = game

    for move_text in record.move_uci_history:
        move = chess.Move.from_uci(move_text)
        node = node.add_variation(move)

    exporter = chess.pgn.StringExporter(
        headers=True,
        comments=False,
        variations=False,
        columns=None,
    )

    return game.accept(exporter) + "\n"
