#!/usr/bin/env python3

import argparse
import logging
import os
import pickle
import pprint
import time
from base64 import b64encode
from gzip import compress

from libs.crypto_helper import get_dice_roll, get_hash, hash_xor
from libs.discourse_helper import (
    DiscourseConnection,
    generate_post_data,
    generate_post_winners,
)

# Logging config
logging.basicConfig(format="%(levelname)s: %(pathname)s: %(message)s")
logger = logging.getLogger()
logger.setLevel(logging.WARN)
deb = logger.debug
info = logger.info
warn = logger.warn
err = logger.error


def parse_args(parser):
    parser.add_argument(
        "mode",
        action="store",
        choices=[
            "print-nice",
            "dump-raw-object",
            "dump-base64-picked-object",
            "post-data-to-topic",
            "post-winners-to-topic",
            "print-data",
            "print-winners",
        ],
        help="What action to take.",
    )
    parser.add_argument(
        "topic_id",
        action="store",
        help="the ID from the URL of the post. EG:"
        + " 'talk.vanhack.ca/t/raffle-welcome-to-2021/11292/18'"
        + " the ID is 11292",
        type=int,
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="increase output verbosity",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="decrease output verbosity",
    )
    parser.add_argument(
        "--close_time_override",
        type=int,
        action="store",
        help="override the time the poll closes.",
    )
    parser.add_argument(
        "--api-key",
        action="store",
        default=os.environ.get("DISCOURSE_API_KEY"),
        help="API key to use to access the forum."
        + " Will be read from ENV_VAR DISCOURSE_API_KEY if not specified.",
    )
    parser.add_argument(
        "--api-key-file", action="store", help="Read API key from a file"
    )
    parser.add_argument(
        "--api-username",
        action="store",
        default="system",
        help="Username to use for API calls.",
    )
    parser.add_argument(
        "--url",
        action="store",
        default="https://talk.vanhack.ca",
        help="URL of the discourse instance to hit",
    )

    return parser.parse_args()


def main():
    parser = argparse.ArgumentParser(
        description="Run raffels for VHS on the Discourse forums."
        + " Randomness is provided from Bitcoin and NIST"
    )
    args = parse_args(parser)

    # Set logging according to verbosity in args
    if args.quiet and args.verbose:
        err("API key specified too many ways. Please only use one")

        parser.print_usage()

        exit(255)
    elif args.quiet:
        logger.setLevel(logging.WARNING)
    elif args.verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)
    if args.api_key and args.api_key_file:
        err("API key specified too many ways. Please only use one")

        parser.print_usage()

        exit(254)
    if not (args.api_key or args.api_key_file):
        err(
            "No API Key found. Must be environmental variable"
            + " or specified as command line argument"
            + " via --api_key or --api-key-file"
        )

        parser.print_usage()

        exit(253)

    discourse_api_key = None

    if args.api_key_file:
        with open(args.api_key_file, encoding="UTF-8") as key_file:
            discourse_api_key = key_file.read().strip()
    else:
        discourse_api_key = args.api_key

    discourse_connection = DiscourseConnection(
        args.url, discourse_api_key, args.api_username
    )

    info(
        "Hitting discourse topic to find some polls."
        + " It can take a bit if there are a lot of polls."
    )
    all_items = discourse_connection.get_all_polls(args.topic_id)
    info("Got %s polls from topic" % len(all_items))

    # Add in the crypto parts to the results we got from Discourse
    for item in all_items:
        # Calculate the unique hash for this item.
        # This is only used to calculate the user's hash.
        item["item_hash"] = get_hash(str(item["close_time"]) + item["id"])

        # Calculate the unique hash for each user.
        for entrant in item["entrants"]:
            entrant["user-item-hash"] = get_hash(
                str(entrant["id"]) + item["item_hash"].hex()
            )

    poll_closed = time.time() > item["close_time"]

    if poll_closed:
        for item in all_items:
            item["dice_roll_hash"] = get_dice_roll(item["close_time"])

            for entrant in item["entrants"]:
                entrant["user-item-dice-result"] = hash_xor(
                    entrant["user-item-hash"], item["dice_roll_hash"]
                )

            # Did my best to keep the next lines simple,
            # as this is what actually sorts the winners
            #
            # First we create a new list with just the keys we care about
            temp_list_of_entrants_with_fewer_keys = [
                {
                    k: v
                    for k, v in d.items()
                    if k in ["user-item-dice-result", "username", "name"]
                }
                for d in item["entrants"]
            ]

            # Next we sort that list by the result of the xor,
            # which is stored in each user (unique list per item)
            item["sorted_winner_list"] = sorted(
                temp_list_of_entrants_with_fewer_keys,
                key=lambda x: x["user-item-dice-result"],
            )

    match args.mode:
        case "print-nice":
            output = ""

            for item in all_items:
                output += f"**{item['description']}**\n\n"
                output += "Entrants: \n"

                for i, entrant in enumerate(item["entrants"]):
                    output += str(i + 1)
                    output += ". "
                    output += entrant["username"]
                    output += " - "
                    output += entrant["user-item-hash"].hex()[:8]
                    output += "...\n"

                output += "\nWinning Order: \n"

                for i, entrant in enumerate(item["sorted_winner_list"]):
                    output += str(i + 1)
                    output += ". "
                    output += entrant["username"]
                    output += " - "
                    output += entrant["user-item-dice-result"].hex()[:8]
                    output += "...\n"

                output += "\n"

            print(output)
        case "dump-raw-object":
            pprint.pprint(all_items)
        case "dump-base64-picked-object":
            print(b64encode(compress(pickle.dumps(all_items))).decode())
        case "post-data-to-topic":
            post_data = generate_post_data(all_items)

            discourse_connection.make_post(args.topic_id, post_data)
        case "post-winners-to-topic":
            discourse_connection.make_post(
                args.topic_id, generate_post_winners(all_items)
            )
        case "print-raw-data-post":
            print(generate_post_data(all_items))
        case "print-raw-winners-post":
            print(generate_post_winners(all_items))


if __name__ == "__main__":
    main()
