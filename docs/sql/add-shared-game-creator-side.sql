alter table public.shared_games
add column if not exists creator_side text not null default 'white';

alter table public.shared_games
drop constraint if exists shared_games_creator_side_check;

alter table public.shared_games
add constraint shared_games_creator_side_check
check (creator_side in ('white', 'black'));
