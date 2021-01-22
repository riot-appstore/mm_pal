import pytest
from conftest import MM_PATH, sleep_before_serial_action
from mock_pal import MockCli


@pytest.mark.parametrize("kwargs", [{},
                                    {'mm_path': MM_PATH},
                                    {'mem_map': []},
                                    {'driver_type': 'serial'},
                                    {"parser_type": 'json'}])
def test_init(mock_app_json, vpr_inst, capsys, kwargs):
    cli = MockCli(port=vpr_inst.ext_port, **kwargs)
    cli.onecmd("get_version")
    sleep_before_serial_action()
    cap = capsys.readouterr()
    assert 'Interface version: 0.0.1' in cap.out


def test_readline_init(mock_app_json, vpr_inst, capsys):
    cli = MockCli(port=vpr_inst.ext_port)
    sleep_before_serial_action()
    cli.preloop()
    cli._hist_file = "/tmp/failhistory"
    cli.preloop()
    cli.postloop()


@pytest.mark.parametrize("cmd", ["read_reg i8",
                                 "write_reg i8 1",
                                 "read_struct stt",
                                 "commit",
                                 "soft_reset",
                                 "get_version",
                                 "data_filter",
                                 "data_filter ON",
                                 "data_filter OFF",
                                 "info_reg i8",
                                 "info_param name",
                                 "special_cmd",
                                 "key_error"])
def test_commands(mock_app_json, vpr_inst, capsys, regtest, cmd):
    cli = MockCli(port=vpr_inst.ext_port)
    cli.onecmd(cmd)
    sleep_before_serial_action()
    cap = capsys.readouterr()
    regtest.write(cap.out)