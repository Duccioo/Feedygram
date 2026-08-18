from abc import ABC, abstractmethod
from typing import List, Tuple, Optional
from .models import FeedItem


class BaseFeedProvider(ABC):
    """
    Interfaccia comune per i provider di feed RSS/Atom o motori esterni (es. Lion Reader, REST API).
    """

    @abstractmethod
    def validate_feed(self, target: str) -> Tuple[bool, Optional[str]]:
        """Verifica se l'URL o l'identificatore del feed è valido e raggiungibile."""
        pass

    @abstractmethod
    def get_feed_title(self, target: str) -> Optional[str]:
        """Recupera il titolo del feed."""
        pass

    @abstractmethod
    def fetch_entries(self, target: str, limit: int = 0) -> List[FeedItem]:
        """Recupera gli articoli per il target specificato."""
        pass
