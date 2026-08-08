const boardElement = document.querySelector("#board");
const arrowsElement = document.querySelector("#board-arrows");
const statusElement = document.querySelector("#status");
const messageElement = document.querySelector("#message");
const openingSelect = document.querySelector("#opening-select");
const sideSelect = document.querySelector("#side-select");
const startButton = document.querySelector("#start-btn");
const resetButton = document.querySelector("#reset-btn");
const undoButton = document.querySelector("#undo-btn");
const hintButton = document.querySelector("#hint-btn");
const revealButton = document.querySelector("#reveal-btn");
const bookLineElement = document.querySelector("#book-line");
const openingNameElement = document.querySelector("#opening-name");
const openingEcoElement = document.querySelector("#opening-eco");
const evaluationElement = document.querySelector("#evaluation");
const evaluationFill = document.querySelector("#evaluation-fill");
const bestMoveElement = document.querySelector("#best-move");
const fenLabel = document.querySelector("#fen-label");
const lichessLink = document.querySelector("#lichess-link");

let openings = [];
let opening = null;
let chessGame = new Chess();
let userColor = "w";
let selectedSquare = null;
let hintArrow = null;
let busy = false;

const boardView = new ChessBoardView({
  boardEl: boardElement,
  arrowsEl: arrowsElement,
  onSquareClick: handleSquareClick,
});

function setMessage(text, kind = "") {
  messageElement.textContent = text;
  messageElement.className = `message ${kind}`;
}

function setStatus(text, active = false) {
  statusElement.textContent = text;
  statusElement.classList.toggle("active", active);
}

function sleep(ms) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

async function loadOpenings() {
  try {
    const apiBase = (window.CHESS_VISION_API_BASE || "").replace(/\/$/, "");
    const response = await fetch(`${apiBase}/api/openings`);
    const result = await response.json();
    if (!result.success) throw new Error("Không tải được danh sách khai cuộc");
    openings = result.openings;
    openingSelect.replaceChildren();
    openings.forEach((item, index) => {
      const option = document.createElement("option");
      option.value = String(index);
      option.textContent = `${item.eco} · ${item.name}`;
      openingSelect.append(option);
    });
    opening = openings[0] || null;
    updateOpeningHeading();
  } catch (error) {
    setMessage(error.message, "error");
  }
}

function updateOpeningHeading() {
  if (!opening) return;
  openingNameElement.textContent = opening.name;
  openingEcoElement.textContent = opening.eco;
}

// Returns book status for the current position: whether we're still
// following the chosen line exactly, and how many plies have been played.
function bookStatus() {
  if (!opening) return { inBook: false, ply: 0 };
  const history = chessGame.history();
  const matchLen = Math.min(history.length, opening.moves.length);
  for (let i = 0; i < matchLen; i += 1) {
    if (history[i] !== opening.moves[i]) return { inBook: false, ply: history.length };
  }
  return { inBook: history.length < opening.moves.length, ply: history.length };
}

function drawBoard() {
  boardView.setOrientation(userColor === "b");
  const squareClasses = {};
  boardView.render(chessGame, { selected: selectedSquare, arrow: hintArrow, squareClasses });
  fenLabel.textContent = chessGame.fen();
  lichessLink.href = `https://lichess.org/analysis/${chessGame.fen().replaceAll(" ", "_")}`;
  updateBookLine();
}

function updateBookLine() {
  if (!opening) {
    bookLineElement.textContent = "";
    return;
  }
  const status = bookStatus();
  if (status.inBook) {
    const remaining = opening.moves.slice(status.ply).join(" ");
    bookLineElement.textContent = `Sách: ${remaining}`;
  } else if (status.ply >= opening.moves.length && opening.moves.length > 0) {
    bookLineElement.textContent = "Đã hết sách khai cuộc — tiếp tục bằng engine.";
  } else {
    bookLineElement.textContent = "Đã ra ngoài sách khai cuộc — tiếp tục bằng engine.";
  }
}

async function fetchEval(fen) {
  const apiBase = (window.CHESS_VISION_API_BASE || "").replace(/\/$/, "");
  const response = await fetch(`${apiBase}/api/analyze-fen`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ fen, use_engine: true }),
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result.detail || "Không thể phân tích vị trí");
  return result;
}

function renderEval(result) {
  const score = result.mate === null ? Number(result.evaluation || 0) : null;
  evaluationElement.textContent = result.mate === null ? `${score >= 0 ? "+" : ""}${score.toFixed(2)}` : `M${Math.abs(result.mate)}`;
  evaluationElement.className = (score !== null ? score >= 0 : result.mate > 0) ? "positive" : "negative";
  const normalized = score === null ? (result.mate > 0 ? 1 : 0) : (Math.max(-4, Math.min(4, score)) + 4) / 8;
  evaluationFill.style.width = `${normalized * 100}%`;
  return result.best_move || null;
}

