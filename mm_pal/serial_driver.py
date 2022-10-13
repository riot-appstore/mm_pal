# Copyright (c) 2020 HAW Hamburg
#
# This file is subject to the terms and conditions of the MIT License. See the
# file LICENSE in the top level directory for more details.
# SPDX-License-Identifier:    MIT
"""Serial Driver for mm_pal.

This module handles generic connection and IO to the serial driver. It provides
more usable defaults for connecting to mm_pal based devices.
"""
import logging
import time
from typing import Dict
from serial import Serial
from serial.tools import list_ports


__author__ = "Kevin Weiss"
__email__ = "weiss.kevin604@gmail.com"


_serialports: Dict[str, Serial] = {}  # Key: port name, value: port instance


class SerialDriver:
    """Serial port drivers for connecting, reading, and writing.

    Contains all reusable functions for connecting, sending and receiving
    data.  Arguments are passed through to the standard pyserial driver.  The
    defaults are changed.  Also if env variables are defined they get used as
    defaults.  Automatically opens the serial port on initialize.  If nothing
    is specified the port is set to the first available port.

    Attributes:
        writeline_preamble (str): String to write before :py:meth:`~writeline`,
            defaults to empty.
        write_bytesize (bool): Enables sending the size of bytes in the write
            message, defaults to False.
        write_bytes_timeout (int): Timeout value to add to the write
            message, defaults to None.
        dev (obj): Serial device.
    """

    def __init__(self, *args, **kwargs):
        """Instantiate the serial port.

        Args:
            *args: Variable list of arguments.
            **kwargs: Variable dict of arguments.

        Keyword Args:
            **reconnect_on_timeout (bool): Attempt reconnect on read timeout,
                defaults to False.
            **flush_on_startup (bool): Perform dummy read and write after
                connect, defaults to false.
            **use_port_that_contains (str): If a port is not specified search
                each port for a match and connects, defaults to None.
            **timeout (float): Serial read timeout, defaults to 0.5.
            **baudrate (int): Serial baudrate, defaults to 115200.
            **port (str): Name of serial port, defaults to autoconnect based
                on ``use_port_that_contains``.

        Note:
            Refer to the
            `Serial <https://pythonhosted.org/pyserial/pyserial_api.html#serial.Serial.__init__>`__
            class for additional ``*args`` and ``**kwargs`` functionality.

        Warning:
            The list ports function for autoconnecting use physical
            boards and are not virtualized. This means that
            ``use_port_that_contains`` and ``port=None`` options are not
            testable with automated tests and require real hardware to
            be used. The ``baudrate`` param also cannot be set with the
            virtual com ports which means it must be verified manually.
        """  # noqa: E501
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.debug("__init__(%r,%r)", args, kwargs)
        self.writeline_preamble = ""
        self.write_preamble = ""
        self.write_bytesize = False
        self.write_bytes_timeout = None
        self._reconnect_on_timeout = kwargs.pop('reconnect_on_timeout', False)
        flush_on_startup = kwargs.pop('flush_on_startup', False)

        self._connect(*args, **kwargs)

        # Used to clear the cpu and mcu buffer from startup junk data
        if flush_on_startup:
            self.logger.debug("flushing buffer")
            time.sleep(0.05)
            self.writeline('')
            try:
                self.readline(0.3)
            except TimeoutError:
                self.logger.debug("flush_on_startup TimeoutError occurred")
            self.dev.flushInput()
            self.dev.flushOutput()

    # flake8: noqa: C901
    def _connect(self, *args, **kwargs):
        # pylint: disable=too-many-branches

        search_com = kwargs.pop('use_port_that_contains', None)
        kwargs['timeout'] = kwargs.pop('timeout', 0.5)
        if len(args) < 2:
            kwargs['baudrate'] = kwargs.pop('baudrate', 115200)
        if len(args) == 0 and 'port' not in kwargs:
            # get the last listed port
            kwargs['port'] = sorted(list_ports.comports(),
                                    key=lambda x: x[0])[-1][0]
            if search_com:
                # Gets the port that contains search string if not specified.
                # eg. If connecting to an nucleo board search for
                # "STM32 STLink"
                # eg. If you know the location of the board for the hub then
                # search for "LOCATION=1-1:1.2"
                kwargs['port'] = next(list_ports.grep(search_com))[0]

        # In order to set rts and dtr before opening port
        # port must == None
        args = list(args)
        if len(args) == 0:
            port = kwargs.pop('port')
            kwargs['port'] = None
        else:
            port = args[0]
            args[0] = None  # pylint: disable=E1137

        rts = kwargs.pop('rts', None)
        dtr = kwargs.pop('dtr', None)

        self.logger.debug("Serial(%r,%r)", args, kwargs)

        if _serialports.get(port):
            self.logger.debug("Serial port %r already exists", port)
            self.dev = _serialports[port]
        else:
            self.dev = Serial(*args, **kwargs)
            _serialports[port] = self.dev

        try:
            if rts is not None:
                self.dev.rts = rts
                kwargs['rts'] = rts
            if dtr is not None:
                self.dev.dtr = dtr
                kwargs['dtr'] = dtr
        except IOError as exc:
            # We want to ignore
            # OSError: [Errno 25] Inappropriate ioctl for device
            # as this is an extra feature
            self.logger.warning(exc)

        if len(args) == 0:
            self.dev.port = port
            kwargs['port'] = port
        else:
            self.dev.port = port
            args[0] = port  # pylint: disable=E1137

        self.logger.debug("opening port=%r", port)
        if (self.dev.port is None) or (not self.dev.is_open):
            self.dev.open()

        self._args = args
        self._kwargs = kwargs

    def open(self, *args, **kwargs):
        # pylint: disable=C0301
        """Open a Serial Connection.

        Args:
            *args: Variable list of arguments.
            **kwargs: Variable dict of arguments.

        Keyword Args:
            **use_port_that_contains (str): If a port is not specified search
            each port for a match and connects, defaults to None.
            **timeout (float): Serial read timeout, defaults to 0.5.
            **baudrate (int): Serial baudrate, defaults to 115200.
            **port (str): Name of serial port, defaults to autoconnect based
                on ``use_port_that_contains``.

        Note:
            Refer to the
            `Serial <https://pyserial.readthedocs.io/en/latest/pyserial_api.html#serial.Serial.__init__>`__
            class for additional ``*args`` and ``**kwargs`` functionality.
        """  # noqa: E501
        self.logger.debug("open(%r,%r)", args, kwargs)
        self._connect(*args, **kwargs)

    def close(self):
        """Close serial connection."""
        self.logger.debug("Closing %s", self.dev.port)
        self.dev.close()

    def readline(self, timeout=None, clean_noise=True):
        """Read Line from Serial.

        Read and decode to utf-8 data from the serial port.

        Args:
            timeout (int): timeout value for command specific timeouts,
                defaults to None.
            clean_noise (bool): Strips null bytes that may be introduced due
                to noise or device startup conditions, defaults to True.

        Returns:
            str: string of utf8 encoded data.

        Raises:
            TimeoutError: If a line cannot be read a timeout is raised.
        """
        if timeout is None:
            res_bytes = self.dev.readline()
        else:
            default_timeout = self.dev.timeout
            self.dev.timeout = timeout
            res_bytes = self.dev.readline()
            self.dev.timeout = default_timeout
        response = res_bytes.decode("utf-8", errors="replace")
        if clean_noise:
            # Gets rid of leading zeros caused by reset
            response = response.strip('\0')
        if response == "":
            if self._reconnect_on_timeout:
                self.close()
                self._connect(*self._args, **self._kwargs)
            raise TimeoutError("Timeout during serial readline")
        self.logger.debug("Response: %s", response.replace('\n', ''))
        return response

    def readlines_to_delim(self, timeout=None, clean_noise=True, delim='>'):
        """Read Lines from serial device until delimiter is in response.

        Args:
            timeout (int): timeout value for command specific timeouts,
                defaults to None.
            clean_noise (bool): Strips null bytes that may be introduced due
                to noise or device startup conditions, defaults to True.
            delim (str): The delimitating string that will end the readlines,
                defaults to ``'>'``

        Returns:
            str: string of utf8 encoded data.

        Raises:
            TimeoutError: If a line cannot be read a timeout is raised.
        """
        response = ""
        rline = ""
        while delim not in rline:
            response += rline
            rline = self.readline(timeout=timeout,
                                  clean_noise=clean_noise)
        return response

    def read(self, size=1, timeout=None):
        """Read and decode to utf-8 data from the serial port.

        Args:
            size (int): Amount of bytes to read, defaults to 1.
            timeout (float): timeout for read command, defaults to dev.timeout

        Returns:
            bytes: The bytes that have been read from the serial port.

        Raises:
            TimeoutError: If a line cannot be read a timeout is raised.
        """
        self.logger.debug("read(size=%r)", size)
        if timeout is None:
            res_bytes = self.dev.read(size)
        else:
            default_timeout = self.dev.timeout
            self.dev.timeout = timeout
            res_bytes = self.dev.read(size)
            self.dev.timeout = default_timeout
        self.logger.debug("ret=%r", res_bytes)
        if len(res_bytes) != size:
            if self._reconnect_on_timeout:
                self.close()
                self._connect(*self._args, **self._kwargs)
            raise TimeoutError("Timeout during serial read")
        return res_bytes

    def writeline(self, line):
        """Write a line.

        Line includes a newline, preable, and encode
        to utf-8. Flush input before writting to ensure clean line.

        Args:
            line (str, list): Bytes to send to the driver.
        """
        self.logger.debug("writeline(line=%r)", line)
        # Clear the input buffer in case it junk data go in creating an offset
        self.dev.flushInput()
        write_data = f"{self.writeline_preamble}{line}\n".encode('utf-8')
        self.logger.debug("writing: %r", write_data)
        self.dev.write(write_data)

    @property
    def write_preamble(self):
        """str, bytes: Bytes to write before :py:meth:`write`.

        Defaults to empty.
        """
        return self._write_preamble

    @write_preamble.setter
    def write_preamble(self, value):
        if isinstance(value, str):
            self._write_preamble = value.encode()
        self._write_preamble = value

    @property
    def timeout(self):
        """int: Read timeout."""
        return self.dev.timeout

    @timeout.setter
    def timeout(self, val):
        self.logger.debug("timeout(val=%r)", val)
        self.dev.timeout = val

    @staticmethod
    def _encode_bytes(val):
        ret = val
        if isinstance(val, str):
            ret = val.encode()
        if isinstance(val, int):
            ret = [val]
        return bytearray(ret)

    def write(self, w_bytes):
        """Write bytes to serial port.

        Write bytes with encapsulation to allow device to passthrough
        data. If :py:attr:`~write_preamble`, :py:attr:`~write_bytesize`,
        or :py:attr:`~write_bytes_timeout` are used then they get
        included with the bytes sent.  The `write_bytesize` consists of
        a 16 bit number with little endianess that represents the amount
        of bytes that are being sent with `w_bytes`. The
        `write_bytes_timeout` consists of a 16 bit number with little
        endianess that tells the device how long to expect the timeout
        for the encapsulated call. The `write_preamble` is used for
        encapsulation of a message so it can be forwarded to another
        device.

        ::

            bytes || len(write_preamble) | 2              | 2                   | write_bytesize
                  || write_preamble      | write_bytesize | write_bytes_timeout | w_bytes

        Args:
            w_bytes (bytes): byte array to write.
        """  # noqa: E501
        # Clear the input buffer in case it junk data go in creating an offset
        self.dev.flushInput()
        self.logger.debug("write(w_bytes=%r)", w_bytes)
        writedata = self._encode_bytes(self.write_preamble)
        w_bytes = self._encode_bytes(w_bytes)
        if self.write_bytesize:
            self.logger.debug("write_bytesize=%r", len(w_bytes))
            writedata.extend(len(w_bytes).to_bytes(2, byteorder='little'))
        if self.write_bytes_timeout is not None:
            timeout = int(self.write_bytes_timeout)
            self.logger.debug("write_bytes_timeout=%r", timeout)
            writedata.extend(timeout.to_bytes(2, byteorder='little'))
        writedata.extend(w_bytes)
        self.logger.debug("writedata=%r", writedata)
        self.dev.write(writedata)
