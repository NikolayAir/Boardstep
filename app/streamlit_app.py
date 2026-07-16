import sys
import time
from pathlib import Path

import chess
import streamlit as st

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from boardstep.computer_player import choose_computer_move

from boardstep.game import (
    STARTING_FEN,
    apply_uci_move,
    board_files,
    board_from_uci_history,
    board_rows,
    game_is_over,
    game_status_from_board,
    side_to_move,
    threefold_draw_can_be_claimed,
    validate_fen_position,
)

from boardstep.shared_game import (
    CREATOR_SIDE_OPTIONS,
    DEFAULT_SHARED_GAME_ROLE,
    SharedGameState,
    create_shared_game_state,
    generate_shared_game_id,
    normalize_shared_game_side,
    opposite_shared_game_side,
    resolve_creator_side,
    shared_game_move_restriction_message,
    shared_game_role_can_move,
    shared_game_state_has_update,
    shared_game_turn_guidance,
)

from boardstep.supabase_rest_storage import (
    SUPABASE_KEY_SECRET,
    SUPABASE_URL_SECRET,
    SharedGameStorageConflictError,
    SupabaseRestConfig,
    create_shared_game,
    create_supabase_rest_config,
    load_shared_game,
    save_shared_game_after_move,
    save_shared_game_draw_claim,
)

from app.ui_components import (
    render_board_area,
    render_game_panel,
)


PLAY_MODE_OPTIONS = ("local", "computer", "shared")
PLAY_MODE_LABELS = {
    "local": "Local practice",
    "computer": "Computer practice",
    "shared": "Shared game",
}

COMPUTER_LEVEL_OPTIONS = (
    "beginner",
    "easy",
    "basic",
    "intermediate",
    "hard",
)
COMPUTER_LEVEL_LABELS = {
    "beginner": "Beginner",
    "easy": "Easy",
    "basic": "Basic",
    "intermediate": "Intermediate",
    "hard": "Hard",
}

PLAYER_SIDE_OPTIONS = ("white", "black")
PLAYER_SIDE_LABELS = {
    "white": "White",
    "black": "Black",
}

SHARED_GAME_ROLE_LABELS = {
    "white": "White",
    "black": "Black",
    "observer": "Observer",
}

CREATOR_SIDE_LABELS = {
    "white": "White",
    "black": "Black",
    "random": "Random",
}


def initialize_game_state() -> None:
    """Create the Streamlit session state used by the current chess game."""
    if "fen" not in st.session_state:
        st.session_state.fen = STARTING_FEN

    if "move_history" not in st.session_state:
        st.session_state.move_history = []

    if "game_start_fen" not in st.session_state:
        st.session_state.game_start_fen = st.session_state.fen

    if "move_uci_history" not in st.session_state:
        st.session_state.move_uci_history = []

    if "claimed_draw_reason" not in st.session_state:
        st.session_state.claimed_draw_reason = None

    if "selected_square" not in st.session_state:
        st.session_state.selected_square = None

    if "click_move_error" not in st.session_state:
        st.session_state.click_move_error = None

    if "board_orientation" not in st.session_state:
        st.session_state.board_orientation = "white"

    if "shared_game_id" not in st.session_state:
        st.session_state.shared_game_id = ""

    if "shared_game_last_move_number" not in st.session_state:
        st.session_state.shared_game_last_move_number = None

    if "shared_game_status" not in st.session_state:
        st.session_state.shared_game_status = None

    if "shared_game_auto_refresh_enabled" not in st.session_state:
        st.session_state.shared_game_auto_refresh_enabled = False

    if "shared_game_last_synced_at" not in st.session_state:
        st.session_state.shared_game_last_synced_at = None

    if "shared_game_role" not in st.session_state:
        st.session_state.shared_game_role = DEFAULT_SHARED_GAME_ROLE

    if "shared_game_creator_side" not in st.session_state:
        st.session_state.shared_game_creator_side = "white"

    if "shared_game_assigned_side" not in st.session_state:
        st.session_state.shared_game_assigned_side = "white"

    if "shared_game_creator_side_selection" not in st.session_state:
        st.session_state.shared_game_creator_side_selection = "white"

    if "shared_game_pending_assigned_side" not in st.session_state:
        st.session_state.shared_game_pending_assigned_side = None

    if "game_mode" not in st.session_state:
        st.session_state.game_mode = "local"

    if "computer_level" not in st.session_state:
        st.session_state.computer_level = "beginner"

    if "player_side" not in st.session_state:
        st.session_state.player_side = "white"

    if "last_computer_move" not in st.session_state:
        st.session_state.last_computer_move = None


