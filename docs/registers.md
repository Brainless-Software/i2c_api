## Register access

To farther simplify interation with devices that have concepts of registers as described above

```python
i2c_master = I2CMaster()
reg_data: Bits | None = i2c_master.read_register(
    0x42, RegisterAddress(address=0x07, bus_width_in_bytes=1)
)
```

Above will read one byte from the register whose address is one byte long 0x07 or return None
if transaction fails for any reason.

There is a shortcut for the above though. If register address is one byte wide, then you
simply pass register address as an int.

```python
i2c_master.read_register(0x42, register=0x07)
```

This will raise `ValueError` if register address is outside of range from 0 to 255.

If register holds let say 4 bytes, then you can read it like so

```python
reg_data: Bits | None = i2c_master.read_register(
    0x42, RegisterAddress(address=0x07, bus_width_in_bytes=1), num_bytes=4
)
```

Writing register has a bit more moving parts. For example write 0x11 into register 0x07 on device at address 0x42

```python
i2c_master = I2CMaster()
data: Bits | None = i2c_master.write_register(0x42, register=0x7, data=0x11)
```

It returns data that was written into a device (in this case 0x11) or None if transaction failed for any reason.
Like with `read_register(...)` register address can be an int for one byte wide address or an instance
of `RegisterAddress`. Like with `write(...)` function above, `data` can be an int for one byte, array of ints one
for each byte or a string representing bit array and optional argument `num_bytes` will pad it the specific number of
bytes or if not provided to the nearest number of bytes to fit payload in.

To confirm that data was acutally written you can set `read_back=True` (default is False).

```python
data = i2c_master.write_register(0x42, register=0x7, data=0x11, read_back=True)
```

This will write register and will then read it back. Normally these two operations, 
register write and then read will be in two separate transaction as not every dongle supports
restart between write and read op. If you dongle does support it though you can 
indicate that you want to use restart and do everything that this function does in
one single transaction by setting `use_restart=True`.
