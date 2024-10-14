# filename: load_data_and_convert.py
from functions import load_data, convert_rmb_to_usd_v2

def main():
    # Load the data
    data = load_data()
    print("Loaded data:")
    print(data)

    # Check if 'amount_rmb' column is present
    if 'amount_rmb' in data.columns:
        data['amount_usd'] = data['amount_rmb'].apply(convert_rmb_to_usd_v2)
        print("Data after currency conversion:")
        print(data[['amount_rmb', 'amount_usd']])
    else:
        print("No 'amount_rmb' column found for currency conversion")

if __name__ == "__main__":
    main()