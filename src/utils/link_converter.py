import logging
import re
import requests
from typing import Optional
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)

_telegraph_token: Optional[str] = None

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
}


def _get_telegraph_poster():
    """Initializes or retrieves TelegraphPoster instance reusing token"""
    global _telegraph_token
    try:
        from html_telegraph_poster import TelegraphPoster

        poster = TelegraphPoster(use_api=True)
        if _telegraph_token:
            poster.access_token = _telegraph_token
        else:
            poster.create_api_token("Feedygram")
            _telegraph_token = poster.access_token
        return poster
    except Exception as e:
        logger.warning("Unable to initialize TelegraphPoster: %s", str(e))
        return None


def _post_html_to_telegraph(title: str, html_content: str, author_name: str = "Feedygram") -> Optional[str]:
    """Publishes clean HTML content to Telegraph"""
    if not html_content or not html_content.strip():
        return None
    try:
        poster = _get_telegraph_poster()
        if poster:
            clean_title = (title or "News Update")[:128]
            clean_author = (author_name or "Feedygram")[:128]
            try:
                res = poster.post(
                    title=clean_title,
                    author=clean_author,
                    text=html_content,
                    upload_images=False,
                )
            except TypeError:
                res = poster.post(
                    title=clean_title,
                    author=clean_author,
                    text=html_content,
                )
            if res and isinstance(res, dict) and "url" in res:
                return str(res["url"])
    except Exception as e:
        logger.warning("Error publishing to Telegraph: %s", str(e))
    return None


def _try_trafilatura_extraction(url: str, title: str = "", fallback_content: str = "") -> Optional[str]:
    """
    Tier 1: High-fidelity article extractor with hero cover image and lazy-image resolution.
    """
    try:
        import trafilatura
        from bs4 import BeautifulSoup

        resp = requests.get(url, headers=BROWSER_HEADERS, timeout=12)
        if resp.status_code != 200 or not resp.text:
            return None

        soup = BeautifulSoup(resp.text, "html.parser")

        # 1. Lead / Hero Image from OpenGraph or Twitter meta tags
        og_image = None
        for meta_prop in ["og:image", "twitter:image", "image", "thumbnail"]:
            tag = soup.find("meta", property=meta_prop) or soup.find("meta", attrs={"name": meta_prop})
            if tag and tag.get("content"):
                candidate_img = urljoin(url, tag["content"])
                if candidate_img.startswith("http"):
                    og_image = candidate_img
                    break

        # 2. Author / Site Name
        site_author = "Feedygram"
        author_meta = (
            soup.find("meta", property="og:site_name")
            or soup.find("meta", attrs={"name": "author"})
            or soup.find("meta", attrs={"name": "publisher"})
        )
        if author_meta and author_meta.get("content"):
            site_author = author_meta["content"].strip()[:128]

        # 3. Resolve lazy-loaded images in DOM before extraction
        for img in soup.find_all("img"):
            for attr in ["data-src", "data-original", "data-lazy-src", "data-hi-res-src", "data-srcset"]:
                if img.get(attr):
                    img_src = img[attr].split()[0]
                    img["src"] = urljoin(url, img_src)
                    break
            if img.get("src"):
                img["src"] = urljoin(url, img["src"])

        # 4. Trafilatura Extraction in HTML mode
        extracted_html = trafilatura.extract(
            str(soup),
            output_format="html",
            include_links=True,
            include_images=True,
            include_formatting=True,
            include_tables=True,
            favor_precision=False,
            favor_recall=True,
        )

        # 5. Fallbacks if Trafilatura output is too short
        if not extracted_html or len(extracted_html.strip()) < 100:
            article_tag = (
                soup.find("article")
                or soup.find("main")
                or soup.find(class_=lambda c: c and any(k in str(c).lower() for k in ["article-body", "post-content", "entry-content", "story-body", "content"]))
            )
            if article_tag:
                for useless_tag in article_tag(["script", "style", "nav", "footer", "aside", "form", "button", "noscript", "iframe"]):
                    useless_tag.decompose()
                extracted_html = str(article_tag)
            elif fallback_content and len(fallback_content.strip()) > 50:
                extracted_html = fallback_content

        if not extracted_html or len(extracted_html.strip()) < 30:
            return None

        # 6. Assemble rich Telegraph HTML
        lead_html = f'<figure><img src="{og_image}"/></figure>' if og_image else ""
        domain = urlparse(url).netloc
        footer_html = f'<p><hr/><a href="{url}">📰 Leggi l\'articolo su {domain}</a></p>'

        final_html = f"{lead_html}{extracted_html}{footer_html}"
        return _post_html_to_telegraph(title=title or "Article", html_content=final_html, author_name=site_author)

    except Exception as e:
        logger.debug("Trafilatura extraction failed for %s: %s", url, str(e))
        return None


