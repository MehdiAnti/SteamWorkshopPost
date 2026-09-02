import httpx

from app.config import (
    TELEGRAM_API_URL,
    REQUEST_TIMEOUT,
)


def telegram_request(
    method,
    payload=None,
):
    """
    Send request to Telegram Bot API.
    """

    url = (
        f"{TELEGRAM_API_URL}/"
        f"{method}"
    )

    try:

        with httpx.Client(
            timeout=REQUEST_TIMEOUT,
        ) as client:

            response = client.post(
                url,
                json=payload or {},
            )

            response.raise_for_status()

            data = response.json()

    except Exception as error:

        print(
            f"Telegram request error "
            f"[{method}]: {error}"
        )

        return None

    if not data.get("ok"):

        print(
            f"Telegram API error "
            f"[{method}]: {data}"
        )

        return None

    return data.get(
        "result"
    )


def send_message(
    chat_id,
    text,
    parse_mode="HTML",
):
    """
    Send normal Telegram message.
    """

    return telegram_request(
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
        },
    )


def send_rich_message(
    chat_id,
    html,
    disable_notification=False,
):
    """
    Send Telegram RichMessage.
    """

    return telegram_request(
        "sendRichMessage",
        {
            "chat_id": chat_id,
            "rich_message": {
                "html": html,
            },
            "disable_notification":
                disable_notification,
        },
    )


def answer_callback_query(
    callback_query_id,
    text=None,
    show_alert=False,
):
    """
    Answer Telegram callback query.
    """

    payload = {
        "callback_query_id":
            callback_query_id,
        "show_alert":
            show_alert,
    }

    if text:

        payload["text"] = text

    return telegram_request(
        "answerCallbackQuery",
        payload,
    )


def set_webhook(
    webhook_url,
):
    """
    Set Telegram webhook.
    """

    return telegram_request(
        "setWebhook",
        {
            "url": webhook_url,
            "allowed_updates": [
                "message",
                "callback_query",
            ],
        },
    )
