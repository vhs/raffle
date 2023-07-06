
Run raffels for VHS on the Discourse forums. Randomness is provided from Bitcoin and NIST. 

Queries the discourse API directly and pulls out poll data to choose winners of raffles. 

Each poll item has a unique ID. This is combined with the close time to generate an item hash.
Each user's ID is combined with the item hash to generate a user-item hash.

When the poll closes, we grab the most recent blockchain hash before the close time, and the closest NIST randomness block hash after the close time. These two are hashed together to produce the dice-hash

To determine winners, each user-item hash is XOR'ed bytewise with the dice-hash. The users with the lowest resulting hash win!

This tool can post winners directly to the topics, or dump various data output to terminal.


## Install

```sh
git clone
```

## Usage

```sh
python3 raffle.py [action] [topic_id]
python3 raffle.py -h
```
