# I²C API

Abstract Python classes for [I2C](https://en.wikipedia.org/wiki/I2C) master devices (normally dongles such I2CDriver etc.) to communicate with I2C slaves.

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
though that is an invalid since `I2CMaster` is an abstract class.

Variable `results` is an instance `ExecResults` named tuple. Which for the above 
example you can access like so:

```python
match results:
    case ExecResults(_, True):
        print(f"Success {results.values()[0]}")
        
    case ExecResults(_, False):
        print("I2C transaction failed")
```

Calling `results.values()` returns list of `BitArray` where each element corresponds 
to each appearance of `read($n_bytes)` call. In the above example we only one read operation, 
hence if `result` is successful, then there is one element in the `.values()` list.

To write in register we can construct transcation object like so

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
it says `Address(auto)`. This allows us to assemble transaction without reference 
to a particular slave device address. This means that this address would have to be supplied when 
we execute this transaction.

```python
results = write_reg_transaction.exec(master, 0x42)

results = master.exec(write_reg_transaction, 0x42)
```
Write transaction above does not have any read operation, hence we need to check only 
if it was a success or not like so

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

## Register read/write ops