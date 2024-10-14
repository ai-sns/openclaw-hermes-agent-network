from functions import convert_rmb_to_usd

# 需要兑换的人民币金额
amount_rmb = 10

# 兑换成美元
amount_usd = convert_rmb_to_usd(amount_rmb)

# 打印兑换后的美元金额
print(f"{amount_rmb} RMB is {amount_usd:.2f} USD")