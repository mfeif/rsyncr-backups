import logging
import os.path

logging.getLogger().setLevel(logging.DEBUG)


# from rsyncr.run import process_job


# def test_process_job():
#     # grab a bogus file...
#     dir = os.path.split(__file__)[:-1]
#     fn = os.path.join(*dir, "test1.toml")
#     process_job("dude", override_filename=fn)
