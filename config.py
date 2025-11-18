from dotenv import load_dotenv
import os
from web3 import Web3


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
        'chain_id': 137,
        'native_token': 'MATIC',
        'explorer': 'https://polygonscan.com'
    },
    'arbitrum': {
        'rpc': ARBITRUM_RPC_URL,
        'wss': ARBITRUM_WSS_URL,
        'chain_id': 42161,
        'native_token': 'ETH',
        'explorer': 'https://arbiscan.io'
    },
    'optimism': {
        'rpc': OPTIMISM_RPC_URL,
        'wss': OPTIMISM_WSS_URL,
        'chain_id': 10,
        'native_token': 'ETH',
        'explorer': 'https://optimistic.etherscan.io'
    },
    'bsc': {
        'rpc': BSC_RPC_URL,
        'wss': BSC_WSS_URL,
        'chain_id': 56,
        'native_token': 'BNB',
        'explorer': 'https://bscscan.com'
    },
    'base': {
        'rpc': BASE_RPC_URL,
        'wss': BASE_WSS_URL,
        'chain_id': 8453,
        'native_token': 'ETH',
        'explorer': 'https://basescan.org'
    },
    'linea': {
        'rpc': LINEA_RPC_URL,
        'wss': LINEA_WSS_URL,
        'chain_id': 59144,
        'native_token': 'ETH',
        'explorer': 'https://lineascan.build'
    },
    'avalanche': {
        'rpc': AVALANCHE_RPC_URL,
        'wss': AVALANCHE_WSS_URL,
        'chain_id': 43114,
        'native_token': 'AVAX',
        'explorer': 'https://snowtrace.io'
    },
    'ethereum': {
        'rpc': ETHEREUM_RPC_URL,
        'wss': ETHEREUM_WSS_URL,
        'chain_id': 1,
        'native_token': 'ETH',
        'explorer': 'https://etherscan.io'
    }
}

# Wallet Configuration
WALLET_ADDRESS = Web3.to_checksum_address(os.getenv('WALLET_ADDRESS'))
PRIVATE_KEY = os.getenv('PRIVATE_KEY')

# Trading Parameters
MIN_PROFIT_THRESHOLD = float(os.getenv('MIN_PROFIT_THRESHOLD', '0.5'))  # Minimum profit percentage

# Separate limits for CEX and DEX trading
MAX_TRADE_AMOUNT_CEX = float(os.getenv('MAX_TRADE_AMOUNT_CEX', os.getenv('MAX_TRADE_AMOUNT', '1000')))  # CEX trade limit in USDT
MAX_TRADE_AMOUNT_DEX = float(os.getenv('MAX_TRADE_AMOUNT_DEX', os.getenv('MAX_TRADE_AMOUNT', '1000')))  # DEX trade limit in USDT

# Keep backward compatibility
MAX_TRADE_AMOUNT = float(os.getenv('MAX_TRADE_AMOUNT', '1000'))  # Fallback for both if not specified

GAS_LIMIT = int(os.getenv('GAS_LIMIT', '300000'))
SLIPPAGE_TOLERANCE = float(os.getenv('SLIPPAGE_TOLERANCE', '0.5'))

# Trading pairs to monitor
TRADING_PAIRS = {
    'CEX': ['USDT/USD', 'ETH/USDT', 'BTC/USDT', 'MATIC/USDT'],
    'DEX': ['WETH/USDC', 'WMATIC/USDC', 'WBTC/USDC']
}

# Multi-Chain DEX Configuration
# Organized by chain for easy expansion

# DEX Routers by Chain
DEX_ROUTERS = {
    'polygon': {
        'quickswap': '0xa5E0829CaCEd8fFDD4De3c43696c57F7D7A678ff',
        'sushiswap': '0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506',
        'uniswap_v3': '0xE592427A0AEce92De3Edee1F18E0157C05861564'
    },
    'ethereum': {
        'uniswap_v2': '0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D',
        'uniswap_v3': '0xE592427A0AEce92De3Edee1F18E0157C05861564',
        'sushiswap': '0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F',
    },
    'arbitrum': {
        'uniswap_v3': '0xE592427A0AEce92De3Edee1F18E0157C05861564',
        'sushiswap': '0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506',
        'camelot': '0xc873fEcbd354f5A56E00E710B90EF4201db2448d'
    },
    'optimism': {
        'uniswap_v3': '0xE592427A0AEce92De3Edee1F18E0157C05861564',
        'sushiswap': '0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506',
        'velodrome': '0xa132DAB612dB5cB9fC9Ac426A0Cc215A3423F9c9'
    },
    'bsc': {
        'pancakeswap': '0x10ED43C718714eb63d5aA57B78B54704E256024E',
        'sushiswap': '0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506',
        'biswap': '0x3a6d8cA21D1CF76F653A67577FA0D27453350dD8'
    }
}

