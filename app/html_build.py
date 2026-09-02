import html
import re

from datetime import (
    datetime,
    timezone,
)

from urllib.parse import (
    parse_qs,
    urlsplit,
)

from bs4 import (
    BeautifulSoup,
    NavigableString,
)

from app.config import (
    MAX_RICH_HTML_LENGTH,
)

from app.steam_workshop import (
    get_workshop_url,
)


GAME_NAMES = {
    "227300": "Euro Truck Simulator 2",
    "270880": "American Truck Simulator",
}


SUPPORTED_TAGS = {
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "p",
    "a",
    "b",
    "strong",
    "i",
    "em",
    "u",
    "ins",
    "s",
    "strike",
    "del",
    "code",
    "pre",
    "blockquote",
    "ul",
    "ol",
    "li",
    "br",
    "hr",
    "img",
    "figure",
    "figcaption",

    "details",
    "summary",

    "tg-collage",
    "tg-slideshow",
    "tg-document",
    "tg-spoiler",
    "tg-button",
    "tg-button-row",
    "tg-emoji",
    "tg-reference",
}


def _escape_text(
    value,
):
    """
    Escape normal text safely.
    """

    return html.escape(
        str(value or ""),
        quote=False,
    )


def _escape_attribute(
    value,
):
    """
    Escape HTML attribute safely.
    """

    return html.escape(
        str(value or ""),
        quote=True,
    )


def _fix_url(
    url,
):
    """
    Convert Steam Workshop linkfilter URLs
    into their real destination URLs.
    """

    if not url:

        return ""

    url = html.unescape(
        str(url)
    ).strip()

    # Fix malformed Steam linkfilter URLs.
    url = url.replace(
        "https://steamcommunity.com:/linkfilter/",
        "https://steamcommunity.com/linkfilter/",
    )

    url = url.replace(
        "http://steamcommunity.com:/linkfilter/",
        "http://steamcommunity.com/linkfilter/",
    )

    # Normal Steam linkfilter:
    #
    # https://steamcommunity.com/linkfilter/?url=https://example.com
    #
    if "/linkfilter/" in url:

        try:

            parsed = urlsplit(
                url
            )

            query = parse_qs(
                parsed.query
            )

            target = query.get(
                "url"
            )

            if target:

                return html.unescape(
                    target[0]
                ).strip()

        except Exception:

            pass

        # Fallback for malformed/unusual
        # Steam linkfilter URLs.
        match = re.search(
            r"/linkfilter/\?url=(.+)$",
            url,
            flags=re.IGNORECASE,
        )

        if match:

            return html.unescape(
                match.group(1)
            ).strip()

    return url


