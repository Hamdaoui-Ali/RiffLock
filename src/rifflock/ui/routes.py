"""Minimal app route selection for startup."""

from __future__ import annotations

from dataclasses import dataclass

from rifflock.auth import OwnerSetupService


@dataclass(frozen=True)
class AppRoute:
    name: str


def determine_initial_route(owner_setup_service: OwnerSetupService) -> AppRoute:
    if owner_setup_service.should_show_setup():
        return AppRoute(name="setup")
    return AppRoute(name="login")
