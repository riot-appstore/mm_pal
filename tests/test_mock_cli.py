import pytest
from conftest import MM_PATH, EXT_PORT
from mock_pal import MockCli


@pytest.mark.parametrize("kwargs", [{},
                                    {'mm_path': MM_PATH},
                                    {'mem_map': []},
                                    {'driver_type': 'serial'},
                                    {"parser_type": 'json'}])
def test_init(mock_app_json, capsys, kwargs):
    tmp = MockCli(port=EXT_PORT, **kwargs).onecmd("get_version")
    cap = capsys.readouterr()
    assert 'Interface version: 0.0.1' in cap.out


@pytest.mark.parametrize("cmd", ["read_reg i8",
                                 "write_reg i8 1",
                                 "read_struct stt",
                                 "commit",
                                 "soft_reset",
                                 "get_version",
                                 "info_reg arru8",
                                 "info_reg",
                                 "info_param name",
                                 "info_param nothing",
                                 "special_cmd",
                                 "key_error"])
def test_commands(mock_app_json, capsys, regtest, cmd):
    tmp = MockCli(port=EXT_PORT, persistent_history_file="/tmp").onecmd(cmd)
    cap = capsys.readouterr()
    regtest.write(cap.out)


def test_completion(mock_app_json):
    cli = MockCli(port=EXT_PORT)
    assert "arru8" in cli.regs_choices_method()
    assert "name" in cli.param_choices_method()
