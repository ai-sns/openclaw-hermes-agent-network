from functions import convert_rmb_to_usd_v2

# 假设要兑换的人民币金额
amount_rmb = 100.0  # 兑换100人民币

# 进行兑换
amount_usd = convert_rmb_to_usd_v2(amount_rmb)

# 输出兑换结果
print(f"{amount_rmb} RMB is converted to {amount_usd} USD.")