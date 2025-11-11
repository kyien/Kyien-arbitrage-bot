from dotenv import load_dotenv
import os

load_dotenv()

# Exchange API Keys
BINANCE_API_KEY = os.getenv('BINANCE_API_KEY')
BINANCE_SECRET_KEY = os.getenv('BINANCE_SECRET_KEY')
OKX_API_KEY = os.getenv('OKX_API_KEY')
OKX_SECRET_KEY = os.getenv('OKX_SECRET_KEY')

# Blockchain RPC URLs
# IMPORTANT: Use private RPC endpoints for 10-50x faster execution
# Recommended providers: Alchemy, Infura, QuickNode, Ankr
POLYGON_RPC_URL = os.getenv('POLYGON_RPC_URL', 'https://polygon-rpc.com')
POLYGON_WSS_URL = os.getenv('POLYGON_WSS_URL', 'wss://polygon-rpc.com')
ARBITRUM_RPC_URL = os.getenv('ARBITRUM_RPC_URL', 'https://arb1.arbitrum.io/rpc')
ARBITRUM_WSS_URL = os.getenv('ARBITRUM_WSS_URL', 'wss://arb1.arbitrum.io/ws')
OPTIMISM_RPC_URL = os.getenv('OPTIMISM_RPC_URL', 'https://mainnet.optimism.io')
OPTIMISM_WSS_URL = os.getenv('OPTIMISM_WSS_URL', 'wss://mainnet.optimism.io/ws')
BSC_RPC_URL = os.getenv('BSC_RPC_URL', 'https://bsc-dataseed.binance.org')
BSC_WSS_URL = os.getenv('BSC_WSS_URL', 'wss://bsc-dataseed.binance.org:8443/ws')

# Additional chains for cross-chain arbitrage
BASE_RPC_URL = os.getenv('BASE_RPC_URL', 'https://mainnet.base.org')
BASE_WSS_URL = os.getenv('BASE_WSS_URL', 'wss://mainnet.base.org/ws')
LINEA_RPC_URL = os.getenv('LINEA_RPC_URL', 'https://rpc.linea.build')
LINEA_WSS_URL = os.getenv('LINEA_WSS_URL', 'wss://rpc.linea.build')
AVALANCHE_RPC_URL = os.getenv('AVALANCHE_RPC_URL', 'https://api.avax.network/ext/bc/C/rpc')
AVALANCHE_WSS_URL = os.getenv('AVALANCHE_WSS_URL', 'wss://api.avax.network/ext/bc/C/ws')
ETHEREUM_RPC_URL = os.getenv('ETHEREUM_RPC_URL', 'https://eth.rpc.node.provider')
ETHEREUM_WSS_URL = os.getenv('ETHEREUM_WSS_URL', 'wss://eth.rpc.node.provider')

# Chain list for iteration
SUPPORTED_CHAINS = {
    'polygon': {
        'rpc': POLYGON_RPC_URL,
        'wss': POLYGON_WSS_URL,
        'chain_id': 137
    },
    'arbitrum': {
        'rpc': ARBITRUM_RPC_URL,
        'wss': ARBITRUM_WSS_URL,
        'chain_id': 42161
    },
    'optimism': {
        'rpc': OPTIMISM_RPC_URL,
        'wss': OPTIMISM_WSS_URL,
        'chain_id': 10
    },
    'bsc': {
        'rpc': BSC_RPC_URL,
        'wss': BSC_WSS_URL,
        'chain_id': 56
    },
    'base': {
        'rpc': BASE_RPC_URL,
        'wss': BASE_WSS_URL,
        'chain_id': 8453
    },
    'linea': {
        'rpc': LINEA_RPC_URL,
        'wss': LINEA_WSS_URL,
        'chain_id': 59144
    },
    'avalanche': {
        'rpc': AVALANCHE_RPC_URL,
        'wss': AVALANCHE_WSS_URL,
        'chain_id': 43114
    },
    'ethereum': {
        'rpc': ETHEREUM_RPC_URL,
        'wss': ETHEREUM_WSS_URL,
        'chain_id': 1
    }
}

# Wallet Configuration
WALLET_ADDRESS = os.getenv('WALLET_ADDRESS')
PRIVATE_KEY = os.getenv('PRIVATE_KEY')

# Trading Parameters
MIN_PROFIT_THRESHOLD = float(os.getenv('MIN_PROFIT_THRESHOLD', '0.5'))  # Minimum profit percentage
MAX_TRADE_AMOUNT = float(os.getenv('MAX_TRADE_AMOUNT', '1000'))  # Maximum trade amount in USDT
GAS_LIMIT = int(os.getenv('GAS_LIMIT', '300000'))
SLIPPAGE_TOLERANCE = float(os.getenv('SLIPPAGE_TOLERANCE', '0.5'))

# Trading pairs to monitor
TRADING_PAIRS = {
    'CEX': ['USDT/USD', 'ETH/USDT', 'BTC/USDT', 'MATIC/USDT'],
    'DEX': ['WETH/USDC', 'WMATIC/USDC', 'WBTC/USDC']
}

# DEX addresses on Polygon
QUICKSWAP_ROUTER = "0xa5E0829CaCEd8fFDD4De3c43696c57F7D7A678ff"
SUSHISWAP_ROUTER = "0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506"
UNISWAP_V3_ROUTER = "0xE592427A0AEce92De3Edee1F18E0157C05861564"

