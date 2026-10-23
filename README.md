# I²C API

[![License - MIT](https://img.shields.io/badge/License-MIT-blue)](https://github.com/Brainless-Software/i2c_api/blob/master/LICENSE)
[![PyPI Latest Release](https://img.shields.io/pypi/v/i2c_api.svg)](https://pypi.org/project/i2c_api/)
[![pytest](https://github.com/Brainless-Software/i2c_api/actions/workflows/test.yml/badge.svg)](https://github.com/Brainless-Software/i2c_api/actions/workflows/test.yml)
[![Documentation](https://img.shields.io/badge/docs-latest-brightgreen)](https://brainless-software.github.io/i2c_api/)

Python library that provides abstract classes for [I2C](https://en.wikipedia.org/wiki/I2C) master devices (normally
dongles such as [I2CDriver](https://i2cdriver.com/) and similar) to communicate with I2C slaves.

It is intended to be used together with [i2c_drivers](https://github.com/Brainless-Software/i2c_drivers) library that
implements this API for several common USB-to-I2C dongles.

[Documentation](https://brainless-software.github.io/i2c_api/)

To add this library to your project do

```shell
uv add i2c-api
```

or with `i2c-drivers`

```shell
uv add i2c-api i2c-drivers
```
