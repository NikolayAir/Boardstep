# Boardstep

Boardstep is a browser-based chess practice app.

It lets you play through chess moves, check whether moves are legal, load positions from FEN, and follow the current position in a simple web interface.

Live demo: https://boardstep.streamlit.app

The deployed demo is session-based. Each browser session has its own game state; it is not online multiplayer yet.

## What you can do now

* play legal chess moves in the browser
* use square buttons to choose a piece and then its target square
* see legal target squares after selecting a piece
* type moves manually, for example `e2e4` or `g1f3`
* use manual input for pawn promotion, for example `e7e8q`
* view move history
* copy the current position as FEN
* load a position from FEN

## Shareable positions

Boardstep shows the current position as FEN, a compact text code for a chess position.

You can copy the FEN from one session and paste it into another session to restore the same board position. Loading a FEN clears the move history.

## Shared game planning

Boardstep does not support shared online games yet.

The project includes an initial design note and a small shared game state helper for a future shared turn-based mode. The intended direction is a simple shared game ID flow with external storage and manual refresh, not real-time multiplayer.

See `docs/shared-game-flow.md` for the current design note.

## Current limitations

* The main styled chessboard is visual only.
* The separate square-button board is used for click moves.
* Each browser session has its own game state.
* There is no shared online game yet.
* There is no database or external shared storage yet.
* There is no chess engine or AI coach yet.

## Version history

* `v0.5.0` — shared game foundation. Adds a shared turn-based game design note, a small shared game state helper, and tests for the helper. This does not add shared online play yet.
* `v0.4.0` — beginner move feedback. Adds legal target-square feedback after selecting a piece and prepares the CI workflow for future Python version checks.
* `v0.3.0` — shareable position flow using FEN. Adds FEN validation and position loading.
* `v0.2.0` — deployed browser demo. Adds the Streamlit Cloud demo link, session-based limitation note, Streamlit Cloud import support, and clearer FEN wording.
* `v0.1.0` — initial playable chess practice baseline. Includes legal move validation, styled board display, click controls, manual UCI input, move history, tests, CI, and README documentation.

## Possible next steps

* improve direct board interaction
* add simple chess exercises or puzzles
* prototype a shared game ID flow
* choose a storage option for future shared turn-based games

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
