#!/usr/bin/env python3
from argparse import ArgumentParser
from hashlib import md5
from os.path import basename, isdir, join
from pathlib import Path
from sqlite3 import connect
from shutil import move as fsmove
import sqlite3
from traceback import print_exc
from typing import List, Literal, NoReturn, Optional, Tuple

parser = ArgumentParser(description="Navidrome database migrator")
parser.add_argument("db_path", help="Path to your navidrome.db")
parser.add_argument(
    "-d",
    "--dry-run",
    action="store_true",
    default=False,
    help="If true, undo all changes before exit (useful primarily for testing)",
)

subparsers = parser.add_subparsers(
    title="Subcommands", description="Subcommands", required=True, dest="command"
)

migrate = subparsers.add_parser(
    "migrate", help="Migrate your entire library from one location to another"
)
migrate.add_argument(
    "old_path",
    help="The full path to your music library before migration",
)
migrate.add_argument(
    "new_path", help="The full path to your music library after migration"
)
migrate.add_argument(
    "-v",
    "--validation",
    choices=["full", "short", "none"],
    default="full",
    help=(
        "Whether to check for the existence of every file [full]"
        ", or just do a short sample to make sure that at least one file exists. "
        "Note that [full] validation may take a while for large libraries, and will fail"
        "if you did not migrate over every file. "
        "none will disable ALL checks of directory integrity. "
        "Use this ONLY if you are having issues with full/short because you did not migrate every file over"
    ),
)

move = subparsers.add_parser(
    "move", help="Move a file/directory to another file/directory"
)
move.add_argument(
    "old_path",
    help="The file/folder to move",
)
move.add_argument("new_path", help="The destination of the file/folder")

# Add the "changeLink" subcommand
change_link = subparsers.add_parser(
    "changeLink",
    help="Open the database and swap the system paths only without migrating files",
)
change_link.add_argument(
    "old_path",
    help="The old system path to be changed",
)
change_link.add_argument(
    "new_path",
    help="The new system path to replace the old one",
)
change_link.add_argument(
    "--windows_to_linux_path",
    action="store_true",
    default=False,
    help="Replace backslashes with forward slashes in the database paths",
)
change_link.add_argument(
    "--linux_to_windows_path",
    action="store_true",
    default=False,
    help="Replace forward slashes with backslashes in the database paths",
)

args = parser.parse_args()

ZERO_WIDTH_SPACE = "\u200b"


def fail(msg: str) -> NoReturn:
    print("ERROR:", msg)
    exit(-1)


db_path: str = args.db_path
old_path: str = args.old_path
new_path: str = args.new_path
dry_run: bool = args.dry_run
windows_to_linux_path: bool = args.windows_to_linux_path
linux_to_windows_path: bool = args.linux_to_windows_path
path_Slash_Change: List[str] = []

# Check if both --windows_to_linux_path and --linux_to_windows_path are set
if windows_to_linux_path and linux_to_windows_path:
    fail("You can only set one of --windows_to_linux_path or --linux_to_windows_path")
elif windows_to_linux_path:
    path_Slash_Change = ["\\", "/"]
elif linux_to_windows_path:
    path_Slash_Change = ["/", "\\"]

