#!/usr/bin/env python3
"""
FN Home Group | Wix Blog import step.

Runs during the Netlify build, BEFORE build/scripts/generate.py. It reads the
published posts out of the Wix Blog API and writes them to

    build/data/wixposts.json

which generate.py then renders into /blog and /blog/<slug>/ using the same
templates, stylesheet, header, and footer as every other page on the site.

WHY A SNAPSHOT FILE
  The API key is only ever used here, inside the build container, so it never
  reaches the browser, the generated HTML, or the repository. The snapshot is
  also the safety net: if Wix cannot be reached during some future build, the
  previous snapshot is reused and the blog keeps rendering exactly as it did
  before instead of collapsing into an empty page. If there is no snapshot at
  all to fall back on, this script exits non zero so the Netlify build fails
  and the currently published production site stays untouched.

CREDENTIALS
  WIX_API_KEY   Wix account API key (Netlify environment variable)
  WIX_SITE_ID   Wix site id (Netlify environment variable)
  Neither value is ever printed, written to a file, or included in an error
  message. Any accidental echo of the key in an upstream error body is
  redacted before it is logged.

CONTENT SAFETY
  Wix returns each post as Ricos rich content (a JSON node tree), not as HTML.
  Every node is rebuilt into a small allowlist of tags here, and all text and
  attribute values are escaped, so nothing authored in Wix can inject script,
  iframe, style, or event handler markup into the site. Node types outside the
  allowlist are skipped rather than passed through.

USAGE
    python3 build/scripts/wixblog.py            # fetch, then write snapshot
    python3 build/scripts/wixblog.py --offline  # skip the API, keep snapshot
"""

import json
import os
import re
import struct
import sys
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA = os.path.join(ROOT, "build", "data")
SNAPSHOT = os.path.join(DATA, "wixposts.json")

API_BASE = "https://www.wixapis.com"
POSTS_ENDPOINT = API_BASE + "/blog/v3/posts"
MEMBERS_ENDPOINT = API_BASE + "/members/v1/members"
PAGE_SIZE = 100
MAX_PAGES = 20
TIMEOUT = 25
IMAGE_TIMEOUT = 10
IMAGE_HEADER_BYTES = 2048
IMAGE_SIZE_CACHE = {}

SITE_URL = "https://www.fnhomegroup.com"

# The old Wix website. Visitors must never be handed back to it, so any link in
# imported content that points at one of these hosts is rewritten to the
# matching page on fnhomegroup.com.
OLD_SITE_HOSTS = {
    "havefaithinrealestate.com",
    "www.havefaithinrealestate.com",
}

OLD_PATH_MAP = {
    "": "/",
    "/": "/",
    "/home": "/",
    "/buying": "/buy.html",
    "/buy": "/buy.html",
    "/buyers": "/buy.html",
    "/selling": "/sell.html",
    "/sell": "/sell.html",
    "/sellers": "/sell.html",
    "/about": "/meetfaith.html",
    "/faith-nance": "/meetfaith.html",
    "/meet-faith": "/meetfaith.html",
    "/contact": "/contact.html",
    "/home-value": "/homevalue.html",
    "/whats-my-home-worth": "/homevalue.html",
    "/relocation": "/relocation.html",
    "/communities": "/communities.html",
    "/testimonials": "/testimonials.html",
    "/faq": "/faq.html",
    "/resources": "/resources.html",
    "/blog": "/blog",
}

MONTHS = ("January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December")

DEFAULT_AUTHOR = "Faith Nance"


# --------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------

def log(message):
    print("[wixblog] " + message)


def redact(text, secrets):
    out = text or ""
    for secret in secrets:
        if secret:
            out = out.replace(secret, "[redacted]")
    return out