def _try_readability_extraction(url: str, title: str = "") -> Optional[str]:
    """
    Tier 2: Mozilla Readability extractor fallback (if readability / readability-lxml installed).
    """
    try:
        from readability import Document
        from bs4 import BeautifulSoup

        resp = requests.get(url, headers=BROWSER_HEADERS, timeout=10)
        if resp.status_code != 200 or not resp.text:
            return None

        doc = Document(resp.text)
        summary_html = doc.summary()
        if summary_html and len(summary_html.strip()) > 100:
            soup = BeautifulSoup(summary_html, "html.parser")
            for tag in soup(["script", "style", "form"]):
                tag.decompose()
            domain = urlparse(url).netloc
            footer = f'<p><hr/><a href="{url}">📰 Leggi l\'articolo su {domain}</a></p>'
            final_html = f"{str(soup)}{footer}"
            return _post_html_to_telegraph(title=title or doc.short_title() or "Article", html_content=final_html)
    except Exception as e:
        logger.debug("Readability extraction failed for %s: %s", url, str(e))
    return None


def _try_jina_reader(url: str, title: str = "") -> Optional[str]:
    """
    Tier 3: Jina AI Reader (r.jina.ai) for JS-heavy SPAs and bypass-resistant sites.
    """
    try:
        jina_url = f"https://r.jina.ai/{url}"
        headers = {"Accept": "text/html", "User-Agent": "Feedygram/1.0"}
        r = requests.get(jina_url, headers=headers, timeout=12)
        if r.status_code != 200 or not r.text or len(r.text) < 100:
            return None

        md = r.text
        if "Markdown Content:" in md:
            md = md.split("Markdown Content:", 1)[1]

        # Convert markdown paragraphs to clean Telegraph HTML
        paragraphs = md.split("\n\n")
        html_parts = []
        for p in paragraphs:
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

        domain = urlparse(url).netloc
        footer_html = f'<p><hr/><a href="{url}">📰 Leggi l\'articolo su {domain}</a></p>'
        final_html = f"{''.join(html_parts[:50])}{footer_html}"
        return _post_html_to_telegraph(title=title or "Article", html_content=final_html)
    except Exception as e:
        logger.debug("Jina reader fallback failed for %s: %s", url, str(e))
        return None


def _try_webpage2telegraph(url: str) -> Optional[str]:
    """
    Tier 4: Attempts conversion via webpage2telegraph if installed.
    """
    try:
        import webpage2telegraph

        res = webpage2telegraph.transfer(url)
        if res and str(res).startswith("http") and "telegra.ph" in str(res):
            logger.info("Telegraph conversion successful via webpage2telegraph: %s", str(res))
            return str(res)
    except Exception as e:
        logger.debug("Tier 4 (webpage2telegraph) failed for %s: %s", url, str(e))
    return None


def convert_to_instant_link(url: str, title: str = "", fallback_content: str = "") -> str:
    """
    Instant View / Telegraph Link multi-tier conversion pipeline:
    1. Tier 1: High-Fidelity Trafilatura (desktop headers, hero cover image, lazy images, clean HTML).
    2. Tier 2: Mozilla Readability extraction fallback.
    3. Tier 3: Jina AI Reader (handles JS-heavy & React pages).
    4. Tier 4: webpage2telegraph library.
    5. Tier 5 (Final Fallback): Original URL.
    """
    if not url:
        return ""

    # 1. Tier 1: High-fidelity Trafilatura
    link = _try_trafilatura_extraction(url, title, fallback_content)
    if link:
        return link

    # 2. Tier 2: Readability
    link = _try_readability_extraction(url, title)
    if link:
        return link

    # 3. Tier 3: Jina AI Reader
    link = _try_jina_reader(url, title)
    if link:
        return link

    # 4. Tier 4: webpage2telegraph
    link = _try_webpage2telegraph(url)
    if link:
        return link

    # 5. Final fallback: original URL
    logger.info("Telegraph conversion not available, using original link: %s", url)
    return url
