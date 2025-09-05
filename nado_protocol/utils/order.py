def gen_order_verifying_contract(product_id: int) -> str:
    """
    Generates the order verifying contract address based on the product ID.

    Args:
        product_id (int): The product ID for which to generate the verifying contract address.

    Returns:
        str: The generated order verifying contract address in hexadecimal format.
    """
    be_bytes = product_id.to_bytes(20, byteorder="big", signed=False)
    return "0x" + be_bytes.hex()