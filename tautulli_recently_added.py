from datetime import datetime
from tautulli import RawAPI
from tautulli.tools.api_helper import APIShortcuts
import json
import os


def parse_movie_content(movie, api):
    movie_string = f"{movie.get('title')} ({movie.get('year')})"
    director_string = " & ".join(movie.get("directors"))
    dur = int(movie.get("duration")) / (1000 * 60)
    dur_hrs = dur // 60
    dur_min = dur % 60
    dur_str = f"{dur_hrs:.0f}h {dur_min:.0f}m"

    image_url = APIShortcuts(api).get_plex_image_url_from_proxy(movie.get("thumb"))
    
    return {
        "title": movie_string,
        "description": movie.get("summary"),
        "fields": [
            {"name": "Director", "value": director_string},
            {"name": "Runtime", "value": dur_str},
        ],
        "image": {"url": image_url},
    }


def parse_tv_content(recently_added):
    tv_webhook_obj = {"content": f"**New TV on {plex_server_name}**"}
    tv_embeds = []

    for show in recently_added.get("show"):
        season_info = ""
        episode_info = ""
        seasons = show.get("season_range")
        seasons = seasons.replace("00", "01")
        seasons = re.sub(r"0+([1-9]+)", r"\1", seasons)
        if show.get("season_count") == 1:
            season_info = show.get("season")[0]
            if season_info.get("episode_count") == 1:
                episode_info = season_info["episode"][0]
                show_added = f"Season {season_info['media_index']} Episode {episode_info['media_index']}: '{episode_info['title']}'"
        num_episodes = 0
        for season_info in show.get("season"):
            num_episodes += season_info.get("episode_count")
        show_added = f"Season {seasons}, {num_episodes} episodes"
        show_string = f"{show.get('title')} ({show.get('year')})"

        image_url = base_img_url + show.get("thumb_url").split("/")[-1]

        tv_embeds.append(
            {
                "title": show_string,
                "description": show_added,
                "image": {"url": image_url},
            }
        )
    tv_webhook_obj["embeds"] = tv_embeds

    # tv_response = requests.post(url, json=tv_webhook_obj)
    tv_body = json.dumps(tv_webhook_obj, indent=4)


def main():
    config_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "config.json"
    )

    with open(config_path, "r") as f:
        config = json.load(f)

    api = RawAPI(base_url=config["tautulli_url"], api_key=config["tautulli_api_key"])

    recently_added = api.get_recently_added(-1)
    plex_server_name = api.server_friendly_name

    movie_webhook_obj = {"content": f"**New Movies on {plex_server_name}**"}
    movie_embeds = []
    tv_webhook_obj = {}

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
            movie_embeds.append(parse_movie_content(item, api))

    print(json.dumps(movie_embeds, indent=4))

    # if recently_added.get("movie"):
    #     movie_webhook_obj = parse_movie_content(recently_added)
    #     print(json.dumps(movie_webhook_obj, indent=4))
    #     # movie_response = requests.post(url, json=movie_webhook_obj)
    # if recently_added.get("show"):
    #     tv_webhook_obj = parse_tv_content(recently_added)
    #     print(json.dumps(tv_webhook_obj, indent=4))
    #     # tv_response = requests.post(url, json=tv_webhook_obj)


if __name__ == "__main__":
    main()
