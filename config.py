from dotenv import load_dotenv
import os

load_dotenv()

# Exchange API Keys
BINANCE_API_KEY = os.getenv('BINANCE_API_KEY')
BINANCE_SECRET_KEY = os.getenv('BINANCE_SECRET_KEY')
OKX_API_KEY = os.getenv('OKX_API_KEY')
OKX_SECRET_KEY = os.getenv('OKX_SECRET_KEY')

# Blockchain RPC URLs
POLYGON_RPC_URL = os.getenv('POLYGON_RPC_URL', 'https://polygon-rpc.com')
POLYGON_WSS_URL = os.getenv('POLYGON_WSS_URL', 'wss://polygon-rpc.com')

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
    'USDT': '0xc2132D05D31c914a87C6611C10748AEb04B58e8F'
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
