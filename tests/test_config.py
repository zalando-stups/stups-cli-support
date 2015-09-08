import stups_cli.config


def test_load_empty_config():
    cfg = stups_cli.config.load_config('doesnotexist')
    assert cfg == {}


def test_store_load_config():
    cfg = {'test': 'abc'}
    stups_cli.config.store_config(cfg, 'foobar')
    new_cfg = stups_cli.config.load_config('foobar')
    assert cfg == new_cfg
