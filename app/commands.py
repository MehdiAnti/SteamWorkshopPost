import re

from app.config import (
    ADMIN_ID,
    CHANNEL_ID,
)

from app.telegram import (
    send_message,
    send_rich_message,
    answer_callback_query,
)

from app.steam_workshop import (
    get_workshop_item,
)

from app.html_build import (
    build_workshop_post,
)


PENDING_ITEMS = {}


def is_admin(
    user_id,
):
    """
    Check admin access.
    """

    return (
        int(user_id or 0)
        == ADMIN_ID
    )


def _extract_workshop_id(
    text,
):
    """
    Extract Workshop ID from command.

    Supports:

    /preview 3776341275

    and URLs containing ?id=3776341275
    """

    if not text:

        return None

    parts = text.split(
        maxsplit=1
    )

    if len(parts) < 2:

        return None

    value = parts[1].strip()

    if value.isdigit():

        return value

    match = re.search(
        r"(?:\?|&)id=(\d+)",
        value,
    )

    if match:

        return match.group(1)

    return None


def handle_start(
    message,
):
    """
    Handle /start command.
    """

    user_id = (
        message.get(
            "from",
            {},
        ).get(
            "id"
        )
    )

    chat_id = (
        message.get(
            "chat",
            {},
        ).get(
            "id"
        )
    )

    if not is_admin(
        user_id
    ):

        return

    send_message(
        chat_id,
        (
            "<b>Steam Workshop Post Bot</b>\n\n"
            "Use:\n"
            "<code>/preview WORKSHOP_ID</code>\n\n"
            "Example:\n"
            "<code>/preview 3776341275</code>"
        ),
    )


def handle_preview(
    message,
):
    """
    Handle:

    /preview WORKSHOP_ID
    """

    user_id = (
        message.get(
            "from",
            {},
        ).get(
            "id"
        )
    )

    chat_id = (
        message.get(
            "chat",
            {},
        ).get(
            "id"
        )
    )

    if not is_admin(
        user_id
    ):

        return

    text = message.get(
        "text",
        ""
    )

    workshop_id = (
        _extract_workshop_id(
            text
        )
    )

    if not workshop_id:

        send_message(
            chat_id,
            (
                "Usage:\n"
                "<code>"
                "/preview WORKSHOP_ID"
                "</code>"
            ),
        )

        return

    send_message(
        chat_id,
        (
            "Fetching Steam Workshop "
            "item..."
        ),
    )

    item = get_workshop_item(
        workshop_id
    )

    if not item:

        send_message(
            chat_id,
            (
                "❌ Unable to read "
                "Steam Workshop item."
            ),
        )

        return

    # Store exact item for Publish callback.
    PENDING_ITEMS[
        workshop_id
    ] = item

    rich_html = build_workshop_post(
        item,
        preview=True,
    )

    result = send_rich_message(
        chat_id,
        rich_html,
    )

    if not result:

        send_message(
            chat_id,
            (
                "❌ Failed to send "
                "Rich Message preview."
            ),
        )


def handle_callback(
    callback_query,
):
    """
    Handle Publish / Cancel buttons.
    """

    callback_id = (
        callback_query.get(
            "id"
        )
    )

    user_id = (
        callback_query.get(
            "from",
            {},
        ).get(
            "id"
        )
    )

    data = (
        callback_query.get(
            "data",
            ""
        )
    )

    if not is_admin(
        user_id
    ):

        answer_callback_query(
            callback_id,
            "Access denied.",
            show_alert=True,
        )

        return

    # -----------------------------
    # Publish
    # -----------------------------

    if data.startswith(
        "publish:"
    ):

        workshop_id = data.split(
            ":",
            1,
        )[1]

        item = PENDING_ITEMS.get(
            workshop_id
        )

        if not item:

            answer_callback_query(
                callback_id,
                (
                    "Preview expired. "
                    "Run /preview again."
                ),
                show_alert=True,
            )

            return

        answer_callback_query(
            callback_id,
            "Publishing...",
        )

        # Final channel post has NO
        # Publish / Cancel controls.
        rich_html = build_workshop_post(
            item,
            preview=False,
        )

        result = send_rich_message(
            CHANNEL_ID,
            rich_html,
        )

        if not result:

            answer_callback_query(
                callback_id,
                "Publishing failed.",
                show_alert=True,
            )

            return

        # Remove pending item.
        PENDING_ITEMS.pop(
            workshop_id,
            None,
        )

        answer_callback_query(
            callback_id,
            "Published successfully.",
        )

        return

    # -----------------------------
    # Cancel
    # -----------------------------

    if data.startswith(
        "cancel:"
    ):

        workshop_id = data.split(
            ":",
            1,
        )[1]

        PENDING_ITEMS.pop(
            workshop_id,
            None,
        )

        answer_callback_query(
            callback_id,
            "Preview cancelled.",
        )

        return

    answer_callback_query(
        callback_id,
        "Unknown action.",
      )
