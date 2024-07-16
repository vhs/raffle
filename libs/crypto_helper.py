import hashlib
import logging
import time
from functools import cache

import dateutil.parser
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


# Cache decorator to force python to cache calls to remote service
@cache
def get_nist_hash(timestamp):
    timestamp_ms = timestamp * 1000
    nist_url = f"https://beacon.nist.gov/beacon/2.0/pulse/time/{timestamp_ms}"

    deb("Getting NIST hash, url: %s" % nist_url)

    try:
        pulse = requests.get(
            nist_url,
            timeout=5,
        ).json()
    except:
        err("NIST Pulse get error")

        raise

    deb("Chosen NIST: %s" % pulse)

    pulse_output = bytes.fromhex(pulse["pulse"]["outputValue"])
    pulse_timestamp = pulse["pulse"]["timeStamp"]
    parsed_timestamp = dateutil.parser.isoparse(pulse_timestamp).timestamp()

    return {"hash": pulse_output, "timestamp": int(parsed_timestamp)}


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
    nist = get_nist_hash(close_time)

    info("Bitcoin Timestamp: %s" % time.ctime(bitcoin["timestamp"]))
    info("Provided Timestamp: %s" % time.ctime(close_time))
    info("NIST Timestamp: %s" % time.ctime(nist["timestamp"]))

    # Check that the timestamps are in the right order:
    # Bitcoin, close time, NIST
    assert bitcoin["timestamp"] <= close_time <= nist["timestamp"]

    # Check that the whole range is within 30 mins.
    assert nist["timestamp"] - bitcoin["timestamp"] <= 3600

    deb(
        "Time delta between two randomeness: %s"
        % (nist["timestamp"] - bitcoin["timestamp"])
    )

    return get_hash(bitcoin["hash"].hex() + nist["hash"].hex())
