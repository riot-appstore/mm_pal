"""Tests Serial Driver for philip pal

    This test should be run with only one PHiLIP device plugged in.
"""
from time import sleep
import pytest
from mock_pal import MockDev
from mm_pal.serial_driver import SerialDriver

@pytest.mark.parametrize("test_string", ['test', 'another_test'])
@pytest.mark.parametrize("preamble", ['', 'pre:', 0])
def test_loopback_line(mock_lb, ser_dri, test_string, preamble):
    """Tests the serial driver using the mock device in loopback mode."""
    ser_dri.writeline_preamble = preamble
    ser_dri.writeline(test_string)
    assert ser_dri.readline() == f"{preamble}{test_string}\n"
    # Just to be safe lets try this twice.
    ser_dri.writeline(test_string)
    assert ser_dri.readline() == f"{preamble}{test_string}\n"


@pytest.mark.parametrize("w_bytes", ['test', b'\x00test', 4,
                                     bytes([3, 2, 1]), '42'*65])
@pytest.mark.parametrize("preamble", ['', 'pre:', 99, bytes([3, 2, 1])])
@pytest.mark.parametrize("write_bytes_timeout", [None, 0, 1, 512])
@pytest.mark.parametrize("writesize_en", [False, True])
def test_loopback(mock_lb_bytes, ser_dri, w_bytes, preamble,
                  write_bytes_timeout, writesize_en):
    """Tests the serial driver using the mock device in loopback bytes mode."""
    ser_dri.write_preamble = preamble
    ser_dri.write_bytesize = writesize_en
    ser_dri.write_bytes_timeout = write_bytes_timeout
    ser_dri.write(w_bytes)
    # Must wait some time for bytes to be read
    byte_wait = 0
    try:
        byte_wait = 0.005 * len(w_bytes)
    except TypeError:
        pass

    sleep(0.03 + byte_wait)
    size = mock_lb_bytes.bytes_written
    read_bytes = ser_dri.read(size=size)

    if isinstance(w_bytes, str):
        w_bytes = w_bytes.encode()
    if isinstance(w_bytes, int):
        w_bytes = bytearray([w_bytes])
    if isinstance(preamble, str):
        preamble = preamble.encode()
    if isinstance(preamble, int):
        preamble = bytearray([preamble])

    expected_size = int(writesize_en) * 2
    if write_bytes_timeout is not None:
        expected_size += 2
    expected_size += len(preamble)
    expected_size += len(w_bytes)
    assert w_bytes in read_bytes
    assert len(read_bytes) == expected_size
