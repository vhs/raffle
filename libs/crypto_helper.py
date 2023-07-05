from functools import cache
import time
import dateutil.parser
import hashlib
import logging
import requests


logger = logging.getLogger()
deb = logger.debug
info = logger.info
warn = logger.warn
err = logger.error


def get_hash(string):
    assert isinstance(string, str)
    return hashlib.sha256(
        string.encode()
    ).digest()  # Specify hash algorithm used through script


def hash_xor(hash_1, hash_2):
    "xor function used to compare dice roll with user digests"
    assert isinstance(hash_1, bytes) and isinstance(hash_2, bytes)
    assert len(hash_1) == len(hash_2)
    return bytes([a ^ b for a, b in zip(hash_1, hash_2)])


# Cache decorator here get's python to just handle caching calls to remote service
@cache
def get_nist_hash(timestamp):
    nist_url = "https://beacon.nist.gov/beacon/2.0/pulse/time/%s" % str(
        timestamp * 1000
    )
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
    pulse_timestamp = dateutil.parser.isoparse(pulse["pulse"]["timeStamp"]).timestamp()
    return {"hash": pulse_output, "timestamp": pulse_timestamp}


# Cache decorator here get's python to just handle caching calls to remote service
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
    # Loop through the received blocks to find the one we're looking for time wise
    for i in blocks:
        closest = i
        if i["time"] < timestamp:
            break
    deb("Chosen blockchain: %s" % closest)
    return {"hash": bytes.fromhex(closest["hash"]), "timestamp": int(closest["time"])}


# May as well cache here too, saves a bit of CPU
@cache
def get_dice_roll(close_time):
    bitcoin = get_bitcoin_hash(close_time)
    nist = get_nist_hash(close_time)
    info("Bitcoin Timestamp: %s" % time.ctime(bitcoin["timestamp"]))
    info("Provided Timestamp: %s" % time.ctime(close_time))
    info("NIST Timestamp: %s" % time.ctime(nist["timestamp"]))
    return get_hash(bitcoin["hash"].hex() + nist["hash"].hex())
