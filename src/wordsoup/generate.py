"""Random grid generation.

Letters are sampled according to how often they appear in the dictionary,
which gives far more playable boards than uniformly random letters.
"""
from __future__ import annotations

import random
from collections import Counter
from functools import lru_cache
from typing import List, Tuple


def read_word_list(path: str) -> List[str]:
    """Read a one-word-per-line file, keeping only alphabetic words (lowercased)."""
    words: List[str] = []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            w = line.strip().lower()
            if w.isalpha():
                words.append(w)
    return words


@lru_cache(maxsize=4)
def _letter_distribution(wordlist_path: str) -> Tuple[Tuple[str, ...], Tuple[float, ...]]:
    """Letters (sorted) and their cumulative sampling probabilities for a word list."""
    words = read_word_list(wordlist_path)
    if not words:
        raise ValueError("Dictionary is empty: " + wordlist_path)

    freq: Counter = Counter()
    for w in words:
        freq.update(w)

    letters, weights = zip(*sorted(freq.items()))
    total = sum(weights)
    cum = []
    s = 0
    for w in weights:
        s += w
        cum.append(s / total)
    return letters, tuple(cum)


def make_grid_from_letter_frequencies(
    rows: int,
    cols: int,
    wordlist_path: str,
    rng: random.Random | None = None,
) -> List[List[str]]:
    """Build a ``rows`` x ``cols`` grid of letters sampled by dictionary letter frequency."""
    if rng is None:
        rng = random
    letters, cum = _letter_distribution(wordlist_path)

    def sample_letter() -> str:
        x = rng.random()
        for letter, c in zip(letters, cum):
            if x <= c:
                return letter
        return letters[-1]

    bag = [sample_letter() for _ in range(rows * cols)]
    rng.shuffle(bag)
    return [bag[r * cols:(r + 1) * cols] for r in range(rows)]
