import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup, NavigableString, Tag

logger = logging.getLogger(__name__)

_telegraph_token: Optional[str] = None

TELEGRAPH_API = "https://api.telegra.ph"

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
}

# The 23 tags strictly allowed by Telegra.ph API
ALLOWED_TAGS = {
    "a", "aside", "b", "blockquote", "br", "code", "em", "figcaption", "figure",
    "h3", "h4", "hr", "i", "iframe", "img", "li", "ol", "p", "pre", "s",
    "strong", "u", "ul", "video"
}


def _get_telegraph_token() -> Optional[str]:
    """Retrieves cached token, DB persistent token, env, or creates a new one via Telegraph API."""
    global _telegraph_token
    if _telegraph_token:
        return _telegraph_token

    env_token = os.getenv("TELEGRAPH_TOKEN")
    if env_token:
        _telegraph_token = env_token
        return _telegraph_token

    # Try reading from SQLite bot_settings
    db_handler = None
    try:
        from utils.database import DatabaseHandler
        db_handler = DatabaseHandler("database", "data.db")
        db_token = db_handler.get_setting("telegraph_token")
        if db_token:
            _telegraph_token = db_token
            return _telegraph_token
    except Exception as e:
        logger.debug("Could not read telegraph_token from database: %s", e)

    # Create new account via Telegraph API
    try:
        resp = requests.post(
            f"{TELEGRAPH_API}/createAccount",
            json={"short_name": "Feedygram", "author_name": "Feedygram"},
            timeout=10,
        )
        data = resp.json()
        if data.get("ok") and "result" in data:
            token = data["result"].get("access_token")
            if token:
                _telegraph_token = token
                if db_handler:
                    try:
                        db_handler.set_setting("telegraph_token", token)
                    except Exception as e:
                        logger.debug("Could not persist telegraph_token to DB: %s", e)
                return token
    except Exception as e:
        logger.warning("Failed to create Telegraph account: %s", e)

    return None


def _post_to_telegraph(
    title: str,
    nodes: List[Any],
    author_name: str = "Feedygram",
    author_url: str = "",
) -> Optional[str]:
    """Posts JSON nodes directly to Telegra.ph API createPage endpoint."""
    if not nodes:
        return None

    token = _get_telegraph_token()
    if not token:
        logger.warning("No Telegraph token available for posting")
        return None

    clean_title = (title or "News Update").strip()[:256] or "News Update"
    clean_author = (author_name or "Feedygram").strip()[:128]

    try:
        content_json = json.dumps(nodes, ensure_ascii=False)
        payload = {
            "access_token": token,
            "title": clean_title,
            "author_name": clean_author,
            "author_url": author_url[:512] if author_url else "",
            "content": content_json,
            "return_content": False,
        }
        resp = requests.post(f"{TELEGRAPH_API}/createPage", json=payload, timeout=12)
        res = resp.json()
        if res.get("ok") and "result" in res and "url" in res["result"]:
            telegraph_url = str(res["result"]["url"])
            logger.info("Telegraph publication successful: %s", telegraph_url)
            return telegraph_url
        logger.warning("Telegraph API error: %s", res.get("error", "Unknown error"))
    except Exception as e:
        logger.warning("Error publishing to Telegraph API: %s", e)

    return None


