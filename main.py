import argparse
import logging
import sys
import chess
from engine.board import ChessBoard
from engine.search import SearchAgent
from ui.gui import ChessGUI

def run_cli(board: ChessBoard, agent: SearchAgent):
    """
    Runs a CLI-based chess game.
    """
    print("=" * 40)
    print("Welcome to AI Chess - CLI Mode")
    print("=" * 40)
    print("To make a move, enter Standard Algebraic Notation (e.g. 'e4', 'Nf3')")
    print("or UCI format (e.g. 'e2e4').")
    print("Special commands: 'undo' to reverse last move, 'exit' or 'quit' to end.")
    print("-" * 40)

    # Let player choose color
    player_color = None
    while player_color is None:
        choice = input("Play as White or Black? (w/b): ").lower().strip()
        if choice in ['w', 'white']:
            player_color = chess.WHITE
        elif choice in ['b', 'black']:
            player_color = chess.BLACK
        else:
            print("Invalid selection.")

    # Main CLI game loop
    is_over, reason = board.is_game_over()
    while not is_over:
        board.print_board()
        
        # Check current turn
        current_turn = board.board.turn
        if current_turn == player_color:
            # Human turn
            move_played = False
            while not move_played:
                user_input = input("Your turn. Enter move: ").strip()
                if user_input.lower() in ['quit', 'exit']:
                    print("Exiting game.")
                    return
                elif user_input.lower() == 'undo':
                    # Undo player and AI move
                    undone_ai = board.undo_move()
                    undone_player = board.undo_move()
                    if undone_player or undone_ai:
                        print("Undid moves.")
                        break
                    else:
                        print("Nothing to undo.")
                        continue
                
                # Try making the move
                success = board.make_move(user_input)
                if success:
                    move_played = True
                else:
                    print("Invalid or illegal move. Try again. (Type 'help' to see legal moves)")
                    # Additional help feature
                    if user_input.lower() == 'help':
                        legals = [board.board.san(m) for m in board.get_legal_moves()]
                        print(f"Legal moves: {', '.join(legals)}")
        else:
            # AI turn
            print("AI is calculating...")
            ai_move = agent.get_best_move(board)
            if ai_move:
                ai_san = board.board.san(ai_move)
                board.make_move(ai_move)
                print(f"AI plays: {ai_san}")
            else:
                print("AI has no legal moves!")
                break
                
        is_over, reason = board.is_game_over()

    # Game Over Output
    board.print_board()
    print("=" * 40)
    print(f"GAME OVER! Result: {reason.upper()}")
    print("=" * 40)

def main():
    parser = argparse.ArgumentParser(description="AI Chess Project")
    parser.add_argument('--cli', action='store_true', help="Run in Command Line Interface mode instead of Pygame GUI.")
    args = parser.parse_args()

    # Make the iterative-deepening search statistics visible to CLI and GUI
    # launches.  SearchAgent records one line for every completed depth.
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s: %(message)s",
    )

    board = ChessBoard()
    agent = SearchAgent(depth=3)

    if args.cli:
        run_cli(board, agent)
    else:
        # Start Pygame interface
        try:
            gui = ChessGUI(board, agent)
            gui.run()
        except Exception as e:
            print(f"Failed to start Pygame GUI: {e}")
            print("Starting CLI mode fallback...")
            run_cli(board, agent)

if __name__ == "__main__":
    main()
