# Computer practice plan

Status: historical planning note for the initial `v0.12.0` computer-practice implementation.

Boardstep v0.12.0 should add a lightweight local computer-practice mode for solo play.

This feature should stay modest and testable. It should use simple move-selection logic on top of normal chess rules, not an external chess engine and not an AI model.

## Goals

* Add a local computer-practice mode for playing without a second human player.
* Keep chess rules, legal move validation, and game-state updates in Python.
* Keep shared games as manual-refresh human-vs-human prototypes.
* Keep the first implementation small enough to test and release safely.
* Make the feature clear in the UI without changing the existing shared-game flow.

## Non-goals

* No external chess engine integration.
* No AI/LLM-based move generation.
* No real-time multiplayer.
* No computer moves in shared games.
* No attempt to provide strong chess play in the first version.

## Proposed play modes

The app should move toward a compact game setup section with three modes:

* Local practice
* Computer practice
* Shared game

Local practice remains the default browser-session game.

Computer practice is local-only. In the first version, the user plays White and the computer replies as Black after each legal user move.

Shared game mode remains separate from computer practice. Loading, saving, or refreshing a shared game must never trigger a computer reply.

## Initial difficulty levels

The first computer-practice mode should use simple move-selection policies:

* Beginner: choose a random legal move.
* Easy: prefer checkmate, captures, checks, and promotions; otherwise choose randomly.
* Basic: use a simple one-ply material evaluation.

These levels are intentionally simple. They should be described as practice levels, not as advanced AI.

## Suggested architecture

Add a pure Python helper module:

```text
boardstep/computer_player.py
```

Suggested responsibilities:

* choose a legal computer move for a given board position;
* keep difficulty logic outside the Streamlit UI;
* return `None` when the game is already over or no legal move exists;
* avoid reading from or modifying Streamlit session state;
* avoid modifying shared-game state directly.

Suggested public helper:

```python
from typing import Literal
import random

ComputerLevel = Literal["beginner", "easy", "basic"]

def choose_computer_move(
    fen: str,
    level: ComputerLevel,
    rng: random.Random | None = None,
) -> str | None:
    ...
```

The helper should return a legal UCI move string, for example `e7e5`, or `None` when no legal move is available.

The Streamlit app should only call this helper in computer-practice mode, after a legal user move has been applied and only when it is Black to move.

The selected computer move should then be applied through the same Python move-validation path used by normal user moves.

## Testing focus

Add unit tests for the computer move selector:

* Beginner returns a legal move from the current position.
* Beginner can be made deterministic with an injected random generator.
* No move is returned for a finished game.
* Easy prefers an immediate checkmate when available.
* Easy prefers captures when no immediate mate is available.
* Basic uses material evaluation consistently.
* Invalid difficulty names are rejected.

Add mode-boundary checks for the app flow:

* computer moves are only applied in computer-practice mode;
* shared-game mode does not call or apply computer moves;
* loading, refreshing, or saving a shared game never triggers a computer reply;
* reset clears computer-practice transient state.

## UI integration notes

Add game mode state to Streamlit session state, probably:

```text
game_mode = "local" | "computer" | "shared"
computer_level = "beginner" | "easy" | "basic"
last_computer_move = None | str
```

Computer replies should happen only after a legal user move in computer-practice mode and only if the game is not over.

Typed move input and click-to-move should both continue to use the same move application path.

Reset should clear computer-related transient state.

Loading a FEN position should clear move history and computer transient state. If computer-practice mode remains active, the app should not immediately make a computer move just because a FEN was loaded.

## Shared game boundaries

Shared game mode remains human-vs-human.

Do not mix computer-practice mode with shared-game storage in v0.12.0.

When shared mode is active:

* no computer replies;
* no computer difficulty selector;
* existing manual-refresh behavior stays unchanged.

## Out of scope for v0.12.0

* Stockfish
* LLM/AI move suggestions
* real-time multiplayer
* WebSockets
* accounts or player ownership
* side assignment
* clocks
* ratings
* chat
* opening books
* engine evaluation display

## Release wording

Suggested release note:

Boardstep v0.12.0 adds a simple local computer-practice mode. The first version lets the user play White against a lightweight Python move selector with beginner-level difficulty options. Chess rules and legal move validation remain in Python, and shared games remain manual-refresh human-vs-human prototypes.