def _convert_bbcode(
    text,
):
    """
    Convert common Steam Workshop BBCode
    into intermediate HTML.
    """

    if not text:

        return ""

    text = _escape_text(
        text
    )

    # -----------------------------
    # Headings
    # -----------------------------

    for level in range(1, 7):

        text = re.sub(
            rf"\[h{level}\](.*?)\[/h{level}\]",
            (
                rf"<h{level}>"
                rf"\1"
                rf"</h{level}>"
            ),
            text,
            flags=(
                re.IGNORECASE
                | re.DOTALL
            ),
        )

    # -----------------------------
    # Basic formatting
    # -----------------------------

    replacements = {
        "b": "b",
        "i": "i",
        "u": "u",
        "s": "s",
        "strike": "s",
        "del": "s",
        "code": "code",
    }

    for source, target in replacements.items():

        text = re.sub(
            rf"\[{source}\](.*?)\[/{source}\]",
            (
                rf"<{target}>"
                rf"\1"
                rf"</{target}>"
            ),
            text,
            flags=(
                re.IGNORECASE
                | re.DOTALL
            ),
        )

    # -----------------------------
    # URL with text
    # -----------------------------

    def replace_url_with_text(
        match,
    ):
        url = _fix_url(
            match.group(1)
        )

        content = match.group(2)

        return (
            '<a href="'
            f'{_escape_attribute(url)}'
            '">'
            f"{content}"
            "</a>"
        )

    text = re.sub(
        r"\[url=([^\]]+)\](.*?)\[/url\]",
        replace_url_with_text,
        text,
        flags=(
            re.IGNORECASE
            | re.DOTALL
        ),
    )

    # -----------------------------
    # Plain URL
    # -----------------------------

    def replace_plain_url(
        match,
    ):
        url = _fix_url(
            match.group(1)
        )

        return (
            '<a href="'
            f'{_escape_attribute(url)}'
            '">'
            f'{_escape_text(url)}'
            "</a>"
        )

    text = re.sub(
        r"\[url\](.*?)\[/url\]",
        replace_plain_url,
        text,
        flags=(
            re.IGNORECASE
            | re.DOTALL
        ),
    )

    # -----------------------------
    # Images
    # -----------------------------

    def replace_image(
        match,
    ):
        url = _fix_url(
            match.group(1)
        )

        return (
            '<img src="'
            f'{_escape_attribute(url)}'
            '"/>'
        )

    text = re.sub(
        r"\[img\](.*?)\[/img\]",
        replace_image,
        text,
        flags=(
            re.IGNORECASE
            | re.DOTALL
        ),
    )

    # -----------------------------
    # Quotes
    # -----------------------------

    text = re.sub(
        r"\[quote\](.*?)\[/quote\]",
        (
            r"<blockquote>"
            r"\1"
            r"</blockquote>"
        ),
        text,
        flags=(
            re.IGNORECASE
            | re.DOTALL
        ),
    )

    # -----------------------------
    # Lists
    # -----------------------------

    text = re.sub(
        r"\[list\](.*?)\[/list\]",
        (
            r"<ul>"
            r"\1"
            r"</ul>"
        ),
        text,
        flags=(
            re.IGNORECASE
            | re.DOTALL
        ),
    )

    text = re.sub(
        r"\[\*\](.*?)(?=\[\*\]|\[/list\])",
        r"<li>\1</li>",
        text,
        flags=(
            re.IGNORECASE
            | re.DOTALL
        ),
    )

    return text


def _replace_linked_images(
    soup,
):
    """
    Telegram RichMessage does not support
    clickable images.

    Convert:

        <a href="URL">
            <img src="IMAGE"/>
        </a>

    Into:

        <a href="URL">URL</a>
    """

    for link in soup.find_all(
        "a"
    ):

        image = link.find(
            "img"
        )

        if not image:
            continue

        href = (
            link.get("href")
            or ""
        ).strip()

        href = _fix_url(
            href
        )

        if not href:

            link.unwrap()
            continue

        replacement = soup.new_tag(
            "a"
        )

        replacement["href"] = href
        replacement.string = href

        link.replace_with(
            replacement
        )

    return soup


def _remove_empty_tags(
    soup,
):
    """
    Remove empty text blocks.
    """

    for tag_name in [
        "p",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "li",
        "blockquote",
    ]:

        for tag in soup.find_all(
            tag_name
        ):

            has_text = bool(
                tag.get_text(
                    strip=True
                )
            )

            has_media = bool(
                tag.find("img")
            )

            if (
                not has_text
                and not has_media
            ):

                tag.decompose()

    return soup


def _remove_unsupported_tags(
    soup,
):
    """
    Remove unsupported HTML tags while preserving
    Telegram RichMessage tg-* custom tags.
    """

    dangerous_tags = {
        "script",
        "style",
        "iframe",
        "svg",
        "noscript",
        "object",
        "embed",
    }

    for tag in soup.find_all(True):

        if tag.name in (
            "html",
            "body",
        ):
            continue

        # Keep known supported tags
        if tag.name in SUPPORTED_TAGS:
            continue

        # Preserve Telegram RichMessage tags
        if tag.name.startswith("tg-"):
            continue

        if tag.name in dangerous_tags:

            tag.decompose()

        else:

            tag.unwrap()

    return soup


def _cleanup_links(
    soup,
):
    """
    Remove invalid or empty links and
    fix Steam linkfilter URLs.
    """

    for link in soup.find_all(
        "a"
    ):

        href = (
            link.get("href")
            or ""
        ).strip()

        href = _fix_url(
            href
        )

        text = link.get_text(
            strip=True
        )

        if not href:

            link.unwrap()
            continue

        if not text:

            link.decompose()
            continue

        link["href"] = href

    return soup


def _cleanup_images(
    soup,
):
    """
    Remove images without valid src
    and fix Steam linkfilter URLs.
    """

    for image in soup.find_all(
        "img"
    ):

        src = (
            image.get("src")
            or ""
        ).strip()

        src = _fix_url(
            src
        )

        if not src:

            image.decompose()
            continue

        image["src"] = src

    return soup


