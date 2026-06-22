# Shared game storage setup

Status: setup note for the first `v0.6.0` shared game storage prototype.

Boardstep uses local Streamlit session state for local practice. The first shared game prototype needs external storage so that two browser sessions can load and update the same game by ID.

The first storage target is Supabase/PostgreSQL.

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

The first prototype should use a simple access model:

* games are loaded by game ID
* there are no user accounts yet
* there is no private invite system yet
* anyone with the game ID may be able to load that game
* this limitation should be documented in public wording if the shared prototype is exposed in the demo

## Security notes

Credentials must not be committed.

Elevated Supabase keys should not be exposed in public code or browser-facing logic. Database permissions and Row Level Security should be configured deliberately for the first prototype.

The first version should remain a small manual-refresh prototype, not real-time multiplayer.
