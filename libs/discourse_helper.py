from datetime import datetime
import logging
from pydiscourse import DiscourseClient

logger = logging.getLogger()
deb = logger.debug
info = logger.info
warn = logger.warn
err = logger.error


class DiscouseConnection:
    def __init__(self, url, discord_api_key, api_username="system") -> None:
        self._discource_client = DiscourseClient(
            url, api_username=api_username, api_key=discord_api_key
        )

    def get_all_voters(self, post_id, poll_name, option_id):
        results = []
        i = 1
        page = self._discource_client._request(
            "GET",
            "/polls/voters.json",
            params={
                "post_id": post_id,
                "poll_name": poll_name,
                "option_id": option_id,
                "page": i,
            },
        )["voters"][
            option_id
        ]  # Hacky way to get voters directly
        results += page
        i += 1
        while len(page) != 0:
            page = self._discource_client._request(
                "GET",
                "/polls/voters.json",
                params={
                    "post_id": post_id,
                    "poll_name": poll_name,
                    "option_id": option_id,
                    "page": i,
                },
            )["voters"][option_id]
            results += page
            i += 1
        # Ugh that (^^^) was a lame way of doing this, I was tired,
        # TODO: Make this cooler/cleaner for pagination and the actual request
        return results

    def get_all_polls(self, post_id, close_time_override=None):
        assert isinstance(post_id, int)
        topic = self._discource_client.topic_posts(str(post_id))
        all_poll_items = []
        for post in topic["post_stream"]["posts"]:
            if "polls" not in post:
                continue  # Skip if this post doesn't have any polls in it (most will skip, only a few polls per post)

            for poll in post["polls"]:
                for item in poll["options"]:
                    winnable_item = {}
                    winnable_item["description"] = item["html"]
                    winnable_item["id"] = item["id"]
                    if close_time_override:
                        winnable_item["close_time"] = close_time_override
                    else:
                        try:
                            winnable_item["close_time"] = int(
                                datetime.fromisoformat(
                                    poll["close"].replace("Z", "+00:00")
                                ).timestamp()
                            )
                        except:
                            err(
                                "Problem with close time for poll. Close time is used for hash generation and is needed. \
                                    You can specify from command line if needed"
                            )
                            exit()
                    winnable_item["entrants"] = self.get_all_voters(
                        post["id"], poll["name"], item["id"]
                    )
                    all_poll_items.append(winnable_item)
        return all_poll_items