def _strip_attributes(
    soup,
):
    """
    Keep supported attributes while preserving
    Telegram RichMessage custom tags.
    """

    for tag in soup.find_all(True):

        if tag.name == "a":

            href = tag.get("href")

            tag.attrs = {}

            if href:

                tag["href"] = _fix_url(
                    href
                )

        elif tag.name == "img":

            src = tag.get("src")

            tag.attrs = {}

            if src:

                tag["src"] = _fix_url(
                    src
                )

        elif tag.name == "details":

            is_open = (
                tag.has_attr("open")
            )

            tag.attrs = {}

            if is_open:

                tag["open"] = ""

        elif tag.name == "summary":

            tag.attrs = {}

        elif tag.name == "tg-button":

            button_type = tag.get("type")
            style = tag.get("style")
            url = tag.get("url")
            data = tag.get("data")

            tag.attrs = {}

            if button_type:

                tag["type"] = button_type

            if style:

                tag["style"] = style

            if url:

                tag["url"] = _fix_url(
                    url
                )

            if data:

                tag["data"] = data

        elif tag.name == "tg-button-row":

            align = tag.get("align")

            tag.attrs = {}

            if align:

                tag["align"] = align

        # Preserve Telegram custom tags.
        elif tag.name.startswith("tg-"):

            continue

        else:

            tag.attrs = {}

    return soup


def _convert_line_breaks(
    soup,
):
    """
    Convert plain newlines into <br>.
    """

    for text_node in list(
        soup.find_all(
            string=True
        )
    ):

        if not isinstance(
            text_node,
            NavigableString,
        ):

            continue

        if "\n" not in text_node:

            continue

        parts = str(
            text_node
        ).split(
            "\n"
        )

        replacement = []

        for index, part in enumerate(
            parts
        ):

            if part:

                replacement.append(
                    NavigableString(
                        part
                    )
                )

            if index < len(parts) - 1:

                replacement.append(
                    soup.new_tag("br")
                )

        if replacement:

            text_node.replace_with(
                *replacement
            )

    return soup


def clean_description(
    description,
):
    """
    Steam BBCode ->
    Telegram RichMessage HTML.
    """

    intermediate_html = (
        _convert_bbcode(
            description
        )
    )

    soup = BeautifulSoup(
        intermediate_html,
        "html.parser",
    )

    # Important:
    # Convert clickable images BEFORE
    # cleaning attributes/tags.
    soup = _replace_linked_images(
        soup
    )

    soup = _remove_unsupported_tags(
        soup
    )

    soup = _cleanup_links(
        soup
    )

    soup = _cleanup_images(
        soup
    )

    soup = _remove_empty_tags(
        soup
    )

    soup = _strip_attributes(
        soup
    )

    soup = _convert_line_breaks(
        soup
    )

    if soup.body:

        content = soup.body.decode_contents()

    else:

        content = str(
            soup
        )

    return content.strip()


def _create_button(
    text,
    url,
    style="primary",
):
    """
    Create Telegram RichMessage URL button.
    """

    safe_text = _escape_text(
        text
    )

    safe_url = _escape_attribute(
        _fix_url(url)
    )

    return (
        '<tg-button-row align="center">'
        '<tg-button '
        'type="url" '
        f'style="{style}" '
        f'url="{safe_url}">'
        f"{safe_text}"
        "</tg-button>"
        "</tg-button-row>"
    )


def _create_callback_button_row(
    workshop_id,
):
    """
    Preview-only Publish / Cancel controls.
    """

    publish_data = (
        f"publish:{workshop_id}"
    )

    cancel_data = (
        f"cancel:{workshop_id}"
    )

    return (
        '<tg-button-row align="center">'

        '<tg-button '
        'type="callback_data" '
        'style="success" '
        f'data="{publish_data}">'
        "Publish"
        "</tg-button>"

        '<tg-button '
        'type="callback_data" '
        'style="danger" '
        f'data="{cancel_data}">'
        "Cancel"
        "</tg-button>"

        "</tg-button-row>"
    )


