from .settings import *  # noqa

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",  # Use in-memory SQLite database
    }
}

# Disable rate limiting for tests
RATELIMIT_ENABLE = False

# Disable real Web3 connections
ETHEREUM_NODE_URL = "http://dummy"
PRIVATE_KEY = "0" * 64
CHAIN_ID = 1
FAUCET_AMOUNT = 0.0001
FAUCET_INTERVAL_MIN = 1
