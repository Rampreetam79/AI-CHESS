import os
from typing import List, Union, Tuple, Optional
import pygame
import chess
from engine.board import ChessBoard
from engine.search import SearchAgent

# Constants for UI configuration
WINDOW_WIDTH = 900
WINDOW_HEIGHT = 640
BOARD_SIZE = 640
SQUARE_SIZE = BOARD_SIZE // 8

# Harmonies of premium color palette (Slate Blue & Cream Theme)
COLOR_LIGHT_SQ = (240, 217, 181)       # Cream
COLOR_DARK_SQ = (181, 136, 99)         # Wood brown
COLOR_BG = (30, 30, 32)               # Sleek Dark Background
COLOR_SIDEBAR_BG = (40, 40, 43)       # Slightly lighter dark grey for sidebar
COLOR_TEXT = (240, 240, 245)           # Bright text
COLOR_TEXT_MUTED = (160, 160, 170)     # Dimmed text
COLOR_SELECTED = (186, 202, 43, 128)  # Semi-transparent gold highlight
COLOR_LAST_MOVE = (247, 247, 105, 100) # Highlight for the last move made
COLOR_LEGAL_DOT = (100, 150, 220, 160) # Soft blue for empty legal landing squares
COLOR_LEGAL_CAPTURE = (220, 80, 80, 180) # Soft red for legal captures
COLOR_BUTTON = (50, 120, 200)
COLOR_BUTTON_HOVER = (70, 140, 220)
COLOR_BUTTON_TEXT = (255, 255, 255)

# Unicode chess piece symbols for rendering
UNICODE_PIECES = {
    'wK': '\u2654', 'wQ': '\u2655', 'wR': '\u2656',
    'wB': '\u2657', 'wN': '\u2658', 'wP': '\u2659',
    'bK': '\u265A', 'bQ': '\u265B', 'bR': '\u265C',
    'bB': '\u265D', 'bN': '\u265E', 'bP': '\u265F',
}


