# Clickable board component plan

Related issue: #29

## Goal

Prototype a clickable main chessboard for Boardstep.

The goal is to let users select a source square and a target square directly on the primary visual board, instead of using a separate square-button board for normal play.

This should improve the main playing experience while keeping Boardstep's existing Python chess logic, shared-game behavior, and fallback controls intact.

## Current state

Boardstep currently has:

- a styled visual chessboard for readability
- separate square-button controls for click-based moves
- typed UCI input as a fallback
- Python move validation using the existing chess helpers
- shared-game create, load, refresh, and save behavior

This works, but the primary visual board is not interactive. A clickable main board would make the app feel more natural to play.

## Preferred approach

Investigate a small Streamlit custom component for the main board interaction.

The component should stay focused on board clicks only. Python should remain the source of truth for chess rules and legal move validation.

The first prototype should avoid a broad frontend rewrite.

## Scope

The prototype should:

- report clicked squares back to Python
- support source-square selection followed by target-square selection
- preserve existing Python legal move validation
- update the board after a legal move
- keep move history working
- keep shared-game save/load/refresh behavior unchanged
- keep typed UCI input available
- keep the current square-button controls as an optional fallback and coordinate-practice tool

The existing square-button controls can be moved into an expander named:

Coordinate practice controls

Suggested description:

Use these controls to practice square names or as a fallback for making moves.

## Technical boundaries

- Prefer Streamlit Custom Components v2 if the prototype remains small and maintainable.
- TypeScript may be added for the frontend component.
- React should only be added if it clearly simplifies the component structure.
- Do not reimplement chess rules in TypeScript.
- Do not move legal move validation into the browser.
- Do not change shared-game storage.
- Do not add real-time multiplayer.
- Do not add a chess engine.
- Do not remove typed UCI input.
- Do not remove FEN tools.

## Acceptance criteria

- A user can select a source square on the main board.
- A user can select a target square on the main board.
- Legal moves still use the existing Python validation path.
- Illegal moves still produce user-facing feedback.
- The board updates after a legal move.
- Move history continues to update.
- Shared-game move saving continues to work.
- Coordinate controls remain available as an optional practice/fallback section.
- Existing tests pass.
- The deployed Streamlit app remains functional.

## Validation plan

Run the existing project checks:

- python -m compileall app boardstep tests
- python -m pytest -q
- git diff --check

Also manually check:

- source-square selection
- target-square selection
- legal move application
- illegal move feedback
- local game behavior
- shared-game move behavior
- coordinate practice controls
- typed move fallback
- FEN tools

## Non-goals

- drag-and-drop pieces
- animations
- real-time multiplayer
- computer opponent
- chess analysis
- mobile-specific redesign
- general frontend rewrite
