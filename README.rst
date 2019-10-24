RsyncR is a this wrapper around rsync; I use it to back up some servers.

It eats config files and runs rsync commands, and sends the results/outputs
to me over telegram.

It's highly inpsired by tools like rsnapshot, and the newer python-rsync-system-backup. Both of those are probably better than this. This is very much "works for me" status.

Why not use one of those? I used rsnapshot for years, and rsync-system-backup looks really nice, but I just want rsync. I'm relying on a set of restic scripts to do the rotations/snapshots/etc... I just want to rsync directories.

Since most of this functionality is other people's code, hopefully I haven't made too many places for bugs, but there are some tests for things I have thought of. Most of the places where bugs can creep in are related to the parsing of config files. I'm sure that TomlKit works well, but there's no validation or anything; it just makes dictionaries out of the config file... making sure those dicts are not going to do something dumb to rsync is another story.

To-do:
- write up how to config things
- write up an example config file
- write up how to integrate this with systemd
- write up how to hook up your own telegram