command: Literal["move", "migrate", "changeLink"] = args.command

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

        if command == "move" and isdir(new_path):
            new_path = join(new_path, basename(old_path))
            print(f"Moving to a directory. Full path is {new_path}")

        OLD_QUERY_ARGS = (old_path,)
        if command == "migrate":
            result: Tuple[int] = conn.execute(
                "SELECT COUNT(*) FROM media_file WHERE path LIKE ? || '%'",
                OLD_QUERY_ARGS,
            ).fetchone()
            path_count = result[0]

            result = conn.execute("SELECT COUNT(*) from media_file").fetchone()
            full_count = result[0]

            if path_count != full_count:
                paths: List[Tuple[str]] = conn.execute(
                    "SELECT path FROM media_file"
                ).fetchall()

                prefix = paths[0][0]
                for (path,) in paths[1:]:
                    for j in range(min(len(prefix), len(path))):
                        if prefix[j] != path[j]:
                            prefix = prefix[:j]
                            break

                raise Exception(
                    (
                        f"The prefix {old_path} does not match all of the songs in your library ({path_count} vs {full_count}).\n"
                        "Please make sure you are using the correct path.\n"
                        f"Based off of your database, the shortest path that matches all of your files is {prefix}\n"
                    )
                )

            validation_mode: Literal["full", "short", "none"] = args.validation
            if validation_mode == "none":
                sample_paths: List[Tuple[str]] = []
            elif validation_mode == "full":
                sample_paths = conn.execute(
                    "SELECT path FROM media_file WHERE path LIKE ? || '%'",
                    OLD_QUERY_ARGS,
                ).fetchall()
            else:
                sample_path: Tuple[str] = cursor.execute(
                    "SELECT path FROM media_file WHERE path LIKE ? || '%' LIMIT 1",
                    OLD_QUERY_ARGS,
                ).fetchone()
                sample_paths = [sample_path]

            for sample_path in sample_paths:
                sample_new_path = sample_path[0].replace(old_path, new_path, 1)

                if not Path(sample_new_path).is_file():
                    raise Exception(
                        f"Could not find a file at '{sample_new_path}'. Please make sure the new path is correct"
                    )

        if command == "move":
            if dry_run:
                print(f"[Dry Run] {old_path} would be moved to {new_path}")
            else:
                fsmove(old_path, new_path)
        elif command == "changeLink":
            # Update media file path and hash for the "changeLink" option
            # The intention of this option is to change the Windows path \ sign to Linux's / sign
            media_files: List[Tuple[str, str]] = cursor.execute(
                "SELECT id, path from media_file WHERE path LIKE ? || '%'",
                OLD_QUERY_ARGS,
            ).fetchall()
            for id, path in media_files:
                new_track_path = path.replace(old_path, new_path, 1)

                if path_Slash_Change:
                    new_track_path.replace(path_Slash_Change[0], path_Slash_Change[1])

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

            # Update albums and playlists paths
            cursor.execute(
                "UPDATE album SET paths = REPLACE(paths, ?, ?)",
                (old_path, new_path),
            )

            cursor.execute(
                "UPDATE playlist SET path = REPLACE(path, ?, ?) WHERE path != ''",
                (old_path, new_path),
            )
        # Update smart playlist paths
        cursor.execute(
            "UPDATE playlist SET path = ? || SUBSTRING(path, ?) WHERE path != ''",
            (new_path, len(old_path) + 1),
        )

        # Update albums embed_art_path column
        albums: List[Tuple[str, str, str]] = cursor.execute(
            "SELECT id, embed_art_path, paths FROM album"
        ).fetchall()
        for id, embed, art_paths in albums:
            new_embed_path = embed.replace(old_path, new_path, 1)

            if path_Slash_Change:
                new_embed_path.replace(path_Slash_Change[0], path_Slash_Change[1])

            if art_paths:
                new_paths: str = ZERO_WIDTH_SPACE.join(
                    [
                        path.replace(old_path, new_path, 1)
                        for path in art_paths.split(ZERO_WIDTH_SPACE)
                    ]
                )
            else:
                new_paths = art_paths

            if path_Slash_Change:
                new_paths.replace(path_Slash_Change[0], path_Slash_Change[1])

            cursor.execute(
                "UPDATE album SET embed_art_path = ?, paths = ? WHERE id = ?",
                (new_embed_path, new_paths, id),
            )
        # Update albums image_files column
        album_images: List[Tuple[str, str]] = cursor.execute(
            "SELECT id, image_files FROM album"
        ).fetchall()
        for id, image_files in album_images:
            if image_files:
                new_image_files: str = ZERO_WIDTH_SPACE.join(
                    [
                        path.replace(old_path, new_path, 1)
                        for path in image_files.split(ZERO_WIDTH_SPACE)
                    ]
                )
            else:
                continue

            if path_Slash_Change:
                new_image_files.replace(path_Slash_Change[0], path_Slash_Change[1])

            cursor.execute(
                "UPDATE album SET image_files = ? WHERE id = ?",
                (new_image_files, id),
            )

        if dry_run:
            print("[Dry Run] Migration ran successfully")
            cursor.execute("ROLLBACK")
        else:
            print("Migration ran successfully. Make sure to do a full rescan")
            cursor.execute("COMMIT")
    except:
        cursor.execute("ROLLBACK")
        raise

except Exception as e:
    print_exc()
    fail(str(e))
