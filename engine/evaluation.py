import chess
from engine.board import ChessBoard

# Material values in centipawns (100 centipawns = 1 pawn value)
# Standard values: pawn=1, knight=3, bishop=3, rook=5, queen=9
PAWN_VALUE = 100
KNIGHT_VALUE = 300
BISHOP_VALUE = 300
ROOK_VALUE = 500
QUEEN_VALUE = 900

# Large value representing infinity / checkmate
CHECKMATE_VALUE = 100000

# Mobility heuristic weight (bonus per legal move in centipawns)
MOBILITY_WEIGHT = 10

# Piece-Square Tables (PST)
# Tables are defined in standard human reading order: rank 8 (top) to rank 1 (bottom).
# Higher values encourage pieces to occupy those squares.

PAWN_PST = [
     0,  0,  0,  0,  0,  0,  0,  0,
    50, 50, 50, 50, 50, 50, 50, 50,
    10, 10, 20, 30, 30, 20, 10, 10,
     5,  5, 10, 25, 25, 10,  5,  5,
     0,  0,  0, 20, 20,  0,  0,  0,
     5, -5,-10,  0,  0,-10, -5,  5,
     5, 10, 10,-20,-20, 10, 10,  5,
     0,  0,  0,  0,  0,  0,  0,  0
]

KNIGHT_PST = [
    -50,-40,-30,-30,-30,-30,-40,-50,
    -40,-20,  0,  0,  0,  0,-20,-40,
    -30,  0, 10, 15, 15, 10,  0,-30,
    -30,  5, 15, 20, 20, 15,  5,-30,
    -30,  0, 15, 20, 20, 15,  0,-30,
    -30,  5, 10, 15, 15, 10,  5,-30,
    -40,-20,  0,  5,  5,  0,-20,-40,
    -50,-40,-30,-30,-30,-30,-40,-50
]

BISHOP_PST = [
    -20,-10,-10,-10,-10,-10,-10,-20,
    -10,  0,  0,  0,  0,  0,  0,-10,
    -10,  0,  5, 10, 10,  5,  0,-10,
    -10,  5,  5, 10, 10,  5,  5,-10,
    -10,  0, 10, 10, 10, 10,  0,-10,
    -10, 10, 10, 10, 10, 10, 10,-10,
    -10,  5,  0,  0,  0,  0,  5,-10,
    -20,-10,-10,-10,-10,-10,-10,-20
]

ROOK_PST = [
      0,  0,  0,  0,  0,  0,  0,  0,
      5, 10, 10, 10, 10, 10, 10,  5,
     -5,  0,  0,  0,  0,  0,  0, -5,
     -5,  0,  0,  0,  0,  0,  0, -5,
     -5,  0,  0,  0,  0,  0,  0, -5,
     -5,  0,  0,  0,  0,  0,  0, -5,
     -5,  0,  0,  0,  0,  0,  0, -5,
      0,  0,  0,  5,  5,  0,  0,  0
]

QUEEN_PST = [
    -20,-10,-10, -5, -5,-10,-10,-20,
    -10,  0,  0,  0,  0,  0,  0,-10,
    -10,  0,  5,  5,  5,  5,  0,-10,
     -5,  0,  5,  5,  5,  5,  0, -5,
      0,  0,  5,  5,  5,  5,  0, -5,
    -10,  5,  5,  5,  5,  5,  0,-10,
    -10,  0,  5,  0,  0,  5,  0,-10,
    -20,-10,-10, -5, -5,-10,-10,-20
]

KING_PST = [
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -20,-30,-30,-40,-40,-30,-30,-20,
    -10,-20,-20,-20,-20,-20,-20,-10,
     20, 20,  0,  0,  0,  0, 20, 20,
     20, 30, 10,  0,  0, 10, 30, 20
]

# Map piece types to their PST tables
PST_MAP = {
    chess.PAWN: PAWN_PST,
    chess.KNIGHT: KNIGHT_PST,
    chess.BISHOP: BISHOP_PST,
    chess.ROOK: ROOK_PST,
    chess.QUEEN: QUEEN_PST,
    chess.KING: KING_PST
}

def evaluate_board(board_wrapper: ChessBoard) -> int:
    """
    Evaluates the chess board and returns a score from White's perspective.
    Positive scores indicate an advantage for White, negative for Black.
    
    Args:
        board_wrapper: The ChessBoard wrapper instance.
    Returns:
        int: The evaluation score in centipawns.
    """
    board = board_wrapper.board
    
    # 1. Check for immediate terminal states
    if board.is_game_over():
        if board.is_checkmate():
            # If it's White's turn, White is checkmated, so score is heavily negative
            return -CHECKMATE_VALUE if board.turn == chess.WHITE else CHECKMATE_VALUE
        # Draw states (stalemate, repetition, insufficient material, fifty moves)
        return 0

    score = 0

    # 2. Material & Position evaluation
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if not piece:
            continue
            
        piece_type = piece.piece_type
        color = piece.color
        rank = chess.square_rank(square)
        file = chess.square_file(square)

        # Base material evaluation
        material_val = 0
        if piece_type == chess.PAWN:
            material_val = PAWN_VALUE
        elif piece_type == chess.KNIGHT:
            material_val = KNIGHT_VALUE
        elif piece_type == chess.BISHOP:
            material_val = BISHOP_VALUE
        elif piece_type == chess.ROOK:
            material_val = ROOK_VALUE
        elif piece_type == chess.QUEEN:
            material_val = QUEEN_VALUE
            
        # Positional evaluation (PST lookup)
        pst = PST_MAP.get(piece_type)
        pst_val = 0
        if pst:
            if color == chess.WHITE:
                # White index: top to bottom (rank 8 -> rank 1)
                idx = (7 - rank) * 8 + file
                pst_val = pst[idx]
            else:
                # Black index: mirrored vertically (rank 1 -> rank 8)
                idx = rank * 8 + file
                pst_val = pst[idx]

        # Combine material and positional score
        piece_score = material_val + pst_val

        # Add for White, subtract for Black
        if color == chess.WHITE:
            score += piece_score
        else:
            score -= piece_score

    # 3. Mobility evaluation
    # Determine white and black legal moves to reward mobility
    original_turn = board.turn
    
    # Get mobility for active turn
    active_mobility = len(list(board.legal_moves))
    
    # Switch turn to check mobility for inactive turn
    board.turn = not original_turn
    inactive_mobility = len(list(board.legal_moves))
    
    # Restore original turn state
    board.turn = original_turn
    
    if original_turn == chess.WHITE:
        white_mobility = active_mobility
        black_mobility = inactive_mobility
    else:
        white_mobility = inactive_mobility
        black_mobility = active_mobility
        
    score += MOBILITY_WEIGHT * (white_mobility - black_mobility)

    return score
