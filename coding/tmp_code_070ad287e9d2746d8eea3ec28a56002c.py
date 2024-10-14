from functions import convert_rmb_to_usd_v2

# 将10人民币转换为美元
amount_rmb = 10
amount_usd = convert_rmb_to_usd_v2(amount_rmb)

print(f"{amount_rmb}人民币兑换成美元是：{amount_usd}美元")