"""Build and run the rsync commands"""

import logging
import argparse

from executor import execute, ExternalCommandFailed

from rsyncr import config
from rsyncr import message

log = logging.getLogger()


def build_command(source, target, excludes, dry_run=False, verbose=False):
    """Make a list that corresponds to the rsync command line"""
    log.debug(
        f"""running build_command with source={source}, """
        f"""target={target}, excludes={excludes}, dry_run={dry_run}"""
    )
    # some things that don't change per directory:
    command = [config.RSYNC]
    if dry_run:
        command.append("--dry-run")
    if verbose:
        command.append("--verbose")
    for g in config.GLOBAL_RSYNC_PARAMS:
        command.append(g)

    for e in config.GLOBAL_EXCLUDES + excludes:
        command.append(f"--exclude={e}")

    command.append(source)
    command.append(target)

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
    name,
    dry_run=None,
    verbose=None,
    override_config_path=None,
    config_dir=None,
    global_config_path=None,
):
    """Handle the directories associated with 'name' for backups"""
    message_text = f"RsyncR is processing config {name}\n"
    # global configs
    gconf = config.get_global(global_config_path)
    gexc = gconf.get("global_excludes", [])

    # per-machine configs
    conf = config.get(name, override_config_path)
    # check for machine-wide excludes
    machine_exc = conf.get("excludes", [])

    # command line switches will override configs in toml,
    # and local machine configs will override global configs
    if dry_run is None:
        dry_run = conf.get("dry_run", gconf.get("dry_run", False))
    if verbose is None:
        verbose = conf.get("verbose", gconf.get("verbose", False))

    # now the directories/sources for sync'ing
    for name, d in conf["sources"].items():
        src = d["location"]
        trg = d["target"]
        exc = gexc + machine_exc + d.get("excludes", [])
        # @@ not yet adding global rsync params logic here @@ !
        cmdlist = build_command(src, trg, exc, dry_run, verbose)
        message_text += f"\nSource {name}: {src} to {trg}\n"
        out = call_command(cmdlist)
        message_text += out
        message_text += (
            "\n--------------------------------------------------------------------\n"
        )
    # send the output off to me
    message.send(message_text)


def cli():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "config",
        help="unique machine/config name to read for rsync commands. example: mycomp",
    )
    parser.add_argument(
        "--override_config_path", help="(optional) what machine toml file to use"
    )

    parser.add_argument(
        "--configs_dir", help="(optional) where to look for machine toml files"
    )

    parser.add_argument(
        "--global_config_path", help="(optional) override global config settings"
    )
    parser.add_argument(
        "--dry-run", help="whether to simulate the action", action="store_true"
    )
    parser.add_argument(
        "--verbose", help="pass verbose flag onto rsync", action="store_true"
    )
    args = parser.parse_args()
    name = args.config
    dry = args.dry_run
    ver = args.verbose
    opath = args.override_config_path
    gcfg = args.global_config_path
    cfgdir = args.configs_dir
    process_machine(
        name,
        dry_run=dry,
        verbose=ver,
        override_config_path=opath,
        config_dir=cfgdir,
        global_config_path=gcfg,
    )


if __name__ == "__main__":
    cli()
