alter table public.shared_games
add column if not exists game_start_fen text;

alter table public.shared_games
add column if not exists move_uci_history jsonb;

alter table public.shared_games
add column if not exists claimed_draw_reason text;

alter table public.shared_games
drop constraint if exists shared_games_move_uci_history_array_check;

alter table public.shared_games
add constraint shared_games_move_uci_history_array_check
check (
    move_uci_history is null
    or jsonb_typeof(move_uci_history) = 'array'
);

alter table public.shared_games
drop constraint if exists shared_games_claimed_draw_reason_check;

alter table public.shared_games
add constraint shared_games_claimed_draw_reason_check
check (
    claimed_draw_reason is null
    or claimed_draw_reason = 'threefold_repetition'
);