# Token addresses on Polygon
TOKENS = {
    'WETH': '0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619',
    'WMATIC': '0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270',
    'WBTC': '0x1BFD67037B42Cf73acF2047067bd4F2C47D9BfD6',
    'USDC': '0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174',
    'USDT': '0xc2132D31c914a87C6611C10748AEb04B58e8F'
}

# Flashloan configuration
AAVE_LENDING_POOL = "0x8dFf5E27EA6b7AC08EbFdf9eB090F32ee9a30fcf"
BALANCER_VAULT = "0xBA12222222228d8Ba445958a75a0704d566BF2C8"

# Websocket configuration
BINANCE_WSS_URL = "wss://stream.binance.com:9443/ws"
OKX_WSS_URL = "wss://ws.okx.com:8443/ws/v5/public"

# Price calculation settings
PRICE_IMPACT_THRESHOLD = float(os.getenv('PRICE_IMPACT_THRESHOLD', '1.0'))  # Maximum allowed price impact in %
MIN_LIQUIDITY_THRESHOLD = float(os.getenv('MIN_LIQUIDITY_THRESHOLD', '50000'))  # Minimum liquidity in USDT
MOVING_AVERAGE_PERIODS = [5, 15, 30]  # Moving average periods for price analysis

# Advanced Strategy Parameters
VOLATILITY_WEIGHT = float(os.getenv('VOLATILITY_WEIGHT', '0.3'))
VOLUME_WEIGHT = float(os.getenv('VOLUME_WEIGHT', '0.25'))
LIQUIDITY_WEIGHT = float(os.getenv('LIQUIDITY_WEIGHT', '0.25'))
RSI_OVERSOLD = float(os.getenv('RSI_OVERSOLD', '30'))
RSI_OVERBOUGHT = float(os.getenv('RSI_OVERBOUGHT', '70'))
BOLLINGER_PERIOD = int(os.getenv('BOLLINGER_PERIOD', '20'))
BOLLINGER_STD = float(os.getenv('BOLLINGER_STD', '2'))
MAX_POSITION_SIZE = float(os.getenv('MAX_POSITION_SIZE', '5000'))  # Maximum position size in USDT

# Gas Price Configuration
MAX_GAS_PRICE_GWEI = int(os.getenv('MAX_GAS_PRICE_GWEI', '100'))

# Cross-Chain Bridge Configuration
ACROSS_ROUTER = os.getenv('ACROSS_ROUTER', '0x69C5BA5efd8562417396DA065EDf29E6C3cFdAe1')
SOCKET_ROUTER = os.getenv('SOCKET_ROUTER', '0x3a23F943181408EAC424116Af7b7790c94Cb97a5')
STARGATE_ROUTER = os.getenv('STARGATE_ROUTER', '0x8731d54E9D02c286767d56ac03e8037C07e01e98')
LAYERZERO_ENDPOINT = os.getenv('LAYERZERO_ENDPOINT', '0x3c2269811836af69497E5F486A85D7316753cf62')

# Monitoring & Alert Configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL')
ALERT_MIN_PROFIT = float(os.getenv('ALERT_MIN_PROFIT', '10.0'))  # Minimum profit to send alert
HEALTH_CHECK_INTERVAL = int(os.getenv('HEALTH_CHECK_INTERVAL', '60'))  # Seconds

# Router ABIs
ROUTER_ABI = [
    # Factory methods
    {
        "inputs": [{"internalType": "address", "name": "_factory", "type": "address"}, {"internalType": "address", "name": "_WETH", "type": "address"}],
        "stateMutability": "nonpayable",
        "type": "constructor"
    },
    # Core swap methods
    {
        "inputs": [
            {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
            {"internalType": "uint256", "name": "amountOutMin", "type": "uint256"},
            {"internalType": "address[]", "name": "path", "type": "address[]"},
            {"internalType": "address", "name": "to", "type": "address"},
            {"internalType": "uint256", "name": "deadline", "type": "uint256"}
        ],
        "name": "swapExactTokensForTokens",
        "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    # Price query methods
    {
        "inputs": [
            {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
            {"internalType": "address[]", "name": "path", "type": "address[]"}
        ],
        "name": "getAmountsOut",
        "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "amountOut", "type": "uint256"},
            {"internalType": "address[]", "name": "path", "type": "address[]"}
        ],
        "name": "getAmountsIn",
        "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}],
        "stateMutability": "view",
        "type": "function"
    }
]

# Uniswap V3 specific router ABI (for future use)
ROUTER_ABI_V3 = [
    {
        "inputs": [
            {
                "components": [
                    {"internalType": "address", "name": "tokenIn", "type": "address"},
                    {"internalType": "address", "name": "tokenOut", "type": "address"},
                    {"internalType": "uint24", "name": "fee", "type": "uint24"},
                    {"internalType": "address", "name": "recipient", "type": "address"},
                    {"internalType": "uint256", "name": "deadline", "type": "uint256"},
                    {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
                    {"internalType": "uint256", "name": "amountOutMinimum", "type": "uint256"},
                    {"internalType": "uint160", "name": "sqrtPriceLimitX96", "type": "uint160"}
                ],
                "internalType": "struct ISwapRouter.ExactInputSingleParams",
                "name": "params",
                "type": "tuple"
            }
        ],
        "name": "exactInputSingle",
        "outputs": [{"internalType": "uint256", "name": "amountOut", "type": "uint256"}],
        "stateMutability": "payable",
        "type": "function"
    }
]
