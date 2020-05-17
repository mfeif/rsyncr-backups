======
RsyncR
======
RsyncR is a thin wrapper around rsync made out of python libraries; I use it to back up some servers.

It eats toml config files, builds rsync commands, runs them, and sends the results/outputs
to me over telegram.

It's highly inpsired by tools like rsnapshot, and the newer python-rsync-system-backup. Both of those are probably better than this for you. This is very much "works for me" status. I've used it on MacOS and Linux, never tried on Windows, it's unlikely to work out of the box.

Why not use one of the tools I mentioned above? I used rsnapshot for years, and rsync-system-backup looks really nice, but I just want rsync without snapshots, rotations, etc. I'm relying on a set of restic scripts to do the rotations/snapshots/etc... I just want to rsync directories.

My workflow is to backup files with this tool to some local storage, and then use restic and rclone to send *that stuff* to Backblaze. So "old" copies of backed up data live in "cold storage" at Backblaze, and only the newest backup exists locally.

Since most of this functionality is other people's code, hopefully I haven't made too many places for bugs, but there are (well, will-be) some tests for things I have thought of. Most of the places where bugs can creep in are related to the parsing of config files. I'm sure that TomlKit works well, but there's no validation or anything; it just makes dictionaries out of the config file... making sure those dicts are not going to do something dumb to rsync is another story.

Why Telegram?
Frankly, it *seemed* easier to get this going than wrestle with the modern reality of getting emails out. (Thanks spammers!) It's likely that I'm overlooking best practices for doing this that would be pretty easy. There's almost nothing in message.py, where functionality to send via email or other services could be added.

To-do:
- write up how to config things
x write up an example config file
- write up how to integrate this with systemd
- write up how to hook up your own telegram
