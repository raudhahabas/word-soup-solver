"use strict";

// ---------------------------------------------------------------------------
// Game rules (same as src/wordsoup/scoring.py and board.py)
// ---------------------------------------------------------------------------
const POINTS = {
  a: 1, e: 1, o: 1, r: 1, s: 1, t: 1, d: 2, g: 2, n: 2, u: 2, b: 3, c: 3, i: 3, m: 3, p: 3,
  f: 4, h: 4, v: 4, w: 4, y: 4, k: 5, l: 5, j: 8, x: 8, q: 10, z: 10,
};
const CLEAR_BONUS = 500;
const ROWS = 12, COLS = 9;

const scoreWord = (w) => (w.length < 3 ? 0 : w.length * [...w].reduce((s, c) => s + (POINTS[c] || 0), 0));
const adjacent = (a, b) => Math.max(Math.abs(a[0] - b[0]), Math.abs(a[1] - b[1])) === 1;

// Drop down each column, then slide right along each row. Works on any 2D array with nulls.
function applyGravity(g) {
  const m = g.length, n = g[0].length;
  for (let c = 0; c < n; c++) {
    const col = [];
    for (let r = 0; r < m; r++) if (g[r][c] !== null) col.push(g[r][c]);
    for (let r = m - 1; r >= 0; r--) g[r][c] = col.length ? col.pop() : null;
  }
  for (let r = 0; r < m; r++) {
    const row = g[r].filter((v) => v !== null);
    for (let c = n - 1; c >= 0; c--) g[r][c] = row.length ? row.pop() : null;
  }
}

// ---------------------------------------------------------------------------
// Players
// ---------------------------------------------------------------------------
const PLAYERS = {
  random: {
    name: "Random", color: "var(--p-random)",
    desc: "Baseline: picks any playable word at random. Shows what happens with no strategy at all.",
  },
  greedy1: {
    name: "Greedy-1", color: "var(--p-greedy1)",
    desc: "Always plays the highest-scoring word available right now. Fast, but it often uses up all the vowels and gets stuck.",
  },
  greedy2: {
    name: "Greedy-2", color: "var(--p-greedy2)",
    desc: "Looks 2 moves ahead (top 20 words per step) and commits to the best pair. Prefers lines that clear the board.",
  },
  greedy3: {
    name: "Greedy-3", color: "var(--p-greedy3)",
    desc: "Looks 3 moves ahead. Much slower, and only clears a few more boards than Greedy-1.",
  },
  hybrid: {
    name: "Hybrid", color: "var(--p-hybrid)",
    desc: "Shortlists the 20 best moves, plays each one out to the end with a fast greedy policy, then picks the line that clears the board with the most points.",
  },
};

// ---------------------------------------------------------------------------
// Board view: absolutely positioned tiles so gravity can animate
// ---------------------------------------------------------------------------
class Board {
  constructor(el) {
    this.el = el;
  }

  load(rows) {
    this.el.innerHTML = "";
    this.svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    this.svg.setAttribute("viewBox", `0 0 ${COLS} ${ROWS}`);
    this.svg.setAttribute("preserveAspectRatio", "none");
    this.el.appendChild(this.svg);
    this.tiles = new Map();
    this.ids = rows.map((row, r) => [...row].map((ch, c) => {
      if (ch === ".") return null;
      const id = r * COLS + c;
      const el = document.createElement("div");
      el.className = "tile";
      el.innerHTML = `${ch.toUpperCase()}<sub>${POINTS[ch] ?? ""}</sub>`;
      this.el.appendChild(el);
      this.tiles.set(id, { letter: ch, el });
      return id;
    }));
    this.layout();
  }

  setCell(px) {
    this.cell = px;
    this.el.style.setProperty("--cell", px + "px");
    this.layout();
  }

  layout() {
    if (!this.ids) return;
    const cell = this.cell || 44;
    this.ids.forEach((row, r) => row.forEach((id, c) => {
      if (id === null) return;
      this.tiles.get(id).el.style.transform = `translate(${c * cell}px, ${r * cell}px)`;
    }));
  }

  letter(r, c) {
    const id = this.ids[r]?.[c];
    return id === null || id === undefined ? null : this.tiles.get(id).letter;
  }

  letters() {
    return this.ids.map((row) => row.map((id) => (id === null ? null : this.tiles.get(id).letter)));
  }

