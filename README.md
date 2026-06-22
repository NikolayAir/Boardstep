# Boardstep

Boardstep is a browser-based chess practice app.

It lets you play through chess moves, check whether moves are legal, and follow the current position in a simple web interface.

Live demo: https://boardstep.streamlit.app

The deployed demo is session-based. Each browser session has its own game state; it is not online multiplayer yet.

## Current version

`v0.2.0` is the first deployed browser demo.

It includes:

* a visual chessboard
* legal move checking
* click-based move controls
* manual move input as a fallback
* move history
* current position shown as FEN, a compact text code for a chess position
* automated tests
* GitHub Actions checks

## How it works now

You can make moves in two ways:

* use the square buttons to choose a piece and then its target square
* type a move manually, for example `e2e4` or `g1f3`

For pawn promotion, use manual input, for example `e7e8q`.

## Current limitations

* The main styled chessboard is visual only.
* The separate square-button board is used for click moves.
* Each browser session has its own game state.
* There is no shared online game yet.
* There is no chess engine or AI coach yet.

## Possible next steps

* improve the board interaction
* make move feedback clearer for beginners
* add simple chess exercises or puzzles
* add shareable positions
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
