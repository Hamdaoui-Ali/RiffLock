"""Authenticated dashboard data and UI helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from rifflock.files import (
    FileProtectionService,
    FileRestoreService,
    FolderProtectionService,
    ProtectedItemService,
    ProtectedItemView,
    parse_container,
)
from rifflock.utils import to_user_message


@dataclass(frozen=True)
class DashboardState:
    items: list[ProtectedItemView]
    is_empty: bool


@dataclass(frozen=True)
class DashboardActionResult:
    succeeded: bool
    message: str
    state: DashboardState


class DashboardDataService:
    """Load protected items for dashboard consumption."""

    def __init__(self, protected_item_service: ProtectedItemService) -> None:
        self._protected_item_service = protected_item_service

    def load(self) -> DashboardState:
        items = self._protected_item_service.list_items()
        return DashboardState(
            items=items,
            is_empty=len(items) == 0,
        )


class ProtectFileFlowService:
    """UI-facing protect-file flow built on the core protection service."""

    def __init__(
        self,
        file_protection_service: FileProtectionService,
        dashboard_data_service: DashboardDataService,
        default_output_dir: Path | str,
    ) -> None:
        self._file_protection_service = file_protection_service
        self._dashboard_data_service = dashboard_data_service
        self._default_output_dir = Path(default_output_dir)

    def get_default_output_path(self, source_path: Path | str) -> Path:
        source = Path(source_path)
        return self._default_output_dir / f"{source.name}.rifflock"

    def protect_file(
        self,
        *,
        source_path: Path | str,
        data_key: bytes,
        output_path: Path | str | None = None,
    ) -> DashboardActionResult:
        final_output = (
            Path(output_path)
            if output_path is not None
            else self.get_default_output_path(source_path)
        )

        try:
            final_output.parent.mkdir(parents=True, exist_ok=True)
            result = self._file_protection_service.protect_file(
                source_path=source_path,
                data_key=data_key,
                output_path=final_output,
            )
            return DashboardActionResult(
                succeeded=True,
                message=f"Protected file created at {result.output_path}.",
                state=self._dashboard_data_service.load(),
            )
        except Exception as error:
            return DashboardActionResult(
                succeeded=False,
                message=to_user_message(error),
                state=self._dashboard_data_service.load(),
            )


class RestoreFileFlowService:
    """UI-facing restore-file flow built on the core restore service."""

    def __init__(
        self,
        file_restore_service: FileRestoreService,
        dashboard_data_service: DashboardDataService,
    ) -> None:
        self._file_restore_service = file_restore_service
        self._dashboard_data_service = dashboard_data_service

    def get_default_output_path(self, protected_path: Path | str) -> Path:
        protected = Path(protected_path)
        container = parse_container(protected.read_bytes())
        original_name = str(container.metadata["original_filename"])
        return protected.with_name(original_name)

    def restore_file(
        self,
        *,
        protected_path: Path | str,
        data_key: bytes,
        output_path: Path | str | None = None,
    ) -> DashboardActionResult:
        try:
            final_output = (
                Path(output_path)
                if output_path is not None
                else self.get_default_output_path(protected_path)
            )
            final_output.parent.mkdir(parents=True, exist_ok=True)
            result = self._file_restore_service.restore_file(
                protected_path=protected_path,
                data_key=data_key,
                output_path=final_output,
            )
            return DashboardActionResult(
                succeeded=True,
                message=f"Restored file created at {result.restored_path}.",
                state=self._dashboard_data_service.load(),
            )
        except Exception as error:
            return DashboardActionResult(
                succeeded=False,
                message=to_user_message(error),
                state=self._dashboard_data_service.load(),
            )


class ProtectFolderFlowService:
    """UI-facing protect-folder flow built on the core folder protection service."""

    def __init__(
        self,
        folder_protection_service: FolderProtectionService,
        dashboard_data_service: DashboardDataService,
        default_output_dir: Path | str,
    ) -> None:
        self._folder_protection_service = folder_protection_service
        self._dashboard_data_service = dashboard_data_service
        self._default_output_dir = Path(default_output_dir)

    def get_default_output_path(self, source_path: Path | str) -> Path:
        source = Path(source_path)
        return self._default_output_dir / f"{source.name}.rifflock"

    def protect_folder(
        self,
        *,
        source_path: Path | str,
        data_key: bytes,
        output_path: Path | str | None = None,
    ) -> DashboardActionResult:
        final_output = (
            Path(output_path)
            if output_path is not None
            else self.get_default_output_path(source_path)
        )

        try:
            final_output.mkdir(parents=True, exist_ok=True)
            result = self._folder_protection_service.protect_folder(
                source_path=source_path,
                data_key=data_key,
                output_path=final_output,
            )
            return DashboardActionResult(
                succeeded=result.failed_count == 0,
                message=self._build_summary_message(result),
                state=self._dashboard_data_service.load(),
            )
        except Exception as error:
            return DashboardActionResult(
                succeeded=False,
                message=to_user_message(error),
                state=self._dashboard_data_service.load(),
            )

    def _build_summary_message(self, result) -> str:
        summary = (
            f"Folder protection finished at {result.output_path}. "
            f"Protected: {result.protected_count}. "
            f"Skipped: {result.skipped_count}. "
            f"Failed: {result.failed_count}."
        )
        if result.failed_count == 0:
            return summary

        first_failure = result.failed_files[0]
        return f"{summary} First failure: {first_failure.path} - {first_failure.reason}"


def build_dashboard_screen(
    app,
    ctk,
    *,
    state: DashboardState,
    on_protect_file: Callable[[], None] | None = None,
    on_protect_folder: Callable[[], None] | None = None,
    on_restore_file: Callable[[], None] | None = None,
    on_settings: Callable[[], None] | None = None,
    on_logout: Callable[[], None] | None = None,
) -> None:
    """Render the main authenticated dashboard screen."""

    container = ctk.CTkFrame(app, corner_radius=0, fg_color="transparent")
    container.pack(fill="both", expand=True, padx=20, pady=20)

    header = ctk.CTkFrame(container, fg_color="transparent")
    header.pack(fill="x")

    title = ctk.CTkLabel(
        header,
        text="Protected Items",
        font=ctk.CTkFont(size=28, weight="bold"),
    )
    title.pack(side="left")

    actions = ctk.CTkFrame(header, fg_color="transparent")
    actions.pack(side="right")

    _add_action_button(ctk, actions, "Protect File", on_protect_file)
    _add_action_button(ctk, actions, "Protect Folder", on_protect_folder)
    _add_action_button(ctk, actions, "Restore File", on_restore_file)
    _add_action_button(ctk, actions, "Settings", on_settings)
    _add_action_button(ctk, actions, "Logout", on_logout)

    subtitle = ctk.CTkLabel(
        container,
        text="Review protected artifacts and launch the main file actions.",
        anchor="w",
    )
    subtitle.pack(fill="x", pady=(8, 20))

    body = ctk.CTkFrame(container)
    body.pack(fill="both", expand=True)

    if state.is_empty:
        empty = ctk.CTkLabel(
            body,
            text="No protected items yet. Use Protect File or Protect Folder to create your first artifact.",
            justify="center",
            wraplength=520,
        )
        empty.pack(expand=True, padx=24, pady=24)
        return

    scroll = ctk.CTkScrollableFrame(body)
    scroll.pack(fill="both", expand=True, padx=12, pady=12)

    for item in state.items:
        card = ctk.CTkFrame(scroll)
        card.pack(fill="x", pady=6)

        name = ctk.CTkLabel(
            card,
            text=item.record.artifact_path,
            anchor="w",
            font=ctk.CTkFont(weight="bold"),
        )
        name.pack(fill="x", padx=12, pady=(10, 2))

        meta = ctk.CTkLabel(
            card,
            text=(
                f"type: {item.record.item_type} | "
                f"status: {item.record.status} | "
                f"source exists: {'yes' if item.source_exists else 'no'} | "
                f"protected exists: {'yes' if item.protected_exists else 'no'}"
            ),
            anchor="w",
        )
        meta.pack(fill="x", padx=12, pady=(0, 10))


def _add_action_button(ctk, parent, text: str, command: Callable[[], None] | None = None) -> None:
    button = ctk.CTkButton(
        parent,
        text=text,
        width=120,
        command=command or (lambda: None),
    )
    button.pack(side="left", padx=(8, 0))
