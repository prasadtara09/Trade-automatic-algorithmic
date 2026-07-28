"""Runtime configuration for the paper-trading and backtest components."""

import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv, set_key

DOTENV_PATH = Path(os.getenv("FYERS_ENV_FILE") or Path(__file__).resolve().parent / ".env").expanduser().resolve()
load_dotenv(DOTENV_PATH)

# Broker credentials come from .env by default.  On EC2, set only
# FYERS_SECRET_ID and AWS_REGION in .env; the credential values are then read
# from that one AWS Secrets Manager JSON secret.
FYERS_SECRET_FIELDS = (
    "FYERS_CLIENT_ID",
    "FYERS_SECRET_KEY",
    "FYERS_REDIRECT_URI",
    "FYERS_ACCESS_TOKEN",
)
FYERS_SECRET_ID = (os.getenv("FYERS_SECRET_ID") or "").strip()
AWS_REGION = (os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "").strip() or None
# Optional shared state for separate scanner and stream containers. The EC2
# instance profile supplies AWS credentials; no access key belongs in .env.
S3_BUCKET = (os.getenv("S3_BUCKET") or "").strip()
S3_TARGETS_KEY = (os.getenv("S3_TARGETS_KEY") or "state/swing_rotation_targets.csv").strip().lstrip("/")


class FyersSecretError(RuntimeError):
    """Raised when the configured FYERS credential source cannot be used."""


class S3TargetsError(RuntimeError):
    """Raised when the configured shared target basket cannot be accessed."""


def _secrets_manager_client():
    try:
        import boto3
    except ImportError as error:
        raise FyersSecretError(
            "FYERS_SECRET_ID is set, but boto3 is unavailable. Run: pip install -r requirements.txt"
        ) from error
    return boto3.client("secretsmanager", region_name=AWS_REGION)


def _s3_client():
    try:
        import boto3
    except ImportError as error:
        raise S3TargetsError("S3_BUCKET is set, but boto3 is unavailable. Run: pip install -r requirements.txt") from error
    return boto3.client("s3", region_name=AWS_REGION)


def s3_targets_enabled() -> bool:
    """Return whether the scanner and stream should share targets through S3."""
    return bool(S3_BUCKET)


def upload_s3_targets(source: Path) -> None:
    """Upload the completed weekly target CSV to the configured private bucket."""
    if not s3_targets_enabled():
        return
    if not source.is_file():
        raise S3TargetsError(f"Target basket does not exist: {source}")
    try:
        _s3_client().upload_file(
            str(source),
            S3_BUCKET,
            S3_TARGETS_KEY,
            ExtraArgs={"ContentType": "text/csv"},
        )
    except S3TargetsError:
        raise
    except Exception as error:
        raise S3TargetsError(
            f"Unable to upload targets to s3://{S3_BUCKET}/{S3_TARGETS_KEY} ({error.__class__.__name__})."
        ) from error


def download_s3_targets(destination: Path) -> None:
    """Atomically download the current weekly target CSV from the configured bucket."""
    if not s3_targets_enabled():
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".download")
    try:
        _s3_client().download_file(S3_BUCKET, S3_TARGETS_KEY, str(temporary))
        temporary.replace(destination)
    except S3TargetsError:
        raise
    except Exception as error:
        temporary.unlink(missing_ok=True)
        raise S3TargetsError(
            f"Unable to download targets from s3://{S3_BUCKET}/{S3_TARGETS_KEY} ({error.__class__.__name__})."
        ) from error


def _parse_fyers_secret(secret_string: str) -> dict[str, str]:
    try:
        payload: Any = json.loads(secret_string)
    except json.JSONDecodeError as error:
        raise FyersSecretError("The FYERS AWS secret must contain a JSON object.") from error
    if not isinstance(payload, dict):
        raise FyersSecretError("The FYERS AWS secret must contain a JSON object.")

    values: dict[str, str] = {}
    for field in FYERS_SECRET_FIELDS:
        value = payload.get(field)
        if value is not None and not isinstance(value, str):
            raise FyersSecretError(f"The FYERS AWS secret has a non-text {field} value.")
        values[field] = (value or "").strip()
    return values


def _load_fyers_credentials() -> dict[str, str]:
    if not FYERS_SECRET_ID:
        return {field: (os.getenv(field) or "").strip() for field in FYERS_SECRET_FIELDS}

    try:
        response = _secrets_manager_client().get_secret_value(SecretId=FYERS_SECRET_ID)
    except FyersSecretError:
        raise
    except Exception as error:
        raise FyersSecretError(
            f"Unable to read FYERS_SECRET_ID from AWS Secrets Manager ({error.__class__.__name__})."
        ) from error

    secret_string = response.get("SecretString")
    if not isinstance(secret_string, str):
        raise FyersSecretError("The FYERS AWS secret must be stored as SecretString JSON, not binary data.")
    return _parse_fyers_secret(secret_string)


