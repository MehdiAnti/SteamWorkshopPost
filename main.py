from flask import (
    Flask,
    request,
    jsonify,
)

from app.config import (
    WEBHOOK_PATH,
    WEBHOOK_URL,
)

from app.telegram import (
    set_webhook,
)

from app.commands import (
    handle_preview,
    handle_callback,
)


app = Flask(
    __name__
)


@app.route(
    "/",
    methods=["GET"],
)
def home():

    return jsonify(
        {
            "status": "running",
            "webhook": WEBHOOK_URL,
        }
    )


@app.route(
    WEBHOOK_PATH,
    methods=["POST"],
)
def webhook():

    update = request.get_json(
        silent=True
    )

    if not update:

        return jsonify(
            {
                "ok": False,
            }
        )

    # ---------------------------------
    # Normal messages
    # ---------------------------------

    message = update.get(
        "message"
    )

    if message:

        text = (
            message.get(
                "text",
                ""
            )
        )

        if text.startswith(
            "/preview"
        ):

            handle_preview(
                message
            )

    # ---------------------------------
    # Callback queries
    # ---------------------------------

    callback_query = update.get(
        "callback_query"
    )

    if callback_query:

        handle_callback(
            callback_query
        )

    return jsonify(
        {
            "ok": True,
        }
    )


@app.route(
    "/set-webhook",
    methods=["GET"],
)
def setup_webhook():

    if not WEBHOOK_URL:

        return jsonify(
            {
                "ok": False,
                "error": (
                    "RENDER_EXTERNAL_URL "
                    "is not available"
                ),
            }
        )

    result = set_webhook(
        WEBHOOK_URL
    )

    if not result:

        return jsonify(
            {
                "ok": False,
                "error": (
                    "Failed to set webhook"
                ),
            }
        )

    return jsonify(
        {
            "ok": True,
            "webhook_url":
                WEBHOOK_URL,
        }
    )


if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
    )
