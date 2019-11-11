"""Build and run the rsync commands"""

import os.path
import logging
import argparse

from executor import execute, ExternalCommandFailed

from rsyncr import config
from rsyncr import message

log = logging.getLogger()


def build_command(conf, src):
    """Make a list that corresponds to the rsync command line"""
    log.debug(f"""running build_command with source={src}, """)
    command = []
    command.append(conf["rsync_command"])
    if conf["dry_run"]:
        command.append("--dry-run")
    if conf["verbose"]:
        command.append("--verbose")
    for g in conf["global_rsync_params"]:
        command.append(g)

    # global excludes
    for e in conf.get("global_excludes", []):
        command.append(f"--exclude={e}")
    # machine excludes
    for e in conf.get("excludes", []):
        command.append(f"--exclude={e}")
    # source excludes
    for e in conf["sources"][src].get("excludes", []):
        command.append(f"--exclude={e}")

    command.append(conf["sources"][src]["location"])
    command.append(conf["sources"][src]["target"])

    log.debug("made command: {}".format(command))
    return command


def call_command(cmdargs):
    # check tells it to not throw exception if there is a non-zero return code
    try:
        output = execute(*cmdargs, capture=True)
    except ExternalCommandFailed as e:
        if e.returncode in (23, 24):
            log.warning(
                f"Return code {e.returncode}! {e.error_message} -- likely permissions?"
            )
            output = e.error_message
        else:
            raise e
    finally:
        return output


def process_machine(
    name, override_config_path=None, config_dir=None, global_config_path=None, args=None
):
    """Handle the directories associated with 'name' for backups"""
    message_text = f"RsyncR is processing config {name}\n"

    # determine where our config files are...
    if config_dir is None:
        config_dir = config.DEFAULTS["configs_dir"]

    # if we pass in a dir to look for configs in, use it
    # otherwise use sane defaults set in config.py
    if global_config_path:
        gtoml = config.read_config(global_config_path)
    else:
        gtoml = config.read_config(os.path.join(config_dir, "global.toml"))

    # machine/recipe level configs... what corresponds to one config.{thing}.toml file
    if override_config_path:
        mtoml = config.read_config(override_config_path)
    else:
        mtoml = config.read_config(os.path.join(config_dir, f"config.{name}.toml"))

    gconf = config.parse_string(gtoml)
    mconf = config.parse_string(mtoml)
    aconf = config.command_line_config(args)

    # merge all the configs properly
    conf = config.merge_configs(gconf, mconf, aconf)

    # now the directories/sources for sync'ing
    for name, d in conf["sources"].items():
        cmdlist = build_command(conf, name)
        message_text += f"\nSource {name}: {d['location']} to {d['target']}\n"
        message_text += "Command:\n" + " ".join(cmdlist)
        message_text += (
            "\n--------------------------------------------------------------------\n"
        )
        out = call_command(cmdlist)
        message_text += out
        message_text += (
            "\n--------------------------------------------------------------------\n"
        )
    if conf["console_override"]:
        print(message_text)
    else:
        # send the output off
        message.send(message_text)
    if conf["capture_file"]:
        with open(conf["capture_file"], "w") as f:
            f.write(message_text)


def parse_command_line(force_args=None):
    """split out arg parsing for easier testing"""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "config",
        help="unique machine/config name to read for rsync commands. example: mycomp",
    )
    parser.add_argument(
        "--override-config-path", help="(optional) what machine toml file to use"
    )

    parser.add_argument(
        "--configs-dir", help="(optional) where to look for machine toml files"
    )

    parser.add_argument(
        "--global-config-path", help="(optional) override global config settings"
    )
    parser.add_argument(
        "--dry-run", help="whether to simulate the action", action="store_true"
    )
    parser.add_argument(
        "--verbose", help="pass verbose flag onto rsync", action="store_true"
    )
    parser.add_argument(
        "--console",
        help="Don't use telegram, just print to console",
        action="store_true",
    )
    parser.add_argument("--capture-output", help="Filename to store output")

    return parser.parse_args(args=force_args)


def cli():
    """hook for command line access"""
    args = parse_command_line()

    # we need some of this stuff to know how/where to find other configs
    name = args.config
    opath = args.override_config_path
    gcfg = args.global_config_path
    cfgdir = args.configs_dir

    process_machine(
        name,
        override_config_path=opath,
        config_dir=cfgdir,
        global_config_path=gcfg,
        args=args,
    )


if __name__ == "__main__":
    cli()
