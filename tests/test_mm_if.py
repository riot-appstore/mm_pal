"""Tests the mm_if of mm_pal."""
from time import sleep
from serial import Serial
import pytest
from conftest import MM_PATH, sleep_before_serial_action
from mm_pal import MmIf
from mm_pal import RESULT_SUCCESS, RESULT_ERROR, RESULT_TIMEOUT


def _expect_read_reg(app, inst, reg, data):
    app.rr_data = data
    assert inst.read_reg(reg)["data"] == data

def _dflt_read(inst, expect=RESULT_SUCCESS):
    resp = inst.read_reg("i8")
    assert resp['result'] == expect
    return resp


@pytest.mark.parametrize("args", [["i8", -127],
                                  ["i8", -1],
                                  ["i8", 127],
                                  ["ui8", 255],
                                  ["ui8", 42],
                                  ["i16", 1],
                                  ["i16", -256],
                                  ["i16", 0x7FFF],
                                  ["ui16", 0],
                                  ["ui16", 1234],
                                  ["ui16", 0xFFFF],
                                  ["i32", 0X10000],
                                  ["i32", -1],
                                  ["i32", -70000],
                                  ["ui32", 0xFFFFFFFF],
                                  ["ui32", 11],
                                  ["bf8.b1", 1],
                                  ["bf8.b1", 0],
                                  ["bf16.b9", 257]])
def test_read_reg_data(mock_app_json, mm_if_inst, args):
    mock_app_json.rr_data = args[1]
    assert mm_if_inst.read_reg(args[0])["data"] == args[1]


def test_read_reg_data_bitfield(mock_app_json, mm_if_inst):
    reg = "bf16.b6"
    data = 63
    offset = mm_if_inst.mem_map[reg]["bit_offset"]
    mock_app_json.rr_data = data << offset
    assert mm_if_inst.read_reg(reg)["data"] == data


def test_read_reg_data_array(mock_app_json, mm_if_inst):
    i = 0
    for data in mm_if_inst.read_reg("arru8")["data"]:
        assert data == i & 0xFF
        i += 1
    i = mm_if_inst.mem_map["arru16"]["offset"]
    for data in mm_if_inst.read_reg("arru16")["data"]:
        assert data == (i & 0xFF) + (((i + 1) & 0xFF) << 8)
        i += 2
    i = mm_if_inst.mem_map["arru32"]["offset"]
    for data in mm_if_inst.read_reg("arru32")["data"]:
        expect = (i & 0xFF)
        expect += (((i + 1) & 0xFF) << 8)
        expect += (((i + 2) & 0xFF) << 16)
        expect += (((i + 3) & 0xFF) << 24)
        assert data == expect
        i += 4


def test_read_reg_kwargs(mock_app_json, mm_if_inst):
    assert mm_if_inst.read_reg("arru8", size=1)["result"] == RESULT_SUCCESS
    assert mm_if_inst.read_reg("ui32", size=1)["result"] == RESULT_SUCCESS


def test_read_reg_fail(mock_app_json, mm_if_inst):
    assert mm_if_inst.read_reg("arru8", offset=9999)["result"] == RESULT_ERROR
    assert mm_if_inst.read_reg("arru8", size=9999)["result"] == RESULT_ERROR

    # Return data even if parse error
    mock_app_json.force_data_fail = 1
    assert mm_if_inst.read_reg("arru8")["data"] == ['f', 'o', 'o']


def test_version(mock_app_json, mm_if_inst):
    resp = mm_if_inst.get_version()
    assert resp["version"] == "0.0.1"
    assert resp["result"] == RESULT_SUCCESS


def test_basic_commands(mock_app_json, mm_if_inst):
    assert mm_if_inst.commit()["result"] == RESULT_SUCCESS
    assert mm_if_inst.soft_reset()["result"] == RESULT_SUCCESS


@pytest.mark.parametrize("data_has_name", [True, False])
def test_read_struct_regression_name(mock_app_json, mm_if_inst, regtest,
                                     data_has_name):
    resps = mm_if_inst.read_struct("stt", data_has_name=data_has_name)
    for resp in resps:
        regtest.write(str(resp["data"]) + "\n")


@pytest.mark.parametrize("reg", ["ui", "arru8", "ui32", "bf8_extra"])
def test_read_struct_regression(mock_app_json, mm_if_inst, regtest, reg):
    resps = mm_if_inst.read_struct(reg)
    for resp in resps:
        regtest.write(str(resp["data"]) + "\n")


