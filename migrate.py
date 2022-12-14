from argparse import ArgumentParser
from pathlib import Path
from sqlite3 import connect
from typing import NoReturn

parser = ArgumentParser(description="Navidrome database migrator")
parser.add_argument("-d", "--db_path", help="Path to your navidrome.db")
parser.add_argument(
    "-o",
    "--old_path",
    help="The original path to your music library (either MusicFolder or ND_MUSICFOLDER",
)
parser.add_argument("-n", "--new_path", help="The current path to your music library")

args = parser.parse_args()


def fail(msg: str) -> NoReturn:
    print("ERROR:", msg)
    exit(-1)


if args.db_path:
    db_path: str = args.db_path
else:
    db_path = input("Please provide a path to your navidrome.db: ").strip()

if args.old_path:
    old_path: str = args.old_path
else:
    old_path = input("Please provide the original path to your music library: ").strip()

if args.new_path:
    new_path: str = args.new_path
else:
    new_path = input("Please provide the current path to your music library: ").strip()


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

        sample_new_path = sample_path.replace(old_path, new_path)

        if not Path(sample_new_path).is_file():
            raise Exception(
                f"Could not find a file at '{sample_new_path}'. Please make sure the new path is correct"
            )

        cursor.execute(
            "UPDATE media_file SET path = ? || SUBSTRING(path, ?)",
            (new_path, len(old_path) + 1),
        )

        cursor.execute(
            "UPDATE property SET id = ? WHERE id = ?",
            (f"LastScan-{new_path}", f"LastScan-{old_path}"),
        )
except Exception as e:
    fail(str(e))
