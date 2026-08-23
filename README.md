# Boardstep

Boardstep is a chess practice app for local play, computer practice, and shared games.

**Core:** Python · `python-chess`

**Web app:** Streamlit · JavaScript/CSS chessboard · [Live demo](https://boardstep.streamlit.app)

**Testing and CI:** pytest · Ruff · GitHub Actions

![Boardstep chess practice interface](docs/assets/boardstep-app-overview.png)

## Key capabilities

* **Local practice** — play legal moves on the interactive board, inspect legal targets and move history, switch board orientation, load or copy positions in Forsyth-Edwards Notation (FEN), and handle repetition draws.
* **Computer practice** — play as White or Black against Boardstep's Python computer opponent, using its own move-selection logic across five practice levels, from random legal moves to bounded alpha-beta search.
* **Shared games** — create or join games through a shared game ID, use side assignment or Observer mode, and synchronise saved state through manual refresh or optional polling-based auto-refresh.
* **Validated game records** — validate game history independently of storage, derive move history in Standard Algebraic Notation (SAN) together with result and termination information, produce deterministic serialisations in JSON and Portable Game Notation (PGN), and generate concise summaries.

## Architecture

```mermaid
flowchart TB
    UI["Streamlit app"] --> Board["JavaScript/CSS chessboard"]
    Board -->|"square click"| Handler["Python UI handler"]
    Handler --> State["Streamlit session state"]

    State --> Rules["Python chess/domain logic<br/>python-chess"]
    Rules --> State
    State --> UI

    State -. "computer turn" .-> Computer["Boardstep computer opponent"]
    Computer -. "selected legal move" .-> Rules

    State -. "shared-game state" .-> Sync["Shared-game synchronisation"]
    Sync -->|"save"| Storage["Supabase/PostgreSQL<br/>via REST"]
    Storage -->|"load saved state"| Sync
    Sync -.-> State

    History["Starting FEN + canonical move history"] --> Record["Validated game record"]
    Record --> JSON["Deterministic JSON"]
    Record --> PGN["Deterministic PGN"]
    Record --> Summary["Concise game summary"]
```

Python owns chess rules, move validation, computer logic, repetition handling, and game-record processing, with `python-chess` providing the rules and notation foundation. Streamlit coordinates the application and browser-session state, while the JavaScript/CSS chessboard handles direct board interaction and presentation.

Optional external storage is confined to shared-game persistence and synchronisation. The validated game-record layer is independent of both Streamlit and shared-game storage.

## Practice modes

### Local practice

Local practice uses the interactive board without requiring shared-game storage.

* select source and target squares directly on the board and inspect legal targets;
* view move history and highlight the latest completed move;
* scale the board to the available browser width and switch its orientation;
* use coordinate controls or typed Universal Chess Interface (UCI) move strings as fallback input;
* claim threefold draws while fivefold repetition ends the game automatically;
* copy the current position as FEN or load a position from FEN.

FEN represents the current chess position but not its preceding move history. Loading a FEN therefore clears the current move history and establishes a new repetition-history baseline.

### Computer practice

Computer practice uses Boardstep's own Python move-selection logic and does not rely on Stockfish or another external chess engine. You can play as White or Black at five practice levels:

* **Beginner** — selects random legal moves.
* **Easy** — prefers immediate mates, captures, checks, and promotions.
* **Basic** — uses simple material scoring.
* **Intermediate** — uses opening priorities, looks one reply ahead, and applies lightweight positional scoring.
* **Hard** — uses bounded alpha-beta search with tactical extensions for captures, promotions, and check evasions.

Full move history is preserved so automatic fivefold draws are detected at every level. Intermediate and Hard also account for claimable threefold outcomes during move evaluation, while the human player can claim an available threefold draw on their turn.

The game panel shows the selected practice level and latest computer move. The board remains visible with `Computer thinking…` while a reply is calculated, and move input is disabled until that reply is ready. Changing side or practice level starts a new computer-practice game.

Simple four-character promotion input defaults to queen promotion when legal.

## Shared games

Shared-game features require configured external storage. One browser session creates a shared game ID and chooses White, Black, or Random. Another browser session that loads the same ID is assigned the opposite colour. Each session can play only as its locally assigned colour or switch to Observer mode.

Board orientation, move permissions, and turn guidance follow the local assignment. The interface shows `Your turn`, waiting, or read-only Observer guidance and disables move controls when the browser cannot move.

After a move, Boardstep attempts to save the updated state to shared storage. Another session can use `Refresh shared game` or optional auto-refresh to check for saved state. A refresh that finds no update normally preserves the current local move selection; failed-save recovery can instead reapply the persisted shared state.

Canonical UCI move history is stored with the shared game so repetition behaviour remains history-aware. The assigned side to move can claim an available threefold draw; the saved claim becomes visible to other sessions after refresh. Fivefold repetition ends the game automatically.

Leaving shared-game mode returns the current browser session to local practice without deleting the saved shared game.

Colour assignment and Observer mode provide browser-session guidance and do not establish protected player ownership. Additional browser sessions that load the same game ID can receive the same joining colour, and anyone with the game ID can load the game.

Synchronisation uses manual refresh or polling and does not use a live WebSocket connection. There are no accounts, protected player ownership, private invitations, clocks, ratings, chat, or chess-engine analysis.

See [`docs/shared-game-flow.md`](docs/shared-game-flow.md) for the design note and [`docs/shared-game-storage-setup.md`](docs/shared-game-storage-setup.md) for storage setup.

## Validated game records

Boardstep builds immutable game records from a starting FEN and canonical UCI move history. These records are independent of shared-game storage.

The game-record layer can:

* replay and validate every recorded move;
* derive SAN move history, final FEN, game result, termination reason, and an optional claimed-draw reason;
* serialise records deterministically as JSON or PGN with the game result;
* include `FEN` and `SetUp` PGN headers for non-standard starting positions;
* preserve side-to-move and fullmove numbering from custom starting FENs in PGN output;
* derive concise summaries containing the outcome, individual move count, latest SAN move, starting-position type, and termination-specific text.

These capabilities are tested domain-layer APIs.

## Scope

Boardstep uses click-to-move and does not provide drag-and-drop. Local and computer practice are session-based and do not provide persistent personal game history. Shared games require configured external storage and do not provide account-backed player ownership.

The computer opponent is designed for bounded practice and does not use an external chess engine or provide Elo-calibrated strength. Game-record review, summaries, and JSON/PGN download controls are not currently exposed in Streamlit.

## Local setup

To run Boardstep locally with Python 3.12, create and activate a virtual environment, then install the application dependencies:

```zsh
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Start the application from the repository root:

```zsh
python -m streamlit run app/streamlit_app.py
```

Shared-game storage is optional for local and computer practice. To configure shared games, see [`docs/shared-game-storage-setup.md`](docs/shared-game-storage-setup.md).

## Verification

Install the development dependencies:

```zsh
python -m pip install -r requirements-dev.txt
```

Run the local checks:

```zsh
python -m pip check
python -m ruff check app boardstep tests
python -m compileall app boardstep tests
python -m pytest -q
git diff --check
```

GitHub Actions runs dependency checks, Ruff linting, Python compilation, and the pytest test suite on Python 3.12 for pull requests, pushes to `main`, and manually triggered workflow runs.

## Releases

Versioned release notes are available in [GitHub Releases](https://github.com/NikolayAir/Boardstep/releases).

## Security

Report suspected vulnerabilities through GitHub Private Vulnerability Reporting. See [SECURITY.md](SECURITY.md) for details.

## Licence

Copyright © 2026 Nikolay Popov. All rights reserved.

No open-source licence is granted for project-authored material.

This public repository may be viewed and forked through GitHub as permitted by GitHub's Terms of Service. Any additional copying, redistribution, modification, or reuse of project-authored material requires prior permission, except as otherwise permitted by applicable law.

Third-party dependencies remain subject to their respective licences.
