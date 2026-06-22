"""Settings screen UI helpers."""

from __future__ import annotations

from typing import Callable

from rifflock.settings import SettingsState
from rifflock.ui.copy import PASSWORD_LOSS_WARNING_TEXT, PASSWORD_LOSS_WARNING_TITLE


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
) -> None:
    """Render the owner settings screen."""

    container = ctk.CTkFrame(app, corner_radius=0, fg_color="transparent")
    container.pack(fill="both", expand=True, padx=20, pady=20)

    header = ctk.CTkFrame(container, fg_color="transparent")
    header.pack(fill="x")

    title = ctk.CTkLabel(
        header,
        text="Settings",
        font=ctk.CTkFont(size=28, weight="bold"),
    )
    title.pack(side="left")

    back_button = ctk.CTkButton(
        header,
        text="Back",
        width=100,
        command=on_back,
    )
    back_button.pack(side="right")

    account_card = ctk.CTkFrame(container)
    account_card.pack(fill="x", pady=(20, 12))

    _row(ctk, account_card, "Account email", state.owner_email)
    _row(ctk, account_card, "Riff 2FA", "Enabled" if state.riff_2fa_enabled else "Disabled")

    actions = ctk.CTkFrame(account_card, fg_color="transparent")
    actions.pack(fill="x", padx=16, pady=(0, 16))

    change_password_button = ctk.CTkButton(
        actions,
        text="Change Password",
        command=on_change_password,
    )
    change_password_button.pack(side="left")

    enroll_button = ctk.CTkButton(
        actions,
        text="Start Riff Enrollment",
        command=on_start_riff_enrollment,
    )
    enroll_button.pack(side="left", padx=(12, 0))

    disable_button = ctk.CTkButton(
        actions,
        text="Disable Riff 2FA",
        fg_color="#8B1E3F",
        hover_color="#6D1731",
        command=on_disable_riff_2fa,
    )
    disable_button.pack(side="left", padx=(12, 0))

    preferences_card = ctk.CTkFrame(container)
    preferences_card.pack(fill="x", pady=(0, 12))

    prefs_title = ctk.CTkLabel(
        preferences_card,
        text="Recording",
        font=ctk.CTkFont(size=18, weight="bold"),
        anchor="w",
    )
    prefs_title.pack(fill="x", padx=16, pady=(16, 8))

    duration_row = ctk.CTkFrame(preferences_card, fg_color="transparent")
    duration_row.pack(fill="x", padx=16, pady=(0, 10))

    duration_label = ctk.CTkLabel(duration_row, text="Recording duration (seconds)", anchor="w")
    duration_label.pack(side="left")

    duration_entry = ctk.CTkEntry(duration_row, width=120)
    duration_entry.insert(0, str(state.recording_duration_seconds))
    duration_entry.pack(side="right")

    advanced_card = ctk.CTkFrame(container)
    advanced_card.pack(fill="x", pady=(0, 12))

    advanced_title = ctk.CTkLabel(
        advanced_card,
        text="Advanced",
        font=ctk.CTkFont(size=18, weight="bold"),
        anchor="w",
    )
    advanced_title.pack(fill="x", padx=16, pady=(16, 8))

    threshold_row = ctk.CTkFrame(advanced_card, fg_color="transparent")
    threshold_row.pack(fill="x", padx=16, pady=(0, 10))

    threshold_label = ctk.CTkLabel(threshold_row, text="Riff similarity threshold", anchor="w")
    threshold_label.pack(side="left")

    threshold_entry = ctk.CTkEntry(threshold_row, width=120)
    threshold_entry.insert(0, f"{state.similarity_threshold:.2f}")
    threshold_entry.pack(side="right")

    recovery_card = ctk.CTkFrame(container, fg_color="#3F2B1B")
    recovery_card.pack(fill="x", pady=(0, 12))

    recovery_title = ctk.CTkLabel(
        recovery_card,
        text=PASSWORD_LOSS_WARNING_TITLE,
        font=ctk.CTkFont(size=18, weight="bold"),
        anchor="w",
    )
    recovery_title.pack(fill="x", padx=16, pady=(16, 8))

    recovery_body = ctk.CTkLabel(
        recovery_card,
        text=PASSWORD_LOSS_WARNING_TEXT,
        anchor="w",
        justify="left",
        wraplength=680,
    )
    recovery_body.pack(fill="x", padx=16, pady=(0, 16))

    footer = ctk.CTkFrame(container, fg_color="transparent")
    footer.pack(fill="x", pady=(8, 0))

    open_button = ctk.CTkButton(
        footer,
        text="Open App Data Folder",
        command=on_open_app_data_folder,
    )
    open_button.pack(side="left")

    save_button = ctk.CTkButton(
        footer,
        text="Save Settings",
        command=lambda: on_save(duration_entry.get(), threshold_entry.get()),
    )
    save_button.pack(side="right")


def _row(ctk, parent, label: str, value: str) -> None:
    row = ctk.CTkFrame(parent, fg_color="transparent")
    row.pack(fill="x", padx=16, pady=(16 if label == "Account email" else 0, 10))

    key = ctk.CTkLabel(row, text=label, anchor="w")
    key.pack(side="left")

    content = ctk.CTkLabel(row, text=value, anchor="e")
    content.pack(side="right")