  tilesLeft() {
    return this.ids.flat().filter((id) => id !== null).length;
  }

  highlight(path, cls = "sel") {
    this.el.querySelectorAll(".tile." + cls).forEach((t) => t.classList.remove(cls));
    for (const [r, c] of path) {
      const id = this.ids[r][c];
      if (id !== null) this.tiles.get(id).el.classList.add(cls);
    }
    if (cls === "sel") this.drawLine(path);
  }

  drawLine(path) {
    this.svg.innerHTML = path.length < 2 ? "" :
      `<polyline points="${path.map(([r, c]) => `${c + 0.5},${r + 0.5}`).join(" ")}"
        fill="none" stroke="var(--line)" stroke-width="0.1" stroke-linecap="round" stroke-linejoin="round"/>`;
  }

  // Remove the tiles on `path`, then let the rest fall. Resolves when the animation is done.
  removePath(path, ms) {
    this.svg.innerHTML = "";
    for (const [r, c] of path) {
      const id = this.ids[r][c];
      const t = this.tiles.get(id);
      t.el.classList.add("gone");
      setTimeout(() => t.el.remove(), 200);
      this.tiles.delete(id);
      this.ids[r][c] = null;
    }
    applyGravity(this.ids);
    this.el.style.setProperty("--fall", ms + "ms");
    return new Promise((resolve) => setTimeout(() => { this.layout(); setTimeout(resolve, ms); }, 120));
  }

  cellAt(clientX, clientY, strict) {
    const rect = this.el.getBoundingClientRect();
    const x = (clientX - rect.left - 6) / this.cell, y = (clientY - rect.top - 6) / this.cell;
    const r = Math.floor(y), c = Math.floor(x);
    if (r < 0 || r >= ROWS || c < 0 || c >= COLS || this.ids[r][c] === null) return null;
    // While dragging, only count the middle of a tile so diagonal moves are easy.
    if (strict && Math.hypot(x - c - 0.5, y - r - 0.5) > 0.42) return null;
    return [r, c];
  }
}

function fitBoards(boards) {
  const avail = Math.min(window.innerWidth - 32, 480);
  const cell = Math.max(28, Math.min(44, Math.floor((avail - 12) / COLS)));
  boards.forEach((b) => b.setCell(cell));
}

// ---------------------------------------------------------------------------
// Dictionary for "Your turn": a sorted word list with binary search for prefixes
// ---------------------------------------------------------------------------
class Dictionary {
  constructor(words) {
    this.words = words;
    this.set = new Set(words);
  }

  has(w) { return this.set.has(w); }

  hasPrefix(p) {
    let lo = 0, hi = this.words.length;
    while (lo < hi) {
      const mid = (lo + hi) >> 1;
      if (this.words[mid] < p) lo = mid + 1; else hi = mid;
    }
    return lo < this.words.length && this.words[lo].startsWith(p);
  }

  // All playable words on a grid of letters: Map word -> list of paths.
  findAll(g) {
    const found = new Map();
    const seen = g.map((row) => row.map(() => false));
    const path = [];
    const dfs = (r, c, prefix) => {
      prefix += g[r][c];
      if (!this.hasPrefix(prefix)) return;
      seen[r][c] = true;
      path.push([r, c]);
      if (prefix.length >= 3 && this.set.has(prefix)) {
        if (!found.has(prefix)) found.set(prefix, []);
        found.get(prefix).push(path.slice());
      }
      for (let dr = -1; dr <= 1; dr++) for (let dc = -1; dc <= 1; dc++) {
        const rr = r + dr, cc = c + dc;
        if ((dr || dc) && rr >= 0 && rr < ROWS && cc >= 0 && cc < COLS && !seen[rr][cc] && g[rr][cc]) dfs(rr, cc, prefix);
      }
      path.pop();
      seen[r][c] = false;
    };
    for (let r = 0; r < ROWS; r++) for (let c = 0; c < COLS; c++) if (g[r][c]) dfs(r, c, "");
    return found;
  }
}

// ---------------------------------------------------------------------------
// App
// ---------------------------------------------------------------------------
const $ = (id) => document.getElementById(id);
const fmtTime = (s) => (s < 1 ? "< 1 s" : s < 60 ? `${s.toFixed(1)} s` : `${Math.floor(s / 60)} m ${Math.round(s % 60)} s`);

