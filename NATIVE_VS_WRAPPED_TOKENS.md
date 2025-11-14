# Native vs Wrapped Tokens - Complete Explanation

**Purpose**: Clarify the difference between native tokens (for gas) and wrapped tokens (for trading)

---

## 🔑 Key Concept

**You need TWO types of tokens on each blockchain:**

1. **Native Tokens** (for gas fees) - YOU MUST BUY THESE
2. **Wrapped Tokens** (for trading) - BORROWED via flash swaps

---

## 💰 Native Tokens (What You Need to Buy)

### Purpose: Pay Gas Fees ONLY

Native tokens are the blockchain's base currency used to pay transaction fees (gas).

| Chain | Native Token | What You Buy | Purpose |
|-------|--------------|--------------|---------|
| Polygon | MATIC | **MATIC** | Pay gas fees |
| Arbitrum | ETH | **ETH** | Pay gas fees |
| Optimism | ETH | **ETH** | Pay gas fees |
| BSC | BNB | **BNB** | Pay gas fees |

**How to Get Them**:
```bash
# Buy on centralized exchange (Binance, Coinbase, etc.)
1. Buy MATIC (for Polygon)
2. Buy ETH (for Arbitrum and Optimism)
3. Buy BNB (for BSC)

# Withdraw to your wallet
- Withdraw MATIC to your wallet address on Polygon network
- Withdraw ETH to your wallet address on Arbitrum network
- Withdraw ETH to your wallet address on Optimism network
- Withdraw BNB to your wallet address on BSC network
```

**Why You Need Them**:
- Every transaction on blockchain costs gas
- Gas is paid in native token (MATIC, ETH, BNB)
- Bot executes transactions → needs gas → needs native tokens
- **This is your ONLY required funding!**

---

## 🎁 Wrapped Tokens (What You DON'T Need to Buy)

### Purpose: DEX Trading (Borrowed via Flash Swaps)

Wrapped tokens are ERC-20 compatible versions of tokens that DEXes can trade.

| Chain | Wrapped Tokens | Examples |
|-------|----------------|----------|
| Polygon | WMATIC, WETH, WBTC, USDC | Wrapped versions |
| Arbitrum | WETH, WBTC, USDC, DAI | Wrapped versions |
| Optimism | WETH, WBTC, USDC, DAI | Wrapped versions |
| BSC | WBNB, ETH, WBTC, USDC | Wrapped versions |

**Examples**:
- **WMATIC** = Wrapped MATIC (on Polygon)
- **WETH** = Wrapped ETH (on all chains)
- **WBNB** = Wrapped BNB (on BSC)
- **WBTC** = Wrapped Bitcoin (on all chains)
- **USDC** = USD Coin (stablecoin, already ERC-20)

**Why They Exist**:
```
Native tokens (MATIC, ETH, BNB) are NOT ERC-20 compatible
          ↓
DEXes like Uniswap V2/V3 ONLY work with ERC-20 tokens
          ↓
Solution: Wrap native tokens into ERC-20 compatible versions
          ↓
MATIC → WMATIC, ETH → WETH, BNB → WBNB
```

**Why You DON'T Need to Buy Them**:
- ✅ Flash swaps BORROW these tokens automatically
- ✅ Borrowed for duration of transaction (milliseconds)
- ✅ Automatically repaid from arbitrage profit
- ✅ **Zero capital requirement for trading!**

---

## 🔄 How Flash Swaps Work

### Step-by-Step Explanation

**Without Flash Swaps** (Traditional Trading):
```
❌ OLD WAY (Requires Capital):
1. You buy 10 WETH ($20,000)
2. Bot swaps 10 WETH → 10.5 WETH on different DEX
3. Profit: 0.5 WETH ($1,000)
4. Problem: You needed $20,000 upfront!
```

**With Flash Swaps** (Our Bot):
```
✅ NEW WAY (Zero Capital):
1. Bot borrows 10 WETH from DEX A (FREE, no collateral)
2. Bot swaps 10 WETH → 10.5 WETH on DEX B
3. Bot repays 10 WETH to DEX A
4. Bot keeps 0.5 WETH profit
5. All happens in ONE transaction (atomic)
6. If unprofitable, transaction reverts (no loss)
7. Capital needed: ZERO (only gas fee ~$0.50)
```

### Complete Transaction Flow

