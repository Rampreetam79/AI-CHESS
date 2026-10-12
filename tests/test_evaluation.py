import pytest
import chess
from engine.board import ChessBoard
from engine.evaluation import evaluate_board, CHECKMATE_VALUE

def test_initial_evaluation():
    """The initial symmetrical board should evaluate to 0."""
    board = ChessBoard()
    score = evaluate_board(board)
    assert score == 0

def test_pawn_move_evaluation():
    """Making a pawn move e4 should change the score (usually positive for white center occupancy)."""
    board = ChessBoard()
    board.make_move("e4")
    score = evaluate_board(board)
    # White has occupied the center with a pawn (e4 PST value is +20, and mobility increases for White)
    assert score > 0

def test_checkmate_evaluation():
    """Checkmate should return the extreme checkmate values."""
    # Scholar's mate: 1. e4 e5 2. Qh5 Nc6 3. Bc4 Nf6 4. Qxf7# (White checkmates Black)
    board = ChessBoard()
    board.make_move("e4")
    board.make_move("e5")
    board.make_move("Qh5")
    board.make_move("Nc6")
    board.make_move("Bc4")
    board.make_move("Nf6")
    board.make_move("Qxf7")
    
    score = evaluate_board(board)
    assert score == CHECKMATE_VALUE

    # Inverse checkmate (Black checkmates White)
    # Fool's mate: 1. f3 e5 2. g4 Qh4#
    board2 = ChessBoard()
    board2.make_move("f3")
    board2.make_move("e5")
    board2.make_move("g4")
    board2.make_move("Qh4")
    
    score2 = evaluate_board(board2)
    assert score2 == -CHECKMATE_VALUE

def test_stalemate_evaluation():
    """Stalemate should evaluate to 0 (draw)."""
    # A known fast stalemate FEN
    # White to move, but stalemate
    stalemate_fen = "k7/8/8/8/8/8/5q2/7K w - - 0 1"
    board = ChessBoard(stalemate_fen)
    score = evaluate_board(board)
    assert score == 0