const state = { data: null, grid: null, policy: "hybrid", tab: "watch" };
const watchBoard = new Board($("watch-board"));
const playBoard = new Board($("play-board"));

// ---- Watch ----------------------------------------------------------------
const watch = { idx: 0, score: 0, playing: false, busy: false, run: 0 };

function speed() { return parseFloat($("speed").value); }

function resetWatch() {
  watch.run++;
  watch.idx = 0;
  watch.score = 0;
  watch.playing = false;
  watch.busy = false;
  watchBoard.load(state.grid.rows);
  $("watch-moves").innerHTML = "";
  $("watch-score").textContent = "0";
  $("watch-tiles").textContent = watchBoard.tilesLeft();
  setStatus("watch-status", `${PLAYERS[state.policy].name}: ${state.grid.games[state.policy].moves.length} words. Press Play.`);
  $("btn-play").textContent = "Play";
  $("btn-play").disabled = $("btn-step").disabled = false;
}

function setStatus(id, text, cls = "") {
  const el = $(id);
  el.textContent = text;
  el.className = "status " + cls;
}

function addMove(listId, n, word, pts) {
  const list = $(listId);
  list.querySelector(".latest")?.classList.remove("latest");
  const li = document.createElement("li");
  li.className = "latest";
  li.innerHTML = `<span><span class="n">${n}.</span><span class="w">${word.toUpperCase()}</span></span><span>+${pts}</span>`;
  list.appendChild(li);
  list.scrollTop = list.scrollHeight;
}

function addBonus(listId) {
  const li = document.createElement("li");
  li.className = "bonus";
  li.innerHTML = `<span>Board cleared</span><span>+${CLEAR_BONUS}</span>`;
  $(listId).appendChild(li);
  $(listId).scrollTop = $(listId).scrollHeight;
}

async function stepWatch() {
  const game = state.grid.games[state.policy];
  if (watch.busy || watch.idx >= game.moves.length) return;
  watch.busy = true;
  const run = watch.run;
  const [word, path, pts] = game.moves[watch.idx];
  const spelled = path.map(([r, c]) => watchBoard.letter(r, c)).join("");
  if (spelled !== word) console.warn(`Replay mismatch at move ${watch.idx + 1}: ${spelled} != ${word}`);

  const s = speed();
  watchBoard.highlight(path);
  setStatus("watch-status", `${word.toUpperCase()}  +${pts}`);
  await sleep(650 / s);
  if (run !== watch.run) return;
  await watchBoard.removePath(path, 380 / s);
  if (run !== watch.run) return;

  watch.idx++;
  watch.score += pts;
  addMove("watch-moves", watch.idx, word, pts);
  $("watch-score").textContent = watch.score;
  $("watch-tiles").textContent = watchBoard.tilesLeft();
  watch.busy = false;

  if (watch.idx >= game.moves.length) return finishWatch(game);
  if (watch.playing) {
    await sleep(250 / s);
    if (run === watch.run && watch.playing) stepWatch();
  }
}

