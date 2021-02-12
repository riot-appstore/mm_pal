[![ci Actions Status](https://github.com/riot-appstore/mm_pal/workflows/ci/badge.svg)](https://github.com/riot-appstore/mm_pal/actions)

# mm_pal (Memory Map Protocol Abstraction Layer)

Python package for providing an runtime access to embedded devices based
on a memory map type interface.

## Description

This package consists of base classes to build interfaces and a mock
device used for testing and as an example of implementation.

Device connection such as `serial` and parsers such as `json` are used to get
standard output.

## Concept

Embedded devices are generally constrained and communication with
runtime parameters can take up lots of resources. Since many users of
microcontroller are familiar with the concept of a memory map or
register map the [Memory Map
Manager](https://github.com/riot-appstore/memory_map_manager) can be
used as and lightweight way of coordinating a single memory map for
documentation, C structures, and python interface. The `mm_pal` provides
the building blocks for a custom interface. All common functions related
to connecting to the device, parsing output of the registers, and
reading/writing to the registers are handled and only application
specific functionality needs to be implemented. This can make
development easier, especially when the registers are changing
frequently.

## Architecture

```
┏━━━━━━━━━━━┓       ┏━━━━━━━━━┓
┃ developer ┃       ┃ script  ┃
┗━━━━━▲━━━━━┛       ┗━━━━▲━━━━┛
      ┃                  ┃
 ┏━━━━┸━━━━┓       ┏━━━━━┸━━━━━┓
 ┃ my_cli  ◄━━━━━━━┫ my_app_if ┃
 ┗━━━━▲━━━━┛       ┗━━━━━▲━━━━━┛
      ┃    ┌────────┐    ┃
      ┃    │ mm_pal │    ┃
┌─────╂────┴────────┴────╂────────┐
│┏━━━━┸━━━┓          ┏━━━┸━━━┓    │
│┃ mm_cmd ◄━━━━━━━━━━┫ mm_if ┃    │
│┗━━━━━━━━┛          ┗━━━▲━━━┛    │
│                        ┃        │
│                ┏━━━━━━━┸━━━━━━━┓│
│                ┃ serial_driver ┃│
│                ┗━━━━━━━▲━━━━━━━┛│
└────────────────────────╂────────┘
                         ┃
              ┏━━━━━━━━━━▼━━━━━━━━━━┓
              ┃ my_embedded_device  ┃
              ┗━━━━━━━━━━━━━━━━━━━━━┛
```

## Installing package

To install `mm_pal` use pip:

`pip install mm_pal --user`

_Note: only use python 3 which may require pip3_


To install from sources:

`./setup.py install --force --user`


_Note: setuptools package should be installed._

## Using the package

This package is meant to be built upon. An example implementation is done with
the [mock_if](mock_pal/mock_if.py) and the [mock_cli](mock_pal/mock_cli.py).

The mm_cmd is based on the [cmd2](https://github.com/python-cmd2/cmd2) module
is probably worth reading the [documenation](https://cmd2.readthedocs.io/en/latest/).

## Useful commands

To regenerate documentation use:
`sphinx-apidoc -f -o docs/source/ mm_pal mock_pal; make html -C docs/`

## Testing

To test the package with `pytest` must be installed installed and updated.

Using `./setup.py test` or `tox` will perform tests on the
source package.

Special thanks to [riotctrl](https://github.com/RIOT-OS/riotctrl) as it served as a great example.