"""
Base declarativa compartida para todos los modelos ORM.
Módulo 8: Acceso a datos y ORM
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base declarativa de SQLAlchemy para todos los modelos ORM."""
