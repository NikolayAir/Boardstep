# Shared game storage plan

Status: planning note for the first `v0.6.0` shared game ID prototype.

Boardstep currently supports local chess practice, FEN loading, beginner move feedback, and a shared game state helper foundation. The deployed app is still session-based: each browser session has its own state, so two users cannot yet continue the same game from different devices.

The next milestone should add a small shared game ID prototype with external storage and manual refresh.

## Goal

Let one player create a shared game, send a game ID or link to another player, and let both players continue the same turn-based chess game from different devices.

This should be a simple turn-based prototype, not real-time multiplayer.

## Recommended storage direction

Use Supabase/PostgreSQL as the recommended first external storage option.

Reasons:

* hosted PostgreSQL storage
* usable from a Python Streamlit app
* fits the current Python/Streamlit architecture
* avoids adding a separate backend at this stage
* supports configuration through Streamlit secrets instead of committed credentials

This choice should first be tested with a small storage slice before expanding the shared-game UI.

## First data model

A first shared game record should store:

* `game_id`
* current `fen`
* `move_history`
* `created_at`
* `updated_at`
* `last_move_number`

This matches the existing shared game state helper and keeps the first prototype focused.

## First user flow

1. Player A creates a shared game.
2. The app creates a random game ID.
3. The initial game state is saved in external storage.
4. Player A sends the game ID or link to Player B.
5. Player B loads the same game.
6. A player makes a move.
7. The move is validated before saving.
8. The updated FEN and move history are saved.
9. The other player manually refreshes the game to see the latest position.

Manual refresh is acceptable for the first shared version.

## Non-goals for the first prototype

Do not add yet:

* real-time synchronization
* WebSockets
* React frontend
* FastAPI backend
* user accounts
* login system
* chat
* timers
* ratings
* chess engine analysis
* AI coach
* full online chess platform behavior

## Main risks

* database credentials must not be committed
* database permissions and Row Level Security must be configured deliberately
* elevated database keys must not be exposed in public code or browser-facing logic
* deployed storage behavior must be tested carefully
* two users could try to move at nearly the same time
* the first version may need simple conflict handling
* public wording must not describe this as real-time multiplayer

## Implementation direction

The next implementation issue should be small and bounded.

A good first implementation slice would be:

* add storage configuration through Streamlit secrets
* add a small storage module
* create a shared game by ID
* load a shared game by ID
* save FEN and move history after each legal move
* keep local practice mode unchanged
* add tests for storage-independent logic where possible

The first version should remain simple, transparent, and clearly documented.
