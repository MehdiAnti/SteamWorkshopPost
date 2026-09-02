import html
import re

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

    "tg-collapse",

    "tg-button",
    "tg-button-row",
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


def _convert_bbcode(
    text,
):
    """
    Convert common Steam Workshop BBCode
    into intermediate HTML.

    The Steam description is escaped first,
    then supported BBCode is converted.
    """

    if not text:

        return ""

    text = _escape_text(
        text
    )

    # ---------------------------------
    # Headings
    # ---------------------------------

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

    # ---------------------------------
    # Basic formatting
    # ---------------------------------

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

    # ---------------------------------
    # URL with label
    #
    # [url=https://example.com]Text[/url]
    # ---------------------------------

    text = re.sub(
        r"\[url=([^\]]+)\](.*?)\[/url\]",
        (
            r'<a href="\1">'
            r"\2"
            r"</a>"
        ),
        text,
        flags=(
            re.IGNORECASE
            | re.DOTALL
        ),
    )

    # ---------------------------------
    # Plain URL
    #
    # [url]https://example.com[/url]
    # ---------------------------------

    text = re.sub(
        r"\[url\](.*?)\[/url\]",
        (
            r'<a href="\1">'
            r"\1"
            r"</a>"
        ),
        text,
        flags=(
            re.IGNORECASE
            | re.DOTALL
        ),
    )

    # ---------------------------------
    # Images
    #
    # [img]https://example.com/image.jpg[/img]
    # ---------------------------------

    text = re.sub(
        r"\[img\](.*?)\[/img\]",
        r'<img src="\1"/>',
        text,
        flags=(
            re.IGNORECASE
            | re.DOTALL
        ),
    )

    # ---------------------------------
    # Quotes
    # ---------------------------------

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

    # ---------------------------------
    # Lists
    # ---------------------------------

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

    # ---------------------------------
    # Newlines
    # ---------------------------------

    text = text.replace(
        "\r\n",
        "\n",
    )

    text = text.replace(
        "\r",
        "\n",
    )

    return text


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

            has_button = bool(
                tag.find("tg-button")
            )

            if (
                not has_text
                and not has_media
                and not has_button
            ):

                tag.decompose()

    return soup


def _remove_unsupported_tags(
    soup,
):
    """
    Remove unsupported HTML tags.
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

        if tag.name in SUPPORTED_TAGS:
            continue

        if tag.name in dangerous_tags:

            tag.decompose()

        else:

            tag.unwrap()

    return soup


def _remove_clickable_image_wrappers(
    soup,
):
    """
    Telegram RichMessage images are not
    used as clickable image links.

    If an <img> is wrapped inside <a>,
    unwrap the link and preserve the image.
    """

    for image in soup.find_all(
        "img"
    ):

        parent = image.parent

        if (
            parent
            and parent.name == "a"
        ):

            parent.unwrap()

    return soup


def _cleanup_links(
    soup,
):
    """
    Remove invalid or empty links.
    """

    for link in soup.find_all(
        "a"
    ):

        href = (
            link.get("href")
            or ""
        ).strip()

        text = link.get_text(
            strip=True
        )

        if not href:

            link.unwrap()
            continue

        if not text:

            if link.find("img"):

                link.unwrap()

            else:

                link.decompose()

    return soup


def _cleanup_images(
    soup,
):
    """
    Remove images without valid src.
    """

    for image in soup.find_all(
        "img"
    ):

        src = (
            image.get("src")
            or ""
        ).strip()

        if not src:

            image.decompose()

    return soup


def _strip_attributes(
    soup,
):
    """
    Keep only RichMessage-supported
    attributes.
    """

    for tag in soup.find_all(True):

        # -----------------------------
        # Links
        # -----------------------------

        if tag.name == "a":

            href = tag.get(
                "href"
            )

            tag.attrs = {}

            if href:

                tag["href"] = href

        # -----------------------------
        # Images
        # -----------------------------

        elif tag.name == "img":

            src = tag.get(
                "src"
            )

            tag.attrs = {}

            if src:

                tag["src"] = src

        # -----------------------------
        # Ordered list
        # -----------------------------

        elif tag.name == "ol":

            start = tag.get(
                "start"
            )

            tag.attrs = {}

            if start:

                tag["start"] = start

        # -----------------------------
        # Telegram button
        # -----------------------------

        elif tag.name == "tg-button":

            button_type = tag.get(
                "type"
            )

            style = tag.get(
                "style"
            )

            url = tag.get(
                "url"
            )

            data = tag.get(
                "data"
            )

            tag.attrs = {}

            if button_type:

                tag["type"] = (
                    button_type
                )

            if style:

                tag["style"] = style

            if url:

                tag["url"] = url

            if data:

                tag["data"] = data

        # -----------------------------
        # Telegram button row
        # -----------------------------

        elif tag.name == "tg-button-row":

            align = tag.get(
                "align"
            )

            tag.attrs = {}

            if align:

                tag["align"] = align

        # -----------------------------
        # Everything else
        # -----------------------------

        else:

            tag.attrs = {}

    return soup


def _convert_line_breaks(
    soup,
):
    """
    Convert plain text newline sequences
    into <br> elements where appropriate.
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
                    soup.new_tag(
                        "br"
                    )
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

    soup = _remove_unsupported_tags(
        soup
    )

    soup = _remove_clickable_image_wrappers(
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
    Create a URL RichMessage button.
    """

    safe_text = _escape_text(
        text
    )

    safe_url = _escape_attribute(
        url
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


def _build_tags(
    item,
):
    """
    Build Workshop tag list.
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


def _build_statistics(
    item,
):
    """
    Build Workshop statistics block.
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


def _build_header(
    item,
):
    """
    Build Workshop post header.

    preview_url is always the top media.
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

    # Main Workshop button first.
    parts.append(
        _create_button(
            "Open Steam Workshop",
            workshop_url,
            style="primary",
        )
    )

    # Preview image directly below.
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

    # Tags.
    tags_html = _build_tags(
        item
    )

    if tags_html:

        parts.append(
            tags_html
        )

    parts.append(
        "<hr/>"
    )

    return "".join(
        parts
    )


def _build_description(
    item,
):
    """
    Put the Steam description inside
    a Telegram collapse block.
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
        "<tg-collapse>"
        "<summary>Description</summary>"
        f"{content}"
        "</tg-collapse>"
    )


def build_workshop_post(
    item,
    preview=False,
):
    """
    Build complete Telegram RichMessage HTML.

    preview=True adds admin-only
    Publish / Cancel controls.
    """

    workshop_id = (
        item.get(
            "publishedfileid",
            ""
        )
        or ""
    )

    parts = []

    parts.append(
        _build_header(
            item
        )
    )

    description_html = (
        _build_description(
            item
        )
    )

    if description_html:

        parts.append(
            description_html
        )

    parts.append(
        "<hr/>"
    )

    parts.append(
        _build_statistics(
            item
        )
    )

    parts.append(
        "<hr/>"
    )

    workshop_url = get_workshop_url(
        workshop_id
    )

    parts.append(
        _create_button(
            "Open Steam Workshop",
            workshop_url,
            style="primary",
        )
    )

    # Preview-only controls.
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

        final_html = (
            final_html[
                :MAX_RICH_HTML_LENGTH
            ]
        )

    return final_html
