#!/usr/bin/env python3
"""
FN Home Group static site generator.

This script assembles the deployable static website from:
  - build/templates/base.html   (page shell: <head>, nav include, footer include)
  - build/templates/nav.html    (shared site navigation, injected into every page)
  - build/templates/footer.html (shared site footer, injected into every page)
  - build/pages/*.html          (one fragment file per hand-authored page, with
                                  a simple front-matter block for SEO metadata)
  - build/data/communities.json (data used to generate one page per community)
  - build/data/articles.json    (data used to generate one page per article)
  - build/data/site-config.json ("scheduling_links": the one place every
                                  scheduling button's destination is defined)
  - build/templates/community-fragment.html  (template for community pages)
  - build/templates/article-fragment.html    (template for article pages)

Output is written to the project root (the folder that gets deployed to Netlify).

USAGE:
    python3 build/scripts/generate.py

Re-run this script any time you edit a fragment in build/pages/, a data file in
build/data/, or a shared template in build/templates/. It safely overwrites the
previously generated HTML files; it does not touch assets, forms config, or any
file outside of the generated page set.
"""

import json
import os
import re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BUILD = os.path.join(ROOT, "build")
TEMPLATES = os.path.join(BUILD, "templates")
PAGES = os.path.join(BUILD, "pages")
DATA = os.path.join(BUILD, "data")

SITE_URL = "https://www.fnhomegroup.com"
DEFAULT_OG_IMAGE = SITE_URL + "/assets/logos/fnhomegrouplogo.png"

# Any calendly.com address at all found in a page about to be written must be
# one of the publicly bookable events listed in site-config.json. Faith's
# client-only events (check ins, contract timeline reviews, offer reviews) are
# never stored in this repository -- the repository root is what gets published
# -- and this guard is what stops one from being pasted into a page by mistake.
SCHEDULING_HOST_PATTERN = re.compile(r"https?://(?:[\w-]+\.)*calendly\.com/[^\s\"'<>]*")


