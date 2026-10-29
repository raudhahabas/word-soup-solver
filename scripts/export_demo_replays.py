"""Record every player's game on a set of grids for the web demo (docs/).

Writes docs/data/replays.json and docs/data/words.txt.

    python scripts/export_demo_replays.py            # 10 expert grids + 6 random grids
    python scripts/export_demo_replays.py --random 0 # expert grids only
"""
from __future__ import annotations

import argparse
import json
import random
import re
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from wordsoup import POLICIES, Trie, load_grid, play_game
from wordsoup.board import copy_grid
from wordsoup.generate import make_grid_from_letter_frequencies
from wordsoup.scoring import CLEAR_BOARD_BONUS

ROOT = Path(__file__).resolve().parents[1]
DICT = ROOT / "data" / "dictionaries" / "enable.txt"
EXPERT = ROOT / "data" / "expert_games"
OUT = ROOT / "docs" / "data"

_trie: Trie | None = None


def _play(job):
    global _trie
    if _trie is None:
        _trie = Trie.from_file(str(DICT))
    grid_id, G, policy = job
    t0 = time.perf_counter()
    result = play_game(copy_grid(G), _trie, policy, rng=random.Random(grid_id))
    return grid_id, policy, {
        "score": result.score,
        "cleared": result.cleared,
        "seconds": round(time.perf_counter() - t0, 2),
        "moves": [[m.word, [list(p) for p in m.path], m.points] for m in result.moves],
    }


def expert_summary(moves_file: Path) -> dict:
    """Total score, whether the board was cleared, and number of words, from an expert's game log."""
    text = moves_file.read_text()
    points = [int(p) for p in re.findall(r"^[A-Z]+\s+(\d+)\s*$", text, re.MULTILINE)]
    cleared = "(clear)" in text
    return {
        "expert_score": sum(points) + (CLEAR_BOARD_BONUS if cleared else 0),
        "expert_cleared": cleared,
        "expert_words": len(points),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--random", type=int, default=6, help="number of random grids to add")
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--workers", type=int, default=None)
    args = ap.parse_args()

    grids = {}
    for f in sorted(EXPERT.glob("game_*_grid.txt")):
        n = int(f.stem.split("_")[1])
        grids[f"expert-{n:02d}"] = {
            "label": f"Expert grid {n}",
            "grid": load_grid(str(f)),
            **expert_summary(EXPERT / f"game_{n:02d}_moves.txt"),
        }
    rng = random.Random(args.seed)
    for i in range(1, args.random + 1):
        grids[f"random-{i:02d}"] = {
            "label": f"Random grid {i}",
            "grid": make_grid_from_letter_frequencies(12, 9, str(DICT), rng=rng),
            "expert_score": None, "expert_cleared": None, "expert_words": None,
        }

    jobs = [(gid, g["grid"], p) for gid, g in grids.items() for p in POLICIES]
    # Slowest jobs first so the pool stays busy.
    jobs.sort(key=lambda j: {"greedy3": 0, "hybrid": 1, "greedy2": 2}.get(j[2], 3))
    games = {gid: {} for gid in grids}
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        for done, (gid, policy, game) in enumerate(pool.map(_play, jobs), 1):
            games[gid][policy] = game
            print(f"[{done}/{len(jobs)}] {gid:10s} {policy:8s} score={game['score']:5d} "
                  f"cleared={game['cleared']} ({game['seconds']}s)", flush=True)

    OUT.mkdir(parents=True, exist_ok=True)
    payload = {
        "dictionary": "ENABLE",
        "policies": list(POLICIES),
        "grids": [
            {
                "id": gid,
                "label": g["label"],
                "rows": ["".join(c or "." for c in row) for row in g["grid"]],
                "expert_score": g["expert_score"],
                "expert_cleared": g["expert_cleared"],
                "expert_words": g["expert_words"],
                "games": {p: games[gid][p] for p in POLICIES},
            }
            for gid, g in grids.items()
        ],
    }
    (OUT / "replays.json").write_text(json.dumps(payload, separators=(",", ":")))

    words = sorted({w.strip().lower() for w in DICT.read_text().split() if len(w.strip()) >= 3 and w.isalpha()})
    (OUT / "words.txt").write_text("\n".join(words) + "\n")
    print(f"Wrote {OUT / 'replays.json'} and {len(words)} words to {OUT / 'words.txt'}")


if __name__ == "__main__":
    main()
