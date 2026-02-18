import os
import time
import threading
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox

import cv2
import numpy as np
import pyautogui
import chess
from stockfish import Stockfish

# Giả định file core.py nằm cùng thư mục
from core import ChessPredictor, detect_chessboard

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_FILE = os.path.join(BASE_DIR, "chess_model_best.pth")
STOCKFISH_FILE = os.path.join(BASE_DIR, "stockfish.exe")

COLORS = {
    "bg_main": "#212121",
    "bg_frame": "#303030",
    "text_main": "#ECECEC",
    "text_accent": "#4CAF50",
    "text_warn": "#FF5252",
    "btn_bg": "#424242",
    "btn_fg": "#FFFFFF",
    "btn_primary": "#2196F3",
    "btn_success": "#4CAF50",
    "board_light": "#EEEED2",
    "board_dark": "#769656",
    "highlight_src": "#F6F669",  # Vàng (Gợi ý đi)
    "highlight_dst": "#BACA2B",  # Xanh (Gợi ý đến)
    "selected": "#64B5F6",       # Màu ô đang chọn
    "last_move": "#C5CAE9"       # Màu nước vừa đi
}

FONTS = {
    "main": ("Segoe UI", 10),
    "bold": ("Segoe UI", 10, "bold"),
    "header": ("Segoe UI", 14, "bold"),
    "score": ("Consolas", 24, "bold"),
    "symbol": ("Segoe UI Symbol", 32)
}

PIECES_UNICODE = {
    'K': '♔', 'Q': '♕', 'R': '♖', 'B': '♗', 'N': '♘', 'P': '♙',
    'k': '♚', 'q': '♛', 'r': '♜', 'b': '♝', 'n': '♞', 'p': '♟'
}

class OverlayWindow(tk.Toplevel):
    def __init__(self, master, w=500, h=500):
        super().__init__(master)
        self.title("Khung Ngắm")
        self.geometry(f"{w}x{h}+100+100")
        self.attributes('-topmost', True)
        self.attributes('-alpha', 0.5)
        
        bg_color = 'fuchsia' if os.name == 'nt' else 'systemTransparent'
        if os.name == 'nt':
            self.attributes('-transparentcolor', bg_color)
        
        self.config(bg=bg_color)
        self.canvas = tk.Canvas(self, bg=bg_color, highlightthickness=4, highlightbackground='#FF3D00')
        self.canvas.pack(fill='both', expand=True)

    def get_geometry(self):
        self.update_idletasks()
        return (self.canvas.winfo_rootx(), self.canvas.winfo_rooty(), 
                self.canvas.winfo_width(), self.canvas.winfo_height())

class ChessAssistApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Chess Vision")
        self.root.geometry("520x700")
        self.root.attributes('-topmost', True)
        self.root.configure(bg=COLORS["bg_main"])
        
        # --- Core Logic Components ---
        self.predictor = None
        self.stockfish = None
        self.engine_lock = threading.Lock()
        self.board_logic = chess.Board()
        
        # --- State Variables ---
        self.overlay = None
        self.is_auto_running = False
        self.selected_square = None
        self.best_move_uci = None
        
        # --- Initialization ---
        self.init_engine()
        self.setup_scrollable_area()
        self.setup_ui()
        self.toggle_overlay()

    def setup_scrollable_area(self):
        container = tk.Frame(self.root, bg=COLORS["bg_main"])
        container.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(container, bg=COLORS["bg_main"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.canvas.yview)
        self.scroll_frame = tk.Frame(self.canvas, bg=COLORS["bg_main"])

        self.scroll_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Mousewheel & Resize handling
        self.canvas.bind('<Configure>', lambda e: self.canvas.itemconfig(self.canvas_window, width=e.width))
        self.root.bind_all("<MouseWheel>", lambda e: self.canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

    def setup_ui(self):
        parent = self.scroll_frame

        # --- Header ---
        header_frame = tk.Frame(parent, bg="#111", pady=10)
        header_frame.pack(fill='x')
        tk.Label(header_frame, text="CHESS VISION", font=FONTS["header"], bg="#111", fg=COLORS["text_accent"]).pack()

        # --- Evaluation Bar ---
        self.frame_eval = tk.Frame(parent, bg=COLORS["bg_frame"], pady=10, padx=10)
        self.frame_eval.pack(fill='x', padx=10, pady=10)
        
        self.lbl_eval_score = tk.Label(self.frame_eval, text="+0.00", font=FONTS["score"], bg=COLORS["bg_frame"], fg=COLORS["text_main"])
        self.lbl_eval_score.pack(side='top', pady=(0, 5))
        
        
        self.canvas_bar = tk.Canvas(self.frame_eval, height=15, bg="#444", highlightthickness=0)
        self.canvas_bar.pack(fill='x', expand=True)
        self.bar_id = self.canvas_bar.create_rectangle(0, 0, 0, 15, fill=COLORS["text_accent"], width=0)

        # --- Chessboard Display ---
        self.board_size = 360
        self.sq_size = self.board_size // 8
        board_container = tk.Frame(parent, bg=COLORS["bg_main"], padx=2, pady=2)
        board_container.pack(pady=5)
        
        self.canvas_board = tk.Canvas(board_container, width=self.board_size, height=self.board_size, bg=COLORS["bg_main"], highlightthickness=0)
        self.canvas_board.pack()
        self.canvas_board.bind("<Button-1>", self.on_board_click)

        # --- Controls Section ---
        ctrl_frame = tk.LabelFrame(parent, text="Thiết lập", font=FONTS["bold"], bg=COLORS["bg_frame"], fg=COLORS["text_main"], bd=0, padx=10, pady=10)
        ctrl_frame.pack(fill='x', padx=10, pady=5)

        # 1. Perspective & Engine Toggle
        f_row1 = tk.Frame(ctrl_frame, bg=COLORS["bg_frame"])
        f_row1.pack(fill='x', pady=5)
        
        self.turn_var = tk.StringVar(value="w")
        tk.Label(f_row1, text="Phe:", bg=COLORS["bg_frame"], fg="#CCC").pack(side='left')
        for val, txt in [("w", "Trắng"), ("b", "Đen")]:
            tk.Radiobutton(f_row1, text=txt, variable=self.turn_var, value=val, command=self.redraw_board,
                           bg=COLORS["bg_frame"], fg="white", selectcolor="#444", activebackground=COLORS["bg_frame"], activeforeground="white").pack(side='left', padx=5)

        self.use_engine_var = tk.BooleanVar(value=True)
        tk.Checkbutton(f_row1, text="Bật Engine", variable=self.use_engine_var, command=self.trigger_analysis_if_needed,
                       bg=COLORS["bg_frame"], fg=COLORS["text_accent"], selectcolor="#333", activebackground=COLORS["bg_frame"], activeforeground="white").pack(side='right', padx=5)

        # 2. Interactive Mode
        f_row2 = tk.Frame(ctrl_frame, bg=COLORS["bg_frame"])
        f_row2.pack(fill='x', pady=5)
        self.interactive_var = tk.BooleanVar(value=False)
        tk.Checkbutton(f_row2, text="Chế độ Tương tác (Click để đi)", variable=self.interactive_var, command=self.toggle_interactive_mode,
                       font=FONTS["bold"], bg=COLORS["bg_frame"], fg="#FF9800", selectcolor="#333", activebackground=COLORS["bg_frame"], activeforeground="white").pack(side='left')

        # 3. Scan Mode
        f_scan = tk.Frame(ctrl_frame, bg=COLORS["bg_frame"])
        f_scan.pack(fill='x', pady=5)
        self.scan_mode = tk.StringVar(value="overlay")
        tk.Radiobutton(f_scan, text="Khung ngắm", variable=self.scan_mode, value="overlay", command=self.toggle_overlay, bg=COLORS["bg_frame"], fg="white", selectcolor="#444", activebackground=COLORS["bg_frame"], activeforeground="white").pack(side='left')
        tk.Radiobutton(f_scan, text="Full màn", variable=self.scan_mode, value="full", command=self.toggle_overlay, bg=COLORS["bg_frame"], fg="white", selectcolor="#444", activebackground=COLORS["bg_frame"], activeforeground="white").pack(side='left', padx=10)

        # 4. Dimensions
        f_size = tk.Frame(ctrl_frame, bg=COLORS["bg_frame"])
        f_size.pack(fill='x', pady=5)
        self.ent_w = tk.Entry(f_size, width=5, bg="#222", fg="white"); self.ent_w.insert(0, "540"); self.ent_w.pack(side='left')
        tk.Label(f_size, text="x", bg=COLORS["bg_frame"], fg="#CCC").pack(side='left')
        self.ent_h = tk.Entry(f_size, width=5, bg="#222", fg="white"); self.ent_h.insert(0, "540"); self.ent_h.pack(side='left')
        self.create_flat_button(f_size, "Set Size", self.apply_overlay_size, bg="#555", width=8).pack(side='left', padx=5)

        # --- Action Buttons ---
        action_frame = tk.Frame(parent, bg=COLORS["bg_main"])
        action_frame.pack(fill='x', padx=10, pady=10)

        self.btn_scan = self.create_flat_button(action_frame, "QUÉT CAMERA (Scan)", self.start_scan_once, bg=COLORS["btn_primary"], height=2)
        self.btn_scan.pack(fill='x', pady=(0, 5))

        f_auto = tk.Frame(action_frame, bg=COLORS["bg_main"])
        f_auto.pack(fill='x')
        tk.Label(f_auto, text="Delay(s):", bg=COLORS["bg_main"], fg="white").pack(side='left')
        self.ent_delay = tk.Entry(f_auto, width=5, bg="#333", fg="white"); self.ent_delay.insert(0, "2"); self.ent_delay.pack(side='left', padx=5)
        self.btn_auto = self.create_flat_button(f_auto, "AUTO: OFF", self.toggle_auto_scan, bg="#555", width=15)
        self.btn_auto.pack(side='right')

        # Footer
        footer = tk.Frame(parent, bg=COLORS["bg_main"])
        footer.pack(fill='x', padx=10, pady=5)
        self.create_flat_button(footer, "Mở Lichess", self.open_lichess, bg="#FF9800", fg="black").pack(fill='x')
        
        self.lbl_info = tk.Label(parent, text="Ready...", bg=COLORS["bg_main"], fg="#777", font=("Segoe UI", 9, "italic"))
        self.lbl_info.pack(side='bottom', pady=20)

        self.redraw_board()

    def create_flat_button(self, parent, text, command, bg, fg="white", width=None, height=1):
        btn = tk.Button(parent, text=text, command=command, bg=bg, fg=fg, 
                        font=FONTS["bold"], bd=0, relief="flat", activebackground="#777", activeforeground="white")
        if width: btn.config(width=width)
        if height: btn.config(height=height)
        return btn

    # --- LOGIC: INTERACTIVE MODE ---
    def toggle_interactive_mode(self):
        if self.interactive_var.get():
            if self.is_auto_running:
                self.toggle_auto_scan()
            self.btn_auto.config(state="disabled", bg="#333", text="AUTO (Locked)")
            self.lbl_info.config(text="Chế độ Tương tác: Click bàn cờ để đi quân", fg="#FF9800")
        else:
            self.btn_auto.config(state="normal", bg="#555", text="AUTO: OFF")
            self.lbl_info.config(text="Đã tắt tương tác", fg="#777")
            self.selected_square = None
            self.redraw_board()

    def on_board_click(self, event):
        if not self.interactive_var.get():
            return

        # Calculate square from click coordinates
        col_idx = event.x // self.sq_size
        row_idx = event.y // self.sq_size
        
        # Adjust for board orientation
        is_black_view = (self.turn_var.get() == 'b')
        if is_black_view:
            col = 7 - col_idx
            rank = row_idx
        else:
            col = col_idx
            rank = 7 - row_idx
            
        clicked_square = chess.square(col, rank)

        # Move Logic
        if self.selected_square is None:
            # Phase 1: Select Piece
            piece = self.board_logic.piece_at(clicked_square)
            if piece:
                self.selected_square = clicked_square
                self.redraw_board()
        else:
            # Phase 2: Move Piece
            if clicked_square == self.selected_square:
                # Click same square -> Deselect
                self.selected_square = None
                self.redraw_board()
            else:
                # Attempt Move
                move = chess.Move(self.selected_square, clicked_square)
                
                # Auto-promote to Queen
                if self.board_logic.piece_at(self.selected_square).piece_type == chess.PAWN:
                    if (self.board_logic.turn == chess.WHITE and rank == 7) or \
                       (self.board_logic.turn == chess.BLACK and rank == 0):
                        move.promotion = chess.QUEEN

                if move in self.board_logic.legal_moves:
                    self.board_logic.push(move)
                    self.selected_square = None
                    self.redraw_board()
                    self.trigger_analysis_if_needed()
                else:
                    # Illegal move: Check if user clicked another friendly piece
                    piece = self.board_logic.piece_at(clicked_square)
                    if piece and piece.color == self.board_logic.turn:
                        self.selected_square = clicked_square
                        self.redraw_board()
                    else:
                        self.selected_square = None
                        self.redraw_board()

    # --- LOGIC: VISUALIZATION ---
    def redraw_board(self):
        self.canvas_board.delete("all")
        is_black_view = (self.turn_var.get() == 'b')

        # 1. Draw Squares
        for r in range(8):
            for c in range(8):
                color = COLORS["board_light"] if (r + c) % 2 == 0 else COLORS["board_dark"]
                x1, y1 = c * self.sq_size, r * self.sq_size
                self.canvas_board.create_rectangle(x1, y1, x1+self.sq_size, y1+self.sq_size, fill=color, outline="")

        # 2. Draw Selected Highlight
        if self.selected_square is not None:
            f, r = chess.square_file(self.selected_square), chess.square_rank(self.selected_square)
            self._highlight_sq(f, 7-r, COLORS["selected"], is_black_view)

        # 3. Draw Engine Highlight
        if self.best_move_uci and self.use_engine_var.get():
             try:
                move = chess.Move.from_uci(self.best_move_uci)
                f1, r1 = chess.square_file(move.from_square), chess.square_rank(move.from_square)
                f2, r2 = chess.square_file(move.to_square), chess.square_rank(move.to_square)
                
                self._highlight_sq(f1, 7-r1, COLORS["highlight_src"], is_black_view)
                self._highlight_sq(f2, 7-r2, COLORS["highlight_dst"], is_black_view)
                
                c1 = self._get_center(f1, 7-r1, is_black_view)
                c2 = self._get_center(f2, 7-r2, is_black_view)
                self.canvas_board.create_line(c1[0], c1[1], c2[0], c2[1], fill="#FF3D00", width=4, arrow=tk.LAST)
             except ValueError: pass

        # 4. Draw Pieces
        for square, piece in self.board_logic.piece_map().items():
            f, r = chess.square_file(square), chess.square_rank(square)
            
            # Convert to visual coordinates
            visual_row = 7 - r
            visual_col = f
            
            draw_r = 7 - visual_row if is_black_view else visual_row
            draw_c = 7 - visual_col if is_black_view else visual_col
            
            x = draw_c * self.sq_size + self.sq_size/2
            y = draw_r * self.sq_size + self.sq_size/2
            
            symbol = PIECES_UNICODE[piece.symbol()]
            p_fill = "white" if piece.color == chess.WHITE else "black"
            
            self.canvas_board.create_text(x+1, y+1, text=symbol, font=FONTS["symbol"], fill="#555")
            self.canvas_board.create_text(x, y, text=symbol, font=FONTS["symbol"], fill=p_fill)

        # 5. Draw Coordinates
        files = "abcdefgh"[::-1] if is_black_view else "abcdefgh"
        ranks = "87654321"[::-1] if is_black_view else "87654321"
        for i, txt in enumerate(files):
            self.canvas_board.create_text(i*self.sq_size + self.sq_size - 8, self.board_size - 10, text=txt, fill="#333", font=("Arial", 8, "bold"))
        for i, txt in enumerate(ranks):
            self.canvas_board.create_text(5, i*self.sq_size + 8, text=txt, fill="#333", font=("Arial", 8, "bold"))

    def _highlight_sq(self, f, visual_r, color, is_black):
        c, row = (7 - f, 7 - visual_r) if is_black else (f, visual_r)
        x1, y1 = c * self.sq_size, row * self.sq_size
        self.canvas_board.create_rectangle(x1, y1, x1+self.sq_size, y1+self.sq_size, fill=color, outline="")

    def _get_center(self, f, visual_r, is_black):
        c, row = (7 - f, 7 - visual_r) if is_black else (f, visual_r)
        return c * self.sq_size + self.sq_size/2, row * self.sq_size + self.sq_size/2

    # --- LOGIC: ENGINE & SCAN ---
    def trigger_analysis_if_needed(self):
        if self.use_engine_var.get():
            threading.Thread(target=self.analyze_current_position).start()
        else:
            self.lbl_info.config(text="Engine đã tắt", fg="#777")
            self.best_move_uci = None
            self.update_eval_display(0, None)
            self.redraw_board()

    def analyze_current_position(self):
        fen = self.board_logic.fen()
        best_move, eval_val, mate_val = self.get_stockfish_move(fen)
        
        self.best_move_uci = best_move
        
        # Update UI Thread-Safe
        self.root.after(0, lambda: self.update_eval_display(eval_val, mate_val))
        self.root.after(0, lambda: self.lbl_info.config(text=f"Gợi ý: {best_move}", fg=COLORS["text_accent"]))
        self.root.after(0, self.redraw_board)

    def get_stockfish_move(self, fen):
        if not self.use_engine_var.get(): return None, 0, None

        with self.engine_lock:
            if not self.stockfish: self.restart_stockfish()
            if not self.stockfish: return None, 0, None
            try:
                if not self.stockfish.is_fen_valid(fen): return None, 0, None
                self.stockfish.set_fen_position(fen)
                bm = self.stockfish.get_best_move()
                ev = self.stockfish.get_evaluation()
                
                val = ev.get('value', 0)/100.0 if ev['type'] != 'mate' else 0
                mate = ev.get('value') if ev['type'] == 'mate' else None
                return bm, val, mate
            except Exception: 
                self.restart_stockfish()
                return None, 0, None

    def run_process_once(self):
        try:
            # Capture Screen
            if self.scan_mode.get() == "overlay" and self.overlay:
                x, y, w, h = self.overlay.get_geometry()
                screenshot = pyautogui.screenshot(region=(x, y, w, h))
                strict = False
            else:
                screenshot = pyautogui.screenshot()
                strict = True

            # Detect Board
            screen_bgr = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
            board_img, _ = detect_chessboard(screen_bgr, strict=strict)
            
            if board_img is None: 
                self.root.after(0, lambda: self.lbl_info.config(text="Không tìm thấy bàn cờ", fg=COLORS["text_warn"]))
                return

            # Predict FEN
            turn = self.turn_var.get()
            if self.predictor:
                partial_fen = self.predictor.predict_fen(board_img, is_black_view=(turn == 'b'))
                if 'K' not in partial_fen or 'k' not in partial_fen: return
                
                full_fen = f"{partial_fen} {turn} - - 0 1"
                self.board_logic.set_fen(full_fen)
                self.analyze_current_position()

        except Exception as e:
            print(f"Scan error: {e}")

    # --- Helpers ---
    def init_engine(self):
        if os.path.exists(MODEL_FILE):
            try: self.predictor = ChessPredictor(MODEL_FILE)
            except Exception as e: print(f"Model Error: {e}")
        self.restart_stockfish()

    def restart_stockfish(self):
        with self.engine_lock:
            if self.stockfish:
                try: del self.stockfish 
                except: pass
                self.stockfish = None
            if os.path.exists(STOCKFISH_FILE):
                try: self.stockfish = Stockfish(path=STOCKFISH_FILE, depth=15, parameters={"Threads": 2, "Hash": 64})
                except Exception as e: print(f"Engine Error: {e}")

    def start_scan_once(self):
        threading.Thread(target=self.run_process_once).start()
    
    def get_user_size(self):
        try: return int(self.ent_w.get()), int(self.ent_h.get())
        except ValueError: return 500, 500

    def apply_overlay_size(self):
        if self.overlay and self.scan_mode.get() == "overlay":
            w, h = self.get_user_size()
            x, y = self.overlay.winfo_x(), self.overlay.winfo_y()
            self.overlay.geometry(f"{w}x{h}+{x}+{y}")

    def toggle_overlay(self):
        if self.scan_mode.get() == "overlay":
            w, h = self.get_user_size()
            if not self.overlay:
                self.overlay = OverlayWindow(self.root, w, h)
            else:
                self.overlay.deiconify()
                self.apply_overlay_size()
        else:
            if self.overlay: self.overlay.withdraw()
            
    def update_eval_display(self, eval_val, mate_val):
        is_playing_black = (self.turn_var.get() == 'b')
        text, fg_color, fill_color, ratio = "0.0", COLORS["text_main"], "#888", 0.5
        
        if mate_val is not None:
            mate_score = -mate_val if is_playing_black else mate_val
            text = f"M{abs(mate_score)}"
            fg_color = fill_color = COLORS["text_accent"] if mate_score > 0 else COLORS["text_warn"]
            ratio = 1.0 if mate_score > 0 else 0.0
        else:
            val = float(eval_val)
            display_score = -val if is_playing_black else val
            text = f"{display_score:+.2f}"
            if display_score > 0.3:
                fg_color = fill_color = COLORS["text_accent"]
            elif display_score < -0.3:
                fg_color = fill_color = COLORS["text_warn"]
            ratio = (max(min(display_score, 4.0), -4.0) + 4.0) / 8.0
            
        self.lbl_eval_score.config(text=text, fg=fg_color)
        w_total = self.canvas_bar.winfo_width()
        self.canvas_bar.coords(self.bar_id, 0, 0, int(ratio * w_total), 15)
        self.canvas_bar.itemconfig(self.bar_id, fill=fill_color)
        self.canvas_bar.config(bg="#3E2723" if ratio < 0.4 else "#444")

    def open_lichess(self):
        if self.board_logic:
            webbrowser.open(f"https://lichess.org/analysis/{self.board_logic.fen().replace(' ', '_')}")

    def toggle_auto_scan(self):
        # Don't allow auto scan in interactive mode
        if self.interactive_var.get() and not self.is_auto_running:
            return 
            
        if self.is_auto_running:
            self.is_auto_running = False
            self.btn_auto.config(text="AUTO: OFF", bg="#555")
        else:
            self.is_auto_running = True
            self.btn_auto.config(text="AUTO: ON", bg=COLORS["btn_success"])
            threading.Thread(target=self.loop_auto_scan, daemon=True).start()

    def loop_auto_scan(self):
        while self.is_auto_running:
            self.run_process_once()
            try:
                time.sleep(float(self.ent_delay.get()))
            except ValueError:
                time.sleep(2)

if __name__ == "__main__":
    root = tk.Tk()
    app = ChessAssistApp(root)
    root.mainloop()