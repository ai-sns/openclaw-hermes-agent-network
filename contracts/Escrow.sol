// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title Escrow
 * @dev Smart contract for AI Agent task escrow
 *
 * Features:
 * - Deposit funds for task payment
 * - Release funds on task completion
 * - Refund on task cancellation
 * - Dispute resolution support
 */
contract Escrow {
    // Escrow status
    enum Status {
        None,       // 0: Not created
        Active,     // 1: Funds deposited
        Released,   // 2: Funds released to beneficiary
        Refunded,   // 3: Funds returned to depositor
        Disputed    // 4: Under dispute
    }

    // Escrow record
    struct EscrowRecord {
        address depositor;
        address beneficiary;
        uint256 amount;
        Status status;
        uint256 createdAt;
        uint256 completedAt;
    }

    // State variables
    address public owner;
    uint256 public platformFeePercent; // Platform fee in basis points (100 = 1%)
    address public feeRecipient;

    // Mappings
    mapping(bytes32 => EscrowRecord) public escrows;
    mapping(address => uint256) public balances;

    // Events
    event Deposited(bytes32 indexed taskId, address indexed depositor, address indexed beneficiary, uint256 amount);
    event Released(bytes32 indexed taskId, address indexed beneficiary, uint256 amount);
    event Refunded(bytes32 indexed taskId, address indexed depositor, uint256 amount);
    event Disputed(bytes32 indexed taskId, address indexed initiator);
    event DisputeResolved(bytes32 indexed taskId, address indexed winner, uint256 amount);
    event FeeUpdated(uint256 oldFee, uint256 newFee);

    // Modifiers
    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner");
        _;
    }

    modifier escrowExists(bytes32 taskId) {
        require(escrows[taskId].status != Status.None, "Escrow not found");
        _;
    }

    modifier onlyDepositor(bytes32 taskId) {
        require(escrows[taskId].depositor == msg.sender, "Only depositor");
        _;
    }

    constructor(uint256 _feePercent) {
        owner = msg.sender;
        feeRecipient = msg.sender;
        platformFeePercent = _feePercent; // e.g., 500 = 5%
    }

    /**
     * @dev Deposit funds into escrow for a task
     * @param taskId Unique task identifier
     * @param beneficiary Address to receive funds on completion
     */
    function deposit(bytes32 taskId, address beneficiary) external payable {
        require(msg.value > 0, "Amount must be > 0");
        require(beneficiary != address(0), "Invalid beneficiary");
        require(escrows[taskId].status == Status.None, "Escrow already exists");

        escrows[taskId] = EscrowRecord({
            depositor: msg.sender,
            beneficiary: beneficiary,
            amount: msg.value,
            status: Status.Active,
            createdAt: block.timestamp,
            completedAt: 0
        });

        emit Deposited(taskId, msg.sender, beneficiary, msg.value);
    }

    /**
     * @dev Release funds to beneficiary (task completed)
     * @param taskId Task identifier
     */
    function release(bytes32 taskId) external escrowExists(taskId) onlyDepositor(taskId) {
        EscrowRecord storage escrow = escrows[taskId];
        require(escrow.status == Status.Active, "Escrow not active");

        escrow.status = Status.Released;
        escrow.completedAt = block.timestamp;

        // Calculate fee
        uint256 fee = (escrow.amount * platformFeePercent) / 10000;
        uint256 payout = escrow.amount - fee;

        // Transfer to beneficiary
        payable(escrow.beneficiary).transfer(payout);

        // Transfer fee
        if (fee > 0) {
            payable(feeRecipient).transfer(fee);
        }

        emit Released(taskId, escrow.beneficiary, payout);
    }

    /**
     * @dev Refund funds to depositor (task cancelled)
     * @param taskId Task identifier
     */
    function refund(bytes32 taskId) external escrowExists(taskId) onlyDepositor(taskId) {
        EscrowRecord storage escrow = escrows[taskId];
        require(escrow.status == Status.Active, "Escrow not active");

        escrow.status = Status.Refunded;
        escrow.completedAt = block.timestamp;

        payable(escrow.depositor).transfer(escrow.amount);

        emit Refunded(taskId, escrow.depositor, escrow.amount);
    }

    /**
     * @dev Initiate dispute
     * @param taskId Task identifier
     */
    function dispute(bytes32 taskId) external escrowExists(taskId) {
        EscrowRecord storage escrow = escrows[taskId];
        require(escrow.status == Status.Active, "Escrow not active");
        require(
            msg.sender == escrow.depositor || msg.sender == escrow.beneficiary,
            "Not party to escrow"
        );

        escrow.status = Status.Disputed;

        emit Disputed(taskId, msg.sender);
    }

    /**
     * @dev Resolve dispute (owner only)
     * @param taskId Task identifier
     * @param winner Address to receive funds
     */
    function resolveDispute(bytes32 taskId, address winner) external onlyOwner escrowExists(taskId) {
        EscrowRecord storage escrow = escrows[taskId];
        require(escrow.status == Status.Disputed, "Not in dispute");
        require(
            winner == escrow.depositor || winner == escrow.beneficiary,
            "Winner must be party"
        );

        escrow.status = winner == escrow.beneficiary ? Status.Released : Status.Refunded;
        escrow.completedAt = block.timestamp;

        payable(winner).transfer(escrow.amount);

        emit DisputeResolved(taskId, winner, escrow.amount);
    }

    /**
     * @dev Get escrow details
     * @param taskId Task identifier
     */
    function getEscrow(bytes32 taskId) external view returns (
        address depositor,
        address beneficiary,
        uint256 amount,
        uint8 status
    ) {
        EscrowRecord storage escrow = escrows[taskId];
        return (
            escrow.depositor,
            escrow.beneficiary,
            escrow.amount,
            uint8(escrow.status)
        );
    }

    /**
     * @dev Get escrow balance
     * @param taskId Task identifier
     */
    function getBalance(bytes32 taskId) external view returns (uint256) {
        EscrowRecord storage escrow = escrows[taskId];
        if (escrow.status == Status.Active) {
            return escrow.amount;
        }
        return 0;
    }

    /**
     * @dev Update platform fee (owner only)
     * @param newFee New fee in basis points
     */
    function updateFee(uint256 newFee) external onlyOwner {
        require(newFee <= 1000, "Fee too high"); // Max 10%
        uint256 oldFee = platformFeePercent;
        platformFeePercent = newFee;
        emit FeeUpdated(oldFee, newFee);
    }

    /**
     * @dev Update fee recipient (owner only)
     * @param newRecipient New fee recipient address
     */
    function updateFeeRecipient(address newRecipient) external onlyOwner {
        require(newRecipient != address(0), "Invalid address");
        feeRecipient = newRecipient;
    }

    /**
     * @dev Transfer ownership (owner only)
     * @param newOwner New owner address
     */
    function transferOwnership(address newOwner) external onlyOwner {
        require(newOwner != address(0), "Invalid address");
        owner = newOwner;
    }
}


