# Funding Guide - Capital Requirements

## Overview

This guide explains exactly what funds you need and where to maintain them for the arbitrage bot to operate.

---

## DEX Trading (Polygon, Arbitrum, etc.)

### ✅ What You Need

**1. Native Tokens for Gas** ⚠️ REQUIRED
- **Polygon**: MATIC tokens
- **Arbitrum**: ETH tokens
- **Optimism**: ETH tokens
- **BSC**: BNB tokens
- **Ethereum**: ETH tokens (expensive!)

**Purpose**: Pay transaction gas fees

**Amount Needed**:
```
Polygon:  100-500 MATIC  (~$50-250)   ✅ RECOMMENDED
Arbitrum: 0.05-0.1 ETH   (~$100-200)
Optimism: 0.05-0.1 ETH   (~$100-200)
BSC:      0.5-1 BNB      (~$200-400)
Ethereum: 0.1-0.5 ETH    (~$200-1000) ⚠️ EXPENSIVE
```

**Gas Cost Per Trade**:
- Polygon: $0.005-$0.05 per trade (VERY CHEAP!)
- Arbitrum: $0.10-$0.50 per trade
- Optimism: $0.10-$0.50 per trade
- BSC: $0.10-$0.30 per trade
- Ethereum: $5-$50 per trade (NOT RECOMMENDED)

**2. Trading Capital** ❌ NOT REQUIRED!

Here's the important part: **With flash swaps (already in your smart contract), you DON'T need trading capital!**

**Why?**
Your `Arbitrage.sol` contract has `executeFlashSwap()` which:
1. Borrows tokens from a DEX pair (0 capital needed)
2. Executes the arbitrage trade
3. Repays the loan + 0.3% fee
4. Keeps the profit

**Example**:
```
1. Flash borrow 10 ETH from Uniswap (you pay: $0)
2. Sell 10 ETH on SushiSwap for $20,100
3. Buy 10 ETH on QuickSwap for $20,000
4. Repay 10.03 ETH to Uniswap (0.3% fee)
5. Keep profit: $100 - gas fees
```

**You never needed the 10 ETH!** All happens in one atomic transaction.

### ⚠️ Important Notes

**Gas Reserve**:
- Keep enough native tokens for at least 100-500 trades
- Bot automatically stops if gas too low (circuit breaker)
- Refill when getting low

**No Trading Capital Needed**:
- Flash swaps handle everything
- Only need gas tokens
- Profits accumulate in your wallet

**Wallet Security**:
- Use a dedicated wallet for the bot
- Never use your main wallet
- Keep private key secure

---

## CEX Trading (Binance & OKX)

### ✅ What You Need

**1. Spot Wallet Funding** ✅ REQUIRED

**On BOTH exchanges** (Binance AND OKX):
- USDT: $1,000 - $10,000
- ETH: 0.5 - 2 ETH
- BTC: 0.02 - 0.1 BTC
- Other pairs: As needed

**Why Both Exchanges?**
You need funds on BOTH sides to execute arbitrage:

**Example CEX Arbitrage**:
```
Binance: ETH = $2,000
OKX:     ETH = $2,010

Arbitrage:
1. Buy ETH on Binance for $2,000 (need $2,000 USDT on Binance)
2. Sell ETH on OKX for $2,010 (need 1 ETH on OKX)
3. Profit: $10

Then rebalance:
- Transfer USDT from OKX to Binance
- Transfer ETH from Binance to OKX
```

**Minimum Recommended**:
```
Binance Spot Wallet:
- 2,000 USDT
- 0.5 ETH
- 0.02 BTC

OKX Spot Wallet:
- 2,000 USDT
- 0.5 ETH
- 0.02 BTC

Total: ~$8,000-$10,000
```

**2. No Gas Fees** ✅
- CEX trading has NO gas fees
- Only trading fees (0.1% typically)
- Fees deducted from trade

**3. Withdrawal Fees** ⚠️
- Needed for rebalancing between exchanges
- Typically $1-$5 per transfer
- Keep some extra for rebalancing

---

## Summary Table

| Requirement | DEX | CEX |
|-------------|-----|-----|
| **Gas Tokens** | ✅ YES (100-500 MATIC, etc.) | ❌ NO |
| **Trading Capital** | ❌ NO (Flash swaps!) | ✅ YES ($5k-$10k) |
| **Both Exchanges** | N/A | ✅ YES (Binance + OKX) |
| **Withdrawal Fees** | ❌ NO | ✅ YES (~$1-$5) |

