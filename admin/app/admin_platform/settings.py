"""Admin platform metadata settings."""
from __future__ import annotations

from dataclasses import dataclass

from . import ADMIN_PLATFORM_VERSION, AV_DS_VERSION


@dataclass(frozen=True)
class AdminPlatformInfo:
    project: str = "fbrk"
    package: str = "local-admin-platform"
    version: str = ADMIN_PLATFORM_VERSION
    av_ds_version: str = AV_DS_VERSION
    upstream_contract: str = "qaz-admin-kit-compatible"


def current_platform_info() -> AdminPlatformInfo:
    return AdminPlatformInfo()

