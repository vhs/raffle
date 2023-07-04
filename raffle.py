#!/usr/bin/env python3
import time
import argparse
import os
import logging
import libs.crypto_helper,libs.discourse_helper

### Logging config
logging.basicConfig(format='%(levelname)s:%(message)s')
l = logging.getLogger()
l.setLevel(logging.WARN)
deb=l.debug
info=l.info
warn=l.warn
err=l.error
parser,args=None,None

def main():
    parser = argparse.ArgumentParser(description='Run raffels for VHS. Randomness from Bitcoin and NIST')
    parser.add_argument("post_id", help='the ID from the URL of the post. EG: \'talk.vanhack.ca/t/raffle-welcome-to-2021/11292/18\' the ID is 11292',
                    type=int)
    parser.add_argument("-v", "--verbosity", action="count", default=0,
                    help="increase output verbosity, max 2")
    parser.add_argument("-q", "--quiet", action="count", default=0,
                    help="surpress default output and steps (Not that useful unless dumping XML)")
    parser.add_argument("--close_time_override", type=int,action="store",
                       help="override the time the poll closes.")
    parser.add_argument("--api_key", action="store", default=os.environ.get('DISCORD_API_KEY'),
                        help="API key to use to access the forum. Will be read from ENV_VAR DISCORD_API_KEY if not specified.")
    parser.add_argument("--api_key_file", action="store",
                        help="Read API key from a file")
    parser.add_argument("--url", action="store", default='https://talk.vanhack.ca',
                       help="URL of the discourse instance to hit")
    parser.add_argument("--no-winners", action="store_true", default="false",
                       help="don't order the winners, just calculate the user hashes")
    args = parser.parse_args()
    # Set logging according to verbosity in args
    l.setLevel([logging.WARNING, logging.INFO, logging.DEBUG][min(3-1,args.verbosity)])
    if args.api_key and args.api_key_file:
        err("API key specified too many ways. Please only use one")
        exit(parser.print_usage())
    if not (args.api_key or args.api_key_file):
        err("No API Key found. Must be environmental variable or specified as command line argument via --api_key or --api-key-file")
        exit(parser.print_usage())
    discord_api_key=None
    if args.api_key_file:
        with open(args.api_key_file,encoding='UTF-8') as key_file:
            discord_api_key=key_file.read().strip()
    else:
        discord_api_key=args.api_key

    os.environ['TZ'] = 'US/Pacific' # Screw it, let's just be west coast centric.
    time.tzset()
    discouse_connection=libs.discourse_helper.discouse_connection(args.url, discord_api_key)

    for item in discouse_connection.get_all_polls(args.post_id):
        print(f"{'=' * 20} {item['description']} {'=' * 20}")
        print(f"Close time: {item['close_time']} - {time.ctime(item['close_time'])}")
        print()
        key_hash = libs.crypto_helper.get_hash(str(item['close_time']) + item['id'])
        #print(f"Key hash hash(Close time + item ID): {key_hash.hex()}", end='\n\n')
        user_hashes = libs.crypto_helper.get_user_hashes(key_hash,item['voters'])
        #print("Users and their unique hashes:")
        #for entrant in user_hashes:
        #    print(f"    {entrant[0]} - {entrant[1].hex()}")
       # If time has passed now, do the next step
        print()
        if time.time() > item['close_time']:
            bitcoin_hash = libs.crypto_helper.get_bitcoin_hash(item['close_time'])
            #print(f"Bitcoin block hash closest to the time of auction (But not after): {bitcoin_hash.hex()}")
            #print(f"https://www.blockchain.com/btc/block/{bitcoin_hash.hex()}")
            nist_hash=libs.crypto_helper.get_nist_hash(item['close_time'])
            #print(f"NIST hash closest to the time of auction (But not before): {nist_hash.hex()}")
            #print(f"https://beacon.nist.gov/beacon/2.0/pulse/time/{item['close_time']*1000}")
            dice_hash = libs.crypto_helper.get_hash(bitcoin_hash.hex()+nist_hash.hex())
            #print(f"Dice hash (hash(Bitcoin + NIST)): {dice_hash.hex()}")
            #print(get_hash(key_hash.hex()+" "+dice_hash.hex()).hex())
            winning = libs.crypto_helper.get_winning_order(key_hash,dice_hash,item['voters'])
            print("Winners, in order, are:")
            for i,entrant in enumerate(winning):
                print(f"    {i+1} - {entrant[0]} - {entrant[1].hex()}")
        else:
            print("This poll has not closed yet")
        print("\n\n",end="")

if __name__ == "__main__":
    main()
