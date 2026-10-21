## I2CMaster

* **read (address: int, num_bytes: int = 1) -> Bits | None**

  Performs read transaction reading `num_bytes` (default is 1) from the target device identified by `address`.
  At the end master will issue Stop condition and will release the clock line.
    * Arguments:
        * `address` - i2c address of the target device
        * `num_bytes` - number of bytes to read
    * Returns:
        * None if failed to read data from the client (that is client did not send ACK bits) or data is Bits


* **write (address: int, data: Bits | str | int | list[int], num_bytes: int | None = None) -> bool**

  Performs write transaction sending `data` to the target device identified by `address`. At the end master will
  issue Stop condition and will release the clock line.
    * Arguments:
        * `address` - i2c address of the target device
        * `data` - array of bits to send to the target device; if int or list[int], then these are assumed to be bytes;
          If it is a string, then BitArray is constructed from that string and that is used as a payload
        * `num_bytes` - number of bytes to send or if None, then send all bits in `data` padded with zero bits to fit
          payload into fixed number of bytes. Raises ValueError if num_bytes is not None and is less than data width
    * Returns:
        * _True_ or _False_ indicating if write succeeded, which is that client responded with ACK bits.


* **exec (transaction: I2CTransaction, device_address: int = -1) -> ExecResults**

  Executes I2C commands in a single transaction and returns a named tuple `ExecResults` where first value is list
  of lists of read bytes if any and second value is True or False indicating if transaction completed successfully.
  Unsuccessful completion usual means that slave device responded with NACK at some point during communication
  between master and the slave. Each sub-list within the list corresponds contiguous sequence of read bytes coming
  from the slave.


* **read_register (
    address: int, 
    register: RegisterAddress | int, 
    num_bytes: int = 1, 
    use_restart: bool = True) -> Bits | None**

  Reads register from the target device identified by `address`. This is a compound operation where we
  send first `write(address, register, num_bytes=1)` followed by `read(address, register, num_bytes)`.
  If `use_restart` is True (default), then if device supports it i2c restart will be used between read and write
  operations and if device does not support it them RuntimeError will be raised. if `use_restart` is False, then
  two separate transactions will be used to perform register read operation with clock line being released between
  them.
    * Arguments:
        * `address` - i2c address of the target device
        * `register` - address of the register to read; if int, then it is assumed that register address is one byte
          wide and thus valid value for this field is from 0 to 255.
        * `num_bytes` - number of bytes to read; this should match length of the register
        * `use_restart` - _True_ or _False_ (default) indicating if we should try using I2C restart op between read and
          write operations
    * Returns:
        * _None_ if at any point during these transactions client sends NACK or actual Bits holding response data


* **write_register (address: int, register: RegisterAddress | int, data: Bits | str | int | list[int], num_bytes: int |
  None = None, read_back: bool = False, use_restart: bool = True) -> Bits | None**

  Writes register to the target device. This is basically same as `write(...)` where first write byte is register
  address and subsequent bytes are values to write into a register.
    * Arguments:
        * `address` - i2c address of the target device
        * `register` - address of the register to write to; if int, then it is assumed that register address is one
          byte wide and thus valid value for this field is from 0 to 255.
        * `data` - array of bits to send to the target device; if int or list[int], then these are assumed to be
          bytes. It can be empty list which means that i2c transaction will include only register address/command.
        * `num_bytes` - number of bytes to send or if _None_, then send all bits in `data` padded with zero bits to fit
          payload into fixed number of bytes. Raises `ValueError` if num_bytes is not None and is less than data width.
        * `read_back` - if _True_, then register read operation will be performed at the end and its value returned.
          Otherwise, if _False_ (default), then just do write and return back to the user the same BitArray that was
          supplied to this function as `data`.
        * `use_restart` - _True_ or _False_ (default) indicating if we should try using I2C restart op between write and
          read operations. This value is applicable only of `read_back` is `True`.
    * Returns:
        * Value written into the register or None if NACK was received at any moment from the client device including
          when performing readback or any other reason that i2c driver failed. Which means that write into register
          might be a success but readback fail and thus None be returned.


* **scan () -> list[int]**

  Scans for all client devices connected on this I2C bus.
    * Returns
        * list of addresses of connected devices


* **list_pullups () -> list[str]**

  Returns list of possible configurable pullup resistor values. These should be human-readable values like [20 OHm].


* **set_pullup (pullup_value: str)**

  Set pullup resistor value. This should be one of the strings returned by `list_pullups()` method.


* **get_pullup () -> str**

  Returns currently active pullup resistor value in human-readable format.


* **list_clk_speeds () -> list[int]**

  Returns list of available configurable clock speeds in KHz.


* **get_clk_speed () -> int**

  Returns currently configured clock speed in KHz.


* **set_clk_speed (speed: int)**
  Sets clock speed to `speed` value in KHz. Supplied value must be one of the returned one by
  method `list_clk_speeds()`, if not, then RuntimeError is raised.

## RegisterAddress

Dataclass used as an argument to `I2CMaster.read_register(...)` and `.write_register(...)` methods.

```python
RegisterAddress(address=0x07, bus_width_in_bytes=1)
```

## ExecResults

Named tuple returned when calling `I2CMaster.exec(...)`. It has fields.

* `is_success: bool` - indication if transaction was successefult or not
* `data: list[list[BitArray]]` - data that was read from the slave devices during transaction. This might be a
  non-empty list even if `is_success == False`. The outer list corresponds to each appearance of `read($num_bytes)`
  command in transaction, while the inner list is list of bytes. For example `read(3)` will result in the inner list
  with three elements.

## I2CLogger

Calling `I2CMaster.read(...)`, `.write(...)`, `.read_register(...)` and `.write_register(...)` (but not `.exec(...)`)
will generate log messages dispatched to the logger. Note that these log message might be very inaccurate since many
dongles do not have an ability to return details of failed transaction, such as where exactly in the transaction NACK
happened, just that it happened. These log messages are to be used in the advisory role only.

## I2CMessage

Grouping of all possible elements that will appear in the messages logged by `I2CLogger`. They are:

* START
* STOP
* RESTART
* READ
* WRITE
* ACK
* NACK
* DATA_MOSI
* DATA_MISO
