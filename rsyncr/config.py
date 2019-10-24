"""Parse config files to get what rsync needs to run."""

import os.path

from tomlkit import parse as toml_parse

# where configs live is hard-coded here now
CONFIGS_DIR = "/etc/rsyncr/"

RSYNC = "rsync"  # might need to be more detailed sometimes?

# things I always want to exclude for all configs
GLOBAL_EXCLUDES = [".DS_Store", "*__pycache__", "*pytest_cache"]

GLOBAL_RSYNC_PARAMS = [
    "--delete",
    "--delete-excluded",
    "--archive",
    "--one-file-system",
    "--numeric-ids",
    # "--verbose",
    # "--info=progress2",   # seems to be not present on macos
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


def read_config(name, override_filename=None):
    """look for a .toml file corresponding to 'name' and parse it"""
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
        assert (
            "location" in conf["sources"][n]
        ), f"Need a 'location' for the sources {n}!"
        assert (
            conf["sources"][n]["location"][0] == "/"
        ), f"""'{conf["sources"][n]['location']}' needs to be a valid path, for the sources {n}!"""

        conf["sources"][n]["location"] = fix_trailing_slashes(
            conf["sources"][n]["location"]
        )
        # merge the paths for source, target here rather than downstream
        conf["sources"][n]["location"] = fix_trailing_slashes(
            os.path.join(conf["location"], conf["sources"][n]["location"])
        )
        conf["sources"][n]["target"] = fix_trailing_slashes(
            os.path.join(conf["target_root"], conf["sources"][n]["target"])
        )
        # if the location isn't local, os.path.join strips off the machine part, so:
        if conf["location"] != "local":
            conf["sources"][n]["location"] = (
                conf["location"] + conf["sources"][n]["location"]
            )
        # not checking excludes; that's an rsync matter that is out of scope for now
    return conf


def fix_trailing_slashes(loc):
    """make sure that the location strings are sane for rsync; this
    basically means that they contain one trailing slash """
    if loc:
        # remove any that are there; could be multiple so better safe than sorry
        loc = loc.rstrip("/") + "/"
    return loc
