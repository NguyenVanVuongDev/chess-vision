const boardElement = document.querySelector("#board");
const arrowsElement = document.querySelector("#board-arrows");
const videoElement = document.querySelector("#screen-preview");
const canvasElement = document.querySelector("#capture-canvas");
const statusElement = document.querySelector("#status");
const messageElement = document.querySelector("#message");
const scanButton = document.querySelector("#scan-now");
const autoButton = document.querySelector("#auto-scan");
const shareButton = document.querySelector("#share-screen");
const stopButton = document.querySelector("#stop-sharing");
const turnSelect = document.querySelector("#turn");
const useEngine = document.querySelector("#use-engine");
const delayInput = document.querySelector("#delay");
const evaluationElement = document.querySelector("#evaluation");
const evaluationFill = document.querySelector("#evaluation-fill");
const bestMoveElement = document.querySelector("#best-move");
const fenLabel = document.querySelector("#fen-label");
const lichessLink = document.querySelector("#lichess-link");
const API_BASE = (window.CHESS_VISION_API_BASE || "").replace(/\/$/, "");

let stream = null;
let autoTimer = null;
let board = new Chess();
let bestMove = null;
let selectedSquare = null;

const boardView = new ChessBoardView({
  boardEl: boardElement,
  arrowsEl: arrowsElement,
  onSquareClick: handleSquareClick,
});

function isBlackView() {
  return turnSelect.value === "b";
}

function setMessage(text, kind = "") {
  messageElement.textContent = text;
  messageElement.className = `message ${kind}`;
}

function setStatus(text, active = false) {
  statusElement.textContent = text;
  statusElement.classList.toggle("active", active);
}

function drawBoard() {
  boardView.setOrientation(isBlackView());
  boardView.render(board, { selected: selectedSquare, arrow: bestMove });
  fenLabel.textContent = board.fen();
  lichessLink.href = `https://lichess.org/analysis/${board.fen().replaceAll(" ", "_")}`;
}

async function shareScreen() {
  try {
    stream = await navigator.mediaDevices.getDisplayMedia({ video: true, audio: false });
    videoElement.srcObject = stream;
    videoElement.classList.add("visible");
    stream.getVideoTracks()[0].addEventListener("ended", stopSharing);
    scanButton.disabled = false;
    autoButton.disabled = false;
    shareButton.disabled = true;
    stopButton.disabled = false;
    setStatus("Đang chia sẻ", true);
    setMessage("Đã kết nối màn hình. Hãy quét để nhận diện bàn cờ.");
  } catch (error) {
    setMessage("Không thể chia sẻ màn hình hoặc bạn đã hủy quyền.", "error");
  }
}

function stopSharing() {
  stopAutoScan();
  if (stream) stream.getTracks().forEach((track) => track.stop());
  stream = null;
  videoElement.srcObject = null;
  videoElement.classList.remove("visible");
  scanButton.disabled = true;
  autoButton.disabled = true;
  shareButton.disabled = false;
  stopButton.disabled = true;
  setStatus("Đã dừng");
  setMessage("Hãy chia sẻ lại màn hình để tiếp tục.");
}

async function captureAndAnalyze() {
  if (!stream || videoElement.readyState < 2) return;
  if (!API_BASE) {
    setMessage("Chưa cấu hình backend AI trong static/config.js.", "error");
    return;
  }
  scanButton.disabled = true;
  setStatus("Đang phân tích", true);

  canvasElement.width = videoElement.videoWidth;
  canvasElement.height = videoElement.videoHeight;
  canvasElement.getContext("2d").drawImage(videoElement, 0, 0);

  const blob = await new Promise((resolve) => canvasElement.toBlob(resolve, "image/jpeg", 0.82));
  const form = new FormData();
  form.append("image", blob, "screen.jpg");
  form.append("turn", turnSelect.value);
  form.append("black_view", String(isBlackView()));
  form.append("use_engine", String(useEngine.checked));

  try {
    const response = await fetch(`${API_BASE}/api/analyze`, { method: "POST", body: form });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || "API lỗi");
    if (!result.success) {
      setMessage(result.message, "error");
      return;
    }
    board = new Chess(result.fen);
    bestMove = result.best_move;
    selectedSquare = null;
    renderAnalysis(result);
    setMessage("Đã nhận diện và cập nhật vị trí.", "success");
  } catch (error) {
    setMessage(error.message, "error");
  } finally {
    scanButton.disabled = false;
    setStatus("Đang chia sẻ", true);
  }
}

function renderAnalysis(result) {
  const score = result.mate === null ? Number(result.evaluation || 0) : null;
  evaluationElement.textContent = result.mate === null ? `${score >= 0 ? "+" : ""}${score.toFixed(2)}` : `M${Math.abs(result.mate)}`;
  evaluationElement.className = (score !== null ? score >= 0 : result.mate > 0) ? "positive" : "negative";
  const normalized = score === null ? (result.mate > 0 ? 1 : 0) : (Math.max(-4, Math.min(4, score)) + 4) / 8;
  evaluationFill.style.width = `${normalized * 100}%`;
  bestMoveElement.textContent = result.best_move || "—";
  drawBoard();
}

function startAutoScan() {
  if (autoTimer || !stream) return;
  autoButton.textContent = "Tự động: Bật";
  autoButton.classList.add("running");
  captureAndAnalyze();
  autoTimer = window.setInterval(captureAndAnalyze, Math.max(1, Number(delayInput.value) || 2) * 1000);
}

function stopAutoScan() {
  if (autoTimer) window.clearInterval(autoTimer);
  autoTimer = null;
  autoButton.textContent = "Tự động: Tắt";
  autoButton.classList.remove("running");
}

function toggleAutoScan() {
  if (autoTimer) stopAutoScan();
  else startAutoScan();
}

async function analyzeCurrentPosition() {
  if (!API_BASE) {
    setMessage("Chưa cấu hình backend AI trong static/config.js.", "error");
    return;
  }
  try {
    const response = await fetch(`${API_BASE}/api/analyze-fen`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ fen: board.fen(), use_engine: useEngine.checked })
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || "Không thể phân tích vị trí");
    bestMove = result.best_move;
    renderAnalysis(result);
  } catch (error) {
    setMessage(error.message, "error");
  }
}

function handleSquareClick(square) {
  if (!selectedSquare) {
    if (board.get(square)) selectedSquare = square;
  } else if (selectedSquare === square) {
    selectedSquare = null;
  } else {
    const move = board.move({ from: selectedSquare, to: square, promotion: "q" });
    if (move) {
      selectedSquare = null;
      bestMove = null;
      drawBoard();
      analyzeCurrentPosition();
      return;
    }
    selectedSquare = board.get(square) ? square : null;
  }
  drawBoard();
}

shareButton.addEventListener("click", shareScreen);
stopButton.addEventListener("click", stopSharing);
scanButton.addEventListener("click", captureAndAnalyze);
autoButton.addEventListener("click", toggleAutoScan);
document.querySelector("#flip-board").addEventListener("click", () => {
  turnSelect.value = isBlackView() ? "w" : "b";
  drawBoard();
  if (stream) captureAndAnalyze();
});
turnSelect.addEventListener("change", () => {
  if (stream) captureAndAnalyze();
});

window.addEventListener("beforeunload", stopSharing);
drawBoard();
