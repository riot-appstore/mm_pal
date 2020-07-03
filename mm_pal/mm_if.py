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
`read_register` and have an expected response shown in the
``response_schema.json``.

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


RESULT_SUCCESS = 'Success'
"""str: Value of the ``result`` when command was successful."""

RESULT_ERROR = 'Error'
"""str: Value of the ``result`` when command had an error.

This occurs when device receives a command but returns an error.
"""

RESULT_TIMEOUT = 'Timeout'
"""str: Value of the ``result`` when command had a timeout.

This occurs when device either does not receive a command or an issue with
the device prevent any parsable response.
"""


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
    with open(path) as csvfile:
        rows = list(csv.reader(csvfile, quotechar="'"))
        for row in range(1, len(rows)):
            _try_parse_int_list(rows[row])
            cmd = dict(zip(rows[0], rows[row]))
            mem_map[rows[row][rows[0].index('name')]] = cmd
    return mem_map


class MmJsonParser:
    """Json style parser for interfacing to memory map based devices.

    Send command and parse response to fit response schema. Read lines
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

            {'cmd': "read_bytes(index=0, size=3)",
             'data'=[0, 1, 2],
             'result'="Success"}
    """

    def __init__(self, driver):
        """Instantiate parser instance and start logger.

        Args:
            driver (obj): Driver to send and receive information to parse.
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.driver = driver

    def read_bytes(self, index, size=1, to_byte_array=False, timeout=None):
        """Read bytes from driver and parse the output.

        Send the ``rr <index> <size>`` command to the driver.

        Args:
            index (int): Index of the memory map register.
            size (int): Amount of bytes to read, defaults to 1.
            to_byte_array (bool): Forces result to remain as byte array,
                defaults to False.
            timeout (float): Optional override driver timeout for command,
                defaults to None.

        Return:
            dict: Parsed command response.

            Example:
            ::

                {
                    'cmd': read_reg_cmd_string,
                    'data': bytes_read_from_device,
                    'result': "Success"
                }


        """
        return self.send_and_parse_cmd((f'rr {index} {size}'),
                                       to_byte_array, timeout)

    @staticmethod
    def _error_msg(data):
        if data not in errno.errorcode:
            return "Unknown Error[{}]".format(data)
        s_errcode = errno.errorcode[data]
        s_errmsg = os.strerror(data)
        return "{}-{} [{}]".format(s_errcode, s_errmsg, data)

    @staticmethod
    def _bytes_to_int(data_list):
        """Try to parse a list of bytes to an integer.

        >>> MmJsonParser._bytes_to_int([0,1])
        256
        """
        val = 0
        try:
            for index, num in enumerate(data_list):
                if num > 255 or num < 0:
                    raise ValueError
                val += num << (index * 8)
        except (ValueError, TypeError):
            return data_list
        return val

    @staticmethod
    def _try_data_to_int(cmd_info):
        """Try to parse data to an integer."""
        if 'data' in cmd_info:
            cmd_info['data'] = MmJsonParser._bytes_to_int(cmd_info['data'])

    def _send_cmd(self, send_cmd, timeout, end_key='result'):
        self.driver.writeline(send_cmd)
        cmd_info = {}
        decode_error = False
        while end_key not in cmd_info:
            line = self.driver.readline(timeout)
            try:
                cmd_info.update(json.loads(line))
            except json.decoder.JSONDecodeError:
                decode_error = True
        if decode_error:
            raise json.decoder.JSONDecodeError
        return cmd_info

    def send_and_parse_cmd(self, send_cmd, to_byte_array=False, timeout=None):
        """Return a dictionary with information from the event.

        Args:
            send_cmd (str): The command to write to the device.
            to_byte_array (bool): If True and data is bytes leave it as an
                array, defaults to False.
            timeout (float): Optional override driver timeout for command,
                defaults to None.
        Returns:
            dict:
            See the ``schemas/response_schema.json``
        """
        cmd_info = {'cmd': send_cmd}
        try:
            cmd_info.update(self._send_cmd(send_cmd, timeout=timeout))
            if to_byte_array is False:
                if 'data' in cmd_info:
                    self._try_data_to_int(cmd_info)
        except json.decoder.JSONDecodeError:
            cmd_info['result'] = RESULT_ERROR
            cmd_info['msg'] = "Failed to parse response"
        except TimeoutError:
            cmd_info['result'] = RESULT_TIMEOUT
        else:
            if cmd_info['result'] == 0:
                cmd_info['result'] = RESULT_SUCCESS
            else:
                cmd_info['data'] = cmd_info['result']
                cmd_info['result'] = RESULT_ERROR
                cmd_info['msg'] = self._error_msg(cmd_info['data'])
        return cmd_info

    @staticmethod
    def _write_byte_arg_to_string(data, size):
        ret_str = ''
        if isinstance(data, list):
            for data_byte in data:
                for i in range(0, size):
                    ret_str += ' {}'.format(
                        (int(data_byte) >> ((i) * 8)) & 0xFF)
        else:
            for i in range(0, size):
                ret_str += ' {}'.format((int(data) >> ((i) * 8)) & 0xFF)
        return ret_str

    def write_bytes(self, index, data, size=1, timeout=None):
        """Write bytes in the register map.

        Args:
            index (int): Index of the memory map register.
            data (list, int): Data to write.
            size (int): Size of bytes of the data type, defaults to 1.
            timeout (float): Optional override driver timeout for command,
                defaults to None.

        Returns:
            dict: Parsed command response.

            Example:
            ::

                {
                    'cmd': write_reg_cmd_string,
                    'result': "Success"
                }
        """
        cmd = f"wr {index}{self._write_byte_arg_to_string(data, size)}"
        return self.send_and_parse_cmd(cmd, timeout=timeout)

    def execute_changes(self, timeout=None):
        """Execute device configuration changes.

        This will cause any changes in configuration to be applied. Call
        after writing a register.

        Args:
            timeout (float): Optional override driver timeout for command,
                defaults to None.

        Returns:
            dict: Parsed command response.

            Example:
            ::

                {
                    'cmd': execute_changes_cmd_string,
                    'result': "Success"
                }
        """
        return self.send_and_parse_cmd("ex", timeout=timeout)

    def soft_reset(self, timeout=None):
        """Send command to get the device to reset itself.

        Args:
            timeout (float): Optional override driver timeout for command,
                defaults to None.

        Returns:
            dict: Parsed command response.

            Example:
            ::

                {
                    'cmd': soft_reset_cmd_string,
                    'result': "Success"
                }
        """
        return self.send_and_parse_cmd("mcu_rst", timeout=timeout)

    def get_version(self, timeout=None):
        """Get interface version from device.

        Args:
            timeout (float): Optional override driver timeout for command,
                defaults to None.

        Returns:
            dict: Parsed command response.

            Example:
            ::

                {
                    'version': "0.0.0",
                    'result': "Success"
                }
        """
        return self.send_and_parse_cmd("version", timeout=timeout)


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
            args: Variable arguments to pass to the driver.
            kwargs: Keyword arguments to pass to the driver.

        Note:
            For args and kwargs, check specific driver for clarification.
        """
        self.logger = logging.getLogger(self.__class__.__name__)

        driver_type = kwargs.pop('driver_type', 'serial')
        parser_type = kwargs.pop('parser_type', 'json')
        mm_path = kwargs.pop('mm_path', None)
        if mm_path is not None:
            mm_path = import_mm_from_csv(mm_path)
        self.mem_map = kwargs.pop('mem_map', mm_path)
        self._driver = self._driver_from_config(driver_type, *args, **kwargs)
        self.parser = self._parser_from_config(parser_type)

    @property
    def driver(self):
        """obj: Driver for communitcating with device.

        defaults to SerialDriver.
        """
        return self._driver

    @driver.setter
    def driver(self, val):
        self._driver = val
        try:
            self.parser.driver = self._driver
        except AttributeError:
            pass

    @staticmethod
    def _driver_from_config(driver_type, *args, **kwargs):
        """Return driver instance given configuration."""
        if driver_type == 'serial':
            return SerialDriver(*args, **kwargs)
        raise NotImplementedError()

    def _parser_from_config(self, parser_type):
        """Return driver instance given configuration."""
        if parser_type == 'json':
            return MmJsonParser(self.driver)
        raise NotImplementedError()

    def _read_bits(self, index, offset, bit_amount, timeout=None):
        """Read specific bits in the register map.

        Args:
            index (int): Index of the memory map (address or offset of bytes).
            offset (int): The bit offset for the bitfield.
            bit_amount (int): The amount of bits within the bitfield.
            timeout (float): Optional override driver timeout for command,
                defaults to None.

        Returns:
            dict: Parsed command response.

            Example:
            ::

                {
                    'cmd': [read_bits_cmd, read_bytes_cmd],
                    'data': data_bits_value,
                    'result': "Success"
                }
        """
        bit_amount = int(bit_amount)
        offset = int(offset)
        index = int(index)
        bytes_to_read = int((bit_amount - 1 + offset)/8 + 1)
        bit_mask = (2 ** bit_amount) - 1
        cmd_info = self.parser.read_bytes(index, bytes_to_read,
                                          timeout=timeout)
        if cmd_info['result'] == RESULT_SUCCESS:
            cmd_info['cmd'] = ['read_bits({},{},{})'.format(index, offset,
                                                            bit_amount),
                               cmd_info['cmd']]
            cmd_info['data'] = cmd_info['data'] >> offset
            cmd_info['data'] = cmd_info['data'] & bit_mask
        return cmd_info

    # pylint: disable=R0913
    def _write_bits(self, index, offset, bit_amount, data, timeout=None):
        """Modify specific bits in the register map.

        Args:
            index (int): Index of the memory map (address or offset of bytes).
            offset (int): The bit offset for the bitfield.
            bit_amount (int): The amount of bits within the bitfield.
            data (int): The data to be converted to bytes then written to
                the map.
            timeout (float): Optional override driver timeout for command,
                defaults to None.

        Returns:
            dict: Parsed command response.

            Example:
            ::
                {
                    'cmd': [write_bits_cmd, write_bytes_cmd],
                    'result': "Success"
                }
        """
        cmds = ['write_bits({},{},{},{})'.format(index, offset,
                                                 bit_amount, data)]
        bit_amount = int(bit_amount)
        offset = int(offset)
        index = int(index)
        bytes_to_read = int((bit_amount - 1 + offset)/8 + 1)
        cmd_info = self.parser.read_bytes(index, bytes_to_read,
                                          timeout=timeout)
        if cmd_info['result'] != RESULT_SUCCESS:
            return cmd_info
        cmds.append(cmd_info['cmd'])
        bit_mask = int((2 ** bit_amount) - 1)
        bit_mask = bit_mask << offset
        cmd_info['data'] = cmd_info['data'] & (~bit_mask)
        shifted_data = cmd_info['data'] | ((data << offset) & bit_mask)
        cmd_info = self.parser.write_bytes(index, shifted_data,
                                           bytes_to_read, timeout=timeout)
        cmds.append(cmd_info['cmd'])
        if cmd_info['result'] == RESULT_SUCCESS:
            cmd_info['cmd'] = 'write_bits {} {} {} {}'.format(index, offset,
                                                              bit_amount, data)
        cmd_info['cmd'] = cmds
        return cmd_info

    def execute_changes(self, timeout=None):
        """Execute device configuration changes.

        This will cause any changes in configuration to be applied. Call
        after writing a register.

        Args:
            timeout (float): Optional override driver timeout for command,
                defaults to None.

        Returns:
            dict: Parsed command response.

            Example:
            ::

                {
                    'cmd': execute_changes_cmd_string,
                    'result': "Success"
                }
        """
        return self.parser.execute_changes(timeout=timeout)

    def soft_reset(self, timeout=None):
        """Send command to get the device to reset itself.

        Args:
            timeout (float): Optional override driver timeout for command,
                defaults to None.

        Returns:
            dict: Parsed command response.

            Example:
            ::

                {
                    'cmd': soft_reset_cmd_string,
                    'result': "Success"
                }
        """
        return self.parser.soft_reset(timeout=timeout)

    def get_version(self, timeout=None):
        """Get interface version from device.

        Args:
            timeout (float): Optional override driver timeout for command,
                defaults to None.

        Returns:
            dict: Parsed command response.

            Example:
            ::

                {
                    'version': "0.0.0",
                    'result': "Success"
                }
        """
        return self.parser.get_version(timeout=timeout)

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

    # pylint: disable=R0913
    def read_reg(self, cmd_name, offset=0, size=None,
                 to_byte_array=False, timeout=None):
        """Read a register defined by the memory map.

        Args:
            cmd_name (str): The name of the register to read.
            offset (int): The number of elements to offset in an array.
            size (int): The number of elements to read in an array.
            to_byte_array (bool): If True and data is bytes leave it as list,
                defaults to False.
            timeout (float): Optional override driver timeout for command,
                defaults to None.

        Returns:
            dict: Parsed command response.

            Example:
            ::

                {
                    'cmd': [read_register_cmd, read_bytes_cmd],
                    'data': register_data,
                    'result': "Success"
                }
        """
        cmd = self.mem_map[cmd_name]
        response = None
        if size is None:
            if cmd['total_size'] == '':
                size = cmd['type_size']
            else:
                size = cmd['total_size']
        else:
            if cmd['total_size'] != '':
                size = int(cmd['type_size']) * int(size)
        if cmd['bits'] != '':
            response = self._read_bits(cmd['offset'],
                                       cmd['bit_offset'],
                                       cmd['bits'],
                                       timeout=timeout)
        elif cmd['total_size'] != '':
            offset = int(offset)
            offset *= int(cmd['type_size'])
            offset += int(cmd['offset'])
            response = self.parser.read_bytes(offset, size, True, timeout)
            response['data'] = self._parse_array(response['data'],
                                                 cmd['type_size'],
                                                 cmd['type'])
        else:
            response = self.parser.read_bytes(cmd['offset'], size,
                                              to_byte_array)
            if 'data' in response:
                response['data'] = self._c_cast(response['data'], cmd['type'])
        response['cmd'] = ['read_reg({},{},{})'.format(cmd_name, offset, size),
                           response['cmd']]
        return response

    def write_reg(self, cmd_name, data, offset=0, timeout=None):
        """Write a register defined by the memory map.

        Args:
            cmd_name (str): The name of the register to write.
            data (list, int): The data to write to the register.
            offset (int): The number of elements to offset in an array,
                defaults to 0.
            timeout (float): Optional override driver timeout for command,
                defaults to None.

        Returns:
            dict: Parsed command response.

            Example:
            ::

                {
                    'cmd': [write_register_cmd, write_bytes_cmd],
                    'result': "Success"
                }
        """
        cmd = self.mem_map[cmd_name]
        data = literal_eval(str(data))
        response = None
        if cmd['bits'] != '':
            response = self._write_bits(cmd['offset'],
                                        cmd['bit_offset'],
                                        cmd['bits'], data)
        elif cmd['total_size'] != '':
            offset = int(offset)
            offset *= int(cmd['type_size'])
            offset += int(cmd['offset'])
            response = self.parser.write_bytes(offset, data,
                                               int(cmd['type_size']),
                                               timeout=timeout)
        else:
            response = self.parser.write_bytes(cmd['offset'], data,
                                               int(cmd['type_size']),
                                               timeout=timeout)
        response['cmd'] = ['write_reg({},{},{})'.format(cmd_name, data,
                                                        offset),
                           response['cmd']]
        return response

    def read_struct(self, cmd_name, data_has_name=True, timeout=None):
        """Read a set of registers defined by the memory map.

        Results ending with ``.res`` are stripped as they are a keyword for
        reserved records.

        Args:
            cmd_name (str): The name if the structure to read.
            data_has_cmd (bool): Include the record name in the data,
                defaults to false.
            timeout (float): Optional override driver timeout for command,
                defaults to None.

        Returns:
            list: List of parsed command response.

        Example:
        ::

            [{
                'cmd': [read_register_cmd0, read_bytes_cmd0],
                'data': read_data,
                'result': "Success"
            },
            {
                'cmd': [read_register_cmd1, read_bytes_cmd1],
                'data': read_data,
                'result': "Success"
            }]
        """
        response = []
        for cmd in self.mem_map.keys():
            if cmd.startswith(cmd_name) and not cmd.endswith('.res'):
                response.append(self.read_reg(cmd, timeout=timeout))
                if data_has_name:
                    response[-1]['data'] = {cmd: response[-1]['data']}
        return response