def clean_and_convert_html_to_nodes(html_content: str, base_url: str = "") -> List[Any]:
    """
    Transforms raw or messy HTML into a sanitized list of Telegraph JSON nodes.
    - Strips unsupported tags (script, style, svg, canvas, forms).
    - Normalizes headings (h1, h2 -> h3; h5, h6 -> h4).
    - Flattens tables into readable blockquotes.
    - Resolves lazy-loaded images and relative URLs while dropping base64 blobs.
    - Enforces the 64KB Telegraph payload limit safely.
    """
    if not html_content or not html_content.strip():
        return []

    soup = BeautifulSoup(html_content, "html.parser")

    # 1. Remove dangerous or non-content tags
    for tag in soup.find_all(
        ["script", "style", "noscript", "svg", "canvas", "form", "button", "input", "select", "textarea", "meta", "link", "head"]
    ):
        tag.decompose()

    # 2. Pre-process images (lazy loading, relative URLs, remove base64)
    for img in soup.find_all("img"):
        for attr in ["data-src", "data-original", "data-lazy-src", "data-hi-res-src", "data-srcset"]:
            if img.get(attr):
                val = img[attr].strip().split()[0]
                img["src"] = val
                break
        src = img.get("src", "").strip()
        if not src or src.startswith("data:"):
            img.decompose()
            continue
        resolved_src = urljoin(base_url, src)
        if resolved_src.startswith("http://") or resolved_src.startswith("https://"):
            img["src"] = resolved_src
        else:
            img.decompose()

    # 3. Pre-process links
    for a in soup.find_all("a"):
        href = a.get("href", "").strip()
        if not href or href.startswith("javascript:") or href.startswith("#"):
            a.unwrap()
            continue
        resolved_href = urljoin(base_url, href)
        if resolved_href.startswith("http://") or resolved_href.startswith("https://") or resolved_href.startswith("mailto:"):
            a["href"] = resolved_href
        else:
            a.unwrap()

    # 4. Normalize headings
    for h in soup.find_all(["h1", "h2"]):
        h.name = "h3"
    for h in soup.find_all(["h5", "h6"]):
        h.name = "h4"

    # 5. Convert tables into readable blockquotes
    for table in soup.find_all("table"):
        rows = []
        for tr in table.find_all("tr"):
            cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
            if cells:
                rows.append(" | ".join(cells))
        if rows:
            bq = soup.new_tag("blockquote")
            bq.string = "\n".join(rows)
            table.replace_with(bq)
        else:
            table.decompose()

    # 6. Filter iframes (only YouTube, Vimeo, Twitter allowed)
    for iframe in soup.find_all("iframe"):
        src = iframe.get("src", "")
        if any(allowed in src for allowed in ["youtube.com/embed/", "youtu.be/", "player.vimeo.com/", "twitframe.com"]):
            pass
        else:
            iframe.decompose()

    # Helper function for recursive DOM to Telegraph Node translation
    def _element_to_node(elem: Any) -> Optional[Union[str, Dict[str, Any], List[Any]]]:
        if isinstance(elem, NavigableString):
            txt = str(elem)
            return txt if txt.strip() or txt == " " else None

        if isinstance(elem, Tag):
            tag_name = elem.name.lower()
            children: List[Any] = []
            for child in elem.children:
                child_node = _element_to_node(child)
                if child_node is not None:
                    if isinstance(child_node, list):
                        children.extend(child_node)
                    else:
                        children.append(child_node)

            if tag_name in ALLOWED_TAGS:
                attrs: Dict[str, str] = {}
                if tag_name == "a" and elem.get("href"):
                    attrs["href"] = elem["href"]
                elif tag_name in ("img", "iframe", "video") and elem.get("src"):
                    attrs["src"] = elem["src"]

                node: Dict[str, Any] = {"tag": tag_name}
                if attrs:
                    node["attrs"] = attrs
                if children:
                    node["children"] = children
                return node
            else:
                # Disallowed container tag (div, section, article, span, etc.)
                if not children:
                    return None
                # If any child is already a block element, return unpacked children
                has_block = any(
                    isinstance(c, dict) and c.get("tag") in (
                        "p", "h3", "h4", "blockquote", "ul", "ol", "figure", "pre", "hr"
                    )
                    for c in children
                )
                if has_block:
                    return children
                return {"tag": "p", "children": children}

        return None

    # 7. Build top-level nodes
    raw_nodes: List[Any] = []
    root = soup.body if soup.body else soup
    for child in root.children:
        node = _element_to_node(child)
        if node is not None:
            if isinstance(node, list):
                raw_nodes.extend(node)
            else:
                raw_nodes.append(node)

    # 8. Normalize top-level nodes (wrap bare strings and inline tags in <p>, images in <figure>)
    final_nodes: List[Dict[str, Any]] = []
    for item in raw_nodes:
        if isinstance(item, str):
            if item.strip():
                final_nodes.append({"tag": "p", "children": [item]})
        elif isinstance(item, dict):
            tag = item.get("tag")
            if tag == "img":
                final_nodes.append({"tag": "figure", "children": [item]})
            elif tag in ("a", "b", "i", "em", "strong", "code", "u", "s"):
                final_nodes.append({"tag": "p", "children": [item]})
            else:
                final_nodes.append(item)

    # 9. Enforce 64KB Telegraph limit (truncate gracefully before 55KB)
    while final_nodes and len(json.dumps(final_nodes, ensure_ascii=False).encode("utf-8")) > 52000:
        final_nodes.pop()

    if base_url:
        domain = urlparse(base_url).netloc
        final_nodes.append({
            "tag": "p",
            "children": [
                {"tag": "hr"},
                {
                    "tag": "a",
                    "attrs": {"href": base_url},
                    "children": [f"📰 Leggi l'articolo completo su {domain}" if domain else "📰 Leggi l'articolo originale"],
                },
            ],
        })

    return final_nodes


