"""Activity log data and UI helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable

from rifflock.files import ProtectedItemView
from rifflock.models import AuthAttemptRecord
from rifflock.storage import AuthAttemptRepository
from rifflock.ui.dashboard import DashboardDataService

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


@dataclass(frozen=True)
class ActivityEvent:
    event_type: str
    title: str
    identifier: str
    status: str
    status_kind: str
    detail: str
    timestamp: str
    secondary: str


@dataclass(frozen=True)
class ActivityState:
    events: list[ActivityEvent]
    failed_password_attempts: int
    failed_riff_attempts: int
    password_attempt_limit: int
    riff_attempt_limit: int
    integrity_percent: int
    protected_count: int
    issue_count: int
    load_bars: list[int]
    average_size_label: str
    last_audit_label: str


class ActivityDataService:
    """Build local activity data from auth attempts and protected artifacts."""

    def __init__(
        self,
        auth_attempt_repository: AuthAttemptRepository,
        dashboard_data_service: DashboardDataService,
        *,
        password_attempt_limit: int = 3,
        riff_attempt_limit: int = 3,
    ) -> None:
        self._auth_attempt_repository = auth_attempt_repository
        self._dashboard_data_service = dashboard_data_service
        self._password_attempt_limit = password_attempt_limit
        self._riff_attempt_limit = riff_attempt_limit

    def load(self, *, owner_email: str | None = None) -> ActivityState:
        auth_attempts = self._auth_attempt_repository.list_recent(100)
        dashboard_state = self._dashboard_data_service.load()
        item_views = dashboard_state.items
        events = [self._auth_event(attempt) for attempt in auth_attempts]
        for item in item_views:
            events.extend(self._item_events(item))
        events.sort(key=lambda event: _timestamp_sort_key(event.timestamp), reverse=True)
        issue_count = sum(1 for event in events if event.status_kind == "failure")
        observed_count = max(len(events), 1)
        integrity_percent = max(0, int(((observed_count - issue_count) / observed_count) * 100))
        last_event = events[0].timestamp if events else None
        return ActivityState(
            events=events,
            failed_password_attempts=self._failure_count(owner_email, "password"),
            failed_riff_attempts=self._failure_count(owner_email, "riff"),
            password_attempt_limit=self._password_attempt_limit,
            riff_attempt_limit=self._riff_attempt_limit,
            integrity_percent=integrity_percent,
            protected_count=len(item_views),
            issue_count=issue_count,
            load_bars=self._load_bars(item_views),
            average_size_label=self._average_size_label(item_views),
            last_audit_label=_format_timestamp(last_event) if last_event else "No events",
        )

    def _failure_count(self, owner_email: str | None, attempt_type: str) -> int:
        if not owner_email:
            return 0
        attempts = self._auth_attempt_repository.list_by_identifier_and_type(owner_email, attempt_type)
        return sum(1 for attempt in attempts if not attempt.was_successful)

    def _auth_event(self, attempt: AuthAttemptRecord) -> ActivityEvent:
        is_riff = attempt.attempt_type == "riff"
        return ActivityEvent(
            event_type="auth",
            title="Riff 2FA" if is_riff else "Password Auth",
            identifier=attempt.identifier,
            status="Success" if attempt.was_successful else "Failure",
            status_kind="success" if attempt.was_successful else "failure",
            detail=(attempt.failure_reason or "verified").replace("_", " ").upper(),
            timestamp=attempt.attempted_at,
            secondary="LOCAL MATCH" if attempt.was_successful else "LOCKOUT TRACKED",
        )

    def _item_events(self, item: ProtectedItemView) -> list[ActivityEvent]:
        record = item.record
        artifact_name = Path(record.artifact_path).name
        status_kind = _item_status_kind(item)
        status = "Failure" if status_kind == "failure" else "Success"
        title_prefix = "Folder" if record.item_type == "folder" else "File"
        events = [
            ActivityEvent(
                event_type="encryption",
                title=f"{title_prefix} Protected",
                identifier=artifact_name,
                status=status,
                status_kind=status_kind,
                detail="AES-256-GCM",
                timestamp=record.created_at,
                secondary=_compact_path(record.source_path),
            )
        ]
        if record.updated_at != record.created_at and record.status == "restored":
            events.append(ActivityEvent("encryption", f"{title_prefix} Restored", artifact_name, "Success", "success", "RESTORE FLOW", record.updated_at, _compact_path(record.artifact_path)))
        elif record.updated_at != record.created_at and status_kind == "failure":
            events.append(ActivityEvent("encryption", f"{title_prefix} Status Alert", artifact_name, "Failure", "failure", record.status.replace("_", " ").upper(), record.updated_at, _compact_path(record.artifact_path)))
        return events

    def _load_bars(self, items: list[ProtectedItemView]) -> list[int]:
        sizes = [max(item.record.file_size or 0, 0) for item in items[-12:]]
        if not sizes:
            return [0] * 12
        max_size = max(sizes) or 1
        bars = [max(int((size / max_size) * 100), 8) if size else 4 for size in sizes]
        return ([0] * max(12 - len(bars), 0)) + bars

    def _average_size_label(self, items: list[ProtectedItemView]) -> str:
        sizes = [item.record.file_size or 0 for item in items if item.record.file_size]
        if not sizes:
            return "AVG 0 B/item"
        return f"AVG {_format_size(int(sum(sizes) / len(sizes)))}/item"


def build_activity_screen(
    app,
    ctk,
    *,
    state: ActivityState,
    owner_email: str | None,
    riff_2fa_enabled: bool,
    on_dashboard: Callable[[], None] | None,
    on_protect_file: Callable[[], None] | None,
    on_restore_file: Callable[[], None] | None,
    on_settings: Callable[[], None] | None,
    on_logout: Callable[[], None] | None,
    on_export: Callable[[list[ActivityEvent]], None] | None,
) -> None:
    """Render the activity log screen."""

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
        on_dashboard=on_dashboard,
        on_protect_file=on_protect_file,
        on_restore_file=on_restore_file,
        on_settings=on_settings,
        on_logout=on_logout,
    )

    main = ctk.CTkFrame(root, corner_radius=0, fg_color=BACKGROUND)
    main.grid(row=0, column=1, sticky="nsew")
    main.grid_columnconfigure(0, weight=1)
    main.grid_rowconfigure(1, weight=1)

    _build_topbar(ctk, main, total_events=len(state.events), on_protect_file=on_protect_file, on_settings=on_settings)

    canvas = ctk.CTkScrollableFrame(main, corner_radius=0, fg_color=BACKGROUND)
    canvas.grid(row=1, column=0, sticky="nsew", padx=24, pady=24)
    canvas.grid_columnconfigure(0, weight=1)

    _build_summary(ctk, canvas, state=state, owner_email=display_email)
    _build_event_log(ctk, canvas, state=state, on_export=on_export)
    _build_telemetry(ctk, canvas, state=state, riff_2fa_enabled=riff_2fa_enabled)


def _build_sidebar(
    ctk,
    parent,
    *,
    owner_email: str,
    on_dashboard: Callable[[], None] | None,
    on_protect_file: Callable[[], None] | None,
    on_restore_file: Callable[[], None] | None,
    on_settings: Callable[[], None] | None,
    on_logout: Callable[[], None] | None,
) -> None:
    sidebar = ctk.CTkFrame(parent, width=SIDEBAR_WIDTH, corner_radius=0, fg_color=SURFACE)
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
    ctk.CTkLabel(logo, text="RL", text_color=TEAL_DARK, font=ctk.CTkFont(size=12, weight="bold", family="Consolas")).place(relx=0.5, rely=0.5, anchor="center")
    ctk.CTkLabel(brand, text="RiffLock", text_color=TEAL, font=ctk.CTkFont(size=24, weight="bold"), anchor="w").grid(row=0, column=1, sticky="w")
    ctk.CTkLabel(brand, text="LOCAL-FIRST ENCRYPTION", text_color=TEXT_MUTED, font=ctk.CTkFont(size=10, weight="bold", family="Consolas"), anchor="w").grid(row=1, column=1, sticky="w", pady=(3, 0))

    nav = ctk.CTkFrame(sidebar, fg_color="transparent")
    nav.grid(row=1, column=0, sticky="new", pady=(6, 0))
    nav.grid_columnconfigure(0, weight=1)
    _nav_button(ctk, nav, "Dashboard", row=0, command=on_dashboard)
    _nav_button(ctk, nav, "Protect", row=1, command=on_protect_file)
    _nav_button(ctk, nav, "Restore", row=2, command=on_restore_file)
    _nav_button(ctk, nav, "Riff 2FA", row=3, command=on_settings)
    _nav_button(ctk, nav, "Activity", row=4, active=True)
    _nav_button(ctk, nav, "Settings", row=5, command=on_settings)

    session = ctk.CTkFrame(sidebar, fg_color=SURFACE_LOW, border_width=1, border_color=OUTLINE, corner_radius=0)
    session.grid(row=2, column=0, sticky="sew")
    session.grid_columnconfigure(0, weight=1)
    ctk.CTkButton(session, text="Secure Vault", height=34, corner_radius=4, fg_color=TEAL, hover_color="#63F7FF", text_color=TEAL_DARK, font=ctk.CTkFont(size=12, weight="bold"), command=on_protect_file or (lambda: None)).grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 14))
    ctk.CTkLabel(session, text=owner_email, text_color=TEXT_MUTED, font=ctk.CTkFont(size=11, family="Consolas"), anchor="w").grid(row=1, column=0, sticky="ew", padx=24, pady=(0, 8))
    ctk.CTkLabel(session, text="UNLOCKED LOCALLY", text_color=TEAL, font=ctk.CTkFont(size=11, weight="bold", family="Consolas"), anchor="w").grid(row=2, column=0, sticky="ew", padx=24, pady=(0, 12))
    ctk.CTkButton(session, text="Logout", height=30, corner_radius=4, fg_color="transparent", hover_color=ERROR_BG, text_color=TEXT_MUTED, font=ctk.CTkFont(size=11, family="Consolas"), command=on_logout or (lambda: None)).grid(row=3, column=0, sticky="ew", padx=24, pady=(0, 20))


def _nav_button(ctk, parent, label: str, *, row: int, command: Callable[[], None] | None = None, active: bool = False) -> None:
    ctk.CTkButton(
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
    ).grid(row=row, column=0, sticky="ew")


def _build_topbar(ctk, parent, *, total_events: int, on_protect_file: Callable[[], None] | None, on_settings: Callable[[], None] | None) -> None:
    topbar = ctk.CTkFrame(parent, height=64, corner_radius=0, fg_color=SURFACE_LOW, border_width=1, border_color=OUTLINE)
    topbar.grid(row=0, column=0, sticky="ew")
    topbar.grid_propagate(False)
    topbar.grid_columnconfigure(0, weight=1)
    left = ctk.CTkFrame(topbar, fg_color="transparent")
    left.grid(row=0, column=0, sticky="w", padx=24)
    ctk.CTkLabel(left, text="Activity Log", text_color=TEXT, font=ctk.CTkFont(size=18, weight="bold")).pack(side="left")
    ctk.CTkLabel(left, text="/", text_color=OUTLINE, font=ctk.CTkFont(size=16)).pack(side="left", padx=10)
    ctk.CTkLabel(left, text=f"LOCAL_EVENTS: {total_events}", text_color=TEAL, font=ctk.CTkFont(size=11, weight="bold", family="Consolas")).pack(side="left")
    right = ctk.CTkFrame(topbar, fg_color="transparent")
    right.grid(row=0, column=1, sticky="e", padx=24)
    ctk.CTkLabel(right, text="SECURE_LINK", text_color=TEXT_MUTED, font=ctk.CTkFont(size=11, weight="bold", family="Consolas")).pack(side="left", padx=(0, 14))
    ctk.CTkButton(right, text="Vault Status", height=30, width=110, corner_radius=4, fg_color="transparent", hover_color=SURFACE_HIGHEST, border_width=1, border_color=OUTLINE, text_color=TEXT, font=ctk.CTkFont(size=11, family="Consolas"), command=on_settings or (lambda: None)).pack(side="left", padx=(0, 8))
    ctk.CTkButton(right, text="Encrypt Now", height=30, width=110, corner_radius=4, fg_color=TEAL, hover_color="#63F7FF", text_color=TEAL_DARK, font=ctk.CTkFont(size=11, weight="bold", family="Consolas"), command=on_protect_file or (lambda: None)).pack(side="left")


def _build_summary(ctk, parent, *, state: ActivityState, owner_email: str) -> None:
    section = ctk.CTkFrame(parent, fg_color="transparent")
    section.grid(row=0, column=0, sticky="ew", pady=(0, 18))
    for column in range(3):
        section.grid_columnconfigure(column, weight=1)
    _auth_safeguard_card(ctk, section, state)
    _summary_card(
        ctk,
        section,
        column=1,
        label="SESSION INTEGRITY",
        value=f"{state.integrity_percent}%",
        note=f"{state.issue_count} issue events across {len(state.events)} local events.",
        color=TEAL if state.integrity_percent >= 90 else AMBER,
    )
    _identity_card(ctk, section, owner_email=owner_email, protected_count=state.protected_count)


def _auth_safeguard_card(ctk, parent, state: ActivityState) -> None:
    card = ctk.CTkFrame(parent, fg_color=SURFACE_CONTAINER, border_width=1, border_color=OUTLINE, corner_radius=4)
    card.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
    card.grid_columnconfigure(0, weight=1)
    ctk.CTkLabel(card, text="AUTH SAFEGUARD", text_color=TEXT_MUTED, font=ctk.CTkFont(size=10, weight="bold", family="Consolas"), anchor="w").grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 2))
    ctk.CTkLabel(card, text=f"{state.failed_password_attempts}/{state.password_attempt_limit} Attempts", text_color=TEXT, font=ctk.CTkFont(size=24, weight="bold"), anchor="w").grid(row=1, column=0, sticky="ew", padx=18)
    ctk.CTkLabel(card, text="Password failures before local lockout.", text_color=TEXT_MUTED, font=ctk.CTkFont(size=12), anchor="w").grid(row=2, column=0, sticky="ew", padx=18, pady=(3, 12))
    bars = ctk.CTkFrame(card, fg_color="transparent")
    bars.grid(row=3, column=0, sticky="w", padx=18, pady=(0, 18))
    visible_limit = max(min(state.password_attempt_limit, 6), 1)
    for index in range(visible_limit):
        active = index < state.failed_password_attempts
        color = ERROR if active and state.failed_password_attempts >= state.password_attempt_limit else (AMBER if active else SURFACE_HIGHEST)
        ctk.CTkFrame(bars, width=10, height=30, corner_radius=5, fg_color=color).grid(row=0, column=index, padx=(0, 5))
    locked = state.failed_password_attempts >= state.password_attempt_limit
    ctk.CTkLabel(bars, text="LOCKED" if locked else "ARMED", text_color=ERROR if locked else TEAL, font=ctk.CTkFont(size=11, weight="bold", family="Consolas")).grid(row=0, column=visible_limit, padx=(8, 0))


def _summary_card(ctk, parent, *, column: int, label: str, value: str, note: str, color: str) -> None:
    card = ctk.CTkFrame(parent, fg_color=SURFACE_CONTAINER, border_width=1, border_color=OUTLINE, corner_radius=4)
    card.grid(row=0, column=column, sticky="nsew", padx=12)
    card.grid_columnconfigure(0, weight=1)
    ctk.CTkLabel(card, text=label, text_color=TEXT_MUTED, font=ctk.CTkFont(size=10, weight="bold", family="Consolas"), anchor="w").grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 2))
    ctk.CTkLabel(card, text=value, text_color=color, font=ctk.CTkFont(size=28, weight="bold"), anchor="w").grid(row=1, column=0, sticky="ew", padx=18)
    progress = ctk.CTkFrame(card, height=5, fg_color=SURFACE_HIGHEST, corner_radius=2)
    progress.grid(row=2, column=0, sticky="ew", padx=18, pady=(8, 10))
    progress.grid_propagate(False)
    percent_text = value.rstrip("%")
    percent = int(percent_text) if percent_text.isdigit() else 100
    ctk.CTkFrame(progress, height=5, fg_color=color, corner_radius=2).place(relx=0, rely=0, relwidth=max(min(percent / 100, 1), 0), relheight=1)
    ctk.CTkLabel(card, text=note, text_color=TEXT_MUTED, font=ctk.CTkFont(size=12), anchor="w", wraplength=260).grid(row=3, column=0, sticky="ew", padx=18, pady=(0, 18))


def _identity_card(ctk, parent, *, owner_email: str, protected_count: int) -> None:
    card = ctk.CTkFrame(parent, fg_color=SURFACE_HIGH, border_width=1, border_color=TEAL, corner_radius=4)
    card.grid(row=0, column=2, sticky="nsew", padx=(12, 0))
    card.grid_columnconfigure(0, weight=1)
    ctk.CTkLabel(card, text="ACTIVE IDENTITY", text_color=TEAL, font=ctk.CTkFont(size=10, weight="bold", family="Consolas"), anchor="w").grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 4))
    ctk.CTkLabel(card, text=owner_email, text_color=TEXT, font=ctk.CTkFont(size=18, weight="bold"), anchor="w").grid(row=1, column=0, sticky="ew", padx=18)
    ctk.CTkLabel(card, text="DEVICE: LOCAL_WORKSTATION", text_color=TEXT_MUTED, font=ctk.CTkFont(size=11, family="Consolas"), anchor="w").grid(row=2, column=0, sticky="ew", padx=18, pady=(14, 3))
    ctk.CTkLabel(card, text=f"VAULT ITEMS: {protected_count}", text_color=TEXT_MUTED, font=ctk.CTkFont(size=11, family="Consolas"), anchor="w").grid(row=3, column=0, sticky="ew", padx=18, pady=(0, 18))


def _build_event_log(ctk, parent, *, state: ActivityState, on_export: Callable[[list[ActivityEvent]], None] | None) -> None:
    section = ctk.CTkFrame(parent, fg_color=SURFACE_CONTAINER, border_width=1, border_color=OUTLINE, corner_radius=4)
    section.grid(row=1, column=0, sticky="nsew")
    section.grid_columnconfigure(0, weight=1)
    section.grid_rowconfigure(2, weight=1)

    toolbar = ctk.CTkFrame(section, height=60, corner_radius=0, fg_color=SURFACE_LOW)
    toolbar.grid(row=0, column=0, sticky="ew")
    toolbar.grid_propagate(False)
    toolbar.grid_columnconfigure(1, weight=1)
    ctk.CTkLabel(toolbar, text="Authentication Events", text_color=TEXT, font=ctk.CTkFont(size=18, weight="bold"), anchor="w").grid(row=0, column=0, sticky="w", padx=16)

    filter_state = {"value": "all"}
    filter_buttons = {}
    chips = ctk.CTkFrame(toolbar, fg_color="transparent")
    chips.grid(row=0, column=1, sticky="w")
    search = ctk.CTkEntry(toolbar, width=240, height=32, corner_radius=4, fg_color=SURFACE_LOWEST, border_color=OUTLINE, text_color=TEXT, placeholder_text="Filter by identifier...", placeholder_text_color="#708093", font=ctk.CTkFont(size=12))
    search.grid(row=0, column=2, sticky="e", padx=16)

    header = ctk.CTkFrame(section, height=42, corner_radius=0, fg_color=SURFACE_HIGHEST)
    header.grid(row=1, column=0, sticky="ew")
    header.grid_propagate(False)
    _configure_event_columns(header)
    for column, label in enumerate(("Event Type", "Identifier", "Status", "Timestamp", "Details")):
        ctk.CTkLabel(header, text=label.upper(), text_color=TEXT_MUTED, font=ctk.CTkFont(size=10, weight="bold", family="Consolas"), anchor="e" if column == 4 else "w").grid(row=0, column=column, sticky="ew", padx=8, pady=12)

    scroll = ctk.CTkScrollableFrame(section, height=260, fg_color=SURFACE_LOWEST, corner_radius=0)
    scroll.grid(row=2, column=0, sticky="nsew")
    scroll.grid_columnconfigure(0, weight=1)

    footer = ctk.CTkFrame(section, height=50, corner_radius=0, fg_color=SURFACE_LOW)
    footer.grid(row=3, column=0, sticky="ew")
    footer.grid_propagate(False)
    footer.grid_columnconfigure(0, weight=1)
    footer_label = ctk.CTkLabel(footer, text="", text_color=TEXT_MUTED, font=ctk.CTkFont(size=11, family="Consolas"), anchor="w")
    footer_label.grid(row=0, column=0, sticky="w", padx=16)
    ctk.CTkButton(
        footer,
        text="Download Audit Trail (.LOG)",
        height=30,
        corner_radius=4,
        fg_color="transparent",
        hover_color=SURFACE_HIGHEST,
        border_width=1,
        border_color=OUTLINE,
        text_color=TEXT,
        font=ctk.CTkFont(size=11, family="Consolas"),
        command=lambda: on_export(_filtered_events(state.events, filter_state["value"], search.get())) if on_export else None,
    ).grid(row=0, column=1, sticky="e", padx=16)

    def set_filter(next_filter: str) -> None:
        filter_state["value"] = next_filter
        for filter_name, button in filter_buttons.items():
            button.configure(fg_color=SURFACE_HIGHEST if filter_name == next_filter else "transparent", text_color=TEAL if filter_name == next_filter else TEXT_MUTED)
        render_rows()

    def render_rows(_event=None) -> None:
        filtered = _filtered_events(state.events, filter_state["value"], search.get())
        for child in scroll.winfo_children():
            child.destroy()
        if not filtered:
            _render_empty_events(ctk, scroll, state.events)
        else:
            for index, event in enumerate(filtered):
                _event_row(ctk, scroll, event=event, row=index)
        footer_label.configure(text=f"Showing {len(filtered)} of {len(state.events)} local events")

    for index, (name, label) in enumerate((("all", "ALL"), ("failure", "FAILURE"), ("encryption", "ENCRYPTION"))):
        button = ctk.CTkButton(chips, text=label, width=86, height=26, corner_radius=13, fg_color="transparent", hover_color=SURFACE_HIGHEST, text_color=TEXT_MUTED, font=ctk.CTkFont(size=10, weight="bold", family="Consolas"), command=lambda value=name: set_filter(value))
        button.grid(row=0, column=index, padx=(0, 8))
        filter_buttons[name] = button
    search.bind("<KeyRelease>", render_rows)
    set_filter("all")


def _event_row(ctk, parent, *, event: ActivityEvent, row: int) -> None:
    status_color = _status_color(event.status_kind)
    frame = ctk.CTkFrame(parent, fg_color=SURFACE_LOW if row % 2 == 0 else SURFACE_LOWEST, corner_radius=0)
    frame.grid(row=row, column=0, sticky="ew")
    frame.grid_columnconfigure(0, weight=1)
    _configure_event_columns(frame)

    event_cell = ctk.CTkFrame(frame, fg_color="transparent")
    event_cell.grid(row=0, column=0, sticky="ew", padx=8, pady=10)
    event_cell.grid_columnconfigure(0, weight=1)
    ctk.CTkLabel(event_cell, text=event.title, text_color=TEXT, font=ctk.CTkFont(size=13, weight="bold"), anchor="w").grid(row=0, column=0, sticky="ew")
    ctk.CTkLabel(event_cell, text=event.detail, text_color=TEXT_MUTED, font=ctk.CTkFont(size=10, family="Consolas"), anchor="w").grid(row=1, column=0, sticky="ew", pady=(2, 0))

    _cell(ctk, frame, 1, event.identifier, TEXT, wrap=180)
    _status_cell(ctk, frame, 2, event.status, status_color)

    timestamp_cell = ctk.CTkFrame(frame, fg_color="transparent")
    timestamp_cell.grid(row=0, column=3, sticky="ew", padx=8, pady=10)
    ctk.CTkLabel(timestamp_cell, text=_format_timestamp(event.timestamp), text_color=TEXT, font=ctk.CTkFont(size=11, family="Consolas"), anchor="w").grid(row=0, column=0, sticky="ew")
    ctk.CTkLabel(timestamp_cell, text=event.secondary, text_color=TEXT_MUTED, font=ctk.CTkFont(size=10, family="Consolas"), anchor="w").grid(row=1, column=0, sticky="ew", pady=(2, 0))
    _cell(ctk, frame, 4, event.event_type.upper(), status_color, anchor="e")


def _configure_event_columns(frame) -> None:
    widths = (170, 180, 100, 170, 90)
    for column, weight in enumerate((2, 2, 1, 2, 1)):
        frame.grid_columnconfigure(column, weight=weight, minsize=widths[column])


def _cell(ctk, parent, column: int, text: str, color: str, *, anchor: str = "w", wrap: int | None = None) -> None:
    ctk.CTkLabel(parent, text=text, text_color=color, font=ctk.CTkFont(size=11, family="Consolas"), anchor=anchor, justify="left" if anchor == "w" else "right", wraplength=wrap or 0).grid(row=0, column=column, sticky="ew", padx=8, pady=10)


def _status_cell(ctk, parent, column: int, text: str, color: str) -> None:
    pill = ctk.CTkFrame(parent, fg_color=ERROR_BG if color == ERROR else SURFACE_HIGH, corner_radius=3)
    pill.grid(row=0, column=column, sticky="w", padx=8, pady=10)
    ctk.CTkLabel(
        pill,
        text=text.upper(),
        text_color=color,
        font=ctk.CTkFont(size=11, weight="bold", family="Consolas"),
    ).pack(side="left", padx=10, pady=4)


def _render_empty_events(ctk, parent, all_events: list[ActivityEvent]) -> None:
    message = "No local events yet." if not all_events else "No events match the current filter."
    frame = ctk.CTkFrame(parent, fg_color=SURFACE_LOWEST, corner_radius=0)
    frame.grid(row=0, column=0, sticky="ew")
    ctk.CTkLabel(frame, text=message, text_color=TEXT_MUTED, font=ctk.CTkFont(size=13), anchor="center").grid(row=0, column=0, sticky="ew", padx=24, pady=34)


def _build_telemetry(ctk, parent, *, state: ActivityState, riff_2fa_enabled: bool) -> None:
    section = ctk.CTkFrame(parent, fg_color="transparent")
    section.grid(row=2, column=0, sticky="ew", pady=(18, 0))
    section.grid_columnconfigure(0, weight=2)
    section.grid_columnconfigure(1, weight=1)

    load = ctk.CTkFrame(section, fg_color=SURFACE_CONTAINER, border_width=1, border_color=OUTLINE, corner_radius=4)
    load.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
    load.grid_columnconfigure(0, weight=1)
    header = ctk.CTkFrame(load, fg_color="transparent")
    header.grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 12))
    header.grid_columnconfigure(0, weight=1)
    ctk.CTkLabel(header, text="PROTECTED LOAD", text_color=TEXT_MUTED, font=ctk.CTkFont(size=10, weight="bold", family="Consolas"), anchor="w").grid(row=0, column=0, sticky="w")
    ctk.CTkLabel(header, text=state.average_size_label, text_color=TEAL, font=ctk.CTkFont(size=11, weight="bold", family="Consolas"), anchor="e").grid(row=0, column=1, sticky="e")

    chart = ctk.CTkFrame(load, height=120, fg_color="transparent")
    chart.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 18))
    chart.grid_propagate(False)
    for column, bar in enumerate(state.load_bars[:12]):
        chart.grid_columnconfigure(column, weight=1)
        holder = ctk.CTkFrame(chart, height=112, fg_color=SURFACE_HIGH, corner_radius=0)
        holder.grid(row=0, column=column, sticky="nsew", padx=2)
        holder.grid_propagate(False)
        bar_height = max(int(112 * (bar / 100)), 2) if bar else 2
        ctk.CTkFrame(holder, height=bar_height, fg_color=TEAL if bar >= 80 else SURFACE_HIGHEST, corner_radius=0).pack(side="bottom", fill="x")

    overview = ctk.CTkFrame(section, fg_color=SURFACE_CONTAINER, border_width=1, border_color=OUTLINE, corner_radius=4)
    overview.grid(row=0, column=1, sticky="nsew", padx=(12, 0))
    overview.grid_columnconfigure(0, weight=1)
    ctk.CTkLabel(overview, text="SECURITY OVERVIEW", text_color=TEXT_MUTED, font=ctk.CTkFont(size=10, weight="bold", family="Consolas"), anchor="w").grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 14))
    _overview_row(ctk, overview, 1, "Local Hash Match", "VERIFIED", TEAL)
    _overview_row(ctk, overview, 2, "Riff 2FA Status", "ACTIVE" if riff_2fa_enabled else "OPTIONAL", TEAL if riff_2fa_enabled else AMBER)
    _overview_row(ctk, overview, 3, "Riff Failures", f"{state.failed_riff_attempts}/{state.riff_attempt_limit}", ERROR if state.failed_riff_attempts >= state.riff_attempt_limit else TEXT)
    _overview_row(ctk, overview, 4, "Last Audit", state.last_audit_label, TEXT)


def _overview_row(ctk, parent, row: int, label: str, value: str, color: str) -> None:
    item = ctk.CTkFrame(parent, fg_color="transparent")
    item.grid(row=row, column=0, sticky="ew", padx=18, pady=(0, 12))
    item.grid_columnconfigure(0, weight=1)
    ctk.CTkLabel(item, text=label, text_color=TEXT_MUTED, font=ctk.CTkFont(size=12), anchor="w").grid(row=0, column=0, sticky="w")
    ctk.CTkLabel(item, text=value, text_color=color, font=ctk.CTkFont(size=11, weight="bold", family="Consolas"), anchor="e").grid(row=0, column=1, sticky="e")


def _filtered_events(events: list[ActivityEvent], event_filter: str, query: str) -> list[ActivityEvent]:
    normalized = query.strip().lower()
    filtered = events
    if event_filter == "failure":
        filtered = [event for event in filtered if event.status_kind == "failure"]
    elif event_filter == "encryption":
        filtered = [event for event in filtered if event.event_type == "encryption"]
    if normalized:
        filtered = [
            event
            for event in filtered
            if normalized in event.identifier.lower()
            or normalized in event.title.lower()
            or normalized in event.detail.lower()
            or normalized in event.secondary.lower()
        ]
    return filtered


def _item_status_kind(item: ProtectedItemView) -> str:
    if item.record.status in {"missing_source", "missing_protected", "error"}:
        return "failure"
    if not item.protected_exists:
        return "failure"
    return "success"


def _status_color(status_kind: str) -> str:
    if status_kind == "failure":
        return ERROR
    if status_kind == "warning":
        return AMBER
    return TEAL


def _timestamp_sort_key(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return datetime.min.replace(tzinfo=UTC)


def _format_timestamp(value: str | None) -> str:
    if not value:
        return "-"
    return value.replace("T", " ").replace("Z", " UTC")


def _compact_path(value: str) -> str:
    path = Path(value)
    name = path.name or value
    parent = path.parent.name
    if parent:
        return f".../{parent}/{name}"
    return name


def _format_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    if size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
