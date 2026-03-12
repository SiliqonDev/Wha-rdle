CREATE TABLE IF NOT EXISTS player_game_data (
    userId integer PRIMARY KEY,
    last_played_game_id integer default -1,
    guesses BLOB,
    completed boolean default 0,
    won boolean default 0,
    answer char(5) default ""
);

CREATE TABLE IF NOT EXISTS player_stats (
    userId integer PRIMARY KEY,
    games_played integer default 0,
    games_won integer default 0,
    win_streak integer default 0
);

/*
Only one row is ever stored here
It has current game's info
*/
CREATE TABLE IF NOT EXISTS current_game_info (
    _id integer primary key check (_id=0),
    gameId integer default 0,
    answer char(5) default "",
    participants BLOB, /* all players who participated in this game */
    past_words BLOB /* words from past words to avoid early repeats */
);