def clear_shared_game_session() -> None:
    """Clear shared-game session metadata."""
    st.session_state.shared_game_id = ""
    st.session_state.shared_game_last_move_number = None
    st.session_state.shared_game_status = None
    st.session_state.shared_game_auto_refresh_enabled = False
    st.session_state.shared_game_last_synced_at = None
    st.session_state.shared_game_creator_side = "white"
    st.session_state.shared_game_assigned_side = "white"
    st.session_state.shared_game_pending_assigned_side = None


def mark_shared_game_synced() -> None:
    """Record the local time of the latest successful shared-game sync."""
    st.session_state.shared_game_last_synced_at = time.strftime("%H:%M:%S")


def leave_shared_game_session() -> None:
    """Return to local practice without deleting the saved shared game."""
    clear_shared_game_session()
    st.session_state.game_mode = "local"
    st.session_state.shared_game_status = (
        "Returned to local practice. The saved shared game was not deleted."
    )


def shared_game_auto_refresh_is_paused() -> bool:
    """Return whether the current shared-game role is choosing a move."""
    if st.session_state.selected_square is None:
        return False

    return shared_game_role_can_move(
        st.session_state.shared_game_role,
        st.session_state.fen,
    )


def apply_shared_game_role_change() -> None:
    """Apply local UI updates after changing the shared-game role."""
    st.session_state.selected_square = None
    st.session_state.click_move_error = None

    if st.session_state.shared_game_role in ("white", "black"):
        st.session_state.board_orientation = st.session_state.shared_game_role


def assign_shared_game_side(side: str) -> None:
    """Assign a playable shared-game side to this browser session."""
    normalized_side = normalize_shared_game_side(side)
    st.session_state.shared_game_assigned_side = normalized_side
    st.session_state.shared_game_role = normalized_side
    st.session_state.board_orientation = normalized_side
    st.session_state.selected_square = None
    st.session_state.click_move_error = None


def queue_shared_game_side_assignment(side: str) -> None:
    """Queue a side assignment for the next full Streamlit run."""
    st.session_state.shared_game_pending_assigned_side = (
        normalize_shared_game_side(side)
    )


def apply_pending_shared_game_side_assignment() -> None:
    """Apply a queued side assignment before role widgets are instantiated."""
    pending_side = st.session_state.shared_game_pending_assigned_side

    if pending_side is None:
        return

    assign_shared_game_side(pending_side)
    st.session_state.shared_game_pending_assigned_side = None


def clear_computer_practice_session() -> None:
    """Clear computer-practice transient metadata."""
    st.session_state.last_computer_move = None


def current_game_board() -> chess.Board:
    """Reconstruct the current board with its known move history."""
    return board_from_uci_history(
        st.session_state.game_start_fen,
        st.session_state.move_uci_history,
    )


def current_game_is_over() -> bool:
    """Return whether no further moves may be played in the current game."""
    return game_is_over(
        current_game_board(),
        st.session_state.claimed_draw_reason,
    )


def current_game_status() -> str:
    """Return a history-aware status for the current game."""
    return game_status_from_board(
        current_game_board(),
        st.session_state.claimed_draw_reason,
    )


def current_game_can_claim_threefold() -> bool:
    """Return whether the current browser may claim a threefold draw."""
    if current_game_is_over():
        return False

    if st.session_state.shared_game_id:
        if not shared_game_role_can_move(
            st.session_state.shared_game_role,
            st.session_state.fen,
        ):
            return False

    elif (
        st.session_state.game_mode == "computer"
        and current_side_to_move_key() != st.session_state.player_side
    ):
        return False

    return threefold_draw_can_be_claimed(current_game_board())


