#!/usr/bin/env python3
# Copyright (c) 2020 HAW Hamburg
#
# This file is subject to the terms and conditions of the MIT License. See the
# file LICENSE in the top level directory for more details.
# SPDX-License-Identifier:    MIT
"""Setup file for mm_pal."""
from setuptools import setup, find_packages

with open("README.md", "r") as fh:
    LONG_DESCRIPTION = fh.read()


setup(
    name="mm_pal",
    version="0.0.0",
    author="Kevin Weiss",
    author_email="weiss.kevin604@gmail.com",
    license="MIT",
    description="Protocol abstraction and parser for embedded devices",
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    url="https://github.com/riot-appstore",
    packages=find_packages(),
    platforms='any',
    python_requires='>=3.6.*',
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers"
    ],
    setup_requires=["pytest-runner"],
    tests_require=["pytest", "jsonschema"],
    install_requires=['pyserial'],
    entry_points={
        'console_scripts': ['start_mock_dev=mock_pal.mock_dev:main',
                            'mm_pal_mock_cli=mock_pal.mock_cli:main']
    }
)
