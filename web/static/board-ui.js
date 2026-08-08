// Shared chessboard renderer: draws the 8x8 grid + an SVG best-move arrow,
// and is orientation-aware (works whether the user is viewing as White or Black).
// Loaded as a plain <script> (no bundler in this project), exposes window.ChessBoardView.

const SVG_NS = "http://www.w3.org/2000/svg";

function svgEl(tag, attrs) {
  const el = document.createElementNS(SVG_NS, tag);
  Object.entries(attrs).forEach(([key, value]) => el.setAttribute(key, value));
  return el;
}

function pieceImagePath(color, type) {
  const names = {
    wk: "Chess_klt45", bk: "Chess_kdt45",
    wq: "Chess_qlt45", bq: "Chess_qdt45",
    wr: "Chess_rlt45", br: "Chess_rdt45",
    wb: "Chess_blt45", bb: "Chess_bdt45",
    wn: "Chess_nlt45", bn: "Chess_ndt45",
    wp: "Chess_plt45", bp: "Chess_pdt45",
  };
  return `/pieces/${names[`${color}${type}`]}.png`;
}

class ChessBoardView {
  constructor({ boardEl, arrowsEl, onSquareClick = null }) {
    this.boardEl = boardEl;
    this.arrowsEl = arrowsEl;
    this.onSquareClick = onSquareClick;
    this.blackView = false;
  }

  setOrientation(blackView) {
    this.blackView = blackView;
  }

  squareCenter(square) {
    const file = "abcdefgh".indexOf(square[0]);
    const rank = Number(square[1]) - 1;
    const displayCol = this.blackView ? 7 - file : file;
    const displayRow = this.blackView ? rank : 7 - rank;
    return { x: displayCol + 0.5, y: displayRow + 0.5 };
  }

  // opts: { selected, arrow, squareClasses: { e4: 'hint-from', ... } }
  render(chessInstance, opts = {}) {
    const { selected = null, arrow = null, squareClasses = {} } = opts;
    this.boardEl.replaceChildren();
    const position = chessInstance.board();

    for (let displayRank = 0; displayRank < 8; displayRank += 1) {
      for (let displayFile = 0; displayFile < 8; displayFile += 1) {
        const file = this.blackView ? 7 - displayFile : displayFile;
        const rank = this.blackView ? displayRank : 7 - displayRank;
        const square = "abcdefgh"[file] + (rank + 1);
        const tile = document.createElement("button");
        tile.type = "button";
        tile.className = `square ${(file + rank) % 2 ? "dark" : "light"}`;
        tile.dataset.square = square;
        tile.setAttribute("aria-label", square);

        if (selected === square) tile.classList.add("selected");
        if (squareClasses[square]) tile.classList.add(squareClasses[square]);
        if (arrow && (arrow.slice(0, 2) === square || arrow.slice(2, 4) === square)) {
          tile.classList.add(arrow.slice(0, 2) === square ? "hint-from" : "hint-to");
        }

        const boardRow = 7 - rank;
        const piece = position[boardRow][file];
        if (piece) {
          const pieceElement = document.createElement("img");
          pieceElement.className = "piece";
          pieceElement.src = pieceImagePath(piece.color, piece.type);
          pieceElement.alt = `${piece.color === "w" ? "Trắng" : "Đen"} ${piece.type}`;
          tile.append(pieceElement);
        }
        if (this.onSquareClick) tile.addEventListener("click", () => this.onSquareClick(square));
        this.boardEl.append(tile);
      }
    }

    this.drawArrow(arrow);
  }

  drawArrow(uci, colorVar = "var(--orange)") {
    if (!this.arrowsEl) return;
    this.arrowsEl.replaceChildren();
    if (!uci) return;

    const from = this.squareCenter(uci.slice(0, 2));
    const to = this.squareCenter(uci.slice(2, 4));
    const dx = to.x - from.x;
    const dy = to.y - from.y;
    const length = Math.hypot(dx, dy);
    if (length === 0) return;

    const unitX = dx / length;
    const unitY = dy / length;
    const headLength = 0.34;
    const startPad = 0.32;
    const start = { x: from.x + unitX * startPad, y: from.y + unitY * startPad };
    const end = { x: to.x - unitX * headLength * 0.7, y: to.y - unitY * headLength * 0.7 };

    const defs = svgEl("defs", {});
    const marker = svgEl("marker", {
      id: `arrowhead-${Math.random().toString(36).slice(2, 8)}`,
      viewBox: "0 0 10 10",
      refX: "8.5",
      refY: "5",
      markerWidth: "5.4",
      markerHeight: "5.4",
      orient: "auto-start-reverse",
    });
    const head = svgEl("path", { d: "M0,0 L10,5 L0,10 L2.8,5 Z" });
    head.style.fill = colorVar;
    marker.append(head);
    defs.append(marker);

    const line = svgEl("line", {
      x1: start.x,
      y1: start.y,
      x2: end.x,
      y2: end.y,
      class: "arrow-line",
      "marker-end": `url(#${marker.id})`,
    });
    line.style.stroke = colorVar;

    this.arrowsEl.append(defs, line);
  }
}

window.ChessBoardView = ChessBoardView;
window.pieceImagePath = pieceImagePath;
