# Shared game storage setup

Status: current setup note for Boardstep shared-game storage.

The initial Supabase-backed manual-refresh prototype was introduced in `v0.6.0`. Optional polling-based auto-refresh was added in `v0.13.0`, shared-side assignment and turn ownership in `v0.14.0`, and history-aware repetition draw state was added in `v0.16.0`.

Boardstep uses local Streamlit session state for local and computer practice. Shared games use external storage so that multiple browser sessions can load and update the same game by ID.

The current storage target is Supabase/PostgreSQL.

## Table

Recommended table name:

```text
shared_games
```

Current columns:

```text
game_id text primary key
fen text not null
game_start_fen text
move_uci_history jsonb
move_history jsonb not null
claimed_draw_reason text
creator_side text not null default 'white'
created_at timestamptz not null
updated_at timestamptz not null
last_move_number integer not null
```

## Creator-side migration

For databases created before the creator-side field was introduced, run the SQL in `docs/sql/add-shared-game-creator-side.sql`.

Existing rows default to White. New games explicitly store the side assigned to the creator.

The `last_move_number` column is used as a stale-state check. Shared writes also require that no draw claim has already been stored, preventing a stale move or duplicate claim from overwriting a completed game.

## Repetition-state migration

For databases created before repetition draw handling was introduced, run the SQL in `docs/sql/add-shared-game-repetition-state.sql`.

The migration adds the game-start FEN, canonical UCI move history, and optional claimed-draw reason. Existing rows remain valid as legacy shared games and begin a new known-history baseline from their current FEN.

## Runtime behavior

After a shared game is created or loaded, later legal moves and claimed threefold draws are saved back to shared storage.

Other browser sessions can use the manual refresh control or optional polling-based auto-refresh to load the latest saved state. This is not push-based real-time multiplayer.

Shared updates use the stored move number and claimed-draw state as optimistic-concurrency guards. If the saved game changed before an update is written, the app shows a conflict message and asks the user to refresh rather than silently overwriting newer state.

## Local secrets

Local secrets should be stored in:

```text
.streamlit/secrets.toml
```

This file must stay out of Git.

Expected local secret names:

```toml
SUPABASE_URL = "..."
SUPABASE_KEY = "..."
```

## Deployed secrets

For Streamlit Community Cloud, the same values should be configured in the app secrets settings, not committed to the repository.

## Access model

The current prototype uses a simple access model:

* games are loaded by ID;
* there are no user accounts or private invitations;
* anyone with the ID can load the game.

## Manual verification

The shared-game setup can be verified with local Streamlit secrets before relying on the deployed demo:

1. create a shared game ID
2. load the same ID in another browser session
3. make a legal move in one session
4. manually refresh the other session
5. confirm that the latest position and move history are loaded

Do not commit local or deployed secret values.

## Security notes

Credentials must not be committed.

Elevated Supabase keys should not be exposed in public code or browser-facing logic. Database permissions and Row Level Security should be configured deliberately for the prototype.

The shared-game model remains a small polling-based prototype, not real-time multiplayer.