def _try_feed_summary_extraction(fallback_content: str, url: str, title: str) -> Optional[str]:
    """Tier 1: Converts native RSS/Atom feed content if already sufficiently detailed."""
    if not fallback_content or len(fallback_content.strip()) < 150:
        return None
    try:
        nodes = clean_and_convert_html_to_nodes(fallback_content, base_url=url)
        # Verify nodes contain enough substantive text
        total_text_len = 0
        for n in nodes:
            if isinstance(n, dict):
                for c in n.get("children", []):
                    if isinstance(c, str):
                        total_text_len += len(c.strip())
        if total_text_len >= 100:
            res = _post_to_telegraph(title=title or "Article", nodes=nodes, author_url=url)
            if res:
                logger.info("Telegraph conversion successful via RSS content: %s", res)
                return res
    except Exception as e:
        logger.debug("Tier 1 (feed summary) conversion failed for %s: %s", url, e)
    return None


def _try_trafilatura_extraction(url: str, title: str = "") -> Optional[str]:
    """Tier 2: High-fidelity web extraction with hero image using Trafilatura."""
    try:
        import trafilatura

        resp = requests.get(url, headers=BROWSER_HEADERS, timeout=12)
        if resp.status_code != 200 or not resp.text:
            return None

        soup = BeautifulSoup(resp.text, "html.parser")

        # 1. Lead image from OpenGraph / Twitter
        lead_img = None
        for prop in ["og:image", "twitter:image", "image", "thumbnail"]:
            tag = soup.find("meta", property=prop) or soup.find("meta", attrs={"name": prop})
            if tag and tag.get("content"):
                cand = urljoin(url, tag["content"])
                if cand.startswith("http://") or cand.startswith("https://"):
                    lead_img = cand
                    break

        # 2. Site Author
        site_author = "Feedygram"
        author_meta = (
            soup.find("meta", property="og:site_name")
            or soup.find("meta", attrs={"name": "author"})
            or soup.find("meta", attrs={"name": "publisher"})
        )
        if author_meta and author_meta.get("content"):
            site_author = author_meta["content"].strip()[:128]

        # 3. Trafilatura Extraction
        extracted_html = trafilatura.extract(
            resp.text,
            output_format="html",
            include_links=True,
            include_images=True,
            include_formatting=True,
            favor_recall=True,
        )
        if not extracted_html or len(extracted_html.strip()) < 80:
            return None

        # Prepend hero image if present
        if lead_img:
            extracted_html = f'<figure><img src="{lead_img}"/></figure>' + extracted_html

        nodes = clean_and_convert_html_to_nodes(extracted_html, base_url=url)
        if nodes:
            res = _post_to_telegraph(title=title or "Article", nodes=nodes, author_name=site_author, author_url=url)
            if res:
                logger.info("Telegraph conversion successful via Trafilatura: %s", res)
                return res
    except Exception as e:
        logger.debug("Tier 2 (Trafilatura) failed for %s: %s", url, e)
    return None


