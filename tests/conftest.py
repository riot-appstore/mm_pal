# Copyright (c) 2020 HAW Hamburg
#
# This file is subject to the terms and conditions of the MIT License. See the
# file LICENSE in the top level directory for more details.
# SPDX-License-Identifier:    MIT
"""Pytest configuration.

Declares fixtures and common functions.
"""
from time import sleep
from pathlib import Path
import pytest
from mock_pal import MockDev, VirtualPortRunner
from mm_pal.serial_driver import SerialDriver
from mm_pal import MmIf


MM_PATH = str(Path(__file__).parents[0]) + \
          "/../mock_pal/mem_map/example_map_t_0_0_0.csv"

def sleep_before_serial_action():
    """Needed since some slower computers error."""
    sleep(0.3)


@pytest.fixture(scope="module")
def vpr_inst():
    vpr = VirtualPortRunner()
    yield vpr


@pytest.fixture(scope="function")
def mock_lb(vpr_inst):
    dev = MockDev(port=vpr_inst.mock_port)
    dev.start_thread_loop()
    sleep_before_serial_action()
    yield dev
    dev.end_thread_loop()


@pytest.fixture(scope="function")
def mock_lb_bytes(vpr_inst):
    dev = MockDev(port=vpr_inst.mock_port)
    dev.start_thread_loop(func=dev.run_loopback_bytes)
    sleep_before_serial_action()
    yield dev
    dev.end_thread_loop()


@pytest.fixture(scope="function")
def mock_app_json(vpr_inst):
    dev = MockDev(port=vpr_inst.mock_port)
    dev.start_thread_loop(func=dev.run_app_json)
    sleep_before_serial_action()
    yield dev
    dev.end_thread_loop()


@pytest.fixture(scope="function")
def ser_dri(vpr_inst):
    driver = SerialDriver(port=vpr_inst.ext_port)
    sleep_before_serial_action()
    yield driver
    driver.close()


@pytest.fixture(scope="function")
def mm_if_inst(vpr_inst):
    mmif = MmIf(port=vpr_inst.ext_port, mm_path=MM_PATH)
    sleep_before_serial_action()
    yield mmif
    mmif.driver.close()