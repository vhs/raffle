# VHS Discourse RaffleBot

This bot takes a post with a number of polls, and runs randomness on it to generate a list of raffle winners, then posts that list in a reply to the original post.

On Discourse, post a poll like so:

```
[poll type=multiple results=always min=1 max=3 public=true chartType=bar close=2025-01-04T23:00:00.000Z]
* 1 x Raffle Item One
* 2 x Raffle itme two (there are two of this thing available)
* 10 x Widgets
[/poll]

[poll type=multiple results=always min=1 max=2 public=true chartType=bar close=2025-01-04T23:00:00.000Z]
* 5 x Raffle section two item one
* 1 x Raffle section two item two
[/poll]
```

To run the RaffleBot as a github action, you need:

1. permission to run github actions on this repo
2. the raffle post's topicID - e.g. talk.vanhack.ca/t/raffle-welcome-to-2021/11292/18 the ID is 11292
3. an action `print-nice`, `dump-raw-object`, `dump-base64-picked-object`, `post-data-to-topic`, `post-winners-to-topic`, `print-raw-data-post`, or  `print-raw-winners-post`

To run the rafflebot locally, you need everything above, plus a discourse api key.

Example:
```bash
python raffle.py print-nice 11292 --api-key <YOUR_API_KEY>
```