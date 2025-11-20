"""
Flashbots Integration Module

Provides MEV protection via Flashbots for Ethereum mainnet high-value transactions.
Flashbots protects against front-running and sandwich attacks by submitting
transactions to a private relay instead of the public mempool.

Usage:
    - For transactions with profit > $100 on Ethereum
    - For transactions after suspicious activity (potential MEV attacks)
    - For high-priority trades where protection is critical
"""

from web3 import Web3, Account
from web3.exceptions import TransactionFailed
from typing import Dict, Optional, Tuple
import requests
from loguru import logger
import config
import asyncio
from eth_account.messages import encode_defunct


class FlashbotsClient:
    """Flashbots MEV protection client"""

    def __init__(self, ethereum_rpc: str, private_key: str):
        """
        Initialize Flashbots client

        Args:
            ethereum_rpc: Ethereum RPC endpoint
            private_key: Private key for signing transactions
        """
        self.w3 = Web3(Web3.HTTPProvider(ethereum_rpc))
        self.private_key = private_key
        self.account = Account.from_key(private_key)

        # Flashbots endpoints
        self.flashbots_relay = "https://relay.flashbots.net"
        self.flashbots_api = "https://api.flashbots.net"

        # Check connection
        if self.w3.is_connected():
            logger.info("Connected to Ethereum via Flashbots")
        else:
            logger.warning("Failed to connect to Ethereum RPC")

    def can_use_flashbots(self, chain: str) -> bool:
        """
        Check if Flashbots is available for this chain

        Currently only supports Ethereum mainnet.

        Args:
            chain: Blockchain name

        Returns:
            True if Flashbots is available
        """
        return chain.lower() in ['ethereum', 'mainnet', 'eth']

    async def send_bundle(
        self,
        transactions: list,
        target_block: Optional[int] = None,
        min_bid: float = 0.0
    ) -> Optional[str]:
        """
        Send a bundle of transactions to Flashbots

        Args:
            transactions: List of signed transactions
            target_block: Target block number (or None for next block)
            min_bid: Minimum bid in ETH

        Returns:
            Bundle hash if successful
        """
        try:
            if not transactions:
                logger.error("No transactions in bundle")
                return None

            # Get target block
            if target_block is None:
                target_block = self.w3.eth.block_number + 1

            # Create bundle
            bundle = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "eth_sendBundle",
                "params": [
                    {
                        "txs": [tx.rawTransaction.hex() if hasattr(tx, 'rawTransaction') else tx for tx in transactions],
                        "revertingTxHashes": [],
                        "blockNumber": hex(target_block),
                        "minTimestamp": 0,
                        "maxTimestamp": 0
                    }
                ]
            }

            # Sign bundle (Flashbots requires bundle signature)
            signature = self._sign_bundle(bundle)

            # Send to Flashbots relay
            headers = {
                "X-Flashbots-Signature": signature,
                "Content-Type": "application/json"
            }

            response = requests.post(
                f"{self.flashbots_relay}/",
                json=bundle,
                headers=headers,
                timeout=10
            )

            if response.status_code == 200:
                result = response.json()
                if "result" in result:
                    bundle_hash = result["result"]
                    logger.info(f"Bundle sent to Flashbots: {bundle_hash}")
                    return bundle_hash
                elif "error" in result:
                    logger.error(f"Flashbots error: {result['error']}")
                    return None
            else:
                logger.error(f"Flashbots API error: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Error sending bundle to Flashbots: {str(e)}")
            return None

    async def send_private_transaction(
        self,
        signed_tx,
        target_block: Optional[int] = None
    ) -> Optional[str]:
        """
        Send a single transaction via Flashbots private relay

        Args:
            signed_tx: Signed transaction
            target_block: Target block number

        Returns:
            Transaction hash if successful
        """
        try:
            bundle = await self.send_bundle([signed_tx], target_block)
            if bundle:
                # Monitor for inclusion
                return await self._wait_for_bundle_inclusion(bundle)
            return None

        except Exception as e:
            logger.error(f"Error sending private transaction: {str(e)}")
            return None

    async def _wait_for_bundle_inclusion(
        self,
        bundle_hash: str,
        timeout: int = 120
    ) -> Optional[str]:
        """
        Wait for bundle to be included in a block

        Args:
            bundle_hash: Bundle hash
            timeout: Timeout in seconds

        Returns:
            Transaction hash if included
        """
        try:
            start_time = asyncio.get_event_loop().time()

            while asyncio.get_event_loop().time() - start_time < timeout:
                # Check bundle status
                status = await self._get_bundle_status(bundle_hash)

                if status and status.get("inclusion_block"):
                    logger.info(f"Bundle included in block {status['inclusion_block']}")
                    return status.get("txHash")

                await asyncio.sleep(2)

            logger.warning(f"Bundle {bundle_hash} not included within timeout")
            return None

        except Exception as e:
            logger.error(f"Error waiting for bundle: {str(e)}")
            return None

    async def _get_bundle_status(self, bundle_hash: str) -> Optional[Dict]:
        """
        Get bundle status from Flashbots API

        Args:
            bundle_hash: Bundle hash

        Returns:
            Bundle status or None
        """
        try:
            # Sign request
            message = f"GET {self.flashbots_api}/bundle/{bundle_hash}\n{self.w3.eth.block_number}"
            signature = self._sign_message(message)

            headers = {
                "X-Flashbots-Signature": signature,
                "Content-Type": "application/json"
            }

            response = requests.get(
                f"{self.flashbots_api}/bundle/{bundle_hash}",
                headers=headers,
                timeout=10
            )

            if response.status_code == 200:
                return response.json()
            else:
                logger.debug(f"Bundle status check failed: {response.status_code}")
                return None

        except Exception as e:
            logger.debug(f"Error getting bundle status: {str(e)}")
            return None

    def _sign_bundle(self, bundle: Dict) -> str:
        """Sign bundle with private key"""
        try:
            # Flashbots signature format: "0x<signature_hex>"
            message = self._get_bundle_message(bundle)
            signature = self._sign_message(message)
            return signature

        except Exception as e:
            logger.error(f"Error signing bundle: {str(e)}")
            return ""

    def _get_bundle_message(self, bundle: Dict) -> str:
        """Create message for bundle signing"""
        try:
            # Extract relevant bundle info for signing
            txs = bundle["params"][0]["txs"]
            block_number = bundle["params"][0]["blockNumber"]

            # Create message
            message = f"bundle_{block_number}_{len(txs)}"
            return message

        except Exception as e:
            logger.error(f"Error creating bundle message: {str(e)}")
            return ""

    def _sign_message(self, message: str) -> str:
        """Sign a message with private key"""
        try:
            message_hash = encode_defunct(text=message)
            signed = self.account.sign_message(message_hash)
            return signed.signature.hex()

        except Exception as e:
            logger.error(f"Error signing message: {str(e)}")
            return ""