def claim_threefold_draw() -> None:
    """Claim an available threefold-repetition draw."""
    if not current_game_can_claim_threefold():
        raise ValueError(
            "A threefold-repetition draw cannot be claimed in the current state."
        )

    if st.session_state.shared_game_id:
        config, _ = read_shared_game_storage_config()

        if config is None:
            raise ValueError(
                "Shared storage is not configured for this session."
            )

        expected_last_move_number = (
            st.session_state.shared_game_last_move_number
        )

        if expected_last_move_number is None:
            raise ValueError(
                "The shared game move number is unknown. "
                "Refresh the shared game before claiming a draw."
            )

        claimed_state = create_shared_game_state(
            st.session_state.shared_game_id,
            fen=st.session_state.fen,
            game_start_fen=st.session_state.game_start_fen,
            move_uci_history=st.session_state.move_uci_history,
            move_history=st.session_state.move_history,
            claimed_draw_reason="threefold_repetition",
            creator_side=st.session_state.shared_game_creator_side,
        )

        try:
            saved_state = save_shared_game_draw_claim(
                config,
                claimed_state,
                expected_last_move_number=expected_last_move_number,
            )
        except SharedGameStorageConflictError as exc:
            raise ValueError(
                "The shared game changed before the draw claim was saved. "
                "Refresh the game and try again."
            ) from exc
        except Exception as exc:
            raise ValueError(
                "The draw claim could not be saved to shared storage."
            ) from exc

        apply_shared_game_state_to_session(
            saved_state,
            status_message=(
                "Threefold repetition draw claimed and saved. "
                "The other player can refresh or use auto-refresh."
            ),
        )
        return

    st.session_state.claimed_draw_reason = "threefold_repetition"
    st.session_state.selected_square = None
    st.session_state.click_move_error = None
    clear_computer_practice_session()


def current_side_to_move_key() -> str:
    """Return the current side to move as a session-state key."""
    return side_to_move(st.session_state.fen).lower()


def is_computer_practice_turn() -> bool:
    """Return whether the local computer should move now."""
    return (
        st.session_state.game_mode == "computer"
        and not st.session_state.shared_game_id
        and not current_game_is_over()
        and current_side_to_move_key() != st.session_state.player_side
    )


def reset_game() -> None:
    """Reset the current chess game to the starting position."""
    st.session_state.fen = STARTING_FEN
    st.session_state.game_start_fen = STARTING_FEN
    st.session_state.move_uci_history = []
    st.session_state.move_history = []
    st.session_state.claimed_draw_reason = None
    st.session_state.selected_square = None
    st.session_state.click_move_error = None
    clear_computer_practice_session()

    if st.session_state.game_mode == "shared":
        st.session_state.game_mode = "local"

    clear_shared_game_session()


def save_current_shared_game_position(config: SupabaseRestConfig) -> None:
    """Save the current session position to shared storage."""
    if not st.session_state.shared_game_id:
        return

    expected_last_move_number = st.session_state.shared_game_last_move_number

    if expected_last_move_number is None:
        st.session_state.shared_game_status = (
            "This move was kept locally, but the shared game move number is unknown. "
            "Refresh the shared game before playing another move."
        )
        return

    state = create_shared_game_state(
        st.session_state.shared_game_id,
        fen=st.session_state.fen,
        game_start_fen=st.session_state.game_start_fen,
        move_uci_history=st.session_state.move_uci_history,
        move_history=st.session_state.move_history,
        claimed_draw_reason=st.session_state.claimed_draw_reason,
        creator_side=st.session_state.shared_game_creator_side,
    )

    try:
        saved_state = save_shared_game_after_move(
            config,
            state,
            expected_last_move_number=expected_last_move_number,
        )
    except SharedGameStorageConflictError:
        st.session_state.shared_game_status = (
            "This move was kept locally, but the shared game changed before it could be saved. "
            "Refresh the shared game to load the latest saved position before playing again."
        )
    except Exception:
        st.session_state.shared_game_status = (
            "This move was kept locally, but it could not be saved to shared storage. "
            "Check the shared-game storage settings, table setup, or whether the storage service is paused."
        )
    else:
        st.session_state.shared_game_last_move_number = saved_state.last_move_number
        mark_shared_game_synced()
        st.session_state.shared_game_status = (
            "Move saved. The other player can refresh manually or use auto-refresh to see it."
        )


