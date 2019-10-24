"""Build and run the rsync commands"""

import logging
import argparse

from executor import execute, ExternalCommandFailed

from rsyncr import config
from rsyncr import message

log = logging.getLogger()


def build_command(source, target, excludes, dry_run=False):
    """Make a list that corresponds to the rsync command line"""
    log.debug(
        f"""running build_command with source={source}, """
        f"""target={target}, excludes={excludes}, dry_run={dry_run}"""
    )
    # some things that don't change per directory:
    command = [config.RSYNC]
    if dry_run:
        command.append("--dry-run")
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


def process_machine(name, dry_run=False, verbose=False, override_filename=None):
    """Handle the directories associated with 'name' for backups"""
    message_text = f"RsyncR is processing config {name}\n"
    conf = config.get(name, override_filename)
    # check for machine-wide excludes
    machine_exc = conf.get("excludes", [])
    # now the directories/sources for sync'ing
    for name, d in conf["sources"].items():
        src = d["location"]
        trg = d["target"]
        exc = machine_exc + d.get("excludes", [])
        cmdlist = build_command(src, trg, exc, dry_run)
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
    parser.add_argument("config", help="unique config name to read for rsync commands.")
    parser.add_argument(
        "--dry-run", help="whether to simulate the action", action="store_true"
    )
    parser.add_argument(
        "--verbose", help="pass verbose flag onto rsync", action="store_true"
    )
    args = parser.parse_args()
    name = args.config
    dry = args.dry_run
    verbose = args.verbose
    process_machine(name, dry, verbose)


if __name__ == "__main__":
    cli()