async function updateEval() {
  try {
    const result = await fetchEval(chessGame.fen());
    const engineBest = renderEval(result);
    bestMoveElement.textContent = engineBest || "—";
    return engineBest;
  } catch (error) {
    setMessage(error.message, "error");
    return null;
  }
}

function startGame() {
  const index = Number(openingSelect.value || 0);
  opening = openings[index] || null;
  userColor = sideSelect.value;
  chessGame = new Chess();
  selectedSquare = null;
  hintArrow = null;
  updateOpeningHeading();
  drawBoard();
  updateEval();
  setMessage(`Đang luyện "${opening ? opening.name : ""}". Đi nước của bạn khi đến lượt.`, "success");
  maybeOpponentMove();
}

function resetGame() {
  chessGame = new Chess();
  selectedSquare = null;
  hintArrow = null;
  drawBoard();
  updateEval();
  setMessage("Đã chơi lại từ đầu.");
  maybeOpponentMove();
}

async function maybeOpponentMove() {
  if (busy || chessGame.game_over() || chessGame.turn() === userColor) return;
  busy = true;
  setStatus("Đối thủ đang đi...", true);
  await sleep(420);

  const status = bookStatus();
  let played = null;
  if (status.inBook) {
    played = chessGame.move(opening.moves[status.ply]);
  } else {
    const bestUci = await updateEval();
    if (bestUci) {
      played = chessGame.move({
        from: bestUci.slice(0, 2),
        to: bestUci.slice(2, 4),
        promotion: bestUci.slice(4, 5) || "q",
      });
    }
  }

  hintArrow = null;
  drawBoard();
  setStatus("Sẵn sàng");
  busy = false;
  if (played) await updateEval();
  if (!chessGame.game_over() && chessGame.turn() !== userColor) {
    maybeOpponentMove();
  }
}

async function handleSquareClick(square) {
  if (busy || !opening) return;
  if (chessGame.turn() !== userColor) return;

  if (!selectedSquare) {
    const piece = chessGame.get(square);
    if (piece && piece.color === userColor) selectedSquare = square;
    drawBoard();
    return;
  }
  if (selectedSquare === square) {
    selectedSquare = null;
    drawBoard();
    return;
  }

  const move = chessGame.move({ from: selectedSquare, to: square, promotion: "q" });
  selectedSquare = null;
  if (!move) {
    const piece = chessGame.get(square);
    selectedSquare = piece && piece.color === userColor ? square : null;
    drawBoard();
    return;
  }

  hintArrow = null;
  const ply = chessGame.history().length - 1;
  const inRange = opening && ply < opening.moves.length;
  const matchesBook = inRange && chessGame.history()[ply] === opening.moves[ply];

  drawBoard();
  await updateEval();

  if (inRange && matchesBook) {
    setMessage("✅ Đúng nước khai cuộc!", "success");
  } else if (inRange && !matchesBook) {
    setMessage(`↪ Khác sách (sách gợi ý: ${opening.moves[ply]}). Từ đây engine sẽ tiếp quản đánh giá.`, "");
  } else {
    setMessage("Đã ra ngoài phạm vi khai cuộc — engine tiếp tục đánh giá vị trí.", "");
  }

  maybeOpponentMove();
}

async function showHint() {
  if (!opening) return;
  const status = bookStatus();
  if (status.inBook && chessGame.turn() === userColor) {
    hintArrow = null;
    setMessage(`Gợi ý (sách): ${opening.moves[status.ply]}`, "success");
    drawBoard();
    return;
  }
  const best = await updateEval();
  if (best) {
    hintArrow = best;
    drawBoard();
    setMessage(`Gợi ý (engine): ${best}`, "success");
  } else {
    setMessage("Không có gợi ý khả dụng.", "error");
  }
}

function revealBookMove() {
  if (!opening) return;
  const status = bookStatus();
  if (status.inBook) {
    setMessage(`📖 Nước sách tiếp theo: ${opening.moves[status.ply]}`, "success");
  } else {
    setMessage("Đã ngoài phạm vi sách khai cuộc cho ván này.", "");
  }
}

function undoMove() {
  if (busy) return;
  chessGame.undo();
  if (chessGame.turn() !== userColor && chessGame.history().length > 0) {
    chessGame.undo();
  }
  selectedSquare = null;
  hintArrow = null;
  drawBoard();
  updateEval();
  setMessage("Đã đi lại.");
}

openingSelect.addEventListener("change", () => {
  const index = Number(openingSelect.value || 0);
  opening = openings[index] || null;
  updateOpeningHeading();
});
startButton.addEventListener("click", startGame);
resetButton.addEventListener("click", resetGame);
undoButton.addEventListener("click", undoMove);
hintButton.addEventListener("click", showHint);
revealButton.addEventListener("click", revealBookMove);
document.querySelector("#flip-board").addEventListener("click", () => {
  userColor = userColor === "w" ? "b" : "w";
  sideSelect.value = userColor;
  drawBoard();
});

loadOpenings().then(() => drawBoard());
