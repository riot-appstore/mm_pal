# Copyright (c) 2020 HAW Hamburg
#
# This file is subject to the terms and conditions of the MIT License. See the
# file LICENSE in the top level directory for more details.
# SPDX-License-Identifier:    MIT
"""Cmd wrapper for memory map interface.

Provide common functionalities to create a cli interface based on
mm_pal devices. This is based on the ``cmd`` library in python. It
exposes all common commands and allows for autocompletion of arguments.
An example of how to integrate it is in the ``mock_pal.mock_cli``
module.

A basic example of how to integrate this into code is the following:
::

    class MyCli(MmCmd):

        prompt = "MyPrompt: "

        def __init__(self, **kwargs):
            if 'dev_driver' in kwargs:
                super().__init__(kwargs['dev_driver'])
            else:
                super().__init__(serial_connect_wizard(MyIf, **kwargs))

"""
import os
import glob
import cmd
from json import dumps
import logging
try:
    import readline
except ImportError:  # pragma: no cover
    readline = None
    logging.warning("readline package could not be found!")
    logging.warning("History will not be available.")
import serial.tools.list_ports
from mm_pal.mm_if import RESULT_SUCCESS


_HISTFILE = os.path.join(os.path.expanduser("~"), ".mm_history")


def write_history_file(history_file=_HISTFILE):
    """Write history file.

    Use before closing program to ensure history is saved. If readline is not
    installed nothing occurs.

    Args:
        history_file (str): Path to the history file,
            defaults to ~/.mm_history.
    """
    try:
        if readline is not None:
            # pylint: disable=no-member
            readline.write_history_file(history_file)
    except IOError:
        pass


def serial_connect_wizard(if_obj, **kwargs):
    """Console based wizard to help connect to a serial port.

    Args:
        if_obj (obj): Interface class to instantiate.
        **kwargs: Keyword args to pass to the instantation of the if_obj.
            ``port`` keyword is overwritten with selected serial port.

    Return:
        (obj): Instantiated if_obj.

    Raises:
        ConnectionError: No connections available.
    """
    serial_devices = sorted(serial.tools.list_ports.comports())
    if len(serial_devices) == 0:
        raise ConnectionError("Could not find any available devices")
    if len(serial_devices) == 1:
        print(f'Connected to {serial_devices[0][0]}')
        kwargs['port'] = serial_devices[0][0]
        return if_obj(**kwargs)

    print('Select a serial port:')
    max_num = 0
    for i, s_dev in enumerate(serial_devices):
        print(f"{i}: {s_dev}")
        max_num = i
    s_num = -1
    while s_num < 0 or max_num < s_num:
        try:
            s_num = int(input("Selection(number): "))
        except ValueError:
            print("Invalid selection!")
    kwargs['port'] = serial_devices[int(s_num)][0]
    return if_obj(**kwargs)


