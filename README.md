# Tautulli Recently Added
Python script to send a Discord webhook message for recently added Plex items using the Tautulli API.

# Setup
Copy `config_template.json` to `config.json` and fill in the configuration values.

- `tautulli_url` - URL of your Tautulli instance
- `tautulli_api_key` - API Key for your Tautulli instance. You can find this under Settings -> Web Interface -> Enable API
- `discord_webhook_url` - The URL to send webhooks to. You can find this in the settings for a channel under Integrations -> Webhooks
- `library_names` - List of library names to include in the messages
- `log_path` - optional, path to a log file. Logs will be appended to this file when running the script.
- `last_run_timestamp` - optional, a ISO 8601 timestamp that serves as the cutoff for which items to include in the message. The script will automatically update this after a successful run to facilitate something like a cronjob deployment

```
{
    "tautulli_url": "<tautulli_url_here>",
    "tautulli_api_key": "<tautulli_api_key_here>",
    "discord_webhook_url": "<discord_webhook_url_here>",
    "library_names": [
        "Movies",
        "TV Shows"
    ],
    "log_path": "tautulli_recently_added.log",
    "last_run_timestamp": null
}
```

Run the script using `uv run tautulli_recently_added.py`
