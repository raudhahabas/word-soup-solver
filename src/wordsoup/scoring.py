"""
Scoring rules for Word Soup

Spec:
- Word score = (word length) × (sum of letter points).
- Letter points use Scrabble-style values (default), but can be swapped.
- Words shorter than 3 letters are not allowed. 
- Bonus: +500 when a move clears the board (handled via helper).
"""
from __future__ import annotations
from typing import Dict

# Default Scrabble-like letter points
SCRABBLE_POINTS: Dict[str, int] = {
    # 1-point letters
    **{c: 1 for c in "aeorst"},
    # 2-point letters
    **{c: 2 for c in "dgnu"},
    # 3-point letters
    **{c: 3 for c in "bcimp"},
    # 4-point letters
    **{c: 4 for c in "fhvwy"},
    # 5-point letters
    **{c: 5 for c in "kl"},
    # 8-point letters
    "j": 8, "x": 8,
    # 10-point letters
    "q": 10, "z": 10,
}

# Clear-the-board one-time bonus applied when the board becomes empty after a move
CLEAR_BOARD_BONUS = 500


def score_word(word: str, *, letter_points: Dict[str, int] = SCRABBLE_POINTS, min_len: int = 3) -> int:
    """
    Return the score for a valid word.

    Rules:
    - Disallow words shorter than ``min_len`` by returning 0.
    - Score = len(word) × sum(letter points).

    Parameters
    ----------
    word : str
        The candidate word (letters only; case-insensitive).
    letter_points : Dict[str, int]
        Mapping from lowercase letter -> point value (default: Scrabble values).
    min_len : int
        Minimum allowed word length (default 3).
    """
    if not word:
        return 0

    w = word.lower()
    if len(w) < min_len:
        return 0

    # Sum letter values; unknown characters score 0 by default.
    letter_sum = 0
    for ch in w:
        letter_sum += letter_points.get(ch, 0)

    return len(w) * letter_sum


def apply_clear_board_bonus(score_so_far: int, grid_is_empty: bool) -> int:
    """
    Add the clear-board bonus if the grid is empty after the move.

    Call this in the controller after applying removal + gravity + refill.
    """
    if grid_is_empty:
        return score_so_far + CLEAR_BOARD_BONUS
    return score_so_far
