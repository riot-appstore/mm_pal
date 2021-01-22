import pytest
from conftest import MM_PATH, sleep_before_serial_action
from mm_pal import RESULT_SUCCESS
from mock_pal import MockIf


def test_commands(mock_app_json, vpr_inst):
    """Tests the serial driver using the mock device in loopback mode."""
    mockif = MockIf(port=vpr_inst.ext_port)
    sleep_before_serial_action()
    assert mockif.get_version()['result'] == RESULT_SUCCESS
    assert mockif.commit()['result'] == RESULT_SUCCESS
    assert mockif.soft_reset()['result'] == RESULT_SUCCESS
    assert mockif.read_struct("stt")[0]['result'] == RESULT_SUCCESS
    assert mockif.read_reg("arru8")['result'] == RESULT_SUCCESS
    assert mockif.write_reg("arru8", [1, 2, 3])['result'] == RESULT_SUCCESS
    assert mockif.special_cmd()['result'] == RESULT_SUCCESS
    mockif.driver.close()