_FYERS_CREDENTIALS = _load_fyers_credentials()
FYERS_CLIENT_ID = _FYERS_CREDENTIALS["FYERS_CLIENT_ID"]
FYERS_SECRET_KEY = _FYERS_CREDENTIALS["FYERS_SECRET_KEY"]
FYERS_REDIRECT_URI = _FYERS_CREDENTIALS["FYERS_REDIRECT_URI"]
FYERS_ACCESS_TOKEN = _FYERS_CREDENTIALS["FYERS_ACCESS_TOKEN"]


def fyers_credentials() -> dict[str, str]:
    """Return a copy of the active FYERS credentials without logging them."""
    return dict(_FYERS_CREDENTIALS)


def save_fyers_access_token(access_token: str, env_file: Path) -> str:
    """Persist a refreshed token in .env or the configured AWS secret."""
    token = (access_token or "").strip()
    if not token:
        raise FyersSecretError("Refusing to store an empty FYERS access token.")

    if not FYERS_SECRET_ID:
        set_key(str(env_file), "FYERS_ACCESS_TOKEN", token, quote_mode="auto")
        return str(env_file)

    try:
        client = _secrets_manager_client()
        response = client.get_secret_value(SecretId=FYERS_SECRET_ID)
        secret_string = response.get("SecretString")
        if not isinstance(secret_string, str):
            raise FyersSecretError("The FYERS AWS secret must be stored as SecretString JSON, not binary data.")
        payload: Any = json.loads(secret_string)
        if not isinstance(payload, dict):
            raise FyersSecretError("The FYERS AWS secret must contain a JSON object.")
        payload["FYERS_ACCESS_TOKEN"] = token
        client.put_secret_value(SecretId=FYERS_SECRET_ID, SecretString=json.dumps(payload, separators=(",", ":")))
    except FyersSecretError:
        raise
    except Exception as error:
        raise FyersSecretError(
            f"Unable to update FYERS_SECRET_ID in AWS Secrets Manager ({error.__class__.__name__})."
        ) from error

    values = _parse_fyers_secret(json.dumps(payload))
    _FYERS_CREDENTIALS.update(values)
    globals()["FYERS_ACCESS_TOKEN"] = token
    return "AWS Secrets Manager"
# Data WebSocket options.  The conservative default of 200 covers the NIFTY
# 200 universe and stays within the smaller published FYERS subscription cap.
FYERS_WS_LITE_MODE = os.getenv("FYERS_WS_LITE_MODE", "false").strip().lower() in {"1", "true", "yes"}
FYERS_WS_MAX_SYMBOLS = int(os.getenv("FYERS_WS_MAX_SYMBOLS", "200"))
FYERS_WS_RECONNECT_RETRY = int(os.getenv("FYERS_WS_RECONNECT_RETRY", "5"))

# Execution and account settings. LIVE mode is deliberately not the default.
MODE = os.getenv("MODE", "PAPER").upper()
INITIAL_CAPITAL = float(os.getenv("INITIAL_CAPITAL", "100000"))
CAPITAL = INITIAL_CAPITAL
RISK_PER_TRADE = float(os.getenv("RISK_PER_TRADE", "0.005"))
# Maximum simultaneous holdings; set this in .env (for example, 3).
MAX_OPEN_POSITIONS = int(os.getenv("MAX_OPEN_POSITIONS", "5"))
MAX_OPEN_TRADES = MAX_OPEN_POSITIONS
MAX_POSITION_VALUE_PCT = float(os.getenv("MAX_POSITION_VALUE_PCT", "0.20"))
MAX_DAILY_LOSS_PCT = float(os.getenv("MAX_DAILY_LOSS_PCT", "0.03"))
MAX_WEEKLY_LOSS_PCT = float(os.getenv("MAX_WEEKLY_LOSS_PCT", "0.06"))
BROKERAGE_PER_ORDER = float(os.getenv("BROKERAGE_PER_ORDER", "20"))
SLIPPAGE = float(os.getenv("SLIPPAGE", "0.0005"))

# Data and scanner settings.
TIMEFRAME = os.getenv("TIMEFRAME", "15m")
HIGHER_TIMEFRAME = os.getenv("HIGHER_TIMEFRAME", "60min")
UNIVERSE = os.getenv("UNIVERSE", "NIFTY200")
SCAN_INTERVAL = int(os.getenv("SCAN_INTERVAL", "15"))
SCANNER_MAX_SIGNALS = int(os.getenv("SCANNER_MAX_SIGNALS", "20"))
# False lets the scanner download missing candles. Set true for offline runs.
SCANNER_CACHE_ONLY = os.getenv("SCANNER_CACHE_ONLY", "false").strip().lower() in {"1", "true", "yes"}
DATA_PROVIDER = os.getenv("DATA_PROVIDER", "AUTO").upper()

