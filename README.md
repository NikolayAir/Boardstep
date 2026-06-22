# Boardstep

Boardstep is a browser-based chess practice app.

It lets you play through chess moves, check whether moves are legal, load positions from FEN, and follow the current position in a simple web interface.

Live demo: https://boardstep.streamlit.app

The deployed demo is session-based. Each browser session has its own game state; it is not online multiplayer yet.

## What you can do now

* play legal chess moves in the browser
* use square buttons to choose a piece and then its target square
* type moves manually, for example `e2e4` or `g1f3`
* use manual input for pawn promotion, for example `e7e8q`
* view move history
* copy the current position as FEN
* load a position from FEN

## Shareable positions

Boardstep shows the current position as FEN, a compact text code for a chess position.

You can copy the FEN from one session and paste it into another session to restore the same board position. Loading a FEN clears the move history.

## Current limitations

* The main styled chessboard is visual only.
* The separate square-button board is used for click moves.
* Each browser session has its own game state.
* There is no shared online game yet.
* There is no chess engine or AI coach yet.

## Version history

* `v0.3.0` — shareable position flow using FEN. Adds FEN validation, position loading, and README documentation.
* `v0.2.0` — deployed browser demo. Added the Streamlit Cloud demo link, session-based limitations, Streamlit Cloud import support, and clearer FEN wording.
* `v0.1.0` — initial playable chess practice baseline. Included legal move validation, styled board display, click controls, manual UCI input, move history, tests, CI, and README documentation.

## Possible next steps

* improve the board interaction
* make move feedback clearer for beginners
* add simple chess exercises or puzzles
* later, explore remote turn-based play

## Run locally

```zsh
python -m streamlit run app/streamlit_app.py
```

## Checks

```zsh
python -m compileall app boardstep tests
python -m pytest -q
git diff --check
```
