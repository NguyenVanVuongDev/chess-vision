"""Post-game analysis: walks every ply of a game through Stockfish,
computes centipawn loss per move relative to the mover, classifies each
move, and derives a Lichess-style accuracy percentage per side.

This is a simplified, honestly-approximate version of what sites like
Lichess/Chess.com do (real engines behind those sites use much deeper
search and more careful win% calibration) - good enough for a personal
training tool, not a certified replica of any specific site's algorithm.
"""

import io
import math
from collections import Counter
from typing import List

import chess
import chess.pgn
from stockfish import Stockfish

REVIEW_DEPTH = 12
EVAL_CAP = 1000  # centipawns used as a stand-in for "decisive" mate scores

CLASS_NAMES = ["brilliant", "good", "ok", "inaccuracy", "mistake", "blunder"]
# (classification, max centipawn loss that still counts as this tier)
CLASS_THRESHOLDS = [
    ("brilliant", 0),
    ("good", 20),
    ("ok", 50),
    ("inaccuracy", 100),
    ("mistake", 200),
]


def extract_san_moves(pgn_text: str) -> List[str]:
    game = chess.pgn.read_game(io.StringIO(pgn_text))
    if game is None:
        raise ValueError("Không thể đọc PGN")
    board = game.board()
    sans = []
    for move in game.mainline_moves():
        sans.append(board.san(move))
        board.push(move)
    if not sans:
        raise ValueError("Không tìm thấy nước đi nào trong PGN")
    return sans


def _read_eval(evaluation: dict) -> int:
    if evaluation.get("type") == "mate":
        mate_value = evaluation.get("value", 0)
        if mate_value == 0:
            return 0
        return EVAL_CAP if mate_value > 0 else -EVAL_CAP
    return max(-EVAL_CAP, min(EVAL_CAP, evaluation.get("value", 0)))


def _win_percent(cp: float) -> float:
    return 50 + 50 * (2 / (1 + math.exp(-0.00368208 * cp)) - 1)


def _move_accuracy(win_before: float, win_after: float) -> float:
    drop = max(0.0, win_before - win_after)
    value = 103.1668 * math.exp(-0.04354 * drop) - 3.1669
    return max(0.0, min(100.0, value))


def _classify(loss: float) -> str:
    for name, threshold in CLASS_THRESHOLDS:
        if loss <= threshold:
            return name
    return "blunder"


def analyze_game(san_moves, stockfish_path, engine_lock, depth: int = REVIEW_DEPTH) -> dict:
    if not stockfish_path.exists():
        raise RuntimeError("Không tìm thấy tệp Stockfish")

    board = chess.Board()
    fens = [board.fen()]
    parsed = []
    for i, san in enumerate(san_moves):
        try:
            move = board.parse_san(san)
        except ValueError as error:
            raise ValueError(f"Nước đi không hợp lệ ở nước {i + 1}: {san}") from error
        parsed.append({"san": board.san(move), "uci": move.uci()})
        board.push(move)
        fens.append(board.fen())

    with engine_lock:
        engine = Stockfish(path=str(stockfish_path), depth=depth, parameters={"Threads": 2, "Hash": 64})

        # One evaluation per position (N+1 positions for N moves) rather than
        # two per move - the eval after move i is the same position as the
        # eval before move i+1, so we only ever need to ask the engine once.
        evals = []
        for fen in fens:
            engine.set_fen_position(fen)
            evals.append(_read_eval(engine.get_evaluation()))

        moves = []
        counts = {"w": Counter(), "b": Counter()}
        accuracies = {"w": [], "b": []}

        for i, mv in enumerate(parsed):
            mover = "w" if i % 2 == 0 else "b"
            eval_before, eval_after = evals[i], evals[i + 1]

            if mover == "w":
                loss = max(0, eval_before - eval_after)
                win_before = _win_percent(eval_before)
                win_after = _win_percent(eval_after)
            else:
                loss = max(0, eval_after - eval_before)
                win_before = 100 - _win_percent(eval_before)
                win_after = 100 - _win_percent(eval_after)

            classification = _classify(loss)
            accuracy = _move_accuracy(win_before, win_after)

            # Only spend an extra search on a "what should I have played"
            # suggestion for moves that weren't already essentially optimal.
            best_move = None
            if classification not in ("brilliant", "good"):
                engine.set_fen_position(fens[i])
                best_move = engine.get_best_move()

            moves.append({
                "ply": i + 1,
                "move_number": i // 2 + 1,
                "color": mover,
                "san": mv["san"],
                "uci": mv["uci"],
                "fen_before": fens[i],
                "fen_after": fens[i + 1],
                "eval_before": eval_before,
                "eval_after": eval_after,
                "loss": round(loss, 1),
                "classification": classification,
                "accuracy": round(accuracy, 1),
                "best_move": best_move,
            })
            counts[mover][classification] += 1
            accuracies[mover].append(accuracy)

    def summarize(color):
        acc_list = accuracies[color]
        return {
            "accuracy": round(sum(acc_list) / len(acc_list), 1) if acc_list else 0.0,
            "counts": {name: counts[color].get(name, 0) for name in CLASS_NAMES},
        }

    return {
        "evals": evals,
        "moves": moves,
        "summary": {"white": summarize("w"), "black": summarize("b")},
    }
