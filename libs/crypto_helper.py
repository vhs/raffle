from functools import cache
import hashlib
import requests

import logging
l = logging.getLogger()
deb=l.debug
info=l.info
warn=l.warn
err=l.error
parser,args=None,None
def get_hash(string):
    assert isinstance(string, str)
    return hashlib.sha256(string.encode()).digest() # Specify hash algorithm used through script
def hash_xor(hash_1, hash_2): # xor function used to compare dice roll with user digests
    assert isinstance(hash_1, bytes) and isinstance(hash_2, bytes)
    assert len(hash_1) == len(hash_2)
    return bytes([a ^ b for a, b in zip(hash_1, hash_2)])
def get_user_hashes(key_hash,entrants_list): # Generate a list of tuples with the user key
    assert isinstance(key_hash, bytes)
    assert isinstance(entrants_list,list)
    return [(entrant,get_hash(entrant+" "+key_hash.hex())) for entrant in entrants_list]
def get_winning_order(key_hash,dice_hash,entrants_list): # Generate a sorted list of the entrants, using lowest value of xor of their digest and the roll digest
    assert isinstance(key_hash, bytes) and isinstance(dice_hash,bytes)
    assert isinstance(entrants_list, list)
    # TODO: refactor next line for readability as per Mike Kes
    return sorted([(name, hash_xor(digest,get_hash(key_hash.hex()+" "+dice_hash.hex()))) 
                   for name, digest in get_user_hashes(key_hash,entrants_list)],key=lambda x: x[1])
#Cache decorator here get's python to just handle caching calls to remote service
@cache
def get_nist_hash(timestamp):
    nist_url='https://beacon.nist.gov/beacon/2.0/pulse/time/'+str(timestamp)
    deb(nist_url)
    try:
        pulse = requests.get(nist_url).json()['pulse']['outputValue']
    except:
        err("NIST Pulse get error")
        raise
    return bytes.fromhex(pulse)
#Cache decorator here get's python to just handle caching calls to remote service
@cache
def get_bitcoin_hash(timestamp): # Get list of coins from https://blockchain.info/blocks/[ts_in_ms]?format=json
    try:
        #print('https://blockchain.info/blocks/'+str((timestamp+1000)*1000))
        blocks = requests.get('https://blockchain.info/blocks/'+str((timestamp+1000)*1000), params={'format':'json'}).json()

    except:
        err("Bitcoin get error")
        raise
    #just_block_times=[ sub['time'] for sub in blocks ]
    for i in blocks:
        closest=i
        if i['time'] < timestamp:
            break
    return bytes.fromhex(closest['hash'])
