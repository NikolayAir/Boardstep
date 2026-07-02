# Boardstep

Boardstep is a browser-based chess practice app.

It lets you play through chess moves, check whether moves are legal, move directly on the main board, load positions from FEN, and follow the current position in a simple web interface.

It also includes a manual-refresh shared game prototype. You can create a shared game ID, load it in another browser session, refresh manually to see the latest saved position, and leave shared mode without deleting the saved game.

Live demo: https://boardstep.streamlit.app

The deployed demo remains a small prototype. Shared game features require configured shared-game storage and are not real-time multiplayer.

## What you can do now

* play legal chess moves in the browser
* click the main board to choose a piece and then its target square
* see legal target squares after selecting a piece
* use coordinate practice controls as an optional fallback
* type moves manually, for example `e2e4` or `g1f3`
* use manual input for pawn promotion, for example `e7e8q`
* view move history
* copy the current position as FEN
* load a position from FEN
* create a shared game ID when shared storage is configured
* load a shared game by ID
* see whether the app is in local practice mode or shared game mode
* find and reuse the active shared game ID
* save moves to shared storage after creating or loading a shared game
* manually refresh a shared game to load the latest saved position
* use a board-side refresh shortcut while playing a shared game
* leave shared game mode and return to local practice without deleting the saved shared game

## Shareable positions

Boardstep shows the current position as FEN, a compact text code for a chess position.

You can copy the FEN from one session and paste it into another session to restore the same board position. Loading a FEN clears the move history.

## Shared game prototype

Boardstep includes a manual-refresh shared game ID flow using external storage.

Boardstep can share a game through a game ID. One browser creates the ID, and another browser loads it. Moves are saved after they are played, and the other browser uses Refresh shared game to load the latest saved position.

You can also leave shared game mode locally. This returns the app to local practice without deleting the saved shared game.

This is not real-time multiplayer. There are no accounts, private invites, clocks, ratings, chat, or chess engine. Anyone with the shared game ID may be able to load that game.

See `docs/shared-game-flow.md` for the design note and `docs/shared-game-storage-setup.md` for storage setup notes.

## Current limitations

* Board interaction uses click-to-move, not drag-and-drop.
* The clickable board may take a moment to appear on first load.
* Local practice is session-based unless a shared game is created or loaded.
* Shared games use manual refresh, not real-time synchronization.
* Shared game storage must be configured before shared games are available.
* There are no accounts, private invites, clocks, ratings, or chat.
* There is no chess engine or AI coach yet.

## Version history

* `v0.9.0` — shared game UX polish. Makes shared games easier to create, load, refresh, leave, and understand while keeping manual refresh as the synchronization model.
* `v0.8.0` — clickable main board. Adds direct source-and-target square selection on the main chessboard while keeping coordinate controls as an optional practice/fallback section.
* `v0.7.0` — playable UI polish. Improves the playing layout with a clearer board and game panel, larger board display, tighter move controls, and refined board/piece styling.
* `v0.6.0` — manual-refresh shared game prototype. Adds shared game ID creation, loading by ID, move saving through configured external storage, manual refresh, and stale-state conflict messaging.
* `v0.5.0` — shared game foundation. Adds a shared turn-based game design note, a small shared game state helper, and tests for the helper.
* `v0.4.0` — beginner move feedback. Adds legal target-square feedback after selecting a piece and keeps CI checks focused on the supported Python version.
* `v0.3.0` — shareable position flow using FEN. Adds FEN validation and position loading.
* `v0.2.0` — deployed browser demo. Adds the Streamlit Cloud demo link, Streamlit Cloud import support, and clearer FEN wording.
* `v0.1.0` — initial playable chess practice baseline. Includes legal move validation, styled board display, manual UCI input, move history, tests, CI, and README documentation.

## Possible next steps

* add a board orientation toggle for playing from Black's side
* design player side selection and move restrictions
* design shared game cleanup or delete behavior
* add simple chess exercises or puzzles
* polish clickable board loading and responsive behavior

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
