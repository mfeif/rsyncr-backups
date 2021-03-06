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
    # job excludes
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
        error_flag = False
    except ExternalCommandFailed as e:
        output = e.error_message
        error_flag = True
        if e.returncode in (23, 24):
            log.warning(
                f"Return code {e.returncode}! {e.error_message} -- likely permissions?"
            )
        else:
            raise e
    finally:
        return output, error_flag


def process_job(
    config_name,
    job_config_path=None,
    config_dir=None,
    global_config_path=None,
    args=None,
):
    """Handle the directories associated with 'config_name' for backups"""
    message_text = f"RsyncR is processing config {config_name}\n"

    # determine where our config files are...
    if config_dir is None:
        config_dir = config.DEFAULTS["configs_dir"]

    # if we pass in a dir to look for configs in, use it
    # otherwise use sane defaults set in config.py
    if global_config_path is None:
        global_config_path = os.path.join(config_dir, "global.toml")

    # job/recipe level configs... what corresponds to one config.{thing}.toml file
    if job_config_path is None:
        job_config_path = os.path.join(config_dir, f"config.{config_name}.toml")

    # make all the config strings into valid/checked confs
    gconf = config.make("global", global_config_path)
    jconf = config.make(config_name, job_config_path)
    aconf = config.command_line_config(args)

    # merge all the configs properly
    conf = config.merge_configs(gconf, jconf, aconf)

    # now the directories/sources for sync'ing
    any_errors = False
    for source_name, d in conf["sources"].items():
        cmdlist = build_command(conf, source_name)
        message_text += f"\nSource {source_name}: {d['location']} to {d['target']}\n"
        message_text += "Command:\n" + " ".join(cmdlist)
        message_text += (
            "\n--------------------------------------------------------------------\n"
        )
        out, source_error_flag = call_command(cmdlist)
        # keep track of whether any of the sources had an error
        any_errors = any_errors or source_error_flag
        message_text += out
        message_text += (
            "\n--------------------------------------------------------------------\n"
        )
    if conf["console_override"]:
        print(message_text)
    else:
        # send the output off, but only detailed if there is an error
        if any_errors:
            message.send(message_text)
        else:
            how_many = len(conf["sources"].items())
            message.send(
                f"RsyncR processed {how_many} sources in config {config_name} without errors."
            )
    if conf["capture_file"]:
        with open(conf["capture_file"], "w") as f:
            f.write(message_text)


def parse_command_line(force_args=None):
    """split out arg parsing for easier testing"""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "config",
        help="unique job/config name to read for rsync commands. example: mycomp",
    )
    parser.add_argument(
        "--job-config-path", help="(optional) what job toml file to use"
    )

    parser.add_argument("--configs-dir", help="(optional) where to look for toml files")

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
    jpath = args.job_config_path
    gcfg = args.global_config_path
    cfgdir = args.configs_dir

    process_job(
        name,
        job_config_path=jpath,
        config_dir=cfgdir,
        global_config_path=gcfg,
        args=args,
    )


if __name__ == "__main__":
    cli()
