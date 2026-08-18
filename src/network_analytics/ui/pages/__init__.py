"""UI page layouts and callback registration."""

from .admin import admin_layout, register_admin
from .data import data_layout
from .netlynx import netlynx_layout
from .rpa import register_rpa, rpa_layout

__all__ = [
    "admin_layout",
    "data_layout",
    "netlynx_layout",
    "register_admin",
    "register_rpa",
    "rpa_layout",
]
