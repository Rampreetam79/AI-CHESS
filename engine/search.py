import logging
import time
from typing import Optional, Dict, Tuple
import chess
from engine.board import ChessBoard
from engine.evaluation import evaluate_board

# Module-level logger — outputs depth, nodes, and timing info
logger = logging.getLogger("engine.search")

# MVV-LVA (Most Valuable Victim – Least Valuable Attacker) lookup.
# Higher score = better capture to try first.
# Index by (victim_piece_type, attacker_piece_type).
_PIECE_VALUE_ORDER = {
    chess.PAWN: 1,
    chess.KNIGHT: 3,
    chess.BISHOP: 3,
    chess.ROOK: 5,
    chess.QUEEN: 9,
    chess.KING: 100,
}

# Transposition-table entry flag types
TT_EXACT = 0   # Exact score
TT_LOWER = 1   # Score is a lower bound (failed high / beta cutoff)
TT_UPPER = 2   # Score is an upper bound (failed low / alpha cutoff)


class SearchAgent:
    """
    Chess AI search agent with three search strategies:

      - 'minimax'    : depth-limited Minimax (no pruning)
      - 'alphabeta'  : depth-limited Alpha-Beta pruning (basic)
      - 'iterative'  : iterative-deepening Alpha-Beta with MVV-LVA move
                        ordering and a FEN-keyed transposition table

    After every search the following attributes are available:
        nodes_searched  – total positions examined
        search_log      – list of dicts, one per iterative-deepening depth
    """

    def __init__(self, depth: int = 3, use_alpha_beta: bool = True):
        """
        Args:
            depth:          Maximum search depth (half-moves to look ahead).
            use_alpha_beta: If True, get_best_move() uses the enhanced
                            iterative-deepening Alpha-Beta.  If False, plain
                            Minimax.
        """
        self.depth = depth
        self.use_alpha_beta = use_alpha_beta
        self.nodes_searched = 0
        # Count child positions skipped when Alpha-Beta cuts off a branch.
        self.nodes_pruned = 0
        self.last_score: Optional[int] = None
        self.last_completed_depth = 0

        # Transposition table: fen -> (depth, flag, score, best_move)
        self.tt: Dict[str, Tuple[int, int, int, Optional[chess.Move]]] = {}

        # Per-search log for benchmarking.  Each entry is:
        #   {"depth": int, "nodes": int, "time_s": float, "best_move": str, "score": int}
        self.search_log: list = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_best_move(self, board: ChessBoard) -> Optional[chess.Move]:
        """Dispatches to the algorithm selected by `use_alpha_beta`."""
        if self.use_alpha_beta:
            return self.get_best_move_iterative(board)
        return self.get_best_move_minimax(board)

    def get_best_move_minimax(self, board: ChessBoard) -> Optional[chess.Move]:
        """Plain depth-limited Minimax (no pruning, no ordering)."""
        legal_moves = board.get_legal_moves()
        if not legal_moves:
            return None

        self.nodes_searched = 0
        self.nodes_pruned = 0
        self.last_score = None
        self.last_completed_depth = self.depth
        self.search_log = []
        is_maximizing = board.board.turn == chess.WHITE

        best_move = None
        best_score = float('-inf') if is_maximizing else float('inf')

        for move in legal_moves:
            board.board.push(move)
            self.nodes_searched += 1
            score = self._minimax(board, self.depth - 1, not is_maximizing)
            board.board.pop()

            if is_maximizing:
                if score > best_score:
                    best_score = score
                    best_move = move
            else:
                if score < best_score:
                    best_score = score
                    best_move = move

        return best_move

    def get_best_move_alphabeta(self, board: ChessBoard) -> Optional[chess.Move]:
        """
        Single-pass Alpha-Beta with MVV-LVA move ordering and
        transposition-table lookups (no iterative deepening).
        """
        legal_moves = board.get_legal_moves()
        if not legal_moves:
            return None

        self.nodes_searched = 0
        self.nodes_pruned = 0
        self.last_score = None
        self.last_completed_depth = 0
        self.search_log = []
        self.tt.clear()

        best_move = self._ab_root(board, self.depth)
        self.last_completed_depth = self.depth
        return best_move

    def get_best_move_iterative(self, board: ChessBoard) -> Optional[chess.Move]:
        """
        Iterative-deepening Alpha-Beta search.

        Searches from depth 1 up to self.depth, reusing the transposition
        table across iterations.  Each completed depth refines the TT entries
        which improve move ordering for the next deeper pass.  Logs nodes
        and elapsed time for every depth.
        """
        legal_moves = board.get_legal_moves()
        if not legal_moves:
            return None

        self.nodes_searched = 0
        self.nodes_pruned = 0
        self.last_score = None
        self.last_completed_depth = 0
        self.search_log = []
        self.tt.clear()

        best_move = None
        total_start = time.perf_counter()

        for current_depth in range(1, self.depth + 1):
            iter_start = time.perf_counter()
            nodes_before = self.nodes_searched

            move = self._ab_root(board, current_depth)
            self.last_completed_depth = current_depth

            iter_time = time.perf_counter() - iter_start
            iter_nodes = self.nodes_searched - nodes_before

            if move is not None:
                best_move = move

            entry = {
                "depth": current_depth,
                "nodes": iter_nodes,
                "time_s": round(iter_time, 4),
                "best_move": str(best_move),
                "score": self._tt_score_for_root(board),
            }
            self.search_log.append(entry)
            logger.info(
                "depth=%d  nodes=%d  time=%.4fs  best=%s",
                current_depth, iter_nodes, iter_time, best_move,
            )

        total_time = time.perf_counter() - total_start
        logger.info(
            "iterative deepening complete: total_nodes=%d  total_time=%.4fs",
            self.nodes_searched, total_time,
        )

        return best_move

    # ------------------------------------------------------------------
    # Move ordering
    # ------------------------------------------------------------------

    def _order_moves(
        self,
        board: ChessBoard,
        moves: list,
        tt_best: Optional[chess.Move] = None,
    ) -> list:
        """
        Orders moves for better Alpha-Beta pruning:
          1. Transposition-table best move (from a shallower search) first.
          2. Captures sorted by MVV-LVA (Most Valuable Victim – Least
             Valuable Attacker): prefer capturing a queen with a pawn
             over capturing a pawn with a queen.
          3. Non-captures last.
        """
        tt_moves = []
        captures = []
        quiets = []

        for move in moves:
            if tt_best and move == tt_best:
                tt_moves.append((move, 1_000_000))
            elif board.board.is_capture(move):
                score = self._mvv_lva_score(board, move)
                captures.append((move, score))
            else:
                quiets.append((move, 0))

        # Sort captures descending by MVV-LVA score
        captures.sort(key=lambda x: x[1], reverse=True)

        ordered = tt_moves + captures + quiets
        return [m for m, _ in ordered]

    @staticmethod
    def _mvv_lva_score(board: ChessBoard, move: chess.Move) -> int:
        """
        Computes MVV-LVA score for a capture move.
        Score = 10 * victim_value - attacker_value
        Higher is better (big victim, small attacker).
        """
        attacker = board.board.piece_at(move.from_square)
        victim = board.board.piece_at(move.to_square)

        # En passant: victim square is empty but it's still a pawn capture
        if victim is None:
            victim_val = _PIECE_VALUE_ORDER[chess.PAWN]
        else:
            victim_val = _PIECE_VALUE_ORDER.get(victim.piece_type, 0)

        attacker_val = _PIECE_VALUE_ORDER.get(attacker.piece_type, 0) if attacker else 0

        return 10 * victim_val - attacker_val

    # ------------------------------------------------------------------
    # Transposition table helpers
    # ------------------------------------------------------------------

    def _tt_probe(
        self, fen: str, depth: int, alpha: float, beta: float
    ) -> Tuple[bool, int]:
        """
        Looks up the transposition table.
        Returns (hit, score).  If hit is False, score is meaningless.
        A TT entry is usable only if it was stored at >= the requested depth.
        """
        entry = self.tt.get(fen)
        if entry is None:
            return False, 0

        tt_depth, flag, score, _ = entry
        if tt_depth < depth:
            return False, 0

        if flag == TT_EXACT:
            return True, score
        elif flag == TT_LOWER and score >= beta:
            return True, score
        elif flag == TT_UPPER and score <= alpha:
            return True, score

        return False, 0

    def _tt_store(
        self,
        fen: str,
        depth: int,
        flag: int,
        score: int,
        best_move: Optional[chess.Move],
    ) -> None:
        """Stores or overwrites a transposition-table entry (always-replace)."""
        existing = self.tt.get(fen)
        # Always-replace with deeper or equal depth
        if existing is None or existing[0] <= depth:
            self.tt[fen] = (depth, flag, score, best_move)

    def _tt_best_move(self, fen: str) -> Optional[chess.Move]:
        """Retrieves the best move from a TT entry, if present."""
        entry = self.tt.get(fen)
        return entry[3] if entry else None

    def _tt_score_for_root(self, board: ChessBoard) -> Optional[int]:
        """Returns the stored score for the root position, if available."""
        entry = self.tt.get(board.board.fen())
        return entry[2] if entry else None

    # ------------------------------------------------------------------
    # Root-level Alpha-Beta (shared by single-pass and iterative)
    # ------------------------------------------------------------------

    def _ab_root(self, board: ChessBoard, depth: int) -> Optional[chess.Move]:
        """
        Root search: iterates over legal moves with Alpha-Beta and returns
        the best move found at the given depth.
        """
        is_maximizing = board.board.turn == chess.WHITE
        legal_moves = list(board.board.legal_moves)
        fen = board.board.fen()

        # Order moves (TT best move first, then captures by MVV-LVA)
        tt_best = self._tt_best_move(fen)
        ordered = self._order_moves(board, legal_moves, tt_best)

        best_move = None
        alpha = float('-inf')
        beta = float('inf')

        if is_maximizing:
            best_score = float('-inf')
            for move in ordered:
                board.board.push(move)
                self.nodes_searched += 1
                score = self._alpha_beta(board, depth - 1, alpha, beta, False)
                board.board.pop()

                if score > best_score:
                    best_score = score
                    best_move = move
                alpha = max(alpha, best_score)
        else:
            best_score = float('inf')
            for move in ordered:
                board.board.push(move)
                self.nodes_searched += 1
                score = self._alpha_beta(board, depth - 1, alpha, beta, True)
                board.board.pop()

                if score < best_score:
                    best_score = score
                    best_move = move
                beta = min(beta, best_score)

        # A root search always uses the full window, so its result is exact.
        self._tt_store(fen, depth, TT_EXACT, best_score, best_move)
        self.last_score = best_score

        return best_move

    # ------------------------------------------------------------------
    # Internal: plain Minimax (unchanged, no ordering/TT)
    # ------------------------------------------------------------------

    def _minimax(self, board: ChessBoard, depth: int, is_maximizing: bool) -> int:
        """Recursive depth-limited Minimax (no pruning)."""
        if depth == 0 or board.board.is_game_over():
            return evaluate_board(board)

        legal_moves = list(board.board.legal_moves)

        if is_maximizing:
            max_eval = float('-inf')
            for move in legal_moves:
                board.board.push(move)
                self.nodes_searched += 1
                eval_score = self._minimax(board, depth - 1, False)
                board.board.pop()
                if eval_score > max_eval:
                    max_eval = eval_score
            return max_eval
        else:
            min_eval = float('inf')
            for move in legal_moves:
                board.board.push(move)
                self.nodes_searched += 1
                eval_score = self._minimax(board, depth - 1, True)
                board.board.pop()
                if eval_score < min_eval:
                    min_eval = eval_score
            return min_eval

    # ------------------------------------------------------------------
    # Internal: Alpha-Beta with move ordering + TT
    # ------------------------------------------------------------------

    def _alpha_beta(
        self,
        board: ChessBoard,
        depth: int,
        alpha: float,
        beta: float,
        is_maximizing: bool,
    ) -> int:
        """
        Recursive Alpha-Beta with:
          - Transposition-table probe/store
          - MVV-LVA move ordering (captures first)
        """
        # Leaf node
        if depth == 0 or board.board.is_game_over():
            return evaluate_board(board)

        fen = board.board.fen()

        # TT probe
        hit, tt_score = self._tt_probe(fen, depth, alpha, beta)
        if hit:
            return tt_score

        legal_moves = list(board.board.legal_moves)

        # Move ordering: TT best move first, then captures (MVV-LVA), then quiets
        tt_best = self._tt_best_move(fen)
        ordered = self._order_moves(board, legal_moves, tt_best)

        best_move = None
        # Keep the window passed to this node.  TT flags describe the score
        # relative to this *original* window, not its progressively tightened
        # alpha/beta values while children are searched.
        original_alpha = alpha
        original_beta = beta

        if is_maximizing:
            max_eval = float('-inf')
            for index, move in enumerate(ordered):
                board.board.push(move)
                self.nodes_searched += 1
                eval_score = self._alpha_beta(board, depth - 1, alpha, beta, False)
                board.board.pop()

                if eval_score > max_eval:
                    max_eval = eval_score
                    best_move = move
                alpha = max(alpha, eval_score)
                if beta <= alpha:
                    self.nodes_pruned += len(ordered) - index - 1
                    break  # Beta cutoff

            score = max_eval
        else:
            min_eval = float('inf')
            for index, move in enumerate(ordered):
                board.board.push(move)
                self.nodes_searched += 1
                eval_score = self._alpha_beta(board, depth - 1, alpha, beta, True)
                board.board.pop()

                if eval_score < min_eval:
                    min_eval = eval_score
                    best_move = move
                beta = min(beta, eval_score)
                if beta <= alpha:
                    self.nodes_pruned += len(ordered) - index - 1
                    break  # Alpha cutoff
            score = min_eval

        # Bound types do not depend on which side is moving: a score at or
        # below alpha is an upper bound; one at or above beta is a lower
        # bound.  This is crucial for safely reusing entries on later visits.
        if score <= original_alpha:
            flag = TT_UPPER
        elif score >= original_beta:
            flag = TT_LOWER
        else:
            flag = TT_EXACT
        self._tt_store(fen, depth, flag, score, best_move)
        return score
