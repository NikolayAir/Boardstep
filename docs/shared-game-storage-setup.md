# Shared game storage setup

Status: setup note for the `v0.6.0` manual-refresh shared game storage prototype.

Boardstep uses local Streamlit session state for local practice. The shared game prototype uses external storage so that two browser sessions can load and update the same game by ID.

The current storage target is Supabase/PostgreSQL.

## Table

Recommended table name:

```text
shared_games
```

Recommended first columns:

```text
game_id text primary key
fen text not null
move_history jsonb not null
created_at timestamptz not null
updated_at timestamptz not null
last_move_number integer not null
```

The `last_move_number` column is used as a simple stale-state check. Before saving a move, the app can compare the stored move number with the move number the user loaded. If they do not match, the app should avoid silently overwriting newer game state.

## Runtime behavior

After a shared game is created or loaded, later legal moves are saved back to shared storage.

Other browser sessions do not update in real time. They use the manual refresh control to load the latest saved position for the shared game ID.

The `last_move_number` value is used as a simple stale-state guard. If the stored game changed before a move is saved, the app should show a conflict message and ask the user to refresh rather than silently overwriting newer state.

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

The first prototype uses a simple access model:

* games are loaded by game ID
* there are no user accounts yet
* there is no private invite system yet
* anyone with the game ID may be able to load that game
* this limitation should be documented in public wording if the shared prototype is exposed in the demo

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

The shared-game model remains a small manual-refresh prototype, not real-time multiplayer.