class MmCmd(cmd.Cmd):
    """Cmd wrapper for mm_pal based devices.

    Contains common commands to build a cli interface.

    Attributes:
        dev_driver (obj): The device driver used to communicate with the
            device.
    """

    def __init__(self, dev_driver, history_file=_HISTFILE):
        """Instantiate cmd based cli class.

        Args:
            dev_driver (obj): The device driver used to communicate with the
                device.
            history_file (str): Path to history file,
                defaults to ~/.mm_history.
        """
        self.logger = self.logger = logging.getLogger(self.__class__.__name__)
        self._hist_file = history_file
        self.dev_driver = dev_driver
        super().__init__()
        self._data_only = True

    def preloop(self):
        """Before starting cmdloop() read readline history."""
        if readline:
            try:
                if readline is not None:
                    # pylint: disable=no-member
                    readline.read_history_file(self._hist_file)
            except IOError:
                pass

    def postloop(self):
        """On successful exit write history file."""
        write_history_file()

    def do_read_reg(self, arg):
        """Read a register defined by the memory map.

        Usage:
            read_reg <cmd_name> [offset] [size] [to_byte_array] [timeout]

        Args:
            cmd_name (str): The name of the register to read.
            offset (int): The number of elements to offset in an array.
            size (int): The number of elements to read in an array.
            to_byte_array (bool): If True and data is bytes leave it as an
                array.
            timeout (float): Optional timeout value for command specific
                timeouts.

        """
        self._print_func_result(self.dev_driver.read_reg, arg)

    def complete_read_reg(self, text, line, begidx, endidx):
        """Completes arg with memory map record names."""
        # pylint: disable=unused-argument
        return self._complete_map(text, line)

    def do_write_reg(self, arg):
        """Write a register defined by the memory map.

        Note:
            May require ``execute_changes``.

        Usage:
            write_reg <cmd_name> <data> [offset] [timeout]

        Args:
            cmd_name (str): The name of the register to write.
            data (int, list): The data to write to the register.
            offset (int): The number of elements to offset in an array.
            timeout (float): Optional timeout value for command specific
                timeouts.

        Example:
            To write to example_reg 0 the data 42 we can do this:
            ``write_reg example_reg 42 0``

            To write many bytes the data must not be separated by spaces:
            ``write_reg example_reg [1,2,3,4,5,6]``
        """
        self._print_func_result(self.dev_driver.write_reg, arg)

    def complete_write_reg(self, text, line, begidx, endidx):
        """Completes arg with memory map record names."""
        # pylint: disable=unused-argument
        return self._complete_map(text, line)

    def do_read_struct(self, arg):
        """Read a set of registers defined by the memory map.

        Usage:
            read_struct <cmd_name> [timeout]

        Args:
            cmd_name (str): The name if the structure to read.
            timeout (float): Optional timeout value for command specific
                timeouts.
        """
        self._print_func_result(self.dev_driver.read_struct, arg)

    def complete_read_struct(self, text, line, begidx, endidx):
        """Completes arg with memory map record structures."""
        # pylint: disable=unused-argument
        mline = line.partition(' ')[2]
        offs = len(mline) - len(text)
        map_records = [*self.dev_driver.mem_map]
        map_structs = []
        for record in map_records:
            first_name = record.split('.')[0]
            if first_name not in map_structs:
                map_structs.append(first_name)
        return [s[offs:] for s in map_structs if s.startswith(mline)]

    def do_execute_changes(self, arg):
        """Execute/commit device configuration changes.

        Usage:
            execute_changes [timeout]

        Args:
            timeout (float): Optional timeout value for command specific
                timeouts.
        """
        self._print_func_result(self.dev_driver.execute_changes, arg)

    def do_soft_reset(self, arg):
        """Send reset signal to the device.

        Usage:
            philip_reset [timeout]

        Args:
            timeout (float): Optional timeout value for command specific
                timeouts.
        """
        self._print_func_result(self.dev_driver.soft_reset, arg)

    def do_get_version(self, arg):
        """Get the version of the interface from the device.

        Usage:
            get_version
        """
        # pylint: disable=unused-argument
        version = self.dev_driver.get_version().pop('version', "UNKNOWN")

        print(f'Interface version: {version}')

    def do_data_filter(self, arg):
        """Select or toggle filtering for data.

        Usage:
            data_filter [{ON, OFF}]

        Args:
            {ON, OFF}: Turn filtering on or off, if no arg it toggles.
        """
        if arg:
            if arg.upper() == "ON":
                self._data_only = True
                print("Filtering for data")
            elif arg.upper() == "OFF":
                self._data_only = False
                print("Raw data, no filtering")
            else:
                print("Incorrect arg")
        elif self._data_only:
            self._data_only = False
            print("Raw data, no filtering")
        else:
            self._data_only = True
            print("Filtering for data")

    def do_info_reg(self, arg):
        """Print all information of a register or all registers.

        Usage:
            info_reg [cmd_name]

        Args:
            cmd_name (str): Register name to get info, empty will show all.

        Example:
        ::

            > info_reg example_reg
            {
                "access": 3,
                "array_size": 256,
                "bit_offset": "",
                "bits": "",
                "default": "",
                "description": "Example description to register",
                "name": "example_reg",
                "offset": 0,
                "total_size": 256,
                "type": "uint8_t",
                "type_size": 1
            }
        """
        # pylint: disable=unused-argument
        if arg:
            try:
                print(dumps(self.dev_driver.mem_map[arg], sort_keys=True,
                            indent=4))
            except KeyError as exc:
                print(f"Cannot parse {exc}")
        else:
            print(dumps(self.dev_driver.mem_map, sort_keys=True, indent=4))

    def complete_info_reg(self, text, line, begidx, endidx):
        """Completes arg with memory map record names."""
        # pylint: disable=unused-argument
        return self._complete_map(text, line)

    def _complete_map(self, text, line):
        mline = line.partition(' ')[2]
        offs = len(mline) - len(text)
        map_records = filter(lambda x: not x.endswith(".res"),
                             [*self.dev_driver.mem_map])
        return [s[offs:] for s in map_records if s.startswith(mline)]

    def do_info_param(self, arg):
        """Print selected parameter of all registers.

        Usage:
            info_record_type <record_type>

        Args:
            record_type (str): The record type in a map, such as "description".
        """
        try:
            record_types = {}
            for key, val in self.dev_driver.mem_map.items():
                if arg in val:
                    if val[arg]:
                        record_types[key] = val[arg]
            print(dumps(record_types, sort_keys=True, indent=4))
        except KeyError as exc:
            print(f"Cannot parse {exc}")

    def complete_info_param(self, text, line, begidx, endidx):
        """Completes arg with common record types."""
        # pylint: disable=unused-argument
        mline = line.partition(' ')[2]
        offs = len(mline) - len(text)
        info_record_types = ['description', 'access', 'default', 'bit',
                             'flag', 'max', 'min']
        return [s[offs:] for s in info_record_types if s.startswith(mline)]

    def do_run_script(self, arg):
        """Run a number of commands from a file.

        Example:
            example.txt
            write_and_execute i2c.slave_addr_1 99
            read_reg i2c.slave_addr_1
            (in the cli)
            PHiLIP: run_script example.txt

        Usage:
            run_script <filename>

        Args:
            filename (str): This is the name of the file that contains the
                commands.
        """
        try:
            with open(os.path.join(os.getcwd(), arg), 'r') as fin:
                script = fin.readlines()
                for line in script:
                    self.onecmd(line)
        except (FileNotFoundError) as exc:
            print(exc)

    def complete_run_script(self, text, line, start_idx, end_idx):
        """Autocomplete file search."""
        # pylint: disable=unused-argument
        before_arg = line.rfind(" ", 0, start_idx)
        if before_arg == -1:
            return []

        fixed = line[before_arg+1:start_idx]
        arg = line[before_arg+1:end_idx]
        pattern = arg + '*'

        completions = []
        for path in glob.glob(pattern):
            if path and os.path.isdir(path) and path[-1] != os.sep:
                path += os.sep
            completions.append(path.replace(fixed, "", 1))
        return completions

    def do_exit(self, arg):
        """I mean it should be obvious.

        Usage:
            exit
        """
        # pylint: disable=unused-argument
        return True

    def _print_func_result_success(self, results):
        """Parse and print results."""
        if not isinstance(results, list):
            results = [results]
        result = RESULT_SUCCESS
        printed_something = False
        for res in results:
            if self._data_only:
                if 'result' in res:
                    if res['result'] is RESULT_SUCCESS:
                        if 'data' in res:
                            print(dumps(res['data']))
                            printed_something = True
                    else:
                        result = res['result']
                else:
                    print(dumps(res))
                    printed_something = True
            else:
                print(dumps(res))
                printed_something = True
        if not printed_something:
            print(result)

    def _print_func_result(self, func, arg):
        """Execute function and prints results."""
        value = (arg or '').split(' ')
        func_args = [v for v in value if v]
        try:
            results = func(*func_args)
        except KeyError as exc:
            print(f"Could not parse argument {exc}")
        except (TypeError, ValueError, SyntaxError) as exc:
            print(exc)
        else:
            self._print_func_result_success(results)
