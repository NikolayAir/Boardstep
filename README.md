# Boardstep

Boardstep is a browser-based chess practice app.

It lets you play through chess moves, check whether moves are legal, load positions from FEN, and follow the current position in a simple web interface.

It also includes a first manual-refresh shared game prototype. When shared storage is configured, a game can be created with a shared ID, loaded from another browser session, and refreshed manually.

Live demo: https://boardstep.streamlit.app

The deployed demo remains a small prototype. Shared game features require configured external storage secrets and are not real-time multiplayer.

## What you can do now

* play legal chess moves in the browser
* use square buttons to choose a piece and then its target square
* see legal target squares after selecting a piece
* type moves manually, for example `e2e4` or `g1f3`
* use manual input for pawn promotion, for example `e7e8q`
* view move history
* copy the current position as FEN
* load a position from FEN
* create a shared game ID when shared storage is configured
* load a shared game by ID
* save moves to shared storage after creating or loading a shared game
* manually refresh a shared game to load the latest saved position

## Shareable positions

Boardstep shows the current position as FEN, a compact text code for a chess position.

You can copy the FEN from one session and paste it into another session to restore the same board position. Loading a FEN clears the move history.

## Shared game prototype

Boardstep includes a first shared game ID flow using external storage and manual refresh.

When Supabase/Streamlit secrets are configured, one browser session can create a shared game ID, another session can load it, and moves played after creating or loading the shared game are saved back to storage. Other sessions use manual refresh to load the latest saved position.

This is not real-time multiplayer. There are no accounts, private invites, clocks, ratings, chat, or chess engine. Anyone with the shared game ID may be able to load that game.

See `docs/shared-game-flow.md` for the design note and `docs/shared-game-storage-setup.md` for storage setup notes.

## Current limitations

* The main styled chessboard is visual only.
* The separate square-button board is used for click moves.
* Local practice is session-based unless a shared game is created or loaded.
* Shared games use manual refresh, not real-time synchronization.
* Shared game storage requires configured Supabase/Streamlit secrets.
* There are no accounts, private invites, clocks, ratings, chat, or chess engine.
* There is no chess engine or AI coach yet.

## Version history

* `v0.6.0` — manual-refresh shared game prototype. Adds shared game ID creation, loading by ID, move saving through configured external storage, manual refresh, and stale-state conflict messaging.
* `v0.5.0` — shared game foundation. Adds a shared turn-based game design note, a small shared game state helper, and tests for the helper. This does not add shared online play yet.
* `v0.4.0` — beginner move feedback. Adds legal target-square feedback after selecting a piece and prepares the CI workflow for future Python version checks.
* `v0.3.0` — shareable position flow using FEN. Adds FEN validation and position loading.
* `v0.2.0` — deployed browser demo. Adds the Streamlit Cloud demo link, session-based limitation note, Streamlit Cloud import support, and clearer FEN wording.
* `v0.1.0` — initial playable chess practice baseline. Includes legal move validation, styled board display, click controls, manual UCI input, move history, tests, CI, and README documentation.

## Possible next steps

* improve direct board interaction
* add simple chess exercises or puzzles
* polish shared game status and conflict messages
* improve shared game setup and storage permission notes

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
