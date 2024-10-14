

def convert_rmb_to_usd(amount_rmb: float) -> float:
    """
    将金额从人民币转换为美元。

    参数:
        amount_rmb (float): 需要转换的人民币金额，必须为正数。

    返回:
        float: 转换后的美元金额。

    抛出:
        ValueError: 如果输入的人民币金额不是正数。
    """
    # 检查输入金额是否为正数
    if amount_rmb <= 0:
        raise ValueError("人民币金额必须为正数")

    # 固定汇率
    exchange_rate = 8.0

    # 计算转换后的美元金额
    amount_usd = amount_rmb / exchange_rate

    return amount_usd