def apply_legal_move_to_session(move_text: str) -> str:
    """Apply a legal move to the current session and return SAN notation."""
    recorded_move_text = move_text.strip().lower()

    try:
        new_fen, san = apply_uci_move(st.session_state.fen, recorded_move_text)
    except ValueError:
        if len(recorded_move_text) != 4:
            raise

        promoted_move_text = f"{recorded_move_text}q"
        new_fen, san = apply_uci_move(st.session_state.fen, promoted_move_text)
        recorded_move_text = promoted_move_text

    st.session_state.fen = new_fen
    st.session_state.move_uci_history.append(recorded_move_text)
    move_number = len(st.session_state.move_history) + 1
    st.session_state.move_history.append(
        f"{move_number}. {recorded_move_text} ({san})"
    )

    return san


def apply_computer_reply_if_needed() -> None:
    """Apply a pending local computer move when it is the computer's turn."""
    if not is_computer_practice_turn():
        return

    computer_move = choose_computer_move(
        st.session_state.fen,
        st.session_state.computer_level,
        game_start_fen=st.session_state.game_start_fen,
        move_uci_history=st.session_state.move_uci_history,
    )

    if computer_move is None:
        return

    computer_san = apply_legal_move_to_session(computer_move)
    st.session_state.last_computer_move = f"{computer_move} ({computer_san})"


def apply_move_text(move_text: str) -> None:
    """Apply a user move and update Streamlit session state."""
    if current_game_is_over():
        raise ValueError(
            "The game is over. Reset the game or load a new position to continue."
        )

    if is_computer_practice_turn():
        raise ValueError("It is the computer's turn in computer practice.")

    if st.session_state.shared_game_id:
        restriction_message = shared_game_move_restriction_message(
            st.session_state.shared_game_role,
            st.session_state.fen,
        )
        if restriction_message:
            raise ValueError(restriction_message)

    clear_computer_practice_session()
    apply_legal_move_to_session(move_text)

    if st.session_state.shared_game_id:
        config, _ = read_shared_game_storage_config()

        if config is None:
            st.session_state.shared_game_status = (
                "This move was kept locally, but shared storage is not configured. "
                "Local practice still works."
            )
        else:
            save_current_shared_game_position(config)

        return


def load_fen_position(fen_text: str) -> None:
    """Load a validated FEN position into the current session."""
    loaded_fen = validate_fen_position(fen_text)

    st.session_state.fen = loaded_fen
    st.session_state.game_start_fen = loaded_fen
    st.session_state.move_uci_history = []
    st.session_state.move_history = []
    st.session_state.claimed_draw_reason = None
    st.session_state.selected_square = None
    st.session_state.click_move_error = None
    clear_computer_practice_session()
    clear_shared_game_session()


def render_fen_load_controls() -> None:
    """Render controls for loading a position from FEN."""
    with st.expander("Load position from FEN"):
        st.caption(
            "Paste a FEN position to restore a board state. "
            "Move history will be cleared."
        )

        with st.form("fen_form"):
            fen_text = st.text_input(
                "FEN position",
                placeholder=STARTING_FEN,
            )
            fen_submitted = st.form_submit_button("Load position")

        if fen_submitted:
            try:
                load_fen_position(fen_text)
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))


def read_shared_game_storage_config() -> tuple[SupabaseRestConfig | None, str]:
    """Read shared game storage settings from Streamlit secrets."""
    try:
        url = st.secrets.get(SUPABASE_URL_SECRET)
        key = st.secrets.get(SUPABASE_KEY_SECRET)
    except Exception:
        return None, "Shared game storage is not configured for this session."

    try:
        config = create_supabase_rest_config(url, key)
    except ValueError:
        return None, "Shared game storage secrets are missing or invalid."

    return config, "Shared games are available."


def apply_shared_game_state_to_session(
    state: SharedGameState,
    *,
    status_message: str,
) -> None:
    """Load shared game state into the current Streamlit session."""
    st.session_state.fen = state.fen
    st.session_state.game_start_fen = state.game_start_fen
    st.session_state.move_uci_history = list(state.move_uci_history)
    st.session_state.move_history = list(state.move_history)
    st.session_state.claimed_draw_reason = state.claimed_draw_reason

    st.session_state.selected_square = None
    st.session_state.click_move_error = None
    st.session_state.shared_game_id = state.game_id
    st.session_state.shared_game_creator_side = state.creator_side
    st.session_state.shared_game_last_move_number = state.last_move_number
    st.session_state.shared_game_status = status_message

    mark_shared_game_synced()
    clear_computer_practice_session()


