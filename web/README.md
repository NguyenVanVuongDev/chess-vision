# Chess Vision Web

## Mo hinh mien phi

- Render phuc vu ca giao dien web va backend AI.
- FastAPI, PyTorch, OpenCV va Stockfish chay tren Render.
- Khong can Vercel, domain rieng hoac Cloudflare Tunnel.

Model khong chay tren Vercel vi PyTorch vuot gioi han Serverless Function. Khong can chuyen sang C++.

URL hien tai: `https://chess-vision-wthy.onrender.com`.

## 1. Cai Python va dependencies

Mo PowerShell tai thu muc `chess-vision`:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-web.txt
```

Neu PowerShell chan script, dung lenh truc tiep voi `.venv\Scripts\python.exe` nhu tren, khong can activate moi truong.

## 2. Chay backend local

Mo PowerShell thu nhat:

```powershell
.\start-backend.ps1
```

Kiem tra bang trinh duyet: `http://127.0.0.1:8000/api/health`.
Can thay `model_loaded: true` va `stockfish_available: true`.

## 3. Deploy Render

Tao **Web Service** tu repository GitHub, chon runtime **Docker**, Dockerfile
`Dockerfile`, context `.`, va health check `/api/health`. Render se cap URL:
`https://chess-vision-wthy.onrender.com`.

Frontend da duoc cau hinh trong [static/config.js](static/config.js) de goi
thang URL Render, khong can Vercel, domain rieng hay Cloudflare Tunnel.

Push len GitHub:

```powershell
git add .
git commit -m "Use Render for web and AI backend"
git push
```

Render tu deploy lai. Mo URL Render, bam **Chia se man hinh** va chon cua so co ban co.

## Moi lan su dung

1. Khong can bat may local.
2. Render Free co the sleep khi khong co request; request dau tien sau do co the cham.
3. Kiem tra `https://chess-vision-wthy.onrender.com/api/health`.

## Luu y

Render Free khong bao dam uptime va co the mat 30-60 giay de wake up. Neu
nhieu nguoi cung quet, PyTorch va Stockfish co the cham hoac het RAM.
