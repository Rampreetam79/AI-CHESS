import pytest
import chess
import time
import sys
from pathlib import Path

# Running this file directly makes Python place ``tests/`` rather than the
# project root on sys.path.  Keep the standalone benchmark command working.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.board import ChessBoard
from engine.search import SearchAgent


# Fixed, reproducible benchmark positions.  Each value is a complete FEN so
# minimax and Alpha-Beta always search the identical position independently.
COMPARISON_POSITIONS = [
    ("Starting position", chess.STARTING_FEN),
    ("After 1. e4 c5", "rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2"),
    ("Scholar's mate threat", "r1bqkb1r/pppp1ppp/2n2n2/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 4 4"),
]


def run_search_comparison(depth: int = 3) -> None:
    """Print a minimax vs. Alpha-Beta comparison for three sample positions.

    Run directly from the project root with:
        python tests/test_search.py
    """
    rows = []
    for name, fen in COMPARISON_POSITIONS:
        minimax_board = ChessBoard(fen)
        alpha_beta_board = ChessBoard(fen)

        minimax = SearchAgent(depth=depth, use_alpha_beta=False)
        start = time.perf_counter()
        minimax_move = minimax.get_best_move_minimax(minimax_board)
        minimax_time = time.perf_counter() - start

        alpha_beta = SearchAgent(depth=depth, use_alpha_beta=True)
        start = time.perf_counter()
        alpha_beta_move = alpha_beta.get_best_move_alphabeta(alpha_beta_board)
        alpha_beta_time = time.perf_counter() - start

        rows.append((
            name,
            str(minimax_move),
            minimax.nodes_searched,
            minimax_time,
            str(alpha_beta_move),
            alpha_beta.nodes_searched,
            alpha_beta_time,
            minimax_move == alpha_beta_move,
        ))

    headers = (
        "Position", "Minimax move", "MM nodes", "MM time (s)",
        "Alpha-Beta move", "AB nodes", "AB time (s)", "Same move",
    )
    widths = [
        max(len(header), *(len(str(row[index])) for row in rows))
        for index, header in enumerate(headers)
    ]

    def format_row(values):
        return " | ".join(
            f"{str(value):<{width}}" for value, width in zip(values, widths)
        )

    print(f"Search comparison at depth {depth}")
    print(format_row(headers))
    print("-+-".join("-" * width for width in widths))
    for row in rows:
        name, mm_move, mm_nodes, mm_time, ab_move, ab_nodes, ab_time, same_move = row
        print(format_row((
            name,
            mm_move,
            mm_nodes,
            f"{mm_time:.4f}",
            ab_move,
            ab_nodes,
            f"{ab_time:.4f}",
            "Yes" if same_move else "No",
        )))


if __name__ == "__main__":
    run_search_comparison()

def test_minimax_returns_legal_move():
    """Minimax should return a legal move from the starting position."""
    board = ChessBoard()
    agent = SearchAgent(depth=2)
    move = agent.get_best_move(board)
    assert move is not None
    assert move in board.board.legal_moves

def test_node_counter_increments():
    """The node counter should be positive after a search."""
    board = ChessBoard()
    agent = SearchAgent(depth=2)
    agent.get_best_move(board)
    assert agent.nodes_searched > 0

def test_node_counter_resets_each_search():
    """Each call to get_best_move should reset the node counter."""
    board = ChessBoard()
    agent = SearchAgent(depth=1)
    agent.get_best_move(board)
    first_count = agent.nodes_searched

    agent.get_best_move(board)
    second_count = agent.nodes_searched

    # Both searches start from the same position with the same depth,
    # so they should examine the same number of nodes.
    assert second_count == first_count

def test_depth_increases_nodes():
    """A deeper search should examine more nodes than a shallower one."""
    board = ChessBoard()

    agent_shallow = SearchAgent(depth=1)
    agent_shallow.get_best_move(board)

    agent_deep = SearchAgent(depth=2)
    agent_deep.get_best_move(board)

    assert agent_deep.nodes_searched > agent_shallow.nodes_searched

def test_finds_checkmate_in_one():
    """Minimax should find a mate-in-one when available."""
    # White to move: Qh5 can deliver mate but the real mate-in-1 setup:
    # After 1.e4 e5 2.Qh5 Nc6 3.Bc4 Nf6 -> 4.Qxf7# is mate in 1
    board = ChessBoard()
    for san in ["e4", "e5", "Qh5", "Nc6", "Bc4", "Nf6"]:
        board.make_move(san)

    agent = SearchAgent(depth=1)
    move = agent.get_best_move(board)

    # The only mate is Qxf7
    assert move is not None
    board.make_move(move)
    is_over, reason = board.is_game_over()
    assert is_over
    assert reason == "checkmate"

