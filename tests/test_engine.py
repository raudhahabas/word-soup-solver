"""Tests for the game rules: scoring, word search and gravity."""
from wordsoup.board import apply_gravity, find_all_words, path_is_valid, words_map_all_paths
from wordsoup.scoring import CLEAR_BOARD_BONUS, score_word
from wordsoup.trie import Trie


def grid(*rows):
    """Build a grid from strings, with '.' for empty cells."""
    return [[None if ch == "." else ch for ch in row] for row in rows]


def test_score_is_length_times_letter_points():
    assert score_word("cat") == 3 * (3 + 1 + 1)
    assert score_word("quiz") == 4 * (10 + 2 + 3 + 10)
    assert score_word("CAT") == score_word("cat")


def test_short_words_score_zero():
    assert score_word("at") == 0
    assert score_word("") == 0


def test_clear_bonus_value():
    assert CLEAR_BOARD_BONUS == 500


def test_trie_words_and_prefixes():
    trie = Trie.from_words(["cat", "cart", "Dog", "it's"])
    assert "cat" in trie and "dog" in trie
    assert "ca" not in trie
    assert trie.has_prefix("car")
    assert not trie.has_prefix("cow")
    assert not trie.has_word("it's")  # non-alphabetic entries are skipped


def test_words_can_be_traced_diagonally():
    trie = Trie.from_words(["cat"])
    G = grid("c..",
             ".a.",
             "..t")
    assert find_all_words(G, trie) == {("cat", ((0, 0), (1, 1), (2, 2)))}


def test_cells_are_not_reused_within_a_word():
    trie = Trie.from_words(["aaa"])
    assert words_map_all_paths(grid("aa"), trie) == {}


def test_empty_cells_break_words():
    trie = Trie.from_words(["cat"])
    assert words_map_all_paths(grid("c.at"), trie) == {}


def test_every_path_to_a_word_is_found():
    trie = Trie.from_words(["tot"])
    found = words_map_all_paths(grid("tot"), trie)
    assert sorted(found["tot"]) == [((0, 0), (0, 1), (0, 2)), ((0, 2), (0, 1), (0, 0))]


def test_minimum_word_length():
    trie = Trie.from_words(["at", "cat"])
    assert set(words_map_all_paths(grid("cat"), trie)) == {"cat"}


def test_path_validity():
    assert path_is_valid(((0, 0), (1, 1), (1, 2)))
    assert not path_is_valid(((0, 0), (0, 2)))          # not adjacent
    assert not path_is_valid(((0, 0), (0, 1), (0, 0)))  # reuses a cell


def test_gravity_drops_down_then_slides_right():
    G = grid("ab.",
             "...",
             "c..")
    apply_gravity(G)
    # Column drop: a falls onto c, b falls to the bottom. Then rows slide right.
    assert G == grid("...",
                     "..a",
                     ".cb")


def test_gravity_keeps_letter_order():
    G = grid("a.",
             "b.",
             ".c")
    apply_gravity(G)
    assert G == grid("..",
                     ".a",
                     "bc")