function finishWatch(game) {
  watch.playing = false;
  $("btn-play").textContent = "Play";
  $("btn-play").disabled = $("btn-step").disabled = true;
  if (game.cleared) {
    watch.score += CLEAR_BONUS;
    addBonus("watch-moves");
    $("watch-score").textContent = watch.score;
    setStatus("watch-status", `Board cleared! Final score ${watch.score}.`, "good");
  } else {
    setStatus("watch-status", `Stuck: no words left, ${watchBoard.tilesLeft()} tiles remain. Final score ${watch.score}.`, "bad");
  }
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function renderPlayers() {
  const wrap = $("player-buttons");
  wrap.innerHTML = "";
  for (const [key, p] of Object.entries(PLAYERS)) {
    const b = document.createElement("button");
    b.setAttribute("role", "radio");
    b.setAttribute("aria-checked", String(key === state.policy));
    b.style.setProperty("--pc", p.color);
    b.innerHTML = `<span class="dot"></span>${p.name}`;
    b.onclick = () => selectPolicy(key);
    wrap.appendChild(b);
  }
  $("player-desc").textContent = PLAYERS[state.policy].desc;
}

function selectPolicy(key) {
  state.policy = key;
  renderPlayers();
  renderCompare();
  resetWatch();
}

function renderCompare() {
  const g = state.grid;
  const rows = Object.entries(PLAYERS).map(([key, p]) => ({ key, ...p, ...g.games[key], words: g.games[key].moves.length }));
  if (g.expert_score !== null) {
    rows.push({ key: "expert", name: "Human expert", color: "var(--p-expert)", score: g.expert_score, cleared: g.expert_cleared, words: g.expert_words, seconds: null });
  }
  const best = Math.max(...rows.map((r) => r.score));
  $("compare-body").innerHTML = rows.map((r) => `
    <tr class="${r.score === best ? "best" : ""}" ${r.key in PLAYERS ? `data-key="${r.key}" style="cursor:pointer"` : ""}>
      <td><span class="name" style="--pc:${r.color}"><span class="dot"></span>${r.name}</span></td>
      <td class="${r.cleared ? "yes" : "no"}">${r.cleared === undefined || r.cleared === null ? "–" : r.cleared ? "Yes" : "No"}</td>
      <td>${r.words ?? "–"}</td>
      <td class="num">${r.score.toLocaleString()}</td>
      <td class="num">${r.seconds === null ? "–" : fmtTime(r.seconds)}</td>
    </tr>`).join("");
  $("compare-body").querySelectorAll("tr[data-key]").forEach((tr) => (tr.onclick = () => selectPolicy(tr.dataset.key)));
  $("compare-note").textContent = g.expert_score !== null
    ? "Human expert scores come from games played in the real app, which uses a larger dictionary than the ENABLE list these AI players use here. Treat the comparison as a rough guide. Click a row to watch that player."
    : "Click a row to watch that player. Think time is measured on a laptop running the Python code.";
}

// ---- Your turn -------------------------------------------------------------
const play = { dict: null, sel: [], score: 0, moves: 0, over: false, dragging: false, available: new Map() };

function resetPlay() {
  playBoard.load(state.grid.rows);
  play.sel = [];
  play.score = 0;
  play.moves = 0;
  play.over = false;
  $("play-moves").innerHTML = "";
  $("play-score").textContent = "0";
  $("play-target").textContent = state.grid.games.hybrid.score.toLocaleString();
  renderSelection();
  refreshAvailable();
}

function refreshAvailable() {
  if (!play.dict) return;
  play.available = play.dict.findAll(playBoard.letters());
  if (playBoard.tilesLeft() === 0) {
    play.over = true;
    play.score += CLEAR_BONUS;
    addBonus("play-moves");
    $("play-score").textContent = play.score;
    const hy = state.grid.games.hybrid.score;
    setStatus("play-status", `You cleared the board! Final score ${play.score}${play.score > hy ? ". You beat the Hybrid!" : "."}`, "good");
  } else if (play.available.size === 0) {
    play.over = true;
    setStatus("play-status", `No words left. ${playBoard.tilesLeft()} tiles remain. Final score ${play.score}.`, "bad");
  } else {
    setStatus("play-status", `${play.available.size.toLocaleString()} different words can be played right now.`);
  }
}

function selectedWord() {
  return play.sel.map(([r, c]) => playBoard.letter(r, c)).join("");
}

function renderSelection() {
  playBoard.highlight(play.sel);
  const w = selectedWord();
  const el = $("play-current");
  const ok = w.length >= 3 && play.dict?.has(w);
  el.className = "current";
  el.innerHTML = w ? `${w.toUpperCase()}${ok ? ` <span style="color:var(--good)">+${scoreWord(w)}</span>` : ""}` : "&nbsp;";
}

function sameCell(a, b) { return a && b && a[0] === b[0] && a[1] === b[1]; }

function onPointerDown(e) {
  if (play.over) return;
  const cell = playBoard.cellAt(e.clientX, e.clientY, false);
  if (!cell) return;
  const last = play.sel[play.sel.length - 1];
  const inSel = play.sel.some((p) => sameCell(p, cell));
  if (sameCell(cell, last)) {
    play.sel.pop();
  } else if (last && adjacent(last, cell) && !inSel) {
    play.sel.push(cell);
    play.dragging = true;
  } else {
    play.sel = [cell];
    play.dragging = true;
  }
  $("play-board").setPointerCapture?.(e.pointerId);
  renderSelection();
}

function onPointerMove(e) {
  if (!play.dragging) return;
  const cell = playBoard.cellAt(e.clientX, e.clientY, true);
  if (!cell) return;
  const n = play.sel.length;
  if (sameCell(cell, play.sel[n - 1])) return;
  if (n >= 2 && sameCell(cell, play.sel[n - 2])) {
    play.sel.pop();
  } else if (adjacent(play.sel[n - 1], cell) && !play.sel.some((p) => sameCell(p, cell))) {
    play.sel.push(cell);
  } else return;
  renderSelection();
}

async function submitWord() {
  if (play.over || !play.dict) return;
  const w = selectedWord();
  const el = $("play-current");
  if (w.length < 3 || !play.dict.has(w)) {
    el.className = "current bad";
    el.textContent = w.length < 3 ? "Words need at least 3 letters" : `${w.toUpperCase()} isn't in the dictionary`;
    return;
  }
  const path = play.sel;
  play.sel = [];
  const pts = scoreWord(w);
  play.score += pts;
  play.moves++;
  addMove("play-moves", play.moves, w, pts);
  $("play-score").textContent = play.score;
  renderSelection();
  await playBoard.removePath(path, 320);
  refreshAvailable();
}

function hint() {
  if (play.over || !play.available.size) return;
  // Greedy-1's choice: highest score, then longest, then alphabetical.
  let best = null;
  for (const w of play.available.keys()) {
    if (!best || scoreWord(w) > scoreWord(best) || (scoreWord(w) === scoreWord(best) && (w.length > best.length || (w.length === best.length && w < best)))) best = w;
  }
  play.sel = play.available.get(best)[0].slice();
  renderSelection();
  setStatus("play-status", `Greedy-1 would play ${best.toUpperCase()} (+${scoreWord(best)}). Careful: the top-scoring word isn't always the best move.`);
}

// ---- Wiring ----------------------------------------------------------------
function selectGrid(id) {
  state.grid = state.data.grids.find((g) => g.id === id);
  $("grid-note").textContent = id.startsWith("expert")
    ? "Grid from a game played by an expert human player."
    : "Grid generated by the project's random grid generator.";
  renderCompare();
  resetWatch();
  resetPlay();
}

function selectTab(tab) {
  state.tab = tab;
  for (const t of ["watch", "play"]) {
    $("tab-" + t).setAttribute("aria-selected", String(t === tab));
    $("panel-" + t).hidden = t !== tab;
  }
  if (tab === "play") { watch.playing = false; $("btn-play").textContent = "Play"; }
}

async function init() {
  const res = await fetch("data/replays.json");
  state.data = await res.json();

  const sel = $("grid-select");
  sel.innerHTML = state.data.grids.map((g) => `<option value="${g.id}">${g.label}</option>`).join("");
  sel.onchange = () => selectGrid(sel.value);

  fitBoards([watchBoard, playBoard]);
  renderPlayers();
  selectGrid(state.data.grids[0].id);

  $("btn-play").onclick = () => {
    watch.playing = !watch.playing;
    $("btn-play").textContent = watch.playing ? "Pause" : "Play";
    if (watch.playing) stepWatch();
  };
  $("btn-step").onclick = () => { watch.playing = false; $("btn-play").textContent = "Play"; stepWatch(); };
  $("btn-reset").onclick = resetWatch;
  $("tab-watch").onclick = () => selectTab("watch");
  $("tab-play").onclick = () => selectTab("play");

  const pb = $("play-board");
  pb.addEventListener("pointerdown", onPointerDown);
  pb.addEventListener("pointermove", onPointerMove);
  window.addEventListener("pointerup", () => (play.dragging = false));
  $("btn-submit").onclick = submitWord;
  $("btn-clear").onclick = () => { play.sel = []; renderSelection(); };
  $("btn-hint").onclick = hint;
  $("btn-restart").onclick = resetPlay;
  document.addEventListener("keydown", (e) => {
    if (state.tab === "play" && e.key === "Enter") submitWord();
    if (state.tab === "play" && e.key === "Escape") { play.sel = []; renderSelection(); }
  });

  let t;
  window.addEventListener("resize", () => { clearTimeout(t); t = setTimeout(() => fitBoards([watchBoard, playBoard]), 100); });

  const text = await (await fetch("data/words.txt")).text();
  play.dict = new Dictionary(text.split("\n").filter(Boolean));
  refreshAvailable();
}

init().catch((err) => {
  console.error(err);
  setStatus("watch-status", "Couldn't load the demo data.", "bad");
});