---

## Funding Checklist

### For DEX Trading Only:

```bash
✅ Wallet Setup:
[ ] Create dedicated MetaMask wallet
[ ] Save private key securely
[ ] Add wallet address to .env (WALLET_ADDRESS)
[ ] Add private key to .env (PRIVATE_KEY)

✅ Fund Wallet:
[ ] Buy 200-500 MATIC (~$100-250)
[ ] Send to your bot wallet
[ ] Verify balance: eth.getBalance(YOUR_ADDRESS)

✅ Smart Contract:
[ ] Deploy Arbitrage.sol contract
[ ] Verify deployed_contracts.json exists
[ ] Test with small amount first
```

**Total Cost**: $100-250 for gas

### For CEX Trading:

```bash
✅ Binance Setup:
[ ] Create Binance account
[ ] Complete KYC verification
[ ] Enable API access
[ ] Create API key with spot trading permission
[ ] Add API key to .env (BINANCE_API_KEY, BINANCE_SECRET_KEY)

✅ Fund Binance:
[ ] Deposit 2,000 USDT
[ ] Deposit 0.5 ETH
[ ] Deposit 0.02 BTC
[ ] Verify funds in Spot Wallet

✅ OKX Setup:
[ ] Create OKX account
[ ] Complete KYC verification
[ ] Enable API access
[ ] Create API key with trading permission
[ ] Add API key to .env (OKX_API_KEY, OKX_SECRET_KEY)

✅ Fund OKX:
[ ] Deposit 2,000 USDT
[ ] Deposit 0.5 ETH
[ ] Deposit 0.02 BTC
[ ] Verify funds in Spot Wallet
```

**Total Cost**: $8,000-10,000 trading capital

### For Both DEX + CEX:

Total: $8,100-10,250

---

## Capital Requirements by Strategy

### Strategy 1: DEX Only (Low Capital)

**Pros**:
- Low capital needed ($100-250)
- Flash swaps = infinite leverage
- Fully decentralized

**Cons**:
- Gas costs per trade
- Lower volume than CEX
- Need to monitor gas prices

**Recommended For**: Beginners, low capital

**Setup**:
```bash
MetaMask Wallet: 200 MATIC ($100)
Trading Capital: $0 (flash swaps)
Total: $100
```

---

### Strategy 2: CEX Only (High Capital)

**Pros**:
- No gas costs
- Higher volume
- Faster execution

**Cons**:
- Requires significant capital ($5k-10k)
- Need funds on both exchanges
- Centralized risk

**Recommended For**: Experienced traders with capital

**Setup**:
```bash
Binance: $4,000 in assets
OKX: $4,000 in assets
Total: $8,000
```

---

### Strategy 3: Both (Best Performance)

**Pros**:
- Maximum opportunities
- Diversified strategies
- Best ROI potential

**Cons**:
- Requires both DEX and CEX capital
- More complex management

**Recommended For**: Serious arbitrageurs

**Setup**:
```bash
MetaMask: 200 MATIC ($100)
Binance: $4,000 in assets
OKX: $4,000 in assets
Total: $8,100
```

---

## Profit Expectations

### DEX Trading (with $100 gas fund)

**Scenario 1: Conservative**
- 3 trades/day
- $5 profit/trade
- Gas: $0.05/trade
- **Daily**: $14.85
- **Monthly**: $445

**ROI**: 445% per month on $100 investment!

**Scenario 2: Aggressive** (high volatility)
- 10 trades/day
- $10 profit/trade
- Gas: $0.05/trade
- **Daily**: $99.50
- **Monthly**: $2,985

**ROI**: 2,985% per month!

### CEX Trading (with $8,000 capital)

**Scenario 1: Conservative**
- 5 trades/day
- 0.5% profit per trade
- Trading fees: 0.1%
- **Daily**: $160
- **Monthly**: $4,800

**ROI**: 60% per month on $8,000

**Scenario 2: Aggressive**
- 20 trades/day
- 0.3% profit per trade
- Trading fees: 0.1%
- **Daily**: $320
- **Monthly**: $9,600

**ROI**: 120% per month

---

## Rebalancing (CEX Only)

After trading, you'll accumulate assets on one exchange and deplete on another.

**Example Problem**:
```
After 10 trades:
Binance: 10,000 USDT, 0 ETH
OKX:     0 USDT, 5 ETH
```

You can't arbitrage anymore!

**Solution - Rebalancing**:

**Option 1: Internal Transfer** (Recommended)
- Use exchange internal transfer (if available)
- Usually free or very cheap
- Fast (minutes)