def _build_game(
    item,
):
    """
    Build Workshop game information.
    """

    app_id = str(
        item.get(
            "consumer_app_id",
            ""
        )
        or ""
    )

    game_name = GAME_NAMES.get(
        app_id
    )

    if not game_name:

        return ""

    return (
        "<p>"
        "<b>Game:</b> "
        f"{_escape_text(game_name)}"
        "</p>"
    )


def _build_tags(
    item,
):
    """
    Build Workshop tags.
    """

    tags = item.get(
        "tags",
        [],
    )

    names = []

    for tag in tags:

        name = tag.get(
            "tag"
        )

        if name:

            names.append(
                _escape_text(
                    name
                )
            )

    if not names:

        return ""

    return (
        "<p>"
        "<b>Tags:</b> "
        f"{', '.join(names)}"
        "</p>"
    )


def _build_header(
    item,
):
    """
    Build the Workshop post header.

    Layout:

        Preview image
        Title
        Game
        Tags
    """

    title = _escape_text(
        item.get(
            "title",
            "Steam Workshop Item",
        )
    )

    preview_url = (
        item.get(
            "preview_url",
            ""
        )
        or ""
    ).strip()

    preview_url = _fix_url(
        preview_url
    )

    parts = []

    # Preview image always first.
    if preview_url:

        parts.append(
            "<figure>"
            f'<img src="{_escape_attribute(preview_url)}"/>'
            "</figure>"
        )

    # Title.
    parts.append(
        f"<h1>{title}</h1>"
    )

    # Game.
    game_html = _build_game(
        item
    )

    if game_html:

        parts.append(
            game_html
        )

    # Tags.
    tags_html = _build_tags(
        item
    )

    if tags_html:

        parts.append(
            tags_html
        )

    return "".join(
        parts
    )


def _get_file_size(
    item,
):
    """
    Get Workshop file size from
    available Steam API fields.
    """

    possible_keys = [
        "file_size",
        "filesize",
        "fileSize",
        "size",
    ]

    for key in possible_keys:

        value = item.get(
            key
        )

        if value:

            return value

    return 0


def _format_file_size(
    size,
):
    """
    Convert bytes into readable size.
    """

    try:

        size = int(
            size
            or 0
        )

    except (
        TypeError,
        ValueError,
    ):

        return ""

    if size <= 0:

        return ""

    units = [
        "B",
        "KB",
        "MB",
        "GB",
        "TB",
    ]

    index = 0
    value = float(
        size
    )

    while (
        value >= 1024
        and index < len(units) - 1
    ):

        value /= 1024
        index += 1

    if index == 0:

        return (
            f"{int(value)} "
            f"{units[index]}"
        )

    return (
        f"{value:.2f} "
        f"{units[index]}"
    )


def _format_timestamp(
    timestamp,
):
    """
    Convert Unix timestamp into
    readable UTC date and time.
    """

    try:

        timestamp = int(
            timestamp
            or 0
        )

    except (
        TypeError,
        ValueError,
    ):

        return ""

    if timestamp <= 0:

        return ""

    try:

        date = datetime.fromtimestamp(
            timestamp,
            tz=timezone.utc,
        )

        return date.strftime(
            "%d %B %Y, %H:%M UTC"
        )

    except (
        OSError,
        OverflowError,
        ValueError,
    ):

        return ""


def _build_information(
    item,
):
    """
    Build Workshop information.

    Includes:

        File size
        Posted date
        Updated date
    """

    file_size = _format_file_size(
        _get_file_size(
            item
        )
    )

    posted = _format_timestamp(
        item.get(
            "time_created",
            0,
        )
    )

    updated = _format_timestamp(
        item.get(
            "time_updated",
            0,
        )
    )

    parts = []

    if file_size:

        parts.append(
            "<li>"
            "<b>📦 File Size:</b> "
            f"{_escape_text(file_size)}"
            "</li>"
        )

    if posted:

        parts.append(
            "<li>"
            "<b>📅 Posted:</b> "
            f"{_escape_text(posted)}"
            "</li>"
        )

    if updated:

        parts.append(
            "<li>"
            "<b>🔄 Updated:</b> "
            f"{_escape_text(updated)}"
            "</li>"
        )

    if not parts:

        return ""

    return (
        "<details>"
        "<summary>Workshop Information</summary>"
        "<ul>"
        f"{''.join(parts)}"
        "</ul>"
        "</details>"
    )
    

