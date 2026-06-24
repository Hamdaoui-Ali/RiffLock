"""Owner login screen UI helpers."""

from __future__ import annotations

from typing import Callable

BACKGROUND = "#051424"
SURFACE_LOW = "#0D1C2D"
SURFACE = "#122131"
SURFACE_HIGH = "#1C2B3C"
SURFACE_HIGHEST = "#273647"
SURFACE_LOWEST = "#010F1F"
TEXT = "#D4E4FA"
TEXT_MUTED = "#C4C7C7"
OUTLINE = "#444748"
TEAL = "#00DCE5"
TEAL_DARK = "#003739"
AMBER = "#FFB77D"
ERROR = "#FFB4AB"
ERROR_CONTAINER = "#3A1114"


def build_login_screen(
    app,
    ctk,
    *,
    on_submit: Callable[[str, str], None],
    on_reset_attempts: Callable[[str], None],
) -> None:
    """Render the owner login screen."""

    app.geometry("900x680")
    app.minsize(760, 560)

    container = ctk.CTkFrame(app, corner_radius=0, fg_color=BACKGROUND)
    container.pack(fill="both", expand=True)

    top_line = ctk.CTkFrame(container, height=3, corner_radius=0, fg_color=TEAL)
    top_line.pack(fill="x", side="top")

    content = ctk.CTkFrame(container, fg_color="transparent")
    content.pack(fill="both", expand=True, padx=32, pady=28)
    content.grid_columnconfigure(0, weight=1)
    content.grid_columnconfigure(1, weight=0)
    content.grid_rowconfigure(0, weight=1)

    main_column = ctk.CTkFrame(content, fg_color="transparent")
    main_column.grid(row=0, column=0, sticky="nsew")
    main_column.grid_columnconfigure(0, weight=1)
    main_column.grid_rowconfigure(0, weight=1)

    auth_stack = ctk.CTkFrame(main_column, fg_color="transparent", width=420)
    auth_stack.grid(row=0, column=0, sticky="")
    auth_stack.grid_columnconfigure(0, weight=1)

    _build_brand_header(ctk, auth_stack)

    card = ctk.CTkFrame(
        auth_stack,
        corner_radius=8,
        fg_color=SURFACE_LOW,
        border_width=1,
        border_color=OUTLINE,
    )
    card.grid(row=1, column=0, sticky="ew", pady=(26, 0))
    card.grid_columnconfigure(0, weight=1)

    card_body = ctk.CTkFrame(card, fg_color="transparent")
    card_body.grid(row=0, column=0, sticky="ew", padx=28, pady=28)
    card_body.grid_columnconfigure(0, weight=1)

    email_entry = _entry_row(
        ctk,
        card_body,
        "Identity Identifier (Email)",
        "owner@riff.lock",
        icon_text="@",
        row=0,
    )

    password_entry = _entry_row(
        ctk,
        card_body,
        "Encryption Key",
        "Enter your master password",
        icon_text="*",
        row=1,
        show="*",
        trailing_action_text="Reset tries",
        trailing_action=lambda: on_reset_attempts(email_entry.get()),
    )

    unlock_button = ctk.CTkButton(
        card_body,
        text="Unlock RiffLock  ->",
        height=46,
        corner_radius=5,
        fg_color=TEAL,
        hover_color="#63F7FF",
        text_color=TEAL_DARK,
        font=ctk.CTkFont(size=15, weight="bold"),
        command=lambda: on_submit(email_entry.get(), password_entry.get()),
    )
    unlock_button.grid(row=2, column=0, sticky="ew", pady=(6, 0))

    note = ctk.CTkFrame(
        card_body,
        corner_radius=5,
        fg_color=SURFACE_LOWEST,
        border_width=1,
        border_color="#004F53",
    )
    note.grid(row=3, column=0, sticky="ew", pady=(26, 0))
    note.grid_columnconfigure(1, weight=1)

    note_icon = ctk.CTkLabel(
        note,
        text="mem",
        width=36,
        text_color=TEAL,
        font=ctk.CTkFont(size=11, weight="bold", family="Consolas"),
    )
    note_icon.grid(row=0, column=0, sticky="ns", padx=(10, 2), pady=10)

    note_text = ctk.CTkLabel(
        note,
        text=(
            "Security note: the data key is unlocked only in memory. "
            "No persistent storage of decryption tokens."
        ),
        text_color=TEXT_MUTED,
        font=ctk.CTkFont(size=11, family="Consolas"),
        justify="left",
        anchor="w",
        wraplength=315,
    )
    note_text.grid(row=0, column=1, sticky="ew", padx=(0, 12), pady=10)

    _build_footer(ctk, auth_stack, row=2)
    _build_telemetry(ctk, content)


def _build_brand_header(ctk, parent) -> None:
    header = ctk.CTkFrame(parent, fg_color="transparent")
    header.grid(row=0, column=0, sticky="ew")
    header.grid_columnconfigure(0, weight=1)

    logo = ctk.CTkFrame(
        header,
        width=64,
        height=64,
        corner_radius=8,
        fg_color=SURFACE,
        border_width=1,
        border_color=OUTLINE,
    )
    logo.grid(row=0, column=0, sticky="", pady=(0, 20))
    logo.grid_propagate(False)

    logo_text = ctk.CTkLabel(
        logo,
        text="RL",
        text_color=TEAL,
        font=ctk.CTkFont(size=20, weight="bold", family="Consolas"),
    )
    logo_text.place(relx=0.5, rely=0.5, anchor="center")

    title = ctk.CTkLabel(
        header,
        text="Owner Login",
        text_color=TEXT,
        font=ctk.CTkFont(size=25, weight="bold"),
    )
    title.grid(row=1, column=0, sticky="", pady=(0, 6))

    subtitle = ctk.CTkLabel(
        header,
        text="RIFFLOCK LOCAL CRYPTOGRAPHIC GATEWAY",
        text_color=TEXT_MUTED,
        font=ctk.CTkFont(size=11, family="Consolas"),
    )
    subtitle.grid(row=2, column=0, sticky="")


