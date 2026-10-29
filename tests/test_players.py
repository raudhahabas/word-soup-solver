"""Tests for the players, using small hand-made boards and word lists."""
import random
from pathlib import Path

import pytest

from wordsoup.board import copy_grid
from wordsoup.players import POLICIES, play_game
from wordsoup.scoring import CLEAR_BOARD_BONUS, score_word
from wordsoup.trie import Trie


def grid(*rows):
    return [[None if ch == "." else ch for ch in row] for row in rows]


# Benchmark board from the report (section 5.5)
JAM_TEA_MILK = grid(".jam",
                    ".tea",
                    "milk")
WORDS = ["jam", "tea", "milk", "kelim", "tilak", "tamale", "meat", "team", "mat", "eat", "lit", "ilk"]


@pytest.mark.parametrize("policy", POLICIES)
def test_every_player_finishes_a_game(policy):
    trie = Trie.from_words(WORDS)
    G = copy_grid(JAM_TEA_MILK)
    result = play_game(G, trie, policy, rng=random.Random(0))
    assert len(result.moves) >= 1
    assert result.score == sum(m.points for m in result.moves) + (CLEAR_BOARD_BONUS if result.cleared else 0)
    assert result.metrics["final_cells_remaining"] == sum(c is not None for row in G for c in row)


def test_greedy1_plays_the_highest_scoring_word_first():
    trie = Trie.from_words(WORDS)
    result = play_game(copy_grid(JAM_TEA_MILK), trie, "greedy1")
    best = max((w for w in WORDS if score_word(w) > 0), key=score_word)
    assert result.moves[0].word == "kelim" == best


def test_one_word_board_is_cleared():
    trie = Trie.from_words(["cow"])
    for policy in POLICIES:
        result = play_game(grid("cow"), trie, policy)
        assert result.cleared
        assert result.score == score_word("cow") + CLEAR_BOARD_BONUS


def test_board_with_no_words():
    trie = Trie.from_words(["cow"])
    result = play_game(grid("xyz"), trie, "hybrid")
    assert not result.cleared and result.score == 0 and result.moves == []


def test_hybrid_clears_a_board_that_greedy1_gets_stuck_on():
    # Found by searching small random boards with the ENABLE word list.
    trie = Trie.from_file(str(Path(__file__).parents[1] / "data" / "dictionaries" / "enable.txt"))
    board = grid("sboa",
                 "lirs",
                 "elsc")
    greedy = play_game(copy_grid(board), trie, "greedy1")
    hybrid = play_game(copy_grid(board), trie, "hybrid")
    assert greedy.words == ["brills", "coss"] and not greedy.cleared
    assert hybrid.words == ["libras", "socles"] and hybrid.cleared
    assert hybrid.score > greedy.score
