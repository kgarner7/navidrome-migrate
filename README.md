# Navidrome Migration Script

Normally, if you change the path to your music library, you will lose all of your ratings and play metadata (play counts, last played, etc).
This is because Navidrome sees new paths to your music, and will remove the old ones.
The purpose of this script is to update the paths in Navidrome so you can keep your metadata if you have to move your music library.

## What it does
To make Navidrome recognize your new library, you have to two things:
1. Update the paths of all of your songs to point to the new location
2. Set the `LastScan-` property corresponding to your new path. If this is not set, then Navidrome will assume this is a new library.

If you are comfortable with SQL, then this can all be accomplished with the below code
(replacing `OLD_PATH` with the old path to your music library, and `NEW_PATH` as the new path).
Although this is in a transaction, I would recommend running this while Navidrome is stopped.

```sql
BEGIN;
UPDATE media_file
SET path = "NEW_PATH" || SUBSTRING(path, LENGTH("OLD_PATH") + 1);

UPDATE property
SET id = "LastScan-NEW_PATH"
WHERE id = "LastScan-OLD_PATH";
COMMIT;
```

## How to use this script

Usage:
1. Stop Navidrome.
1. Make note of the original path to your music library. 
This is the `MusicFolder` (`navidrome.toml`) or `ND_MUSICFOLDER` (environment variable) property
1. Run the migration script: `python migrate.py -d PATH_TO_ORIGINAL_DB -o ORIGINAL_MUSIC_FOLDER PATH_TO_NEW_DB -n NEW_MUSIC_FOLDER`, or just `python migrate.py` and input those values as needed.
1. Change the `MusicFolder`/`ND_MUSICFOLDER` variable to point to the new location of your library.
1. Start Navidrome. 