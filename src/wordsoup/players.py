"""The five algorithmic players and the game loop that runs them.

Players (``POLICIES``):

- ``random``   picks a uniformly random playable word (baseline).
- ``greedy1``  plays the highest-scoring word right now.
- ``greedy2``  plans the best 2-move block, then commits to it.
- ``greedy3``  plans the best 3-move block, then commits to it.
- ``hybrid``   shortlists the top-k moves by immediate score, then plays each
               one out to the end of the game with a greedy rollout and picks
               the line that clears the board (and then scores the most).
               The rollout depth adapts to how many tiles are left.
"""
from __future__ import annotations

import random
import statistics
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .board import (
    Grid,
    Path,
    apply_move,
    copy_grid,
    count_tiles,
    grid_is_empty,
    simulate_move,
    words_map_all_paths,
)
from .scoring import CLEAR_BOARD_BONUS, score_word
from .trie import Trie

POLICIES = ("random", "greedy1", "greedy2", "greedy3", "hybrid")

# Beam width: how many candidate words (by immediate score) lookahead explores per state.
DEFAULT_MAX_CANDIDATES = 20

# Hybrid defaults
HYBRID_TOP_K = 20
HYBRID_EARLY_THRESHOLD = 0.50  # above this fraction of tiles left, roll out with greedy-1
HYBRID_LATE_THRESHOLD = 0.20   # above this, greedy-2; below it, greedy-3

Playable = Dict[str, List[Path]]
Value = Tuple[int, int, int, int]


@dataclass
class Move:
    word: str
    path: Path
    points: int


@dataclass
class GameResult:
    score: int                  # includes the clear bonus when the board is cleared
    cleared: bool
    moves: List[Move] = field(default_factory=list)
    metrics: Dict[str, float] = field(default_factory=dict)

    @property
    def words(self) -> List[str]:
        return [m.word for m in self.moves]

    @property
    def score_without_bonus(self) -> int:
        return self.score - CLEAR_BOARD_BONUS if self.cleared else self.score


# ---------------------------------------------------------------------------
# Greedy-n lookahead
# ---------------------------------------------------------------------------

def _value(score_sum: int, cleared: int, not_stuck: int, neg_tiles_left: int) -> Value:
    """Lexicographic value of a line of play.

    Prefer lines that clear the board, then lines that don't get stuck,
    then the higher score, then fewer tiles left.
    """
    return (cleared, not_stuck, score_sum, neg_tiles_left)


def _top_candidates(playable: Playable, max_candidates: int) -> List[Tuple[str, List[Path]]]:
    """Playable words sorted by immediate score, cut to the beam width."""
    ranked = sorted(playable.items(), key=lambda kv: score_word(kv[0]), reverse=True)
    if max_candidates is not None and max_candidates > 0:
        ranked = ranked[:max_candidates]
    return ranked


def greedy_best_choice(G: Grid, trie: Trie, playable: Playable, *, min_len: int) -> Tuple[str, Path]:
    """Greedy-1: play the highest-scoring word.

    Ties are broken by longer word, then alphabetically. If the word can be
    traced along several paths, pick the path that leaves the best next
    position (best next word, then best top-3 mean, then most options).
    """
    best_word: Optional[str] = None
    best_score = -1
    best_len = -1

    for w in playable.keys():
        s = score_word(w)
        L = len(w)
        if (
            s > best_score
            or (s == best_score and L > best_len)
            or (s == best_score and L == best_len and (best_word is None or w < best_word))
        ):
            best_score = s
            best_len = L
            best_word = w

    assert best_word is not None

    paths = playable[best_word]
    if len(paths) == 1:
        return best_word, paths[0]

    def path_quality(path: Path) -> Tuple[int, float, int, Path]:
        nxt = words_map_all_paths(simulate_move(G, path), trie, min_len=min_len)
        if not nxt:
            return (0, 0.0, 0, path)
        scores = sorted((score_word(x) for x in nxt.keys()), reverse=True)
        next_top1 = scores[0]
        next_top3 = sum(scores[:3]) / min(3, len(scores))
        return (next_top1, next_top3, len(nxt), path)

    return best_word, max(paths, key=path_quality)