def _entry_row(
    ctk,
    parent,
    label: str,
    placeholder: str,
    *,
    icon_text: str,
    row: int,
    show: str | None = None,
    trailing_action_text: str | None = None,
    trailing_action: Callable[[], None] | None = None,
):
    group = ctk.CTkFrame(parent, fg_color="transparent")
    group.grid(row=row, column=0, sticky="ew", pady=(0, 20))
    group.grid_columnconfigure(0, weight=1)

    header = ctk.CTkFrame(group, fg_color="transparent")
    header.grid(row=0, column=0, sticky="ew", pady=(0, 7))
    header.grid_columnconfigure(0, weight=1)

    label_widget = ctk.CTkLabel(
        header,
        text=label.upper(),
        text_color=TEXT_MUTED,
        font=ctk.CTkFont(size=11, weight="bold"),
        anchor="w",
    )
    label_widget.grid(row=0, column=0, sticky="w")

    if trailing_action_text and trailing_action:
        action = ctk.CTkButton(
            header,
            text=trailing_action_text.upper(),
            width=82,
            height=20,
            corner_radius=4,
            fg_color="transparent",
            hover_color=SURFACE_HIGHEST,
            text_color=TEAL,
            font=ctk.CTkFont(size=10, weight="bold", family="Consolas"),
            command=trailing_action,
        )
        action.grid(row=0, column=1, sticky="e")

    input_frame = ctk.CTkFrame(
        group,
        height=46,
        corner_radius=5,
        fg_color=SURFACE_LOWEST,
        border_width=1,
        border_color=OUTLINE,
    )
    input_frame.grid(row=1, column=0, sticky="ew")
    input_frame.grid_columnconfigure(1, weight=1)
    input_frame.grid_propagate(False)

    icon = ctk.CTkLabel(
        input_frame,
        text=icon_text,
        width=38,
        text_color="#8E9192",
        font=ctk.CTkFont(size=12, weight="bold", family="Consolas"),
    )
    icon.grid(row=0, column=0, sticky="ns")

    entry = ctk.CTkEntry(
        input_frame,
        height=42,
        border_width=0,
        corner_radius=0,
        fg_color=SURFACE_LOWEST,
        text_color=TEXT,
        placeholder_text=placeholder,
        placeholder_text_color="#708093",
        show=show or "",
        font=ctk.CTkFont(size=14),
    )
    entry.grid(row=0, column=1, sticky="ew", padx=(0, 10), pady=1)
    return entry


def _build_footer(ctk, parent, *, row: int) -> None:
    footer = ctk.CTkFrame(parent, fg_color="transparent")
    footer.grid(row=row, column=0, sticky="ew", pady=(38, 0))
    footer.grid_columnconfigure(0, weight=1)

    badges = ctk.CTkFrame(footer, fg_color="transparent")
    badges.grid(row=0, column=0, sticky="")

    for index, text in enumerate(("AES-256-GCM", "LOCAL-ONLY", "ZERO-KNOWLEDGE")):
        if index > 0:
            divider = ctk.CTkFrame(badges, width=1, height=22, fg_color=OUTLINE)
            divider.grid(row=0, column=index * 2 - 1, padx=12)
        badge = ctk.CTkLabel(
            badges,
            text=text,
            text_color="#7E8996",
            font=ctk.CTkFont(size=10, family="Consolas"),
        )
        badge.grid(row=0, column=index * 2)

    engine = ctk.CTkLabel(
        footer,
        text="RiffLock Encryption Engine v2.4.1",
        text_color="#687583",
        font=ctk.CTkFont(size=9, family="Consolas"),
    )
    engine.grid(row=1, column=0, sticky="", pady=(14, 0))


def _build_telemetry(ctk, parent) -> None:
    panel = ctk.CTkFrame(parent, fg_color="transparent", width=180)
    panel.grid(row=0, column=1, sticky="e", padx=(28, 0))
    panel.grid_columnconfigure(0, weight=1)

    _telemetry_item(ctk, panel, row=0, label="ENTROPY LEVEL: HIGH", value=0.68, color=TEAL)
    _telemetry_item(ctk, panel, row=1, label="SIGNAL NOISE: MINIMAL", value=0.25, color=AMBER)
    _telemetry_item(ctk, panel, row=2, label="GATEWAY STATUS: STANDBY", value=1.0, color=TEAL)


def _telemetry_item(ctk, parent, *, row: int, label: str, value: float, color: str) -> None:
    item = ctk.CTkFrame(parent, fg_color="transparent")
    item.grid(row=row, column=0, sticky="ew", pady=(0 if row == 0 else 34, 0))
    item.grid_columnconfigure(0, weight=1)

    track = ctk.CTkFrame(item, height=4, corner_radius=0, fg_color=SURFACE_HIGHEST)
    track.grid(row=0, column=0, sticky="ew")
    track.grid_columnconfigure(0, weight=max(int(value * 100), 1))
    track.grid_columnconfigure(1, weight=max(100 - int(value * 100), 1))

    fill = ctk.CTkFrame(track, height=4, corner_radius=0, fg_color=color)
    fill.grid(row=0, column=0, sticky="ew")

    label_widget = ctk.CTkLabel(
        item,
        text=label,
        text_color="#6F7D8B",
        font=ctk.CTkFont(size=10, family="Consolas"),
        anchor="w",
    )
    label_widget.grid(row=1, column=0, sticky="w", pady=(8, 0))
