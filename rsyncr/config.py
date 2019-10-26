"""Parse config files to get what rsync needs to run."""

import os.path
import logging

from tomlkit import parse as toml_parse

# where configs live is hard-coded here now
CONFIGS_DIR = "/etc/rsyncr/"

RSYNC = "rsync"  # might need to be more detailed sometimes?

# things I always want to exclude for all configs
GLOBAL_EXCLUDES = []

GLOBAL_RSYNC_PARAMS = [
    "--delete",
    "--delete-excluded",
    "--archive",
    "--one-file-system",
    "--numeric-ids",
]


class BadConfig(TypeError):
    pass


def get(name, override_filename=None, override_string=None):
    """do all the steps to get a good config back"""
    if override_string:
        config_string = override_string
    else:
        config_string = read_config(name, override_filename)
    data = parse_string(config_string)
    good_data = check_config(data)
    return good_data


def get_global(override_filename=None, override_string=None):
    """do all the steps to get a good global config back"""
    if override_string:
        config_string = override_string
    else:
        if override_filename:
            path = override_filename
        else:
            path = os.path.join(CONFIGS_DIR, "global.toml")
        config_string = read_config("global", override_filename=path)
    data = parse_string(config_string)
    good_data = check_global_config(data)
    return good_data


def read_config(name, override_filename=None):
    """look for a .toml file and parse it"""
    if override_filename:
        path = override_filename
    else:
        path = os.path.join(CONFIGS_DIR, f"config.{name}.toml")
    with open(path, "r") as f:
        cfgstr = f.read()
    return cfgstr


def parse_string(config_string):
    cfg = toml_parse(config_string)
    return cfg


def check_config(conf):
    """fills in the optional stuff, and does a wee bit of data checking"""
    assert "target_root" in conf, "config missing target_root!"
    if "location" not in conf or conf["location"] == "local":
        # no location implies local rsyncing, so remove it
        conf["location"] = "/"
    assert (
        "sources" in conf and len(conf["sources"]) > 0
    ), "config missing sources or no sources there!"

    for n in conf["sources"]:
        # these need a location, a target, and optional excludes
        assert "location" in conf["sources"][n], f"Need a 'location' in sources {n}!"
        assert (
            conf["sources"][n]["location"][0] == "/"
        ), f"""'{conf["sources"][n]['location']}' needs to be a valid path in sources {n}!"""

        conf["sources"][n]["location"] = fix_trailing_slashes(
            conf["sources"][n]["location"]
        )
        # merge the paths for source, target here rather than downstream
        conf["sources"][n]["location"] = fix_trailing_slashes(
            os.path.join(conf["location"], conf["sources"][n]["location"])
        )

        # we CAN override the normal behavior or root + target, and have an explicit
        # target in a source:
        if "target_full_path" in conf["sources"][n]:
            conf["sources"][n]["target"] = fix_trailing_slashes(
                conf["sources"][n]["target_full_path"]
            )
        else:
            conf["sources"][n]["target"] = fix_trailing_slashes(
                os.path.join(conf["target_root"], conf["sources"][n]["target"])
            )
        # if the location isn't local, os.path.join strips off the machine part, so:
        if conf["location"] != "/":
            conf["sources"][n]["location"] = (
                conf["location"] + conf["sources"][n]["location"]
            )
        # not checking excludes; that's an rsync matter that is out of scope for now
    return conf


def check_global_config(conf):
    """check the vars declared in a global conf object; already parsed from toml"""
    # all options are currently optional, but build a dictionary here and update it
    updated_conf = {
        "rsync_cli": RSYNC,
        "configs_dir": CONFIGS_DIR,
        "global_excludes": GLOBAL_EXCLUDES,
        "global_rsync_params": GLOBAL_RSYNC_PARAMS,
        "verbose": False,
        "dry_run": False,
        "logging_level": "warning",
    }

    # none of the below really has sanity checks for datatype and so on

    if "rsync_cli" in conf:
        updated_conf["rsync_cli"] = conf["rsync_cli"]

    if "verbose" in conf:
        updated_conf["verbose"] = conf["verbose"]

    if "dry_run" in conf:
        updated_conf["dry_run"] = conf["dry_run"]

    if "global_excludes" in conf:
        updated_conf["global_excludes"] = conf["global_excludes"]

    if "override_rsync_params" in conf:
        updated_conf["global_rsync_params"] = conf["override_rsync_params"]
    elif "added_rsync_params" in conf:
        updated_conf["global_rsync_params"] += conf["added_rsync_params"]

    if "logging_level" in conf:
        updated_conf["logging_level"] = conf["logging_level"]

    # set that logging level...
    level = logging._nameToLevel[updated_conf["logging_level"].upper()]
    logging.getLogger().setLevel(level)

    return updated_conf


def fix_trailing_slashes(loc):
    """make sure that the location strings are sane for rsync; this
    basically means that they contain one trailing slash """
    if loc:
        # remove any that are there; could be multiple so better safe than sorry
        loc = loc.rstrip("/") + "/"
    return loc