def _try_newspaper_extraction(url: str, title: str = "") -> Optional[str]:
    """Tier 3: News article extractor fallback using newspaper4k."""
    try:
        import newspaper

        article = newspaper.article(url)
        if not article:
            return None

        article_text = getattr(article, "text", "")
        if not article_text or len(article_text.strip()) < 80:
            return None

        html_parts: List[str] = []
        top_image = getattr(article, "top_image", None)
        if top_image and (top_image.startswith("http://") or top_image.startswith("https://")):
            html_parts.append(f'<figure><img src="{top_image}"/></figure>')

        for p in article_text.split("\n\n"):
            p_clean = p.strip()
            if p_clean:
                html_parts.append(f"<p>{p_clean}</p>")

        author = "Feedygram"
        authors = getattr(article, "authors", [])
        if authors and isinstance(authors, list):
            author = str(authors[0]).strip()[:128]

        nodes = clean_and_convert_html_to_nodes("".join(html_parts), base_url=url)
        if nodes:
            res = _post_to_telegraph(
                title=title or getattr(article, "title", "Article") or "Article",
                nodes=nodes,
                author_name=author,
                author_url=url,
            )
            if res:
                logger.info("Telegraph conversion successful via newspaper4k: %s", res)
                return res
    except Exception as e:
        logger.debug("Tier 3 (newspaper4k) failed for %s: %s", url, e)
    return None


def _try_jina_reader(url: str, title: str = "") -> Optional[str]:
    """Tier 4: Jina AI Reader (r.jina.ai) for JS-heavy SPAs and bypass-resistant sites."""
    try:
        jina_url = f"https://r.jina.ai/{url}"
        headers = {"Accept": "text/html", "User-Agent": "Feedygram/1.0"}
        r = requests.get(jina_url, headers=headers, timeout=12)
        if r.status_code != 200 or not r.text or len(r.text) < 100:
            return None

        md = r.text
        if "Markdown Content:" in md:
            md = md.split("Markdown Content:", 1)[1]

        html_parts: List[str] = []
        for p in md.split("\n\n"):
            p = p.strip()
            if not p:
                continue
            if p.startswith("#"):
                p_clean = p.lstrip("#").strip()
                html_parts.append(f"<h3>{p_clean}</h3>")
            elif p.startswith("!["):
                match = re.search(r"\!\[.*?\]\((.*?)\)", p)
                if match and match.group(1).startswith("http"):
                    html_parts.append(f'<figure><img src="{match.group(1)}"/></figure>')
            else:
                html_parts.append(f"<p>{p}</p>")

        if not html_parts:
            return None

        nodes = clean_and_convert_html_to_nodes("".join(html_parts), base_url=url)
        if nodes:
            res = _post_to_telegraph(title=title or "Article", nodes=nodes, author_url=url)
            if res:
                logger.info("Telegraph conversion successful via Jina Reader: %s", res)
                return res
    except Exception as e:
        logger.debug("Tier 4 (Jina Reader) failed for %s: %s", url, e)
    return None


def convert_to_instant_link(url: str, title: str = "", fallback_content: str = "") -> str:
    """
    Instant View / Telegraph Link multi-tier conversion pipeline:
    1. Tier 1: Native RSS/Atom feed content (if rich/full article).
    2. Tier 2: High-Fidelity Trafilatura (desktop headers, hero cover image, clean HTML).
    3. Tier 3: Newspaper4k article extractor.
    4. Tier 4: Jina AI Reader (handles JS-heavy & React pages).
    5. Tier 5 (Final Fallback): Original URL.
    """
    if not url:
        return ""

    # 1. Tier 1: Native RSS content
    link = _try_feed_summary_extraction(fallback_content, url, title)
    if link:
        return link

    # 2. Tier 2: Trafilatura
    link = _try_trafilatura_extraction(url, title)
    if link:
        return link

    # 3. Tier 3: Newspaper4k
    link = _try_newspaper_extraction(url, title)
    if link:
        return link

    # 4. Tier 4: Jina AI Reader
    link = _try_jina_reader(url, title)
    if link:
        return link

    # 5. Final fallback: original URL
    logger.info("Telegraph conversion not available, using original link: %s", url)
    return url


def transfer(url: str, title: str = "") -> Optional[str]:
    """Drop-in replacement for the legacy webpage2telegraph.transfer API."""
    res = convert_to_instant_link(url, title=title)
    if res and res.startswith("http") and "telegra.ph" in res:
        return res
    return None
