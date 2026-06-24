"""Authenticated dashboard data and UI helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from rifflock.files import (
    FileProtectionService,
    FileRestoreService,
    FileViewingResult,
    FolderProtectionService,
    ProtectedItemService,
    ProtectedItemView,
    parse_container,
)
from rifflock.utils.errors import FileOperationError
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

    def prepare_file_for_opening(
        self,
        *,
        protected_path: Path | str,
        data_key: bytes,
    ) -> FileViewingResult:
        return self._file_restore_service.prepare_file_for_viewing(
            protected_path=protected_path,
            data_key=data_key,
        )


class DeleteProtectedItemFlowService:
    """UI-facing protected-item deletion flow."""

    def __init__(
        self,
        protected_item_service: ProtectedItemService,
        dashboard_data_service: DashboardDataService,
    ) -> None:
        self._protected_item_service = protected_item_service
        self._dashboard_data_service = dashboard_data_service

    def delete_item(self, item: ProtectedItemView) -> DashboardActionResult:
        artifact_path = Path(item.record.artifact_path)

        try:
            if artifact_path.exists():
                artifact_path.unlink()

            removed = self._protected_item_service.remove_metadata(item.record.id)
            if not removed:
                raise FileOperationError("The protected item could not be removed.")

            return DashboardActionResult(
                succeeded=True,
                message=f"Removed {artifact_path.name} from protection.",
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


BACKGROUND = "#051424"
SURFACE = "#051424"
SURFACE_LOWEST = "#010F1F"
SURFACE_LOW = "#0D1C2D"
SURFACE_CONTAINER = "#122131"
SURFACE_HIGH = "#1C2B3C"
SURFACE_HIGHEST = "#273647"
TEXT = "#D4E4FA"
TEXT_MUTED = "#C4C7C7"
OUTLINE = "#444748"
TEAL = "#00DCE5"
TEAL_DARK = "#003739"
AMBER = "#FFB77D"
ERROR = "#FFB4AB"
ERROR_BG = "#2A1116"
SIDEBAR_WIDTH = 260


def build_dashboard_screen(
    app,
    ctk,
    *,
    state: DashboardState,
    on_protect_file: Callable[[], None] | None = None,
    on_protect_folder: Callable[[], None] | None = None,
    on_restore_file: Callable[[], None] | None = None,
    on_open_item: Callable[[ProtectedItemView], None] | None = None,
    on_restore_item: Callable[[ProtectedItemView], None] | None = None,
    on_delete_item: Callable[[ProtectedItemView], None] | None = None,
    on_settings: Callable[[], None] | None = None,
    on_activity: Callable[[], None] | None = None,
    on_logout: Callable[[], None] | None = None,
    owner_email: str | None = None,
    riff_2fa_enabled: bool = False,
) -> None:
    """Render the main authenticated dashboard screen."""

    app.geometry("1180x760")
    app.minsize(980, 640)

    root = ctk.CTkFrame(app, corner_radius=0, fg_color=BACKGROUND)
    root.pack(fill="both", expand=True)
    root.grid_columnconfigure(0, minsize=SIDEBAR_WIDTH, weight=0)
    root.grid_columnconfigure(1, weight=1)
    root.grid_rowconfigure(0, weight=1)

    display_email = owner_email or "local owner"
    _build_sidebar(
        ctk,
        root,
        owner_email=display_email,
        on_protect_file=on_protect_file,
        on_restore_file=on_restore_file,
        on_settings=on_settings,
        on_activity=on_activity,
        on_logout=on_logout,
    )

    main = ctk.CTkFrame(root, corner_radius=0, fg_color=BACKGROUND)
    main.grid(row=0, column=1, sticky="nsew")
    main.grid_columnconfigure(0, weight=1)
    main.grid_rowconfigure(1, weight=1)

    _build_topbar(
        ctk,
        main,
        riff_2fa_enabled=riff_2fa_enabled,
        on_protect_file=on_protect_file,
        on_settings=on_settings,
    )

    content = ctk.CTkFrame(main, corner_radius=0, fg_color=BACKGROUND)
    content.grid(row=1, column=0, sticky="nsew", padx=24, pady=24)
    content.grid_columnconfigure(0, weight=1)
    content.grid_rowconfigure(1, weight=1)

    _build_summary_section(
        ctk,
        content,
        state=state,
        owner_email=display_email,
        riff_2fa_enabled=riff_2fa_enabled,
        on_protect_file=on_protect_file,
        on_protect_folder=on_protect_folder,
    )

    _build_artifacts_section(
        ctk,
        content,
        state=state,
        on_open_item=on_open_item,
        on_restore_item=on_restore_item,
        on_delete_item=on_delete_item,
    )


def _build_sidebar(
    ctk,
    parent,
    *,
    owner_email: str,
    on_protect_file: Callable[[], None] | None,
    on_restore_file: Callable[[], None] | None,
    on_settings: Callable[[], None] | None,
    on_activity: Callable[[], None] | None,
    on_logout: Callable[[], None] | None,
) -> None:
    sidebar = ctk.CTkFrame(
        parent,
        width=SIDEBAR_WIDTH,
        corner_radius=0,
        fg_color=SURFACE,
        border_width=0,
    )
    sidebar.grid(row=0, column=0, sticky="nsew")
    sidebar.grid_propagate(False)
    sidebar.grid_columnconfigure(0, weight=1)
    sidebar.grid_rowconfigure(1, weight=1)

    brand = ctk.CTkFrame(sidebar, fg_color="transparent")
    brand.grid(row=0, column=0, sticky="ew", padx=24, pady=(26, 22))
    brand.grid_columnconfigure(1, weight=1)

    logo = ctk.CTkFrame(brand, width=34, height=34, corner_radius=5, fg_color=TEAL)
    logo.grid(row=0, column=0, rowspan=2, sticky="w", padx=(0, 12))
    logo.grid_propagate(False)
    ctk.CTkLabel(
        logo,
        text="RL",
        text_color=TEAL_DARK,
        font=ctk.CTkFont(size=12, weight="bold", family="Consolas"),
    ).place(relx=0.5, rely=0.5, anchor="center")

    ctk.CTkLabel(
        brand,
        text="RiffLock",
        text_color=TEAL,
        font=ctk.CTkFont(size=24, weight="bold"),
        anchor="w",
    ).grid(row=0, column=1, sticky="w")
    ctk.CTkLabel(
        brand,
        text="LOCAL-FIRST ENCRYPTION",
        text_color=TEXT_MUTED,
        font=ctk.CTkFont(size=10, weight="bold", family="Consolas"),
        anchor="w",
    ).grid(row=1, column=1, sticky="w", pady=(3, 0))

    nav = ctk.CTkFrame(sidebar, fg_color="transparent")
    nav.grid(row=1, column=0, sticky="new", pady=(6, 0))
    nav.grid_columnconfigure(0, weight=1)

    _nav_button(ctk, nav, "Dashboard", row=0, active=True)
    _nav_button(ctk, nav, "Protect", row=1, command=on_protect_file)
    _nav_button(ctk, nav, "Restore", row=2, command=on_restore_file)
    _nav_button(ctk, nav, "Riff 2FA", row=3, command=on_settings)
    _nav_button(ctk, nav, "Activity", row=4, command=on_activity)
    _nav_button(ctk, nav, "Settings", row=5, command=on_settings)

    session = ctk.CTkFrame(
        sidebar,
        fg_color=SURFACE_LOW,
        border_width=1,
        border_color=OUTLINE,
        corner_radius=0,
    )
    session.grid(row=2, column=0, sticky="sew", padx=0, pady=0)
    session.grid_columnconfigure(0, weight=1)

    ctk.CTkButton(
        session,
        text="Secure Vault",
        height=34,
        corner_radius=4,
        fg_color=TEAL,
        hover_color="#63F7FF",
        text_color=TEAL_DARK,
        font=ctk.CTkFont(size=12, weight="bold"),
        command=on_protect_file or (lambda: None),
    ).grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 14))

    ctk.CTkLabel(
        session,
        text=owner_email,
        text_color=TEXT_MUTED,
        font=ctk.CTkFont(size=11, family="Consolas"),
        anchor="w",
    ).grid(row=1, column=0, sticky="ew", padx=24, pady=(0, 8))
    ctk.CTkLabel(
        session,
        text="UNLOCKED LOCALLY",
        text_color=TEAL,
        font=ctk.CTkFont(size=11, weight="bold", family="Consolas"),
        anchor="w",
    ).grid(row=2, column=0, sticky="ew", padx=24, pady=(0, 12))
    ctk.CTkButton(
        session,
        text="Logout",
        height=30,
        corner_radius=4,
        fg_color="transparent",
        hover_color=ERROR_BG,
        text_color=TEXT_MUTED,
        font=ctk.CTkFont(size=11, family="Consolas"),
        command=on_logout or (lambda: None),
    ).grid(row=3, column=0, sticky="ew", padx=24, pady=(0, 20))


def _nav_button(
    ctk,
    parent,
    label: str,
    *,
    row: int,
    command: Callable[[], None] | None = None,
    active: bool = False,
    disabled: bool = False,
) -> None:
    button = ctk.CTkButton(
        parent,
        text=label,
        height=40,
        corner_radius=0,
        fg_color=SURFACE_HIGH if active else "transparent",
        hover_color=SURFACE_HIGHEST,
        text_color=TEAL if active else TEXT_MUTED,
        font=ctk.CTkFont(size=14, weight="bold" if active else "normal"),
        anchor="w",
        command=command or (lambda: None),
        state="disabled" if disabled else "normal",
    )
    button.grid(row=row, column=0, sticky="ew")


def _build_topbar(
    ctk,
    parent,
    *,
    riff_2fa_enabled: bool,
    on_protect_file: Callable[[], None] | None,
    on_settings: Callable[[], None] | None,
) -> None:
    topbar = ctk.CTkFrame(
        parent,
        height=64,
        corner_radius=0,
        fg_color=SURFACE_LOW,
        border_width=1,
        border_color=OUTLINE,
    )
    topbar.grid(row=0, column=0, sticky="ew")
    topbar.grid_propagate(False)
    topbar.grid_columnconfigure(0, weight=1)

    left = ctk.CTkFrame(topbar, fg_color="transparent")
    left.grid(row=0, column=0, sticky="w", padx=24)
    ctk.CTkLabel(
        left,
        text="Vault Dashboard",
        text_color=TEXT,
        font=ctk.CTkFont(size=18, weight="bold"),
    ).pack(side="left")
    _status_pill(
        ctk,
        left,
        "2FA ENABLED" if riff_2fa_enabled else "2FA DISABLED",
        TEAL if riff_2fa_enabled else AMBER,
    ).pack(side="left", padx=(14, 0))

    right = ctk.CTkFrame(topbar, fg_color="transparent")
    right.grid(row=0, column=1, sticky="e", padx=24)
    ctk.CTkButton(
        right,
        text="Vault Status",
        height=30,
        width=110,
        corner_radius=4,
        fg_color="transparent",
        hover_color=SURFACE_HIGHEST,
        border_width=1,
        border_color=OUTLINE,
        text_color=TEXT,
        font=ctk.CTkFont(size=11, family="Consolas"),
        command=on_settings or (lambda: None),
    ).pack(side="left", padx=(0, 8))
    ctk.CTkButton(
        right,
        text="Encrypt Now",
        height=30,
        width=110,
        corner_radius=4,
        fg_color=TEAL,
        hover_color="#63F7FF",
        text_color=TEAL_DARK,
        font=ctk.CTkFont(size=11, weight="bold", family="Consolas"),
        command=on_protect_file or (lambda: None),
    ).pack(side="left")


def _build_summary_section(
    ctk,
    parent,
    *,
    state: DashboardState,
    owner_email: str,
    riff_2fa_enabled: bool,
    on_protect_file: Callable[[], None] | None,
    on_protect_folder: Callable[[], None] | None,
) -> None:
    section = ctk.CTkFrame(parent, fg_color="transparent")
    section.grid(row=0, column=0, sticky="ew", pady=(0, 18))
    section.grid_columnconfigure(0, weight=3)
    section.grid_columnconfigure(1, weight=1)

    summary = ctk.CTkFrame(
        section,
        fg_color=SURFACE_CONTAINER,
        border_width=1,
        border_color=OUTLINE,
        corner_radius=4,
    )
    summary.grid(row=0, column=0, sticky="nsew", padx=(0, 18))
    summary.grid_columnconfigure(0, weight=1)

    ctk.CTkLabel(
        summary,
        text="Vault Unlocked",
        text_color=TEAL,
        font=ctk.CTkFont(size=24, weight="bold"),
        anchor="w",
    ).grid(row=0, column=0, sticky="ew", padx=22, pady=(22, 4))
    ctk.CTkLabel(
        summary,
        text=f"Connected as {owner_email}. Your local data key is available only for this session.",
        text_color=TEXT_MUTED,
        font=ctk.CTkFont(size=13),
        anchor="w",
        wraplength=570,
    ).grid(row=1, column=0, sticky="ew", padx=22, pady=(0, 20))

    actions = ctk.CTkFrame(summary, fg_color="transparent")
    actions.grid(row=2, column=0, sticky="ew", padx=22, pady=(0, 22))
    actions.grid_columnconfigure(0, weight=1)
    actions.grid_columnconfigure(1, weight=1)
    _quick_action(ctk, actions, "Protect File", "Individual file artifact", row=0, column=0, command=on_protect_file)
    _quick_action(ctk, actions, "Protect Folder", "Recursive project directory", row=0, column=1, command=on_protect_folder)

    stats = ctk.CTkFrame(section, fg_color="transparent")
    stats.grid(row=0, column=1, sticky="nsew")
    stats.grid_columnconfigure(0, weight=1)
    counts = _dashboard_counts(state)
    _stat_card(ctk, stats, row=0, label="Protected Files", value=str(counts["files"]), note="Current vault", color=TEAL)
    _stat_card(ctk, stats, row=1, label="Protected Folders", value=str(counts["folders"]), note="Folder artifacts", color=TEAL)
    _stat_card(ctk, stats, row=2, label="Missing Sources", value=str(counts["missing"]), note="Action required" if counts["missing"] else "No issues", color=ERROR if counts["missing"] else TEXT_MUTED)


def _quick_action(ctk, parent, label: str, detail: str, *, row: int, column: int, command: Callable[[], None] | None) -> None:
    button = ctk.CTkButton(
        parent,
        text=f"{label}\n{detail}",
        height=70,
        corner_radius=4,
        fg_color=SURFACE_HIGHEST,
        hover_color=SURFACE_HIGH,
        border_width=1,
        border_color=OUTLINE,
        text_color=TEXT,
        font=ctk.CTkFont(size=14, weight="bold"),
        anchor="w",
        command=command or (lambda: None),
    )
    button.grid(row=row, column=column, sticky="ew", padx=(0 if column == 0 else 10, 0))


def _stat_card(ctk, parent, *, row: int, label: str, value: str, note: str, color: str) -> None:
    card = ctk.CTkFrame(
        parent,
        fg_color=SURFACE_LOW,
        border_width=1,
        border_color=OUTLINE,
        corner_radius=3,
    )
    card.grid(row=row, column=0, sticky="ew", pady=(0 if row == 0 else 10, 0))
    card.grid_columnconfigure(0, weight=1)
    ctk.CTkLabel(
        card,
        text=label.upper(),
        text_color=TEXT_MUTED if color != ERROR else ERROR,
        font=ctk.CTkFont(size=10, weight="bold", family="Consolas"),
        anchor="w",
    ).grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 2))
    ctk.CTkLabel(
        card,
        text=value,
        text_color=TEXT if color != ERROR else ERROR,
        font=ctk.CTkFont(size=28, weight="bold"),
        anchor="w",
    ).grid(row=1, column=0, sticky="ew", padx=14)
    ctk.CTkLabel(
        card,
        text=note,
        text_color=color,
        font=ctk.CTkFont(size=10, family="Consolas"),
        anchor="w",
    ).grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 12))


def _build_artifacts_section(
    ctk,
    parent,
    *,
    state: DashboardState,
    on_open_item: Callable[[ProtectedItemView], None] | None,
    on_restore_item: Callable[[ProtectedItemView], None] | None,
    on_delete_item: Callable[[ProtectedItemView], None] | None,
) -> None:
    section = ctk.CTkFrame(
        parent,
        fg_color=SURFACE_LOWEST,
        border_width=1,
        border_color=OUTLINE,
        corner_radius=3,
    )
    section.grid(row=1, column=0, sticky="nsew")
    section.grid_columnconfigure(0, weight=1)
    section.grid_rowconfigure(2, weight=1)

    toolbar = ctk.CTkFrame(section, height=58, corner_radius=0, fg_color=SURFACE_LOW)
    toolbar.grid(row=0, column=0, sticky="ew")
    toolbar.grid_propagate(False)
    toolbar.grid_columnconfigure(0, weight=1)

    ctk.CTkLabel(
        toolbar,
        text="Protected Artifacts",
        text_color=TEXT,
        font=ctk.CTkFont(size=18, weight="bold"),
        anchor="w",
    ).grid(row=0, column=0, sticky="w", padx=16)

    filter_entry = ctk.CTkEntry(
        toolbar,
        width=260,
        height=32,
        corner_radius=4,
        fg_color=SURFACE,
        border_color=OUTLINE,
        text_color=TEXT,
        placeholder_text="Filter artifacts...",
        placeholder_text_color="#708093",
        font=ctk.CTkFont(size=12),
    )
    filter_entry.grid(row=0, column=1, sticky="e", padx=16)

    header = ctk.CTkFrame(section, height=42, corner_radius=0, fg_color=SURFACE_CONTAINER)
    header.grid(row=1, column=0, sticky="ew")
    header.grid_propagate(False)
    _configure_table_columns(header)
    for column, label in enumerate(("Artifact Name", "Type", "Status", "Size", "Timestamp", "Source", "Actions")):
        ctk.CTkLabel(
            header,
            text=label.upper(),
            text_color=TEXT_MUTED,
            font=ctk.CTkFont(size=10, weight="bold", family="Consolas"),
            anchor="e" if column == 6 else "w",
        ).grid(row=0, column=column, sticky="ew", padx=8, pady=12)

    scroll = ctk.CTkScrollableFrame(section, fg_color=SURFACE_LOWEST, corner_radius=0)
    scroll.grid(row=2, column=0, sticky="nsew")
    scroll.grid_columnconfigure(0, weight=1)

    footer = ctk.CTkFrame(section, height=48, corner_radius=0, fg_color=SURFACE_LOW)
    footer.grid(row=3, column=0, sticky="ew")
    footer.grid_propagate(False)
    footer.grid_columnconfigure(0, weight=1)
    footer_label = ctk.CTkLabel(
        footer,
        text="",
        text_color=TEXT_MUTED,
        font=ctk.CTkFont(size=11, family="Consolas"),
        anchor="w",
    )
    footer_label.grid(row=0, column=0, sticky="w", padx=16)

    def render_rows(_event=None) -> None:
        query = filter_entry.get().strip().lower()
        for child in scroll.winfo_children():
            child.destroy()
        filtered = [item for item in state.items if _matches_item(item, query)]
        if not filtered:
            _render_empty_artifacts(ctk, scroll, state.is_empty)
        else:
            for index, item in enumerate(filtered):
                _artifact_row(
                    ctk,
                    scroll,
                    item=item,
                    row=index,
                    on_open_item=on_open_item,
                    on_restore_item=on_restore_item,
                    on_delete_item=on_delete_item,
                )
        footer_label.configure(text=f"Showing {len(filtered)} of {len(state.items)} artifacts")

    filter_entry.bind("<KeyRelease>", render_rows)
    render_rows()


def _artifact_row(
    ctk,
    parent,
    *,
    item: ProtectedItemView,
    row: int,
    on_open_item: Callable[[ProtectedItemView], None] | None,
    on_restore_item: Callable[[ProtectedItemView], None] | None,
    on_delete_item: Callable[[ProtectedItemView], None] | None,
) -> None:
    status_color = _status_color(item)
    row_color = ERROR_BG if status_color == ERROR else (SURFACE_LOW if row % 2 == 0 else SURFACE_LOWEST)
    frame = ctk.CTkFrame(parent, fg_color=row_color, corner_radius=0, border_width=0)
    frame.grid(row=row, column=0, sticky="ew")
    frame.grid_columnconfigure(0, weight=1)
    _configure_table_columns(frame)

    artifact_name = _path_name(item.record.artifact_path)
    source_hint = _compact_path(item.record.source_path)
    name_cell = ctk.CTkFrame(frame, fg_color="transparent")
    name_cell.grid(row=0, column=0, sticky="ew", padx=8, pady=8)
    name_cell.grid_columnconfigure(0, weight=1)
    ctk.CTkLabel(
        name_cell,
        text=artifact_name,
        text_color=ERROR if status_color == ERROR else TEXT,
        font=ctk.CTkFont(size=13, weight="bold"),
        anchor="w",
    ).grid(row=0, column=0, sticky="ew")
    ctk.CTkLabel(
        name_cell,
        text=source_hint,
        text_color=TEXT_MUTED,
        font=ctk.CTkFont(size=10, family="Consolas"),
        anchor="w",
    ).grid(row=1, column=0, sticky="ew", pady=(2, 0))

    _cell(ctk, frame, 1, item.record.item_type.upper(), TEXT_MUTED)
    _cell(ctk, frame, 2, item.record.status.upper(), status_color)
    _cell(ctk, frame, 3, _format_size(item.record.file_size), TEXT_MUTED)
    _cell(ctk, frame, 4, _compact_timestamp(item.record.updated_at), TEXT_MUTED)
    _cell(ctk, frame, 5, "OK" if item.source_exists else "MISS", TEAL if item.source_exists else ERROR)

    actions = ctk.CTkFrame(frame, fg_color="transparent")
    actions.grid(row=0, column=6, sticky="e", padx=8, pady=8)
    is_file = item.record.item_type == "file"
    can_use_artifact = is_file and item.protected_exists
    _row_button(ctk, actions, "Open", lambda: on_open_item(item) if on_open_item else None, enabled=can_use_artifact and on_open_item is not None)
    _row_button(ctk, actions, "Restore", lambda: on_restore_item(item) if on_restore_item else None, enabled=can_use_artifact and on_restore_item is not None)
    _row_button(ctk, actions, "Delete", lambda: on_delete_item(item) if on_delete_item else None, enabled=on_delete_item is not None, danger=True)


def _cell(ctk, parent, column: int, text: str, color: str) -> None:
    ctk.CTkLabel(
        parent,
        text=text,
        text_color=color,
        font=ctk.CTkFont(size=11, family="Consolas"),
        anchor="w",
    ).grid(row=0, column=column, sticky="ew", padx=8, pady=10)


def _row_button(ctk, parent, text: str, command, *, enabled: bool, danger: bool = False) -> None:
    button = ctk.CTkButton(
        parent,
        text=text,
        width=62,
        height=28,
        corner_radius=4,
        fg_color="transparent",
        hover_color=ERROR_BG if danger else SURFACE_HIGHEST,
        border_width=1,
        border_color=ERROR if danger else OUTLINE,
        text_color=ERROR if danger else TEAL,
        font=ctk.CTkFont(size=10, family="Consolas"),
        command=command or (lambda: None),
        state="normal" if enabled else "disabled",
    )
    button.pack(side="left", padx=(0, 6))


def _render_empty_artifacts(ctk, parent, is_empty_dashboard: bool) -> None:
    message = "No protected items yet." if is_empty_dashboard else "No artifacts match the current filter."
    detail = "Protect a file or folder to create your first .rifflock artifact." if is_empty_dashboard else "Clear the filter to see all protected artifacts."
    empty = ctk.CTkFrame(parent, fg_color="transparent")
    empty.grid(row=0, column=0, sticky="nsew", pady=80)
    empty.grid_columnconfigure(0, weight=1)
    ctk.CTkLabel(
        empty,
        text=message,
        text_color=TEXT,
        font=ctk.CTkFont(size=20, weight="bold"),
    ).grid(row=0, column=0)
    ctk.CTkLabel(
        empty,
        text=detail,
        text_color=TEXT_MUTED,
        font=ctk.CTkFont(size=13),
        wraplength=420,
    ).grid(row=1, column=0, pady=(8, 0))


def _configure_table_columns(frame) -> None:
    widths = (280, 70, 120, 90, 130, 70, 210)
    for index, width in enumerate(widths):
        frame.grid_columnconfigure(index, minsize=width, weight=1 if index == 0 else 0)


def _status_pill(ctk, parent, text: str, color: str):
    pill = ctk.CTkFrame(parent, fg_color=SURFACE_CONTAINER, border_width=1, border_color=OUTLINE, corner_radius=999)
    ctk.CTkLabel(
        pill,
        text=text,
        text_color=color,
        font=ctk.CTkFont(size=10, weight="bold", family="Consolas"),
    ).pack(padx=12, pady=5)
    return pill


def _dashboard_counts(state: DashboardState) -> dict[str, int]:
    return {
        "files": sum(1 for item in state.items if item.record.item_type == "file"),
        "folders": sum(1 for item in state.items if item.record.item_type == "folder"),
        "missing": sum(1 for item in state.items if not item.source_exists or not item.protected_exists),
    }


def _matches_item(item: ProtectedItemView, query: str) -> bool:
    if not query:
        return True
    values = (
        item.record.artifact_path,
        item.record.source_path,
        item.record.item_type,
        item.record.status,
    )
    return any(query in str(value).lower() for value in values)


def _status_color(item: ProtectedItemView) -> str:
    if item.record.status == "error" or not item.protected_exists:
        return ERROR
    if item.record.status == "missing_source" or not item.source_exists:
        return ERROR
    if item.record.status == "restored":
        return TEXT_MUTED
    return TEAL


def _format_size(size: int | None) -> str:
    if size is None:
        return "-"
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return f"{value:.1f} GB"


def _compact_timestamp(value: str) -> str:
    return value.replace("T", " ").replace("Z", "")[:16] if value else "-"


def _path_name(value: str) -> str:
    name = Path(value).name
    return name or value


def _compact_path(value: str) -> str:
    if len(value) <= 64:
        return value
    return f"...{value[-61:]}"
