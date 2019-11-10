"""Parse config files and command line switches to get what rsync needs to run.

For precedence, it's:
command line switches > machine level conf > global conf > defaults
... BUT...
for excludes (things passed to the '--exclude' feature of rsync) have a wrinkle:
what to ALWAYS exclude (global_excludes) has sane defaults,
but can be overridden in a a global config file
and then machine and source/target excludes ADD to those
"""

import os.path
from copy import deepcopy

from tomlkit import parse as toml_parse

DEFAULTS = {
    # a dictionary containing sane defaults;
    # these are overridden by anything in global conf
    # which is in turn overridden by anything in machine conf
    # and ALL can be overridden by command line switches to rsyncr
    #
    # wrinkle about excludes; they don't override; they accumulate
    # where configs live by default
    "configs_dir": "/etc/rsyncr/",
    # whether to override telegram send and dump to console
    "console_override": False,
    # if this is not None, save a file copy of the output of the command
    "capture_file": None,
    # might need to be more detailed sometimes?
    "rsync_command": "rsync",
    # things to always exclude for all configs
    "global_excludes": [],
    "global_rsync_params": [
        "--delete",
        "--delete-excluded",
        "--archive",
        "--one-file-system",
        "--numeric-ids",
    ],
    "verbose": False,
    "dry_run": False,
    "logging_level": "warning",  # for standard python logging
}


class BadConfig(TypeError):
    pass


def parse_string(config_string):
    cfg = toml_parse(config_string)
    return cfg


def read_config(filename):
    """look for a .toml file and parse it"""
    with open(filename, "r") as f:
        cfgstr = f.read()
    return cfgstr


def make_machine_config(fromtoml):
    """fills in the optional config stuff for a machine, and does a wee bit of data
    checking"""
    # some basic checks...
    assert "target_root" in fromtoml, "config missing target_root!"
    assert (
        "sources" in fromtoml and len(fromtoml["sources"]) > 0
    ), "config missing sources or no sources there!"
    for n in fromtoml["sources"]:
        # these need a location, a target, and optional excludes
        assert (
            "location" in fromtoml["sources"][n]
        ), f"Need a 'location' in sources {n}!"
        assert (
            fromtoml["sources"][n]["location"][0] == "/"
        ), f"""'{fromtoml["sources"][n]['location']}' needs to be a valid path in sources {n}!"""
        assert "target" in fromtoml["sources"][n], f"Need a 'target' in sources {n}!"
        if "excludes" in fromtoml["sources"][n]:
            assert (
                len(fromtoml["sources"][n]["excludes"]) >= 1
            ), f"Excludes should be a list in sources {n}!"
        # not checking actual excludes; that's an rsync matter and too hard to check

        # @@ some more sanity checking probably would be good...

    # ok, now make a clean copy of config for returning...
    current = {"sources": {}}

    # one required item:
    current["target_root"] = fromtoml["target_root"]

    # loop through some optional ones
    for i in [
        "verbose",
        "dry_run",
        "console_override",
        "capture_file",
        "logging_level",
    ]:
        if i in fromtoml:
            current[i] = fromtoml.get(i)

    if "host" not in fromtoml or fromtoml["host"] == "local":
        # no host implies local rsyncing, so use root
        current["host"] = "/"
    else:
        current["host"] = fromtoml["host"]

    # make a safe copy
    current["excludes"] = []
    for i in fromtoml.get("excludes", []):
        current["excludes"].append(i)

    # individual source configs:
    for n, val in fromtoml["sources"].items():
        current["sources"][n] = {}

        # merge the paths for source, target here rather than downstream
        loc = fix_trailing_slashes(val["location"])
        current["sources"][n]["location"] = fix_trailing_slashes(
            os.path.join(fromtoml["host"], loc)
        )

        # we CAN override the normal behavior or root + target, and have an explicit
        # target in a source:
        if "target_full_path" in val:
            current["sources"][n]["target"] = fix_trailing_slashes(
                val["target_full_path"]
            )
        else:
            current["sources"][n]["target"] = fix_trailing_slashes(
                os.path.join(fromtoml["target_root"], val["target"])
            )
        # if the host isn't local, os.path.join strips off the machine part,
        # which looks like this: 'machine:' so fix that...
        if current["host"] != "/":
            current["sources"][n]["location"] = current["host"] + val["location"]

        # and source-level excludes
        current["sources"][n]["excludes"] = []
        for i in val.get("excludes", []):
            current["sources"][n]["excludes"].append(i)

    return current


def make_global_config(fromtoml):
    """check the vars declared in a conf object for this global install;
    already parsed from toml"""
    current = deepcopy(DEFAULTS)

    # none of the below really has sanity checks for datatype and so on; assuming good
    # stuff in conf and so on !!

    # update these without any particulars...
    for i in [
        "rsync_command",
        "verbose",
        "dry_run",
        "console_override",
        "capture_file",
        "logging_level",
    ]:
        if fromtoml.get(i):
            current[i] = fromtoml[i]

    # some that need a little more finesse:
    # these two are sequences, so we want to copy their elements rather than wholesale,
    # because they are stuffed with tomlkit artifacts
    if "global_rsync_params" in fromtoml:
        current["global_rsync_params"] = []
        for i in fromtoml.get("global_rsync_params", []):
            current["global_rsync_params"].append(i)
    if "global_excludes" in fromtoml:
        current["global_excludes"] = []
        for i in fromtoml.get("global_excludes", []):
            current["global_excludes"].append(i)

    if "override_rsync_params" in fromtoml:
        current["global_rsync_params"] = fromtoml["override_rsync_params"]
    elif "added_rsync_params" in fromtoml:
        current["global_rsync_params"] += fromtoml["added_rsync_params"]

    return current


def merge_configs(globalconf={}, machineconf={}, cmdline_args={}):
    """merge all the possible configs/switches into one conf object
    that is used to build command lines and such """
    # simple now, but edge conditions like adding rather than overwriting can come here
    current = deepcopy(DEFAULTS)
    current.update(globalconf)
    current.update(machineconf)
    current.update(cmdline_args)
    return current


def command_line_config(args):
    """turn passed args into a config dictionary that we can use to build context"""
    cfg = {}
    # I want a cfg composed of ONLY what is on command line, so don't want to stuff
    # any blank values/defaults, so have to do it manually; blah.
    if args.dry_run:
        cfg["dry_run"] = args.dry_run
    if args.verbose:
        cfg["verbose"] = args.verbose
    if args.console:
        cfg["console_override"] = args.console
    if args.capture_output:
        cfg["capture_file"] = args.capture_output
    return cfg


def fix_trailing_slashes(loc):
    """make sure that the location strings are sane for rsync; this
    basically means that they contain one trailing slash """
    if loc:
        # remove any that are there; could be multiple so better safe than sorry
        loc = loc.rstrip("/") + "/"
    return loc
