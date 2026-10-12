from typing import List, Union, Tuple, Optional
import chess

class ChessBoard:
    """
    A wrapper around chess.Board that simplifies move generation, move application,
    game-over condition checking, and console output.
    """
    def __init__(self, fen: Optional[str] = None):
        """
        Initializes the chess board.
        Args:
            fen: An optional FEN string to initialize the board to a custom state.
        """
        if fen:
            self.board = chess.Board(fen)
        else:
            self.board = chess.Board()

    def get_legal_moves(self) -> List[chess.Move]:
        """
        Returns a list of all legal chess.Move objects in the current position.
        """
        return list(self.board.legal_moves)

    def make_move(self, move: Union[chess.Move, str]) -> bool:
        """
        Applies a move to the board.
        Accepts a chess.Move object, or a SAN string (e.g. 'e4', 'Nf3'), or a UCI string (e.g. 'e2e4').
        Returns True if the move was legal and successfully applied, False otherwise.
        """
        if isinstance(move, str):
            # Clean up white space
            move_str = move.strip()
            # Try parsing as SAN first, then fallback to UCI
            try:
                parsed_move = self.board.parse_san(move_str)
            except ValueError:
                try:
                    parsed_move = self.board.parse_uci(move_str)
                except ValueError:
                    return False
        elif isinstance(move, chess.Move):
            parsed_move = move
        else:
            return False

        if parsed_move in self.board.legal_moves:
            self.board.push(parsed_move)
            return True
        return False

    def undo_move(self) -> Optional[chess.Move]:
        """
        Undoes the last move played on the board and returns it.
        Returns:
            The chess.Move object that was undone, or None if no moves have been made.
        """
        if len(self.board.move_stack) > 0:
            return self.board.pop()
        return None

    def is_game_over(self) -> Tuple[bool, str]:
        """
        Checks if the game has ended.
        Returns:
            Tuple[bool, str]: (is_over, reason_string)
            Possible reasons: "checkmate", "stalemate", "insufficient_material",
                              "threefold_repetition", "fifty_moves", "active"
        """
        if self.board.is_game_over():
            if self.board.is_checkmate():
                return True, "checkmate"
            elif self.board.is_stalemate():
                return True, "stalemate"
            elif self.board.is_insufficient_material():
                return True, "insufficient_material"
            elif self.board.is_threefold_repetition():
                return True, "threefold_repetition"
            elif self.board.is_fifty_moves():
                return True, "fifty_moves"
            else:
                return True, "draw"
        return False, "active"

    def print_board(self) -> None:
        """
        Prints a clean, nicely formatted unicode chess board to the console.
        Falls back to ASCII if the console does not support unicode characters (e.g. Windows CMD).
        """
        try:
            # Try to print unicode representation
            piece_symbols = {
                'R': '♖', 'N': '♘', 'B': '♗', 'Q': '♕', 'K': '♔', 'P': '♙',
                'r': '♜', 'n': '♞', 'b': '♝', 'q': '♛', 'k': '♚', 'p': '♟'
            }
            
            lines = []
            lines.append("\n    a   b   c   d   e   f   g   h")
            lines.append("  +---------------------------------+")
            for rank in range(8, 0, -1):
                row_str = f"{rank} |"
                for file in range(1, 9):
                    square = chess.square(file - 1, rank - 1)
                    piece = self.board.piece_at(square)
                    if piece:
                        symbol = piece.symbol()
                        char = piece_symbols.get(symbol, symbol)
                        row_str += f" {char} |"
                    else:
                        is_dark_square = (rank + file) % 2 == 0
                        empty_char = "·" if is_dark_square else " "
                        row_str += f" {empty_char} |"
                lines.append(row_str + f" {rank}")
                lines.append("  +---------------------------------+")
            lines.append("    a   b   c   d   e   f   g   h\n")
            
            # Print the entire board at once
            print("\n".join(lines))
            
        except UnicodeEncodeError:
            # Fallback to pure ASCII representation (standard chess letters)
            lines = []
            lines.append("\n    a   b   c   d   e   f   g   h")
            lines.append("  +---------------------------------+")
            for rank in range(8, 0, -1):
                row_str = f"{rank} |"
                for file in range(1, 9):
                    square = chess.square(file - 1, rank - 1)
                    piece = self.board.piece_at(square)
                    if piece:
                        char = piece.symbol() # 'R', 'r', etc.
                        row_str += f" {char} |"
                    else:
                        row_str += " . |"
                lines.append(row_str + f" {rank}")
                lines.append("  +---------------------------------+")
            lines.append("    a   b   c   d   e   f   g   h\n")
            print("\n".join(lines))

