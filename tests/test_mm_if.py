"""Tests the mm_if of mm_pal."""
from time import sleep
from serial import Serial
import pytest
from conftest import MM_PATH, EXT_PORT
from mm_pal import MmIf


def _expect_read_reg(app, inst, reg, data):
    app.rr_data = data
    assert inst.read_reg(reg) == data


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
    assert mm_if_inst.read_reg(args[0]) == args[1]


def test_read_reg_data_bitfield(mock_app_json, mm_if_inst):
    reg = "bf16.b6"
    data = 63
    offset = mm_if_inst.mem_map[reg]["bit_offset"]
    mock_app_json.rr_data = data << offset
    assert mm_if_inst.read_reg(reg) == data


def test_read_reg_data_array(mock_app_json, mm_if_inst):
    i = 0
    for data in mm_if_inst.read_reg("arru8"):
        assert data == i & 0xFF
        i += 1
    i = mm_if_inst.mem_map["arru16"]["offset"]
    for data in mm_if_inst.read_reg("arru16"):
        assert data == (i & 0xFF) + (((i + 1) & 0xFF) << 8)
        i += 2
    i = mm_if_inst.mem_map["arru32"]["offset"]
    for data in mm_if_inst.read_reg("arru32"):
        expect = (i & 0xFF)
        expect += (((i + 1) & 0xFF) << 8)
        expect += (((i + 2) & 0xFF) << 16)
        expect += (((i + 3) & 0xFF) << 24)
        assert data == expect
        i += 4


def test_read_reg_kwargs(mock_app_json, mm_if_inst):
    mm_if_inst.read_reg("arru8", size=1)
    mm_if_inst.read_reg("ui32", size=1)


def test_read_reg_fail(mock_app_json, mm_if_inst):
    with pytest.raises(ValueError):
        mm_if_inst.read_reg("arru8", offset=9999)
    with pytest.raises(ValueError):
        assert mm_if_inst.read_reg("arru8", size=9999)

    # Return data even if parse error
    mock_app_json.force_data_fail = 1
    assert mm_if_inst.read_reg("arru8") == ['f', 'o', 'o']


def test_version(mock_app_json, mm_if_inst):
    resp = mm_if_inst.get_version()
    assert resp == "0.0.1"


def test_basic_commands(mock_app_json, mm_if_inst):
    mm_if_inst.commit()
    mm_if_inst.soft_reset()


@pytest.mark.parametrize("data_has_name", [True, False])
def test_read_struct_regression_name(mock_app_json, mm_if_inst, regtest,
                                     data_has_name):
    resps = mm_if_inst.read_struct("stt", data_has_name=data_has_name)
    for resp in resps:
        regtest.write(str(resp) + "\n")


@pytest.mark.parametrize("reg", [".", "ui", "arru8", "ui32", "bf8_extra"])
def test_read_struct_regression(mock_app_json, mm_if_inst, regtest, reg):
    resps = mm_if_inst.read_struct(reg)
    for resp in resps:
        regtest.write(str(resp) + "\n")


def test_read_frag(mock_app_json, mm_if_inst):
    resp = mm_if_inst.read_reg("arru16")
    resps = mm_if_inst.read_struct("stt")

    mm_if_inst.frag_size = 8
    assert resp == mm_if_inst.read_reg("arru16")
    assert resps == mm_if_inst.read_struct("stt")

def test_write_frag(mock_app_json, mm_if_inst):
    mm_if_inst.frag_size = 2
    mm_if_inst.write_reg("arru8", [0, 1])
    assert mock_app_json.wr_bytes == [0, 1]

    mm_if_inst.write_reg("arru8", [0, 1, 2, 3])
    # We only can see that last chunk of data
    assert mock_app_json.wr_bytes == [2, 3]


def test_read_struct_fail(mock_app_json, mm_if_inst):
    with pytest.raises(IndexError):
        mm_if_inst.read_struct("does_not_exist")
    mock_app_json.force_fails = 1
    with pytest.raises(IOError):
        assert mm_if_inst.read_struct("stt")