def create_shared_game_from_current_session(
    config: SupabaseRestConfig,
    *,
    creator_side: str,
) -> SharedGameState:
    """Create a shared game from the current local session state."""
    game_id = generate_shared_game_id()
    state = create_shared_game_state(
        game_id,
        fen=st.session_state.fen,
        game_start_fen=st.session_state.game_start_fen,
        move_uci_history=st.session_state.move_uci_history,
        move_history=st.session_state.move_history,
        claimed_draw_reason=st.session_state.claimed_draw_reason,
        creator_side=creator_side,
    )

    return create_shared_game(config, state)


def refresh_current_shared_game(config: SupabaseRestConfig) -> bool:
    """Refresh the shared game and report whether saved state changed."""
    active_game_id = st.session_state.shared_game_id

    if not active_game_id:
        return False

    try:
        refreshed_state = load_shared_game(config, active_game_id)
    except Exception:
        st.session_state.shared_game_status = (
            "Shared game could not be refreshed. "
            "Check the shared-game storage settings, table setup, or whether the storage service is paused."
        )
        return False

    if refreshed_state is None:
        st.session_state.shared_game_status = (
            "The active shared game ID was not found. "
            "Check that the ID was copied correctly."
        )
        return False

    has_update = shared_game_state_has_update(
        previous_last_move_number=(
            st.session_state.shared_game_last_move_number
        ),
        previous_claimed_draw_reason=(
            st.session_state.claimed_draw_reason
        ),
        refreshed_state=refreshed_state,
    )

    if has_update:
        status_message = "Updated to the latest saved game state."
    else:
        status_message = "No new move or game result found yet."

    apply_shared_game_state_to_session(
        refreshed_state,
        status_message=status_message,
    )

    return has_update