# Intraday session guardrails. Candle timestamps represent the start of a
# 15-minute bar, so the square-off is executed at the 15:15 bar open.
INTRADAY_ONLY = os.getenv("INTRADAY_ONLY", "true").strip().lower() in {"1", "true", "yes"}
# Selective profile: avoid the volatile open and late-session whipsaws.
INTRADAY_ENTRY_START = os.getenv("INTRADAY_ENTRY_START", "10:00")
INTRADAY_LAST_ENTRY = os.getenv("INTRADAY_LAST_ENTRY", "13:45")
INTRADAY_SQUARE_OFF = os.getenv("INTRADAY_SQUARE_OFF", "15:15")
MAX_TRADES_PER_SYMBOL_PER_DAY = int(os.getenv("MAX_TRADES_PER_SYMBOL_PER_DAY", "1"))

# Multi-timeframe trend-and-volume-breakout strategy settings.
EMA_FAST = int(os.getenv("EMA_FAST", "20"))
EMA_SLOW = int(os.getenv("EMA_SLOW", "50"))
HTF_EMA_FAST = int(os.getenv("HTF_EMA_FAST", "20"))
HTF_EMA_SLOW = int(os.getenv("HTF_EMA_SLOW", "50"))
RSI_PERIOD = int(os.getenv("RSI_PERIOD", "14"))
RSI_MIN = float(os.getenv("RSI_MIN", "58"))
RSI_MAX = float(os.getenv("RSI_MAX", "68"))
SHORT_RSI_MIN = float(os.getenv("SHORT_RSI_MIN", "32"))
SHORT_RSI_MAX = float(os.getenv("SHORT_RSI_MAX", "42"))
ADX_PERIOD = int(os.getenv("ADX_PERIOD", "14"))
ADX_MIN = float(os.getenv("ADX_MIN", "25"))
ATR_PERIOD = int(os.getenv("ATR_PERIOD", "14"))
ATR_STOP = float(os.getenv("ATR_STOP", "1.5"))
ATR_TARGET = float(os.getenv("ATR_TARGET", "3.0"))
BREAKOUT_LOOKBACK = int(os.getenv("BREAKOUT_LOOKBACK", "20"))
VOLUME_LOOKBACK = int(os.getenv("VOLUME_LOOKBACK", "20"))
VOLUME_MULTIPLIER = float(os.getenv("VOLUME_MULTIPLIER", "1.75"))
MIN_SIGNAL_SCORE = int(os.getenv("MIN_SIGNAL_SCORE", "90"))
# A breakout must be meaningful but not already too extended, and the candle
# body must show conviction rather than an intrabar spike.
BREAKOUT_MIN_ATR = float(os.getenv("BREAKOUT_MIN_ATR", "0.10"))
BREAKOUT_MAX_ATR = float(os.getenv("BREAKOUT_MAX_ATR", "1.00"))
MIN_CANDLE_BODY_PCT = float(os.getenv("MIN_CANDLE_BODY_PCT", "0.60"))
# Enter only after price retests a confirmed breakout level, rather than on the
# initial breakout candle where false moves are most common.
RETEST_LOOKBACK = int(os.getenv("RETEST_LOOKBACK", "2"))
RETEST_TOLERANCE_ATR = float(os.getenv("RETEST_TOLERANCE_ATR", "0.15"))
RETEST_CLOSE_BUFFER_ATR = float(os.getenv("RETEST_CLOSE_BUFFER_ATR", "0.10"))

# Long-only swing trades are permitted only when the broad market is healthy.
# Optional research filter. It is disabled by default until it improves the
# full-universe out-of-sample result.
SWING_REQUIRE_MARKET_REGIME = os.getenv("SWING_REQUIRE_MARKET_REGIME", "false").strip().lower() in {"1", "true", "yes"}
SWING_MARKET_FAST_EMA = int(os.getenv("SWING_MARKET_FAST_EMA", "50"))
SWING_MARKET_SLOW_EMA = int(os.getenv("SWING_MARKET_SLOW_EMA", "200"))
SWING_REQUIRE_STOCK_LONG_TREND = os.getenv("SWING_REQUIRE_STOCK_LONG_TREND", "false").strip().lower() in {"1", "true", "yes"}
MIN_LOOKBACK = max(EMA_SLOW, BREAKOUT_LOOKBACK, VOLUME_LOOKBACK)

DATABASE = os.getenv("DATABASE", "database/trading.db")
LOGFILE = os.getenv("LOGFILE", "logs/tradebot.log")