/**
 * @title AuditLog
 * @dev Contract for storing audit hashes
 */
contract AuditLog {
    address public owner;

    // Mapping of audit ID to data hash
    mapping(bytes32 => bytes32) public audits;
    mapping(bytes32 => uint256) public timestamps;

    event AuditLogged(bytes32 indexed auditId, bytes32 dataHash, uint256 timestamp);

    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    /**
     * @dev Log an audit entry
     * @param auditId Unique audit identifier
     * @param dataHash Hash of the audit data
     */
    function logAudit(bytes32 auditId, bytes32 dataHash) external onlyOwner {
        require(audits[auditId] == bytes32(0), "Audit already exists");

        audits[auditId] = dataHash;
        timestamps[auditId] = block.timestamp;

        emit AuditLogged(auditId, dataHash, block.timestamp);
    }

    /**
     * @dev Get audit hash
     * @param auditId Audit identifier
     */
    function getAuditHash(bytes32 auditId) external view returns (bytes32) {
        return audits[auditId];
    }

    /**
     * @dev Verify audit hash
     * @param auditId Audit identifier
     * @param dataHash Hash to verify
     */
    function verifyAudit(bytes32 auditId, bytes32 dataHash) external view returns (bool) {
        return audits[auditId] == dataHash;
    }

    /**
     * @dev Get audit timestamp
     * @param auditId Audit identifier
     */
    function getAuditTimestamp(bytes32 auditId) external view returns (uint256) {
        return timestamps[auditId];
    }
}
