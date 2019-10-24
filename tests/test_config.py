from rsyncr import config


def test_working_config():
    c = config.parse_string(_ex_cfg)
    d = config.check_and_fill_out(c)
    assert "source_BOGUS_TEST" in d, "oops!"
    print(d)
