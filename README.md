# Chess Vision

Ứng dụng nhận diện bàn cờ từ màn hình bằng PyTorch/OpenCV và phân tích bằng Stockfish.

## Deploy Render

Repository này chạy dưới dạng Docker Web Service trên Render.

1. Tạo **New Web Service** từ repository GitHub.
2. Runtime: **Docker**.
3. Dockerfile: `Dockerfile`.
4. Docker Context: thư mục gốc repository.
5. Health Check Path: `/api/health`.
6. Có thể dùng cấu hình trong `render.yaml`.

Render sẽ cấp URL dạng:

```text
https://your-service.onrender.com
```

Mở URL đó để dùng cả giao diện và backend. Không cần Vercel, domain riêng hoặc Cloudflare Tunnel.

Kiểm tra backend:

```text
https://your-service.onrender.com/api/health
```

Kết quả cần có:

```json
{
  "success": true,
  "model_loaded": true,
  "stockfish_available": true
}
```

## Cấu trúc runtime

- `Dockerfile`: image triển khai Render.
- `requirements-backend.txt`: dependencies Python trong Docker.
- `web/server.py`: FastAPI backend và các route giao diện.
- `core.py`: OpenCV và PyTorch model.
- `chess_model_best.pth`: model nhận diện.
- `pieces/`: ảnh PNG quân cờ.
- Docker cài Stockfish Linux tự động trong image.

## Chạy local tùy chọn

Nếu cần kiểm tra trước khi push, cài dependencies backend và chạy:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-backend.txt
.\.venv\Scripts\python.exe -m uvicorn web.server:app --host 127.0.0.1 --port 8000
```

Render Free có thể sleep khi không có request; lần truy cập đầu tiên sau đó có thể mất 30-60 giây. PyTorch và Stockfish cũng có thể chậm hoặc thiếu RAM nếu có nhiều người dùng đồng thời.
