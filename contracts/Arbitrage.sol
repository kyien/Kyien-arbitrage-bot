// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@uniswap/v2-periphery/contracts/interfaces/IUniswapV2Router02.sol";

contract ArbitrageExecutor is Ownable {
    // DEX router addresses
    address public immutable uniswapRouter;
    address public immutable sushiswapRouter;
    
    // Events
    event TradeExecuted(address tokenIn, address tokenOut, uint amountIn, uint amountOut, address dex);
    event FlashSwapExecuted(address tokenBorrow, uint amount, uint fee);
    event ArbitrageExecuted(uint profit);
    
    // Constructor
    constructor(address _uniswapRouter, address _sushiswapRouter) {
        uniswapRouter = _uniswapRouter;
        sushiswapRouter = _sushiswapRouter;
    }
    
    // Execute a simple swap on a specified DEX
    function executeSwap(
        address router,
        address tokenIn,
        address tokenOut,
        uint amountIn,
        uint minAmountOut,
        uint deadline
    ) external onlyOwner returns (uint[] memory amounts) {
        // Approve router to spend our tokens
        IERC20(tokenIn).approve(router, amountIn);
        
        // Set up the path
        address[] memory path = new address[](2);
        path[0] = tokenIn;
        path[1] = tokenOut;
        
        // Execute the swap
        amounts = IUniswapV2Router02(router).swapExactTokensForTokens(
            amountIn,
            minAmountOut,
            path,
            address(this),
            deadline
        );
        
        emit TradeExecuted(tokenIn, tokenOut, amountIn, amounts[1], router);
        
        return amounts;
    }
    
    // Execute a v2 flashswap (Uniswap V2, Sushiswap, etc)
    function executeFlashSwap(
        address pair,        // The Uniswap V2 pair to use for the flashswap
        address tokenBorrow, // Token to borrow from the pair
        uint amount,         // Amount to borrow
        bytes calldata data  // Custom data to pass to the callback
    ) external onlyOwner {
        // Call the swap function with amount0Out or amount1Out set to 0 depending on the token we want
        // This is a simplified version - actual implementation would need to check token0/token1 ordering
        address token0 = IUniswapV2Pair(pair).token0();
        address token1 = IUniswapV2Pair(pair).token1();
        
        uint amount0Out = tokenBorrow == token0 ? amount : 0;
        uint amount1Out = tokenBorrow == token1 ? amount : 0;
        
        // Initiate the flashswap
        IUniswapV2Pair(pair).swap(
            amount0Out,
            amount1Out,
            address(this),
            data
        );
    }
    
    // Callback function for flashswap
    function uniswapV2Call(
        address sender,
        uint amount0,
        uint amount1,
        bytes calldata data
    ) external {
        // Verify the caller is a valid pair
        address token0 = IUniswapV2Pair(msg.sender).token0();
        address token1 = IUniswapV2Pair(msg.sender).token1();
        address pair = IUniswapV2Factory(IUniswapV2Pair(msg.sender).factory()).getPair(token0, token1);
        require(msg.sender == pair, "Invalid caller");
        
        // Decode the data
        (address targetRouter, address tokenIn, address tokenOut) = abi.decode(data, (address, address, address));
        
        // Calculate the amount we borrowed
        uint amountBorrowed = amount0 > 0 ? amount0 : amount1;
        address tokenBorrowed = amount0 > 0 ? token0 : token1;
        
        // Calculate the fee (0.3% for Uniswap V2)
        uint fee = (amountBorrowed * 3) / 997 + 1;
        uint amountToRepay = amountBorrowed + fee;
        
        // Execute arbitrage logic here
        // 1. Swap the borrowed token on target DEX
        IERC20(tokenBorrowed).approve(targetRouter, amountBorrowed);
        
        address[] memory path = new address[](2);
        path[0] = tokenBorrowed;
        path[1] = tokenIn;
        
        IUniswapV2Router02(targetRouter).swapExactTokensForTokens(
            amountBorrowed,
            0, // No min amount for simplicity
            path,
            address(this),
            block.timestamp
        );
        
        // 2. Pay back the loan
        IERC20(tokenBorrowed).transfer(pair, amountToRepay);
        
        // 3. Keep the profit
        uint balance = IERC20(tokenBorrowed).balanceOf(address(this));
        if (balance > 0) {
            emit ArbitrageExecuted(balance);
        }
    }
    
    // Withdraw tokens (for the owner to collect profits)
    function withdrawToken(address token, uint amount) external onlyOwner {
        IERC20(token).transfer(owner(), amount);
    }
    
    // Allow receiving ETH
    receive() external payable {}
}

// Required interfaces
interface IUniswapV2Pair {
    function token0() external view returns (address);
    function token1() external view returns (address);
    function factory() external view returns (address);
    function swap(uint amount0Out, uint amount1Out, address to, bytes calldata data) external;
}

interface IUniswapV2Factory {
    function getPair(address tokenA, address tokenB) external view returns (address pair);
}
