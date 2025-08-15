import json
import os
from datetime import UTC, datetime, timedelta

import requests
from tautulli import RawAPI


def parse_movie_content(movie, api):
    """Parse a Tautulli recently added movie object into a Discord embed.

    Args:
        movie (dict): The movie object from Tautulli.
        api (RawAPI): The Tautulli API instance.

    Returns:
        2-tuple: First element is a dictionary representing the Discord embed,
                 Second element is a tuple containing the image filename, image bytes, and image format. Will be used in the post request to embed the image.
    """
    # Grab the first 5 directors, actors, and genres
    max_items = 5
    director_string = ", ".join(movie.get("directors")[0:max_items])
    actors_string = ", ".join(movie.get("actors")[0:max_items])
    genres_string = ", ".join(movie.get("genres")[0:max_items])

    # Parse the release date
    parsed_release_dt = datetime.strptime(
        movie.get("originally_available_at"), "%Y-%m-%d"
    )
    release_date_str = parsed_release_dt.strftime("%B %d, %Y")

    # Calculate the duration in hours and minutes
    dur = int(movie.get("duration")) / (1000 * 60)
    dur_hrs = dur // 60
    dur_min = dur % 60
    dur_str = f"{dur_hrs:.0f}h {dur_min:.0f}m"

    # Set the date added field to Discord's timestamp format
    date_added = datetime.fromtimestamp(float(movie.get("added_at"))).astimezone(UTC)
    date_added_str = date_added.replace(tzinfo=None).isoformat()

    # Get the image from the Plex server
    movie_img_path = movie.get("thumb")
    img_format = "jpeg"
    img_bytes = api.pms_image_proxy(img=movie_img_path, img_format=img_format)
    img_filename = f"{movie.get('rating_key')}.{img_format}"

    embed = {
        "title": movie.get("full_title"),
        "description": movie.get("summary"),
        "fields": [
            {"name": "Year", "value": movie.get("year")},
            {"name": "Director", "value": director_string},
            {"name": "Starring", "value": actors_string},
            {"name": "Runtime", "value": dur_str},
            {"name": "Original Release Date", "value": release_date_str},
            {"name": "Genre", "value": genres_string},
        ],
        "image": {"url": f"attachment://{img_filename}"},
        "timestamp": date_added_str,
    }

    image_tuple = (img_filename, img_bytes, f"image/{img_format}")

    return embed, image_tuple


def parse_tv_content(recently_added):
    pass
    # tv_webhook_obj = {"content": f"**New TV on {plex_server_name}**"}
    # tv_embeds = []

    # for show in recently_added.get("show"):
    #     season_info = ""
    #     episode_info = ""
    #     seasons = show.get("season_range")
    #     seasons = seasons.replace("00", "01")
    #     seasons = re.sub(r"0+([1-9]+)", r"\1", seasons)
    #     if show.get("season_count") == 1:
    #         season_info = show.get("season")[0]
    #         if season_info.get("episode_count") == 1:
    #             episode_info = season_info["episode"][0]
    #             show_added = f"Season {season_info['media_index']} Episode {episode_info['media_index']}: '{episode_info['title']}'"
    #     num_episodes = 0
    #     for season_info in show.get("season"):
    #         num_episodes += season_info.get("episode_count")
    #     show_added = f"Season {seasons}, {num_episodes} episodes"
    #     show_string = f"{show.get('title')} ({show.get('year')})"

    #     # image_url = base_img_url + show.get("thumb_url").split("/")[-1]

    #     tv_embeds.append(
    #         {
    #             "title": show_string,
    #             "description": show_added,
    #             "image": {"url": image_url},
    #         }
    #     )
    # tv_webhook_obj["embeds"] = tv_embeds

    # # tv_response = requests.post(url, json=tv_webhook_obj)
    # # tv_body = json.dumps(tv_webhook_obj, indent=4)


def main():
    config_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "config.json"
    )

    with open(config_path, "r") as f:
        config = json.load(f)

    api = RawAPI(base_url=config["tautulli_url"], api_key=config["tautulli_api_key"])

    recently_added = api.get_recently_added(-1)
    plex_server_name = api.server_friendly_name

    movie_embeds = []
    movie_files = {}

    last_run_timestamp = config.get("last_run_timestamp", None)
    if last_run_timestamp:
        last_run_datetime = datetime.fromisoformat(last_run_timestamp)
    else:
        last_run_datetime = datetime.now() - timedelta(days=1)

    for item in recently_added["recently_added"]:
        added_at_datetime = datetime.fromtimestamp(int(item["added_at"]))
        if added_at_datetime < last_run_datetime:
            break
        if item["media_type"] == "movie":
            embed, img_tuple = parse_movie_content(item, api)
            movie_embeds.append(embed)
            movie_files[f"file{len(movie_files) + 1}"] = img_tuple

    if len(movie_embeds) > 0:
        movie_webhook_obj = {}
        if len(movie_embeds) == 1:
            movie_webhook_obj["content"] = f"1 new movie added to {plex_server_name}"
        movie_webhook_obj["content"] = (
            f"{len(movie_embeds)} new movies added to {plex_server_name}"
        )
        movie_webhook_obj["embeds"] = movie_embeds

        requests.post(
            config["discord_webhook_url"],
            files=movie_files,
            data={"payload_json": json.dumps(movie_webhook_obj)},
        )
        print(json.dumps(movie_webhook_obj, indent=4))
        [
            print("key=", k, "value=", (v[0], v[1][0:10], v[2]))
            for k, v in movie_files.items()
        ]


if __name__ == "__main__":
    main()
