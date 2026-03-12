CREATE TABLE IF NOT EXISTS player_game_data (
    userId integer PRIMARY KEY,
    last_played_game_id integer default -1,
    guesses BLOB,
    completed boolean default 0,
    won boolean default 0,
    answer varchar(255) default ""
);

CREATE TABLE IF NOT EXISTS player_stats (
    userId integer PRIMARY KEY,
    games_played integer default 0,
    games_won integer default 0
);

/*
Only one row is ever stored here
It has the bot's internal data
*/
CREATE TABLE IF NOT EXISTS internal_data (
    _id integer primary key check (_id=0),
    gameId integer default 0,
    answer varchar(255) default "",
    past_words BLOB
);