# I²C API

Abstract Python classes for [I2C](https://en.wikipedia.org/wiki/I2C) master devices (normally dongles such I2CDriver
etc.) to communicate with I2C slaves.

I2C is a simple 2-wire (SDA and SCL lines) protocol commonly used to communicate with environmental sensors, motor and
pwm controllers and so on. Multiple devices can be connected on the same I2C bus. One of which is a master/controller
device
and others are slave/client devices. Multiple master devices can also be connected on the same bus but managing that
particular use case is outside the scope of this library. Master always is the one who drives the clock line (CLK),
while master and a target slave take turns driving the data (SDA) line. Whichever device drives data line for every
byte sent recipient device sends ACK or NACK bit at the end of each byte. Each exchange is known as transaction.
And each transaction starts with start condition (`S` in official documentation) and ends with stop
condition (`P` in official documentation) driven by the master. From standpoint of
view of the master transaction consist of mixture of one or more of read or write operations (blocks). If a single
transaction has more than one block, blocks are separated by the restart condition (`Sr` in on official documentation).
In [EBNF](https://en.wikipedia.org/wiki/Extended_Backus%E2%80%93Naur_form) notation it can be written like so

```ebnf
S           = start_condition;
Sr          = restart;
P           = stop_condition;
transaction = S block {Sr block} P;
```

Both read and
write ops are initiated by the master. Master writes 7 bits target slave address following by a bit which indicates
that this is a read or write
operation. If operation is "read", then master stops driving the data line and then the target slave drives data line in
response. If master keep driving the clock and does not issue a stop condition slave must keep sending bytes back.
If operation is "write", then master continues driving the data line sending as many bytes as necessary. After
completing read or write part master can issue the stop condition and thus and transaction, or it could issue restart
condition followed by read or write part.

```ebnf
block       = read_block | write_bloc;
read_bit    = 1;
write_bit   = 0;
read_block  = slave_address_7bits read_bit [byte_from_slave];
write_block = slave_address_7bits write_bit {byte_to_slave};
```

Notice, that nowhere above we talked about reading or writing registers.
Common way to define register write is simply to send `write($device_address)` followed by write bit and
then `write($register_address)` and then by `write($register_value)`. Register read operation consist of "write"
part to the device (`write($device_address)`) followed by write bit, then `write($register_addres)` and then
stop followed by a start condition or just a restart condition, then `write($device_address)` followed by a read bit,
then read bytes from the slave device. If, for example register value is 16 bits, then write first byte and then
second byte.

This library provides three forms of communicating to the slave/controller device. Low level, using something called
_I2C
Language_, a more traditional methods `I2CMaster::read(...)` and `I2CMaster::write(...)` and registers read/write
methods. Let's take a look at them in order.

## I2C Language

This API allows one to construct arbitrary I2C transactions in a very intuitive way. It relies on the Python type system
(such as it is) to constrain function calls only to valid set in the valid order. Thus making it impossible to construct
an invalid I2C transaction. Each part of the transaction is a function call which can be chained with a next valid
function call. For example lets create a transaction object to read from slave device at address 0x42 one byte register
with register address 0x7.

```python
from i2c_api import I2CTransactionBuilder

i2c = I2CTransactionBuilder()
read_reg_transaction = i2c.start().address(0x42).write(0x7).restart().address(0x42).read(1).stop()
```

Returned object `read_reg_transaction` is an instance of `I2CTransaction` class. If we print this object it will look
like so:

```text
S().Address(0x42).W().Data(0x07).Sr().Address(0x42).Read(1).P()
```

Where `W()` is an indication of the write bit and `Data(0x07)` is one byte to be sent from the master to the slave
device at `Address(0x42)`. Call `Read(1)` means read one byte from the slave. Valid chain of these
function calls can be represented like so:

![](docs/images/i2c_grammar.png)

This transaction can be executed in two ways with the help of `I2CMaster` class.

```python
from i2c_api import I2CMaster, ExecResults

master = I2CMaster()

results: ExecResults = master.exec(read_reg_transaction)
results: ExecResults = read_reg_transaction.exec(master)
```

Note, that instance of `I2CMaster` is to be obtained from another library where it is implemented for your specific
dongle. For the sake of flow though we simply write above `master = I2CMaster()` even
though that is invalid since `I2CMaster` is an abstract class.

Variable `results` is an instance of `ExecResults` named tuple. Which for the above
example you can access like so:

```python
match results:
    case ExecResults(_, True):
        print(f"Success {results.values()[0]}")

    case ExecResults(_, False):
        print("I2C transaction failed")
```

Calling `results.values()` returns list of `BitArray` where each element corresponds
to each appearance of `read($n_bytes)` call. In the above example we have only one read operation,
hence if `result` is successful, then there is just one element in the `.values()` list.

To write into a register we can construct transaction object like so

```python
from i2c_api import I2CTransactionBuilder

i2c = I2CTransactionBuilder()
write_reg_transaction = i2c.start().address().write([0x7, 0x11]).stop()
```

If we print above transaction we will see

```text
S().Address(auto).W().Data(0x07).Data(0x11).P()
```

Notice that we did not pass slave address in the `address()` function call, hence in string above
it says `Address(auto)`. This allows us to assemble transactions without reference
to a particular slave device address. This means that this address would have to be supplied when
we execute this transaction.

```python
results = write_reg_transaction.exec(master, 0x42)

results = master.exec(write_reg_transaction, 0x42)
```

Address passed to the `exec(...)` function will be applied only to the unfilled `address()` calls.

Write transaction above does not have any read operation, hence we need to check only
if it was a successful or not like so

```python
_, is_success = write_reg_transaction.exec(master, 0x42)

_, is_success = master.exec(write_reg_transaction, 0x42)
```

Transaction object can be serialized to json, saved to some permanent store and then later restored like so:

```python
from i2c_api import I2CTransaction

tr_json_str = I2CTransaction.to_json(write_reg_transaction)
transaction = I2CTransaction.from_json(tr_json_str)
```

## Read/Write ops

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

## Register read/write ops

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