def test_read_struct_fail(mock_app_json, mm_if_inst):
    assert mm_if_inst.read_struct("does_not_exist")["result"] == RESULT_ERROR
    mock_app_json.force_fails = 1
    assert mm_if_inst.read_struct("stt")["result"] == RESULT_ERROR


def test_write_reg(mock_app_json, mm_if_inst):
    assert mm_if_inst.write_reg("arru8", 1)['result'] == RESULT_SUCCESS
    assert mock_app_json.wr_bytes == [1]

    resp = mm_if_inst.write_reg("arru8", 1, offset=9999)
    assert resp['result'] == RESULT_ERROR

    mock_app_json.force_fails = 1
    assert mm_if_inst.write_reg("ui8", 1)['result'] == RESULT_ERROR

    mock_app_json.force_fails = 1
    assert mm_if_inst.write_reg("bf8.b2", 1)['result'] == RESULT_ERROR

    mock_app_json.force_write_fail = 1
    assert mm_if_inst.write_reg("bf8.b2", 1)['result'] == RESULT_ERROR

    assert mm_if_inst.write_reg("ui8", 2)['result'] == RESULT_SUCCESS
    assert mock_app_json.wr_bytes == [2]

    assert mm_if_inst.write_reg("bf16.b9", 5)['result'] == RESULT_SUCCESS
    assert mock_app_json.wr_bytes[0] == 5

    assert mm_if_inst.write_reg("bf8.b2", 2)['result'] == RESULT_SUCCESS
    assert mock_app_json.wr_bytes[0] & 0x6 == 2 << 1


def test_error_result(mock_app_json, mm_if_inst):
    mock_app_json.force_fails = 2
    _dflt_read(mm_if_inst, RESULT_ERROR)

    mock_app_json.force_error_code = -999
    _dflt_read(mm_if_inst, RESULT_ERROR)

    mock_app_json.force_parse_error = 1
    _dflt_read(mm_if_inst, RESULT_TIMEOUT)

    mock_app_json.force_timeout = 1
    _dflt_read(mm_if_inst, RESULT_TIMEOUT)
    _dflt_read(mm_if_inst)


def test_write_bytes_list(mock_app_json, mm_if_inst):
    w_data = [9, 8, 7]
    assert mm_if_inst.parser.write_bytes(0, w_data)['result'] == RESULT_SUCCESS
    assert mock_app_json.wr_index == 0
    assert len(w_data) == len(mock_app_json.wr_bytes)
    assert all([a == b for a, b in zip(w_data, mock_app_json.wr_bytes)])


def test_write_bytes_int(mock_app_json, mm_if_inst):
    resp = mm_if_inst.parser.write_bytes(1, 0x102, 2)
    assert resp['result'] == RESULT_SUCCESS
    assert mock_app_json.wr_index == 1
    assert mock_app_json.wr_bytes[0] == 2
    assert mock_app_json.wr_bytes[1] == 1


def test_driver_setting(mock_app_json, mm_if_inst):
    mm_if_inst.driver = mm_if_inst.driver
    _dflt_read(mm_if_inst)
    mm_if_inst.driver = Serial()


def test_retry(mock_app_json, mm_if_inst):
    mock_app_json.force_fails = 1
    mm_if_inst.default_retry = 1
    _dflt_read(mm_if_inst)
    mm_if_inst.default_retry = 0
    mock_app_json.force_fails = 1
    assert mm_if_inst.read_reg("i8", retry=1)['result'] == RESULT_SUCCESS
    mock_app_json.force_fails = 1
    _dflt_read(mm_if_inst, RESULT_ERROR)
    _dflt_read(mm_if_inst)

    mock_app_json.force_timeout = 1
    mm_if_inst.default_retry = 1
    _dflt_read(mm_if_inst)
    mock_app_json.force_timeout = 2
    _dflt_read(mm_if_inst, RESULT_TIMEOUT)
    _dflt_read(mm_if_inst)

    mock_app_json.force_fails = 3
    mm_if_inst.default_retry = 3
    _dflt_read(mm_if_inst)


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


def test_init_fail(mock_app_json, vpr_inst):
    with pytest.raises(NotImplementedError):
        mmif = MmIf(port=vpr_inst.ext_port, driver_type='foo')
        sleep_before_serial_action()
        mmif.driver.close()
    with pytest.raises(NotImplementedError):
        mmif = MmIf(port=vpr_inst.ext_port, parser_type='bar')
        sleep_before_serial_action()
        mmif.driver.close()
    mmif = MmIf(port=vpr_inst.ext_port)
    mmif.parser = 'foo'
    mmif.driver = 'bar'