class ChessGUI:
    def __init__(self, board: ChessBoard, agent: SearchAgent):
        self.board = board
        self.agent = agent
        self.selected_square = None
        self.legal_moves_for_selected = []

        # Move history: list of SAN strings, cached at the time the move is made
        self.move_history_san: List[str] = []

        # Game Mode settings
        # "human_vs_human" or "human_vs_ai"
        self.game_mode = "human_vs_ai"
        self.ai_color = chess.BLACK  # AI plays as black by default
        self.ai_thinking = False

        # Initialize pygame
        pygame.init()
        pygame.display.set_caption("AI Chess Studio")
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        self.clock = pygame.time.Clock()

        # Font initialization
        self.font_title = pygame.font.SysFont("Helvetica", 24, bold=True)
        self.font_ui = pygame.font.SysFont("Helvetica", 16)
        self.font_btn = pygame.font.SysFont("Helvetica", 16, bold=True)

        # Piece font: try several unicode-capable fonts in order of preference
        self.font_piece = None
        for font_name in ["Segoe UI Symbol", "Arial Unicode MS", "DejaVu Sans", "Symbola", "Noto Sans"]:
            try:
                test_font = pygame.font.SysFont(font_name, 56)
                # Verify it can actually render a chess piece
                test_surf = test_font.render('\u2654', True, (0, 0, 0))
                if test_surf.get_width() > 5:
                    self.font_piece = test_font
                    break
            except Exception:
                continue

        if self.font_piece is None:
            self.font_piece = pygame.font.SysFont(None, 56)

        # Fallback letter font for when Unicode symbols don't render
        self.font_piece_letter = pygame.font.SysFont("Helvetica", 36, bold=True)

        # Pre-render piece surfaces for performance
        self.piece_surfaces = {}
        self._generate_piece_surfaces()

        # UI Elements
        # Buttons definitions: (rect, label, action_name)
        self.buttons = [
            (pygame.Rect(670, 480, 200, 40), "Undo Move", "undo"),
            (pygame.Rect(670, 530, 200, 40), "Restart Game", "restart"),
            (pygame.Rect(670, 430, 200, 40), "Toggle Mode", "toggle_mode")
        ]

    def _generate_piece_surfaces(self):
        """Pre-renders chess piece images using Unicode symbols with shadows."""
        for code, symbol in UNICODE_PIECES.items():
            is_white = code.startswith('w')

            surf = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA)

            # Try rendering with the unicode font
            text_surf = self.font_piece.render(symbol, True, (255, 255, 255) if is_white else (40, 40, 40))
            rendered_ok = text_surf.get_width() > 10

            if rendered_ok:
                # Draw shadow for depth
                shadow_color = (0, 0, 0, 80) if is_white else (255, 255, 255, 60)
                shadow_surf = self.font_piece.render(symbol, True, shadow_color[:3])
                shadow_surf.set_alpha(shadow_color[3])
                shadow_rect = shadow_surf.get_rect(center=(SQUARE_SIZE // 2 + 2, SQUARE_SIZE // 2 + 2))
                surf.blit(shadow_surf, shadow_rect)

                # Draw piece
                text_rect = text_surf.get_rect(center=(SQUARE_SIZE // 2, SQUARE_SIZE // 2))
                surf.blit(text_surf, text_rect)

                # Draw thin outline for white pieces to make them visible on light squares
                if is_white:
                    outline_surf = self.font_piece.render(symbol, True, (60, 60, 60))
                    outline_rect = outline_surf.get_rect(center=(SQUARE_SIZE // 2, SQUARE_SIZE // 2))
                    # Blit outline at slight offsets
                    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        surf.blit(outline_surf, outline_rect.move(dx, dy))
                    # Re-blit the white piece on top
                    surf.blit(text_surf, text_rect)
            else:
                # Fallback: draw letter on a colored circle
                piece_letter = code[1]  # 'K', 'Q', 'R', etc.
                bg_color = (220, 220, 225) if is_white else (50, 50, 55)
                text_color = (40, 40, 40) if is_white else (230, 230, 230)

                # Circle background
                pygame.draw.circle(surf, bg_color, (SQUARE_SIZE // 2, SQUARE_SIZE // 2), int(SQUARE_SIZE * 0.38))
                pygame.draw.circle(surf, (100, 100, 100), (SQUARE_SIZE // 2, SQUARE_SIZE // 2), int(SQUARE_SIZE * 0.38), 2)

                # Letter
                letter_surf = self.font_piece_letter.render(piece_letter, True, text_color)
                letter_rect = letter_surf.get_rect(center=(SQUARE_SIZE // 2, SQUARE_SIZE // 2))
                surf.blit(letter_surf, letter_rect)

            self.piece_surfaces[code] = surf

    def _get_piece_sprite_name(self, piece: chess.Piece) -> str:
        """Helper to get asset code for a chess.Piece (e.g. 'wK', 'bP')."""
        color_char = 'w' if piece.color == chess.WHITE else 'b'
        piece_char = piece.symbol().upper()
        return f"{color_char}{piece_char}"

    def _get_square_under_mouse(self) -> Optional[chess.Square]:
        """Translates mouse coordinate to chess.Square."""
        x, y = pygame.mouse.get_pos()
        if 0 <= x < BOARD_SIZE and 0 <= y < BOARD_SIZE:
            file = x // SQUARE_SIZE
            rank = 7 - (y // SQUARE_SIZE)
            return chess.square(file, rank)
        return None

    def _push_move(self, move: chess.Move) -> bool:
        """
        Makes a move on the board and records its SAN in our history cache.
        SAN must be computed BEFORE the move is applied to the board.
        Returns True if the move was legal and applied.
        """
        # Compute SAN while the board is still in the pre-move state
        if move in self.board.board.legal_moves:
            san_str = self.board.board.san(move)
            success = self.board.make_move(move)
            if success:
                self.move_history_san.append(san_str)
                return True
        return False

    def _pop_move(self) -> Optional[chess.Move]:
        """Undoes the last move and removes its SAN from our history cache."""
        undone = self.board.undo_move()
        if undone is not None and self.move_history_san:
            self.move_history_san.pop()
        return undone

    def draw_board(self):
        """Draws the chessboard grid."""
        for rank in range(8):
            for file in range(8):
                is_dark = (rank + file) % 2 != 0
                color = COLOR_DARK_SQ if is_dark else COLOR_LIGHT_SQ
                rect = pygame.Rect(file * SQUARE_SIZE, (7 - rank) * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE)
                pygame.draw.rect(self.screen, color, rect)

    def draw_highlights(self):
        """Highlights the selected square, last move, and legal landing squares."""
        # 1. Highlight Last Move
        if len(self.board.board.move_stack) > 0:
            last_move = self.board.board.peek()
            for sq in [last_move.from_square, last_move.to_square]:
                file = chess.square_file(sq)
                rank = chess.square_rank(sq)
                rect = pygame.Rect(file * SQUARE_SIZE, (7 - rank) * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE)
                s = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA)
                s.fill(COLOR_LAST_MOVE)
                self.screen.blit(s, rect)

        # 2. Highlight Selected Square
        if self.selected_square is not None:
            file = chess.square_file(self.selected_square)
            rank = chess.square_rank(self.selected_square)
            rect = pygame.Rect(file * SQUARE_SIZE, (7 - rank) * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE)
            s = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA)
            s.fill(COLOR_SELECTED)
            self.screen.blit(s, rect)

            # 3. Highlight Legal Destination Squares
            for move in self.legal_moves_for_selected:
                dest = move.to_square
                d_file = chess.square_file(dest)
                d_rank = chess.square_rank(dest)

                is_capture = self.board.board.is_capture(move)

                s = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA)
                if is_capture:
                    pygame.draw.circle(s, COLOR_LEGAL_CAPTURE, (SQUARE_SIZE // 2, SQUARE_SIZE // 2), int(SQUARE_SIZE / 2.5), 4)
                else:
                    pygame.draw.circle(s, COLOR_LEGAL_DOT, (SQUARE_SIZE // 2, SQUARE_SIZE // 2), SQUARE_SIZE // 6)

                self.screen.blit(s, (d_file * SQUARE_SIZE, (7 - d_rank) * SQUARE_SIZE))

    def draw_pieces(self):
        """Draws pieces using pre-rendered surfaces."""
        for square in chess.SQUARES:
            piece = self.board.board.piece_at(square)
            if piece:
                file = chess.square_file(square)
                rank = chess.square_rank(square)
                rect = pygame.Rect(file * SQUARE_SIZE, (7 - rank) * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE)

                sprite_code = self._get_piece_sprite_name(piece)
                if sprite_code in self.piece_surfaces:
                    self.screen.blit(self.piece_surfaces[sprite_code], rect)

    def draw_sidebar(self):
        """Draws the right panel UI containing stats, buttons, and status."""
        sidebar_rect = pygame.Rect(BOARD_SIZE, 0, WINDOW_WIDTH - BOARD_SIZE, WINDOW_HEIGHT)
        pygame.draw.rect(self.screen, COLOR_SIDEBAR_BG, sidebar_rect)

        # Border separating board and sidebar
        pygame.draw.line(self.screen, (60, 60, 65), (BOARD_SIZE, 0), (BOARD_SIZE, WINDOW_HEIGHT), 2)

        # Title
        title_surf = self.font_title.render("AI Chess Studio", True, COLOR_TEXT)
        self.screen.blit(title_surf, (BOARD_SIZE + 20, 30))

        # Active Mode
        mode_str = "Human vs Computer" if self.game_mode == "human_vs_ai" else "Human vs Human"
        mode_surf = self.font_ui.render(f"Mode: {mode_str}", True, COLOR_TEXT_MUTED)
        self.screen.blit(mode_surf, (BOARD_SIZE + 20, 80))

        # Active Turn Info
        current_turn = "White" if self.board.board.turn == chess.WHITE else "Black"
        turn_text = f"Turn: {current_turn}"
        if self.game_mode == "human_vs_ai" and self.board.board.turn == self.ai_color:
            turn_text += " (AI thinking...)" if self.ai_thinking else " (AI)"
        turn_surf = self.font_ui.render(turn_text, True, COLOR_TEXT)
        self.screen.blit(turn_surf, (BOARD_SIZE + 20, 110))

        # Game State / Results
        is_over, reason = self.board.is_game_over()
        if is_over:
            status_text = f"GAME OVER: {reason.upper()}"
            status_color = (240, 100, 100)
        else:
            if self.board.board.is_check():
                status_text = "STATUS: CHECK!"
                status_color = (240, 200, 100)
            else:
                status_text = "STATUS: ACTIVE"
                status_color = (100, 220, 100)

        status_surf = self.font_ui.render(status_text, True, status_color)
        self.screen.blit(status_surf, (BOARD_SIZE + 20, 150))

        # Move History (uses cached SAN strings — no board.san() calls needed)
        history_header = self.font_ui.render("Recent Moves:", True, COLOR_TEXT_MUTED)
        self.screen.blit(history_header, (BOARD_SIZE + 20, 200))

        # Show last 10 half-moves (5 full moves) from the SAN cache
        total_moves = len(self.move_history_san)
        start_idx = max(0, total_moves - 10)
        y_offset = 230
        idx = start_idx
        while idx < total_moves:
            turn_num = (idx // 2) + 1
            # Build the display string for this full move
            if idx % 2 == 0:
                # White's move
                line = f"{turn_num}. {self.move_history_san[idx]}"
                if idx + 1 < total_moves:
                    line += f"  {self.move_history_san[idx + 1]}"
                    idx += 2
                else:
                    idx += 1
            else:
                # Black's move (starting mid-pair)
                line = f"{turn_num}. ...  {self.move_history_san[idx]}"
                idx += 1

            move_surf = self.font_ui.render(line, True, COLOR_TEXT)
            self.screen.blit(move_surf, (BOARD_SIZE + 20, y_offset))
            y_offset += 25

        # Render Buttons
        mouse_pos = pygame.mouse.get_pos()
        for rect, label, _ in self.buttons:
            is_hover = rect.collidepoint(mouse_pos)
            color = COLOR_BUTTON_HOVER if is_hover else COLOR_BUTTON
            pygame.draw.rect(self.screen, color, rect, border_radius=6)
            btn_surf = self.font_btn.render(label, True, COLOR_BUTTON_TEXT)
            btn_rect = btn_surf.get_rect(center=rect.center)
            self.screen.blit(btn_surf, btn_rect)

    def handle_click(self, pos):
        """Processes mouse clicks on the board or sidebar."""
        # 1. Check sidebar buttons
        for rect, _, action in self.buttons:
            if rect.collidepoint(pos):
                self.execute_sidebar_action(action)
                return

        # 2. Check Board interactions (only if game is active and not AI's turn)
        is_over, _ = self.board.is_game_over()
        if is_over:
            return

        if self.game_mode == "human_vs_ai" and self.board.board.turn == self.ai_color:
            return

        clicked_square = self._get_square_under_mouse()
        if clicked_square is not None:
            # If a square is already selected and we click a legal landing square, play it
            if self.selected_square is not None:
                played = False
                for move in self.legal_moves_for_selected:
                    if move.to_square == clicked_square:
                        # Auto-promote to Queen for simplicity
                        piece = self.board.board.piece_at(self.selected_square)
                        if piece and piece.piece_type == chess.PAWN:
                            dest_rank = chess.square_rank(clicked_square)
                            if dest_rank == 7 or dest_rank == 0:
                                move = chess.Move(move.from_square, move.to_square, promotion=chess.QUEEN)

                        self._push_move(move)
                        played = True
                        break

                self.selected_square = None
                self.legal_moves_for_selected = []

                if played:
                    return

            # Otherwise, select a new piece of the active turn color
            piece = self.board.board.piece_at(clicked_square)
            if piece and piece.color == self.board.board.turn:
                self.selected_square = clicked_square
                all_legals = self.board.get_legal_moves()
                self.legal_moves_for_selected = [m for m in all_legals if m.from_square == clicked_square]
            else:
                self.selected_square = None
                self.legal_moves_for_selected = []

    def execute_sidebar_action(self, action):
        """Runs side actions like reset, undo, toggles."""
        if action == "undo":
            if self.game_mode == "human_vs_ai":
                self._pop_move()
                self._pop_move()
            else:
                self._pop_move()
            self.selected_square = None
            self.legal_moves_for_selected = []

        elif action == "restart":
            self.board = ChessBoard()
            self.move_history_san.clear()
            self.selected_square = None
            self.legal_moves_for_selected = []

        elif action == "toggle_mode":
            if self.game_mode == "human_vs_ai":
                self.game_mode = "human_vs_human"
            else:
                self.game_mode = "human_vs_ai"
                self.ai_color = chess.BLACK if self.board.board.turn == chess.WHITE else chess.WHITE
            self.selected_square = None
            self.legal_moves_for_selected = []

    def run(self):
        """Launches the main loop of Pygame GUI."""
        running = True
        while running:
            # Check for AI Turn
            is_over, _ = self.board.is_game_over()
            if not is_over and self.game_mode == "human_vs_ai" and self.board.board.turn == self.ai_color:
                self.ai_thinking = True

                # Draw the thinking state before blocking
                self.screen.fill(COLOR_BG)
                self.draw_board()
                self.draw_highlights()
                self.draw_pieces()
                self.draw_sidebar()
                pygame.display.flip()

                # Calculate AI move
                ai_move = self.agent.get_best_move(self.board)
                if ai_move:
                    self._push_move(ai_move)
                self.ai_thinking = False

            # Event loop
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        self.handle_click(event.pos)

            # Rendering
            self.screen.fill(COLOR_BG)
            self.draw_board()
            self.draw_highlights()
            self.draw_pieces()
            self.draw_sidebar()

            pygame.display.flip()
            self.clock.tick(30)

        pygame.quit()
