"""Settings screen UI helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from rifflock.settings import SettingsState
from rifflock.ui.copy import PASSWORD_LOSS_WARNING_TEXT, PASSWORD_LOSS_WARNING_TITLE

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


def build_settings_screen(
    app,
    ctk,
    *,
    state: SettingsState,
    on_save: Callable[[str, str], None],
    on_change_password: Callable[[], None],
    on_start_riff_enrollment: Callable[[], None],
    on_disable_riff_2fa: Callable[[], None],
    on_open_app_data_folder: Callable[[], None],
    on_back: Callable[[], None],
    on_protect_file: Callable[[], None] | None = None,
    on_restore_file: Callable[[], None] | None = None,
    on_activity: Callable[[], None] | None = None,
    on_logout: Callable[[], None] | None = None,
) -> None:
    """Render the owner settings screen."""

    app.geometry("1180x760")
    app.minsize(980, 640)

    root = ctk.CTkFrame(app, corner_radius=0, fg_color=BACKGROUND)
    root.pack(fill="both", expand=True)
    root.grid_columnconfigure(0, minsize=SIDEBAR_WIDTH, weight=0)
    root.grid_columnconfigure(1, weight=1)
    root.grid_rowconfigure(0, weight=1)

    _build_sidebar(
        ctk,
        root,
        owner_email=state.owner_email,
        on_dashboard=on_back,
        on_protect_file=on_protect_file,
        on_restore_file=on_restore_file,
        on_activity=on_activity,
        on_logout=on_logout,
    )

    main = ctk.CTkFrame(root, corner_radius=0, fg_color=BACKGROUND)
    main.grid(row=0, column=1, sticky="nsew")
    main.grid_columnconfigure(0, weight=1)
    main.grid_rowconfigure(1, weight=1)

    _build_topbar(ctk, main, state=state, on_back=on_back)

    canvas = ctk.CTkScrollableFrame(main, corner_radius=0, fg_color=BACKGROUND)
    canvas.grid(row=1, column=0, sticky="nsew", padx=34, pady=26)
    canvas.grid_columnconfigure(0, weight=1)

    inputs = _build_settings_content(
        ctk,
        canvas,
        state=state,
        on_change_password=on_change_password,
        on_start_riff_enrollment=on_start_riff_enrollment,
        on_disable_riff_2fa=on_disable_riff_2fa,
        on_open_app_data_folder=on_open_app_data_folder,
    )

    _build_footer(
        ctk,
        canvas,
        on_save=lambda: on_save(inputs["duration"].get(), inputs["threshold"].get()),
    )


def _build_sidebar(
    ctk,
    parent,
    *,
    owner_email: str,
    on_dashboard: Callable[[], None] | None,
    on_protect_file: Callable[[], None] | None,
    on_restore_file: Callable[[], None] | None,
    on_activity: Callable[[], None] | None,
    on_logout: Callable[[], None] | None,
) -> None:
    sidebar = ctk.CTkFrame(parent, width=SIDEBAR_WIDTH, corner_radius=0, fg_color=SURFACE)
    sidebar.grid(row=0, column=0, sticky="nsew")
    sidebar.grid_propagate(False)
    sidebar.grid_columnconfigure(0, weight=1)
    sidebar.grid_rowconfigure(1, weight=1)

    brand = ctk.CTkFrame(sidebar, fg_color="transparent")
    brand.grid(row=0, column=0, sticky="ew", padx=24, pady=(28, 20))
    brand.grid_columnconfigure(1, weight=1)
    logo = ctk.CTkFrame(brand, width=34, height=34, corner_radius=5, fg_color=TEAL)
    logo.grid(row=0, column=0, rowspan=2, sticky="w", padx=(0, 12))
    logo.grid_propagate(False)
    ctk.CTkLabel(logo, text="RL", text_color=TEAL_DARK, font=ctk.CTkFont(size=12, weight="bold", family="Consolas")).place(relx=0.5, rely=0.5, anchor="center")
    ctk.CTkLabel(brand, text="RiffLock", text_color=TEAL, font=ctk.CTkFont(size=24, weight="bold"), anchor="w").grid(row=0, column=1, sticky="w")
    ctk.CTkLabel(brand, text="LOCAL-FIRST ENCRYPTION", text_color=TEXT_MUTED, font=ctk.CTkFont(size=10, weight="bold", family="Consolas"), anchor="w").grid(row=1, column=1, sticky="w", pady=(3, 0))

    nav = ctk.CTkFrame(sidebar, fg_color="transparent")
    nav.grid(row=1, column=0, sticky="new", pady=(8, 0))
    nav.grid_columnconfigure(0, weight=1)
    _nav_button(ctk, nav, "Dashboard", row=0, command=on_dashboard)
    _nav_button(ctk, nav, "Protect", row=1, command=on_protect_file)
    _nav_button(ctk, nav, "Restore", row=2, command=on_restore_file)
    _nav_button(ctk, nav, "Riff 2FA", row=3, command=None)
    _nav_button(ctk, nav, "Activity", row=4, command=on_activity)
    _nav_button(ctk, nav, "Settings", row=5, active=True)

    session = ctk.CTkFrame(sidebar, fg_color=SURFACE_LOW, border_width=1, border_color=OUTLINE, corner_radius=0)
    session.grid(row=2, column=0, sticky="sew")
    session.grid_columnconfigure(0, weight=1)
    ctk.CTkLabel(session, text=owner_email, text_color=TEXT, font=ctk.CTkFont(size=11, family="Consolas"), anchor="w").grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 4))
    ctk.CTkLabel(session, text="UNLOCKED LOCALLY", text_color=TEAL, font=ctk.CTkFont(size=10, weight="bold", family="Consolas"), anchor="w").grid(row=1, column=0, sticky="ew", padx=24, pady=(0, 14))
    ctk.CTkButton(session, text="Logout", height=30, corner_radius=4, fg_color="transparent", hover_color=ERROR_BG, text_color=TEXT_MUTED, font=ctk.CTkFont(size=11, family="Consolas"), command=on_logout or (lambda: None)).grid(row=2, column=0, sticky="ew", padx=24, pady=(0, 20))


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


def _build_topbar(ctk, parent, *, state: SettingsState, on_back: Callable[[], None]) -> None:
    topbar = ctk.CTkFrame(parent, height=64, corner_radius=0, fg_color=SURFACE_LOW, border_width=1, border_color=OUTLINE)
    topbar.grid(row=0, column=0, sticky="ew")
    topbar.grid_propagate(False)
    topbar.grid_columnconfigure(0, weight=1)
    left = ctk.CTkFrame(topbar, fg_color="transparent")
    left.grid(row=0, column=0, sticky="w", padx=24)
    ctk.CTkLabel(left, text="System Configuration", text_color=TEXT, font=ctk.CTkFont(size=18, weight="bold")).pack(side="left")
    ctk.CTkLabel(left, text="/", text_color=OUTLINE, font=ctk.CTkFont(size=16)).pack(side="left", padx=10)
    ctk.CTkLabel(left, text="LOCAL ENGINE: OPTIMAL", text_color=TEAL, font=ctk.CTkFont(size=11, weight="bold", family="Consolas")).pack(side="left")
    right = ctk.CTkFrame(topbar, fg_color="transparent")
    right.grid(row=0, column=1, sticky="e", padx=24)
    _top_pill(ctk, right, "2FA ACTIVE" if state.riff_2fa_enabled else "2FA OPTIONAL", TEAL if state.riff_2fa_enabled else AMBER).pack(side="left", padx=(0, 10))
    ctk.CTkButton(right, text="Back", height=30, width=86, corner_radius=4, fg_color="transparent", hover_color=SURFACE_HIGHEST, border_width=1, border_color=OUTLINE, text_color=TEXT, font=ctk.CTkFont(size=11, family="Consolas"), command=on_back).pack(side="left")


def _top_pill(ctk, parent, label: str, color: str):
    pill = ctk.CTkFrame(parent, fg_color=SURFACE_LOWEST, border_width=1, border_color=OUTLINE, corner_radius=4)
    ctk.CTkLabel(pill, text=label, text_color=color, font=ctk.CTkFont(size=11, weight="bold", family="Consolas")).pack(side="left", padx=10, pady=5)
    return pill


def _build_settings_content(
    ctk,
    parent,
    *,
    state: SettingsState,
    on_change_password: Callable[[], None],
    on_start_riff_enrollment: Callable[[], None],
    on_disable_riff_2fa: Callable[[], None],
    on_open_app_data_folder: Callable[[], None],
):
    _section_title(ctk, parent, row=0, title="Account", marker="ACCOUNT")
    _build_account_card(ctk, parent, row=1, state=state, on_change_password=on_change_password)

    _section_title(ctk, parent, row=2, title="Riff 2FA", marker="RIFF")
    threshold_entry = _build_riff_card(
        ctk,
        parent,
        row=3,
        state=state,
        on_start_riff_enrollment=on_start_riff_enrollment,
        on_disable_riff_2fa=on_disable_riff_2fa,
    )

    _section_title(ctk, parent, row=4, title="Recording Prefs", marker="MIC")
    duration_entry = _build_recording_card(ctk, parent, row=5, state=state)

    _section_title(ctk, parent, row=6, title="Local App Data", marker="DATA")
    _build_local_data_card(ctk, parent, row=7, state=state, on_open_app_data_folder=on_open_app_data_folder)

    _build_recovery_warning(ctk, parent, row=8)
    return {"duration": duration_entry, "threshold": threshold_entry}


def _section_title(ctk, parent, *, row: int, title: str, marker: str) -> None:
    section = ctk.CTkFrame(parent, fg_color="transparent")
    section.grid(row=row, column=0, sticky="ew", pady=(10 if row == 0 else 28, 10))
    section.grid_columnconfigure(1, weight=1)
    ctk.CTkLabel(section, text=marker, text_color=TEAL, font=ctk.CTkFont(size=11, weight="bold", family="Consolas")).grid(row=0, column=0, sticky="w", padx=(0, 10))
    ctk.CTkLabel(section, text=title, text_color=TEXT, font=ctk.CTkFont(size=24, weight="bold"), anchor="w").grid(row=0, column=1, sticky="ew")
    ctk.CTkFrame(section, height=1, fg_color=OUTLINE).grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))


def _build_account_card(ctk, parent, *, row: int, state: SettingsState, on_change_password: Callable[[], None]) -> None:
    card = _card(ctk, parent, row)
    _setting_action_row(
        ctk,
        card,
        row=0,
        title="Security Credentials",
        body="Update your master encryption password. This cannot be recovered if lost.",
        action_label="Change Password",
        command=on_change_password,
    )
    _divider(ctk, card, row=1)
    _info_row(ctk, card, row=2, title="Account Email", value=state.owner_email, note="Owner identity stored only in the local database.")
    _divider(ctk, card, row=3)
    _disabled_select_row(ctk, card, row=4, title="Session Persistence", value="Current session only", note="Automatic idle locking is planned but not available in this build.")


def _build_riff_card(
    ctk,
    parent,
    *,
    row: int,
    state: SettingsState,
    on_start_riff_enrollment: Callable[[], None],
    on_disable_riff_2fa: Callable[[], None],
):
    card = _card(ctk, parent, row)
    card.grid_columnconfigure(0, weight=1)

    header = ctk.CTkFrame(card, fg_color="transparent")
    header.grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 14))
    header.grid_columnconfigure(0, weight=1)
    ctk.CTkLabel(header, text="Acoustic Identity Verification", text_color=TEXT, font=ctk.CTkFont(size=18, weight="bold"), anchor="w").grid(row=0, column=0, sticky="ew")
    ctk.CTkLabel(header, text="Enable two-factor authentication via audio patterns. Matching and templates stay local.", text_color=TEXT_MUTED, font=ctk.CTkFont(size=12), anchor="w", wraplength=560).grid(row=1, column=0, sticky="ew", pady=(4, 0))
    _status_toggle(ctk, header, enabled=state.riff_2fa_enabled).grid(row=0, column=1, rowspan=2, sticky="e", padx=(16, 0))

    actions = ctk.CTkFrame(card, fg_color="transparent")
    actions.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 18))
    ctk.CTkButton(actions, text="Start Riff Enrollment", height=34, corner_radius=4, fg_color=TEAL, hover_color="#63F7FF", text_color=TEAL_DARK, font=ctk.CTkFont(size=12, weight="bold"), command=on_start_riff_enrollment).pack(side="left")
    ctk.CTkButton(actions, text="Disable Riff 2FA", height=34, corner_radius=4, fg_color=ERROR_BG, hover_color="#3A1620", text_color=ERROR, border_width=1, border_color="#5B2430", font=ctk.CTkFont(size=12, weight="bold"), command=on_disable_riff_2fa).pack(side="left", padx=(10, 0))

    _divider(ctk, card, row=2)
    settings = ctk.CTkFrame(card, fg_color="transparent")
    settings.grid(row=3, column=0, sticky="ew", padx=18, pady=(14, 18))
    settings.grid_columnconfigure(0, weight=1)
    settings.grid_columnconfigure(1, weight=1)
    threshold_entry = _number_input_block(
        ctk,
        settings,
        row=0,
        column=0,
        title="Similarity Threshold",
        value=f"{state.similarity_threshold:.2f}",
        suffix="score",
        note="Higher values require more precise playback accuracy.",
    )
    _disabled_value_block(
        ctk,
        settings,
        row=0,
        column=1,
        title="Auth Duration",
        value="Current session",
        note="Re-challenge timing is tied to the local login session in this build.",
    )
    return threshold_entry


def _build_recording_card(ctk, parent, *, row: int, state: SettingsState):
    card = _card(ctk, parent, row)
    grid = ctk.CTkFrame(card, fg_color="transparent")
    grid.grid(row=0, column=0, sticky="ew", padx=18, pady=18)
    grid.grid_columnconfigure(0, weight=1)
    grid.grid_columnconfigure(1, weight=1)
    duration_entry = _number_input_block(
        ctk,
        grid,
        row=0,
        column=0,
        title="Max Capture Duration",
        value=str(state.recording_duration_seconds),
        suffix="Seconds",
        note="Limits the length of Riff enrollment and verification recordings.",
    )
    _disabled_value_block(
        ctk,
        grid,
        row=0,
        column=1,
        title="Silence Threshold",
        value="Auto",
        note="Silence detection is managed by the local feature extraction engine.",
    )
    return duration_entry


def _build_local_data_card(ctk, parent, *, row: int, state: SettingsState, on_open_app_data_folder: Callable[[], None]) -> None:
    card = _card(ctk, parent, row)
    _path_row(ctk, card, row=0, label="App Data Path", path=str(state.app_data_path), action="Open Folder", command=on_open_app_data_folder)
    _divider(ctk, card, row=1)
    _path_row(ctk, card, row=2, label="Vault Storage Path", path=str(Path(state.app_data_path) / "vault"), action="Open App Data", command=on_open_app_data_folder)
    _divider(ctk, card, row=3)
    _disabled_select_row(ctk, card, row=4, title="Temporary Cache", value="Managed automatically", note="Manual cache clearing is not exposed yet.")


def _build_recovery_warning(ctk, parent, *, row: int) -> None:
    card = ctk.CTkFrame(parent, fg_color=ERROR_BG, border_width=1, border_color="#5B2430", corner_radius=8)
    card.grid(row=row, column=0, sticky="ew", pady=(30, 0))
    card.grid_columnconfigure(0, weight=1)
    ctk.CTkLabel(card, text=PASSWORD_LOSS_WARNING_TITLE.upper(), text_color=ERROR, font=ctk.CTkFont(size=22, weight="bold"), anchor="w").grid(row=0, column=0, sticky="ew", padx=22, pady=(22, 8))
    ctk.CTkLabel(card, text=PASSWORD_LOSS_WARNING_TEXT, text_color="#FFDAD6", font=ctk.CTkFont(size=13), anchor="w", justify="left", wraplength=780).grid(row=1, column=0, sticky="ew", padx=22, pady=(0, 16))
    disabled = ctk.CTkFrame(card, fg_color="transparent")
    disabled.grid(row=2, column=0, sticky="ew", padx=22, pady=(0, 22))
    ctk.CTkButton(disabled, text="Recovery Export Not Available", height=34, corner_radius=4, fg_color="transparent", hover_color=ERROR_BG, border_width=1, border_color="#5B2430", text_color=ERROR, state="disabled").pack(side="left")


def _build_footer(ctk, parent, *, on_save: Callable[[], None]) -> None:
    footer = ctk.CTkFrame(parent, fg_color="transparent")
    footer.grid(row=9, column=0, sticky="ew", pady=(24, 26))
    footer.grid_columnconfigure(0, weight=1)
    ctk.CTkLabel(footer, text="Changes are saved to the local RiffLock database.", text_color=TEXT_MUTED, font=ctk.CTkFont(size=12), anchor="e").grid(row=0, column=0, sticky="e", padx=(0, 14))
    ctk.CTkButton(footer, text="Save All Changes", height=42, width=170, corner_radius=4, fg_color=TEAL, hover_color="#63F7FF", text_color=TEAL_DARK, font=ctk.CTkFont(size=13, weight="bold"), command=on_save).grid(row=0, column=1, sticky="e")


def _card(ctk, parent, row: int):
    card = ctk.CTkFrame(parent, fg_color=SURFACE_CONTAINER, border_width=1, border_color=OUTLINE, corner_radius=8)
    card.grid(row=row, column=0, sticky="ew")
    card.grid_columnconfigure(0, weight=1)
    return card


def _divider(ctk, parent, *, row: int) -> None:
    ctk.CTkFrame(parent, height=1, fg_color=OUTLINE).grid(row=row, column=0, sticky="ew", padx=18)


def _setting_action_row(ctk, parent, *, row: int, title: str, body: str, action_label: str, command: Callable[[], None]) -> None:
    frame = ctk.CTkFrame(parent, fg_color="transparent")
    frame.grid(row=row, column=0, sticky="ew", padx=18, pady=18)
    frame.grid_columnconfigure(0, weight=1)
    ctk.CTkLabel(frame, text=title, text_color=TEXT, font=ctk.CTkFont(size=16, weight="bold"), anchor="w").grid(row=0, column=0, sticky="ew")
    ctk.CTkLabel(frame, text=body, text_color=TEXT_MUTED, font=ctk.CTkFont(size=12), anchor="w", wraplength=560).grid(row=1, column=0, sticky="ew", pady=(4, 0))
    ctk.CTkButton(frame, text=action_label, height=34, corner_radius=4, fg_color=SURFACE_HIGHEST, hover_color=SURFACE_HIGH, border_width=1, border_color=OUTLINE, text_color=TEXT, font=ctk.CTkFont(size=12, weight="bold"), command=command).grid(row=0, column=1, rowspan=2, sticky="e", padx=(16, 0))


def _info_row(ctk, parent, *, row: int, title: str, value: str, note: str) -> None:
    frame = ctk.CTkFrame(parent, fg_color="transparent")
    frame.grid(row=row, column=0, sticky="ew", padx=18, pady=16)
    frame.grid_columnconfigure(0, weight=1)
    ctk.CTkLabel(frame, text=title, text_color=TEXT, font=ctk.CTkFont(size=15, weight="bold"), anchor="w").grid(row=0, column=0, sticky="ew")
    ctk.CTkLabel(frame, text=note, text_color=TEXT_MUTED, font=ctk.CTkFont(size=12), anchor="w").grid(row=1, column=0, sticky="ew", pady=(3, 0))
    ctk.CTkLabel(frame, text=value, text_color=TEAL, font=ctk.CTkFont(size=12, family="Consolas"), anchor="e").grid(row=0, column=1, rowspan=2, sticky="e", padx=(16, 0))


def _disabled_select_row(ctk, parent, *, row: int, title: str, value: str, note: str) -> None:
    frame = ctk.CTkFrame(parent, fg_color="transparent")
    frame.grid(row=row, column=0, sticky="ew", padx=18, pady=16)
    frame.grid_columnconfigure(0, weight=1)
    ctk.CTkLabel(frame, text=title, text_color=TEXT, font=ctk.CTkFont(size=15, weight="bold"), anchor="w").grid(row=0, column=0, sticky="ew")
    ctk.CTkLabel(frame, text=note, text_color=TEXT_MUTED, font=ctk.CTkFont(size=12), anchor="w").grid(row=1, column=0, sticky="ew", pady=(3, 0))
    ctk.CTkLabel(frame, text=value, text_color=TEXT_MUTED, fg_color=SURFACE_LOWEST, corner_radius=4, font=ctk.CTkFont(size=11, family="Consolas")).grid(row=0, column=1, rowspan=2, sticky="e", padx=(16, 0), ipadx=12, ipady=7)


def _number_input_block(ctk, parent, *, row: int, column: int, title: str, value: str, suffix: str, note: str):
    block = ctk.CTkFrame(parent, fg_color="transparent")
    block.grid(row=row, column=column, sticky="nsew", padx=(0 if column == 0 else 18, 18 if column == 0 else 0))
    block.grid_columnconfigure(0, weight=1)
    ctk.CTkLabel(block, text=title.upper(), text_color=TEXT_MUTED, font=ctk.CTkFont(size=10, weight="bold", family="Consolas"), anchor="w").grid(row=0, column=0, columnspan=2, sticky="ew")
    entry = ctk.CTkEntry(block, width=115, height=34, corner_radius=4, fg_color=SURFACE_LOWEST, border_color=OUTLINE, text_color=TEXT, font=ctk.CTkFont(size=12, family="Consolas"))
    entry.insert(0, value)
    entry.grid(row=1, column=0, sticky="w", pady=(8, 6))
    ctk.CTkLabel(block, text=suffix, text_color=TEXT_MUTED, font=ctk.CTkFont(size=12), anchor="w").grid(row=1, column=1, sticky="w", padx=(8, 0), pady=(8, 6))
    ctk.CTkLabel(block, text=note, text_color=TEXT_MUTED, font=ctk.CTkFont(size=11), anchor="w", justify="left", wraplength=330).grid(row=2, column=0, columnspan=2, sticky="ew")
    return entry


def _disabled_value_block(ctk, parent, *, row: int, column: int, title: str, value: str, note: str) -> None:
    block = ctk.CTkFrame(parent, fg_color="transparent")
    block.grid(row=row, column=column, sticky="nsew", padx=(0 if column == 0 else 18, 18 if column == 0 else 0))
    block.grid_columnconfigure(0, weight=1)
    ctk.CTkLabel(block, text=title.upper(), text_color=TEXT_MUTED, font=ctk.CTkFont(size=10, weight="bold", family="Consolas"), anchor="w").grid(row=0, column=0, sticky="ew")
    ctk.CTkLabel(block, text=value, text_color=TEXT_MUTED, fg_color=SURFACE_LOWEST, corner_radius=4, font=ctk.CTkFont(size=12, family="Consolas")).grid(row=1, column=0, sticky="w", pady=(8, 6), ipadx=12, ipady=8)
    ctk.CTkLabel(block, text=note, text_color=TEXT_MUTED, font=ctk.CTkFont(size=11), anchor="w", justify="left", wraplength=330).grid(row=2, column=0, sticky="ew")


def _status_toggle(ctk, parent, *, enabled: bool):
    frame = ctk.CTkFrame(parent, width=56, height=28, corner_radius=14, fg_color=TEAL if enabled else SURFACE_HIGHEST, border_width=1, border_color=TEAL if enabled else OUTLINE)
    frame.grid_propagate(False)
    knob_x = 0.74 if enabled else 0.26
    ctk.CTkFrame(frame, width=20, height=20, corner_radius=10, fg_color=TEAL_DARK if enabled else TEXT_MUTED).place(relx=knob_x, rely=0.5, anchor="center")
    return frame


def _path_row(ctk, parent, *, row: int, label: str, path: str, action: str, command: Callable[[], None]) -> None:
    frame = ctk.CTkFrame(parent, fg_color="transparent")
    frame.grid(row=row, column=0, sticky="ew", padx=18, pady=16)
    frame.grid_columnconfigure(0, weight=1)
    ctk.CTkLabel(frame, text=label.upper(), text_color=TEXT_MUTED, font=ctk.CTkFont(size=10, weight="bold", family="Consolas"), anchor="w").grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))
    path_label = ctk.CTkLabel(frame, text=path, text_color=TEXT_MUTED, fg_color=SURFACE_LOWEST, corner_radius=4, font=ctk.CTkFont(size=11, family="Consolas"), anchor="w")
    path_label.grid(row=1, column=0, sticky="ew", padx=(0, 10), ipadx=12, ipady=8)
    ctk.CTkButton(frame, text=action, height=34, corner_radius=4, fg_color=SURFACE_HIGHEST, hover_color=SURFACE_HIGH, border_width=1, border_color=OUTLINE, text_color=TEXT, font=ctk.CTkFont(size=12, weight="bold"), command=command).grid(row=1, column=1, sticky="e")
