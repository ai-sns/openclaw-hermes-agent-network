"""
智能合约调用示例

演示如何使用 Python Web3.py 调用智能合约函数
"""

from web3 import Web3
from eth_account import Account

# ============================================================
# 1. 连接到 Sepolia 测试网
# ============================================================
w3 = Web3(Web3.HTTPProvider("https://rpc.sepolia.org"))
print(f"连接状态: {'✅ 已连接' if w3.is_connected() else '❌ 未连接'}")

# ============================================================
# 2. 合约 ABI (Application Binary Interface)
# ============================================================
# ABI 是合约的"接口说明书"，告诉程序如何与合约交互
ESCROW_ABI = [
    # 读取函数 (view) - 不需要 Gas
    {
        "name": "owner",
        "type": "function",
        "stateMutability": "view",
        "inputs": [],
        "outputs": [{"type": "address"}]
    },
    {
        "name": "getDeposit",
        "type": "function",
        "stateMutability": "view",
        "inputs": [{"name": "taskId", "type": "string"}],
        "outputs": [
            {"name": "user", "type": "address"},
            {"name": "amount", "type": "uint256"},
            {"name": "released", "type": "bool"}
        ]
    },
    # 写入函数 - 需要 Gas 和签名
    {
        "name": "deposit",
        "type": "function",
        "stateMutability": "payable",
        "inputs": [{"name": "taskId", "type": "string"}],
        "outputs": []
    },
    {
        "name": "release",
        "type": "function",
        "stateMutability": "nonpayable",
        "inputs": [{"name": "taskId", "type": "string"}],
        "outputs": []
    }
]

# 合约地址 (示例)
CONTRACT_ADDRESS = "0x1234567890123456789012345678901234567890"

# ============================================================
# 3. 创建合约实例
# ============================================================
contract = w3.eth.contract(
    address=Web3.to_checksum_address(CONTRACT_ADDRESS),
    abi=ESCROW_ABI
)

# ============================================================
# 4. 调用只读函数 (View Functions) - 免费，不需要私钥
# ============================================================
def call_view_function():
    """调用只读函数 - 任何人都可以调用，不需要 Gas"""
    print("\n" + "="*60)
    print("调用只读函数 (View Functions)")
    print("="*60)

    try:
        # 方式1: 直接调用
        owner = contract.functions.owner().call()
        print(f"合约所有者: {owner}")

        # 方式2: 带参数调用
        deposit_info = contract.functions.getDeposit("task-123").call()
        print(f"存款信息: 用户={deposit_info[0]}, 金额={deposit_info[1]}, 已释放={deposit_info[2]}")

    except Exception as e:
        print(f"调用失败 (合约可能不存在): {e}")

# ============================================================
# 5. 调用写入函数 (需要私钥签名 + Gas)
# ============================================================
def call_write_function(private_key: str, task_id: str, amount_eth: float):
    """
    调用写入函数 - 需要私钥签名和 Gas

    Args:
        private_key: 你的钱包私钥
        task_id: 任务ID
        amount_eth: 存款金额 (ETH)
    """
    print("\n" + "="*60)
    print("调用写入函数 (需要签名)")
    print("="*60)

    # 从私钥获取账户
    account = Account.from_key(private_key)
    print(f"发送地址: {account.address}")

    # 检查余额
    balance = w3.eth.get_balance(account.address)
    print(f"账户余额: {Web3.from_wei(balance, 'ether')} ETH")

    if balance == 0:
        print("❌ 余额为 0，无法支付 Gas 费用")
        return None

    # 构建交易
    amount_wei = Web3.to_wei(amount_eth, 'ether')

    # 获取 nonce (交易序号，防止重放攻击)
    nonce = w3.eth.get_transaction_count(account.address)

    # 构建合约调用交易
    transaction = contract.functions.deposit(task_id).build_transaction({
        'chainId': 11155111,  # Sepolia Chain ID
        'gas': 100000,        # Gas 限制
        'gasPrice': w3.eth.gas_price,
        'nonce': nonce,
        'value': amount_wei,  # 发送的 ETH 金额
    })

    print(f"交易详情:")
    print(f"  - 目标合约: {CONTRACT_ADDRESS}")
    print(f"  - 函数: deposit('{task_id}')")
    print(f"  - 金额: {amount_eth} ETH")
    print(f"  - Gas 价格: {Web3.from_wei(transaction['gasPrice'], 'gwei')} Gwei")

    # 签名交易 (这一步使用你的私钥)
    signed_txn = w3.eth.account.sign_transaction(transaction, private_key)
    print(f"✅ 交易已签名")

    # 发送交易到区块链
    # tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
    # print(f"交易已发送: {tx_hash.hex()}")

    # 等待确认
    # receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    # print(f"交易状态: {'成功' if receipt['status'] == 1 else '失败'}")

    print("\n⚠️ 演示模式: 交易未实际发送")
    print("取消注释上面的代码即可真正发送交易")

    return signed_txn

# ============================================================
# 6. 完整调用流程图
# ============================================================
"""
调用写入函数的完整流程:

┌──────────────┐
│   你的代码    │
└──────┬───────┘
       │ 1. 构建交易数据
       ▼
┌──────────────┐
│  build_tx()  │  → { to, data, value, gas, nonce }
└──────┬───────┘
       │ 2. 用私钥签名
       ▼
┌──────────────┐
│ sign_tx(key) │  → 生成签名 (v, r, s)
└──────┬───────┘
       │ 3. 发送到网络
       ▼
┌──────────────┐
│  send_raw()  │  → 返回 tx_hash
└──────┬───────┘
       │ 4. 矿工验证并执行
       ▼
┌──────────────┐
│   区块链     │  → 状态改变, 事件触发
└──────────────┘
"""

# ============================================================
# 主程序
# ============================================================
if __name__ == "__main__":
    print("智能合约调用演示")
    print("="*60)

    # 演示只读调用
    call_view_function()

    # 演示写入调用 (使用测试私钥)
    # ⚠️ 永远不要在代码中硬编码真实私钥！
    TEST_PRIVATE_KEY = "0x" + "1" * 64  # 仅用于演示
    call_write_function(TEST_PRIVATE_KEY, "task-demo-001", 0.001)
