from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import reduce

from bitstring import BitArray, Bits

from i2c_api.commands import Address, P
from i2c_api.exec_results import ExecResults
from i2c_api.language import I2CTransaction, I2CTransactionBuilder
from i2c_api.log import I2CMessage, I2CTransactionElement
from i2c_api.logger import I2CLogger


class DummyI2CLogger(I2CLogger):
    def log_message(self, message: list[I2CTransactionElement]):
        pass


@dataclass(frozen=True, slots=True)
class RegisterAddress:
    address: int
    bus_width_in_bytes: int

    def __post_init__(self):
        if self.address < 0 or self.address > (pow(2, self.bus_width_in_bytes * 8) - 1):
            raise ValueError(f"Register address 0x{self.address:02X} is outside of valid range")


class I2CMaster(ABC):
    def __init__(self, logger: I2CLogger | None = None):
        self.__logger: I2CLogger = DummyI2CLogger() if logger is None else logger

    @staticmethod
    def __pad_up_to_bytes(data: BitArray, num_bytes: int | None) -> BitArray:
        if num_bytes is None:
            if data.len % 8 != 0:
                data.prepend(BitArray(8 - data.len % 8))
            return data
        elif data.len <= num_bytes * 8:
            data.prepend(BitArray(num_bytes * 8 - data.len))
            return data
        else:
            raise ValueError(f"Input bit array is larger then pad_up_to_num_bytes={num_bytes}")

    @staticmethod
    def mk_payload(data: Bits | str | int | list[int], pad_up_to_num_bytes: int | None = None) -> BitArray:
        """
        Creates BitArray to be used as a payload in i2c write operations from `data` argument.
        If `pad_up_to_num_bytes` is None, then returned value will be padded to the next nearest number of bytes to
        ensure that returned value is integer multiple of 8 bits.

        If data is str then pass, then construct BitArray(data). For example, you can pass "`0b10010`" as a string.
        If data is Bits, then simply wrap it in BitArray.
        If data is int, then it is interpreted as unsigned value of one byte
        if data is list[int], then that is assumed to be a list of bytes.
        """
        if isinstance(data, int):
            return I2CMaster.__pad_up_to_bytes(BitArray(f"uint:8={data}"), pad_up_to_num_bytes)
        elif isinstance(data, list):
            return I2CMaster.__pad_up_to_bytes(BitArray("".join([f"uint:8={a}," for a in data])), pad_up_to_num_bytes)
        elif isinstance(data, (str, Bits)):
            return I2CMaster.__pad_up_to_bytes(BitArray(data), pad_up_to_num_bytes)
        else:
            raise TypeError("Invalid payload type")

    def logger(self) -> I2CLogger:
        return self.__logger

    def write(
        self,
        address: int,
        data: Bits | str | int | list[int],
        num_bytes: int | None = None,
    ) -> bool:
        """
        Performs write transaction sending `data` to the target device identified by `address`. At the end master will
        issue Stop condition and will release the clock line.

        :param address: i2c address of the target device
        :param data: array of bits to send to the target device; if int or list[int], then these are assumed to be bytes;
            If it is a string, then BitArray is constructed from that string and that is used as a payload.
        :param num_bytes: number of bytes to send or if None, then send all bits in `data` padded with zero bits to fit
            payload into fixed number of bytes. Raises ValueError if num_bytes is not None and is less than data width.
        :return: True or False indicating if write succeeded, which is that client responded with ACK bits.
        """
        log_message = [I2CMessage.START, I2CMessage.DATA_MOSI(BitArray(f"uint:7={address}")), I2CMessage.WRITE]
        data_out: list[Bits] = [BitArray(f"uint:8={x}") for x in I2CMaster.mk_payload(data, num_bytes).tobytes()]
        try:
            data, is_success = (
                I2CTransactionBuilder().start().address(address).write([b.uint for b in data_out]).stop().exec(self)
            )
            if is_success:
                log_message.append(I2CMessage.ACK)
                for b in data_out:
                    log_message.extend([I2CMessage.DATA_MOSI(b), I2CMessage.ACK])
            else:
                log_message.append(I2CMessage.NACK)
            return is_success
        finally:
            log_message.append(I2CMessage.STOP)
            self.logger().log_message(log_message)

    def read(self, address: int, num_bytes: int = 1) -> Bits | None:
        """
        Performs read transaction reading `num_bytes` (default is 1) from the target device identified by `address`.
        At the end master will issue Stop condition and will release the clock line.

        :param address: i2c address of the target device
        :param num_bytes: number of bytes to read
        :return: None if failed to read data from the client (that is client did not send ACK bits) or data is Bits
        """
        log_message = [I2CMessage.START, I2CMessage.DATA_MOSI(BitArray(f"uint:7={address}")), I2CMessage.READ]
        try:
            data, is_success = I2CTransactionBuilder().start().address(address).read(num_bytes).stop().exec(self)
            if is_success:
                log_message.append(I2CMessage.ACK)
                for b in data[0]:
                    log_message.extend([I2CMessage.DATA_MISO(b), I2CMessage.ACK])
                return reduce(lambda acc, b: acc + b, data[0], BitArray())
            else:
                log_message.append(I2CMessage.NACK)
                return None
        finally:
            log_message.append(I2CMessage.STOP)
            self.logger().log_message(log_message)

    def exec(self, transaction: I2CTransaction, device_address: int = -1) -> ExecResults:
        """
        Executes I2C commands in a single transaction and returns a named tuple `ExecResults` where first value is list
        of lists of read bytes if any and second value is True or False indicating if transaction completed successfully.
        Unsuccessful completion usual means that slave device responded with NACK at some point during communication
        between master and the slave. Each sub-list within the list corresponds contiguous sequence of read bytes coming
        from the slave.
        """
        if not isinstance(transaction, I2CTransaction):
            raise ValueError("transaction argument must be instance of I2CTransaction")
        elif transaction._i2c._i2c_commands == [] or not isinstance(transaction._i2c._i2c_commands[-1], P):
            raise ValueError("Unable to execute incomplete transaction")
        elif device_address == -1:
            for c in transaction._i2c._i2c_commands:
                if isinstance(c, Address) and c.address == -1:
                    raise ValueError(
                        "Some Address(...) commands are given without the address. "
                        "Thus, argument `address` must be provided."
                    )
        return self._exec(transaction, device_address)

    @abstractmethod
    def _exec(self, transaction: I2CTransaction, device_address: int = -1) -> ExecResults:
        pass

    def read_register(
        self,
        address: int,
        register: RegisterAddress | int,
        num_bytes: int = 1,
        use_restart: bool = True,
    ) -> Bits | None:
        """
        Reads register from the target device identified by `address`. This is a compound operation where we
        send first `write(address, register, num_bytes=1)` followed by `read(address, register, num_bytes)`.
        If `use_restart` is True (default), then if device supports it i2c restart will be used between read and write
        operations and if device does not support it them RuntimeError will be raised. if `use_restart` is False, then
        two separate transactions will be used to perform register read operation with clock line being released between
        them.

        :param address: i2c address of the target device
        :param register: address of the register to read; if int, then it is assumed that register address is one
            byte wide and thus valid value for this field is from 0 to 255.
        :param num_bytes: number of bytes to read; this should match length of the register
        :param use_restart: True or False (default) indicating if we should try using I2C restart op between read and
            write operations
        :return: None if at any point during these transactions client sends NACK or actual Bits holding response data
        """
        register_addr: RegisterAddress = (
            RegisterAddress(address=register, bus_width_in_bytes=1) if isinstance(register, int) else register
        )
        register_address_bitarray: BitArray = I2CMaster.mk_payload(
            BitArray(f"uint:{8 * register_addr.bus_width_in_bytes}={register_addr.address}"),
            register_addr.bus_width_in_bytes,
        )
        reg_addr_out = [BitArray(f"uint:8={x}") for x in register_address_bitarray.tobytes()]

        if not use_restart:
            if self.write(address, register_address_bitarray):
                return self.read(address, num_bytes)
            else:
                return None
        else:
            addr_log_message = I2CMessage.DATA_MOSI(BitArray(f"uint:7={address}"))
            log_message = [I2CMessage.START, addr_log_message, I2CMessage.WRITE]
            try:
                data, is_success = (
                    I2CTransactionBuilder()
                    .start()
                    .address(address)
                    .write([b.uint for b in reg_addr_out])
                    .restart()
                    .address(address)
                    .read(num_bytes)
                    .stop()
                    .exec(self)
                )
                if is_success:
                    log_message.append(I2CMessage.ACK)
                    for b in reg_addr_out:
                        log_message.extend([I2CMessage.DATA_MOSI(b), I2CMessage.ACK])
                    log_message.extend([I2CMessage.RESTART, addr_log_message, I2CMessage.READ, I2CMessage.ACK])
                    for b in data[0]:
                        log_message.extend([I2CMessage.DATA_MISO(b), I2CMessage.ACK])
                    return reduce(lambda acc, b: acc + b, data[0], BitArray())
                else:
                    log_message.append(I2CMessage.NACK)
                    return None
            finally:
                log_message.append(I2CMessage.STOP)
                self.logger().log_message(log_message)

    def write_register(
        self,
        address: int,
        register: RegisterAddress | int,
        data: Bits | str | int | list[int],
        num_bytes: int | None = None,
        read_back: bool = False,
        use_restart: bool = True,
    ) -> Bits | None:
        """
        Writes register to the target device. This is basically same as `write(...)` where first write byte is register
        address and subsequent bytes are values to write into a register.

        :param address: i2c address of the target device
        :param register: address of the register to write to; if int, then it is assumed that register address is one
            byte wide and thus valid value for this field is from 0 to 255.
        :param data: array of bits to send to the target device; if int or list[int], then these are assumed to be
            bytes. It can be empty list which means that i2c transaction will include only register address/command.
        :param num_bytes: number of bytes to send or if None, then send all bits in `data` padded with zero bits to fit
            payload into fixed number of bytes. Raises ValueError if num_bytes is not None and is less than data width.
        :param read_back: if True, then register read operation will be performed at the end and its value returned.
            Otherwise, if False (default), then just do write and return back to the user the same BitArray that was
            supplied to this function as `data`.
        :param use_restart: True or False (default) indicating if we should try using I2C restart op between write and
            read operations. This value is applicable only of `read_back` is `True`.
        :return: Value written into the register or None if NACK was received at any moment from the client device
            including when performing readback or any other reason that i2c driver failed. Which means that write into
            register might be a success but readback fail and thus None be returned.
        """
        register_addr: RegisterAddress = (
            RegisterAddress(address=register, bus_width_in_bytes=1) if isinstance(register, int) else register
        )

        register_value = I2CMaster.mk_payload(data, num_bytes)
        write_data = BitArray(f"uint:{8 * register_addr.bus_width_in_bytes}={register_addr.address}") + register_value
        if not self.write(address, write_data):
            return None
        elif read_back:
            return self.read_register(address, register_addr, len(register_value.tobytes()), use_restart=use_restart)
        else:
            return register_value

    @abstractmethod
    def scan(self) -> list[int]:
        """
        Scans for all client devices connected on this I2C bus.

        :return: list of addresses of connected devices
        """

    @abstractmethod
    def list_pullups(self) -> list[str]:
        """
        Returns list of possible configurable pullup resistor values.
        These should be human-readable values like [20 OHm]
        """

    @abstractmethod
    def set_pullup(self, pullup_value: str) -> None:
        """
        Set pullup resistor value. This should be one of the strings returned by `list_pullups()` method.
        """

    @abstractmethod
    def get_pullup(self) -> str:
        """
        Returns currently active pullup resistor value in human-readable format.
        """

    @abstractmethod
    def list_clk_speeds(self) -> list[int]:
        """Returns list of available configuable clock speeds in KHz."""

    @abstractmethod
    def get_clk_speed(self) -> int:
        """Returns currently configued clock speed in KHz."""

    @abstractmethod
    def set_clk_speed(self, speed: int) -> None:
        """
        Sets clock speed to `speed` value in KHz. Supplied value must be one of the returned one by
        method `list_clk_speeds()`, if not, then RuntimeError is raised.
        """

    @abstractmethod
    def close(self):
        """
        Some dongles require to close instance of I2CMaster. Thus make sure to call it.
        """

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
