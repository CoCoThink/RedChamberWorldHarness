"""Immutable release storage; importing a baseline never promotes a candidate."""

from .manifest import ReleaseManifest

__all__ = ["ReleaseManifest"]
