"""Tests Serial Driver for philip pal

    This test should be run with only one PHiLIP device plugged in.
"""
import pytest
from conftest import MM_PATH
from mm_pal import RESULT_SUCCESS
from mock_pal import MockIf


def test_loopback_line(mock_app_json, vpr_inst):
    """Tests the serial driver using the mock device in loopback mode."""
    mockif = MockIf(port=vpr_inst.ext_port)
    assert mockif.get_version()['result'] == RESULT_SUCCESS
    assert mockif.execute_changes()['result'] == RESULT_SUCCESS
    assert mockif.soft_reset()['result'] == RESULT_SUCCESS
    assert mockif.read_struct("snum")[0]['result'] == RESULT_SUCCESS
    assert mockif.read_reg("arr_8")['result'] == RESULT_SUCCESS
    assert mockif.write_reg("arr_8", [1, 2, 3])['result'] == RESULT_SUCCESS
    assert mockif.special_cmd()['result'] == RESULT_SUCCESS
    mockif.driver.close()


@pytest.mark.parametrize("kwargs", [{},
                                    {'mm_path': MM_PATH},
                                    {'mem_map': []},
                                    {'driver_type': 'serial'},
                                    {"parser_type": 'json'}])
def test_init(mock_app_json, vpr_inst, kwargs):
    mockif = MockIf(port=vpr_inst.ext_port, **kwargs)
    assert mockif.mem_map is not None
    mockif.driver.close()
