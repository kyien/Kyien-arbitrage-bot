"""
Logging Configuration for Arbitrage Bot
Prevents disk fill-up with rotation and size limits
"""

import os
import sys
from loguru import logger
from pathlib import Path


def setup_logging(
    log_dir: str = "/var/log/arbitrage-bot",
    max_size: str = "100 MB",
    retention: str = "7 days",
    rotation: str = "daily",
    compression: str = "gz",
    enable_console: bool = True
):
    """
    Configure logging with rotation to prevent disk fill-up

    Args:
        log_dir: Directory for log files
        max_size: Maximum size before rotation (e.g., "100 MB")
        retention: How long to keep logs (e.g., "7 days")
        rotation: When to rotate ("daily", "100 MB", "1 week")
        compression: Compression format ("gz", "zip", "tar.gz")
        enable_console: Whether to log to console (stdout)
    """
    # Remove default handler
    logger.remove()

    # Create log directory if it doesn't exist
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    Path(f"{log_dir}/trades").mkdir(parents=True, exist_ok=True)
    Path(f"{log_dir}/errors").mkdir(parents=True, exist_ok=True)
    Path(f"{log_dir}/alerts").mkdir(parents=True, exist_ok=True)

    # Console handler (for development and debugging)
    if enable_console:
        logger.add(
            sys.stdout,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                   "<level>{level: <8}</level> | "
                   "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
                   "<level>{message}</level>",
            level="INFO",
            colorize=True
        )

    # Main application log (INFO and above)
    logger.add(
        f"{log_dir}/bot.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        level="INFO",
        rotation=rotation,
        retention=retention,
        compression=compression,
        enqueue=True,  # Thread-safe
        backtrace=True,
        diagnose=True
    )

    # Debug log (DEBUG and above) - smaller retention
    logger.add(
        f"{log_dir}/debug.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        level="DEBUG",
        rotation=max_size,
        retention="3 days",
        compression=compression,
        enqueue=True
    )

    # Error log (ERROR and above) - longer retention
    logger.add(
        f"{log_dir}/errors/error.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}\n{extra}",
        level="ERROR",
        rotation=rotation,
        retention="30 days",
        compression=compression,
        enqueue=True,
        backtrace=True,
        diagnose=True
    )

    # Trade execution log (structured for analysis)
    logger.add(
        f"{log_dir}/trades/trades.log",
        format="{{time:YYYY-MM-DD HH:mm:ss}} | {{extra[trade_type]}} | {{message}}",
        level="INFO",
        rotation=rotation,
        retention="90 days",
        compression=compression,
        enqueue=True,
        filter=lambda record: "trade_type" in record["extra"]
    )

    # Alert log (for monitoring system)
    logger.add(
        f"{log_dir}/alerts/alerts.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
        level="WARNING",
        rotation=rotation,
        retention="14 days",
        compression=compression,
        enqueue=True
    )

    # Performance log (for optimization)
    logger.add(
        f"{log_dir}/performance.log",
        format="{{time:YYYY-MM-DD HH:mm:ss}} | {{extra[metric]}} | {{message}}",
        level="INFO",
        rotation=rotation,
        retention="7 days",
        compression=compression,
        enqueue=True,
        filter=lambda record: "metric" in record["extra"]
    )

    logger.info("Logging configured successfully")
    logger.info(f"  Log directory: {log_dir}")
    logger.info(f"  Rotation: {rotation}")
    logger.info(f"  Retention: {retention}")
    logger.info(f"  Compression: {compression}")


def log_trade(
    trade_type: str,
    chain: str,
    token_pair: str,
    profit: float,
    tx_hash: str = None,
    **kwargs
):
    """
    Log trade execution (goes to trades.log)

    Args:
        trade_type: Type of trade (DEX_ARBITRAGE, CEX_ARBITRAGE, LIQUIDATION)
        chain: Blockchain chain
        token_pair: Trading pair
        profit: Profit amount
        tx_hash: Transaction hash
        **kwargs: Additional metadata
    """
    message = f"{chain} | {token_pair} | Profit: ${profit:.2f}"
    if tx_hash:
        message += f" | TX: {tx_hash}"

    for key, value in kwargs.items():
        message += f" | {key}: {value}"

    logger.bind(trade_type=trade_type).info(message)


def log_performance(metric: str, value: float, unit: str = "ms", **kwargs):
    """
    Log performance metric (goes to performance.log)

    Args:
        metric: Metric name (e.g., "execution_time", "rpc_latency")
        value: Metric value
        unit: Unit of measurement
        **kwargs: Additional context
    """
    message = f"{metric}: {value:.2f}{unit}"

    for key, val in kwargs.items():
        message += f" | {key}: {val}"

    logger.bind(metric=metric).info(message)


def get_log_size(log_dir: str = "/var/log/arbitrage-bot") -> dict:
    """
    Get current log directory size

    Args:
        log_dir: Log directory path

    Returns:
        Dictionary with size information
    """
    total_size = 0
    file_count = 0

    log_path = Path(log_dir)

    if not log_path.exists():
        return {'total_size_mb': 0, 'file_count': 0, 'error': 'Directory does not exist'}

    for file in log_path.rglob('*'):
        if file.is_file():
            total_size += file.stat().st_size
            file_count += 1

    total_size_mb = total_size / (1024 * 1024)

    return {
        'total_size_mb': round(total_size_mb, 2),
        'file_count': file_count,
        'log_dir': str(log_dir)
    }


def cleanup_old_logs(log_dir: str = "/var/log/arbitrage-bot", days: int = 30):
    """
    Manually cleanup logs older than specified days

    Args:
        log_dir: Log directory path
        days: Delete logs older than this many days
    """
    import time

    log_path = Path(log_dir)
    if not log_path.exists():
        logger.warning(f"Log directory does not exist: {log_dir}")
        return

    cutoff = time.time() - (days * 86400)
    deleted_count = 0
    freed_mb = 0

    for file in log_path.rglob('*.log*'):
        if file.is_file() and file.stat().st_mtime < cutoff:
            size_mb = file.stat().st_size / (1024 * 1024)
            try:
                file.unlink()
                deleted_count += 1
                freed_mb += size_mb
                logger.debug(f"Deleted old log: {file.name} ({size_mb:.2f}MB)")
            except Exception as e:
                logger.error(f"Failed to delete {file.name}: {str(e)}")

    logger.info(f"Cleanup complete: Deleted {deleted_count} files, freed {freed_mb:.2f}MB")


if __name__ == "__main__":
    # Test logging configuration
    setup_logging(
        log_dir="./logs",
        max_size="10 MB",
        retention="3 days",
        rotation="1 MB"
    )

    logger.info("Testing logging system...")
    logger.debug("Debug message - goes to debug.log")
    logger.warning("Warning message - goes to all logs")
    logger.error("Error message - goes to error.log too")

    # Test trade logging
    log_trade(
        trade_type="DEX_ARBITRAGE",
        chain="polygon",
        token_pair="WETH/USDC",
        profit=15.50,
        tx_hash="0x1234...",
        gas_used=250000
    )

    # Test performance logging
    log_performance(
        metric="execution_time",
        value=85.5,
        unit="ms",
        chain="polygon",
        success=True
    )

    # Check log sizes
    size_info = get_log_size("./logs")
    logger.info(f"Log directory size: {size_info}")

    logger.info("Logging test complete!")
