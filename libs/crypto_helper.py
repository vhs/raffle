import hashlib
import logging
import time
from functools import cache

import requests

logger = logging.getLogger()
deb = logger.debug
info = logger.info
warn = logger.warn
err = logger.error


def get_hash(string):
    assert isinstance(string, str)

    # Specify hash algorithm used through script
    return hashlib.sha256(string.encode()).digest()


def hash_xor(hash_1, hash_2):
    "xor function used to compare dice roll with user digests"

    assert isinstance(hash_1, bytes) and isinstance(hash_2, bytes)
    assert len(hash_1) == len(hash_2)

    return bytes([a ^ b for a, b in zip(hash_1, hash_2)])


# Drand configuration (League of Entropy mainnet - default network)
DRAND_API_URL = "https://api.drand.sh"
DRAND_PERIOD = 30  # seconds between rounds
DRAND_GENESIS_TIME = 1595431050  # July 21, 2020 14:37:30 UTC
# Genesis time fetched from https://api.drand.sh/info


def _get_drand_round(timestamp):
    """Convert a UNIX timestamp to the corresponding Drand round number."""
    return int((timestamp - DRAND_GENESIS_TIME) // DRAND_PERIOD)


# Cache decorator to force python to cache calls to remote service
@cache
def get_drand_hash(timestamp):
    """Get the most recent Drand beacon round published after the given timestamp.

    Returns dict with 'hash' (bytes) and 'timestamp' (int UNIX epoch).
    """
    target_round = _get_drand_round(timestamp)
    # Fetch the NEXT round so the timestamp is guaranteed to be >= timestamp
    fetch_round = target_round + 1
    deb("Getting Drand hash, round: %s" % fetch_round)

    try:
        resp = requests.get(
            f"{DRAND_API_URL}/public/{fetch_round}",
            timeout=5,
        )
        resp.raise_for_status()
        beacon = resp.json()
    except:
        err("Drand get error")
        raise

    deb("Chosen Drand: %s" % beacon)

    beacon_round = beacon["round"]
    randomness = bytes.fromhex(beacon["randomness"])
    beacon_timestamp = DRAND_GENESIS_TIME + (beacon_round * DRAND_PERIOD)

    return {"hash": randomness, "timestamp": beacon_timestamp}


# Cache decorator to force python to cache calls to remote service
@cache
def get_bitcoin_hash(timestamp):
    "Get list of coins from https://blockchain.info/blocks/[ts_in_ms]?format=json"

    try:
        blockchain_url = "https://blockchain.info/blocks/%s" % str(
            (timestamp + 1000) * 1000
        )

        deb("Getting blockchain hash, url: %s" % blockchain_url)

        blocks = requests.get(
            blockchain_url, params={"format": "json"}, timeout=15
        ).json()
    except:
        err("Bitcoin get error")
        raise

    # Loop through the received blocks until we have one matching the timeframe
    for i in blocks:
        closest = i

        if i["time"] < timestamp:
            break

    deb("Chosen blockchain: %s" % closest)

    closest_hash = bytes.fromhex(closest["hash"])
    closest_time = int(closest["time"])

    return {"hash": closest_hash, "timestamp": closest_time}


# May as well cache here too, saves a bit of CPU
@cache
def get_dice_roll(close_time):
    bitcoin = get_bitcoin_hash(close_time)
    drand = get_drand_hash(close_time)

    info("Bitcoin Timestamp: %s" % time.ctime(bitcoin["timestamp"]))
    info("Provided Timestamp: %s" % time.ctime(close_time))
    info("Drand Timestamp: %s" % time.ctime(drand["timestamp"]))

    # Check that the timestamps are in the right order:
    # Bitcoin, close time, Drand
    assert bitcoin["timestamp"] <= close_time <= drand["timestamp"]

    # Check that the whole range is within 30 mins.
    assert drand["timestamp"] - bitcoin["timestamp"] <= 3600

    deb(
        "Time delta between two randomness: %s"
        % (drand["timestamp"] - bitcoin["timestamp"])
    )

    return get_hash(bitcoin["hash"].hex() + drand["hash"].hex())
