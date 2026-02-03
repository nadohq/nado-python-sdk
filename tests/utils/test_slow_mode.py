import pytest
from nado_protocol.utils.slow_mode import (
    SlowModeTxType,
    encode_claim_builder_fee_tx,
)


def test_slow_mode_tx_type_constants():
    """Test slow mode transaction type constants."""
    assert SlowModeTxType.CLAIM_BUILDER_FEE == 31


def test_encode_claim_builder_fee_tx_basic():
    """Test basic ClaimBuilderFee encoding."""
    sender = bytes(32)  # 32 zero bytes
    builder_id = 1

    tx = encode_claim_builder_fee_tx(sender, builder_id)

    # Should start with tx type 31 (0x1f)
    assert tx[0] == 31
    # Total length: 1 (tx type) + 32 (sender) + 32 (uint32 padded to 32 bytes)
    assert len(tx) == 65


def test_encode_claim_builder_fee_tx_with_real_sender():
    """Test ClaimBuilderFee encoding with a real sender."""
    # Construct a sender bytes32 (20 bytes address + 12 bytes name)
    address = bytes.fromhex("1234567890abcdef1234567890abcdef12345678")
    name = b"default" + bytes(5)  # "default" is 7 bytes, pad to 12
    sender = address + name

    assert len(sender) == 32

    builder_id = 42
    tx = encode_claim_builder_fee_tx(sender, builder_id)

    # Verify tx type
    assert tx[0] == 31


def test_encode_claim_builder_fee_tx_invalid_sender_length():
    """Test that invalid sender length raises error."""
    with pytest.raises(ValueError, match="sender must be 32 bytes"):
        encode_claim_builder_fee_tx(bytes(31), 1)

    with pytest.raises(ValueError, match="sender must be 32 bytes"):
        encode_claim_builder_fee_tx(bytes(33), 1)

    with pytest.raises(ValueError, match="sender must be 32 bytes"):
        encode_claim_builder_fee_tx(bytes(0), 1)


def test_encode_claim_builder_fee_tx_max_builder_id():
    """Test ClaimBuilderFee with max uint32 builder ID."""
    sender = bytes(32)
    max_builder_id = (1 << 32) - 1  # Max uint32

    tx = encode_claim_builder_fee_tx(sender, max_builder_id)
    assert tx[0] == 31