# DEX Factories by Chain (for getting pair addresses)
DEX_FACTORIES = {
    'polygon': {
        'quickswap': '0x5757371414417b8C6CAad45bAeF941aBc7d3Ab32',
        'sushiswap': '0xc35DADB65012eC5796536bD9864eD8773aBc74C4',
        'uniswap_v3': '0x1F98431c8aD98523631AE4a59f267346ea31F984'
    },
    'ethereum': {
        'uniswap_v2': '0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f',
        'uniswap_v3': '0x1F98431c8aD98523631AE4a59f267346ea31F984',
        'sushiswap': '0xC0AEe478e3658e2610c5F7A4A2E1777cE9e4f2Ac'
    },
    'arbitrum': {
        'uniswap_v3': '0x1F98431c8aD98523631AE4a59f267346ea31F984',
        'sushiswap': '0xc35DADB65012eC5796536bD9864eD8773aBc74C4',
        'camelot': '0x6EcCab422D763aC031210895C81787E87B43A652'
    },
    'optimism': {
        'uniswap_v3': '0x1F98431c8aD98523631AE4a59f267346ea31F984',
        'sushiswap': '0xc35DADB65012eC5796536bD9864eD8773aBc74C4',
        'velodrome': '0x25CbdDb98b35ab1FF77413456B31EC81A6B6B746'
    },
    'bsc': {
        'pancakeswap': '0xcA143Ce32Fe78f1f7019d7d551a6402fC5350c73',
        'sushiswap': '0xc35DADB65012eC5796536bD9864eD8773aBc74C4',
        'biswap': '0x858E3312ed3A876947EA49d572A7C42DE08af7EE'
    }
}

# Token addresses by Chain
TOKENS_BY_CHAIN = {
    'polygon': {
        'WETH': '0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619',
        'WMATIC': '0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270',
        'WBTC': '0x1BFD67037B42Cf73acF2047067bd4F2C47D9BfD6',
        'USDC': '0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174',
        'USDT': '0xc2132D05D31c914a87C6611C10748AEb04B58e8F',
        'DAI': '0x8f3Cf7ad23Cd3CaDbD9735AFf958023239c6A063'
    },
    'ethereum': {
        'WETH': '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',
        'WBTC': '0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599',
        'USDC': '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48',
        'USDT': '0xdAC17F958D2ee523a2206206994597C13D831ec7',
        'DAI': '0x6B175474E89094C44Da98b954EedeAC495271d0F'
    },
    'arbitrum': {
        'WETH': '0x82aF49447D8a07e3bd95BD0d56f35241523fBab1',
        'WBTC': '0x2f2a2543B76A4166549F7aaB2e75Bef0aefC5B0f',
        'USDC': '0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8',
        'USDT': '0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9',
        'DAI': '0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1',
        'ARB': '0x912CE59144191C1204E64559FE8253a0e49E6548'
    },
    'optimism': {
        'WETH': '0x4200000000000000000000000000000000000006',
        'WBTC': '0x68f180fcCe6836688e9084f035309E29Bf0A2095',
        'USDC': '0x7F5c764cBc14f9669B88837ca1490cCa17c31607',
        'USDT': '0x94b008aA00579c1307B0EF2c499aD98a8ce58e58',
        'DAI': '0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1',
        'OP': '0x4200000000000000000000000000000000000042'
    },
    'bsc': {
        'WBNB': '0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c',
        'WETH': '0x2170Ed0880ac9A755fd29B2688956BD959F933F8',
        'WBTC': '0x7130d2A12B9BCbFAe4f2634d864A1Ee1Ce3Ead9c',
        'USDC': '0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d',
        'USDT': '0x55d398326f99059fF775485246999027B3197955',
        'BUSD': '0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56'
    }
}

# Backward compatibility - use Polygon tokens as default
TOKENS = TOKENS_BY_CHAIN['polygon']

# Legacy router addresses (for backward compatibility)
QUICKSWAP_ROUTER = DEX_ROUTERS['polygon']['quickswap']
SUSHISWAP_ROUTER = DEX_ROUTERS['polygon']['sushiswap']
UNISWAP_V3_ROUTER = DEX_ROUTERS['polygon']['uniswap_v3']

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