import json
import logging
import os
from datetime import datetime, timedelta

from tautulli import RawAPI

from utils import (
    duration_to_str,
    epoch_to_iso8601,
    format_originally_available_date,
    send_request_with_logging,
)

MAX_ITEMS = 5
MAX_LINES_PER_EMBED = 6
IMG_FORMAT = "jpeg"


config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

with open(config_path, "r") as f:
    config = json.load(f)

# Setup logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter("{asctime} - {name} - {levelname} - {message}", style="{")
consoleHandler = logging.StreamHandler()
consoleHandler.setFormatter(formatter)
logger.addHandler(consoleHandler)

LOG_PATH = config.get("log_path")
if LOG_PATH:
    file_handler = logging.FileHandler(LOG_PATH, "a+")
    file_handler.setLevel(logging.DEBUG)

    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)


def parse_movie_content(movie: dict, api: RawAPI):
    """Parse a Tautulli recently added movie object into a Discord embed.

    Args:
        movie (dict): The movie object from Tautulli.
        api (RawAPI): The Tautulli API instance.

    Returns:
        2-tuple: First element is a dictionary representing the Discord embed,
                 Second element is a tuple containing the image filename, image bytes, and image format. Will be used in the post request to embed the image.
    """
    # Grab the first 5 directors, actors, and genres
    director_string = ", ".join(movie.get("directors")[0:MAX_ITEMS])
    actors_string = ", ".join(movie.get("actors")[0:MAX_ITEMS])
    genres_string = ", ".join(movie.get("genres")[0:MAX_ITEMS])

    # Parse the release date
    release_date_str = format_originally_available_date(
        movie.get("originally_available_at")
    )
    dur_str = duration_to_str(movie.get("duration"))

    # Set the date added field to Discord's timestamp format
    date_added_str = epoch_to_iso8601(movie.get("added_at"))

    # Get the image from the Plex server
    movie_img_path = movie.get("thumb")
    img_bytes = api.pms_image_proxy(img=movie_img_path, img_format=IMG_FORMAT)
    img_filename = f"{movie.get('rating_key')}.{IMG_FORMAT}"

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

    image_tuple = (img_filename, img_bytes, f"image/{IMG_FORMAT}")

    return embed, image_tuple


def parse_tv_content(tv_data, api):
    """Parse a Tautulli recently added TV episode/show/season object into a Discord embed.

    Args:
        tv_data (dict): The object from Tautulli.
        api (RawAPI): The Tautulli API instance.

    Returns:
        2-tuple: First element is a dictionary representing the Discord embed,
                 Second element is a tuple containing the image filename, image bytes, and image format. Will be used in the post request to embed the image.
    """
    if tv_data.get("media_type") == "episode":
        show_rating_key = tv_data.get("grandparent_rating_key")
        episode_number = tv_data.get("media_index")
        season_title = tv_data.get("parent_title")
        episodes_field = {
            "name": "Episode",
            "value": f"{season_title}, Episode {episode_number} - {tv_data.get('title')}",
        }
        if tv_data.get("originally_available_at"):
            air_date_field = {
                "name": "Air Date",
                "value": format_originally_available_date(
                    tv_data.get("originally_available_at")
                ),
            }
        img_path = tv_data.get("parent_thumb")
        num_episodes = 1
    elif tv_data.get("media_type") == "season":
        show_rating_key = tv_data.get("parent_rating_key")
        episodes_data = api.get_children_metadata(
            tv_data.get("rating_key"), media_type="season"
        )
        num_episodes = episodes_data.get("children_count", 0)
        season_title = tv_data.get("title")

        ep_names = []
        latest_air_date = datetime.fromtimestamp(0)
        for episode in episodes_data.get("children_list", []):
            episode_title = episode.get("title")
            ep_num = episode.get("media_index")
            if episode_title.lower() == f"episode {ep_num}":
                episode_title = ""
            ep_names.append(f"{season_title}, Episode {ep_num} - {episode_title}")
            air_date = datetime.fromisoformat(episode.get("originally_available_at"))
            if air_date > latest_air_date:
                latest_air_date = air_date

        if num_episodes < MAX_LINES_PER_EMBED:
            episodes_field = {
                "name": "Episodes",
                "value": "\n".join(ep_names[0:MAX_LINES_PER_EMBED]),
            }
        else:
            episodes_field = {
                "name": "Episode",
                "value": f"{season_title}, {num_episodes} episodes",
            }

        air_date_field = {
            "name": "Most Recent Episode Air Date",
            "value": format_originally_available_date(latest_air_date),
        }
        img_path = tv_data.get("thumb")
    else:
        show_rating_key = tv_data.get("rating_key")
        seasons_data = api.get_children_metadata(
            tv_data.get("rating_key"), media_type="show"
        )
        season_titles = []
        num_episodes = 0
        latest_air_date = datetime.min
        for season in seasons_data.get("children_list", []):
            if season.get("media_type") != "season":
                continue

            season_metadata = api.get_metadata(season.get("rating_key"))
            eps_in_season = season_metadata.get("children_count", 0)
            num_episodes += eps_in_season
            season_titles.append(f"{season.get("title")}, {eps_in_season} episodes")
            episodes_data = api.get_children_metadata(
                season.get("rating_key"), media_type="season"
            )
            for episode in episodes_data.get("children_list", []):
                air_date_str = episode.get("originally_available_at")
                if air_date_str:
                    air_date = datetime.fromisoformat(air_date_str)
                    if air_date > latest_air_date:
                        latest_air_date = air_date
        if len(season_titles) < MAX_LINES_PER_EMBED:
            episodes_field = {
                "name": "Epsiodes",
                "value": "\n".join(season_titles[0:MAX_LINES_PER_EMBED]),
            }
        else:
            episodes_field = {
                "name": "Episodes",
                "value": f"{len(season_titles)} seasons, {num_episodes} episodes",
            }
        air_date_field = {
            "name": "Most Recent Episode Air Date",
            "value": format_originally_available_date(latest_air_date),
        }
        img_path = tv_data.get("thumb")

    show_data = api.get_metadata(show_rating_key)

    fields = [
        {
            "name": "Year",
            "value": show_data.get("year"),
        },
    ]

    if episodes_field:
        fields.append(episodes_field)
    if air_date_field:
        fields.append(air_date_field)
    if show_data.get("actors"):
        fields.append(
            {
                "name": "Starring",
                "value": ", ".join(show_data.get("actors", [])[0:MAX_ITEMS]),
            }
        )
    if show_data.get("genres"):
        fields.append(
            {
                "name": "Genre",
                "value": ", ".join(show_data.get("genres", [])[0:MAX_ITEMS]),
            }
        )

    img_key = img_path.split("/")[-1]
    image_filename = f"{img_key}.{IMG_FORMAT}"
    img_bytes = api.pms_image_proxy(img=img_path, img_format=IMG_FORMAT)

    embed = {
        "title": show_data.get("title"),
        "description": show_data.get("summary"),
        "fields": fields,
        "image": {"url": f"attachment://{image_filename}"},
        "timestamp": epoch_to_iso8601(tv_data.get("added_at")),
    }

    image_tuple = (image_filename, img_bytes, f"image/{IMG_FORMAT}")

    return embed, image_tuple, num_episodes


