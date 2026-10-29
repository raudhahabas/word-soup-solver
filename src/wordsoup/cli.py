"""Command-line interface.

    wordsoup play                                   # play a game yourself in the terminal
    wordsoup solve data/expert_games/game_01_grid.txt --policy hybrid
    wordsoup batch --policy greedy2 --runs 100 --seed 123 --csv greedy2.csv
"""
from __future__ import annotations

import argparse
import os
import random
import time
from pathlib import Path

from .board import apply_move, grid_is_empty, grid_to_str, load_grid, words_map_all_paths
from .experiments import DEFAULT_COLS, DEFAULT_ROWS, run_batch
from .generate import make_grid_from_letter_frequencies
from .players import POLICIES, play_game
from .scoring import CLEAR_BOARD_BONUS, score_word
from .trie import Trie

_REPO_DICT = Path(__file__).resolve().parents[2] / "data" / "dictionaries" / "enable.txt"


def default_dict_path() -> str:
    return os.environ.get("WORDSOUP_DICT") or str(_REPO_DICT)


def _cmd_solve(args: argparse.Namespace) -> None:
    trie = Trie.from_file(args.dict)
    G = load_grid(args.grid)
    print(grid_to_str(G), "\n")

    t0 = time.perf_counter()
    result = play_game(G, trie, args.policy)
    elapsed = time.perf_counter() - t0

    running = 0
    for i, m in enumerate(result.moves, 1):
        running += m.points
        print(f"{i:>3}. {m.word.upper():<20} +{m.points:<4} total {running}")
    if result.cleared:
        print(f"     (board cleared)       +{CLEAR_BOARD_BONUS}")
    else:
        print(f"\nStuck with {int(result.metrics['final_cells_remaining'])} tiles left:\n{grid_to_str(G)}")
    print(f"\nFinal score: {result.score}  ({elapsed:.1f}s, policy={args.policy})")


def _cmd_batch(args: argparse.Namespace) -> None:
    trie = Trie.from_file(args.dict)
    run_batch(
        args.policy, trie, args.dict,
        runs=args.runs, rows=args.rows, cols=args.cols, seed=args.seed,
        csv_path=args.csv, jsonl_path=args.jsonl,
    )


def _cmd_play(args: argparse.Namespace) -> None:
    trie = Trie.from_file(args.dict)
    if args.grid:
        G = load_grid(args.grid)
    else:
        if args.seed is not None:
            random.seed(args.seed)
        G = make_grid_from_letter_frequencies(DEFAULT_ROWS, DEFAULT_COLS, args.dict)

    total = 0
    while True:
        print(f"\n{grid_to_str(G)}\n")
        playable = words_map_all_paths(G, trie)
        if not playable:
            print("No words left to play.")
            break
        choice = input(f"Score {total}. Your word (or 'q' to quit): ").strip().lower()
        if choice == "q":
            break
        if choice not in playable:
            print("  That word can't be traced on this board.")
            continue
        paths = playable[choice]
        path = paths[0]
        if len(paths) > 1:
            for i, p in enumerate(paths, 1):
                print(f"  {i}) {p}")
            sel = input(f"  Which path? (1-{len(paths)}) [1]: ").strip()
            if sel.isdigit() and 1 <= int(sel) <= len(paths):
                path = paths[int(sel) - 1]
        pts = score_word(choice)
        total += pts
        print(f"  +{pts}")
        apply_move(G, path)
        if grid_is_empty(G):
            total += CLEAR_BOARD_BONUS
            print(f"  Board cleared! +{CLEAR_BOARD_BONUS}")
            break
    print(f"\nFinal score: {total}")


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="wordsoup", description="Word Soup solver")
    ap.add_argument("--dict", default=default_dict_path(),
                    help="word list, one word per line (default: ENABLE, or $WORDSOUP_DICT)")
    sub = ap.add_subparsers(dest="command", required=True)

    p = sub.add_parser("solve", help="let a player solve a grid from a text file")
    p.add_argument("grid", help="grid file: one row of letters per line")
    p.add_argument("--policy", choices=POLICIES, default="hybrid")
    p.set_defaults(func=_cmd_solve)

    p = sub.add_parser("batch", help="benchmark a player on many random grids")
    p.add_argument("--policy", choices=POLICIES, required=True)
    p.add_argument("--runs", type=int, default=100)
    p.add_argument("--rows", type=int, default=DEFAULT_ROWS)
    p.add_argument("--cols", type=int, default=DEFAULT_COLS)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--csv", help="write one row per game here")
    p.add_argument("--jsonl", help="write each starting grid and the words played here")
    p.set_defaults(func=_cmd_batch)

    p = sub.add_parser("play", help="play a game yourself in the terminal")
    p.add_argument("--grid", help="grid file (default: a random 12x9 grid)")
    p.add_argument("--seed", type=int, default=None)
    p.set_defaults(func=_cmd_play)

    args = ap.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
