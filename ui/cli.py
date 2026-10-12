"""Terminal interface for a human-vs-AI chess game.

Run from the project root with:
    python -m ui.cli --depth 3
"""

import argparse
from typing import Optional

import chess

from engine.board import ChessBoard
from engine.search import SearchAgent


def _show_position(board: ChessBoard) -> None:
    """Print the board and the side that is to move."""
    board.print_board()
    side = "White (you)" if board.board.turn == chess.WHITE else "Black (AI)"
    print(f"Turn: {side}")


def _read_human_move(board: ChessBoard) -> bool:
    """Read and apply one legal White move; return False when the user quits."""
    while True:
        move_text = input("Your move (SAN/UCI, or 'quit'): ").strip()
        if move_text.lower() in {"quit", "exit"}:
            return False
        if board.make_move(move_text):
            return True
        print("Invalid or illegal move. Please try again.")


def run_cli(depth: int = 3, debug: bool = False) -> None:
    """Run a game where a human plays White and Alpha-Beta plays Black."""
    board = ChessBoard()
    ai = SearchAgent(depth=depth, use_alpha_beta=True)

    print("AI Chess — you are White. Enter moves in SAN (e4, Nf3) or UCI (e2e4).")
    _show_position(board)

    while not board.board.is_game_over():
        if board.board.turn == chess.WHITE:
            if not _read_human_move(board):
                print("Game ended by user.")
                return
        else:
            print(f"AI is searching to depth {depth}...")
            move: Optional[chess.Move] = ai.get_best_move_alphabeta(board)
            if move is None:
                break
            san = board.board.san(move)
            board.make_move(move)
            print(f"AI plays: {san}")
            if debug:
                print(
                    "Search debug: "
                    f"depth reached={ai.last_completed_depth}, "
                    f"nodes visited={ai.nodes_searched}, "
                    f"nodes pruned={ai.nodes_pruned}, "
                    f"root evaluation={ai.last_score}"
                )

        # This runs after both human and AI moves, including the final move.
        _show_position(board)

    _, reason = board.is_game_over()
    print(f"Game over: {reason.replace('_', ' ')}.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Play chess against the Alpha-Beta AI.")
    parser.add_argument(
        "--depth",
        type=int,
        default=3,
        help="Alpha-Beta search depth in plies (default: 3).",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Show Alpha-Beta statistics after every AI move.",
    )
    args = parser.parse_args()
    if args.depth < 1:
        parser.error("--depth must be at least 1")
    run_cli(args.depth, debug=args.debug)


if __name__ == "__main__":
    main()
