import os
import stups_cli.config


def test_load_empty_config():
    cfg = stups_cli.config.load_config('doesnotexist')
    assert cfg == {}


def test_store_load_config():
    cfg = {'test': 'abc'}
    stups_cli.config.store_config(cfg, 'foobar')
    new_cfg = stups_cli.config.load_config('foobar')
    assert cfg == new_cfg


def test_load_config_with_environment():
    os.environ['EXAMPLE_PROJ_MY_KEY'] = 'some value'
    cfg = stups_cli.config.load_config('example-proj')
    assert cfg == {'my_key': 'some value'}
