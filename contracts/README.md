# Smart Contracts

This directory contains Solidity smart contracts for the AI Agent Open Platform.

## Contracts

### Escrow.sol

Task payment escrow contract that supports:
- Depositing funds for task payment
- Releasing funds to beneficiary on task completion
- Refunding funds to depositor on task cancellation
- Dispute resolution

### AuditLog.sol

Audit logging contract for storing interaction hashes on-chain:
- Immutable audit trail
- Hash verification
- Timestamp recording

## Deployment

### Prerequisites

- Node.js >= 14
- Hardhat or Foundry
- Infura API key (for testnet deployment)

### Install Dependencies

```bash
npm install hardhat @openzeppelin/contracts
```

### Compile

```bash
npx hardhat compile
```

### Deploy to Sepolia

1. Create `.env` file:
```
INFURA_API_KEY=your_infura_key
PRIVATE_KEY=your_private_key
```

2. Deploy:
```bash
npx hardhat run scripts/deploy.js --network sepolia
```

## Contract Addresses (Sepolia)

After deployment, update these addresses in `blockchain/config.py`:

- Escrow: `0x...`
- AuditLog: `0x...`

## Testing

```bash
npx hardhat test
```

## Security

- The Escrow contract includes a platform fee mechanism
- Only the depositor can release or refund
- Disputes can be resolved by the contract owner
- AuditLog entries are immutable once created
