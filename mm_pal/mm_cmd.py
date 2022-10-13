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
import argparse
import logging
import os
from pprint import pformat
from typing import List
from cmd2 import Cmd, with_argparser, Settable


def add_timeout_retry_arguments(arg_parser):
    """Add common arguments to arg parser."""
    arg_parser.add_argument('--timeout', '-t', type=float,
                            help="Time to wait for device to respond (sec)")
    arg_parser.add_argument('--retry', '-r', type=int,
                            help="Amount of times to retry the command")


class MmCmd(Cmd):
    """Cmd wrapper for mm_pal based devices.

    Contains common commands to build a cli interface.

    Attributes:
        dev_driver (obj): The device driver used to communicate with the
            device.
    """

    def __init__(self, dev_driver, *args, **kwargs):
        """Instantiate cmd based cli class.

        Args:
            dev_driver (obj): The device driver used to communicate with the
                device.
            persistent_history_file (str): Path to history file,
                defaults to ~/.mm_history.
        """
        self.logger = self.logger = logging.getLogger(self.__class__.__name__)
        self.dev_driver = dev_driver
        phf = 'persistent_history_file'
        kwargs[phf] = kwargs.pop(phf, os.path.join(os.path.expanduser("~"),
                                                   ".mm_history"))
        super().__init__(allow_cli_args=False, *args, **kwargs)
        self.loglevel = logging.getLevelName(logging.root.level)
        settable = Settable('loglevel', str, 'Logging Level', self,
                            choices=['NOTSET', 'DEBUG', 'INFO',
                                     'WARNING', 'ERROR', 'CRITICAL'],
                            onchange_cb=self._onchange_loglevel)
        self.add_settable(settable)

    def regs_choices_method(self) -> List[str]:
        """Return a list of valid register names."""
        return list(self.dev_driver.mem_map.keys())

    def param_choices_method(self) -> List[str]:
        """Return a list of parameters of memory map."""
        first_reg = list(self.dev_driver.mem_map.keys())[0]
        return list(self.dev_driver.mem_map[first_reg].keys())

    read_reg_parser = argparse.ArgumentParser()
    read_reg_parser.add_argument('reg', choices_provider=regs_choices_method,
                                 help="name of the register to read")
    read_reg_parser.add_argument('--offset', '-o', type=int, default=0,
                                 help="offset of the array")
    read_reg_parser.add_argument('--size', '-s', type=int,
                                 help="number of elements to read in array")
    add_timeout_retry_arguments(read_reg_parser)

    @with_argparser(read_reg_parser)
    def do_read_reg(self, opts):
        """Read a register defined by the memory map."""
        resp = self.dev_driver.read_reg(opts.reg,
                                        offset=opts.offset,
                                        size=opts.size,
                                        timeout=opts.timeout,
                                        retry=opts.retry)
        self.poutput(resp)

    write_reg_parser = argparse.ArgumentParser()
    write_reg_parser.add_argument('reg', choices_provider=regs_choices_method,
                                  help="name of the register to read")
    write_reg_parser.add_argument('data', nargs="+",
                                  help="Data to write")
    write_reg_parser.add_argument('--offset', '-o', type=int, default=0,
                                  help="offset of the array")
    write_reg_parser.add_argument('--verify', '-v', action="store_true",
                                  help="Verify the data was written")
    add_timeout_retry_arguments(write_reg_parser)

    @with_argparser(write_reg_parser)
    def do_write_reg(self, opts):
        """Write a register defined by the memory map."""
        self.dev_driver.write_reg(opts.reg, opts.data,
                                  offset=opts.offset,
                                  verify=opts.verify,
                                  timeout=opts.timeout,
                                  retry=opts.retry)
        self.poutput("Success")

    commit_write_parser = argparse.ArgumentParser()
    commit_write_parser.add_argument('reg',
                                     choices_provider=regs_choices_method,
                                     help="name of the register to read")
    commit_write_parser.add_argument('data', nargs="+",
                                     help="Data to write")
    commit_write_parser.add_argument('--offset', '-o', type=int, default=0,
                                     help="offset of the array")
    commit_write_parser.add_argument('--verify', '-v', action="store_true",
                                     help="Verify the data was written")
    add_timeout_retry_arguments(commit_write_parser)

    @with_argparser(commit_write_parser)
    def do_commit_write(self, opts):
        """Write a register defined by the memory map."""
        self.dev_driver.commit_write(opts.reg, opts.data,
                                     offset=opts.offset,
                                     verify=opts.verify,
                                     timeout=opts.timeout,
                                     retry=opts.retry)
        self.poutput("Success")

    read_struct_parser = argparse.ArgumentParser()
    read_struct_parser.add_argument('struct', default='.', nargs='?',
                                    choices_provider=regs_choices_method,
                                    help="Name of the struct to read"
                                    ", use \".\" for all")
    read_struct_parser.add_argument('--data_only', '-d',
                                    action="store_false",
                                    help="Show only the data without reg name")
    read_struct_parser.add_argument('--compact', '-c',
                                    action="store_true",
                                    help="Output is compact")
    add_timeout_retry_arguments(read_struct_parser)

    @with_argparser(read_struct_parser)
    def do_read_struct(self, opts):
        """Read a set of registers defined by the memory map."""
        resp = self.dev_driver.read_struct(opts.struct,
                                           data_has_name=opts.data_only,
                                           timeout=opts.timeout,
                                           retry=opts.retry)
        self.poutput(pformat(resp, compact=opts.compact))

    commit_parser = argparse.ArgumentParser()
    add_timeout_retry_arguments(commit_parser)

    @with_argparser(commit_parser)
    def do_commit(self, opts):
        """Execute/commit device configuration changes."""
        self.dev_driver.commit(timeout=opts.timeout, retry=opts.retry)
        self.poutput("Success")

    soft_reset_parser = argparse.ArgumentParser()
    add_timeout_retry_arguments(soft_reset_parser)

    @with_argparser(soft_reset_parser)
    def do_soft_reset(self, opts):
        """Send reset signal to the device."""
        self.dev_driver.soft_reset(timeout=opts.timeout, retry=opts.retry)
        self.poutput("Success")

    version_parser = argparse.ArgumentParser()
    add_timeout_retry_arguments(version_parser)

    @with_argparser(version_parser)
    def do_get_version(self, opts):
        """Get the version of the interface from the device."""
        # pylint: disable=unused-argument
        version = self.dev_driver.get_version(timeout=opts.timeout,
                                              retry=opts.retry)

        self.poutput(f'Interface version: {version}')

    info_reg_parser = argparse.ArgumentParser()
    info_reg_parser.add_argument('reg', choices_provider=regs_choices_method,
                                 nargs=(0, 1),
                                 help="name of the register to read")

    @with_argparser(info_reg_parser)
    def do_info_reg(self, opts):
        """Print all information of a register or all registers.

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
        if opts.reg:
            self.poutput(pformat(self.dev_driver.mem_map[opts.reg]))
        else:
            self.poutput(pformat(self.dev_driver.mem_map))

    info_param_parser = argparse.ArgumentParser()
    info_param_parser.add_argument('param',
                                   choices_provider=param_choices_method,
                                   help="name of the register to read")

    @with_argparser(info_param_parser)
    def do_info_param(self, opts):
        """Print selected parameter of all registers."""
        record_types = {}
        for key, val in self.dev_driver.mem_map.items():
            if opts.param in val:
                record_types[key] = val[opts.param]
        self.poutput(pformat(record_types))

    # pylint: disable=unused-argument
    def _onchange_loglevel(self, param_name, old, new):
        self.loglevel = logging.getLevelName(new)
        logging.getLogger().setLevel(self.loglevel)
