# AI Chess: Adversarial Search Case Study

This project implements a chess-playing agent for the Fundamentals of Artificial Intelligence case study. A human can play White through the command-line interface while the AI plays Black using depth-limited adversarial search.

## Problem formulation

Chess is modeled as a game-playing/search problem rather than as a single-agent path-finding problem.

| Property | Classification | Why |
|---|---|---|
| Agents | Two-player | One human and one AI alternate turns. |
| Utilities | Zero-sum | A position favorable to White is unfavorable to Black. The evaluation is positive for White and negative for Black. |
| Dynamics | Deterministic | A legal move always produces the same next board state. |
| Observability | Fully observable | Both players can see the complete board and move history needed to determine legal moves. |
| Interaction | Sequential | Each move changes the state and influences the opponent's future choices. |

The state is represented by a `python-chess` board (and may be stored in the transposition table by its FEN). Actions are legal chess moves. A terminal state is checkmate, stalemate, or another draw condition. The utility/evaluation function returns a score from White's perspective.

## Agent architecture

The program uses a model-based, utility-based game-playing agent.

```text
Current board state
       |
Legal-move generator (python-chess)
       |
SearchAgent: Minimax / Alpha-Beta search
       |
Evaluation function: material + piece-square tables + mobility
       |
Best legal move
       |
Updated board state
```

Main modules:

- `engine/board.py` — board wrapper, legal moves, move application, and terminal-state detection.
- `engine/evaluation.py` — static position evaluation. Material, piece-square-table values, and mobility produce a White-centric score.
- `engine/search.py` — Minimax and Alpha-Beta search, move ordering, iterative deepening, and the transposition table.
- `ui/cli.py` — human-vs-AI command-line interface.

## AI strategy: Minimax with Alpha-Beta pruning

The agent applies the Minimax principle:

- White is the maximizing player and chooses the move with the largest evaluation.
- Black is the minimizing player and chooses the move with the smallest evaluation.
- Search stops at a chosen depth or a terminal board, then evaluates the resulting position.

Plain Minimax explores every move in the search tree up to the depth limit. Alpha-Beta pruning produces the same Minimax decision while avoiding branches that cannot change the final choice:

- `alpha` is the best score that the maximizing player can already guarantee.
- `beta` is the best score that the minimizing player can already guarantee.
- A branch is cut off when `beta <= alpha`, because the opponent has a better alternative and will never choose that branch.

The implementation additionally improves Alpha-Beta efficiency through:

- **MVV-LVA move ordering:** captures are searched first, preferring a more valuable victim captured by a less valuable attacker.
- **Iterative deepening:** searches shallow depths before deeper ones to obtain useful move ordering.
- **FEN-keyed transposition table:** caches previously searched positions with exact, lower-bound, or upper-bound scores.

These enhancements reduce the number of nodes searched but do not change the intended Minimax decision.

## Run the project

Install dependencies:

```bash
pip install -r requirements.txt
```

Start the command-line game at depth 3:

```bash
python -m ui.cli --depth 3
```

The human always plays White. Enter moves in SAN (for example, `e4` or `Nf3`) or UCI notation (for example, `e2e4`).

Use `--debug` to display the reached search depth, visited nodes, Alpha-Beta-pruned child continuations, and root evaluation after each AI move:

```bash
python -m ui.cli --depth 3 --debug
```

## Testing and search comparison

Run the test suite:

```bash
python -m pytest -q
```

Compare Minimax and Alpha-Beta over three fixed positions at the same depth:

```bash
python tests/test_search.py
```

The comparison prints each algorithm's best move, nodes searched, execution time, and whether both algorithms selected the same move. This demonstrates that Alpha-Beta preserves the Minimax choice while searching fewer positions.
