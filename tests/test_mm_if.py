"""Tests Serial Driver for philip pal

    This test should be run with only one PHiLIP device plugged in.
"""
from time import sleep
from pathlib import Path
import pytest
from conftest import MM_PATH, sleep_before_serial_action
from mm_pal import MmIf


def test_parser(mock_app_json, mm_if_inst):
    """Tests the serial driver using the mock device in loopback mode."""
    sleep_before_serial_action()
    mm_if_inst.get_version()
    mm_if_inst.execute_changes()
    mm_if_inst.soft_reset()
    mm_if_inst.read_struct("snum")
    mm_if_inst.read_reg("arr_8")
    mm_if_inst.write_reg("arr_8", [1, 2, 3])


@pytest.mark.parametrize("kwargs", [{},
                                    {'mm_path': MM_PATH},
                                    {'mem_map': []},
                                    {'driver_type': 'serial'},
                                    {"parser_type": 'json'}])
def test_init(mock_app_json, vpr_inst, kwargs):
    mmif = MmIf(port=vpr_inst.ext_port, **kwargs)
    sleep_before_serial_action()
    assert 'version' in mmif.get_version()
    mmif.driver.close()
