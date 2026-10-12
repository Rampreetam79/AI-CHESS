import pytest
import chess
from engine.board import ChessBoard

def test_initial_board():
    """Verifies that the initial board has the correct setup and initial legal moves."""
    board = ChessBoard()
    # At the start of chess, there are 20 legal moves (16 pawn moves, 4 knight moves)
    legal_moves = board.get_legal_moves()
    assert len(legal_moves) == 20
    
    # Active state checks
    is_over, reason = board.is_game_over()
    assert not is_over
    assert reason == "active"

def test_make_move_san():
    """Tests that making a move via standard algebraic notation (SAN) works."""
    board = ChessBoard()
    # Play 1. e4
    success = board.make_move("e4")
    assert success
    
    # Check if turn switched to black
    assert board.board.turn == chess.BLACK
    
    # Check that e2 is empty and e4 contains a white pawn
    assert board.board.piece_at(chess.E2) is None
    piece_e4 = board.board.piece_at(chess.E4)
    assert piece_e4 is not None
    assert piece_e4.piece_type == chess.PAWN
    assert piece_e4.color == chess.WHITE

def test_make_move_uci():
    """Tests that making a move via Universal Chess Interface notation (UCI) works."""
    board = ChessBoard()
    # Play 1. g1f3 (Knight Nf3)
    success = board.make_move("g1f3")
    assert success
    
    piece_f3 = board.board.piece_at(chess.F3)
    assert piece_f3 is not None
    assert piece_f3.piece_type == chess.KNIGHT
    assert piece_f3.color == chess.WHITE

def test_make_invalid_move():
    """Tests that invalid moves are gracefully rejected."""
    board = ChessBoard()
    
    # Random invalid notation
    assert not board.make_move("invalid_string")
    
    # Illegal move (e.g. White pawn jumping e2 to e5)
    assert not board.make_move("e2e5")

def test_undo_move():
    """Tests that undoing moves restores board state correctly."""
    board = ChessBoard()
    
    # Play moves
    board.make_move("e4")
    board.make_move("e5")
    
    # Check move stack depth
    assert len(board.board.move_stack) == 2
    
    # Undo black move
    undone = board.undo_move()
    assert undone is not None
    assert len(board.board.move_stack) == 1
    assert board.board.turn == chess.BLACK
    
    # Undo white move
    undone2 = board.undo_move()
    assert undone2 is not None
    assert len(board.board.move_stack) == 0
    assert board.board.turn == chess.WHITE
    
    # Undo from empty stack
    assert board.undo_move() is None

def test_checkmate_detection():
    """Tests that checkmate is correctly detected and reported."""
    # Scholar's mate: 1. e4 e5 2. Qh5 Nc6 3. Bc4 Nf6 4. Qxf7#
    board = ChessBoard()
    board.make_move("e4")
    board.make_move("e5")
    board.make_move("Qh5")
    board.make_move("Nc6")
    board.make_move("Bc4")
    board.make_move("Nf6")
    
    is_over, reason = board.is_game_over()
    assert not is_over
    
    board.make_move("Qxf7")
    is_over, reason = board.is_game_over()
    assert is_over
    assert reason == "checkmate"

def test_print_board(capsys):
    """Tests that the print_board method successfully outputs representation to stdout."""
    board = ChessBoard()
    board.print_board()
    
    captured = capsys.readouterr()
    assert "a   b   c   d   e   f   g   h" in captured.out
    assert "8 |" in captured.out
    assert "1 |" in captured.out
