from fastapi import APIRouter

from . import admin, auth, cases  # noqa: F401

__all__ = ["admin", "auth", "cases"]