def render_shared_game_controls() -> None:
    """Render shared game create/load controls."""
    active_game_id = st.session_state.shared_game_id

    with st.expander("Shared game"):
        if active_game_id:
            st.markdown("**Mode:** Shared game mode")
        else:
            st.markdown("**Mode:** Shared game setup")

        if active_game_id:
            st.caption(
                "Send the game ID to the other player. "
                "After either player moves, the other browser can refresh manually "
                "or enable auto-refresh to check for the latest board."
            )
        else:
            st.caption(
                "Create a shared game ID or load one from another player. "
                "Each browser can refresh manually or enable auto-refresh "
                "after loading a shared game."
            )

        config, _ = read_shared_game_storage_config()

        if config is None:
            st.info("Shared games are not available in this session.")
            st.caption(
                "Local practice still works. Shared games need storage settings "
                "to be configured first."
            )
        elif not active_game_id:
            st.success("Shared games are available.")

        if active_game_id:
            st.markdown("**Active shared game ID**")
            st.code(active_game_id, language="text")

            assigned_side = st.session_state.shared_game_assigned_side
            st.markdown(
                f"**Your color:** {SHARED_GAME_ROLE_LABELS[assigned_side]}"
            )

            st.radio(
                "Play as",
                options=(assigned_side, "observer"),
                format_func=lambda value: SHARED_GAME_ROLE_LABELS[value],
                horizontal=True,
                key="shared_game_role",
                on_change=apply_shared_game_role_change,
                help=(
                    "Play as your assigned color, or choose Observer "
                    "to watch without making moves."
                ),
            )

            st.caption(
                "Your color is saved for this browser session. "
                "Choose Observer to watch without making moves."
            )

            leave_col, _ = st.columns([1.3, 5.7])

            with leave_col:
                st.button(
                    "Leave shared game",
                    help="Return to local practice without deleting the saved shared game.",
                    use_container_width=True,
                    on_click=leave_shared_game_session,
                )

        if st.session_state.shared_game_status:
            st.info(st.session_state.shared_game_status)

        if not active_game_id:
            create_disabled = config is None

            st.radio(
                "Your color",
                options=CREATOR_SIDE_OPTIONS,
                format_func=lambda value: CREATOR_SIDE_LABELS[value],
                horizontal=True,
                key="shared_game_creator_side_selection",
                disabled=create_disabled,
                help=(
                    "Choose White or Black, or let Boardstep pick randomly. "
                    "The other player gets the opposite color."
                ),
            )
            st.caption(
                "The current position decides who moves next. "
                "Wait for the other player when it is their turn."
            )
            if st.button(
                "Create shared game",
                disabled=create_disabled,
                help="Save the current board as a new shared game.",
            ):
                if config is not None:
                    try:
                        creator_side = resolve_creator_side(
                            st.session_state.shared_game_creator_side_selection
                        )
                        state = create_shared_game_from_current_session(
                            config,
                            creator_side=creator_side,
                        )
                    except Exception:
                        st.error(
                            "Shared game could not be created. "
                            "Check the shared-game storage settings, table setup, or whether the storage service is paused."
                        )
                    else:
                        assigned_label = SHARED_GAME_ROLE_LABELS[
                            state.creator_side
                        ]
                        apply_shared_game_state_to_session(
                            state,
                            status_message=(
                                f"Shared game created. You are playing "
                                f"{assigned_label}. Send the game ID to the other player."
                            ),
                        )
                        queue_shared_game_side_assignment(state.creator_side)
                        st.rerun()

        load_container = (
            st.expander("Switch to an existing shared game")
            if active_game_id
            else st.container()
        )

        with load_container:
            with st.form("shared_game_load_form"):
                requested_game_id = st.text_input(
                    "Load shared game by ID",
                    placeholder="Paste a shared game ID.",
                    disabled=config is None,
                )

                load_submitted = st.form_submit_button(
                    "Load shared game",
                    disabled=config is None,
                )

        if load_submitted and config is not None:
            normalized_game_id = requested_game_id.strip()

            if not normalized_game_id:
                st.warning("Enter a shared game ID before loading a shared game.")
            else:
                try:
                    loaded_state = load_shared_game(config, normalized_game_id)
                except ValueError:
                    st.error("Enter a valid shared game ID.")
                except Exception:
                    st.error(
                        "Shared game could not be loaded. "
                        "Check the shared-game storage settings, table setup, or whether the storage service is paused."
                    )
                else:
                    if loaded_state is None:
                        st.warning(
                            "No shared game was found for that ID. "
                            "Check that the ID was copied correctly."
                        )
                    else:
                        assigned_side = opposite_shared_game_side(
                            loaded_state.creator_side
                        )
                        assigned_label = SHARED_GAME_ROLE_LABELS[assigned_side]
                        apply_shared_game_state_to_session(
                            loaded_state,
                            status_message=(
                                f"Shared game loaded. You are playing "
                                f"{assigned_label}. Refresh manually or enable auto-refresh "
                                f"to see the other player's moves."
                            ),
                        )
                        queue_shared_game_side_assignment(assigned_side)
                        st.rerun()


@st.fragment(run_every="3s")
def render_shared_game_auto_refresh(config: SupabaseRestConfig | None) -> None:
    """Render and run optional polling-based shared-game auto-refresh."""
    if not st.session_state.shared_game_id:
        return

    auto_refresh_enabled = st.toggle(
        "Auto-refresh shared game",
        key="shared_game_auto_refresh_enabled",
        disabled=config is None,
        help="Poll shared storage every few seconds while this browser is in shared game mode.",
    )

    last_synced_at = st.session_state.shared_game_last_synced_at or "not yet"
    status_text = "on" if auto_refresh_enabled else "off"
    st.caption(f"Auto-refresh: {status_text}. Last synced: {last_synced_at}.")

    if config is None:
        st.caption("Shared-game storage is not configured for this session.")
        return

    if not auto_refresh_enabled:
        return

    if shared_game_auto_refresh_is_paused():
        st.caption("Auto-refresh paused while you are choosing a move.")
        return

    refreshed_has_update = refresh_current_shared_game(config)

    if refreshed_has_update:
        st.rerun()

    st.caption("Waiting for opponent move...")


def render_shared_game_refresh_shortcut() -> None:
    """Render a board-side refresh shortcut for active shared games."""
    if not st.session_state.shared_game_id:
        return

    config, _ = read_shared_game_storage_config()

    st.write("")
    st.markdown("**Shared game**")

    turn_guidance = shared_game_turn_guidance(
        st.session_state.shared_game_role,
        st.session_state.fen,
    )

    if turn_guidance == "Your move.":
        st.success(turn_guidance)
    else:
        st.info(turn_guidance)

    if st.button(
        "Refresh shared game",
        disabled=config is None,
        help="Reload the latest saved position for the active shared game ID.",
    ):
        if config is not None:
            refresh_current_shared_game(config)
            st.rerun()

    st.caption("Check for the other player’s latest move.")
    render_shared_game_auto_refresh(config)


