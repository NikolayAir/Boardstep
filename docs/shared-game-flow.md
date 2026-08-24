# Shared turn-based game flow

Status: historical design note for the shared turn-based game direction, linked to Issue #16. A first manual-refresh shared game prototype was implemented during the `v0.6.0` milestone.

Boardstep started as a session-based chess practice app. Local practice still uses per-session state, while the shared-game prototype uses external storage so another browser session can load and refresh the same game by ID.

This note documents the intended direction for shared turn-based play. The initial shared-game implementation used manual refresh and was not real-time multiplayer.

## Goal

The goal is to let one player create a shared game, send a game ID to another player, and continue the same chess game from different browser sessions.

The first shared version is deliberately simple turn-based play with manual refresh, not real-time multiplayer.

## Later documented baseline

By `v0.14.0`, Boardstep supported:

* legal move validation through the `chess` Python library
* board state represented by FEN
* move history
* click-based move input on the main board
* typed UCI move input as a fallback
* FEN loading for shareable positions
* legal-target feedback after selecting a piece
* manual-refresh shared games backed by external storage
* a deployed Streamlit demo

The shared-game prototype used external storage because Streamlit session state is local to one browser session and cannot be used as the shared source of truth for a game between two users.

## Initial manual-refresh flow

The initial shared-game prototype worked like this:

1. Player A creates a shared game.
2. The app creates a random game ID.
3. The initial game state is saved in external storage.
4. Player A sends the game ID to Player B.
5. Player B loads the same game ID in another browser session.
6. Each move is validated in Python before it is saved.
7. The updated FEN and move history are stored.
8. The other player presses `Refresh shared game` to load the latest saved position.

Manual refresh is intentional for the first shared version.

## State to store

A shared game needs at least:

* `game_id`
* current `fen`
* move history
* creator side
* creation timestamp
* last update timestamp
* last move number

The v0.14.0-era setup used this table shape:

```text
shared_games
------------
game_id text primary key
fen text not null
move_history jsonb not null
creator_side text not null default 'white'
created_at timestamptz not null
updated_at timestamptz not null
last_move_number integer not null
```

The side to move can be derived from the FEN, so it does not need to be stored separately in the first version.

## Storage direction

Streamlit session state is not suitable for shared games because it is not shared between users.

Local files or local SQLite can be useful for local experiments and tests, but they should not be treated as reliable deployed shared storage.

A small external database was the most realistic direction for the initial deployed shared-game prototype. The initial implementation used Supabase/PostgreSQL through REST from the Python Streamlit app.

## First shared prototype scope

The initial shared prototype included:

* creating a shared game ID
* loading a game by ID
* saving FEN and move history after each legal move
* manually refreshing to see the latest state
* a simple stale-state check using the last move number

It did not include real-time synchronization, user accounts, private invites, chat, timers, ratings, chess engine analysis, or a full backend server.

## Summary

Boardstep introduced shared online play in small steps. This note documents the initial shared-game model and storage direction for the manual-refresh prototype.
