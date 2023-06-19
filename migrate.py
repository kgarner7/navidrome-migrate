#!/usr/bin/env python3
from argparse import ArgumentParser
from hashlib import md5
from pathlib import Path
from sqlite3 import connect
from traceback import print_exc
from typing import List, NoReturn, Optional, Tuple

parser = ArgumentParser(description="Navidrome database migrator")
parser.add_argument("db_path", help="Path to your navidrome.db")
parser.add_argument(
    "old_path",
    help="The original path to your music library (either MusicFolder or ND_MUSICFOLDER",
)
parser.add_argument("new_path", help="The current path to your music library")

args = parser.parse_args()

ZERO_WIDTH_SPACE = "\u200b"


def fail(msg: str) -> NoReturn:
    print("ERROR:", msg)
    exit(-1)


db_path: str = args.db_path
old_path: str = args.old_path
new_path: str = args.new_path

if not Path(db_path).is_file():
    fail(f"The database '{db_path}' does not exist")


try:
    conn = connect(db_path, isolation_level=None)
    try:
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        # Since we are messing with media file ids, this will give us trouble.
        # defer checking foreign key constraints until the end
        cursor.execute("PRAGMA defer_foreign_keys = ON")
        cursor.execute("BEGIN")

        result: Tuple[int] = conn.execute(
            "SELECT COUNT(*) FROM media_file WHERE path LIKE ? || '%'",
            (old_path,),
        ).fetchone()
        path_count = result[0]

        result = conn.execute("SELECT COUNT(*) from media_file").fetchone()
        full_count = result[0]

        if path_count != full_count:
            raise Exception(
                f"The prefix {old_path} does not match all of the songs in your library ({path_count} vs {full_count}). Please make sure you are using the correct path"
            )

        first_file: Tuple[str] = cursor.execute(
            "SELECT path FROM media_file LIMIT 1"
        ).fetchone()
        sample_path = first_file[0]

        sample_new_path = sample_path.replace(old_path, new_path, 1)

        if not Path(sample_new_path).is_file():
            raise Exception(
                f"Could not find a file at '{sample_new_path}'. Please make sure the new path is correct"
            )

        # update media file path and hash
        media_files: List[Tuple[str, str]] = cursor.execute(
            "SELECT id, path from media_file"
        ).fetchall()
        for id, path in media_files:
            new_track_path = path.replace(old_path, new_path, 1)
            new_id = md5(new_track_path.encode()).hexdigest()

            cursor.execute(
                "UPDATE media_file SET id = ?, path = ? where id = ?",
                (new_id, new_track_path, id),
            )

            changes = (new_id, id)

            # Update ids of items that reference to this
            cursor.execute(
                "UPDATE annotation SET item_id = ? WHERE item_id = ? AND item_type = 'media_file'",
                changes,
            )

            cursor.execute(
                "UPDATE media_file_genres SET media_file_id = ? WHERE media_file_id = ?",
                changes,
            )

            cursor.execute(
                "UPDATE playlist_tracks SET media_file_id = ? WHERE media_file_id = ?",
                changes,
            )

            cursor.execute(
                "UPDATE scrobble_buffer SET media_file_id = ? WHERE media_file_id = ?",
                changes,
            )

        # Update smart playlist paths
        cursor.execute(
            "UPDATE playlist SET path = ? || SUBSTRING(path, ?) WHERE path != ''",
            (new_path, len(old_path) + 1),
        )

        # Update albums
        albums: List[Tuple[str, str, Optional[str]]] = cursor.execute(
            "SELECT id, embed_art_path, paths FROM album"
        ).fetchall()
        for id, embed, paths in albums:
            new_embed_path = embed.replace(old_path, new_path, 1)

            if paths:
                new_paths: Optional[str] = ZERO_WIDTH_SPACE.join(
                    [
                        path.replace(old_path, new_path, 1)
                        for path in paths.split(ZERO_WIDTH_SPACE)
                    ]
                )
            else:
                new_paths = paths

            cursor.execute(
                "UPDATE album SET embed_art_path = ?, paths = ? WHERE id = ?",
                (new_embed_path, new_paths, id),
            )
        cursor.execute("COMMIT")
    except:
        cursor.execute("ROLLBACK")
        raise

except Exception as e:
    print_exc()
    fail(str(e))
