import io
import html
import xml.etree.ElementTree as ET
from typing import List, Tuple


def export_opml(feeds: List[Tuple[str, str, ...]]) -> io.BytesIO:
    """
    Genera un file OPML 2.0 a partire dalla lista dei feed dell'utente.
    Ogni elemento contiene almeno (url, alias, ...).
    """
    root = ET.Element("opml", version="2.0")
    head = ET.SubElement(root, "head")
    title_elem = ET.SubElement(head, "title")
    title_elem.text = "Feedygram Subscriptions"

    body = ET.SubElement(root, "body")
    for feed in feeds:
        url = feed[0]
        alias = feed[1] if len(feed) > 1 else url
        ET.SubElement(
            body,
            "outline",
            text=alias,
            title=alias,
            type="rss",
            xmlUrl=url,
        )

    xml_str = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    buffer = io.BytesIO(xml_str)
    buffer.name = "feedygram_subscriptions.opml"
    buffer.seek(0)
    return buffer


def parse_opml(content: str | bytes) -> List[Tuple[str, str]]:
    """
    Parsa un file OPML ed estrae la lista di tuple (url, title).
    """
    if isinstance(content, str):
        content = content.strip().encode("utf-8")

    feeds: List[Tuple[str, str]] = []
    try:
        root = ET.fromstring(content)
        # Cerca tutti gli elementi outline che contengono xmlUrl o url
        for outline in root.iter("outline"):
            xml_url = (
                outline.get("xmlUrl")
                or outline.get("xmlurl")
                or outline.get("url")
                or outline.get("htmlUrl")
            )
            if xml_url and xml_url.strip():
                url = xml_url.strip()
                title = outline.get("title") or outline.get("text") or url
                feeds.append((url, title.strip()))
    except Exception as e:
        raise ValueError(f"Formato OPML non valido: {e}")

    return feeds
