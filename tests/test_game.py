import pytest

from boardstep.game import (
    STARTING_FEN,
    apply_uci_move,
    board_files,
    board_ranks,
    board_rows,
    board_from_uci_history,
    build_uci_move,
    game_is_over,
    game_status,
    game_status_from_board,
    legal_move_count,
    legal_target_squares,
    repetition_draw_state,
    threefold_draw_can_be_claimed,
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


def test_board_files_returns_white_orientation_by_default():
    assert board_files() == ("a", "b", "c", "d", "e", "f", "g", "h")


def test_board_files_returns_black_orientation_order():
    assert board_files("black") == ("h", "g", "f", "e", "d", "c", "b", "a")


def test_board_ranks_returns_white_orientation_by_default():
    assert board_ranks() == (8, 7, 6, 5, 4, 3, 2, 1)


def test_board_ranks_returns_black_orientation_order():
    assert board_ranks("black") == (1, 2, 3, 4, 5, 6, 7, 8)


def test_board_rows_support_black_orientation():
    rows = board_rows(STARTING_FEN, orientation="black")

    assert rows[0]["rank"] == "1"
    assert rows[-1]["rank"] == "8"
    assert rows[0]["e"] == "♔"
    assert rows[0]["d"] == "♕"
    assert rows[-1]["e"] == "♚"
    assert rows[-1]["d"] == "♛"


def test_board_from_uci_history_preserves_threefold_repetition_context():
    repetition_cycle = (
        "g1f3",
        "g8f6",
        "f3g1",
        "f6g8",
    )

    board = board_from_uci_history(
        STARTING_FEN,
        repetition_cycle * 2,
    )

    assert board.is_repetition(3)
    assert board.is_fivefold_repetition() is False


def test_board_from_uci_history_preserves_fivefold_repetition_context():
    repetition_cycle = (
        "g1f3",
        "g8f6",
        "f3g1",
        "f6g8",
    )

    board = board_from_uci_history(
        STARTING_FEN,
        repetition_cycle * 4,
    )

    assert board.is_fivefold_repetition()


def test_board_from_uci_history_rejects_illegal_history():
    with pytest.raises(ValueError, match="entry 2 is illegal"):
        board_from_uci_history(
            STARTING_FEN,
            ("e2e4", "e2e3"),
        )


def test_repetition_draw_state_marks_threefold_as_claimable_not_automatic():
    repetition_cycle = (
        "g1f3",
        "g8f6",
        "f3g1",
        "f6g8",
    )
    board = board_from_uci_history(
        STARTING_FEN,
        repetition_cycle * 2,
    )

    assert repetition_draw_state(board) == "claimable_threefold"
    assert board.is_game_over(claim_draw=False) is False
    assert game_status_from_board(board) == (
        "White to move. Draw can be claimed by threefold repetition."
    )


def test_repetition_draw_state_marks_fivefold_as_automatic():
    repetition_cycle = (
        "g1f3",
        "g8f6",
        "f3g1",
        "f6g8",
    )
    board = board_from_uci_history(
        STARTING_FEN,
        repetition_cycle * 4,
    )

    assert repetition_draw_state(board) == "automatic_fivefold"
    assert board.is_game_over(claim_draw=False) is True
    assert game_status_from_board(board) == "Draw by fivefold repetition."


def test_repetition_draw_state_is_empty_for_ordinary_position():
    board = board_from_uci_history(
        STARTING_FEN,
        ("e2e4", "e7e5"),
    )

    assert repetition_draw_state(board) is None


def test_threefold_draw_can_be_claimed_without_ending_game_automatically():
    repetition_cycle = (
        "g1f3",
        "g8f6",
        "f3g1",
        "f6g8",
    )
    board = board_from_uci_history(
        STARTING_FEN,
        repetition_cycle * 2,
    )

    assert threefold_draw_can_be_claimed(board)
    assert game_is_over(board) is False


def test_claimed_threefold_draw_ends_game():
    repetition_cycle = (
        "g1f3",
        "g8f6",
        "f3g1",
        "f6g8",
    )
    board = board_from_uci_history(
        STARTING_FEN,
        repetition_cycle * 2,
    )

    assert game_is_over(board, "threefold_repetition")
    assert game_status_from_board(
        board,
        "threefold_repetition",
    ) == "Draw claimed by threefold repetition."


def test_fivefold_repetition_ends_game_without_claim():
    repetition_cycle = (
        "g1f3",
        "g8f6",
        "f3g1",
        "f6g8",
    )
    board = board_from_uci_history(
        STARTING_FEN,
        repetition_cycle * 4,
    )

    assert game_is_over(board)
