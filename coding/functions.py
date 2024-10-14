

def convert_rmb_to_usd_v2(amount_rmb: float) -> float:
    """
    Convert amount from RMB to USD.

    Parameters:
        amount_rmb (float): The amount in RMB to be converted, must be positive.

    Returns:
        float: The converted amount in USD.

    Raises:
        ValueError: If the input RMB amount is not positive.
    """
    # Check if the input amount is positive
    if amount_rmb <= 0:
        raise ValueError("The RMB amount must be positive")

    # Fixed exchange rate
    exchange_rate = 8.0

    # Calculate the converted amount in USD
    amount_usd = amount_rmb / exchange_rate

    return amount_usd


