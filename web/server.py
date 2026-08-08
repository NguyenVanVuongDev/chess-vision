import os
import sys
import threading
from pathlib import Path
from typing import List, Optional

import chess
import cv2
import numpy as np
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from stockfish import Stockfish

ROOT_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = Path(__file__).resolve().parent / "static"
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(STATIC_DIR))

from core import ChessPredictor, detect_chessboard
from game_review import analyze_game as run_game_review
from game_review import extract_san_moves
from openings_data import OPENINGS

MODEL_FILE = Path(os.getenv("MODEL_FILE", ROOT_DIR / "chess_model_best.pth"))
STOCKFISH_FILE = Path(os.getenv("STOCKFISH_FILE", ROOT_DIR / "stockfish.exe"))

app = FastAPI(title="Chess Vision Web")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/pieces", StaticFiles(directory=ROOT_DIR / "pieces"), name="pieces")

predictor = ChessPredictor(str(MODEL_FILE)) if MODEL_FILE.exists() else None
stockfish = None
engine_lock = threading.Lock()


class FenRequest(BaseModel):
    fen: str
    use_engine: bool = True


class GameReviewRequest(BaseModel):
    pgn: Optional[str] = None
    moves: Optional[List[str]] = None
    depth: int = 12


def get_engine():
    global stockfish
    if stockfish is None and STOCKFISH_FILE.exists():
        stockfish = Stockfish(
            path=str(STOCKFISH_FILE),
            depth=15,
            parameters={"Threads": 2, "Hash": 64},
        )
    return stockfish


def analyze_fen(fen: str, use_engine: bool = True):
    global stockfish
    board = chess.Board(fen)
    if not use_engine:
        return {"best_move": None, "evaluation": 0, "mate": None}

    with engine_lock:
        engine = get_engine()
        if engine is None:
            return {"best_move": None, "evaluation": 0, "mate": None}

        try:
            engine.set_fen_position(board.fen())
            best_move = engine.get_best_move()
            evaluation = engine.get_evaluation()
            if evaluation["type"] == "mate":
                return {
                    "best_move": best_move,
                    "evaluation": 0,
                    "mate": evaluation["value"],
                }
            return {
                "best_move": best_move,
                "evaluation": evaluation.get("value", 0) / 100.0,
                "mate": None,
            }
        except Exception:
            stockfish = None
            return {"best_move": None, "evaluation": 0, "mate": None}


def response_for_fen(fen: str, use_engine: bool):
    try:
        board = chess.Board(fen)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=f"FEN không hợp lệ: {error}") from error

    result = analyze_fen(board.fen(), use_engine)
    return {"success": True, "fen": board.fen(), **result}


@app.get("/")
def index():
    return FileResponse(
        STATIC_DIR / "index.html",
        headers={"Cache-Control": "no-store, max-age=0"},
    )


@app.get("/opening")
def opening_page():
    return FileResponse(
        STATIC_DIR / "opening.html",
        headers={"Cache-Control": "no-store, max-age=0"},
    )


@app.get("/review")
def review_page():
    return FileResponse(
        STATIC_DIR / "review.html",
        headers={"Cache-Control": "no-store, max-age=0"},
    )


@app.get("/api/health")
def health():
    return {
        "success": True,
        "model_loaded": predictor is not None,
        "stockfish_available": STOCKFISH_FILE.exists(),
    }


@app.post("/api/analyze")
def analyze_screen(
    image: UploadFile = File(...),
    turn: str = Form("w"),
    black_view: bool = Form(False),
    use_engine: bool = Form(True),
):
    if turn not in {"w", "b"}:
        raise HTTPException(status_code=400, detail="turn phải là w hoặc b")
    if predictor is None:
        raise HTTPException(status_code=503, detail="Không tìm thấy chess_model_best.pth")

    raw_image = image.file.read()
    frame = cv2.imdecode(np.frombuffer(raw_image, np.uint8), cv2.IMREAD_COLOR)
    if frame is None:
        raise HTTPException(status_code=400, detail="Ảnh màn hình không hợp lệ")

    board_image, bounds = detect_chessboard(frame, strict=True)
    if board_image is None:
        return {"success": False, "message": "Không tìm thấy bàn cờ trong màn hình"}

    partial_fen = predictor.predict_fen(board_image, is_black_view=black_view)
    if "K" not in partial_fen or "k" not in partial_fen:
        return {"success": False, "message": "Không nhận diện được đủ hai vua"}

    try:
        fen = chess.Board(f"{partial_fen} {turn} - - 0 1").fen()
    except ValueError as error:
        return {"success": False, "message": f"Vị trí nhận diện không hợp lệ: {error}"}

    result = analyze_fen(fen, use_engine)
    return {
        "success": True,
        "fen": fen,
        "bounds": bounds,
        **result,
    }


@app.post("/api/analyze-fen")
def analyze_position(request: FenRequest):
    return response_for_fen(request.fen, request.use_engine)


@app.get("/api/openings")
def list_openings():
    return {"success": True, "openings": OPENINGS}


@app.post("/api/analyze-game")
def analyze_game_endpoint(request: GameReviewRequest):
    moves = request.moves
    if not moves and request.pgn:
        try:
            moves = extract_san_moves(request.pgn)
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
    if not moves:
        raise HTTPException(status_code=400, detail="Cần cung cấp PGN hoặc danh sách nước đi")
    if not STOCKFISH_FILE.exists():
        raise HTTPException(status_code=503, detail="Không tìm thấy Stockfish để phân tích ván đấu")

    depth = max(6, min(18, request.depth))
    try:
        result = run_game_review(moves, STOCKFISH_FILE, engine_lock, depth=depth)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error

    return {"success": True, **result}
