To hide details I2C protocol you can use methods `read($device_address, $num_bytes)` and
`write($device_address, $data, ...)` present in the `I2CMaster` class. These methods encapsulate the whole transaction,
that is communications starts with start condition and ends with the stop.

```python
from bitstring import Bits

i2c_master = I2CMaster()
data: Bits | None = i2c_master.read(address=0x42, num_bytes=2)
if data is None:
    print("Error")
else:
    print(data)
```

If transaction fails for any reason it return `None`. Otherwise, it returns
[_Bits_](https://bitstring.readthedocs.io/en/stable/bits.html#bits) class from the
[bitstring](https://bitstring.readthedocs.io/en/stable/index.html) library.

Method `write(...)` returns boolean indicating success or failure of the write operation
and it accepts data to be sent in several different forms.

```python
i2c_master = I2CMaster()
is_success: bool = i2c_master.write(0x42, data=0x10)
```

It is an int, then it will send one byte encoded in that int value. If it is an array of integers,
that is understood as array of bytes. Naturally each int has to be a range from 0 to 255 or ValueError
is raised.

```python
is_success: bool = i2c_master.write(0x42, data=[0x07, 0x10])
```

If `data` is a string, then it has to be a string representation of bit or byte array.
For example `write(0x42, data=0x07)` can be written like so

```python
i2c_master.write(0x42, data="0b111")
```

Note that `0b111` is only 3 bits wide. This payload by default will be padded with zeroes to nearest whole number of
bytes. Thus, above will become `0b00000111`. If you want to be padded to a greater number of bytes, let say 2 in
this example

```python
i2c_master.write(0x42, data="0b111", num_bytes=2)
```

This will send two bytes to the slave device `0b0000000000000111` (or `0x0007`).