def main():
    api = RawAPI(base_url=config["tautulli_url"], api_key=config["tautulli_api_key"])

    section_ids = []
    for library in api.libraries:
        if library["section_name"] in config["library_names"]:
            section_ids.append(library["section_id"])

    recently_added = api.get_recently_added(-1)
    plex_server_name = api.server_friendly_name

    movie_embeds = []
    movie_files = {}

    tv_embeds = []
    tv_files = {}
    total_episodes = 0

    last_run_timestamp = config.get("last_run_timestamp", None)
    if last_run_timestamp:
        last_run_datetime = datetime.fromisoformat(last_run_timestamp)
    else:
        last_run_datetime = datetime.now() - timedelta(days=1)

    for item in recently_added["recently_added"]:
        if item["section_id"] not in section_ids:
            continue
        added_at_datetime = datetime.fromtimestamp(int(item["added_at"]))
        if added_at_datetime < last_run_datetime:
            break
        if item["media_type"] == "movie":
            embed, img_tuple = parse_movie_content(item, api)
            movie_embeds.append(embed)
            movie_files[f"file{len(movie_files) + 1}"] = img_tuple
        else:
            embed, img_tuple, num_episodes = parse_tv_content(item, api)
            tv_embeds.append(embed)
            tv_files[f"file{len(tv_files) + 1}"] = img_tuple
            total_episodes += num_episodes

    if len(movie_embeds) > 0:
        movie_webhook_obj = {}
        if len(movie_embeds) == 1:
            movie_webhook_obj["content"] = f"1 new movie added to {plex_server_name}"
        movie_webhook_obj["content"] = (
            f"{len(movie_embeds)} new movies added to {plex_server_name}"
        )
        movie_webhook_obj["embeds"] = movie_embeds

        send_request_with_logging(
            url=config["discord_webhook_url"],
            files=movie_files,
            data={"payload_json": json.dumps(movie_webhook_obj)},
            logger=logger,
        )

    if len(tv_embeds) > 0:
        tv_webhook_obj = {}
        if total_episodes == 1:
            tv_webhook_obj["content"] = f"1 new TV episode added to {plex_server_name}"
        else:
            tv_webhook_obj["content"] = (
                f"{total_episodes} new TV episodes added to {plex_server_name}"
            )
        tv_webhook_obj["embeds"] = tv_embeds

        send_request_with_logging(
            url=config["discord_webhook_url"],
            files=tv_files,
            data={"payload_json": json.dumps(tv_webhook_obj)},
            logger=logger,
        )

    config["last_run_timestamp"] = datetime.now().isoformat()
    with open(config_path, "w") as f:
        json.dump(config, f, indent=4)
    logger.info(
        "Script completed successfully. Sent %d movie embeds and %d TV embeds.",
        len(movie_embeds),
        len(tv_embeds),
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(e, exc_info=True)
        raise
