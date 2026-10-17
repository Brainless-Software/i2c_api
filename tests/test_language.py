from i2c_api import I2CTransaction, I2CTransactionBuilder


def test_language_serialization():
    i2c = I2CTransactionBuilder()
    tr1 = i2c.start().address().write([0x7, 0x11]).restart().address(0x44).read(2).stop()
    assert str(tr1) == "S().Address(auto).W().Data(0x07).Data(0x11).Sr().Address(0x44).Read(2).P()"
    json = I2CTransaction.to_json(tr1)
    tr2 = I2CTransaction.from_json(json)
    assert str(tr1) == str(tr2)

    tr1 = i2c.start().address().write(0x7).stop()
    assert str(tr1) == "S().Address(auto).W().Data(0x07).P()"
    json = I2CTransaction.to_json(tr1)
    tr2 = I2CTransaction.from_json(json)
    assert str(tr1) == str(tr2)
