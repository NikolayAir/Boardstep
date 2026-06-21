# Boardstep

Boardstep is a browser-based chess practice app for learning chess logic, validating legal moves, and playing through positions in a simple web interface.

The project starts with a local chess baseline: board state, legal move validation, simple move input, move history, and tests.

## Current scope

- Python + Streamlit app
- chess rules handled through a Python chess library
- simple move input
- legal move validation
- move history
- pytest checks

## Planned later

- clearer board display
- beginner-friendly learning flow
- chess exercises or puzzles
- remote turn-based play after the local baseline is stable

## Not included yet

- online multiplayer
- chess engine
- AI chess coach
- user accounts
- real-time backend

## Run locally

python -m streamlit run app/streamlit_app.py

## Checks

python -m compileall app boardstep tests
python -m pytest -q
