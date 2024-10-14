def convert_rmb_to_usd(amount_rmb: float) -> float:
    """
    将金额从人民币转换为美元。

    参数:
        amount_rmb (float): 需要转换的人民币金额，必须为正数。

    返回:
        float: 转换后的美元金额。
    """
    if amount_rmb <= 0:
        raise ValueError("人民币金额必须为正数")
    # 假设当前兑换汇率为1人民币 = 0.15美元
    exchange_rate = 0.15
    return amount_rmb * exchange_rate

# 将10元人民币兑换成美元
amount_rmb = 10.0
amount_usd = convert_rmb_to_usd(amount_rmb)

print(f"{amount_rmb} 元人民币兑换成美元是: {amount_usd} 美元")