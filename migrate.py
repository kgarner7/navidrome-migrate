from argparse import ArgumentParser
from hashlib import md5
from pathlib import Path
from sqlite3 import connect
from traceback import print_exc
from typing import NoReturn

parser = ArgumentParser(description="Navidrome database migrator")
parser.add_argument("db_path", help="Path to your navidrome.db")
parser.add_argument(
    "old_path",
    help="The original path to your music library (either MusicFolder or ND_MUSICFOLDER",
)
parser.add_argument("new_path", help="The current path to your music library")

args = parser.parse_args()


def fail(msg: str) -> NoReturn:
    print("ERROR:", msg)
    exit(-1)


db_path: str = args.db_path
old_path: str = args.old_path
new_path: str = args.new_path

if not Path(db_path).is_file():
    fail(f"The database '{db_path}' does not exist")


try:
    with connect(db_path) as conn:
        cursor = conn.cursor()

        (path_count,) = conn.execute(
            "SELECT COUNT(*) FROM media_file WHERE path LIKE ? || '%'",
            (old_path,),
        ).fetchone()

        (full_count,) = conn.execute("SELECT COUNT(*) from media_file").fetchone()

        if path_count != full_count:
            raise Exception(
                f"The prefix {old_path} does not match all of the songs in your library ({path_count} vs {full_count}). Please make sure you are using the correct path"
            )

        (sample_path,) = cursor.execute(
            "SELECT path FROM media_file LIMIT 1"
        ).fetchone()

        sample_new_path = sample_path.replace(old_path, new_path, 1)

        if not Path(sample_new_path).is_file():
            raise Exception(
                f"Could not find a file at '{sample_new_path}'. Please make sure the new path is correct"
            )

        # update media file path and hash
        cursor.execute("SELECT id, path from media_file")
        for id, path in cursor.fetchall():
            new_track_path = path.replace(old_path, new_path, 1)
            new_id = md5(new_track_path.encode()).hexdigest()

            cursor.execute(
                "UPDATE media_file SET id = ?, path = ? where id = ?",
                (new_id, new_path, id),
            )
            cursor.execute(
                "UPDATE annotation SET item_id = ? WHERE item_id = ? AND item_type = 'media_file'",
                (new_id, id),
            )

except Exception as e:
    fail(str(e))
