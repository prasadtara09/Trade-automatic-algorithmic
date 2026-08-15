"""Validated weekly relative-strength rotation strategy package."""

from .momentum_rotation import MODEL_NAME, select_rotation_targets

__all__ = ["MODEL_NAME", "select_rotation_targets"]