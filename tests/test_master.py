import pytest
from bitstring import BitArray, Bits

from i2c_api import I2CMaster, RegisterAddress


def test_mk_payload_int():
    # single int as argument creates BitArray of one byte length and valid values for int are from 0 to 255 inclusive.
    assert I2CMaster.mk_payload(0) == BitArray("uint:8=0")
    assert I2CMaster.mk_payload(7) == BitArray("uint:8=7")
    assert I2CMaster.mk_payload(255) == BitArray("uint:8=255")

    # value of 300 does not fit into one byte
    with pytest.raises(ValueError):
        I2CMaster.mk_payload(300)

    with pytest.raises(ValueError):
        I2CMaster.mk_payload(-1)

    assert I2CMaster.mk_payload(250, pad_up_to_num_bytes=5) == BitArray("uint:40=250")

    # does not matter how much we pad this, value of 300 does not fit into one byte.
    with pytest.raises(ValueError):
        I2CMaster.mk_payload(300, pad_up_to_num_bytes=5)


def test_mk_payload_list():
    assert I2CMaster.mk_payload([7]) == BitArray("uint:8=7")
    assert I2CMaster.mk_payload([7, 10]) == BitArray("uint:16=1802")

    with pytest.raises(ValueError):
        I2CMaster.mk_payload([700, 2])

    assert I2CMaster.mk_payload([7, 10], pad_up_to_num_bytes=3) == BitArray("uint:24=1802")

    with pytest.raises(ValueError):
        I2CMaster.mk_payload([7, 10], pad_up_to_num_bytes=1)

    assert I2CMaster.mk_payload([]) == BitArray("")
    assert I2CMaster.mk_payload([], pad_up_to_num_bytes=0) == BitArray("")
    assert I2CMaster.mk_payload([], pad_up_to_num_bytes=1) == BitArray("0x00")


def test_mk_payload_str():
    assert I2CMaster.mk_payload("0b00000010") == BitArray("uint:8=2")
    assert I2CMaster.mk_payload("0b000000010") == BitArray("uint:16=2")
    assert I2CMaster.mk_payload("0b000000010", pad_up_to_num_bytes=4) == BitArray("uint:32=2")


def test_mk_payload_bits():
    assert I2CMaster.mk_payload(Bits("0x02")) == BitArray("uint:8=2")
    assert I2CMaster.mk_payload(Bits("0x02"), pad_up_to_num_bytes=2) == BitArray("uint:16=2")

    assert I2CMaster.mk_payload(Bits("0x002")) == BitArray("uint:16=2")

    with pytest.raises(ValueError):
        I2CMaster.mk_payload(Bits("0x002"), pad_up_to_num_bytes=1)


def test_register_address():
    assert RegisterAddress(0x07, 1).address == 7
    with pytest.raises(ValueError):
        RegisterAddress(0xABC, 1)
