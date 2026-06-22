import pytest

from boardstep.game import (
    STARTING_FEN,
    apply_uci_move,
    board_rows,
    build_uci_move,
    game_status,
    legal_move_count,
    legal_target_squares,
    side_to_move,
    validate_fen_position,
)


def test_starting_position_has_white_to_move():
    assert side_to_move(STARTING_FEN) == "White"
    assert game_status(STARTING_FEN) == "White to move."
    assert legal_move_count(STARTING_FEN) == 20


def test_board_rows_show_starting_position():
    rows = board_rows(STARTING_FEN)

    assert len(rows) == 8
    assert rows[0]["rank"] == "8"
    assert rows[-1]["rank"] == "1"
    assert rows[0]["a"] == "♜"
    assert rows[-1]["e"] == "♔"


def test_apply_legal_uci_move_updates_position():
    new_fen, san = apply_uci_move(STARTING_FEN, "e2e4")

    assert san == "e4"
    assert side_to_move(new_fen) == "Black"


def test_validate_fen_position_accepts_starting_position():
    assert validate_fen_position(STARTING_FEN) == STARTING_FEN


def test_validate_fen_position_accepts_extra_spaces():
    assert validate_fen_position(f"  {STARTING_FEN}  ") == STARTING_FEN


def test_validate_fen_position_rejects_empty_text():
    with pytest.raises(ValueError, match="Enter a FEN position"):
        validate_fen_position("   ")


def test_validate_fen_position_rejects_invalid_text():
    with pytest.raises(ValueError, match="valid FEN position"):
        validate_fen_position("not-a-fen")


def test_validate_fen_position_rejects_invalid_position():
    with pytest.raises(ValueError, match="valid FEN position"):
        validate_fen_position("8/8/8/8/8/8/8/8 w - - 0 1")


def test_apply_uci_move_accepts_extra_spaces():
    new_fen, san = apply_uci_move(STARTING_FEN, "  g1f3  ")

    assert san == "Nf3"
    assert side_to_move(new_fen) == "Black"


def test_build_uci_move_from_selected_squares():
    assert build_uci_move("e2", "e4") == "e2e4"
    assert build_uci_move(" G1 ", " F3 ") == "g1f3"


def test_build_uci_move_rejects_invalid_square():
    with pytest.raises(ValueError, match="valid source and target squares"):
        build_uci_move("e9", "e4")


def test_legal_target_squares_returns_pawn_moves_from_starting_position():
    assert legal_target_squares(STARTING_FEN, "e2") == ["e3", "e4"]


def test_legal_target_squares_returns_knight_moves_from_starting_position():
    assert legal_target_squares(STARTING_FEN, "g1") == ["f3", "h3"]


def test_legal_target_squares_returns_empty_list_for_empty_square():
    assert legal_target_squares(STARTING_FEN, "e4") == []


def test_legal_target_squares_returns_empty_list_for_blocked_piece():
    assert legal_target_squares(STARTING_FEN, "a1") == []


def test_legal_target_squares_handles_spaces_and_uppercase_square_input():
    assert legal_target_squares(STARTING_FEN, " E2 ") == ["e3", "e4"]


def test_legal_target_squares_returns_empty_list_for_invalid_square():
    assert legal_target_squares(STARTING_FEN, "not-a-square") == []


def test_apply_uci_move_rejects_invalid_format():
    with pytest.raises(ValueError, match="Use UCI format"):
        apply_uci_move(STARTING_FEN, "not-a-move")


def test_apply_uci_move_rejects_illegal_move():
    with pytest.raises(ValueError, match="Illegal move"):
        apply_uci_move(STARTING_FEN, "e2e5")


def test_game_status_detects_checkmate():
    fen = STARTING_FEN

    for move_text in ["e2e4", "e7e5", "d1h5", "b8c6", "f1c4", "g8f6", "h5f7"]:
        fen, _san = apply_uci_move(fen, move_text)

    assert game_status(fen) == "Checkmate. White wins."
