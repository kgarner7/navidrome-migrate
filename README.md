# Navidrome Migration Script

Normally, if you change the path to your music library, you will lose all of your ratings and play metadata (play counts, last played, etc).
This is because Navidrome sees new paths to your music, and will remove the old ones.
The purpose of this script is to update the paths in Navidrome so you can keep your metadata if you have to move your music library.

## What it does

To make Navidrome recognize your new library, you have to make your media files consistent.
This requires two things:

1. The media files should point to the new path
2. The ID of your the file should be md5sum(new path)

## How to use this script

### Full Library Migration

This is useful if you have changed the path to your entire library (e.g. migrating from one machine to another, different host path)

Usage:

1. Stop Navidrome.
2. Back up your database (make a copy of `navidrome.db`). If there are `navidrome.db-shm` and `navidrome.db-wal`, save those as well.
3. Make note of the original path to your music library. This must be the FULL path to your library.
4. Copy/move your music to the new music folder. (The script will check the validity of the new paths)
   - The new music path may contain symlinks if needed
5. Run the migration script: `python3 migrate.py PATH_TO_DB migrate ORIGINAL_MUSIC_FOLDER NEW_MUSIC_FOLDER`.
6. Change the `MusicFolder`/`ND_MUSICFOLDER` variable to point to the new location of your library.
7. Start Navidrome, and run a full scan.

### Already Moved Library And Only Need File Path Changes
Using the `changeLink` option, this will allow you to just change all the paths and md5 hashes, without moving your files. Perhaps you are moving from one system to another and the file systems may not be the same.

Example `python3 migrate.py navidrome.db changeLink 'E:\Media Server Content\' 'D:\Media Server Content\'`

### Moving From Windows To Linux/Mac
Moving your Navidrome from a Windows machine to a Linux or Mac based operating system can be a pain. If you moved your files already and, along with the `changeLink` option, use the `--windows_to_linux_path` option, it will allow any \\'s (Windows path) to be replaced with /'s (Linux/Unix path).

Example `python3 migrate.py navidrome.db changeLink 'E:\Media Server Content\' '/mnt/drive/Media Server Content/' --windows_to_linux_path`
- This will replace something such as `E:\Media Server Content\blah\blah.mp3` to `/mnt/drive/Media Server Content/blah/blah.mp3`

### Moving From Windows To Linux/Mac
Moving your Navidrome from a Linux or Mac based operating system to a Windows based operating system can be a pain. If you moved your files already and, along with the `changeLink` option, use the `--linux_to_windows_path` option, it will allow any  /'s (Linux/Unix path) to be replaced with \\'s (Windows path).

Example `python3 migrate.py navidrome.db changeLink '/mnt/drive/Media Server Content/' 'E:\Media Server Content\' --linux_to_windows_path`
- This will replace something such as `/mnt/drive/Media Server Content/blah/blah.mp3` to `E:\Media Server Content\blah\blah.mp3`

### Moving file/directory

This is useful if you just want to move a single folder in your library.

**CAUTION**: this script will move the target file/directory to the new location.
If you have specified an existing file, it **will** get overridden.

Usage:
`python3 migrate.py PATH_TO_DB move OLD_PATH NEW_PATH`

Notes:

- If `NEW_PATH` is a directory, the file/directory at `OLD_PATH` will be moved **into** this directory (not overwrite).
- Your database is only modified if the move succeeds.
  Note that a move is not guaranteed to be atomic (e.g. you are moving from one disk to another, and the destination fills up)
- Similar to migration, you _should_ stop Navidrome before doing this.
  However, the entire operation is atomic with respect to the database, so you _can_ do this live.