def _max_future_value(
    G: Grid,
    trie: Trie,
    *,
    min_len: int,
    depth: int,
    max_candidates: int = DEFAULT_MAX_CANDIDATES,
) -> Value:
    """Best value reachable from ``G`` within ``depth`` more moves (beam-pruned search)."""
    if depth <= 0:
        if grid_is_empty(G):
            return _value(CLEAR_BOARD_BONUS, 1, 1, 0)
        return _value(0, 0, 1, -count_tiles(G))

    playable = words_map_all_paths(G, trie, min_len=min_len)
    if not playable:
        if grid_is_empty(G):
            return _value(CLEAR_BOARD_BONUS, 1, 1, 0)
        return _value(0, 0, 0, -count_tiles(G))

    best_total: Value = (-1, -1, -10**9, -10**9)
    for w, paths in _top_candidates(playable, max_candidates):
        move_score = score_word(w)
        for path in paths:
            future = _max_future_value(
                simulate_move(G, path), trie,
                min_len=min_len, depth=depth - 1, max_candidates=max_candidates,
            )
            total = (future[0], future[1], move_score + future[2], future[3])
            if total > best_total:
                best_total = total
    return best_total


def choose_move_with_ply(
    G: Grid,
    trie: Trie,
    playable: Playable,
    *,
    min_len: int,
    ply: int,
    max_candidates: int = DEFAULT_MAX_CANDIDATES,
) -> Tuple[str, Path]:
    """Pick the move maximising its score plus the best (ply - 1)-move continuation."""
    if ply <= 1:
        return greedy_best_choice(G, trie, playable, min_len=min_len)

    best_word: Optional[str] = None
    best_path: Optional[Path] = None
    best_value: Value = (-1, -1, -10**9, -10**9)

    for w, paths in _top_candidates(playable, max_candidates):
        move_score = score_word(w)
        for path in paths:
            future = _max_future_value(
                simulate_move(G, path), trie,
                min_len=min_len, depth=ply - 1, max_candidates=max_candidates,
            )
            total_value = (future[0], future[1], move_score + future[2], future[3])
            if total_value > best_value:
                best_value = total_value
                best_word = w
                best_path = path

    assert best_word is not None and best_path is not None
    return best_word, best_path


def best_two_move_plan(
    G: Grid, trie: Trie, *, min_len: int, max_candidates: int = DEFAULT_MAX_CANDIDATES,
) -> List[Tuple[str, Path]]:
    """Greedy-2: the (first move, greedy reply) pair with the highest combined score."""
    playable = words_map_all_paths(G, trie, min_len=min_len)
    if not playable:
        return []

    best_total = -1
    best_plan: List[Tuple[str, Path]] = []

    for w1, paths1 in _top_candidates(playable, max_candidates):
        s1 = score_word(w1)
        for p1 in paths1:
            G1 = simulate_move(G, p1)
            playable1 = words_map_all_paths(G1, trie, min_len=min_len)
            if not playable1:
                if s1 > best_total:
                    best_total = s1
                    best_plan = [(w1, p1)]
                continue

            w2, p2 = greedy_best_choice(G1, trie, playable1, min_len=min_len)
            total = s1 + score_word(w2)
            if total > best_total:
                best_total = total
                best_plan = [(w1, p1), (w2, p2)]

    return best_plan