```
┌─────────────────────────────────────────────────────────┐
│  Your Wallet Has: 100 MATIC (for gas)                   │
└─────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│  Bot Detects Opportunity:                                │
│  QuickSwap: 1 WETH = 2000 USDC                          │
│  SushiSwap: 1 WETH = 2010 USDC                          │
│  Profit: 10 USDC (0.5%)                                 │
└─────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│  Transaction Starts (pays ~0.5 MATIC gas)               │
│                                                          │
│  1. Borrow 1 WETH from QuickSwap pair                   │
│     ├─ No collateral needed                             │
│     └─ Must repay by end of transaction                 │
│                                                          │
│  2. Swap 1 WETH → 2010 USDC on SushiSwap               │
│     └─ Now have 2010 USDC                               │
│                                                          │
│  3. Swap 2000 USDC → 1 WETH on QuickSwap               │
│     └─ Now have 1 WETH + 10 USDC                        │
│                                                          │
│  4. Repay 1 WETH to QuickSwap                           │
│     └─ Debt cleared                                      │
│                                                          │
│  5. Keep 10 USDC profit in contract                     │
│                                                          │
│  ✅ Transaction Complete (0.3 seconds total)            │
└─────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│  Result:                                                 │
│  Your Wallet: 99.5 MATIC (paid gas)                     │
│  Contract: 10 USDC profit                                │
│  Total Cost: ~$0.50 (gas fee)                           │
│  Total Profit: ~$10                                      │
│  ROI: 2000%                                              │
└─────────────────────────────────────────────────────────┘
```

**Key Points**:
- You NEVER owned the 1 WETH being traded
- WETH was borrowed and repaid in same transaction
- Only cost: Gas fee in MATIC
- Only profit: 10 USDC (kept in contract)

---

## 💡 Practical Example: Your First Trade

### Initial Setup

**What You Buy** (Total: $250):
```
Polygon:  $50 worth of MATIC  → ~200 MATIC
Arbitrum: $75 worth of ETH    → ~0.025 ETH
Optimism: $75 worth of ETH    → ~0.025 ETH
BSC:      $50 worth of BNB    → ~0.15 BNB
```

**What You DON'T Buy**:
```
❌ WMATIC, WETH, WBTC, USDC, DAI, etc.
   (These are borrowed via flash swaps)
```

### Your Wallet Balance

**After Funding**:
```
Polygon Network:
├─ MATIC: 200 (native - for gas) ✅ You bought this
└─ WMATIC: 0 (wrapped - not needed) ❌ Don't need to buy

Arbitrum Network:
├─ ETH: 0.025 (native - for gas) ✅ You bought this
└─ WETH: 0 (wrapped - not needed) ❌ Don't need to buy

Optimism Network:
├─ ETH: 0.025 (native - for gas) ✅ You bought this
└─ WETH: 0 (wrapped - not needed) ❌ Don't need to buy

BSC Network:
├─ BNB: 0.15 (native - for gas) ✅ You bought this
└─ WBNB: 0 (wrapped - not needed) ❌ Don't need to buy
```

### After 100 Trades

**Your Wallet** (native tokens for gas):
```
Polygon:  150 MATIC (paid 50 MATIC in gas)
Arbitrum: 0.020 ETH (paid 0.005 ETH in gas)
Optimism: 0.020 ETH (paid 0.005 ETH in gas)
BSC:      0.12 BNB (paid 0.03 BNB in gas)
```

**Your Contract** (trading profits):
```
Polygon Contract:
├─ USDC: 500
├─ WETH: 0.2
├─ WMATIC: 100
└─ Total Value: ~$1,200

Arbitrum Contract:
├─ USDC: 800
├─ WETH: 0.3
└─ Total Value: ~$1,400

... etc
```

**Withdraw Profits**:
```bash
# Withdraw from contract to your wallet
python -c "
from contract_interface_v2 import ContractInterfaceV2

interface = ContractInterfaceV2(chain='polygon')
await interface.withdraw_profits(
    token_address='0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174',  # USDC
    amount=500 * 10**6  # 500 USDC
)
"

# Now USDC is in your wallet
# You can:
# 1. Keep as USDC
# 2. Swap to MATIC (for more gas)
# 3. Withdraw to CEX and cash out
```

---

## 🔄 Wrapping and Unwrapping

### What is Wrapping?

Converting native tokens to wrapped tokens (and vice versa) is called wrapping/unwrapping.

**Example: MATIC ↔ WMATIC**:
```solidity
// Wrapping (MATIC → WMATIC)
1. Send 100 MATIC to WMATIC contract
2. Receive 100 WMATIC (ERC-20 token)
3. Now you can trade WMATIC on DEXes

// Unwrapping (WMATIC → MATIC)
1. Send 100 WMATIC to WMATIC contract
2. Receive 100 MATIC (native token)
3. Now you can pay gas fees
```

