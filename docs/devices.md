Following devices (usb-to-i2c bridges) are supported by [_i2c_drivers_](https://github.com/Brainless-Software/i2c_drivers) library which implements this API.

* [I2CDriver](https://i2cdriver.com/)
* [MCP2221](https://www.adafruit.com/product/4471) (official chip link is [here](https://www.microchip.com/en-us/product/mcp2221))
* [FT232H](https://www.adafruit.com/product/2264)

To add these to your project do

```shell
uv add i2c_api i2c_drivers
uv sync
```