import html
import re

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

    item["screenshots"] = (
        get_workshop_screenshots(
            workshop_id
        )
    )

    return item


def get_workshop_screenshots(
    workshop_id,
):
    """
    Fetch Workshop screenshots from
    the Steam Workshop page.
    """

    url = get_workshop_url(
        workshop_id
    )

    try:

        with httpx.Client(
            timeout=REQUEST_TIMEOUT,
        ) as client:

            response = client.get(
                url
            )

            response.raise_for_status()

            page = response.text

    except Exception as error:

        print(
            f"Steam screenshot request "
            f"error: {error}"
        )

        return []


    # Steam exposes the full screenshot
    # URLs inside rgFullScreenshotURLs.
    match = re.search(
        r"var\s+rgFullScreenshotURLs\s*=\s*\[(.*?)\];",
        page,
        flags=(
            re.IGNORECASE
            | re.DOTALL
        ),
    )

    if not match:

        print(
            "No Workshop screenshots found"
        )

        return []

    screenshot_block = match.group(
        1
    )

    pattern = re.compile(
        r"""
        ['"]previewid['"]\s*:\s*
        ['"](\d+)['"]\s*,\s*
        ['"]url['"]\s*:\s*
        ['"]([^'"]+)['"]
        """,
        flags=(
            re.IGNORECASE
            | re.VERBOSE
        ),
    )

    screenshots = []

    for screenshot_match in pattern.finditer(
        screenshot_block
    ):

        screenshot_url = html.unescape(
            screenshot_match.group(2)
        ).strip()

        if screenshot_url:

            screenshots.append(
                screenshot_url
            )

    print(
        "Workshop screenshots found | "
        f"Count={len(screenshots)}"
    )

    return screenshots


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
