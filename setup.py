#!/usr/bin/env python3
# Copyright (c) 2020 HAW Hamburg
#
# This file is subject to the terms and conditions of the MIT License. See the
# file LICENSE in the top level directory for more details.
# SPDX-License-Identifier:    MIT
"""Setup file for mm_pal."""
import os
from setuptools import setup, find_packages

PACKAGE = 'mm_pal'

with open("README.md", "r", encoding="utf8") as fh:
    LONG_DESCRIPTION = fh.read()


def get_version(package):
    """ Extract package version without importing file
    Importing cause issues with coverage,
        (modules can be removed from sys.modules to prevent this)
    Importing __init__.py triggers importing rest and then requests too
    Inspired from pep8 setup.py
    """
    with open(os.path.join(package, '__init__.py')) as init_fd:
        for line in init_fd:
            if line.startswith('__version__'):
                return eval(line.split('=')[-1])
    return None


setup(
    name=PACKAGE,
    version=get_version(PACKAGE),
    author="Kevin Weiss",
    author_email="weiss.kevin604@gmail.com",
    license="MIT",
    description="Protocol abstraction and parser for embedded devices",
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    url="https://github.com/riot-appstore",
    packages=find_packages(),
    platforms='any',
    python_requires='>=3.7.*',
    include_package_data=True,
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 3 - Alpha",
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        "Intended Audience :: Developers"
    ],
    setup_requires=["pytest-runner"],
    tests_require=["pytest", "pytest-cov", "pytest-regtest"],
    install_requires=['pyserial', 'cmd2>=2'],
    entry_points={
        'console_scripts': ['start_mock_dev=mock_pal.mock_dev:main',
                            'mm_pal_mock_cli=mock_pal.mock_cli:main']
    }
)
