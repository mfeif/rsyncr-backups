from rsyncr import config
from rsyncr import run

# there are various cascades of overrides where
# command line > machine config > global config > defaults
# so that can get tricky... some tests to make sure
# intended results work...


# bunch of override / cascade testing


override_gtoml = """
rsync_command = "/usr/local/bin/rsync"
verbose = true
dry_run = true
console_override = true
capture_file = "my_rsyncr_output.txt"
logging_level = "error"
override_rsync_params = ['1', '2', '3']
added_rsync_params = ['some', 'are', 'added']
global_excludes = ["these", "are", "excluded"]
"""


def test_globals_override_defaults():
    """make sure that set global config options override defaults"""
    g = config.make_global_config(config.parse_string(override_gtoml))
    merged = config.merge_configs(globalconf=g)

    assert (
        merged["rsync_command"] == "/usr/local/bin/rsync"
    ), "rsync_command didn't override right"
    assert merged["verbose"] is True, "verbose didn't override right"
    assert merged["dry_run"] is True, "dry_run didn't override right"
    assert merged["console_override"] is True, "console_override didn't override right"
    assert (
        merged["capture_file"] == "my_rsyncr_output.txt"
    ), "capture_file didn't override right"
    assert merged["global_rsync_params"] == [
        "1",
        "2",
        "3",
    ], "override_rsync_params didn't override right"
    assert merged["global_excludes"] == [
        "these",
        "are",
        "excluded",
    ], "global_excludes didn't override right"
    assert merged["logging_level"] == "error", "logging_level didn't override right"

    # one for added rsyncs instead of override rsyncs
    gtoml = """added_rsync_params = ['one', 'two']"""
    g = config.make_global_config(config.parse_string(gtoml))
    merged = config.merge_configs(globalconf=g)
    assert (
        "two" in merged["global_rsync_params"]
        and "--delete" in merged["global_rsync_params"]
    ), "added_rsync_params didn't override right"


override_mtoml = """
target_root = "/path/to/my/backups/"
host = "pasilla:"
verbose = true
dry_run = true
excludes = ['nasty', 'canasta']
console_override = true
capture_file = "my_rsyncr_output.txt"
logging_level = "error"

[sources.bogus]
location = "/usr/local/share/"
target = "usr.local.share"
excludes = ['doc', 'man']
"""


def test_machine_configs_override_defaults():
    """make sure that passed machine config stuff properly
    overrides default values """
    g = config.make_global_config(config.parse_string(override_gtoml))
    m = config.make_machine_config(config.parse_string(override_mtoml))
    merged = config.merge_configs(g, m)
    assert merged.get("verbose") is True, "'verbose' didn't overwrite defaults properly"
    assert merged.get("dry_run") is True, "'dry_run' didn't overwrite defaults properly"
    assert (
        merged.get("logging_level") == "error"
    ), "'logging_level' didn't overwrite defaults properly"
    assert (
        merged.get("console_override") is True
    ), "'console_override' didn't overwrite defaults properly"
    assert (
        merged.get("capture_file") == "my_rsyncr_output.txt"
    ), "'capture_file' didn't overwrite defaults properly"


def test_machine_configs_override_globals():
    """make sure that passed machine config stuff properly
    overrides global values """
    # stuff some new values to globals that we can overwrite...
    gtoml = """
    configs_dir = "/etc/globals"
    rsync_command = "/usr/not/really/here"
    verbose = false
    dry_run = false
    console_override = false
    capture_file = "Nobody_asked_me.txt"
    logging_level = "warning"
    override_rsync_params = ['a', 'b', 'c']
    added_rsync_params = ['way', 'down', 'south']
    global_excludes = ["nobody", "said", "anything"]
    """
    g = config.make_global_config(config.parse_string(gtoml))
    m = config.make_machine_config(config.parse_string(override_mtoml))
    merged = config.merge_configs(g, m)
    assert merged.get("verbose") is True, "'verbose' didn't overwrite defaults properly"
    assert merged.get("dry_run") is True, "'dry_run' didn't overwrite defaults properly"
    assert (
        merged.get("logging_level") == "error"
    ), "'logging_level' didn't overwrite defaults properly"
    assert (
        merged.get("console_override") is True
    ), "'console_override' didn't overwrite defaults properly"
    assert (
        merged.get("capture_file") == "my_rsyncr_output.txt"
    ), "'capture_file' didn't overwrite defaults properly"


def test_global_excludes_overwrite():
    """exclude clauses in global configs should replace default values, and
    machine configs should completely replace globally defined ones"""
    g = config.make_global_config(config.parse_string(override_gtoml))
    merged = config.merge_configs(g)
    assert merged["global_excludes"] == ["these", "are", "excluded"]


def test_excludes_accumulate():
    """make sure that excludes accumulate and don't overwrite..."""
    # just test it's getting values from machine config first...
    g = config.make_global_config(config.parse_string(override_gtoml))
    m = config.make_machine_config(config.parse_string(override_mtoml))
    merged = config.merge_configs(g, m)
    assert merged["excludes"] == ["nasty", "canasta"]
    # now test accumulation...
    merged = config.merge_configs({}, m)  # let's not override defaults for this one
    cmd_list = run.build_command(merged, "bogus")
    for t in ("nasty", "canasta", "doc", "man"):
        assert f"--exclude={t}" in cmd_list, "malformed commandline exclude!"


def test_accumulated_rsync_params():
    """make sure that rsync params can be ADDED to defaults"""
    gtoml = """added_rsync_params = ['--quiet', '--checksum']"""
    mtoml = """
target_root = "/path/to/my/backups/"
host = "pasilla:"

[sources.tst]
location = "/usr/local/share/"
target = "usr.local.share"
"""
    g = config.make_global_config(config.parse_string(gtoml))
    m = config.make_machine_config(config.parse_string(mtoml))
    c = {}
    merged = config.merge_configs(g, m, c)
    # check defaults are still there
    assert (
        "--delete" in merged["global_rsync_params"]
    ), "Oops; default rsync param --delete is missing!"
    # check also that our added thing is there
    assert (
        "--quiet" in merged["global_rsync_params"]
    ), "Oops; added rsync param --quiet is missing!"
