# Copyright (c) 2020 HAW Hamburg
#
# This file is subject to the terms and conditions of the MIT License. See the
# file LICENSE in the top level directory for more details.
# SPDX-License-Identifier:    MIT
"""Simple helpers that can be useful with mm_pal."""
import serial.tools.list_ports


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
