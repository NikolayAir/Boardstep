# Boardstep

Boardstep is a browser-based chess practice app.

It lets you play through chess moves, check whether moves are legal, and follow the current position in a simple web interface.

## Current version

`v0.1.0` is the first playable local version.

It includes:

* a visual chessboard
* legal move checking
* click-based move controls
* manual move input as a fallback
* move history
* automated tests

## How it works now

The app is mainly for local practice.

You can make moves in two ways:

* use the square buttons to choose a piece and then its target square
* type a move manually, for example `e2e4` or `g1f3`

For pawn promotion, use manual input, for example `e7e8q`.

## Current limitations

* The main styled chessboard is visual only.
* The separate square-button board is used for click moves.
* There is no online play yet.
* There is no chess engine or AI coach yet.

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
```
