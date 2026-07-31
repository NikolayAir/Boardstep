from dataclasses import FrozenInstanceError

import pytest

from boardstep.game_record import create_game_record
from boardstep.game_record_summary import (
    GameRecordSummary,
    create_game_record_summary,
)


def test_summary_describes_empty_ongoing_game() -> None:
    summary = create_game_record_summary(
        create_game_record()
    )

    assert summary == GameRecordSummary(
        outcome="ongoing",
        move_count=0,
        latest_san_move=None,
        start_position="standard",
        text=(
            "Game in progress. 0 moves. "
            "Standard starting position."
        ),
    )


def test_summary_includes_latest_move_for_ongoing_game() -> None:
    record = create_game_record(
        move_uci_history=("e2e4",),
    )

    summary = create_game_record_summary(record)

    assert summary.outcome == "ongoing"
    assert summary.move_count == 1
    assert summary.latest_san_move == "e4"
    assert summary.start_position == "standard"
    assert summary.text == (
        "Game in progress. 1 move. "
        "Latest move: e4. Standard starting position."
    )


def test_summary_identifies_white_checkmate_win() -> None:
    record = create_game_record(
        move_uci_history=(
            "e2e4",
            "e7e5",
            "d1h5",
            "b8c6",
            "f1c4",
            "g8f6",
            "h5f7",
        ),
    )

    summary = create_game_record_summary(record)

    assert summary.outcome == "white_win"
    assert summary.move_count == 7
    assert summary.latest_san_move == "Qxf7#"
    assert summary.text == (
        "White won by checkmate. 7 moves. "
        "Latest move: Qxf7#. Standard starting position."
    )


def test_summary_identifies_black_checkmate_win() -> None:
    record = create_game_record(
        move_uci_history=(
            "f2f3",
            "e7e5",
            "g2g4",
            "d8h4",
        ),
    )

    summary = create_game_record_summary(record)

    assert summary.outcome == "black_win"
    assert summary.move_count == 4
    assert summary.latest_san_move == "Qh4#"
    assert summary.text == (
        "Black won by checkmate. 4 moves. "
        "Latest move: Qh4#. Standard starting position."
    )


def test_summary_identifies_stalemate_draw() -> None:
    record = create_game_record(
        start_fen="7k/5Q2/6K1/8/8/8/8/8 b - - 0 1",
    )

    summary = create_game_record_summary(record)

    assert summary.outcome == "draw"
    assert summary.move_count == 0
    assert summary.latest_san_move is None
    assert summary.start_position == "custom"
    assert summary.text == (
        "Draw by stalemate. 0 moves. "
        "Custom starting position."
    )


def test_summary_identifies_insufficient_material_draw() -> None:
    record = create_game_record(
        start_fen="8/8/8/8/8/8/4K3/7k w - - 0 1",
    )

    summary = create_game_record_summary(record)

    assert summary.outcome == "draw"
    assert summary.text == (
        "Draw by insufficient material. 0 moves. "
        "Custom starting position."
    )


def test_summary_identifies_seventy_five_move_draw() -> None:
    record = create_game_record(
        start_fen=(
            "rnbqkbnr/pppppppp/8/8/8/8/"
            "PPPPPPPP/RNBQKBNR w KQkq - 150 76"
        ),
    )

    summary = create_game_record_summary(record)

    assert summary.outcome == "draw"
    assert summary.text == (
        "Draw by the seventy-five-move rule. 0 moves. "
        "Custom starting position."
    )


def test_summary_identifies_fivefold_repetition_draw() -> None:
    repetition_cycle = (
        "g1f3",
        "g8f6",
        "f3g1",
        "f6g8",
    )
    record = create_game_record(
        move_uci_history=repetition_cycle * 4,
    )

    summary = create_game_record_summary(record)

    assert summary.outcome == "draw"
    assert summary.move_count == 16
    assert summary.latest_san_move == "Ng8"
    assert summary.text == (
        "Draw by fivefold repetition. 16 moves. "
        "Latest move: Ng8. Standard starting position."
    )


def test_summary_identifies_claimed_threefold_draw() -> None:
    repetition_cycle = (
        "g1f3",
        "g8f6",
        "f3g1",
        "f6g8",
    )
    record = create_game_record(
        move_uci_history=repetition_cycle * 2,
        claimed_draw_reason="threefold_repetition",
    )

    summary = create_game_record_summary(record)

    assert summary.outcome == "draw"
    assert summary.move_count == 8
    assert summary.latest_san_move == "Ng8"
    assert summary.text == (
        "Draw claimed by threefold repetition. 8 moves. "
        "Latest move: Ng8. Standard starting position."
    )


def test_summary_distinguishes_custom_start_and_is_deterministic() -> None:
    record = create_game_record(
        start_fen="7k/8/8/8/8/8/4K3/R7 w - - 0 1",
        move_uci_history=("a1a2",),
    )

    first_summary = create_game_record_summary(record)
    second_summary = create_game_record_summary(record)

    assert first_summary == second_summary
    assert first_summary.start_position == "custom"
    assert first_summary.move_count == 1
    assert first_summary.latest_san_move == "Ra2"
    assert first_summary.text == (
        "Game in progress. 1 move. "
        "Latest move: Ra2. Custom starting position."
    )


def test_game_record_summary_is_immutable() -> None:
    summary = create_game_record_summary(
        create_game_record()
    )

    with pytest.raises(FrozenInstanceError):
        summary.move_count = 1  # type: ignore[misc]
