"""Prefix tree (trie) used to look up dictionary words and prefixes quickly.

During the grid search, a path of letters is abandoned as soon as it stops
being a prefix of any dictionary word, which prunes most of the search space.
"""
from __future__ import annotations

from typing import Dict, Iterable


class Trie:
    """A compact, case-insensitive trie.

    - ``ch``: maps a single lowercase letter to the child node
    - ``end``: True if a complete word ends at this node
    """

    __slots__ = ("ch", "end")

    def __init__(self) -> None:
        self.ch: Dict[str, Trie] = {}
        self.end: bool = False

    def insert(self, word: str) -> None:
        if not word:
            return
        node = self
        for c in word.lower():
            node = node.ch.setdefault(c, Trie())
        node.end = True

    def has_prefix(self, prefix: str) -> bool:
        """True if any word in the trie starts with ``prefix``."""
        node = self
        for c in prefix.lower():
            if c not in node.ch:
                return False
            node = node.ch[c]
        return True

    def has_word(self, word: str) -> bool:
        """True if ``word`` is in the trie as a complete word (not just a prefix)."""
        node = self
        for c in word.lower():
            if c not in node.ch:
                return False
            node = node.ch[c]
        return node.end

    def __contains__(self, word: str) -> bool:
        return self.has_word(word)

    def build(self, words: Iterable[str]) -> None:
        """Insert every alphabetic string from ``words`` (stripped and lowercased)."""
        for w in words:
            w = (w or "").strip().lower()
            if w and w.isalpha():
                self.insert(w)

    @staticmethod
    def from_words(words: Iterable[str]) -> "Trie":
        t = Trie()
        t.build(words)
        return t

    @staticmethod
    def from_file(path: str, encoding: str = "utf-8") -> "Trie":
        """Build a trie from a text file with one word per line."""
        with open(path, "r", encoding=encoding, errors="ignore") as f:
            return Trie.from_words(f)

    @property
    def root(self) -> "Trie":
        """The trie object is its own root node."""
        return self

    def __repr__(self) -> str:
        return f"Trie(end={self.end}, children={len(self.ch)})"
