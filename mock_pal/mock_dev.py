#! /usr/bin/env python3
# Copyright (c) 2020 HAW Hamburg
#
# This file is subject to the terms and conditions of the MIT License. See the
# file LICENSE in the top level directory for more details.
# SPDX-License-Identifier:    MIT
"""Mock serial device for simulated serial testing.

This module provides setup a virtual com port and implementations of devices
on one side of the com port.
"""
import argparse
import errno
import json
import os
import logging
import subprocess
from time import sleep
from threading import Thread

from serial import Serial


__author__ = "Kevin Weiss"
__email__ = "weiss.kevin604@gmail.com"


class VirtualPortRunner:
    """Starts a background process that opens two virtual com ports.

    This uses ``socat`` to open a virtual com port that is used by the mock
    serial device and a virtual com port to connect to for serial testing.

    Warning:
        This starts a background process that may not stop if __del__ does not
        get called, such as when the program exits due to an unhandled
        exception. If this is the case ``killall -2 socat`` will stop all
        processes.

    Attributes:
        logger (obj): Class level logger based on class name
        ext_port (str): Name and path to the external port used to connect
            to the mock dev.
        mock_port (str): Name and path to the mock port that the mock dev
            connects to.
    """

    def __init__(self, ext_port='/tmp/mm_pal_dev0',
                 mock_port='/tmp/mm_pal_mock_dev0'):
        """Start the virtual com ports with `socat`.

        Args:
            ext_port (str): Name and path to the external port used to connect
                to the mock dev.
            mock_port (str): Name and path to the mock port that the mock dev
                connects to.
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info("Creating mock device on %r connected to %r",
                         mock_port, ext_port)
        commands = ['socat', f'pty,link={ext_port},raw,echo=0',
                    f'pty,link={mock_port},raw,echo=0']
        # pylint: disable=consider-using-with
        self._socat_p = subprocess.Popen(commands)
        self.ext_port = ext_port
        self.mock_port = mock_port
        # It takes some time to setup the ports
        for _ in range(100):
            if os.path.exists(ext_port) and os.path.exists(mock_port):
                break
            sleep(0.1)

    def __del__(self):
        """Destructor that terminates the process."""
        self._socat_p.terminate()
        self.logger.debug("socat process terminated")


class MockDev:
    """Connects a mock device to read and write a virtual serial port.

    This uses ``socat`` to open a virtual com port that is used by the mock
    serial device and a virtual com port to connect to for serial testing.
    Remaining kwargs are used for instantiating the serial port.

    Attributes:
        logger (obj): Class level logger based on class name
        bytes_read (int): Counts the number of bytes that are read from the
            mock serial port.
        bytes_written (int): Counts the number of bytes that the mock serial
            port writes.
        dev (obj): The serial device instance.
    """

    def __init__(self, **kwargs):
        # pylint: disable=C0301
        """Initialize the mock serial device.

        Keyword Args:
            **dev_driver (obj, optional): Already instantiated serial driver,
                if not present serial port will be created.
            **port (string): Serial port of mock dev, defaults to "/tmp/mm_pal_mock_dev0"
            **baudrate (int): Baudrate for mock dev, defaults to 115200

        Note:
            Refer to the
            `Serial <https://pyserial.readthedocs.io/en/latest/pyserial_api.html#serial.Serial.__init__>`_
            class for additional ``**kwargs`` functionality.
        """  # noqa: E501
        self.logger = logging.getLogger(self.__class__.__name__)
        kwargs['port'] = kwargs.pop('port', "/tmp/mm_pal_mock_dev0")
        kwargs['baudrate'] = kwargs.pop('baudrate', 115200)
        self.mock_port = kwargs['port']
        self.logger.debug("Mock device = Serial(%r)", kwargs)

        self.bytes_read = 0
        self.bytes_written = 0
        self.wr_bytes = None
        self.wr_index = None
        self.rr_data = None

        self.force_fails = 0
        self.force_error_code = errno.EADDRNOTAVAIL
        self.force_timeout = 0
        self.force_parse_error = 0
        self.force_data_fail = 0
        self.force_write_fail = 0

        self._exit_thread = False
        self._run_thread = None
        if 'dev_driver' in kwargs:
            self.dev = kwargs.pop('dev_driver')
        else:
            self.dev = Serial(**kwargs)

    def __del__(self):
        """Destructor that ends the thread loop."""
        self.end_thread_loop()
        self.dev.close()

    def close(self):
        """Close serial port."""
        self.dev.close()

    def run_loopback_line(self):
        """Run loopback per line on mock serial dev.

        Read serial line and write line back to the serial port. Update the
        :py:attr:`~bytes_written` and :py:attr:`~bytes_read`. Loop until the
        :py:attr:`~_exit_thread` is set to `True`.
        """
        while True:
            self.logger.debug("run_loopback_line: readline()")
            read = self.dev.readline()
            if self.force_timeout > 0:
                self.force_timeout -= 1
                continue

            self.bytes_read += len(read)
            self.logger.debug("run_loopback_line: readline=%r", read)
            self.dev.write(read)
            self.bytes_written += len(read)
            self.logger.debug("bytes_read=%r", self.bytes_read)
            self.logger.debug("bytes_written=%r", self.bytes_written)
            if self._exit_thread:
                self._exit_thread = False
                break
        self.logger.debug("run_loopback_line exited")

    def run_loopback_bytes(self):
        """Run loopback for every byte on mock serial dev.

        Read byte and write it back. Update the :py:attr:`~bytes_written` and
        :py:attr:`~bytes_read`. Loop until the :py:attr:`~_exit_thread` is set
        to `True`.
        """
        while True:
            self.logger.debug("run_loopback_bytes: read()")
            read = self.dev.read()
            self.bytes_read += len(read)
            self.logger.debug("run_loopback_bytes: read=%r", read)
            self.dev.write(read)
            self.bytes_written += len(read)
            self.logger.debug("bytes_read=%r", self.bytes_read)
            self.logger.debug("bytes_written=%r", self.bytes_written)
            if self._exit_thread:
                self._exit_thread = False
                break
        self.logger.debug("run_loopback_bytes exited")

    def _parse_wr_cmd(self, args):
        if self.force_write_fail > 0:
            self.force_write_fail -= 1
            return {"result": errno.EINVAL}
        if len(args) < 3:
            response = {"result": errno.EINVAL}
            self.logger.debug("Invalid args")
        else:
            response = {"result": 0}
            index = int(args[1])
            self.wr_index = index
            self.wr_bytes = []
            for arg in args[2:]:
                num = int(arg)
                self.wr_bytes.append(num)
                if num > 255:
                    response = {"result": errno.EOVERFLOW}
                    break
                self.logger.debug("data[%r]=%r", index, num)
                index += 1

        return response

    def _parse_rr_cmd(self, args):
        if self.force_data_fail > 0:
            self.force_data_fail -= 1
            return {"result": 0, "data": "foo"}
        index = int(args[1])
        size = int(args[2])
        if size == 0:
            response = {"result": errno.EINVAL}
            self.logger.debug("Invalid size")
        else:
            if self.rr_data is None:
                data = list(range(index, index + size))
                data = [i & 0xFF for i in data]
            else:
                try:
                    data = list(self.rr_data.to_bytes(size,
                                                      byteorder='little',
                                                      signed=True))
                except OverflowError:
                    data = list(self.rr_data.to_bytes(size,
                                                      byteorder='little',
                                                      signed=False))
                self.rr_data = None
            response = {"data": data, "result": 0}
            self.logger.debug("response=%r", response)
        return response

    def _parse_json_cmd(self, args):
        if self.force_fails > 0:
            self.force_fails -= 1
            return {"result": self.force_error_code}
        if self.force_timeout > 0:
            self.force_timeout -= 1
            return {}

        try:
            if args[0] == b'rr':
                response = self._parse_rr_cmd(args)
            elif args[0] == b'version':
                response = {"version": "0.0.1", "result": 0}
            elif (args[0] == b'ex' or
                  args[0] == b'mcu_rst' or
                  args[0] == b'special_cmd'):
                response = {"result": 0}
            elif args[0] == b'wr':
                response = self._parse_wr_cmd(args)
            else:
                response = {"result": errno.EPROTONOSUPPORT}

        except (IndexError) as exc:
            response = {"result": errno.EPROTONOSUPPORT}
            self.logger.debug("error=%r", exc)
        except (ValueError, TypeError) as exc:
            response = {"result": errno.EBADMSG}
            self.logger.debug("error=%r", exc)
        return response

    def run_app_json(self):
        """Run a basic json parsing app.

        Support a number a defined commands to simulate a device with parsed
        json structure.

        ``rr <index> <size>`` reads a byte value, mock values start at 0 when
        ``index`` is 0 and increase by one and truncate at 255. Respond with
        data and result.

        ``wr <index> <data0..datan>`` writes bytes to register. each number
        must be within 0-255 except for the index. Respond only with a result.

        ``ex`` or ``mcu_rst`` are basic commands that just respond with result.

        ``version`` indicates interface version. Respond with result and
        version.
        """
        while True:
            self.logger.debug("run_app_json: readline()")
            read = self.dev.readline()
            args = read.split()
            self.logger.debug("cmd=%r", args)
            response = self._parse_json_cmd(args)
            if self.force_parse_error > 0:
                self.force_parse_error -= 1
                response = f"foobar\n{{\"response\": {-999}}}\n"
            else:
                response = json.dumps(response)
                response = f"{response}\n"
            self.dev.write(response.encode())
            self.bytes_read += len(read)
            self.bytes_written += len(response)
            self.logger.debug("bytes_read=%r", self.bytes_read)
            self.logger.debug("bytes_written=%r", self.bytes_written)
            if self._exit_thread:
                self._exit_thread = False
                break
        self.logger.debug("run_app_json exited")

    # pylint: disable=W1113
    def start_thread_loop(self, func=None, *args):
        """Start a daemon thread to run a function.

        Only one thread can be active at a time. If another function is started
        the current thread will stop. The thread *should* get cleaned up in the
        :py:meth:`__del__` destructor.

        Args:
            func (function, optional): Function to run in the background,
                defaults to :py:meth:`run_loopback_line`.
            *args: Variable length arguments list.
        """
        self.end_thread_loop()
        if func is None:
            func = self.run_loopback_line
        self._run_thread = Thread(target=func, args=args)
        self._run_thread.daemon = True
        self.logger.debug("start_loopback_line_thread_loop")
        self._run_thread.start()

    def end_thread_loop(self):
        """End the thread started with :py:meth:`start_thread_loop`.

        Set the :py:attr:`~_exit_thread` to True and cancel any serial reads.
        Wait until the thread has ended before returning.
        """
        self._exit_thread = True
        self.dev.cancel_read()
        if self._run_thread is not None:
            self.logger.debug("Exiting thread loop")
            while self._run_thread.is_alive():
                sleep(0.1)
        self._exit_thread = False


def log_level_module_control(pargs):
    """Enable logs depending on modules.

    Args:
        pargs: arguments from argparse
    """
    if pargs.loglevel:
        loglevel = logging.getLevelName(pargs.loglevel.upper())
        if pargs.logmodules is not None:
            logging.basicConfig()
            for logname in pargs.logmodules:
                logger = logging.getLogger(logname)
                logger.setLevel(loglevel)
        else:
            logging.basicConfig(level=loglevel)


def main():
    """Run serial loopback example.

    To exit from the loop use the KeyboardInterrupt
    """
    parser = argparse.ArgumentParser()

    parser.add_argument('--loglevel', default='INFO',
                        help='Python logger log level, defaults to INFO.')
    parser.add_argument('--logmodules', nargs='+', default=None,
                        help='Modules to enable logging.')
    parser.add_argument('--func', '-f',
                        help='Function to run, defaults to run_loopback_line. '
                        '{run_loopback_line, '
                        'run_loopback_bytes, '
                        'run_app_json}',
                        default="run_loopback_line")
    pargs = parser.parse_args()

    log_level_module_control(pargs)

    virtual_port_runner = VirtualPortRunner()

    dev = MockDev(port=virtual_port_runner.mock_port)
    if pargs.func == "run_loopback_line":
        dev.run_loopback_line()
    elif pargs.func == "run_loopback_bytes":
        dev.run_loopback_bytes()
    elif pargs.func == "run_app_json":
        dev.run_app_json()


if __name__ == '__main__':
    main()
