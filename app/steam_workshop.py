import httpx

from app.config import (
    STEAM_API_URL,
    STEAM_WORKSHOP_URL,
    REQUEST_TIMEOUT,
)


def get_workshop_item(
    workshop_id,
):
    """
    Fetch Steam Workshop item details.
    """

    payload = {
        "itemcount": 1,
        "publishedfileids[0]":
            str(workshop_id),
    }

    try:

        with httpx.Client(
            timeout=REQUEST_TIMEOUT,
        ) as client:

            response = client.post(
                STEAM_API_URL,
                data=payload,
            )

            response.raise_for_status()

            data = response.json()

    except Exception as error:

        print(
            f"Steam request error: {error}"
        )

        return None

    response_data = data.get(
        "response",
        {},
    )

    if response_data.get(
        "result"
    ) != 1:

        print(
            "Steam response result "
            "is not successful"
        )

        return None

    items = response_data.get(
        "publishedfiledetails",
        [],
    )

    if not items:

        print(
            "No Workshop item returned"
        )

        return None

    item = items[0]

    if item.get(
        "result"
    ) != 1:

        print(
            "Workshop item result "
            "is not successful"
        )

        return None

    return item


def get_workshop_url(
    workshop_id,
):
    """
    Build Steam Workshop item URL.
    """

    return (
        f"{STEAM_WORKSHOP_URL}"
        f"?id={workshop_id}"
    )
