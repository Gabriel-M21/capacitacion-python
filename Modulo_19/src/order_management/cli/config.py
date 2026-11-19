"""
Configuración de la CLI - Módulo 18: CLI y automatización
Lee configuración desde variables de entorno con valores por defecto.
"""

import os
from pathlib import Path


class CliConfig:
    """
    Configuración de la CLI leída desde variables de entorno.

    Variables disponibles:
        ORDERS_API_URL     URL base de la API (default: http://localhost:8000)
        ORDERS_API_TIMEOUT Timeout en segundos   (default: 10)
        ORDERS_TOKEN_FILE  Ruta al archivo token  (default: ~/.orders-cli/token)
    """

    @property
    def api_url(self) -> str:
        return os.getenv("ORDERS_API_URL", "http://localhost:8000").rstrip("/")

    @property
    def timeout(self) -> float:
        return float(os.getenv("ORDERS_API_TIMEOUT", "10"))

    @property
    def token_file(self) -> Path:
        default = Path.home() / ".orders-cli" / "token"
        return Path(os.getenv("ORDERS_TOKEN_FILE", str(default)))

    def save_token(self, token: str) -> None:
        """Guarda el JWT en disco."""
        self.token_file.parent.mkdir(parents=True, exist_ok=True)
        self.token_file.write_text(token, encoding="utf-8")

    def load_token(self) -> str | None:
        """Lee el JWT desde disco. Retorna None si no existe."""
        if not self.token_file.exists():
            return None
        return self.token_file.read_text(encoding="utf-8").strip() or None

    def clear_token(self) -> None:
        """Elimina el token guardado."""
        if self.token_file.exists():
            self.token_file.unlink()

    def auth_headers(self) -> dict[str, str]:
        """Retorna headers de autenticación o dict vacío si no hay token."""
        token = self.load_token()
        if token:
            return {"Authorization": f"Bearer {token}"}
        return {}


# Instancia global compartida por todos los módulos de la CLI
config = CliConfig()
