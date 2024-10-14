# filename: convert_rmb_to_usd.py
from convert_rmb_to_usd_v2 import convert_rmb_to_usd_v2

def main():
    try:
        amount_rmb = float(input("请输入要转换成美元的人民币金额: "))
        usd_amount = convert_rmb_to_usd_v2(amount_rmb)
        print(f"{amount_rmb}人民币转换成美元为: {usd_amount:.2f}美元")
    except ValueError as e:
        print(e)

if __name__ == "__main__":
    main()