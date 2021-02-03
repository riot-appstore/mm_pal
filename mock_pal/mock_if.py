# Copyright (c) 2020 HAW Hamburg
# This file is subject to the terms and conditions of the MIT License. See the
# file LICENSE in the top level directory for more details.
# SPDX-License-Identifier:    MIT
"""Mock interface class based on mm_pal.

Mock implementation of interface class. This is an runnable example of how to
implement and mm_pal based interface class.
"""
import logging
from pathlib import Path
from mm_pal import MmIf, import_mm_from_csv


__author__ = "Kevin Weiss"
__email__ = "weiss.kevin604@gmail.com"


class MockIf(MmIf):
    """Interface to a mock memory map.

    Attributes:
        parser (obj): The type of parser to use, defaults to MmJsonParser.
        mem_map (dict): Register memory mapping information.
        if_version (str): Interface version of connected device.
    """

    def __init__(self, *args, **kwargs):
        """Initialize driver and parser to interface to memory map device.

        If a mem_map is not provided, check version and and match the memory
        map provided by the package.

        Args:
            args: Variable arguments to pass to the driver.
            kwargs: Keyword arguments to pass to the driver.

        Note:
            For args and kwargs, check ``MmIf`` for clarification.
        """
        self.logger = logging.getLogger(self.__class__.__name__)

        super().__init__(*args, **kwargs)

        # Sometimes initial version string is correct so try again
        self.if_version = self.get_version(retry=2)

        if self.mem_map is None:
            version_str = self.if_version.replace('.', '_')
            rel_path = f"/mem_map/example_map_t_{version_str}.csv"
            version_path = str(Path(__file__).parents[0]) + rel_path
            self.mem_map = import_mm_from_csv(version_path)

    def special_cmd(self):
        """Use send_and_parse_cmd for special_cmd.

        Returns:
            dict: Parsed command response.

            Example:
            ::

                {
                    'cmd': special_cmd,
                    'result': "Success"
                }
        """
        return self.parser.send_and_parse_cmd("special_cmd")