def esc(value):
    """Escape a string for use as HTML text or as an attribute value."""
    return (str(value)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;"))


def load_json_file(path, fallback=None):
    if not os.path.exists(path):
        return fallback
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def community_slugs():
    data = load_json_file(os.path.join(DATA, "communities.json"), []) or []
    return {c["slug"] for c in data if c.get("slug")}


def public_scheduling_urls():
    config = load_json_file(os.path.join(DATA, "site-config.json"), {}) or {}
    return set((config.get("scheduling_links") or {}).values())


COMMUNITY_SLUGS = community_slugs()
PUBLIC_SCHEDULING_URLS = public_scheduling_urls()


# --------------------------------------------------------------------------
# link handling
# --------------------------------------------------------------------------

def map_old_site_path(path, slug_lookup):
    """Translate a path on the old Wix website to its fnhomegroup.com page."""
    clean = (path or "/").rstrip("/").lower() or "/"
    if clean in OLD_PATH_MAP:
        return OLD_PATH_MAP[clean]

    # Old blog post addresses were /post/<slug>.
    if clean.startswith("/post/"):
        post_slug = clean[len("/post/"):]
        if post_slug in slug_lookup:
            return "/blog/" + post_slug
        return "/blog"

    # Old listing pages looked like /spring-hill-tn-homes-for-sale.
    if clean.endswith("-homes-for-sale"):
        town = clean[1:].replace("-tn-homes-for-sale", "").replace("-homes-for-sale", "")
        town = town.replace("-", "")
        if town in COMMUNITY_SLUGS:
            return "/communities/" + town + ".html"
        return "/communities.html"

    # Anything else on the old site sends the visitor to the FN Home Group home
    # page rather than off to Wix.
    return "/"


def resolve_link(raw, slug_lookup):
    """Return (href, is_external) for a link found in imported content.

    Returns (None, False) when the address cannot be trusted, in which case the
    caller renders the link text as plain text.
    """
    url = (raw or "").strip()
    if not url:
        return None, False

    lowered = url.lower()
    if lowered.startswith(("javascript:", "data:", "vbscript:", "file:", "blob:")):
        return None, False
    if url.startswith("#"):
        return None, False
    if url.startswith("/"):
        return url, False
    if lowered.startswith(("mailto:", "tel:")):
        return url, False
    if not lowered.startswith(("http://", "https://")):
        return None, False

    parts = urllib.parse.urlsplit(url)
    host = parts.hostname or ""
    host = host.lower()

    if host in OLD_SITE_HOSTS or host.endswith(".wixsite.com") or host.endswith(".wixblog.com"):
        return map_old_site_path(parts.path, slug_lookup), False

    if host in ("fnhomegroup.com", "www.fnhomegroup.com"):
        internal = parts.path or "/"
        if parts.query:
            internal += "?" + parts.query
        if parts.fragment:
            internal += "#" + parts.fragment
        return internal, False

    # Scheduling addresses are held to the same rule as the rest of the site:
    # only the publicly bookable events named in site-config.json may be
    # published. Anything else becomes an on site contact link.
    if host.endswith("calendly.com"):
        if url in PUBLIC_SCHEDULING_URLS:
            return url, True
        return "/contact.html", False

    return url, True


# --------------------------------------------------------------------------
# Ricos rich content to HTML
# --------------------------------------------------------------------------

def decoration_map(decorations):
    found = {}
    for decoration in decorations or []:
        kind = decoration.get("type")
        if kind == "LINK":
            link = ((decoration.get("linkData") or {}).get("link") or {})
            found["LINK"] = link.get("url") or ""
        elif kind in ("BOLD", "ITALIC", "UNDERLINE"):
            found[kind] = True
    return found


def render_text_node(node, slug_lookup):
    text_data = node.get("textData") or {}
    text = text_data.get("text", "")
    if text == "":
        return ""
    html = esc(text)
    marks = decoration_map(text_data.get("decorations"))

    if marks.get("BOLD"):
        html = "<strong>" + html + "</strong>"
    if marks.get("ITALIC"):
        html = "<em>" + html + "</em>"

    if "LINK" in marks:
        href, external = resolve_link(marks["LINK"], slug_lookup)
        if href:
            attrs = ' href="' + esc(href) + '"'
            if external:
                attrs += ' target="_blank" rel="noopener noreferrer"'
            return "<a" + attrs + ">" + html + "</a>"
        return html

    if marks.get("UNDERLINE"):
        html = "<u>" + html + "</u>"
    return html


def render_inline(nodes, slug_lookup):
    out = []
    for node in nodes or []:
        kind = node.get("type")
        if kind == "TEXT":
            out.append(render_text_node(node, slug_lookup))
        else:
            # Anything unexpected inline still contributes its readable text.
            out.append(render_inline(node.get("nodes"), slug_lookup))
    return "".join(out)


def image_source(image):
    """Return the absolute URL for a Ricos image node.

    Wix hands the address back in a few shapes: a plain url, a nested
    {"src": {"url": ...}}, or a media id that has to be joined onto the Wix
    static host.
    """
    node = image or {}
    candidates = [node, node.get("src") or {}]
    for candidate in candidates:
        url = (candidate.get("url") or "").strip()
        if url.lower().startswith(("http://", "https://")):
            return url
        media_id = (candidate.get("id") or "").strip()
        if media_id and not media_id.lower().startswith(("http://", "https://")):
            return "https://static.wixstatic.com/media/" + media_id
        if media_id:
            return media_id
    return ""


def parse_image_header(data):
    """Read the pixel dimensions out of the opening bytes of an image file.

    Handles the formats Wix and Marblism serve (WebP, PNG, JPEG, GIF) and
    returns None for anything it does not recognise.
    """
    if len(data) < 24:
        return None

    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        kind = data[12:16]
        if kind == b"VP8 " and data[23:26] == b"\x9d\x01\x2a":
            width, height = struct.unpack("<HH", data[26:30])
            return width & 0x3FFF, height & 0x3FFF
        if kind == b"VP8L":
            bits = struct.unpack("<I", data[21:25])[0]
            return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
        if kind == b"VP8X":
            width = data[24] | data[25] << 8 | data[26] << 16
            height = data[27] | data[28] << 8 | data[29] << 16
            return width + 1, height + 1
        return None

    if data[:8] == b"\x89PNG\r\n\x1a\n" and data[12:16] == b"IHDR":
        width, height = struct.unpack(">II", data[16:24])
        return width, height

    if data[:6] in (b"GIF87a", b"GIF89a"):
        width, height = struct.unpack("<HH", data[6:10])
        return width, height

    if data[:2] == b"\xff\xd8":
        index = 2
        limit = len(data)
        while index + 9 < limit:
            if data[index] != 0xFF:
                index += 1
                continue
            marker = data[index + 1]
            if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD9:
                index += 2
                continue
            length = struct.unpack(">H", data[index + 2:index + 4])[0]
            if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
                height, width = struct.unpack(">HH", data[index + 5:index + 9])
                return width, height
            index += 2 + length
        return None

    return None


def real_image_size(url):
    """Return the true (width, height) of an image, or None.

    Wix reports whatever dimensions were recorded when the post was written,
    and for posts imported from another tool that can be a placeholder that
    does not match the file actually being served. Reading a few bytes of the
    real file keeps the width and height attributes honest, so the browser
    reserves the correct space and the article does not shift as the images
    load. Only a byte range of each image is requested, no credentials are
    involved, and a failure here is never fatal: the attributes are left off
    and the layout still works.
    """
    if not url.lower().startswith(("http://", "https://")):
        return None
    if url in IMAGE_SIZE_CACHE:
        return IMAGE_SIZE_CACHE[url]

    size = None
    try:
        request = urllib.request.Request(url, method="GET")
        request.add_header("Range", "bytes=0-%d" % (IMAGE_HEADER_BYTES - 1))
        request.add_header("Accept", "image/*")
        with urllib.request.urlopen(request, timeout=IMAGE_TIMEOUT) as response:
            size = parse_image_header(response.read(IMAGE_HEADER_BYTES))
    except Exception:
        size = None
    if size and (size[0] < 1 or size[1] < 1):
        size = None

    IMAGE_SIZE_CACHE[url] = size
    return size


def image_dimensions(image, url):
    """Prefer the measured size of the file, fall back to what Wix reported."""
    measured = real_image_size(url)
    if measured:
        return measured
    node = image or {}
    try:
        width = int(node.get("width") or 0)
        height = int(node.get("height") or 0)
    except (TypeError, ValueError):
        return None
    if width > 0 and height > 0:
        return width, height
    return None


def render_image(node):
    image_data = node.get("imageData") or {}
    image = image_data.get("image") or {}
    src = image_source(image)
    if not src:
        return ""

    attrs = ['src="' + esc(src) + '"']
    attrs.append('alt="' + esc(image_data.get("altText") or "") + '"')
    size = image_dimensions(image, src)
    if size:
        attrs.append('width="' + esc(size[0]) + '"')
        attrs.append('height="' + esc(size[1]) + '"')
    attrs.append('loading="lazy"')
    attrs.append('decoding="async"')

    caption = (image_data.get("caption") or "").strip()
    figure = '<figure class="blog-figure"><img ' + " ".join(attrs) + ">"
    if caption:
        figure += "<figcaption>" + esc(caption) + "</figcaption>"
    return figure + "</figure>"


def render_list(node, slug_lookup):
    tag = "ol" if node.get("type") == "ORDERED_LIST" else "ul"
    items = []
    for item in node.get("nodes") or []:
        if item.get("type") != "LIST_ITEM":
            continue
        inner = []
        for child in item.get("nodes") or []:
            if child.get("type") == "PARAGRAPH":
                inner.append(render_inline(child.get("nodes"), slug_lookup))
            elif child.get("type") in ("BULLETED_LIST", "ORDERED_LIST"):
                inner.append(render_list(child, slug_lookup))
            else:
                inner.append(render_node(child, slug_lookup))
        body = "".join(piece for piece in inner if piece)
        if body.strip():
            items.append("<li>" + body + "</li>")
    if not items:
        return ""
    return "<" + tag + ' class="blog-list">' + "".join(items) + "</" + tag + ">"


def render_table(node, slug_lookup):
    rows = [row for row in (node.get("nodes") or []) if row.get("type") == "TABLE_ROW"]
    if not rows:
        return ""

    def cells_of(row):
        return [cell for cell in (row.get("nodes") or []) if cell.get("type") == "TABLE_CELL"]

    def cell_html(cell):
        pieces = []
        for child in cell.get("nodes") or []:
            if child.get("type") == "PARAGRAPH":
                pieces.append(render_inline(child.get("nodes"), slug_lookup))
            else:
                pieces.append(render_node(child, slug_lookup))
        return "".join(piece for piece in pieces if piece)

    head = "".join("<th scope=\"col\">" + cell_html(cell) + "</th>" for cell in cells_of(rows[0]))
    body = []
    for row in rows[1:]:
        body.append("<tr>" + "".join("<td>" + cell_html(cell) + "</td>" for cell in cells_of(row)) + "</tr>")

    return ('<div class="blog-table-wrap"><table class="blog-table"><thead><tr>'
            + head + "</tr></thead><tbody>" + "".join(body) + "</tbody></table></div>")


def render_node(node, slug_lookup):
    kind = node.get("type")

    if kind == "PARAGRAPH":
        inner = render_inline(node.get("nodes"), slug_lookup)
        if not re.sub(r"(&nbsp;|\s)+", "", inner):
            return ""
        return "<p>" + inner + "</p>"

    if kind == "HEADING":
        level = int(((node.get("headingData") or {}).get("level")) or 2)
        # The post title is the page h1, so imported headings start at h2.
        level = min(max(level, 2), 5)
        inner = render_inline(node.get("nodes"), slug_lookup)
        if not inner.strip():
            return ""
        return "<h{0}>{1}</h{0}>".format(level, inner)

    if kind in ("BULLETED_LIST", "ORDERED_LIST"):
        return render_list(node, slug_lookup)

    if kind == "IMAGE":
        return render_image(node)

    if kind == "DIVIDER":
        return '<hr class="blog-divider">'

    if kind == "TABLE":
        return render_table(node, slug_lookup)

    if kind == "BLOCKQUOTE":
        pieces = [render_node(child, slug_lookup) for child in node.get("nodes") or []]
        inner = "".join(piece for piece in pieces if piece)
        if not inner.strip():
            return ""
        return '<blockquote class="blog-quote">' + inner + "</blockquote>"

    if kind == "CODE_BLOCK":
        inner = render_inline(node.get("nodes"), slug_lookup)
        if not inner.strip():
            return ""
        return "<pre class=\"blog-code\"><code>" + inner + "</code></pre>"

    if kind == "BULLETED_LIST_ITEM" or kind == "LIST_ITEM":
        return render_inline(node.get("nodes"), slug_lookup)

    # Everything else (embeds, raw HTML, video, buttons, polls, galleries) is
    # intentionally left out rather than trusted.
    return ""


def rich_content_to_html(rich_content, slug_lookup):
    nodes = (rich_content or {}).get("nodes") or []
    pieces = [render_node(node, slug_lookup) for node in nodes]
    return "\n".join(piece for piece in pieces if piece)


# --------------------------------------------------------------------------
# Wix API
# --------------------------------------------------------------------------

class WixError(Exception):
    pass


def api_get(url, api_key, site_id):
    request = urllib.request.Request(url, method="GET")
    request.add_header("Authorization", api_key)
    request.add_header("wix-site-id", site_id)
    request.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        try:
            detail = error.read().decode("utf-8", "replace")[:400]
        except Exception:
            detail = ""
        raise WixError("HTTP %s from %s %s" % (
            error.code, urllib.parse.urlsplit(url).path, detail))
    except urllib.error.URLError as error:
        raise WixError("network error reaching %s: %s" % (
            urllib.parse.urlsplit(url).netloc, error.reason))
    except json.JSONDecodeError as error:
        raise WixError("unreadable JSON from %s: %s" % (
            urllib.parse.urlsplit(url).path, error))


def fetch_published_posts(api_key, site_id):
    """Return every PUBLISHED post, newest first.

    /blog/v3/posts is the published collection: drafts and scheduled posts live
    behind a separate draft endpoint that this build never calls.
    """
    collected = []
    offset = 0
    for _ in range(MAX_PAGES):
        query = urllib.parse.urlencode({
            "paging.limit": PAGE_SIZE,
            "paging.offset": offset,
            "sort": "PUBLISHED_DATE_DESC",
            "fieldsets": "RICH_CONTENT",
        })
        payload = api_get(POSTS_ENDPOINT + "?" + query, api_key, site_id)
        page = payload.get("posts") or []
        collected.extend(page)
        total = (payload.get("metaData") or {}).get("total")
        offset += len(page)
        if not page or (total is not None and offset >= total):
            break
    return collected


def fetch_author_name(member_id, api_key, site_id, cache):
    """Return the display name for a post author, or the brand name."""
    if not member_id:
        return DEFAULT_AUTHOR
    if member_id in cache:
        return cache[member_id]
    name = DEFAULT_AUTHOR
    try:
        payload = api_get(MEMBERS_ENDPOINT + "/" + urllib.parse.quote(member_id),
                          api_key, site_id)
        profile = ((payload.get("member") or {}).get("profile") or {})
        # Only the public display name is read. No other member detail is
        # stored or published.
        nickname = (profile.get("nickname") or "").strip()
        if nickname:
            name = nickname
    except WixError as error:
        log("author name unavailable, using %s (%s)" % (DEFAULT_AUTHOR, error))
    cache[member_id] = name
    return name


# --------------------------------------------------------------------------
# normalising a post for the generator
# --------------------------------------------------------------------------

def cover_image(media):
    node = media or {}
    candidates = [
        ((node.get("wixMedia") or {}).get("image") or {}),
        (node.get("wixMedia") or {}),
        ((node.get("embedMedia") or {}).get("thumbnail") or {}),
    ]
    for candidate in candidates:
        url = image_source(candidate)
        if url.lower().startswith(("http://", "https://")):
            size = image_dimensions(candidate, url)
            return {
                "url": url,
                "width": size[0] if size else 0,
                "height": size[1] if size else 0,
                "alt": (node.get("altText") or "").strip(),
            }
    return None


def display_date(iso_value):
    match = re.match(r"(\d{4})-(\d{2})-(\d{2})", iso_value or "")
    if not match:
        return ""
    year, month, day = match.groups()
    index = int(month) - 1
    if index < 0 or index > 11:
        return ""
    return "%s %d, %s" % (MONTHS[index], int(day), year)


def shorten(text, limit):
    clean = re.sub(r"\s+", " ", (text or "")).strip()
    clean = clean.rstrip(". ").strip()
    if len(clean) <= limit:
        return clean
    cut = clean[:limit].rsplit(" ", 1)[0].rstrip(",;: ")
    return cut + "..."


def normalise(post, author_name, slug_lookup):
    title = (post.get("title") or "").strip()
    slug = (post.get("slug") or "").strip().strip("/")
    excerpt_source = (post.get("customExcerpt") or post.get("excerpt") or "").strip()
    body_html = rich_content_to_html(post.get("richContent"), slug_lookup)
    published = post.get("firstPublishedDate") or post.get("lastPublishedDate") or ""

    return {
        "id": post.get("id") or "",
        "slug": slug,
        "title": title,
        "excerpt": shorten(excerpt_source, 210),
        "meta_description": shorten(excerpt_source, 155),
        "author": author_name,
        "published": published,
        "updated": post.get("lastPublishedDate") or published,
        "published_display": display_date(published),
        "minutes_to_read": int(post.get("minutesToRead") or 0),
        "cover": cover_image(post.get("media")),
        "body_html": body_html,
        "canonical": "/blog/" + slug if slug else "/blog",
    }


def usable(post):
    return bool(post.get("slug") and post.get("title") and post.get("body_html"))


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def keep_previous(reason, previous):
    """Reuse the committed snapshot so a build never empties the blog."""
    if previous and previous.get("posts"):
        log("WARNING: %s" % reason)
        log("Reusing the previous snapshot of %d post(s); /blog is unchanged."
            % len(previous["posts"]))
        return 0
    log("ERROR: %s" % reason)
    log("No previous snapshot exists to fall back on, so this build is being "
        "stopped on purpose. The currently published site stays exactly as it "
        "is until a build can read the blog again.")
    return 1


def main():
    previous = load_json_file(SNAPSHOT)
    offline = "--offline" in sys.argv[1:]

    api_key = os.environ.get("WIX_API_KEY", "").strip()
    site_id = os.environ.get("WIX_SITE_ID", "").strip()
    secrets = [api_key, site_id]

    if offline:
        return keep_previous("running with --offline, the Wix API was not called", previous)

    if not api_key or not site_id:
        missing = " and ".join(
            name for name, value in (("WIX_API_KEY", api_key), ("WIX_SITE_ID", site_id))
            if not value)
        return keep_previous("%s is not set in this environment" % missing, previous)

    try:
        raw_posts = fetch_published_posts(api_key, site_id)
    except WixError as error:
        return keep_previous("Wix Blog API request failed: %s"
                             % redact(str(error), secrets), previous)

    slug_lookup = {(p.get("slug") or "").strip().strip("/") for p in raw_posts}
    slug_lookup.discard("")

    author_cache = {}
    posts = []
    for raw in raw_posts:
        author = fetch_author_name(raw.get("memberId"), api_key, site_id, author_cache)
        post = normalise(raw, author, slug_lookup)
        if usable(post):
            posts.append(post)
        else:
            log("Skipping a post that is missing a title, slug, or body.")

    posts.sort(key=lambda p: p.get("published") or "", reverse=True)

    if not posts:
        return keep_previous("the Wix Blog API returned no usable published posts",
                             previous)

    snapshot = {
        "_comment": ("Generated by build/scripts/wixblog.py from the Wix Blog API "
                     "during the Netlify build. Rendered into /blog and "
                     "/blog/<slug>/ by build/scripts/generate.py. Published posts "
                     "only. Contains no credentials. Committed on purpose so the "
                     "blog still renders if a future build cannot reach Wix."),
        "source": "wix-blog-v3-posts",
        "posts": posts,
    }

    os.makedirs(DATA, exist_ok=True)
    with open(SNAPSHOT, "w", encoding="utf-8") as handle:
        json.dump(snapshot, handle, indent=2, ensure_ascii=False)
        handle.write("\n")

    log("Imported %d published post(s) from the Wix Blog API." % len(posts))
    for post in posts:
        log("   /blog/%s  (%s)" % (post["slug"], post["published_display"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
