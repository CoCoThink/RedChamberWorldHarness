"""Versioned physical assets; registering a file grants no evidential authority."""

from .catalog import AssetCatalog, AssetError, ResolvedAsset
from .store import CatalogStore

__all__ = ["AssetCatalog", "AssetError", "ResolvedAsset", "CatalogStore"]
