# Shared turn-based game flow

Status: design note for the shared turn-based game direction, linked to Issue #16. A first manual-refresh shared game prototype was implemented during the `v0.6.0` milestone.

Boardstep started as a session-based chess practice app. Local practice still uses per-session state, while the first shared-game prototype uses external storage so another browser session can load and refresh the same game by ID.

This note defines the intended direction for shared turn-based play. The first implemented version remains a manual-refresh prototype, not real-time multiplayer.

## Goal

The goal is to let one player create a shared game, send a game ID or link to another player, and continue the same chess game from different devices.

The first shared version should be a simple turn-based prototype, not real-time multiplayer.

## Current baseline

Boardstep already supports:

* legal move validation through the `chess` Python library
* board state represented by FEN
* move history
* manual and click-based move input
* FEN loading for shareable positions
* beginner feedback for legal target squares
* a deployed Streamlit demo

The first shared version uses external storage because Streamlit session state is local to one browser session and cannot be used as the shared source of truth for a game between two users.

## Intended flow

A first shared-game prototype could work like this:

1. Player A creates a shared game.
2. The app creates a random game ID.
3. The initial game state is saved in external storage.
4. Player A sends the game ID or link to Player B.
5. Player B loads the same game.
6. Each move is validated before it is saved.
7. The updated FEN and move history are stored.
8. The other player refreshes the game to see the latest position.

Manual refresh is acceptable for the first version.

## State to store

A shared game needs at least:

* `game_id`
* current `fen`
* move history
* creation timestamp
* last update timestamp
* last move number

A possible storage shape is:

```text
games
-----
game_id text primary key
fen text not null
move_history text or json not null
created_at timestamp not null
updated_at timestamp not null
last_move_number integer not null
```

The side to move can be derived from the FEN, so it does not need to be stored separately in the first version.

## Storage direction

Streamlit session state is not suitable for shared games because it is not shared between users.

Local files or local SQLite can be useful for local experiments and tests, but they should not be treated as reliable deployed shared storage.

A small external database is the most realistic direction for a deployed shared-game prototype. The first implementation uses Supabase/PostgreSQL with a manual-refresh flow.

## First shared prototype scope

The first implemented shared prototype includes:

* creating a shared game ID
* loading a game by ID
* saving FEN and move history after each legal move
* manually refreshing to see the latest state

It does not include real-time synchronization, user accounts, chat, timers, ratings, chess engine analysis, or a full backend server.

## Summary

Boardstep can move toward shared online play in small steps. This note documents the shared-game model and storage direction while keeping the first implemented version clearly scoped as a manual-refresh prototype.