def test_write_reg(mock_app_json, mm_if_inst):
    mm_if_inst.write_reg("arru8", 1)
    assert mock_app_json.wr_bytes == [1]

    mm_if_inst.commit_write("arru8", 2)
    assert mock_app_json.wr_bytes == [2]

    with pytest.raises(ValueError):
        mm_if_inst.write_reg("arru8", 1, offset=9999)

    with pytest.raises(TypeError):
        mm_if_inst.write_reg("i8", [1, 2])

    with pytest.raises(TypeError):
        mm_if_inst.write_reg("bf8.b1", [1, 2])

    with pytest.raises(TypeError):
        mm_if_inst.write_reg("i8", {"expect": "fail"})

    mock_app_json.force_fails = 1
    with pytest.raises(IOError):
        mm_if_inst.write_reg("ui8", 1)

    with pytest.raises(ValueError):
        mm_if_inst.write_reg("bf8.b1", 2)

    mock_app_json.force_fails = 1
    with pytest.raises(IOError):
        mm_if_inst.write_reg("bf8.b2", 1)

    mock_app_json.force_write_fail = 1
    with pytest.raises(IOError):
        mm_if_inst.write_reg("bf8.b2", 1)

    mm_if_inst.write_reg("ui8", 2)
    assert mock_app_json.wr_bytes == [2]

    mm_if_inst.write_reg("i8", -1)
    assert mock_app_json.wr_bytes == [255]

    mm_if_inst.write_reg("i8", [1])
    assert mock_app_json.wr_bytes == [1]

    mm_if_inst.write_reg("bf16.b9", 5)
    assert mock_app_json.wr_bytes[0] == 5

    mm_if_inst.write_reg("bf8.b2", 2)
    assert mock_app_json.wr_bytes[0] & 0x6 == 2 << 1

    mm_if_inst.write_reg("bf8.b2", 2)
    assert mock_app_json.wr_bytes[0] & 0x6 == 2 << 1

    mm_if_inst.write_reg("arru8", [0, 1, 2], verify=True)

    with pytest.raises(RuntimeError):
        mm_if_inst.write_reg("arru8", [99, 1, 2], verify=True)


def test_error_result(mock_app_json, mm_if_inst):
    mock_app_json.force_fails = 2
    with pytest.raises(IOError):
        mm_if_inst.read_reg('i8')

    mock_app_json.force_error_code = -999
    with pytest.raises(IOError):
        mm_if_inst.read_reg('i8')

    mock_app_json.force_parse_error = 1
    with pytest.raises(TimeoutError):
        mm_if_inst.read_reg('i8')
    mock_app_json.force_timeout = 1
    with pytest.raises(TimeoutError):
        mm_if_inst.read_reg('i8')
    mm_if_inst.read_reg('i8')


def test_write_bytes_list(mock_app_json, mm_if_inst):
    w_data = [9, 8, 7]
    mm_if_inst.parser.write_bytes(0, w_data)
    assert mock_app_json.wr_index == 0
    assert len(w_data) == len(mock_app_json.wr_bytes)
    assert all([a == b for a, b in zip(w_data, mock_app_json.wr_bytes)])


def test_write_bytes_int(mock_app_json, mm_if_inst):
    mm_if_inst.parser.write_bytes(1, [0x02, 0x01])
    assert mock_app_json.wr_index == 1
    assert mock_app_json.wr_bytes[0] == 2
    assert mock_app_json.wr_bytes[1] == 1


def test_driver_setting(mock_app_json, mm_if_inst):
    mm_if_inst.driver = mm_if_inst.driver
    mm_if_inst.read_reg('i8')
    mm_if_inst.driver = Serial()


def test_retry(mock_app_json, mm_if_inst):
    mock_app_json.force_fails = 1
    mm_if_inst.default_retry = 1
    mm_if_inst.read_reg('i8')
    mm_if_inst.default_retry = 0
    mock_app_json.force_fails = 1
    mm_if_inst.read_reg("i8", retry=1)
    mock_app_json.force_fails = 1
    with pytest.raises(IOError):
        mm_if_inst.read_reg('i8')
    mm_if_inst.read_reg('i8')

    mock_app_json.force_timeout = 1
    mm_if_inst.default_retry = 1
    mm_if_inst.read_reg('i8')
    mock_app_json.force_timeout = 2
    with pytest.raises(TimeoutError):
        mm_if_inst.read_reg('i8')
    mm_if_inst.read_reg('i8')

    mock_app_json.force_fails = 3
    mm_if_inst.default_retry = 3
    mm_if_inst.read_reg('i8')


@pytest.mark.parametrize("kwargs", [{},
                                    {'mm_path': MM_PATH},
                                    {'mem_map': []},
                                    {'driver_type': 'serial'},
                                    {"parser_type": 'json'}])
def test_init(mock_app_json, kwargs):
    mmif = MmIf(port=EXT_PORT, **kwargs)
    mmif.get_version()
    mmif.driver.close()


def test_copy_driver(mock_app_json):
    mmif = MmIf(port=EXT_PORT)
    mmif.get_version()
    mmif = MmIf(driver=mmif.driver)
    mmif.get_version()
    mmif.driver.close()


def test_init_fail(mock_app_json):
    with pytest.raises(NotImplementedError):
        mmif = MmIf(port=EXT_PORT, driver_type='foo')
    with pytest.raises(NotImplementedError):
        mmif = MmIf(port=EXT_PORT, parser_type='bar')
    mmif = MmIf(port=EXT_PORT)
    mmif.parser = 'foo'
    mmif.driver = 'bar'
