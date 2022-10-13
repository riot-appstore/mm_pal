# Copyright (c) 2020 HAW Hamburg
# This file is subject to the terms and conditions of the MIT License. See the
# file LICENSE in the top level directory for more details.
# SPDX-License-Identifier:    MIT
"""Interface for memory map based devices.

Use parsers and drivers to allow abstracted, python based register type
access to devices as well as some basic commands. The target is for
resource contrained devices that require many parameters to write and
read. On instantiation, a driver is selected, serial by default, and a
parser is selected, json by default. A command is given, such as
`read_register` and have an expected response.

Generation of a memory map can be done with the
`Memory Map Manager <https://github.com/riot-appstore/memory_map_manager>`_
tool.
"""
import logging
import errno
import os
import json
import csv
from ctypes import c_uint8, c_uint16, c_uint32, c_int8, c_int16, c_int32
from ast import literal_eval
from .serial_driver import SerialDriver


__author__ = "Kevin Weiss"
__email__ = "weiss.kevin604@gmail.com"


MM_IF_EXCEPTIONS = IOError, ValueError, KeyError, TimeoutError, RuntimeError


def _try_parse_int_list(list_int):
    for i, val in enumerate(list_int):
        try:
            list_int[i] = literal_eval(str(val))
        except (ValueError, TypeError, SyntaxError):
            pass


def import_mm_from_csv(path):
    """Import a memory map csv file.

    Open a csv file and parse it to a memory map object as define by the
    `Memory Map Manager <https://github.com/riot-appstore/memory_map_manager>`_
    .

    Args:
        path (str): Path to the csv containing the memory map.
    Returns:
        obj: memory map from the csv.
    """
    mem_map = {}
    with open(path, encoding='utf-8') as csvfile:
        rows = list(csv.reader(csvfile, quotechar="'"))
        for row in range(1, len(rows)):
            _try_parse_int_list(rows[row])
            cmd = dict(zip(rows[0], rows[row]))
            mem_map[rows[row][rows[0].index('name')]] = cmd
    return mem_map


