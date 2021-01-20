#!/usr/bin/env python3

parser,args=None,None
def main():
    import argparse, os
    global parser
    parser = argparse.ArgumentParser(description='Run raffels for VHS. Randomness from Bitcoin and NIST')
    parser.add_argument("post_id", help='the ID from the URL of the post. EG: \'talk.vanhack.ca/t/raffle-welcome-to-2021/11292/18\' the ID is 11292',
                    type=int)
    parser.add_argument("-v", "--verbosity", action="count", default=0,
                    help="increase output verbosity, max 2")
    parser.add_argument("-q", "--quiet", action="count", default=0,
                    help="surpress default output and steps (Not that useful unless dumping XML)")
    parser.add_argument("-x", "--xml", type=str, action="store",
                    help="store data into XML files in CWD with specified prefix")
    parser.add_argument("--close_time_override", type=int,action="store",
                       help="override the close in the poll")
    parser.add_argument("--api_key", action="store", default=os.environ.get('VHS_APIK'),
                        help="API key to use to access the forum. Will be read from ENV_VAR VHS_APIK if not specified.")
    parser.add_argument("--url", action="store", default='https://talk.vanhack.ca',
                       help="URL of the discourse instance to hit")
    parser.add_argument("--no-winners", action="store_true", default="false",
                       help="don't order the winners, just calculate the user hashes")
    global args
    args = parser.parse_args()
    l.setLevel([logging.WARNING, logging.INFO, logging.DEBUG][min(3-1,args.verbosity)])
    if not args.api_key:
        err("No API Key found. Must be environmental variable or specified as command line argument via --api_key")
        exit(parser.print_usage())
    
    global discource_client
    discource_client = DiscourseClient(
        args.url,
        api_username='system',
        api_key=args.api_key)
    import time
    os.environ['TZ'] = 'US/Pacific'
    time.tzset()
    for item in get_all_polls(args.post_id):
        print(f"{'=' * 20} {item['description']} {'=' * 20}")
        print(f"Close time: {item['close_time']} - {time.ctime(item['close_time'])}")
        print()
        key_hash = get_hash(str(item['close_time']) + item['id'])
        print(f"Key hash hash(Close time + item ID): {key_hash.hex()}", end='\n\n')
        user_hashes = get_user_hashes(key_hash,item['voters'])
        print("Users and their unique hashes:")
        for entrant in user_hashes:
            print(f"    {entrant[0]} - {entrant[1].hex()}")
       # If time has passed now, do the next step
        print()
        if time.time() > item['close_time']:
            bitcoin_hash = get_bitcoin_hash(item['close_time'])
            print(f"Bitcoin block hash closest to the time of auction (But not after): {bitcoin_hash.hex()}")
            print(f"https://www.blockchain.com/btc/block/{bitcoin_hash.hex()}")
            nist_hash=get_nist_hash(item['close_time'])
            print(f"NIST hash closest to the time of auction (But not before): {nist_hash.hex()}")
            print(f"https://beacon.nist.gov/beacon/2.0/pulse/time/{item['close_time']*1000}")
            dice_hash = get_hash(bitcoin_hash.hex()+nist_hash.hex())
            print(f"Dice hash (hash(Bitcoin + NIST)): {dice_hash.hex()}")
            winning = get_winning_order(key_hash,dice_hash,item['voters'])
            print("Winners, in order, are:")
            for i,entrant in enumerate(winning):
                print(f"    {i+1} - {entrant[0]} - {entrant[1].hex()}")
        else:
            print("This poll has not closed yet")
        print("\n\n",end="")
    

### Logging config
import logging
logging.basicConfig(format='%(levelname)s:%(message)s')
l = logging.getLogger()
l.setLevel(logging.WARN)
deb=l.debug
info=l.info
warn=l.warn
err=l.error

import hashlib,requests
def get_hash(string):
    assert type(string)==str
    return hashlib.sha256(string.encode()).digest() # Specify hash algorithm used through script
def hash_xor(b1, b2): # xor function used to compare dice roll with user digests
    assert type(b1)==type(b2) == bytes
    return bytes([a ^ b for a, b in zip(b1, b2)])
def get_user_hashes(key_hash,entrants_list): # Generate a list of tuples with the user key
    assert type(key_hash) == bytes
    assert type(entrants_list) == list
    return [(entrant,get_hash(entrant+" "+key_hash.hex())) for entrant in entrants_list]
def get_winning_order(key_hash,dice_hash,entrants_list): # Generate a sorted list of the entrants, using lowest value of xor of their digest and the roll digest
    assert type(key_hash) == type(dice_hash) == bytes
    assert type(entrants_list) == list
    # TODO: refactor next line for readability as per Mike Kes
    return sorted([(name, hash_xor(digest,get_hash(key_hash.hex()+" "+dice_hash.hex()))) for name, digest in get_user_hashes(key_hash,entrants_list)],key=lambda x: x[1])
def get_nist_hash(timestamp):
    try:
        pulse = requests.get('https://beacon.nist.gov/beacon/2.0/pulse/time/'+str(timestamp*1000)).json()['pulse']['outputValue']
    except:
        err("NIST Pulse get error")
        raise
    return bytes.fromhex(pulse)
def get_bitcoin_hash(timestamp): # Get list of coins from https://blockchain.info/blocks/[ts_in_ms]?format=json
    try:
        blocks = requests.get('https://blockchain.info/blocks/'+str(timestamp*1000), params={'format':'json'}).json()['blocks']
    except:
        err("Bitcoin get error")
        raise
    closest=None
    for i in blocks:
        if i['main_chain']==False:
            continue
        if i['time'] > timestamp:
            break
        closest=i
    return bytes.fromhex(closest['hash'])

from pydiscourse import DiscourseClient
discource_client=None
def get_all_voters(post_id, poll_name, option_id):
    results=[]
    i=1
    page = discource_client._request("GET","/polls/voters.json",params={"post_id":post_id,"poll_name":poll_name,"option_id":option_id, "page":i})['voters'][option_id] # Hacky way to get voters directly
    results+=page
    i+=1
    while len(page) !=0:
        page = discource_client._request("GET","/polls/voters.json",params={"post_id":post_id,"poll_name":poll_name,"option_id":option_id, "page":i})['voters'][option_id]
        results+=page
        i+=1
    # Ugh that (^^^) was a lame way of doing this, I was tired, TODO: Make this cooler/cleaner for pagination and the actual request
    return [voter['username'] for voter in results] # Get just the usernames

from datetime import datetime
def get_all_polls(post_id):
    assert type(post_id) == int
    topic=discource_client.topic_posts(str(post_id))
    all_poll_items=[]
    for post in topic['post_stream']['posts']:
        if 'polls' not in post:
            continue # Skip if this post doesn't have any polls in it (most will skip, only a few polls per post)
        else:
            for poll in post['polls']:
                for item in poll['options']:
                    winnable_item={}
                    winnable_item['description'] = item['html']
                    winnable_item['id']          = item['id']
                    if args.close_time_override:
                        winnable_item['close_time']  = args.close_time_override
                    else:
                        try:
                            winnable_item['close_time']  = int(datetime.fromisoformat(poll['close'].replace('Z','+00:00')).timestamp())
                        except:
                            err("Problem with close time for poll. Close time is used for hash generation and is needed. You can specify from command line if needed")
                            exit(parser.print_usage())
                    winnable_item['voters']      = get_all_voters(post['id'],poll['name'],item['id'])
                    all_poll_items.append(winnable_item)
    return all_poll_items
    
if __name__ == "__main__":
    main()
