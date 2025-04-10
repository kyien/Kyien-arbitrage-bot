from brownie import accounts, config, network, Contract, project
from pathlib import Path
import json
import os
from loguru import logger

def main():
    """Deploy the arbitrage contracts to multiple chains"""
    # Load account using private key from environment
    account = accounts.add(config.PRIVATE_KEY)
    
    # Get the contract directory
    contracts_dir = Path("contracts")
    
    # Build the project if it doesn't exist
    if not os.path.exists("build/contracts"):
        project.build(contracts_dir)
    
    # Dictionary of networks and their router addresses
    network_configs = {
        'polygon': {
            'network_name': 'polygon-main',
            'uniswap_router': '0xE592427A0AEce92De3Edee1F18E0157C05861564',  # Uniswap v3
            'sushiswap_router': '0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506'  # Sushiswap
        },
        'arbitrum': {
            'network_name': 'arbitrum-main',
            'uniswap_router': '0xE592427A0AEce92De3Edee1F18E0157C05861564',  # Uniswap v3
            'sushiswap_router': '0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506'  # Sushiswap
        },
        'optimism': {
            'network_name': 'optimism-main',
            'uniswap_router': '0xE592427A0AEce92De3Edee1F18E0157C05861564',  # Uniswap v3
            'sushiswap_router': '0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506'  # Sushiswap
        },
        'bsc': {
            'network_name': 'bsc-main',
            'uniswap_router': '0x10ED43C718714eb63d5aA57B78B54704E256024E',  # PancakeSwap
            'sushiswap_router': '0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506'  # Sushiswap
        }
    }
    
    # Deploy contracts to each network
    deployed_contracts = {}
    
    for chain, chain_config in network_configs.items():
        try:
            # Connect to the network
            network.connect(chain_config['network_name'])
            
            logger.info(f"Deploying to {chain}...")
            
            # Deploy the contract
            arbitrage_executor = deploy_arbitrage_executor(
                account,
                chain_config['uniswap_router'],
                chain_config['sushiswap_router']
            )
            
            # Save the deployed address
            deployed_contracts[chain] = {
                'arbitrage_executor': arbitrage_executor.address
            }
            
            # Disconnect from the network
            network.disconnect()
            
        except Exception as e:
            logger.error(f"Error deploying to {chain}: {str(e)}")
            network.disconnect()
    
    # Save deployed contract addresses to a file
    with open('deployed_contracts.json', 'w') as f:
        json.dump(deployed_contracts, f, indent=4)
    
    logger.info(f"Deployment complete. Addresses saved to deployed_contracts.json")

def deploy_arbitrage_executor(account, uniswap_router, sushiswap_router):
    """Deploy the ArbitrageExecutor contract"""
    # Import the contract
    ArbitrageExecutor = project.get_contract('ArbitrageExecutor')
    
    # Deploy the contract
    arbitrage_executor = ArbitrageExecutor.deploy(
        uniswap_router,
        sushiswap_router,
        {'from': account},
        publish_source=True  # Verify the contract on Etherscan
    )
    
    logger.info(f"ArbitrageExecutor deployed at: {arbitrage_executor.address}")
    
    return arbitrage_executor

if __name__ == "__main__":
    main()