def test_minimax_plays_as_black():
    """Minimax should work correctly when playing as Black (minimizing)."""
    board = ChessBoard()
    board.make_move("e4")

    agent = SearchAgent(depth=2)
    move = agent.get_best_move(board)

    assert move is not None
    assert move in board.board.legal_moves
    assert agent.nodes_searched > 0


# ---- Alpha-Beta specific tests ----

def test_alphabeta_returns_legal_move():
    """Alpha-Beta should return a legal move from the starting position."""
    board = ChessBoard()
    agent = SearchAgent(depth=2, use_alpha_beta=True)
    move = agent.get_best_move(board)
    assert move is not None
    assert move in board.board.legal_moves

def test_alphabeta_finds_checkmate_in_one():
    """Alpha-Beta should find a mate-in-one just like plain Minimax."""
    board = ChessBoard()
    for san in ["e4", "e5", "Qh5", "Nc6", "Bc4", "Nf6"]:
        board.make_move(san)

    agent = SearchAgent(depth=1, use_alpha_beta=True)
    move = agent.get_best_move(board)

    assert move is not None
    board.make_move(move)
    is_over, reason = board.is_game_over()
    assert is_over
    assert reason == "checkmate"

def test_alphabeta_examines_fewer_nodes():
    """Alpha-Beta should examine fewer or equal nodes compared to plain Minimax."""
    board = ChessBoard()

    agent = SearchAgent(depth=3)

    agent.get_best_move_minimax(board)
    minimax_nodes = agent.nodes_searched

    agent.get_best_move_alphabeta(board)
    ab_nodes = agent.nodes_searched

    assert ab_nodes <= minimax_nodes
    # At depth 3, alpha-beta should prune a significant portion
    assert ab_nodes < minimax_nodes

def test_flag_selects_algorithm():
    """The use_alpha_beta flag should control which algorithm get_best_move uses."""
    board = ChessBoard()

    agent_mm = SearchAgent(depth=2, use_alpha_beta=False)
    agent_mm.get_best_move(board)
    mm_nodes = agent_mm.nodes_searched

    agent_ab = SearchAgent(depth=2, use_alpha_beta=True)
    agent_ab.get_best_move(board)
    ab_nodes = agent_ab.nodes_searched

    # Alpha-beta should prune and thus examine fewer nodes
    assert ab_nodes <= mm_nodes

def test_direct_api_calls():
    """Both get_best_move_minimax() and get_best_move_alphabeta() work independently."""
    board = ChessBoard()
    agent = SearchAgent(depth=2)

    move_mm = agent.get_best_move_minimax(board)
    nodes_mm = agent.nodes_searched
    assert move_mm is not None

    move_ab = agent.get_best_move_alphabeta(board)
    nodes_ab = agent.nodes_searched
    assert move_ab is not None

    # Both should return legal moves
    assert move_mm in board.board.legal_moves
    assert move_ab in board.board.legal_moves

    # Node counters should be independent
    assert nodes_mm > 0
    assert nodes_ab > 0


def test_iterative_deepening_logs_each_completed_depth():
    """Iterative Alpha-Beta records separate node and timing data per depth."""
    board = ChessBoard()
    agent = SearchAgent(depth=3, use_alpha_beta=True)

    move = agent.get_best_move(board)

    assert move in board.board.legal_moves
    assert [entry["depth"] for entry in agent.search_log] == [1, 2, 3]
    assert all(entry["nodes"] > 0 for entry in agent.search_log)
    assert all(entry["time_s"] >= 0 for entry in agent.search_log)


def test_mvv_lva_orders_captures_before_quiet_moves():
    """Captures precede quiet moves and use victim/attacker value ordering."""
    board = ChessBoard("4k3/8/8/3q4/2P1P3/8/8/4K3 w - - 0 1")
    agent = SearchAgent()
    ordered = agent._order_moves(board, board.get_legal_moves())

    capture_indices = [
        index for index, move in enumerate(ordered) if board.board.is_capture(move)
    ]
    quiet_indices = [
        index for index, move in enumerate(ordered) if not board.board.is_capture(move)
    ]

    assert capture_indices
    assert max(capture_indices) < min(quiet_indices)
