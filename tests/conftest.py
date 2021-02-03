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

SLEEP_TIME = 0.1

MM_PATH = str(Path(__file__).parents[0]) + \
          "/../mock_pal/mem_map/example_map_t_0_0_1.csv"

EXT_PORT="/tmp/mm_pal_dev0"

@pytest.fixture(scope="module")
def vpr_inst():
    vpr = VirtualPortRunner()
    yield vpr


@pytest.fixture(scope="function")
def mock_lb(vpr_inst):
    dev = MockDev(port=vpr_inst.mock_port)
    dev.start_thread_loop()
    sleep(SLEEP_TIME)
    yield dev
    dev.end_thread_loop()


@pytest.fixture(scope="function")
def mock_lb_bytes(vpr_inst):
    dev = MockDev(port=vpr_inst.mock_port)
    dev.start_thread_loop(func=dev.run_loopback_bytes)
    sleep(SLEEP_TIME)
    yield dev
    dev.end_thread_loop()


@pytest.fixture(scope="function")
def mock_app_json(vpr_inst):
    dev = MockDev(port=vpr_inst.mock_port)
    dev.start_thread_loop(func=dev.run_app_json)
    sleep(SLEEP_TIME)
    yield dev
    dev.end_thread_loop()


@pytest.fixture(scope="function")
def ser_dri():
    driver = SerialDriver(port=EXT_PORT)
    sleep(SLEEP_TIME)
    yield driver
    driver.close()


@pytest.fixture(scope="function")
def mm_if_inst():
    mmif = MmIf(port=EXT_PORT, mm_path=MM_PATH)
    sleep(SLEEP_TIME)
    yield mmif
    mmif.driver.close()
