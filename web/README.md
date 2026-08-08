# Chess Vision Web

## Deploy Vercel

Vercel chi phuc vu giao dien tinh. Backend FastAPI can chay tren Render, Railway
hoac mot may chu Python khac vi PyTorch va Stockfish vuot gioi han Serverless
Function cua Vercel.

Sau khi co URL backend, thay gia tri `window.CHESS_VISION_API_BASE` trong
`web/static/index.html`, `opening.html` va `review.html` bang URL do, vi du:

```html
<script>window.CHESS_VISION_API_BASE = "https://your-backend.example.com";</script>
```

Ban web thay cho giao dien Tkinter. Trinh duyet se chia se cua so/man hinh bang `getDisplayMedia()`, sau do gui frame ve FastAPI de OpenCV va PyTorch nhan dien ban co.

## Cai dat

Mo PowerShell tai thu muc `chess-vision`:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-web.txt
```

Neu PowerShell chan kich hoat moi truong ao, co the chay truc tiep:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-web.txt
```

## Chay

```powershell
.\.venv\Scripts\python.exe -m uvicorn web.server:app --reload
```

Mo `http://127.0.0.1:8000` tren trinh duyet, bam **Chia se man hinh**, roi chon cua so dang mo ban co.

## Luu y

- `chess_model_best.pth` va `stockfish.exe` phai nam o thu muc goc `chess-vision`.
- Trinh duyet chi cho phep chia se man hinh tren `localhost`/`127.0.0.1` hoac HTTPS.
- Neu nhan dien khong tim thay ban co, hay chon chia se cua so ban co thay vi chia se mot tab khong chua ban co.
- File `main.py` cu van duoc giu lai; ban web chay doc lap qua `web.server:app`.
