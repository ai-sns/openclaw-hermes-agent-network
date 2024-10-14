# filename: convert_currency.py
from convert_rmb_to_usd_v2 import convert_rmb_to_usd_v2

amount_rmb = 10
amount_usd = convert_rmb_to_usd_v2(amount_rmb)
print(f"{amount_rmb} 人民币兑换成美元是: {amount_usd} USD")