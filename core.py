import numpy as np
import cv2
import torch
import torch.nn as nn
from torchvision import transforms
from PIL import Image

# --- CONFIGURATION ---
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
PIECES = ['p', 'r', 'n', 'b', 'q', 'k', 'P', 'R', 'N', 'B', 'Q', 'K', 'empty']
IDX_TO_CLASS = {i: p for i, p in enumerate(PIECES)}

VAL_TRANSFORM = transforms.Compose([
    transforms.Resize((50, 50)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

# --- BOARD DETECTION HELPERS ---

def rle_1d(arr):
    if len(arr) == 0:
        return [], []
    diffs = np.diff(arr)
    change_indices = np.where(diffs != 0)[0] + 1
    indices = np.concatenate(([0], change_indices, [len(arr)]))
    lengths = np.diff(indices)
    values = arr[indices[:-1]]
    return values, lengths

def find_k_equal_segments_1d(arr, k, eps=0, min_L=10):
    values, lengths = rle_1d(arr)
    if len(lengths) < k:
        return False, None, None, None, None
    
    for i in range(len(lengths) - k + 1):
        window = lengths[i : i+k]
        if np.any(window < min_L):
            continue
        
        if (np.max(window) - np.min(window)) <= eps:
            L_avg = int(np.mean(window))
            start_seg = i
            start_pixel = np.sum(lengths[:start_seg])
            end_pixel = start_pixel + np.sum(window)
            return True, L_avg, start_seg, start_pixel, end_pixel
            
    return False, None, None, None, None

def find_board_range(img_bin, axis, k=8, eps=50, min_L=30):
    H, W = img_bin.shape
    found_ranges = []
    step = 20
    scan_limit = H if axis == 1 else W
    
    for i in range(0, scan_limit, step):
        line = img_bin[i, :] if axis == 1 else img_bin[:, i]
        found, _, _, start, end = find_k_equal_segments_1d(line, k, eps, min_L)
        if found:
            found_ranges.append((start, end))
            
    if not found_ranges:
        return None
        
    found_ranges = np.array(found_ranges)
    return int(np.median(found_ranges[:, 0])), int(np.median(found_ranges[:, 1]))

def detect_chessboard(screen_img_bgr, strict=True):
    if screen_img_bgr is None:
        return None, None
        
    gray = cv2.cvtColor(screen_img_bgr, cv2.COLOR_BGR2GRAY)
    thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                   cv2.THRESH_BINARY, 11, 2)
    
    x_range = find_board_range(thresh, axis=1)
    y_range = find_board_range(thresh, axis=0)
    
    if x_range and y_range:
        x0, x1 = x_range
        y0, y1 = y_range
        w, h = x1 - x0, y1 - y0
        
        # Aspect ratio check
        if 0.8 < w/h < 1.2:
            return screen_img_bgr[y0:y1, x0:x1], (x0, y0, w, h)
    
    if not strict:
        h, w = screen_img_bgr.shape[:2]
        return screen_img_bgr, (0, 0, w, h)
        
    return None, None

# --- AI MODEL ---

class ChessCNN(nn.Module):
    def __init__(self, num_classes=13):
        super(ChessCNN, self).__init__()
        self.features = nn.Sequential(
            nn.Conv2d(3, 32, kernel_size=3, padding=1), nn.ReLU(), nn.BatchNorm2d(32), nn.MaxPool2d(2, 2),
            nn.Conv2d(32, 64, kernel_size=3, padding=1), nn.ReLU(), nn.BatchNorm2d(64), nn.MaxPool2d(2, 2),
            nn.Conv2d(64, 128, kernel_size=3, padding=1), nn.ReLU(), nn.BatchNorm2d(128), nn.MaxPool2d(2, 2),
        )
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(128 * 6 * 6, 512), nn.ReLU(), nn.Dropout(0.5),
            nn.Linear(512, num_classes)
        )

    def forward(self, x):
        x = self.features(x)
        x = self.classifier(x)
        return x

class ChessPredictor:
    def __init__(self, model_path):
        self.model = ChessCNN().to(DEVICE)
        try:
            self.model.load_state_dict(torch.load(model_path, map_location=DEVICE))
            self.model.eval()
        except Exception as e:
            print(f"Error loading model: {e}")

    def reverse_fen_string(self, fen_row):
        expanded = ""
        for char in fen_row:
            if char.isdigit():
                expanded += "1" * int(char)
            else:
                expanded += char
                
        reversed_str = expanded[::-1]
        compressed = ""
        count = 0
        
        for char in reversed_str:
            if char == '1':
                count += 1
            else:
                if count > 0:
                    compressed += str(count)
                    count = 0
                compressed += char
                
        if count > 0:
            compressed += str(count)
        return compressed

    def predict_fen(self, board_img_bgr, is_black_view=False):
        h, w = board_img_bgr.shape[:2]
        y_steps = np.linspace(0, h, 9).astype(int)
        x_steps = np.linspace(0, w, 9).astype(int)
        
        squares_batch = []
        
        # Preprocessing: Cut 64 squares
        for row in range(8):
            for col in range(8):
                y1, y2 = y_steps[row], y_steps[row+1]
                x1, x2 = x_steps[col], x_steps[col+1]
                
                square_bgr = board_img_bgr[y1:y2, x1:x2]
                square_rgb = cv2.cvtColor(square_bgr, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(square_rgb)
                squares_batch.append(VAL_TRANSFORM(pil_img))

        # Batch Inference
        input_tensor = torch.stack(squares_batch).to(DEVICE)
        
        with torch.no_grad():
            outputs = self.model(input_tensor)
            _, preds = torch.max(outputs, 1)
            predictions = preds.cpu().numpy()

        # Post-processing: Generate FEN
        fen_rows = []
        idx = 0
        for row in range(8):
            empty_count = 0
            row_str = ""
            for col in range(8):
                piece_idx = predictions[idx]
                idx += 1
                piece = IDX_TO_CLASS[piece_idx]
                
                if piece == 'empty':
                    empty_count += 1
                else:
                    if empty_count > 0:
                        row_str += str(empty_count)
                        empty_count = 0
                    row_str += piece
                    
            if empty_count > 0:
                row_str += str(empty_count)
            fen_rows.append(row_str)
        
        if is_black_view:
            fen_rows = fen_rows[::-1]
            fen_rows = [self.reverse_fen_string(r) for r in fen_rows]

        return "/".join(fen_rows)