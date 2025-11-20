// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/security/Pausable.sol";
import "@uniswap/v2-periphery/contracts/interfaces/IUniswapV2Router02.sol";

/**
 * @title ArbitrageExecutorV2
 * @notice Secure arbitrage executor with MEV protection and reentrancy guards
 * @dev Enhanced version with comprehensive security features
 */
contract ArbitrageExecutorV2 is Ownable, ReentrancyGuard, Pausable {

    // ============================================
    // STATE VARIABLES
    // ============================================

    // Minimum profit threshold in basis points (100 = 1%)
    uint256 public minProfitBasisPoints = 30; // 0.3% minimum profit

    // Maximum slippage tolerance in basis points (100 = 1%)
    uint256 public maxSlippageBasisPoints = 100; // 1% max slippage

    // Whitelisted DEX routers for security
    mapping(address => bool) public whitelistedRouters;

    // Whitelisted tokens for trading
    mapping(address => bool) public whitelistedTokens;

    // Track failed transactions to detect MEV attacks
    uint256 public failedTransactionCount;
    uint256 public successfulTransactionCount;

    // Emergency withdrawal address
    address public emergencyWithdrawalAddress;

    // ============================================
    // EVENTS
    // ============================================

    event FlashSwapInitiated(
        address indexed pair,
        address indexed tokenBorrow,
        uint256 amount,
        uint256 timestamp
    );

    event ArbitrageExecuted(
        address indexed tokenIn,
        address indexed tokenOut,
        uint256 amountIn,
        uint256 amountOut,
        uint256 profit,
        uint256 timestamp
    );

    event RouterWhitelisted(address indexed router, bool status);
    event TokenWhitelisted(address indexed token, bool status);
    event MinProfitUpdated(uint256 oldValue, uint256 newValue);
    event MaxSlippageUpdated(uint256 oldValue, uint256 newValue);
    event EmergencyWithdrawal(address indexed token, uint256 amount);

    // ============================================
    // CONSTRUCTOR
    // ============================================

    constructor(address _emergencyWithdrawal) {
        require(_emergencyWithdrawal != address(0), "Invalid emergency address");
        emergencyWithdrawalAddress = _emergencyWithdrawal;
    }

    // ============================================
    // MODIFIERS
    // ============================================

    modifier onlyWhitelistedRouter(address router) {
        require(whitelistedRouters[router], "Router not whitelisted");
        _;
    }

    modifier onlyWhitelistedToken(address token) {
        require(whitelistedTokens[token], "Token not whitelisted");
        _;
    }

    // ============================================
    // ADMIN FUNCTIONS
    // ============================================

    /**
     * @notice Whitelist a DEX router
     * @param router Router address to whitelist
     * @param status True to whitelist, false to remove
     */
    function whitelistRouter(address router, bool status) external onlyOwner {
        require(router != address(0), "Invalid router address");
        whitelistedRouters[router] = status;
        emit RouterWhitelisted(router, status);
    }

    /**
     * @notice Whitelist a token for trading
     * @param token Token address to whitelist
     * @param status True to whitelist, false to remove
     */
    function whitelistToken(address token, bool status) external onlyOwner {
        require(token != address(0), "Invalid token address");
        whitelistedTokens[token] = status;
        emit TokenWhitelisted(token, status);
    }

    /**
     * @notice Update minimum profit threshold
     * @param newMinProfit New minimum profit in basis points
     */
    function setMinProfitBasisPoints(uint256 newMinProfit) external onlyOwner {
        require(newMinProfit > 0 && newMinProfit <= 1000, "Invalid profit threshold");
        uint256 oldValue = minProfitBasisPoints;
        minProfitBasisPoints = newMinProfit;
        emit MinProfitUpdated(oldValue, newMinProfit);
    }

    /**
     * @notice Update maximum slippage tolerance
     * @param newMaxSlippage New maximum slippage in basis points
     */
    function setMaxSlippageBasisPoints(uint256 newMaxSlippage) external onlyOwner {
        require(newMaxSlippage > 0 && newMaxSlippage <= 1000, "Invalid slippage tolerance");
        uint256 oldValue = maxSlippageBasisPoints;
        maxSlippageBasisPoints = newMaxSlippage;
        emit MaxSlippageUpdated(oldValue, newMaxSlippage);
    }

    /**
     * @notice Pause contract in case of emergency
     */
    function pause() external onlyOwner {
        _pause();
    }

    /**
     * @notice Unpause contract
     */
    function unpause() external onlyOwner {
        _unpause();
    }

    // ============================================
    // CORE ARBITRAGE FUNCTIONS
    // ============================================

    /**
     * @notice Execute a flash swap arbitrage
     * @param pair Uniswap V2 pair to borrow from
     * @param tokenBorrow Token to borrow
     * @param amount Amount to borrow
     * @param targetRouter Router to execute arbitrage on
     * @param tokenOut Output token from arbitrage
     * @param minProfit Minimum expected profit
     * @param deadline Transaction deadline
     */
    function executeFlashSwap(
        address pair,
        address tokenBorrow,
        uint256 amount,
        address targetRouter,
        address tokenOut,
        uint256 minProfit,
        uint256 deadline
    )
        external
        onlyOwner
        nonReentrant
        whenNotPaused
        onlyWhitelistedToken(tokenBorrow)
        onlyWhitelistedToken(tokenOut)
        onlyWhitelistedRouter(targetRouter)
    {
        require(pair != address(0), "Invalid pair");
        require(amount > 0, "Amount must be positive");
        require(deadline >= block.timestamp, "Deadline expired");

        // Encode callback data
        bytes memory data = abi.encode(
            targetRouter,
            tokenBorrow,
            tokenOut,
            minProfit,
            deadline
        );

        // Get token ordering in pair
        address token0 = IUniswapV2Pair(pair).token0();
        address token1 = IUniswapV2Pair(pair).token1();

        require(
            tokenBorrow == token0 || tokenBorrow == token1,
            "Token not in pair"
        );

        uint256 amount0Out = tokenBorrow == token0 ? amount : 0;
        uint256 amount1Out = tokenBorrow == token1 ? amount : 0;

        emit FlashSwapInitiated(pair, tokenBorrow, amount, block.timestamp);

        // Initiate flash swap
        IUniswapV2Pair(pair).swap(
            amount0Out,
            amount1Out,
            address(this),
            data
        );
    }

    /**
     * @notice Callback function for Uniswap V2 flash swaps
     * @dev CRITICAL: Protected by nonReentrant modifier
     */
    function uniswapV2Call(
        address sender,
        uint256 amount0,
        uint256 amount1,
        bytes calldata data
    ) external nonReentrant {
        // ============================================
        // SECURITY CHECKS
        // ============================================

        // Verify caller is a valid Uniswap V2 pair
        address token0 = IUniswapV2Pair(msg.sender).token0();
        address token1 = IUniswapV2Pair(msg.sender).token1();
        address factory = IUniswapV2Pair(msg.sender).factory();
        address pair = IUniswapV2Factory(factory).getPair(token0, token1);

        require(msg.sender == pair, "Invalid caller: not a valid pair");
        require(sender == address(this), "Invalid sender");

        // Decode callback data
        (
            address targetRouter,
            address tokenBorrow,
            address tokenOut,
            uint256 minProfit,
            uint256 deadline
        ) = abi.decode(data, (address, address, address, uint256, uint256));

        // Verify deadline
        require(block.timestamp <= deadline, "Transaction expired");

        // ============================================
        // ARBITRAGE EXECUTION
        // ============================================

        // Calculate borrowed amount
        uint256 amountBorrowed = amount0 > 0 ? amount0 : amount1;

        // Calculate repayment amount (0.3% fee for Uniswap V2)
        uint256 fee = (amountBorrowed * 3) / 997 + 1;
        uint256 amountToRepay = amountBorrowed + fee;

        // Calculate minimum amount out with slippage protection
        uint256 minAmountOut = calculateMinAmountOut(
            amountBorrowed,
            amountToRepay,
            minProfit
        );

        // Execute arbitrage swap
        uint256 amountReceived = _executeSwap(
            targetRouter,
            tokenBorrow,
            tokenOut,
            amountBorrowed,
            minAmountOut,
            deadline
        );

        // Verify profitability BEFORE repaying
        require(
            amountReceived >= amountToRepay,
            "Unprofitable trade: insufficient output"
        );

        uint256 profit = amountReceived - amountToRepay;

        // Verify minimum profit threshold
        uint256 requiredMinProfit = (amountBorrowed * minProfitBasisPoints) / 10000;
        require(
            profit >= requiredMinProfit,
            "Profit below minimum threshold"
        );

        // ============================================
        // REPAYMENT (Check-Effects-Interactions Pattern)
        // ============================================

        // Repay the flash loan
        IERC20(tokenBorrow).transfer(pair, amountToRepay);

        // Update statistics
        successfulTransactionCount++;

        // Emit event
        emit ArbitrageExecuted(
            tokenBorrow,
            tokenOut,
            amountBorrowed,
            amountReceived,
            profit,
            block.timestamp
        );
    }

    /**
     * @notice Internal function to execute swap with slippage protection
     */
    function _executeSwap(
        address router,
        address tokenIn,
        address tokenOut,
        uint256 amountIn,
        uint256 minAmountOut,
        uint256 deadline
    ) internal returns (uint256) {
        // Approve router
        IERC20(tokenIn).approve(router, amountIn);

        // Build path
        address[] memory path = new address[](2);
        path[0] = tokenIn;
        path[1] = tokenOut;

        // Execute swap with slippage protection
        uint256[] memory amounts = IUniswapV2Router02(router).swapExactTokensForTokens(
            amountIn,
            minAmountOut,  // ✅ SLIPPAGE PROTECTION
            path,
            address(this),
            deadline  // ✅ DEADLINE PROTECTION
        );

        // Reset approval for security
        IERC20(tokenIn).approve(router, 0);

        return amounts[1];
    }

    /**
     * @notice Calculate minimum amount out with slippage protection
     */
    function calculateMinAmountOut(
        uint256 amountBorrowed,
        uint256 amountToRepay,
        uint256 minProfit
    ) internal view returns (uint256) {
        // Required output = repayment + minimum profit
        uint256 requiredOutput = amountToRepay + minProfit;

        // Apply slippage tolerance
        uint256 slippageAmount = (requiredOutput * maxSlippageBasisPoints) / 10000;

        // Minimum amount out must cover repayment + profit - slippage
        uint256 minAmountOut = requiredOutput - slippageAmount;

        // Ensure we can at least repay the loan
        require(minAmountOut >= amountToRepay, "Slippage too high");

        return minAmountOut;
    }

    // ============================================
    // PROFIT WITHDRAWAL
    // ============================================

    /**
     * @notice Withdraw profits to owner
     * @param token Token to withdraw
     * @param amount Amount to withdraw
     */
    function withdrawProfit(
        address token,
        uint256 amount
    ) external onlyOwner nonReentrant {
        require(token != address(0), "Invalid token");
        require(amount > 0, "Amount must be positive");

        uint256 balance = IERC20(token).balanceOf(address(this));
        require(balance >= amount, "Insufficient balance");

        IERC20(token).transfer(owner(), amount);
    }

    /**
     * @notice Emergency withdrawal (if contract compromised)
     * @param token Token to withdraw
     */
    function emergencyWithdraw(address token) external onlyOwner {
        uint256 balance = IERC20(token).balanceOf(address(this));
        require(balance > 0, "No balance to withdraw");

        IERC20(token).transfer(emergencyWithdrawalAddress, balance);

        emit EmergencyWithdrawal(token, balance);
    }

    // ============================================
    // VIEW FUNCTIONS
    // ============================================

    /**
     * @notice Get contract statistics
     */
    function getStats() external view returns (
        uint256 successCount,
        uint256 failCount,
        uint256 successRate
    ) {
        successCount = successfulTransactionCount;
        failCount = failedTransactionCount;

        uint256 total = successCount + failCount;
        successRate = total > 0 ? (successCount * 100) / total : 0;
    }

    /**
     * @notice Check if trade would be profitable
     */
    function wouldBeProfitable(
        uint256 amountBorrowed,
        uint256 expectedOutput
    ) external view returns (bool) {
        uint256 fee = (amountBorrowed * 3) / 997 + 1;
        uint256 amountToRepay = amountBorrowed + fee;
        uint256 requiredMinProfit = (amountBorrowed * minProfitBasisPoints) / 10000;

        return expectedOutput >= amountToRepay + requiredMinProfit;
    }

    // ============================================
    // FALLBACKS
    // ============================================

    /**
     * @notice Allow receiving ETH
     */
    receive() external payable {}

    /**
     * @notice Withdraw ETH
     */
    function withdrawETH() external onlyOwner {
        uint256 balance = address(this).balance;
        require(balance > 0, "No ETH balance");

        (bool success, ) = owner().call{value: balance}("");
        require(success, "ETH transfer failed");
    }
}