**Key Facts**:
- ✅ Always 1:1 ratio (1 MATIC = 1 WMATIC)
- ✅ No fees (except gas ~$0.01)
- ✅ Instant conversion
- ✅ Fully reversible

### When You Need to Wrap/Unwrap

**Scenario 1: Running Low on Gas**
```
Problem: You have 500 USDC profit but only 5 MATIC for gas

Solution:
1. Swap USDC → WMATIC on DEX (e.g., 100 USDC → 400 WMATIC)
2. Unwrap WMATIC → MATIC (400 WMATIC → 400 MATIC)
3. Now you have 400 MATIC for more gas
```

**Scenario 2: Withdrawing Profits**
```
Problem: You want to cash out WETH profits to CEX

Solution:
1. Withdraw WETH from contract to wallet
2. Keep as WETH (CEXes accept WETH)
   OR
3. Unwrap WETH → ETH if CEX only accepts native ETH
4. Send to CEX
```

**You DON'T Need to Wrap for Trading**:
- ❌ Don't wrap MATIC → WMATIC before trading
- ✅ Bot borrows WMATIC via flash swaps
- ✅ Keep MATIC for gas only

---

## 📊 Capital Requirements Summary

### What You MUST Buy (Initial Funding)

| Purpose | Token Type | Amount Needed | Cost |
|---------|-----------|---------------|------|
| **Gas (Polygon)** | Native MATIC | 200 MATIC | $50 |
| **Gas (Arbitrum)** | Native ETH | 0.025 ETH | $75 |
| **Gas (Optimism)** | Native ETH | 0.025 ETH | $75 |
| **Gas (BSC)** | Native BNB | 0.15 BNB | $50 |
| **Total** | - | - | **$250** |

### What You DON'T Need to Buy

| Purpose | Token Type | Amount Needed | Cost |
|---------|-----------|---------------|------|
| **Trading Capital** | Wrapped tokens (WETH, WMATIC, WBTC, USDC) | 0 | **$0** |
| **Flash Swap Collateral** | Any | 0 | **$0** |
| **Total** | - | - | **$0** |

### Total Capital Required

```
Gas Funds:        $250  ✅ Required
Trading Capital:  $0    ✅ Flash swaps eliminate this
Total:            $250  ✅ Low barrier to entry
```

---

## ❓ Common Questions

### Q1: Why can't I just use MATIC to trade on Polygon DEXes?

**A**: DEXes require ERC-20 compatible tokens. Native MATIC is not ERC-20 compatible. You must use WMATIC (Wrapped MATIC) for trading.

```
MATIC (native)  → Pay gas fees ✅
WMATIC (ERC-20) → Trade on DEXes ✅

MATIC → WMATIC conversion is easy (wrapping)
```

### Q2: If I have profitable trades in WETH, how do I pay gas with it?

**A**: You can't pay gas with WETH. You need to:

```
Option 1: Swap WETH → WMATIC on DEX, then unwrap WMATIC → MATIC
Option 2: Keep some native MATIC reserved for gas
Option 3: Withdraw WETH profits, sell on CEX, buy more MATIC
```

**Bot handles this automatically**:
- Monitors gas balance on each chain
- Alerts when gas < $10 USD
- You manually refill or auto-swap profits to gas

### Q3: Do flash swaps work with all tokens?

**A**: Flash swaps work with any token pair on Uniswap V2 compatible DEXes.

**Supported**:
- ✅ WETH, WMATIC, WBNB (wrapped native tokens)
- ✅ WBTC (wrapped Bitcoin)
- ✅ USDC, USDT, DAI (stablecoins - already ERC-20)
- ✅ Any ERC-20 token with sufficient liquidity

**Not Supported**:
- ❌ Native tokens directly (MATIC, ETH, BNB)
- ❌ Use wrapped versions instead

### Q4: What happens to my profits?

**Your Profits Stay in the Contract** (in wrapped tokens):

```
After 1 month of trading:
├─ Polygon Contract: 500 USDC, 0.2 WETH, 100 WMATIC
├─ Arbitrum Contract: 800 USDC, 0.3 WETH
└─ Total Value: ~$5,000

Options:
1. Withdraw to wallet anytime (call withdraw_profits)
2. Let it accumulate
3. Auto-compound (trade with larger amounts)
```

**Withdrawal Example**:
```bash
# Withdraw USDC from Polygon contract
python scripts/withdraw_profits.py --chain polygon --token USDC --amount 500
```

### Q5: What if I run out of gas mid-trade?

**A**: Transaction will fail and revert. This is GOOD because:

```
✅ Flash swap reverts = no loss
✅ You only lose the gas fee (~$0.50)
✅ No borrowed funds lost (automatic revert)
✅ No capital at risk
```

