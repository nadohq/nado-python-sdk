"""
Utilities for encoding slow mode transactions for on-chain submission.

Slow mode transactions are submitted directly to the Endpoint contract
via `submitSlowModeTransaction(bytes)`.
"""

from eth_abi import encode


# Slow mode transaction type constants
class SlowModeTxType:
    CLAIM_BUILDER_FEE = 31


def encode_claim_builder_fee_tx(sender: bytes, builder_id: int) -> bytes:
    """
    Encodes a ClaimBuilderFee slow mode transaction.

    This transaction is submitted on-chain via `endpoint.submitSlowModeTransaction(bytes)`.

    Args:
        sender: The subaccount bytes32 that will receive the claimed fees.
        builder_id: The builder ID to claim fees for.

    Returns:
        bytes: The encoded transaction ready for submission.

    Example:
        ```python
        from nado_protocol.utils.slow_mode import encode_claim_builder_fee_tx
        from nado_protocol.utils.bytes32 import subaccount_to_bytes32

        sender = subaccount_to_bytes32({"subaccount_owner": "0x...", "subaccount_name": "default"})
        tx_bytes = encode_claim_builder_fee_tx(sender, builder_id=1)

        # Submit via endpoint contract
        endpoint.functions.submitSlowModeTransaction(tx_bytes).transact()
        ```
    """
    if len(sender) != 32:
        raise ValueError("sender must be 32 bytes")

    # Encode the parameters: (bytes32 sender, uint32 builderId)
    tx_bytes = encode(["bytes32", "uint32"], [sender, builder_id])

    # Prepend the transaction type byte
    return bytes([SlowModeTxType.CLAIM_BUILDER_FEE]) + tx_bytes