class MmJsonParser:
    """Json style parser for interfacing to memory map based devices.

    Send command and parse response. Read lines
    until json information contains a ``result``. Convert result to
    ``RESULT_*`` type. Add `cmd` element with evaluated call.

    Attributes:
        driver (obj): Driver to send and receive information to parse.

    Example:
        send with driver
        ``rr 0 3``

        receive with driver
        ``{"data":[0,1,2],"result":0}`` of type ``str``

        return parsed data:
        ::

            [0, 1, 2]
    """

    def __init__(self, driver):
        """Instantiate parser instance and start logger.

        Args:
            driver (obj): Driver to send and receive information to parse.
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.debug("__init__(driver=%r)", driver)
        self.driver = driver

    def _error_msg(self, error_code):
        self.logger.debug("_error_msg("
                          "error_code=%r)", error_code)
        if error_code not in errno.errorcode:
            raise IOError(f"Unknown Error[{error_code}]")
        s_errcode = errno.errorcode[error_code]
        s_errmsg = os.strerror(error_code)
        raise IOError(f"{s_errcode}-{s_errmsg} [{error_code}]")

    def _send_cmd(self, cmd, timeout, end_key='result'):
        self.logger.debug("_send_cmd("
                          "cmd=%r, "
                          "timeout=%r, "
                          "end_key=%r)", cmd, timeout, end_key)
        self.driver.writeline(cmd)
        cmd_info = {}
        while end_key not in cmd_info:
            line = self.driver.readline(timeout)
            try:
                # We want to ignore non-json type messages
                # this allows us to have debug messages in our command
                cmd_info.update(json.loads(line))
            except json.decoder.JSONDecodeError:
                self.logger.warning("JSON parse error: line=%r", line)
        return cmd_info

    def send_and_parse_cmd(self, cmd, timeout=None):
        """Return a dictionary with information from the event.

        Args:
            send_cmd (str): The command to write to the device.
            to_byte_array (bool): If True and data is bytes leave it as an
                array, defaults to False.
            timeout (float): Optional override driver timeout for command,
                defaults to None.
        Returns:
            dict: parsed json data
        """
        self.logger.debug("send_and_parse_cmd("
                          "cmd=%r, "
                          "timeout=%r)", cmd, timeout)
        resp = self._send_cmd(cmd, timeout=timeout)

        if resp['result'] == 0:
            return resp
        return self._error_msg(resp['result'])

    def read_bytes(self, index, size=1, timeout=None):
        """Read bytes from driver and parse the output.

        Send the ``rr <index> <size>`` command to the driver.

        Args:
            index (int): Index of the memory map register.
            size (int): Amount of bytes to read, defaults to 1.
            timeout (float): Optional override driver timeout for command,
                defaults to None.

        Return:
            list: bytes from device.


        """
        self.logger.debug("read_bytes("
                          "index=%r, "
                          "size=%r, "
                          "timeout=%r)", index, size, timeout)
        return self.send_and_parse_cmd((f'rr {index} {size}'), timeout)['data']

    def write_bytes(self, index, data, timeout=None):
        """Write bytes in the register map.

        Args:
            index (int): Index of the memory map register.
            data (list): Data to write, list of bytes.
            timeout (float): Optional override driver timeout for command,
                defaults to None.

        Exceptions:
            IOError: Errno based error from device
            TimeoutError: Device did not respond
        """
        self.logger.debug("write_bytes(index=%r, "
                          "data=%r, "
                          "timeout=%r)", index, data, timeout)
        wbytes = " ".join(map(str, data))
        cmd = f"wr {index} {wbytes}"
        self.send_and_parse_cmd(cmd, timeout=timeout)

    def commit(self, timeout=None):
        """Commit device configuration changes.

        This will cause any changes in configuration to be applied. Call
        after writing a register.

        Args:
            timeout (float): Optional override driver timeout for command,
                defaults to None.

        Exceptions:
            IOError: Errno based error from device
            TimeoutError: Device did not respond
        """
        self.send_and_parse_cmd("ex", timeout=timeout)

    def soft_reset(self, timeout=None):
        """Send command to get the device to reset itself.

        Args:
            timeout (float): Optional override driver timeout for command,
                defaults to None.

        Exceptions:
            IOError: Errno based error from device
            TimeoutError: Device did not respond
        """
        self.logger.debug("soft_reset(timeout=%r", timeout)
        self.send_and_parse_cmd("mcu_rst", timeout=timeout)

    def get_version(self, timeout=None):
        """Get interface version from device.

        Args:
            timeout (float): Optional override driver timeout for command,
                defaults to None.

        Returns:
            str: version string

        Exceptions:
            IOError: Errno based error from device
            TimeoutError: Device did not respond
        """
        self.logger.debug("get_version(timeout=%r", timeout)
        resp = self.send_and_parse_cmd("version", timeout=timeout)
        return resp['version']


class MmIf:
    """Interface to a device memory map.

    Attributes:
        parser (obj): The type of parser to use, defaults to MmJsonParser.
        mem_map (dict): Register memory mapping information.
    """

    def __init__(self, *args, **kwargs):
        """Initialize driver and parser to interface to memory map device.

        Args:
            driver_type (string): Selects driver type to use, defaults to
                "serial".
            parser_type (string): Selects parser type to use, defaults to
                "json".
            mem_map (dict, optional): Memory map for device. Optional if
                ``mm_path`` is provided.
            mm_path (string, optional): Path to memory map, not needed if
                ``mem_map`` is used.
            default_retry (int, optional): Default amount of retries for each
                call, defaults to 0.
            frag_size (int, optional): Max amount of single registers to access
                in one command, defaults to None which has no limit.
            args: Variable arguments to pass to the driver.
            kwargs: Keyword arguments to pass to the driver.

        Note:
            For args and kwargs, check specific driver for clarification.
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.debug("__init__(args=%r, kwargs=%r)", args, kwargs)

        driver_type = kwargs.pop('driver_type', 'serial')
        parser_type = kwargs.pop('parser_type', 'json')
        self.default_retry = kwargs.pop('default_retry', 0)
        self.frag_size = kwargs.pop('frag_size', None)
        mm_path = kwargs.pop('mm_path', None)
        if mm_path is not None:
            mm_path = import_mm_from_csv(mm_path)
        self.mem_map = kwargs.pop('mem_map', mm_path)
        # The pop trick doesn't work here because it evaluates the function
        if 'driver' in kwargs:
            self._driver = kwargs['driver']
        else:
            self._driver = self._driver_from_config(driver_type,
                                                    *args, **kwargs)
        self.parser = self._parser_from_config(parser_type)

    @property
    def driver(self):
        """obj: Driver for communitcating with device.

        defaults to SerialDriver.
        """
        return self._driver

    @driver.setter
    def driver(self, val):
        self.logger.debug("driver(val=%r)", val)
        self._driver = val
        # I don't remember why we needed this but it is somehow important
        # I think it is something to do with reverse dependency issues
        # After this is used we can check if it can be removed and properly
        # throw the error
        try:
            self.parser.driver = self._driver
        except AttributeError:
            self.logger.warning("AttributeError setting parser driver")

    def _driver_from_config(self, driver_type, *args, **kwargs):
        """Return driver instance given configuration."""
        self.logger.debug("_driver_from_config("
                          "driver_type=%r"
                          "args=%r"
                          "kwargs=%r)", driver_type, args, kwargs)
        if driver_type == 'serial':
            return SerialDriver(*args, **kwargs)
        raise NotImplementedError()

    def _parser_from_config(self, parser_type):
        """Return driver instance given configuration."""
        self.logger.debug("_parser_from_config("
                          "driver_type=%r)", parser_type)
        if parser_type == 'json':
            return MmJsonParser(self.driver)
        raise NotImplementedError()

    def _retry_func(self, func, retry, *args, **kwargs):
        self.logger.debug("_retry_func(func=%r, "
                          "retry=%r, "
                          "args=%r, "
                          "kwargs=%r)", func, retry, args, kwargs)
        resp = None
        final_exc = None
        if retry is None:
            retry = self.default_retry
        for _ in range(retry + 1):
            try:
                resp = func(*args, **kwargs)
                break
            except (MM_IF_EXCEPTIONS) as exc:
                self.logger.warning("failed func due to %r, retrying ", exc)
                final_exc = exc
        else:
            raise final_exc
        return resp

    def commit(self, timeout=None, retry=None):
        """Commit device configuration changes.

        This will cause any changes in configuration to be applied. Call
        after writing a register.

        Args:
            timeout (float): Optional override driver timeout for command,
                defaults to None.

        Exceptions:
            IOError: Errno based error from device
            TimeoutError: Device did not respond
        """
        self.logger.debug("commit(timeout=%r,retry=%r)", timeout, retry)
        self._retry_func(self.parser.commit, retry, timeout=timeout)

    def soft_reset(self, timeout=None, retry=None):
        """Send command to get the device to reset itself.

        Args:
            timeout (float): Optional override driver timeout for command,
                defaults to None.

        Exceptions:
            IOError: Errno based error from device
            TimeoutError: Device did not respond
        """
        self.logger.debug("soft_reset(timeout=%r,retry=%r)", timeout, retry)
        self._retry_func(self.parser.soft_reset, retry, timeout=timeout)

    def get_version(self, timeout=None, retry=None):
        """Get interface version from device.

        Args:
            timeout (float): Optional override driver timeout for command,
                defaults to None.

        Returns:
            str: Version string

        Exceptions:
            IOError: Errno based error from device
            TimeoutError: Device did not respond
        """
        self.logger.debug("get_version(timeout=%r, retry=%r)", timeout, retry)
        version = self._retry_func(self.parser.get_version, retry,
                                   timeout=timeout)
        return version

    @staticmethod
    def _c_cast(num, prim_type):
        if prim_type == "uint8_t":
            num = c_uint8(num).value
        if prim_type == "int8_t":
            num = c_int8(num).value
        if prim_type == "uint16_t":
            num = c_uint16(num).value
        if prim_type == "int16_t":
            num = c_int16(num).value
        if prim_type == "uint32_t":
            num = c_uint32(num).value
        if prim_type == "int32_t":
            num = c_int32(num).value
        return num

    @staticmethod
    def _parse_array(data, type_size, prim_type):
        parsed_data = []
        try:
            elements = int(len(data)/type_size)
            for i in range(0, elements):
                num = int.from_bytes(data[i*type_size:(i+1)*type_size],
                                     byteorder='little')
                parsed_data.append(MmIf._c_cast(num, prim_type))
        except (ValueError, TypeError):
            return data
        return parsed_data

    @staticmethod
    def _parse_resp_bit(reg_info, r_data):
        bits = int(reg_info['bits'])
        offset = int(reg_info['bit_offset'])
        bit_mask = (2 ** bits) - 1
        data = int.from_bytes(r_data, byteorder='little')
        data = data >> offset
        return data & bit_mask

    def _get_off_size_reg(self, reg_info, offset, size):
        self.logger.debug("_get_off_size_reg("
                          "reg_info=%r, "
                          "offset=%r, "
                          "size=%r)", reg_info, offset, size)
        if size is None:
            if reg_info['total_size'] == '':
                size = reg_info['type_size']
            else:
                size = reg_info['total_size']
        elif reg_info['total_size'] != '':
            size = int(reg_info['type_size']) * int(size)
        if reg_info['total_size'] != '':
            offset = int(offset)
            offset *= int(reg_info['type_size'])
            offset += int(reg_info['offset'])
            max_mem = int(reg_info['offset']) + int(reg_info['total_size'])
            if max_mem < offset + size:
                raise ValueError(f"array out of bounds, "
                                 f"{offset+size} must be greater than{max_mem}"
                                 f", {reg_info}")
        else:
            offset = int(reg_info['offset'])
            size = int(reg_info['type_size'])
        return offset, size

    def _parse_resp_reg(self, reg_info, r_data):
        self.logger.debug("_parse_resp_reg("
                          "reg_info=%r, "
                          "r_data=%r)", reg_info, r_data)
        data = self._parse_array(r_data, reg_info['type_size'],
                                 reg_info['type'])
        if reg_info['total_size'] == '':
            return data[0]
        return data

    def _read_bytes_with_parser(self, offset, size, retry, timeout):
        self.logger.debug("_read_bytes_with_parser("
                          "offset=%r, "
                          "size=%r, "
                          "retry=%r, "
                          "timeout=%r)", offset, size, retry, timeout)
        data = []

        frag_size = self.frag_size or size
        for byte_cnt in range(0, size, frag_size):
            rbytes = self._retry_func(self.parser.read_bytes,
                                      retry,
                                      offset + byte_cnt,
                                      min(size-byte_cnt, frag_size),
                                      timeout=timeout)
            data.extend(rbytes)
        return data

    # pylint: disable=R0913
    def read_reg(self, reg, offset=0, size=None,
                 timeout=None, retry=None):
        """Read a register defined by the memory map.

        Args:
            reg (str): The name of the register to read.
            offset (int): The number of elements to offset in an array.
            size (int): The number of elements to read in an array.
            timeout (float): Optional override driver timeout for command,
                defaults to None.
            retry (int): Retries on failure

        Returns:
            int, list: Parsed response depending on register type.

        Exceptions:
            IOError: Errno based error from device
            TimeoutError: Device did not respond
            ValueError: Argument incorrect
        """
        self.logger.debug("read_reg("
                          "reg=%r, "
                          "offset=%r, "
                          "size=%r, "
                          "timeout=%r, "
                          "retry=%r)", reg, offset, size, timeout, retry)
        reg_info = self.mem_map[reg]

        offset, size = self._get_off_size_reg(reg_info, offset, size)

        data = self._read_bytes_with_parser(offset, size, retry, timeout)

        if reg_info['bits'] != '':
            data = self._parse_resp_bit(reg_info, data)
        else:
            data = self._parse_resp_reg(reg_info, data)
        return data

    def _get_off_size_regs(self, regs):
        self.logger.debug("_get_off_size_regs(regs=%r)", regs)
        size = 0
        offset = self.mem_map[regs[0]]['offset']
        last_size = self.mem_map[regs[-1]]['total_size']
        if last_size == '':
            last_size = self.mem_map[regs[-1]]['type_size']
        size = self.mem_map[regs[-1]]['offset'] + last_size - offset
        return offset, size

    def _parse_read_struct(self, regs, rdata, data_has_name):
        self.logger.debug("_parse_read_struct("
                          "regs=%r, "
                          "rdata=%r, "
                          "data_has_name=%r)", regs, rdata, data_has_name)
        resps = []
        last_offset = -1
        data = None
        for reg in regs:

            reg_info = self.mem_map[reg]
            offset, reg_size = self._get_off_size_reg(reg_info, 0, None)

            # In order to not remove data when bitfields are used we make
            # sure the offset does not change when popping new data
            if offset != last_offset:
                data = [rdata.pop(0) for idx in range(reg_size)]
            last_offset = offset
            if reg.endswith('.res'):
                continue
            if reg_info['bits'] != '':
                result = self._parse_resp_bit(reg_info, data)
            else:
                result = self._parse_resp_reg(reg_info, data)
            if data_has_name:
                resps.append({reg: result})
            else:
                resps.append(result)
        return resps

    def read_struct(self, struct, data_has_name=True, timeout=None,
                    retry=None):
        """Read a set of registers defined by the memory map.

        Results ending with ``.res`` are stripped as they are a keyword for
        reserved records.

        Args:
            cmd_start (str): The name if the structure to read.
            data_has_name (bool): Include the record name in the data,
                defaults to True.
            timeout (float): Optional override driver timeout for command,
                defaults to None.
            retry (int): Optional override retry count, defaults to None.

        Returns:
            list: Parsed responses depending on each register type.

        Exceptions:
            IOError: Errno based error from device
            TimeoutError: Device did not respond
            ValueError: Argument incorrect
        """
        self.logger.debug("read_struct(struct=%r, "
                          "data_has_name=%r, "
                          "timeout=%r, "
                          "retry=%r)", struct, data_has_name, timeout, retry)
        started = False
        regs = []
        # We want to collect all names starting with the cmd_start
        if struct == '.':
            regs = list(self.mem_map.keys())
        else:
            for name in self.mem_map.keys():
                if name.startswith(struct):
                    regs.append(name)
                    started = True
                elif started is True:
                    # If there is a break in the list we should exit out
                    # otherwise the data will not be grouped.
                    break
        offset, size = self._get_off_size_regs(regs)
        data = self._read_bytes_with_parser(offset, size, retry, timeout)
        data = self._parse_read_struct(regs, data, data_has_name)
        return data

    def _write_data_to_bytes(self, reg_info, data):
        self.logger.debug("_write_data_to_bytes(reg_info=%r, "
                          "data=%r)", reg_info, data)
        signed = False
        if reg_info['type'].startswith('int'):
            signed = True
        wdata = bytearray()
        if isinstance(data, int):
            wdata = data.to_bytes(reg_info['type_size'], "little",
                                  signed=signed)
        else:
            for element in data:
                wdata += element.to_bytes(reg_info['type_size'], "little",
                                          signed=signed)
        return list(wdata)

    def _write_bytes_with_parser(self, data, offset, size, retry, timeout):
        self.logger.debug("_write_bytes_with_parser("
                          "data=%r, "
                          "offset=%r, "
                          "size=%r, "
                          "retry=%r, "
                          "timeout=%r, ", data, offset, size, retry, timeout)
        frag_size = self.frag_size or size
        for byte_cnt in range(0, size, frag_size):
            bytes_to_write = min(size - byte_cnt, frag_size)
            self._retry_func(self.parser.write_bytes,
                             retry,
                             offset + byte_cnt,
                             data[:bytes_to_write],
                             timeout=timeout)
            for _ in range(bytes_to_write):
                data.pop(0)

    @staticmethod
    def _parse_write_bit(cmd, w_data, r_data):
        bits = int(cmd['bits'])
        offset = int(cmd['bit_offset'])
        bit_mask = (2 ** bits) - 1
        if w_data > bit_mask:
            raise ValueError(f"Writing value outside bitfield"
                             f" {w_data} !<= {bit_mask}")
        data = r_data & ~(bit_mask << offset)
        data = (w_data << offset) | data
        return list(data.to_bytes(cmd['type_size'], 'little'))

    @staticmethod
    def _prep_write_data(data):
        if isinstance(data, list):
            if len(data) == 1:
                data = data[0]
        if isinstance(data, list):
            elements = []
            for element in data:
                elements.append(literal_eval(str(element)))
            data = elements
        else:
            data = literal_eval(str(data))
        return data

    def _write_formatted_bytes(self, reg_info, data, offset, size, timeout,
                               retry):
        wb_offset, wb_size = self._get_off_size_reg(reg_info, offset, size)
        wb_data = self._write_data_to_bytes(reg_info, data)
        if reg_info['bits'] != '':
            rb_data = self._read_bytes_with_parser(wb_offset, wb_size, retry,
                                                   timeout)
            rb_data = int.from_bytes(bytearray(rb_data), 'little')
            self.logger.debug("_parse_write_bit(reg_info=%r, "
                              "data=%r, "
                              "rb_data=%r)", reg_info, data, rb_data)
            wb_data = self._parse_write_bit(reg_info, data, rb_data)
        self._write_bytes_with_parser(wb_data, wb_offset, wb_size, retry,
                                      timeout)

    def write_reg(self, reg, data, offset=0, verify=False, timeout=None,
                  retry=None):
        """Write a register defined by the memory map.

        Args:
            cmd_name (str): The name of the register to write.
            data (list, int, str): The data to write to the register.
            verify (bool): Verify the register has changed, defaults to False
            offset (int): The number of elements to offset in an array,
                defaults to 0.
            timeout (float): Optional override driver timeout for command,
                defaults to None.
            retry (int): Optional override retry count, defaults to None.

        Exceptions:
            IOError: Errno based error from device
            TimeoutError: Device did not respond
            ValueError: Argument incorrect
            TypeError: Data type not correct
        """
        self.logger.debug("write_bytes(reg=%r, "
                          "data=%r, "
                          "offset=%r, "
                          "timeout=%r,"
                          "retry=%r)", reg, data, offset, timeout, retry)

        data = self._prep_write_data(data)

        self.logger.debug("parser data is %r", data)

        reg_info = self.mem_map[reg]
        if isinstance(data, list):
            size = len(data)
            if size > 1 and reg_info['bits'] != '':
                raise TypeError(f"Cannot parse arrays of bitfields{data}")
            if size > 1 and reg_info['total_size'] == '':
                raise TypeError(f"Cannot parse arrays if int, {data}")
        elif isinstance(data, int):
            size = 1
        else:
            raise TypeError(f"Cannot parse {data}")

        self._write_formatted_bytes(reg_info, data, offset, size, timeout,
                                    retry)

        if verify:
            v_data = self.read_reg(reg, offset=offset, timeout=timeout,
                                   size=size, retry=retry)
            if data != v_data:
                raise RuntimeError(f"Verification of written data failed! "
                                   f"wrote {data} but read {v_data}")

    def commit_write(self, reg, data, offset=0, verify=False, timeout=None,
                     retry=None):
        """Write and commit in one step.

        This may need to be overridden if commit involves more complicated
        checks.

        Args:
            cmd_name (str): The name of the register to write.
            data (list, int, str): The data to write to the register.
            verify (bool): Verify the register has changed, defaults to False
            offset (int): The number of elements to offset in an array,
                defaults to 0.
            timeout (float): Optional override driver timeout for command,
                defaults to None.
            retry (int): Optional override retry count, defaults to None.

        Exceptions:
            IOError: Errno based error from device
            TimeoutError: Device did not respond
            ValueError: Argument incorrect
            TypeError: Data type not correct
        """
        self.write_reg(reg, data, offset=offset, verify=verify,
                       timeout=timeout, retry=retry)
        self.commit(timeout=timeout, retry=retry)
