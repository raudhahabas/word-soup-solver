"""Board mechanics: finding words on the grid, removing them, and gravity.

A grid is a list of rows; each cell holds a lowercase letter or ``None``
(an empty cell). Words are traced through 8-directionally adjacent cells,
and each cell can be used at most once per word.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple

from .trie import Trie

Coord = Tuple[int, int]
Path = Tuple[Coord, ...]
Grid = List[List[Optional[str]]]


# ---------------------------------------------------------------------------
# Word search
# ---------------------------------------------------------------------------

def _neighbors8(m: int, n: int, r: int, c: int):
    """Yield all 8-direction neighbours of (r, c) inside an m x n grid."""
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue
            rr, cc = r + dr, c + dc
            if 0 <= rr < m and 0 <= cc < n:
                yield rr, cc


def _is_letter(ch) -> bool:
    return isinstance(ch, str) and len(ch) == 1 and ch.isalpha()


def find_all_words(G: Grid, trie: Trie, min_len: int = 3) -> Set[Tuple[str, Path]]:
    """Return every (word, path) pair that can be traced on ``G``.

    Depth-first search from every cell, pruned by the trie: a branch stops
    as soon as the letters so far are not a prefix of any dictionary word.
    """
    m = len(G)
    n = len(G[0]) if m > 0 else 0
    found: Set[Tuple[str, Path]] = set()
    visited = [[False] * n for _ in range(m)]

    def dfs(r: int, c: int, node: Trie, prefix: str, path: List[Coord]) -> None:
        ch = G[r][c].lower()
        node = node.ch[ch]
        prefix += ch
        path.append((r, c))
        visited[r][c] = True

        if len(prefix) >= min_len and node.end:
            found.add((prefix, tuple(path)))

        for rr, cc in _neighbors8(m, n, r, c):
            if visited[rr][cc]:
                continue
            ch2 = G[rr][cc]
            # Only recurse if the neighbour's letter continues a valid prefix.
            if _is_letter(ch2) and ch2.lower() in node.ch:
                dfs(rr, cc, node, prefix, path)

        visited[r][c] = False
        path.pop()

    for r in range(m):
        for c in range(n):
            ch = G[r][c]
            if _is_letter(ch) and ch.lower() in trie.root.ch:
                dfs(r, c, trie.root, "", [])

    return found


def _adjacent(a: Coord, b: Coord) -> bool:
    return max(abs(a[0] - b[0]), abs(a[1] - b[1])) == 1


def path_is_valid(path: Path) -> bool:
    """A path is valid if it never reuses a cell and each step is to a neighbour."""
    if len(set(path)) != len(path):
        return False
    return all(_adjacent(path[i], path[i + 1]) for i in range(len(path) - 1))


def words_map_all_paths(G: Grid, trie: Trie, *, min_len: int = 3) -> Dict[str, List[Path]]:
    """Map each playable word to every path that spells it on the grid."""
    mp: Dict[str, List[Path]] = {}
    for w, path in find_all_words(G, trie, min_len=min_len):
        if not path_is_valid(path):
            continue
        mp.setdefault(w, []).append(path)
    return mp


# ---------------------------------------------------------------------------
# Applying a move
# ---------------------------------------------------------------------------

def remove_path(G: Grid, path: Path) -> None:
    """Empty every cell on ``path`` (in place)."""
    for r, c in path:
        G[r][c] = None


def apply_gravity(G: Grid) -> None:
    """Drop letters down each column, then slide them right along each row (in place).

    The relative order of surviving letters is preserved in both steps.
    No new letters are added.
    """
    m = len(G)
    n = len(G[0]) if m > 0 else 0

    # 1) Vertical gravity: compact each column downward
    for c in range(n):
        col = [G[r][c] for r in range(m) if G[r][c] is not None]
        r_write = m - 1
        for val in reversed(col):
            G[r_write][c] = val
            r_write -= 1
        for r in range(r_write, -1, -1):
            G[r][c] = None

    # 2) Horizontal gravity: shift each row's letters to the right
    for r in range(m):
        row_vals = [G[r][c] for c in range(n) if G[r][c] is not None]
        c_write = n - 1
        for val in reversed(row_vals):
            G[r][c_write] = val
            c_write -= 1
        for c in range(c_write, -1, -1):
            G[r][c] = None


def apply_move(G: Grid, path: Path) -> None:
    """Remove ``path`` and apply gravity, in place."""
    remove_path(G, path)
    apply_gravity(G)


def simulate_move(G: Grid, path: Path) -> Grid:
    """Return a copy of ``G`` after playing ``path``; ``G`` itself is unchanged."""
    G_copy = copy_grid(G)
    apply_move(G_copy, path)
    return G_copy


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def copy_grid(G: Grid) -> Grid:
    return [row[:] for row in G]


def grid_is_empty(G: Grid) -> bool:
    return all(cell is None for row in G for cell in row)


def count_tiles(G: Grid) -> int:
    return sum(1 for row in G for c in row if c is not None)


def grid_letters(G: Grid) -> List[str]:
    return [c for row in G for c in row if c is not None]


def load_grid(path: str) -> Grid:
    """Read a grid from a text file: one row per line, ``.`` or ``*`` for empty cells."""
    with open(path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]
    return [[None if ch in ".*" else ch.lower() for ch in line] for line in lines]


def grid_to_str(G: Grid) -> str:
    return "\n".join(" ".join(c.upper() if c else "." for c in row) for row in G)