def render_app_header() -> None:
    """Render the compact application heading."""
    st.title("Boardstep")
    st.caption(
        "Click-to-move chess practice with local, computer, and shared game modes."
    )


def render_game_setup() -> None:
    """Render play-mode controls for local, computer, and shared practice."""
    with st.container(border=True):
        st.subheader("Game setup")

        selected_mode = st.radio(
            "Play mode",
            options=PLAY_MODE_OPTIONS,
            format_func=lambda value: PLAY_MODE_LABELS[value],
            horizontal=True,
            key="game_mode",
        )

        if selected_mode != "shared" and st.session_state.shared_game_id:
            clear_shared_game_session()

        if selected_mode == "local":
            st.caption("Practice locally in this browser session.")
            return

        if selected_mode == "computer":
            st.caption(
                "Choose a side. The computer replies when it is its turn."
            )
            st.radio(
                "You play",
                options=PLAYER_SIDE_OPTIONS,
                format_func=lambda value: PLAYER_SIDE_LABELS[value],
                horizontal=True,
                key="player_side",
                on_change=reset_game,
            )

            if st.session_state.board_orientation != st.session_state.player_side:
                st.session_state.board_orientation = st.session_state.player_side

            st.radio(
                "Practice level",
                options=COMPUTER_LEVEL_OPTIONS,
                format_func=lambda value: COMPUTER_LEVEL_LABELS[value],
                horizontal=True,
                key="computer_level",
                on_change=reset_game,
            )

            with st.expander("What do the levels mean?"):
                st.markdown(
                    "- **Beginner:** random legal moves.\n"
                    "- **Easy:** prefers immediate mates, captures, checks, and promotions.\n"
                    "- **Basic:** chooses moves using simple material scoring.\n"
                    "- **Intermediate:** looks one reply ahead and uses lightweight positional scoring.\n"
                    "- **Hard:** uses bounded deeper search and tactical continuation analysis."
                )

            st.caption("Changing side or level starts a new game.")

            return

        render_shared_game_controls()


def main() -> None:
    st.set_page_config(page_title="Boardstep", layout="wide")
    initialize_game_state()
    apply_pending_shared_game_side_assignment()
    render_app_header()
    render_game_setup()

    if is_computer_practice_turn():
        with st.spinner("Computer is thinking..."):
            apply_computer_reply_if_needed()

    board_col, game_col = st.columns([1.65, 1], gap="large")

    with board_col:
        with st.container(border=True):
            _, orientation_col, _ = st.columns([0.85, 1.9, 0.25], gap="small")

            with orientation_col:
                orientation_locked_by_shared_role = (
                    bool(st.session_state.shared_game_id)
                    and st.session_state.shared_game_role in ("white", "black")
                )

                board_orientation = st.radio(
                    "Board orientation",
                    options=("white", "black"),
                    format_func=lambda value: (
                        "White at bottom" if value == "white" else "Black at bottom"
                    ),
                    horizontal=True,
                    key="board_orientation",
                    label_visibility="collapsed",
                    disabled=orientation_locked_by_shared_role,
                    help=(
                        "This changes only your local board view. "
                        "It is not saved to shared games."
                    ),
                )

            rows = board_rows(st.session_state.fen, orientation=board_orientation)
            files = board_files(board_orientation)
            render_board_area(rows, files, apply_move_text)

    with game_col:
        with st.container(border=True):
            render_shared_game_refresh_shortcut()

            render_game_panel(
                fen=st.session_state.fen,
                status_text=current_game_status(),
                can_claim_threefold=current_game_can_claim_threefold(),
                claim_threefold_draw=claim_threefold_draw,
                move_history=st.session_state.move_history,
                apply_move=apply_move_text,
                reset_game=reset_game,
                render_fen_load_controls=render_fen_load_controls,
                game_mode=st.session_state.game_mode,
                shared_game_active=bool(st.session_state.shared_game_id),
                computer_level=st.session_state.computer_level,
                player_side=st.session_state.player_side,
                last_computer_move=st.session_state.last_computer_move,
            )


if __name__ == "__main__":
    main()
