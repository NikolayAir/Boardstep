# Shared turn-based game flow

Status: design note for planned future work, linked to Issue #16.

Boardstep is currently a session-based chess practice app. Each browser session has its own independent game state. This works for local practice, move validation, FEN sharing, and beginner move feedback, but it is not enough for two people to play the same shared game from different devices.

This note defines the intended direction for a future shared turn-based mode. It does not implement shared online play yet.

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

The missing part is shared storage. Streamlit session state is local to one browser session, so it cannot be used as the shared source of truth for a game between two users.

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

A small external database is the most realistic direction for a deployed shared-game prototype. The exact storage choice should be decided in a later implementation milestone.

## First shared prototype scope

A later implementation milestone could include:

* creating a shared game ID
* loading a game by ID
* saving FEN and move history after each legal move
* manually refreshing to see the latest state

It should not include real-time synchronization, user accounts, chat, timers, ratings, chess engine analysis, or a full backend server.

## Summary

Boardstep can move toward shared online play in small steps. This note documents the shared-game model and storage direction before adding a database or claiming shared online play.
