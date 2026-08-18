import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)

_telegraph_token: Optional[str] = None


def _get_telegraph_poster():
    """Inizializza o recupera l'istanza TelegraphPoster riutilizzando il token"""
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
        logger.warning("Impossibile inizializzare TelegraphPoster: %s", str(e))
        return None


def _post_html_to_telegraph(title: str, html_content: str) -> Optional[str]:
    """Pubblica contenuto HTML su Telegraph evitando l'upload di immagini su endpoint deprecati"""
    if not html_content or not html_content.strip():
        return None
    try:
        poster = _get_telegraph_poster()
        if poster:
            clean_title = (title or "News Update")[:128]
            try:
                res = poster.post(title=clean_title, author="Feedygram", text=html_content, upload_images=False)
            except TypeError:
                res = poster.post(title=clean_title, author="Feedygram", text=html_content)
            if res and isinstance(res, dict) and "url" in res:
                return str(res["url"])
    except Exception as e:
        logger.warning("Errore pubblicazione su Telegraph: %s", str(e))
    return None


def _try_jina_reader(url: str, title: str = "") -> Optional[str]:
    """
    Tier 1: Estrae il testo tramite Jina Reader API e tenta la pubblicazione su Telegraph.
    """
    try:
        jina_url = f"https://r.jina.ai/{url}"
        headers = {
            "Accept": "text/html",
            "User-Agent": "Mozilla/5.0 (compatible; FeedygramBot/1.0)",
        }
        resp = requests.get(jina_url, headers=headers, timeout=5)
        if resp.status_code == 200 and resp.text:
            telegraph_url = _post_html_to_telegraph(title or "Article", resp.text)
            if telegraph_url:
                logger.info("Conversione Telegraph riuscita tramite Jina Reader: %s", telegraph_url)
                return telegraph_url
    except Exception as e:
        logger.debug("Tier 1 (Jina Reader) non riuscito per %s: %s", url, str(e))
    return None


def _try_webpage2telegraph(url: str) -> Optional[str]:
    """
    Tier 2: Tenta la conversione tramite webpage2telegraph.
    """
    try:
        import webpage2telegraph

        res = webpage2telegraph.transfer(url)
        if res and str(res).startswith("http"):
            logger.info("Conversione Telegraph riuscita tramite webpage2telegraph: %s", str(res))
            return str(res)
    except Exception as e:
        logger.debug("Tier 2 (webpage2telegraph) non riuscito per %s: %s", url, str(e))
    return None


def _try_trafilatura(url: str, title: str = "") -> Optional[str]:
    """
    Tier 3: Estrae l'articolo usando Trafilatura e lo pubblica su Telegraph.
    """
    try:
        import trafilatura

        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            extracted_html = trafilatura.extract(
                downloaded,
                output_format="xml",
                include_links=True,
                include_images=True,
            )
            if extracted_html:
                telegraph_url = _post_html_to_telegraph(title or "Article", extracted_html)
                if telegraph_url:
                    logger.info("Conversione Telegraph riuscita tramite Trafilatura: %s", telegraph_url)
                    return telegraph_url
    except Exception as e:
        logger.debug("Tier 3 (Trafilatura) non riuscito per %s: %s", url, str(e))
    return None


def convert_to_instant_link(url: str, title: str = "") -> str:
    """
    Pipeline completa di conversione Instant View / Reader Link:
    1. Tier 1: Jina Reader + Telegraph
    2. Fallback Tier 2: webpage2telegraph
    3. Fallback Tier 3: Trafilatura + Telegraph
    4. Fallback Tier 4: Link diretto Jina Reader (https://r.jina.ai/<url>)
    5. Fallback Finale: URL originale
    """
    if not url:
        return ""

    # 1. Prova Tier 1 (Jina Reader -> Telegraph)
    link = _try_jina_reader(url, title)
    if link:
        return link

    # 2. Fallback Tier 2 (webpage2telegraph)
    link = _try_webpage2telegraph(url)
    if link:
        return link

    # 3. Fallback Tier 3 (Trafilatura -> Telegraph)
    link = _try_trafilatura(url, title)
    if link:
        return link

    # 4. Fallback Tier 4: Direct Jina Reader URL proxy
    jina_direct = f"https://r.jina.ai/{url}"
    logger.info("Uso fallback Jina Reader URL diretto: %s", jina_direct)
    return jina_direct
