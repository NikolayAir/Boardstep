# Clickable board component

Status: historical planning and implementation note for the clickable main board work. The first clickable-board implementation was added in `v0.8.0`, and the board component assets were separated into HTML, CSS, and JavaScript files during `v0.11.0`.

Related issue: #29

## Goal

The goal was to let users select a source square and a target square directly on the primary visual board, instead of using a separate square-button board for normal play.

This improved the main playing experience while keeping Boardstep's existing Python chess logic, shared-game behavior, and fallback controls intact.

## Current state

Boardstep now has:

- a clickable main chessboard rendered through a lightweight Streamlit component
- separate HTML, CSS, and JavaScript assets for the board component
- source-square selection followed by target-square selection
- legal-target highlighting after a source square is selected
- Python move validation using the existing chess helpers
- typed UCI input as a fallback
- coordinate practice controls as an optional fallback and square-name practice tool
- shared-game create, load, refresh, and save behavior

Python remains the source of truth for chess rules and legal move validation. The browser-side component reports square clicks back to Python and does not reimplement chess rules.

## Implemented approach

The implemented version uses a small Streamlit component for the main board interaction.

The component stays focused on board rendering and square-click reporting. It does not contain chess-rule logic, game-state ownership, shared-game storage logic, or real-time multiplayer behavior.

The board component assets are kept in:

```text
app/components/clickable_board.html
app/components/clickable_board.css
app/components/clickable_board.js
```

The Python rendering and click handling live in:

```text
app/ui_components.py
```

The main application state and shared-game flow remain in:

```text
app/streamlit_app.py
```

## Behavior

The clickable board supports this flow:

1. The board is rendered from the current FEN-derived board rows.
2. The user clicks a source square.
3. Python stores the selected source square in Streamlit session state.
4. Legal target squares are computed in Python and shown on the board.
5. The user clicks a target square.
6. Python builds a UCI move from the selected source and target squares.
7. The existing Python move-validation path applies or rejects the move.
8. After a legal move, the FEN and move history are updated.
9. In shared-game mode, the updated position is saved to shared storage.
10. Other sessions can load the latest saved shared-game state either by manual refresh or by enabling optional polling-based auto-refresh.

## Technical boundaries

The implementation keeps these boundaries:

- chess rules and legal move validation stay in Python
- the browser-side component reports square clicks only
- shared-game storage is unchanged
- shared games use manual refresh or optional polling-based auto-refresh, not real-time multiplayer
- typed UCI input and FEN tools remain available
- coordinate practice controls remain available as an optional fallback

The current implementation uses plain JavaScript. TypeScript or React are not required for the current component.

## Validation

The expected checks are:

```zsh
python -m compileall app boardstep tests
python -m pytest -q
git diff --check
```

Manual checks should include:

- source-square selection
- target-square selection
- legal move application
- illegal move feedback
- legal-target highlighting
- local game behavior
- shared-game move saving
- shared-game manual refresh
- coordinate practice controls
- typed move fallback
- FEN tools

## Non-goals

The clickable-board work does not include:

- drag-and-drop pieces
- animations
- real-time multiplayer
- computer opponent
- chess analysis
- mobile-specific redesign
- general frontend rewrite