class FlashbotsManager:
    """Manages Flashbots integration for the bot"""

    def __init__(self, ethereum_rpc: str, private_key: str):
        self.client = FlashbotsClient(ethereum_rpc, private_key)
        self.enabled = False
        self.profit_threshold = 100.0  # $100 USD
        self.failure_threshold = 3  # Enable after 3 consecutive failures

    def should_use_flashbots(
        self,
        chain: str,
        profit: float,
        recent_failures: int = 0
    ) -> bool:
        """
        Determine if Flashbots should be used

        Args:
            chain: Blockchain name
            profit: Expected profit in USD
            recent_failures: Number of recent failures

        Returns:
            True if Flashbots should be used
        """
        # Check if chain supports Flashbots
        if not self.client.can_use_flashbots(chain):
            return False

        # Use for high-value trades
        if profit > self.profit_threshold:
            return True

        # Use if we're seeing MEV attacks
        if recent_failures >= self.failure_threshold:
            return True

        return False

    async def send_transaction(
        self,
        signed_tx,
        chain: str,
        profit: float,
        recent_failures: int = 0
    ) -> Optional[str]:
        """
        Send transaction, using Flashbots if appropriate

        Args:
            signed_tx: Signed transaction
            chain: Blockchain name
            profit: Expected profit
            recent_failures: Recent failure count

        Returns:
            Transaction hash if successful
        """
        try:
            # Check if we should use Flashbots
            if self.should_use_flashbots(chain, profit, recent_failures):
                logger.info(
                    f"Using Flashbots for high-value transaction "
                    f"(profit: ${profit:.2f})"
                )
                return await self.client.send_private_transaction(signed_tx)
            else:
                # Send via regular RPC
                return await self._send_regular_transaction(signed_tx)

        except Exception as e:
            logger.error(f"Error sending transaction: {str(e)}")
            return None

    async def _send_regular_transaction(self, signed_tx) -> Optional[str]:
        """Send transaction via regular RPC"""
        try:
            tx_hash = self.client.w3.eth.send_raw_transaction(
                signed_tx.rawTransaction if hasattr(signed_tx, 'rawTransaction') else signed_tx
            )
            return tx_hash.hex()

        except Exception as e:
            logger.error(f"Error sending regular transaction: {str(e)}")
            return None


# Configuration for Flashbots
def create_flashbots_manager(
    ethereum_rpc: Optional[str] = None,
    private_key: Optional[str] = None
) -> Optional[FlashbotsManager]:
    """
    Create a Flashbots manager instance

    Args:
        ethereum_rpc: Ethereum RPC endpoint (or None to use config)
        private_key: Private key (or None to use config)

    Returns:
        FlashbotsManager instance or None if not configured
    """
    try:
        rpc = ethereum_rpc or config.ETHEREUM_RPC_URL
        key = private_key or config.PRIVATE_KEY

        if not rpc or not key:
            logger.warning("Flashbots not configured (missing RPC or private key)")
            return None

        return FlashbotsManager(rpc, key)

    except Exception as e:
        logger.error(f"Error creating Flashbots manager: {str(e)}")
        return None


# Create singleton if configured
flashbots_manager = create_flashbots_manager()