def read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write(path, content):
    check_public_scheduling_only(content, path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def load_scheduling_links():
    """Return the {token: destination} map from build/data/site-config.json.

    Templates and page fragments never hard-code a scheduling address; they
    write a token such as {{SCHEDULE_BUYER}} and the generator fills it in, so
    every scheduling button on the site is defined in exactly one place.
    """
    config_path = os.path.join(DATA, "site-config.json")
    if not os.path.exists(config_path):
        return {}
    return json.loads(read(config_path)).get("scheduling_links", {})


SCHEDULING_LINKS = load_scheduling_links()
PUBLIC_SCHEDULING_URLS = frozenset(SCHEDULING_LINKS.values())


def fill_scheduling_links(html):
    """Replace every {{SCHEDULE_*}} token with its destination."""
    def repl(match):
        token = match.group(1)
        if token not in SCHEDULING_LINKS:
            raise ValueError(
                "Unknown scheduling token {{%s}}. Add it to 'scheduling_links' "
                "in build/data/site-config.json first." % token
            )
        return SCHEDULING_LINKS[token]
    return re.sub(r"\{\{(SCHEDULE_\w+)\}\}", repl, html)


def check_public_scheduling_only(html, path):
    """Refuse to write a page that links to a scheduling event we don't publish.

    Every calendly.com address in generated output has to be one of the public
    events in site-config.json, so a private client-only booking link can never
    reach the deployed site.
    """
    for url in SCHEDULING_HOST_PATTERN.findall(html):
        if url not in PUBLIC_SCHEDULING_URLS:
            raise ValueError(
                "%s links to a scheduling address that is not a published "
                "public event: %s. Use a {{SCHEDULE_*}} token instead."
                % (os.path.relpath(path, ROOT), url)
            )


def parse_frontmatter(text):
    """Split a fragment file into a metadata dict and the HTML body."""
    parts = text.split("\n---\n", 1)
    if len(parts) != 2:
        raise ValueError("Fragment file missing '---' front matter separator")
    meta_block, body = parts
    meta = {}
    for line in meta_block.strip().splitlines():
        if not line.strip() or ":" not in line:
            continue
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip()
    return meta, body.strip()


def schema_block(meta):
    """Return a JSON-LD <script> block based on the 'schema' front-matter key."""
    schema_type = meta.get("schema", "none")
    if schema_type == "none" or not schema_type:
        return ""

    if schema_type == "person":
        data = {
            "@context": "https://schema.org",
            "@type": "RealEstateAgent",
            "name": "Faith Nance",
            "jobTitle": "REALTOR®",
            "worksFor": {
                "@type": "RealEstateAgent",
                "name": "Epique Realty"
            },
            "url": SITE_URL,
            "image": SITE_URL + "/assets/headshots/faithnanceheadshot.jpg",
            "telephone": "931-332-6089",
            "email": "faithnance@epique.me",
            "areaServed": "Southern Middle Tennessee"
        }
    elif schema_type == "localbusiness":
        data = {
            "@context": "https://schema.org",
            "@type": "RealEstateAgent",
            "name": "FN Home Group | Faith Nance, REALTOR® — Epique Realty",
            "image": SITE_URL + "/assets/logos/fnhomegrouplogo.png",
            "url": SITE_URL,
            "telephone": "931-332-6089",
            "email": "faithnance@epique.me",
            "address": {
                "@type": "PostalAddress",
                "streetAddress": "40 Burton Hills Blvd. #200",
                "addressLocality": "Nashville",
                "addressRegion": "TN",
                "postalCode": "37215",
                "addressCountry": "US"
            },
            "areaServed": "Southern Middle Tennessee"
        }
    elif schema_type == "faq":
        return meta.get("_faq_json", "")
    else:
        return ""

    return '<script type="application/ld+json">\n' + json.dumps(data, indent=2, ensure_ascii=False) + "\n</script>"


def rootify_links(html, root_prefix):
    """Rewrite root-absolute hrefs/srcs (e.g. "/assets/styles.css", "/buy.html")
    into paths relative to a given page's own location (e.g. "assets/styles.css"
    or "../assets/styles.css"). Root-absolute paths are correct once the site is
    deployed to a domain root (e.g. Netlify), but they silently 404 if someone
    opens a page directly from disk via file://, which breaks every stylesheet,
    script, and image on the page (no CSS = no circular headshot mask, no
    carousel positioning; no JS = no autoplay/dots/arrows). Making every link
    relative means the site works identically both ways, with no downside for
    real hosting.
    Leaves alone: full URLs (http/https), protocol-relative ("//..."), and the
    already-templated {{...}} tokens/absolute SITE_URL references used in
    canonical/schema/OG tags.
    """
    # Home link ("/") needs an explicit filename once it's relative.
    html = re.sub(r'href="/"', 'href="' + root_prefix + 'index.html"', html)
    # Any other root-absolute href/src -> same path, relative-prefixed.
    html = re.sub(
        r'(href|src)="/(?!/)([^"]*)"',
        lambda m: '{}="{}{}"'.format(m.group(1), root_prefix, m.group(2)),
        html,
    )
    return html


def render_page(meta, body, base_tpl, nav_tpl, footer_tpl, extra_schema=None,
                root_prefix="", rootify=True):
    canonical_path = meta.get("canonical", "/")
    canonical = SITE_URL + canonical_path
    html = base_tpl
    html = html.replace("{{TITLE}}", meta.get("title", "FN Home Group"))
    html = html.replace("{{OG_TITLE}}", meta.get("title", "FN Home Group"))
    html = html.replace("{{DESCRIPTION}}", meta.get("description", ""))
    html = html.replace("{{CANONICAL}}", canonical)
    html = html.replace("{{OG_TYPE}}", meta.get("ogtype", "website"))
    html = html.replace("{{OG_IMAGE}}", meta.get("ogimage", DEFAULT_OG_IMAGE))
    html = html.replace("{{BODY_CLASS}}", meta.get("bodyclass", ""))
    schema = extra_schema if extra_schema is not None else schema_block(meta)
    html = html.replace("{{SCHEMA}}", schema)
    html = html.replace("{{NAV}}", nav_tpl)
    html = html.replace("{{FOOTER}}", footer_tpl)
    html = html.replace("{{CONTENT}}", body)
    html = fill_scheduling_links(html)
    if rootify:
        html = rootify_links(html, root_prefix)
    return html


def redirected_paths():
    """Return the set of page paths that netlify.toml permanently redirects away.

    Some pages exist twice on purpose: the current dash-free address plus the
    older hyphenated address it replaced, which netlify.toml 301s to the new
    one. Both are generated so the old address keeps working, but only the
    destination belongs in the sitemap -- listing a permanently redirected URL
    there sends search engines to a page that immediately redirects.
    """
    config_path = os.path.join(ROOT, "netlify.toml")
    if not os.path.exists(config_path):
        return set()
    blocks = re.findall(
        r'from\s*=\s*"([^"]+)"\s*\n\s*to\s*=\s*"[^"]*"\s*\n\s*status\s*=\s*301',
        read(config_path),
    )
    return set(blocks)


def fill_tokens(template_str, tokens):
    def repl(match):
        key = match.group(1)
        return str(tokens.get(key, ""))
    return re.sub(r"\{\{(\w+)\}\}", repl, template_str)


# ---------------------------------------------------------------------------
# Blog pages (imported from the Wix Blog by build/scripts/wixblog.py)
# ---------------------------------------------------------------------------

BLOG_SNAPSHOT = os.path.join(DATA, "wixposts.json")


def esc_attr(value):
    """Escape a value for use in HTML text or an attribute."""
    return (str(value)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;"))


def read_time(post):
    minutes = int(post.get("minutes_to_read") or 0)
    if minutes < 1:
        return ""
    return "%d minute read" % minutes


def post_meta_line(post, separator=" &middot; "):
    """Author, publication date, and reading time, in the site's meta style."""
    parts = [post.get("author") or "", post.get("published_display") or "",
             read_time(post)]
    return separator.join(part for part in parts if part)


def cover_img_tag(post, css_class, sizes=None):
    cover = post.get("cover") or {}
    url = cover.get("url") or ""
    if not url:
        return ""
    attrs = ['src="%s"' % esc_attr(url)]
    alt = cover.get("alt") or post.get("title") or ""
    attrs.append('alt="%s"' % esc_attr(alt))
    if cover.get("width"):
        attrs.append('width="%d"' % int(cover["width"]))
    if cover.get("height"):
        attrs.append('height="%d"' % int(cover["height"]))
    if sizes:
        attrs.append('sizes="%s"' % esc_attr(sizes))
    attrs.append('decoding="async"')
    return '<div class="%s"><img %s></div>' % (css_class, " ".join(attrs))


def blog_card(post, featured=False):
    """One post card for the blog index, built from the site's card styles."""
    href = "/blog/" + post["slug"]
    title = esc_attr(post.get("title") or "")
    excerpt = esc_attr(post.get("excerpt") or "")
    meta = post_meta_line(post)

    if featured:
        media = cover_img_tag(post, "blog-feature-media")
        media = media.replace("<img ", '<img loading="eager" fetchpriority="high" ')
        return (
            '<a class="blog-feature" href="%s">'
            '%s'
            '<div class="blog-feature-text">'
            '<span class="tag">Latest post</span>'
            '<h2>%s</h2>'
            '<p class="blog-card-meta">%s</p>'
            '<p>%s</p>'
            '<span class="blog-card-link">Read the full article</span>'
            '</div></a>'
        ) % (href, media, title, meta, excerpt)

    media = cover_img_tag(post, "blog-card-media")
    media = media.replace("<img ", '<img loading="lazy" ')
    return (
        '<a class="card blog-card" href="%s">'
        '%s'
        '<div class="blog-card-text">'
        '<h3>%s</h3>'
        '<p class="blog-card-meta">%s</p>'
        '<p>%s</p>'
        '<span class="blog-card-link">Read the full article</span>'
        '</div></a>'
    ) % (href, media, title, meta, excerpt)


def blog_post_schema(post):
    """JSON-LD plus the article specific head tags for a single blog post."""
    canonical = SITE_URL + "/blog/" + post["slug"]
    image = (post.get("cover") or {}).get("url") or DEFAULT_OG_IMAGE
    data = {
        "@context": "https://schema.org",
        "@type": "BlogPosting",
        "headline": post.get("title", ""),
        "description": post.get("meta_description", ""),
        "image": image,
        "datePublished": post.get("published", ""),
        "dateModified": post.get("updated") or post.get("published", ""),
        "author": {
            "@type": "Person",
            "name": post.get("author") or "Faith Nance",
            "url": SITE_URL + "/meetfaith.html"
        },
        "publisher": {
            "@type": "RealEstateAgent",
            "name": "FN Home Group",
            "logo": {
                "@type": "ImageObject",
                "url": SITE_URL + "/assets/logos/fnhomegrouplogo.png"
            }
        },
        "mainEntityOfPage": {"@type": "WebPage", "@id": canonical},
        "url": canonical,
        "isPartOf": {"@type": "Blog", "name": "FN Home Group Blog",
                     "url": SITE_URL + "/blog"}
    }
    head = ['<meta property="article:published_time" content="%s">'
            % esc_attr(post.get("published", ""))]
    if post.get("updated"):
        head.append('<meta property="article:modified_time" content="%s">'
                     % esc_attr(post["updated"]))
    head.append('<meta property="article:author" content="%s">'
                % esc_attr(post.get("author") or "Faith Nance"))
    head.append('<script type="application/ld+json">\n'
                + json.dumps(data, indent=2, ensure_ascii=False) + "\n</script>")
    return "\n".join(head)


def blog_index_schema(posts):
    data = {
        "@context": "https://schema.org",
        "@type": "Blog",
        "name": "FN Home Group Blog",
        "description": ("Real estate notes, neighborhood comparisons, and market "
                        "guidance for Southern Middle Tennessee from Faith Nance, "
                        "REALTOR\u00ae."),
        "url": SITE_URL + "/blog",
        "publisher": {"@type": "RealEstateAgent", "name": "FN Home Group",
                      "url": SITE_URL},
        "blogPost": [
            {
                "@type": "BlogPosting",
                "headline": post.get("title", ""),
                "url": SITE_URL + "/blog/" + post["slug"],
                "datePublished": post.get("published", ""),
                "author": {"@type": "Person",
                           "name": post.get("author") or "Faith Nance"}
            }
            for post in posts
        ]
    }
    return ('<script type="application/ld+json">\n'
            + json.dumps(data, indent=2, ensure_ascii=False) + "\n</script>")


def build_blog(base_tpl, nav_tpl, footer_tpl):
    """Render /blog and /blog/<slug>/ from the imported Wix post snapshot.

    Blog pages are served at directory addresses (/blog and /blog/<slug>), so
    unlike the rest of the site their asset and navigation links stay
    root absolute instead of being rewritten to relative paths.

    Returns a list of (path, canonical) pairs for the sitemap.
    """
    if not os.path.exists(BLOG_SNAPSHOT):
        print("  (no build/data/wixposts.json yet; /blog was not rendered)")
        return []

    snapshot = json.loads(read(BLOG_SNAPSHOT))
    posts = [p for p in snapshot.get("posts", []) if p.get("slug") and p.get("title")]
    posts.sort(key=lambda p: p.get("published") or "", reverse=True)

    generated = []
    index_tpl = read(os.path.join(TEMPLATES, "blog-index-fragment.html"))
    post_tpl = read(os.path.join(TEMPLATES, "blog-post-fragment.html"))

    # --- index -------------------------------------------------------------
    featured_html = ""
    grid_html = ""
    empty_html = ""
    if posts:
        featured_html = blog_card(posts[0], featured=True)
        if len(posts) > 1:
            cards = "".join(blog_card(p) for p in posts[1:])
            grid_html = '<div class="grid blog-grid">' + cards + "</div>"
    else:
        empty_html = ('<div class="notice"><strong>New posts are on the way.</strong> '
                      'Faith is writing the next one now. In the meantime, the '
                      '<a href="/resources.html">Resource Hub</a> has plenty to '
                      'read.</div>')

    index_body = fill_tokens(index_tpl, dict(SCHEDULING_LINKS,
                                             FEATURED=featured_html,
                                             POSTS=grid_html,
                                             EMPTY=empty_html))
    index_meta = {
        "title": "Blog | FN Home Group | Faith Nance, REALTOR\u00ae",
        "description": ("Real estate notes, neighborhood comparisons, and market "
                        "guidance for Southern Middle Tennessee from Faith Nance, "
                        "REALTOR\u00ae with Epique Realty."),
        "canonical": "/blog",
        "bodyclass": "page-blog",
    }
    html = render_page(index_meta, index_body, base_tpl, nav_tpl, footer_tpl,
                       extra_schema=blog_index_schema(posts), rootify=False)
    write(os.path.join(ROOT, "blog", "index.html"), html)
    generated.append(("/blog", "/blog"))

    # --- one page per published post ---------------------------------------
    for post in posts:
        cover = cover_img_tag(post, "blog-post-cover", sizes="(max-width: 820px) 100vw, 760px")
        cover = cover.replace("<img ", '<img loading="eager" fetchpriority="high" ')
        body = fill_tokens(post_tpl, dict(
            SCHEDULING_LINKS,
            TITLE=esc_attr(post.get("title") or ""),
            META=post_meta_line(post),
            COVER=cover,
            BODY=post.get("body_html") or "",
            SLUG=post["slug"],
        ))
        meta = {
            "title": "%s | FN Home Group Blog" % post.get("title", ""),
            "description": post.get("meta_description", ""),
            "canonical": "/blog/" + post["slug"],
            "bodyclass": "page-blogpost",
            "ogtype": "article",
            "ogimage": (post.get("cover") or {}).get("url") or DEFAULT_OG_IMAGE,
        }
        html = render_page(meta, body, base_tpl, nav_tpl, footer_tpl,
                           extra_schema=blog_post_schema(post), rootify=False)
        write(os.path.join(ROOT, "blog", post["slug"], "index.html"), html)
        generated.append(("/blog/" + post["slug"], "/blog/" + post["slug"]))

    return generated


def main():
    base_tpl = read(os.path.join(TEMPLATES, "base.html"))
    nav_tpl = read(os.path.join(TEMPLATES, "nav.html"))
    footer_tpl = read(os.path.join(TEMPLATES, "footer.html"))

    generated = []

    # 1. Hand-authored page fragments -> output at matching relative path
    for dirpath, _, filenames in os.walk(PAGES):
        for filename in sorted(filenames):
            if not filename.endswith(".html"):
                continue
            src_path = os.path.join(dirpath, filename)
            rel_dir = os.path.relpath(dirpath, PAGES)
            text = read(src_path)
            meta, body = parse_frontmatter(text)
            out_rel = filename if rel_dir == "." else os.path.join(rel_dir, filename)
            out_path = os.path.join(ROOT, out_rel)
            depth = 0 if rel_dir == "." else len(rel_dir.split(os.sep))
            root_prefix = "../" * depth
            html = render_page(meta, body, base_tpl, nav_tpl, footer_tpl, root_prefix=root_prefix)
            write(out_path, html)
            out_url = "/" + out_rel.replace(os.sep, "/")
            generated.append((out_url, meta.get("canonical", out_url)))

    # 2. Community pages generated from data + template
    community_data_path = os.path.join(DATA, "communities.json")
    if os.path.exists(community_data_path):
        communities = json.loads(read(community_data_path))
        community_tpl = read(os.path.join(TEMPLATES, "community-fragment.html"))
        for c in communities:
            body = fill_tokens(community_tpl, dict(SCHEDULING_LINKS, **c))
            meta = {
                "title": f"{c['name']} TN Real Estate | FN Home Group",
                "description": c.get("meta_description", ""),
                "canonical": f"/communities/{c['slug']}.html",
                "bodyclass": "page-community",
            }
            html = render_page(meta, body, base_tpl, nav_tpl, footer_tpl, root_prefix="../")
            out_path = os.path.join(ROOT, "communities", f"{c['slug']}.html")
            write(out_path, html)
            generated.append((f"/communities/{c['slug']}.html", meta["canonical"]))

    # 3. Article pages generated from data + template
    article_data_path = os.path.join(DATA, "articles.json")
    if os.path.exists(article_data_path):
        articles = json.loads(read(article_data_path))
        article_tpl = read(os.path.join(TEMPLATES, "article-fragment.html"))
        for a in articles:
            body = fill_tokens(article_tpl, dict(SCHEDULING_LINKS, **a))
            meta = {
                "title": f"{a['title']} | FN Home Group Resources",
                "description": a.get("meta_description", ""),
                "canonical": f"/resources/{a['slug']}.html",
                "bodyclass": "page-article",
            }
            html = render_page(meta, body, base_tpl, nav_tpl, footer_tpl, root_prefix="../")
            out_path = os.path.join(ROOT, "resources", f"{a['slug']}.html")
            write(out_path, html)
            generated.append((f"/resources/{a['slug']}.html", meta["canonical"]))

    # 4. Blog pages imported from the Wix Blog
    generated.extend(build_blog(base_tpl, nav_tpl, footer_tpl))

    # 5. sitemap.xml (auto-generated from every page produced above)
    sitemap_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    EXCLUDE_FROM_SITEMAP = {"/404.html", "/success.html"} | redirected_paths()
    for path, canonical in generated:
        if path in EXCLUDE_FROM_SITEMAP:
            continue
        loc_path = canonical or ("/" if path == "/index.html" else path)
        sitemap_lines.append(f"  <url>\n    <loc>{SITE_URL}{loc_path}</loc>\n  </url>")
    sitemap_lines.append("</urlset>")
    write(os.path.join(ROOT, "sitemap.xml"), "\n".join(sitemap_lines) + "\n")

    print(f"Generated {len(generated)} pages + sitemap.xml.")
    for path, _canonical in generated:
        print("  ", path)


if __name__ == "__main__":
    main()
