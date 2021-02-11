"""Tests Serial Driver for mm_pal

    This test can be run without any hardware but some tests must have at least
    one virtual com port plugged in otherwise they be skipped.
"""
from time import sleep
import pytest
from serial.tools import list_ports
from mm_pal.serial_driver import SerialDriver
from conftest import EXT_PORT


def _confirm_echo_readline(ser_dri):
    ser_dri.writeline("foo")
    assert ser_dri.readline() == "foo\n"


@pytest.mark.parametrize("fos", [True, False])
def test_init_flush_on_startup(mock_lb, fos):
    port = EXT_PORT
    SerialDriver(port, flush_on_startup=fos)
    mock_lb.force_timeout = 1
    if fos:
        assert mock_lb.bytes_written == 1
        _confirm_echo_readline(SerialDriver(port, flush_on_startup=fos))
    else:
        assert mock_lb.bytes_written == 0
        with pytest.raises(TimeoutError):
            _confirm_echo_readline(SerialDriver(port, flush_on_startup=fos))


@pytest.mark.skipif(list_ports.comports() == [] or
                    list_ports.comports()[0][0] == '/dev/ttyS1',
                    reason="No com port or fake com port (likey from CI)")
def test_init_usb_only():
    SerialDriver()
    SerialDriver(use_port_that_contains="/dev")


def test_init_args(mock_lb):
    _confirm_echo_readline(SerialDriver(EXT_PORT))
    _confirm_echo_readline(SerialDriver(EXT_PORT, 115200))


def test_init_kwargs(mock_lb):
    _confirm_echo_readline(SerialDriver(port=EXT_PORT,
                                        rts=True,
                                        dtr=True))
    with pytest.raises(TypeError):
        # Since serial exception is caught
        ser_dri = SerialDriver(port="foo")

    mock_lb.force_timeout = 1
    ser_dri = SerialDriver(port=EXT_PORT,
                           reconnect_on_timeout=False)
    with pytest.raises(TimeoutError):
        _confirm_echo_readline(ser_dri)
    _confirm_echo_readline(ser_dri)

    ser_dri = SerialDriver(port=EXT_PORT,
                           reconnect_on_timeout=True)
    mock_lb.force_timeout = 1
    with pytest.raises(TimeoutError):
        _confirm_echo_readline(ser_dri)
    _confirm_echo_readline(ser_dri)


def test_init_close_open(mock_lb, ser_dri):
    ser_dri.close()
    ser_dri.open(*ser_dri._args, **ser_dri._kwargs)

def test_readline(mock_lb, ser_dri):

    ser_dri.writeline("\0\0\0foo")
    assert ser_dri.readline(clean_noise=True) == "foo\n"

    ser_dri.writeline("\0\0\0foo")
    assert ser_dri.readline(clean_noise=False) == "\0\0\0foo\n"

    with pytest.raises(TimeoutError):
        ser_dri.readline()

    ser_dri.writeline("foo")
    assert ser_dri.readline(timeout=1) == "foo\n"

    ser_dri.writeline("foo")
    with pytest.raises(TimeoutError):
        ser_dri.readline(timeout=0)


def test_readline_to_delim(mock_lb, ser_dri):

    ser_dri.writeline("foo")
    ser_dri.writeline("bar")
    ser_dri.writeline(">")
    lines = ser_dri.readlines_to_delim()
    sleep(0.3)
    assert lines == "foo\nbar\n"

    ser_dri.writeline("foo")
    ser_dri.writeline("bar")
    ser_dri.writeline("DELIM")
    sleep(0.3)
    lines = ser_dri.readlines_to_delim(delim="DELIM")
    assert lines == "foo\nbar\n"

    ser_dri.writeline("foo")
    ser_dri.writeline("bar")
    with pytest.raises(TimeoutError):
        ser_dri.readlines_to_delim()


def test_read(mock_lb, ser_dri):
    ser_dri.writeline("foo")
    line = ser_dri.read(size=4, timeout=1)
    assert line == b"foo\n"

    ser_dri.timeout = 1.2
    assert ser_dri.timeout == 1.2
    ser_dri.writeline("foo")
    line = ser_dri.read(size=4, timeout=1)
    assert line == b"foo\n"

    with pytest.raises(TimeoutError):
        ser_dri.read()
    ser_dri._reconnect_on_timeout = True
    with pytest.raises(TimeoutError):
        ser_dri.read()


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
