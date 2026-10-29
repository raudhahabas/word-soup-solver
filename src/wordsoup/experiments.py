"""Batch experiments: play many random grids with one player and log the results."""
from __future__ import annotations

import csv
import json
import random
import time
from typing import Dict, Optional

from .board import Grid, copy_grid, grid_letters, words_map_all_paths
from .generate import make_grid_from_letter_frequencies
from .players import play_game
from .scoring import score_word
from .trie import Trie

DEFAULT_ROWS = 12
DEFAULT_COLS = 9

CSV_COLUMNS = [
    "grid", "policy", "startWords", "startTopScore", "vowelRatio", "rareRatio",
    "cleared", "scoreNoBonus", "scoreWithBonus", "runtimeSec", "moves", "cellsLeft",
    "branchingAvg", "ppMoveAvg", "moveMax", "wordLenAvg", "scorePerCell",
]


def initial_grid_features(G: Grid, trie: Trie, *, min_len: int = 3) -> Dict[str, float]:
    """Features of the starting grid used in the analysis (playable words, vowel ratio, ...)."""
    playable = words_map_all_paths(G, trie, min_len=min_len)
    scores = sorted((score_word(w) for w in playable), reverse=True)
    letters = grid_letters(G)
    n = max(1, len(letters))
    return {
        "words_t0": float(len(playable)),
        "top1_score_t0": float(scores[0] if scores else 0),
        "vowel_ratio": sum(1 for c in letters if c in "aeiou") / n,
        "rare_ratio": sum(1 for c in letters if c in "qzxj") / n,
    }


def run_batch(
    policy: str,
    trie: Trie,
    dict_path: str,
    *,
    runs: int = 100,
    rows: int = DEFAULT_ROWS,
    cols: int = DEFAULT_COLS,
    min_len: int = 3,
    seed: Optional[int] = None,
    csv_path: Optional[str] = None,
    jsonl_path: Optional[str] = None,
    **player_kwargs,
) -> float:
    """Play ``runs`` freshly generated grids with ``policy``. Returns the clear rate.

    Writes one CSV row per game (and optionally the starting grid + words as JSONL).
    """
    if seed is not None:
        random.seed(seed)

    csv_file = open(csv_path, "w", newline="", encoding="utf-8") if csv_path else None
    writer = csv.DictWriter(csv_file, fieldnames=CSV_COLUMNS) if csv_file else None
    if writer:
        writer.writeheader()
    jsonl_file = open(jsonl_path, "w", encoding="utf-8") if jsonl_path else None

    cleared_count = 0
    print(f"[{policy}] {runs} games on {rows}x{cols} grids")
    try:
        for i in range(1, runs + 1):
            G = make_grid_from_letter_frequencies(rows, cols, dict_path)
            G_start = copy_grid(G)
            feats = initial_grid_features(G, trie, min_len=min_len)

            t0 = time.perf_counter()
            result = play_game(G, trie, policy, min_len=min_len, **player_kwargs)
            runtime = time.perf_counter() - t0
            cleared_count += result.cleared

            print(f"\r[{policy}] {i}/{runs}  cleared so far: {cleared_count}", end="", flush=True)

            if writer:
                m = result.metrics
                writer.writerow({
                    "grid": f"lfreq_{i}",
                    "policy": policy,
                    "startWords": int(feats["words_t0"]),
                    "startTopScore": int(feats["top1_score_t0"]),
                    "vowelRatio": f"{feats['vowel_ratio']:.2f}",
                    "rareRatio": f"{feats['rare_ratio']:.2f}",
                    "cleared": int(result.cleared),
                    "scoreNoBonus": result.score_without_bonus,
                    "scoreWithBonus": result.score,
                    "runtimeSec": f"{runtime:.2f}",
                    "moves": len(result.moves),
                    "cellsLeft": int(m["final_cells_remaining"]),
                    "branchingAvg": f"{m['branching_factor_mean']:.2f}",
                    "ppMoveAvg": f"{m['avg_points_per_move']:.2f}",
                    "moveMax": int(m["max_move_score"]),
                    "wordLenAvg": f"{m['avg_word_len']:.2f}",
                    "scorePerCell": f"{m['score_per_removed_cell']:.2f}",
                })
            if jsonl_file:
                jsonl_file.write(json.dumps({
                    "grid": f"lfreq_{i}",
                    "initial_grid": G_start,
                    "words": result.words,
                    "score": result.score,
                    "cleared": result.cleared,
                }) + "\n")
    finally:
        if csv_file:
            csv_file.close()
        if jsonl_file:
            jsonl_file.close()

    rate = cleared_count / runs if runs else 0.0
    print(f"\n[{policy}] cleared {cleared_count}/{runs} boards ({rate:.0%})")
    return rate