**Prevention**:
- Bot monitors gas balance
- Alerts when < $10 USD on any chain
- Stops trading when gas critically low

### Q6: Can I start with just one chain?

**A**: YES! Start with Polygon (cheapest gas):

```
Minimal Start:
├─ Polygon: $50 of MATIC
├─ Deploy ArbitrageV2 to Polygon only
├─ Run bot on Polygon only
└─ Expected: $500-2,000/month

Then expand:
├─ Add Arbitrum with $75 ETH
├─ Add Optimism with $75 ETH
├─ Add BSC with $50 BNB
└─ Expected: $2,300-9,000/month total
```

---

## 🎯 Action Plan

### Step 1: Buy Native Tokens for Gas

**On Centralized Exchange (Binance, Coinbase, etc.)**:
```
1. Buy MATIC (Polygon)
2. Buy ETH (for Arbitrum and Optimism)
3. Buy BNB (for BSC)

Total: ~$250
```

### Step 2: Withdraw to Your Wallet

**IMPORTANT: Select Correct Network!**

```
Polygon:
├─ Token: MATIC
├─ Network: Polygon (NOT Ethereum!)
└─ Address: Your wallet address

Arbitrum:
├─ Token: ETH
├─ Network: Arbitrum One
└─ Address: Same wallet address

Optimism:
├─ Token: ETH
├─ Network: Optimism
└─ Address: Same wallet address

BSC:
├─ Token: BNB
├─ Network: BNB Smart Chain (BSC)
└─ Address: Same wallet address
```

**Common Mistake**: Sending MATIC via Ethereum network (expensive gas!)
**Correct**: Send MATIC via Polygon network (cheap gas!)

### Step 3: Verify Balances

```bash
# Check balances on each chain
python -c "
from web3 import Web3
import config

for chain, cfg in config.SUPPORTED_CHAINS.items():
    w3 = Web3(Web3.HTTPProvider(cfg['rpc']))
    balance = w3.eth.get_balance(config.WALLET_ADDRESS)
    balance_eth = w3.from_wei(balance, 'ether')
    print(f'{chain}: {balance_eth} {cfg[\"native_token\"]}'
)
"

# Expected output:
# polygon: 200.0 MATIC
# arbitrum: 0.025 ETH
# optimism: 0.025 ETH
# bsc: 0.15 BNB
```

### Step 4: Deploy and Trade

```bash
# Deploy ArbitrageV2
python scripts/deploy_arbitrage_v2.py --chain polygon

# Start trading (bot borrows wrapped tokens via flash swaps)
docker-compose up -d
```

### Step 5: Monitor Gas and Profits

```bash
# Check gas balances
docker exec arbitrage-bot python scripts/health_check.py

# View profits
docker exec arbitrage-bot python -c "
from contract_interface_v2 import ContractInterfaceV2
interface = ContractInterfaceV2(chain='polygon')
stats = await interface.get_contract_stats()
print(stats)
"
```

---

## ✅ Summary

### What You Need to Understand

1. **Native Tokens (MATIC, ETH, BNB)**:
   - ✅ Used for gas fees ONLY
   - ✅ YOU MUST BUY THESE ($250 total)
   - ✅ Stored in your wallet
   - ✅ Decreases as you execute trades

2. **Wrapped Tokens (WMATIC, WETH, WBTC, USDC)**:
   - ✅ Used for trading
   - ✅ BORROWED via flash swaps (FREE)
   - ✅ Never need to buy upfront
   - ✅ Profits accumulate in contract

3. **Capital Efficiency**:
   ```
   Traditional Trading:
   - Need $10,000 to trade 5 ETH
   - ROI: 10-20% per month = $1,000-2,000

   Flash Swap Trading:
   - Need $250 for gas to trade 5 ETH
   - ROI: 920-3,600% per month = $2,300-9,000

   Flash swaps are 37x more capital efficient!
   ```

4. **Your Only Costs**:
   - Initial: $250 (native tokens for gas)
   - Ongoing: Gas refills when running low (~$50/month per chain)
   - Total: $250 upfront + $200/month ongoing

---

## 🚀 You're Ready!

Now you understand:
- ✅ Why you need native tokens (gas fees)
- ✅ Why you don't need wrapped tokens (flash swaps)
- ✅ How flash swaps work (borrow + trade + repay)
- ✅ Where profits go (contract, in wrapped tokens)
- ✅ How to withdraw profits (withdraw_profits function)

**Next step**: Fund your wallet with native tokens and deploy! 🎉

---

**Created**: 2025-11-13
**Version**: 2.0.0