def best_three_move_plan(
    G: Grid, trie: Trie, *, min_len: int, max_candidates: int = DEFAULT_MAX_CANDIDATES,
) -> List[Tuple[str, Path]]:
    """Greedy-3: plan three moves with a shrinking horizon (3-ply, then 2-ply, then 1-ply)."""
    plan: List[Tuple[str, Path]] = []
    G_sim = copy_grid(G)

    for horizon in (3, 2, 1):
        playable = words_map_all_paths(G_sim, trie, min_len=min_len)
        if not playable:
            break
        w, path = choose_move_with_ply(
            G_sim, trie, playable, min_len=min_len, ply=horizon, max_candidates=max_candidates,
        )
        plan.append((w, path))
        apply_move(G_sim, path)

    return plan


# ---------------------------------------------------------------------------
# Hybrid: shortlist + rollout
# ---------------------------------------------------------------------------

def _rollout(
    G: Grid, trie: Trie, *, min_len: int, ply: int, max_candidates: int = DEFAULT_MAX_CANDIDATES,
) -> Tuple[int, bool]:
    """Play greedy-``ply`` from ``G`` to the end. Returns (score incl. bonus, cleared)."""
    total = 0
    G_sim = copy_grid(G)

    while True:
        playable = words_map_all_paths(G_sim, trie, min_len=min_len)
        if not playable:
            if grid_is_empty(G_sim):
                return total + CLEAR_BOARD_BONUS, True
            return total, False

        w, path = choose_move_with_ply(
            G_sim, trie, playable, min_len=min_len, ply=ply, max_candidates=max_candidates,
        )
        total += score_word(w)
        apply_move(G_sim, path)

        if grid_is_empty(G_sim):
            return total + CLEAR_BOARD_BONUS, True


def hybrid_rollout_ply(
    G: Grid,
    initial_tiles: int,
    *,
    early_threshold: float = HYBRID_EARLY_THRESHOLD,
    late_threshold: float = HYBRID_LATE_THRESHOLD,
) -> int:
    """Rollout depth for the hybrid: cheap early on, deeper as the board empties."""
    remaining_ratio = count_tiles(G) / max(1, initial_tiles)
    if remaining_ratio > early_threshold:
        return 1
    if remaining_ratio > late_threshold:
        return 2
    return 3


def choose_move_hybrid(
    G: Grid,
    trie: Trie,
    playable: Playable,
    *,
    min_len: int,
    initial_tiles: int,
    top_k: int = HYBRID_TOP_K,
    early_threshold: float = HYBRID_EARLY_THRESHOLD,
    late_threshold: float = HYBRID_LATE_THRESHOLD,
    max_candidates: int = DEFAULT_MAX_CANDIDATES,
) -> Tuple[str, Path]:
    """Hybrid move choice.

    1. Rank every (word, path) by immediate score (+ bonus if it clears the board).
    2. Keep the top-k.
    3. Play each one out to the end with a greedy rollout.
    4. Prefer lines that clear the board, then the higher total score.
    """
    deep_ply = hybrid_rollout_ply(
        G, initial_tiles, early_threshold=early_threshold, late_threshold=late_threshold,
    )

    shallow_ranked: List[Tuple[int, str, Path]] = []
    for w, paths in playable.items():
        move_score = score_word(w)
        for path in paths:
            G_after = simulate_move(G, path)
            shallow_score = move_score + (CLEAR_BOARD_BONUS if grid_is_empty(G_after) else 0)
            shallow_ranked.append((shallow_score, w, path))

    shallow_ranked.sort(key=lambda item: item[0], reverse=True)
    shortlist = shallow_ranked[:max(1, min(top_k, len(shallow_ranked)))]

    best_word: Optional[str] = None
    best_path: Optional[Path] = None
    best_value: Tuple[int, int] = (-1, -10**9)

    for _, w, path in shortlist:
        move_score = score_word(w)
        G_after = simulate_move(G, path)

        if grid_is_empty(G_after):
            compare_value = (1, move_score + CLEAR_BOARD_BONUS)
        else:
            continuation, cleared = _rollout(
                G_after, trie, min_len=min_len, ply=deep_ply, max_candidates=max_candidates,
            )
            compare_value = (int(cleared), move_score + continuation)

        if compare_value > best_value:
            best_value = compare_value
            best_word = w
            best_path = path

    assert best_word is not None and best_path is not None
    return best_word, best_path


