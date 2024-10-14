from functions import convert_rmb_to_usd

# 将10元人民币兑换成美元
amount_rmb = 10.0
amount_usd = convert_rmb_to_usd(amount_rmb)

print(f"{amount_rmb} 元人民币兑换成美元是: {amount_usd} 美元")