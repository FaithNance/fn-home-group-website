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


def read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


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


def render_page(meta, body, base_tpl, nav_tpl, footer_tpl, extra_schema=None, root_prefix=""):
    canonical_path = meta.get("canonical", "/")
    canonical = SITE_URL + canonical_path
    html = base_tpl
    html = html.replace("{{TITLE}}", meta.get("title", "FN Home Group"))
    html = html.replace("{{OG_TITLE}}", meta.get("title", "FN Home Group"))
    html = html.replace("{{DESCRIPTION}}", meta.get("description", ""))
    html = html.replace("{{CANONICAL}}", canonical)
    html = html.replace("{{BODY_CLASS}}", meta.get("bodyclass", ""))
    schema = extra_schema if extra_schema is not None else schema_block(meta)
    html = html.replace("{{SCHEMA}}", schema)
    html = html.replace("{{NAV}}", nav_tpl)
    html = html.replace("{{FOOTER}}", footer_tpl)
    html = html.replace("{{CONTENT}}", body)
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
            body = fill_tokens(community_tpl, c)
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
            body = fill_tokens(article_tpl, a)
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

    # 4. sitemap.xml (auto-generated from every page produced above)
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
