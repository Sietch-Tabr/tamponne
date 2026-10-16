"""Réponse HTTP simulée pour les tests des clients (pas de réseau)."""

import io


class ReponseHttp(io.BytesIO):
    """Corps lisible avec les `headers` et `geturl()` d'une vraie réponse."""

    def __init__(
        self,
        contenu: bytes,
        url: str = "",
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(contenu)
        self._url = url
        self.headers = headers or {}

    def geturl(self) -> str:
        return self._url
