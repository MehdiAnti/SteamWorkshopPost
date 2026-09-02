import os


BOT_TOKEN = os.getenv(
    "BOT_TOKEN",
    "",
)


ADMIN_ID = int(
    os.getenv(
        "ADMIN_ID",
        "0",
    )
)


CHANNEL_ID = os.getenv(
    "CHANNEL_ID",
    "",
)


RENDER_EXTERNAL_URL = os.getenv(
    "RENDER_EXTERNAL_URL",
    "",
).rstrip("/")


WEBHOOK_PATH = "/webhook"


WEBHOOK_URL = (
    f"{RENDER_EXTERNAL_URL}"
    f"{WEBHOOK_PATH}"
    if RENDER_EXTERNAL_URL
    else ""
)


TELEGRAM_API_URL = (
    f"https://api.telegram.org/"
    f"bot{BOT_TOKEN}"
)


STEAM_API_URL = (
    "https://api.steampowered.com/"
    "ISteamRemoteStorage/"
    "GetPublishedFileDetails/v1/"
)


STEAM_WORKSHOP_URL = (
    "https://steamcommunity.com/"
    "sharedfiles/filedetails/"
)


REQUEST_TIMEOUT = 30.0


MAX_RICH_HTML_LENGTH = 32000