def _build_description(
    item,
):
    """
    Put Steam description into
    a collapsible details section.
    """

    description = item.get(
        "description",
        ""
    )

    content = clean_description(
        description
    )

    if not content:

        return ""

    return (
        "<details>"
        "<summary>Description</summary>"
        f"{content}"
        "</details>"
    )


def _build_statistics(
    item,
):
    """
    Put Workshop statistics into
    a collapsible details section.
    """

    subscriptions = int(
        item.get(
            "subscriptions",
            0,
        )
        or 0
    )

    favorited = int(
        item.get(
            "favorited",
            0,
        )
        or 0
    )

    views = int(
        item.get(
            "views",
            0,
        )
        or 0
    )

    return (
        "<details>"
        "<summary>Workshop Statistics</summary>"

        "<ul>"

        "<li>"
        f"<b>Subscriptions:</b> "
        f"{subscriptions:,}"
        "</li>"

        "<li>"
        f"<b>Favorites:</b> "
        f"{favorited:,}"
        "</li>"

        "<li>"
        f"<b>Views:</b> "
        f"{views:,}"
        "</li>"

        "</ul>"

        "</details>"
    )


def _build_screenshots(
    item,
):
    """
    Build Workshop screenshots.

    Only show the section when there are
    more than one additional screenshots.
    """

    screenshots = item.get(
        "screenshots",
        [],
    )

    if len(screenshots) <= 1:

        return ""

    images = []

    for screenshot in screenshots:

        screenshot = _fix_url(
            screenshot
        )

        if not screenshot:

            continue

        images.append(
            '<img src="'
            f'{_escape_attribute(screenshot)}'
            '"/>'
        )

    if len(images) <= 1:

        return ""

    return (
        "<details>"
        "<summary>Screenshots</summary>"
        "<tg-slideshow>"
        f"{''.join(images)}"
        "</tg-slideshow>"
        "</details>"
    )


def build_workshop_post(
    item,
    preview=False,
):
    """
    Build complete Telegram RichMessage HTML.

    Final layout:

        Preview image
        Title
        Game
        Tags

        Description (details)

        Workshop Statistics (details)

        Screenshots

        View Steam Workshop button

        Publish / Cancel
        (preview only)
    """

    workshop_id = (
        item.get(
            "publishedfileid",
            ""
        )
        or ""
    )

    workshop_url = get_workshop_url(
        workshop_id
    )

    parts = []

    # -----------------------------
    # Header
    # -----------------------------

    parts.append(
        _build_header(
            item
        )
    )

    # -----------------------------
    # Description
    # -----------------------------

    description_html = (
        _build_description(
            item
        )
    )

    if description_html:

        parts.append(
            "<hr/>"
        )

        parts.append(
            description_html
        )

    # -----------------------------
    # Workshop Information
    # -----------------------------

    information_html = (
        _build_information(
            item
        )
    )

    if information_html:

        parts.append(
            "<hr/>"
        )

        parts.append(
            information_html
        )

    # -----------------------------
    # Statistics
    # -----------------------------

    parts.append(
        "<hr/>"
    )

    parts.append(
        _build_statistics(
            item
        )
    )

    # -----------------------------
    # Screenshots
    # -----------------------------

    screenshots_html = (
        _build_screenshots(
            item
        )
    )

    if screenshots_html:

        parts.append(
            "<hr/>"
        )

        parts.append(
            screenshots_html
        )

    # -----------------------------
    # Workshop button
    #
    # Always at bottom.
    # -----------------------------

    parts.append(
        "<hr/>"
    )

    parts.append(
        _create_button(
            "View in Steam Workshop",
            workshop_url,
            style="primary",
        )
    )

    # -----------------------------
    # Admin preview controls
    # -----------------------------

    if preview:

        parts.append(
            "<hr/>"
        )

        parts.append(
            _create_callback_button_row(
                workshop_id
            )
        )

    final_html = "".join(
        parts
    ).strip()

    if (
        len(final_html)
        > MAX_RICH_HTML_LENGTH
    ):

        print(
            "WARNING: Rich HTML exceeded "
            f"{MAX_RICH_HTML_LENGTH} characters"
        )

        final_html = final_html[
            :MAX_RICH_HTML_LENGTH
        ]

    print(
        "Workshop HTML built | "
        f"Length={len(final_html)}"
    )

    return final_html
