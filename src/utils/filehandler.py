import os
import json
import logging
from typing import Any, List, Optional

logger = logging.getLogger(__name__)


class FileHandler:
    def __init__(self, relative_root_path: Optional[str] = None) -> None:
        """
        Inizializza il gestore file con un percorso base relativo

        Args:
            relative_root_path: Percorso relativo dalla directory corrente
                              (None per directory corrente)
        """
        base_dir = os.path.abspath(os.path.dirname(__file__))

        if relative_root_path:
            self.base_path = os.path.normpath(os.path.join(base_dir, relative_root_path))
        else:
            self.base_path = base_dir

        logger.debug("FileHandler initialized with base path: %s", self.base_path)

    def join_path(self, *path_segments: str) -> str:
        """
        Combina il percorso base con i segmenti forniti

        Args:
            *path_segments: Segmenti del percorso da unire

        Returns:
            Percorso assoluto normalizzato

        Raises:
            ValueError: Se si tenta di uscire dalla root
        """
        full_path = os.path.join(self.base_path, *path_segments)
        normalized_path = os.path.normpath(full_path)

        if not normalized_path.startswith(self.base_path):
            raise ValueError("Tentativo di accesso fuori dalla directory base")

        return normalized_path

    def load_json(self, path: str) -> Any:
        """
        Carica un file JSON

        Args:
            path: Percorso relativo al base path

        Returns:
            Dati parsati dal JSON

        Raises:
            FileNotFoundError: Se il file non esiste
            JSONDecodeError: Se il JSON è malformato
        """
        file_path = self.join_path(path)

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error("Errore nel caricamento JSON: %s", str(e))
            raise

    def save_json(self, data: Any, path: str, indent: int = 2) -> None:
        """
        Salva dati in formato JSON

        Args:
            data: Dati da salvare
            path: Percorso relativo al base path
            indent: Indentazione del JSON
        """
        file_path = self.join_path(path)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=indent)
        except Exception as e:
            logger.error("Errore nel salvataggio JSON: %s", str(e))
            raise

    def load_file(self, path: str, binary: bool = False) -> str | bytes:
        """
        Carica il contenuto di un file

        Args:
            path: Percorso relativo al base path
            binary: Se True legge in modalità binaria

        Returns:
            Contenuto del file come stringa o bytes
        """
        file_path = self.join_path(path)
        mode = "rb" if binary else "r"

        try:
            with open(file_path, mode, encoding=None if binary else "utf-8") as f:
                return f.read()
        except Exception as e:
            logger.error("Errore nel caricamento file: %s", str(e))
            raise

    def save_file(self, data: str | bytes, path: str, binary: bool = False) -> None:
        """
        Salva dati in un file

        Args:
            data: Dati da salvare
            path: Percorso relativo al base path
            binary: Se True scrive in modalità binaria
        """
        file_path = self.join_path(path)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        mode = "wb" if binary else "w"

        try:
            with open(file_path, mode, encoding=None if binary else "utf-8") as f:
                f.write(data)
        except Exception as e:
            logger.error("Errore nel salvataggio file: %s", str(e))
            raise

    def file_exists(self, path: str) -> bool:
        """
        Verifica l'esistenza di un file/directory

        Args:
            path: Percorso relativo al base path

        Returns:
            True se il file/directory esiste
        """
        try:
            file_path = self.join_path(path)
            return os.path.exists(file_path)
        except ValueError:
            return False

    def get_files_in_dir(self, path: str) -> List[str]:
        """
        Elenca i contenuti di una directory

        Args:
            path: Percorso relativo al base path

        Returns:
            Lista ordinata di nomi di file/directory
        """
        dir_path = self.join_path(path)

        try:
            return sorted(os.listdir(dir_path))
        except Exception as e:
            logger.error("Errore nell'elenco directory: %s", str(e))
            raise

    def open_file(self, path: str, mode: str = "r"):
        """
        Restituisce un file object gestito

        Args:
            path: Percorso relativo al base path
            mode: Modalità di apertura file

        Returns:
            Context manager per il file
        """
        file_path = self.join_path(path)
        return open(file_path, mode, encoding="utf-8")
