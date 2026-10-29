# Data

## `dictionaries/enable.txt`

The **ENABLE** (Enhanced North American Benchmark Lexicon) word list, about 173,000 words. It is public domain. This is the default dictionary for the code and the web demo.

The report's experiments used a larger list (~279,000 words) supplied by the project supervisor. That list isn't redistributed here. To run with any other word list (one word per line), use `--dict path/to/words.txt` or set `WORDSOUP_DICT`.

## `expert_games/`

10 games played in the real Word Soup app by an expert human player:

- `game_NN_grid.txt`: the starting 12×9 grid, one row per line
- `game_NN_moves.txt`: the words played in order, with points, and whether the board was cleared

Summary: 8 of 10 boards cleared, mean score 1,949 including the clear bonus.
The expert's strategy was to build one long word first, then clear the remaining tiles. When there were a lot of Qs, they got rid of those first.
