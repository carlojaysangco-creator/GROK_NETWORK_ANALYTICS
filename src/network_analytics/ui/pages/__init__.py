"""UI page layouts and callback registration."""

from .data import data_layout
from .netlynx import netlynx_layout
from .rpa import register_rpa, rpa_layout

__all__ = ["data_layout", "netlynx_layout", "register_rpa", "rpa_layout"]
