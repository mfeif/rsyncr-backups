import logging
import os.path

logging.getLogger().setLevel(logging.DEBUG)


from rsyncr.run import process_machine


def test_process_machine():
    # grab a bogus file...
    dir = os.path.split(__file__)[:-1]
    fn = os.path.join(*dir, "test1.toml")
    process_machine("dude", override_filename=fn)