**Option 2: Blockchain Transfer**
- Withdraw from OKX
- Deposit to Binance
- Cost: $1-$10 per transfer
- Time: 10-30 minutes

**Automation**:
```python
# Pseudo-code for auto-rebalancing
if binance_usdt_balance > 80% of total:
    # Too much USDT on Binance, rebalance
    transfer_usdt_to_okx(amount)

if okx_eth_balance > 80% of total:
    # Too much ETH on OKX, rebalance
    transfer_eth_to_binance(amount)
```

**Frequency**: Rebalance when >70% imbalance

---

## Security Best Practices

### Wallet Security (DEX)

```bash
✅ DO:
- Use a dedicated wallet for the bot
- Keep private key in .env (never commit to git)
- Use hardware wallet for large amounts
- Regularly withdraw profits to cold storage
- Monitor wallet balance

❌ DON'T:
- Use your main wallet
- Share private key
- Store private key in code
- Leave large amounts in hot wallet
```

### API Security (CEX)

```bash
✅ DO:
- Use API keys with minimal permissions (spot trading only)
- Enable IP whitelist
- Use separate API keys for each bot
- Regularly rotate API keys
- Enable 2FA on exchange accounts

❌ DON'T:
- Give withdrawal permissions to API
- Use same API key everywhere
- Share API secret
- Disable 2FA
```

---

## Starting Recommendations

### Absolute Beginner (Under $500 capital)

**Strategy**: DEX Only
```bash
Fund: 100 MATIC ($50)
Start: Small test trades ($10)
Scale: Gradually increase after 50 successful trades
Risk: Very low
```

### Intermediate ($500-$5,000 capital)

**Strategy**: DEX + Small CEX
```bash
DEX: 200 MATIC ($100)
CEX: $2,000 split between exchanges
Start: Test both strategies
Scale: Focus on most profitable
```

### Advanced ($5,000+ capital)

**Strategy**: Full Multi-Strategy
```bash
DEX: 500 MATIC ($250)
CEX: $8,000+ split between exchanges
Multi-chain: Add Arbitrum ($100 ETH)
Mempool: Enable for backrunning
```

---

## Monthly Operating Costs

### DEX Trading

```
Gas (Polygon): $15-50/month
RPC (Alchemy free tier): $0/month
VPS (optional): $0-15/month
Total: $15-65/month
```

### CEX Trading

```
Trading fees: 0.1-0.2% per trade
Withdrawal fees: $10-50/month (rebalancing)
API costs: $0 (free)
Total: $50-200/month (depends on volume)
```

### Combined

```
Total: $65-265/month
```

With expected profits of $445-$9,600/month, costs are minimal.

---

## FAQ

**Q: Do I need $10k to start?**
A: No! For DEX trading, you only need $100-250 for gas.

**Q: How much can I make with just $100?**
A: With DEX flash swaps, $100 gas can generate $445-$2,985/month.

**Q: Why don't I need trading capital for DEX?**
A: Flash swaps borrow tokens for free during the transaction.

**Q: What if I run out of gas?**
A: Bot will stop trading. Refill your wallet with native tokens.

**Q: How often do I need to rebalance CEX?**
A: When one exchange has >70% of your capital (every few days).

**Q: Can I withdraw profits?**
A: Yes! Regularly withdraw to cold storage for security.

---

## Summary

### Your Thinking is Correct, But...

✅ **You said**: "Fund MetaMask with native tokens for gas"
- **CORRECT!** You need MATIC, ETH, BNB, etc. for gas

❌ **You said**: "Fund with tokens for swap fees"
- **NOT NEEDED!** Flash swaps handle this (no capital required!)

✅ **You said**: "Fund CEX spot wallets for trading"
- **CORRECT!** Need funds on both Binance and OKX

### Minimum to Start

**DEX Only**: $100 (just gas)
**CEX Only**: $5,000 (trading capital)
**Both**: $5,100

### Maximum Profit Potential

**DEX** ($100 investment): $445-$2,985/month
**CEX** ($8,000 investment): $4,800-$9,600/month
**Both**: $5,245-$12,585/month

---

## Next Steps

1. **Choose your strategy** (DEX only, CEX only, or both)
2. **Fund accordingly** (see checklist above)
3. **Deploy smart contract** (for DEX)
4. **Test with small amounts**
5. **Scale gradually**
6. **Monitor and optimize**

---

Generated: 2025-11-11
Version: 2.1.0
