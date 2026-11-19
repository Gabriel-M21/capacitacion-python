"""
Configuración centralizada - Módulo 19: Seguridad y mantenimiento
Lee configuración desde variables de entorno o archivo .env.

Reglas de seguridad:
  - Nunca hardcodear secretos en el código
  - SECRET_KEY debe tener al menos 32 caracteres en producción
  - DATABASE_URL no debe contener credenciales en texto plano en repos
"""

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Configuración de la aplicación cargada desde variables de entorno.

    Prioridad de carga (mayor a menor):
      1. Variables de entorno del sistema
      2. Archivo .env en el directorio raíz
      3. Valores por defecto definidos aquí

    En producción NUNCA uses los valores por defecto para secretos.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ------------------------------------------------------------------
    # API y servidor
    # ------------------------------------------------------------------
    app_name: str        = Field(default="Order Management API")
    app_version: str     = Field(default="0.1.0")
    debug: bool          = Field(default=False)
    api_host: str        = Field(default="0.0.0.0")
    api_port: int        = Field(default=8000)

    # ------------------------------------------------------------------
    # Seguridad — JWT
    # ------------------------------------------------------------------
    secret_key: str = Field(
        default="CHANGE-ME-IN-PRODUCTION-USE-32-CHARS-MINIMUM",
        description="Clave secreta para firmar tokens JWT. "
                    "Mínimo 32 caracteres. "
                    "Generar con: python -c \"import secrets; print(secrets.token_hex(32))\"",
    )
    algorithm: str               = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=30)

    # ------------------------------------------------------------------
    # Base de datos
    # ------------------------------------------------------------------
    database_url: str = Field(
        default="sqlite:///order_management.db",
        description="URL de conexión a la base de datos. "
                    "Ejemplo PostgreSQL: postgresql://user:pass@localhost/dbname",
    )
    db_echo: bool = Field(default=False, description="Loguear SQL generado (solo desarrollo)")

    # ------------------------------------------------------------------
    # CORS
    # ------------------------------------------------------------------
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"],
        description="Orígenes permitidos para CORS. Usar ['*'] solo en desarrollo.",
    )

    # ------------------------------------------------------------------
    # Notificaciones
    # ------------------------------------------------------------------
    notification_url: str | None = Field(
        default=None,
        description="URL del servicio de notificaciones (opcional)",
    )
    notification_timeout: float = Field(default=3.0)

    # ------------------------------------------------------------------
    # Validaciones
    # ------------------------------------------------------------------

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Advierte si el secret_key es el valor por defecto."""
        if v == "CHANGE-ME-IN-PRODUCTION-USE-32-CHARS-MINIMUM":
            import warnings
            warnings.warn(
                "⚠ SECRET_KEY usa el valor por defecto. "
                "Esto es INSEGURO en producción. "
                "Define la variable de entorno SECRET_KEY.",
                UserWarning,
                stacklevel=2,
            )
        if len(v) < 16:
            raise ValueError("SECRET_KEY debe tener al menos 16 caracteres")
        return v

    @field_validator("access_token_expire_minutes")
    @classmethod
    def validate_token_expiry(cls, v: int) -> int:
        if v < 1:
            raise ValueError("access_token_expire_minutes debe ser >= 1")
        if v > 1440:  # 24 horas
            raise ValueError("access_token_expire_minutes no debería superar 1440 (24h)")
        return v


@lru_cache
def get_settings() -> Settings:
    """
    Retorna la instancia de Settings (singleton con caché).

    Usar lru_cache garantiza que el archivo .env se lee una sola vez
    y la misma instancia se reutiliza en toda la aplicación.

    En tests, llamar a get_settings.cache_clear() para resetear.
    """
    return Settings()
