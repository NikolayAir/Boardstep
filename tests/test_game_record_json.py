import json

from boardstep.game import STARTING_FEN
from boardstep.game_record import create_game_record
from boardstep.game_record_json import (
    game_record_to_json,
    game_record_to_json_data,
)


def test_game_record_to_json_data_serializes_ongoing_game() -> None:
    record = create_game_record(
        move_uci_history=("e2e4", "e7e5"),
    )

    data = game_record_to_json_data(record)

    assert data == {
        "schema_version": 1,
        "start_fen": STARTING_FEN,
        "move_uci_history": ["e2e4", "e7e5"],
        "move_san_history": ["e4", "e5"],
        "final_fen": record.final_fen,
        "result": "*",
        "termination_reason": None,
        "claimed_draw_reason": None,
    }
    assert isinstance(data["move_uci_history"], list)
    assert isinstance(data["move_san_history"], list)


def test_game_record_to_json_data_serializes_completed_game() -> None:
    record = create_game_record(
        move_uci_history=(
            "f2f3",
            "e7e5",
            "g2g4",
            "d8h4",
        ),
    )

    data = game_record_to_json_data(record)

    assert data["move_san_history"] == [
        "f3",
        "e5",
        "g4",
        "Qh4#",
    ]
    assert data["result"] == "0-1"
    assert data["termination_reason"] == "checkmate"
    assert data["claimed_draw_reason"] is None


def test_game_record_to_json_data_serializes_claimed_draw() -> None:
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

    data = game_record_to_json_data(record)

    assert data["result"] == "1/2-1/2"
    assert data["termination_reason"] == "threefold_repetition"
    assert data["claimed_draw_reason"] == "threefold_repetition"


def test_game_record_to_json_data_supports_custom_fen() -> None:
    start_fen = "7k/8/8/8/8/8/4K3/R7 w - - 0 1"
    record = create_game_record(
        start_fen=start_fen,
        move_uci_history=("a1a2",),
    )

    data = game_record_to_json_data(record)

    assert data["start_fen"] == start_fen
    assert data["move_uci_history"] == ["a1a2"]
    assert data["move_san_history"] == ["Ra2"]
    assert data["final_fen"] == record.final_fen


def test_game_record_to_json_is_deterministic_and_parseable() -> None:
    record = create_game_record(
        move_uci_history=("e2e4", "e7e5"),
    )

    first_export = game_record_to_json(record)
    second_export = game_record_to_json(record)

    assert first_export == second_export
    assert first_export.endswith("\n")
    assert json.loads(first_export) == game_record_to_json_data(record)


def test_game_record_to_json_has_stable_formatted_output() -> None:
    record = create_game_record()

    assert game_record_to_json(record) == (
        "{\n"
        '  "schema_version": 1,\n'
        f'  "start_fen": "{STARTING_FEN}",\n'
        '  "move_uci_history": [],\n'
        '  "move_san_history": [],\n'
        f'  "final_fen": "{STARTING_FEN}",\n'
        '  "result": "*",\n'
        '  "termination_reason": null,\n'
        '  "claimed_draw_reason": null\n'
        "}\n"
    )