# ---------------------------------------------------------------------------
# Game loop
# ---------------------------------------------------------------------------

def play_game(
    G: Grid,
    trie: Trie,
    policy: str,
    *,
    min_len: int = 3,
    max_candidates: int = DEFAULT_MAX_CANDIDATES,
    top_k: int = HYBRID_TOP_K,
    early_threshold: float = HYBRID_EARLY_THRESHOLD,
    late_threshold: float = HYBRID_LATE_THRESHOLD,
    rng: random.Random | None = None,
) -> GameResult:
    """Play ``policy`` on ``G`` (modified in place) until the board is cleared or stuck."""
    if policy not in POLICIES:
        raise ValueError(f"Unknown policy {policy!r}; choose from {', '.join(POLICIES)}")
    if rng is None:
        rng = random

    initial_tiles = len(G) * (len(G[0]) if G else 0)
    moves: List[Move] = []
    pending_plan: List[Tuple[str, Path]] = []

    # Per-turn statistics for the metrics dict
    branching: List[int] = []
    top1_scores: List[int] = []
    top3_means: List[float] = []
    tie_events = 0
    multi_path_events = 0

    while True:
        playable = words_map_all_paths(G, trie, min_len=min_len)
        branching.append(len(playable))
        scores = sorted((score_word(w) for w in playable), reverse=True)
        top1_scores.append(scores[0] if scores else 0)
        top3_means.append(sum(scores[:3]) / min(3, len(scores)) if scores else 0.0)

        if not playable:
            break

        if policy == "random":
            w = rng.choice(list(playable.keys()))
            path = playable[w][0]
        elif policy == "greedy1":
            w, path = choose_move_with_ply(
                G, trie, playable, min_len=min_len, ply=1, max_candidates=max_candidates,
            )
        elif policy in ("greedy2", "greedy3"):
            # Plan a block of moves, then execute it without replanning mid-block.
            if not pending_plan:
                planner = best_two_move_plan if policy == "greedy2" else best_three_move_plan
                pending_plan = planner(G, trie, min_len=min_len, max_candidates=max_candidates)
            w, path = pending_plan.pop(0)
        else:
            w, path = choose_move_hybrid(
                G, trie, playable,
                min_len=min_len, initial_tiles=initial_tiles, top_k=top_k,
                early_threshold=early_threshold, late_threshold=late_threshold,
                max_candidates=max_candidates,
            )

        if sum(1 for s in scores if s == scores[0]) > 1:
            tie_events += 1
        if w in playable and len(playable[w]) > 1:
            multi_path_events += 1

        moves.append(Move(w, path, score_word(w)))
        apply_move(G, path)

        if grid_is_empty(G):
            break

    total = sum(m.points for m in moves)
    cleared = grid_is_empty(G)
    tiles_removed = sum(len(m.path) for m in moves)
    metrics = {
        "n_moves": float(len(moves)),
        "branching_factor_mean": float(statistics.mean(branching)),
        "branching_factor_median": float(statistics.median(branching)),
        "top1_score_mean": float(statistics.mean(top1_scores)),
        "top3_mean": float(statistics.mean(top3_means)),
        "tie_rate": float(tie_events / len(branching)),
        "multi_path_rate": float(multi_path_events / max(1, len(moves))),
        "avg_points_per_move": float(total / max(1, len(moves))),
        "max_move_score": float(max((m.points for m in moves), default=0)),
        "avg_word_len": float(statistics.mean(len(m.word) for m in moves)) if moves else 0.0,
        "score_per_removed_cell": float(total / max(1, tiles_removed)),
        "final_cells_remaining": float(count_tiles(G)),
    }
    return GameResult(
        score=total + (CLEAR_BOARD_BONUS if cleared else 0),
        cleared=cleared,
        moves=moves,
        metrics=metrics,
    )
