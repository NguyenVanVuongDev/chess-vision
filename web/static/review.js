const boardElement = document.querySelector("#board");
const arrowsElement = document.querySelector("#board-arrows");
const statusElement = document.querySelector("#status");
const messageElement = document.querySelector("#message");
const pgnInput = document.querySelector("#pgn-input");
const analyzeButton = document.querySelector("#analyze-btn");
const clearButton = document.querySelector("#clear-btn");
const resultsSection = document.querySelector("#review-results");
const moveListElement = document.querySelector("#move-list");
const moveLabelElement = document.querySelector("#review-move-label");
const fenLabel = document.querySelector("#fen-label");
const whiteAccuracyElement = document.querySelector("#white-accuracy");
const blackAccuracyElement = document.querySelector("#black-accuracy");
const summaryCountsElement = document.querySelector("#summary-counts");
const evalGraph = document.querySelector("#eval-graph");

const CLASS_LABELS = {
  brilliant: "Đẹp",
  good: "Tốt",
  ok: "Bình thường",
  inaccuracy: "Thiếu chính xác",
  mistake: "Sai lầm",
  blunder: "Đại sai lầm",
};
const CLASS_ORDER = ["brilliant", "good", "ok", "inaccuracy", "mistake", "blunder"];

let chessGame = new Chess();
let reviewData = null;
let blackView = false;
let activePly = 0;

const boardView = new ChessBoardView({ boardEl: boardElement, arrowsEl: arrowsElement });

function setMessage(text, kind = "") {
  messageElement.textContent = text;
  messageElement.className = `message ${kind}`;
}

function setStatus(text, active = false) {
  statusElement.textContent = text;
  statusElement.classList.toggle("active", active);
}

async function analyzeGame() {
  const pgn = pgnInput.value.trim();
  if (!pgn) {
    setMessage("Hãy dán PGN của ván đấu trước.", "error");
    return;
  }
  analyzeButton.disabled = true;
  setStatus("Đang phân tích...", true);
  setMessage("Đang chạy Stockfish qua từng nước, vui lòng đợi...");

  try {
    const response = await fetch("/api/analyze-game", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pgn }),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || "Không thể phân tích ván đấu");
    reviewData = result;
    activePly = 0;
    renderSummary();
    renderMoveList();
    renderEvalGraph();
    jumpTo(0);
    resultsSection.hidden = false;
    setMessage(`Đã phân tích ${reviewData.moves.length} nước đi.`, "success");
  } catch (error) {
    setMessage(error.message, "error");
  } finally {
    analyzeButton.disabled = false;
    setStatus("Sẵn sàng");
  }
}

function renderSummary() {
  const { white, black } = reviewData.summary;
  whiteAccuracyElement.textContent = `${white.accuracy.toFixed(1)}%`;
  blackAccuracyElement.textContent = `${black.accuracy.toFixed(1)}%`;

  summaryCountsElement.replaceChildren();
  CLASS_ORDER.forEach((key) => {
    const row = document.createElement("div");
    row.className = `count-row class-${key}`;
    row.innerHTML = `<span>${CLASS_LABELS[key]}</span><span>${white.counts[key] || 0} · ${black.counts[key] || 0}</span>`;
    summaryCountsElement.append(row);
  });
}

function renderMoveList() {
  moveListElement.replaceChildren();
  reviewData.moves.forEach((move, index) => {
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = `move-chip class-${move.classification}`;
    chip.dataset.ply = String(index + 1);
    const prefix = move.color === "w" ? `${move.move_number}.` : `${move.move_number}...`;
    chip.innerHTML = `<span class="move-num">${prefix}</span><span class="move-san">${move.san}</span>`;
    chip.title = CLASS_LABELS[move.classification];
    chip.addEventListener("click", () => jumpTo(index + 1));
    moveListElement.append(chip);
  });
}

function renderEvalGraph() {
  evalGraph.replaceChildren();
  const evals = reviewData.evals;
  if (!evals || evals.length < 2) return;

  const clamp = (v) => Math.max(-8, Math.min(8, v / 100));
  const points = evals.map((cp, i) => {
    const x = (i / (evals.length - 1)) * 100;
    const y = 15 - clamp(cp) * (15 / 8);
    return `${x},${y}`;
  });

  const mid = document.createElementNS("http://www.w3.org/2000/svg", "line");
  mid.setAttribute("x1", "0"); mid.setAttribute("x2", "100");
  mid.setAttribute("y1", "15"); mid.setAttribute("y2", "15");
  mid.setAttribute("class", "eval-graph-mid");
  evalGraph.append(mid);

  const polyline = document.createElementNS("http://www.w3.org/2000/svg", "polyline");
  polyline.setAttribute("points", points.join(" "));
  polyline.setAttribute("class", "eval-graph-line");
  evalGraph.append(polyline);
}

function jumpTo(ply) {
  activePly = ply;
  const fen = ply === 0 ? new Chess().fen() : reviewData.moves[ply - 1].fen_after;
  chessGame = new Chess(fen);
  boardView.setOrientation(blackView);

  const move = ply > 0 ? reviewData.moves[ply - 1] : null;
  const arrow = move && move.best_move ? move.best_move : null;
  boardView.render(chessGame, { arrow });
  fenLabel.textContent = fen;

  moveLabelElement.textContent = move
    ? `${move.move_number}${move.color === "w" ? "." : "..."} ${move.san} — ${CLASS_LABELS[move.classification]}`
    : "Vị trí ban đầu";

  document.querySelectorAll(".move-chip").forEach((chip) => {
    chip.classList.toggle("active", Number(chip.dataset.ply) === ply);
  });
}

clearButton.addEventListener("click", () => {
  pgnInput.value = "";
  resultsSection.hidden = true;
  reviewData = null;
  setMessage("Dán PGN rồi bấm Phân tích ván đấu để bắt đầu.");
});
analyzeButton.addEventListener("click", analyzeGame);
document.addEventListener("click", (event) => {
  if (event.target && event.target.id === "flip-board") {
    blackView = !blackView;
    if (reviewData) jumpTo(activePly);
  }
});
