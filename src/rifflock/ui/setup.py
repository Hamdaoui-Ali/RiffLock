"""Owner setup screen UI helpers."""

from __future__ import annotations

from typing import Callable

from rifflock.ui.copy import (
    PASSWORD_LOSS_ACKNOWLEDGEMENT_TEXT,
    PASSWORD_LOSS_WARNING_TITLE,
)

BACKGROUND = "#051424"
SURFACE_LOW = "#0D1C2D"
SURFACE_HIGHEST = "#273647"
TEXT = "#D4E4FA"
TEXT_MUTED = "#C4C7C7"
OUTLINE = "#444748"
TEAL = "#00DCE5"
TEAL_DARK = "#003739"
AMBER = "#FFB77D"
AMBER_DARK = "#4D2600"
ERROR = "#FFB4AB"


def build_setup_screen(
    app,
    ctk,
    *,
    on_submit: Callable[[str, str, str, bool], None],
) -> None:
    """Render the first-run owner setup screen."""

    app.geometry("900x720")
    app.minsize(760, 620)

    container = ctk.CTkFrame(app, corner_radius=0, fg_color=BACKGROUND)
    container.pack(fill="both", expand=True)

    ambient_top = ctk.CTkFrame(container, height=3, corner_radius=0, fg_color=TEAL)
    ambient_top.pack(fill="x", side="top")

    content = ctk.CTkFrame(container, fg_color="transparent")
    content.pack(fill="both", expand=True, padx=28, pady=24)
    content.grid_columnconfigure(0, weight=1)
    content.grid_rowconfigure(0, weight=1)

    auth_card = ctk.CTkFrame(
        content,
        corner_radius=8,
        fg_color=SURFACE_LOW,
        border_width=1,
        border_color=OUTLINE,
    )
    auth_card.grid(row=0, column=0, sticky="")
    auth_card.grid_columnconfigure(0, weight=1)

    form_body = ctk.CTkFrame(auth_card, width=480, fg_color="transparent")
    form_body.grid(row=0, column=0, sticky="nsew", padx=34, pady=32)
    form_body.grid_columnconfigure(0, weight=1)

    _build_brand_header(ctk, form_body)

    email_entry = _entry_row(
        ctk,
        form_body,
        "Email Address",
        "owner@riff.lock",
        icon_text="@",
        row=3,
    )
    password_entry = _entry_row(
        ctk,
        form_body,
        "Master Password",
        "Minimum 12 characters",
        icon_text="*",
        row=4,
        show="*",
    )
    strength_label, strength_bars = _build_strength_meter(ctk, form_body, row=5)
    password_confirmation_entry = _entry_row(
        ctk,
        form_body,
        "Confirm Password",
        "Repeat your master password",
        icon_text="ok",
        row=6,
        show="*",
    )

    acknowledged = ctk.BooleanVar(value=False)
    _build_recovery_warning(ctk, form_body, acknowledged, row=7)

    create_button = ctk.CTkButton(
        form_body,
        text="Create Account  ->",
        height=46,
        corner_radius=4,
        fg_color=TEAL,
        hover_color="#63F7FF",
        text_color=TEAL_DARK,
        font=ctk.CTkFont(size=15, weight="bold"),
        command=lambda: on_submit(
            email_entry.get(),
            password_entry.get(),
            password_confirmation_entry.get(),
            bool(acknowledged.get()),
        ),
    )
    create_button.grid(row=8, column=0, sticky="ew", pady=(24, 0))

    trust_note = ctk.CTkLabel(
        form_body,
        text="Zero-knowledge local encryption active",
        text_color=TEXT_MUTED,
        font=ctk.CTkFont(size=11, family="Consolas"),
    )
    trust_note.grid(row=9, column=0, sticky="ew", pady=(12, 0))

    footer = ctk.CTkFrame(content, fg_color="transparent")
    footer.grid(row=1, column=0, sticky="ew", pady=(18, 0))
    footer.grid_columnconfigure(0, weight=1)
    footer.grid_columnconfigure(1, weight=1)

    version = ctk.CTkLabel(
        footer,
        text="RIFFLOCK LOCAL MVP",
        text_color="#6F7D8B",
        font=ctk.CTkFont(size=11, family="Consolas"),
    )
    version.grid(row=0, column=0, sticky="w")

    policy = ctk.CTkLabel(
        footer,
        text="Security-first local policy",
        text_color="#6F7D8B",
        font=ctk.CTkFont(size=11, family="Consolas"),
    )
    policy.grid(row=0, column=1, sticky="e")

    def update_strength(_event=None) -> None:
        strength = _password_strength(password_entry.get())
        labels = ["Empty", "Weak", "Moderate", "Strong", "Fortified"]
        strength_label.configure(
            text=f"{labels[strength]} password",
            text_color=TEAL if strength >= 3 else TEXT_MUTED,
        )
        for index, bar in enumerate(strength_bars):
            if index >= strength:
                bar.configure(fg_color=SURFACE_HIGHEST)
            elif strength == 1:
                bar.configure(fg_color=ERROR)
            elif strength == 2:
                bar.configure(fg_color=AMBER)
            else:
                bar.configure(fg_color=TEAL)

    password_entry.bind("<KeyRelease>", update_strength)
    update_strength()


def _build_brand_header(ctk, parent) -> None:
    header = ctk.CTkFrame(parent, fg_color="transparent")
    header.grid(row=0, column=0, sticky="ew", pady=(0, 24))
    header.grid_columnconfigure(1, weight=1)

    logo = ctk.CTkFrame(
        header,
        width=42,
        height=42,
        corner_radius=6,
        fg_color="#001516",
        border_width=1,
        border_color="#004F53",
    )
    logo.grid(row=0, column=0, rowspan=2, sticky="nw", padx=(0, 12))
    logo.grid_propagate(False)

    logo_text = ctk.CTkLabel(
        logo,
        text="RL",
        text_color=TEAL,
        font=ctk.CTkFont(size=14, weight="bold", family="Consolas"),
    )
    logo_text.place(relx=0.5, rely=0.5, anchor="center")

    brand = ctk.CTkLabel(
        header,
        text="RiffLock",
        text_color=TEXT,
        font=ctk.CTkFont(size=22, weight="bold"),
    )
    brand.grid(row=0, column=1, sticky="w")

    eyebrow = ctk.CTkLabel(
        header,
        text="LOCAL ENCRYPTION VAULT",
        text_color=TEAL,
        font=ctk.CTkFont(size=11, weight="bold", family="Consolas"),
    )
    eyebrow.grid(row=1, column=1, sticky="w", pady=(2, 0))

    title = ctk.CTkLabel(
        parent,
        text="Create Owner Account",
        text_color=TEXT,
        font=ctk.CTkFont(size=30, weight="bold"),
        anchor="w",
    )
    title.grid(row=1, column=0, sticky="w")

    subtitle = ctk.CTkLabel(
        parent,
        text="Set up the single local RiffLock owner account on this device.",
        text_color=TEXT_MUTED,
        font=ctk.CTkFont(size=14),
        anchor="w",
        justify="left",
        wraplength=410,
    )
    subtitle.grid(row=2, column=0, sticky="w", pady=(6, 24))


def _entry_row(
    ctk,
    parent,
    label: str,
    placeholder: str,
    *,
    icon_text: str,
    row: int,
    show: str | None = None,
):
    group = ctk.CTkFrame(parent, fg_color="transparent")
    group.grid(row=row, column=0, sticky="ew", pady=(0, 16))
    group.grid_columnconfigure(0, weight=1)

    label_widget = ctk.CTkLabel(
        group,
        text=label.upper(),
        text_color=TEXT_MUTED,
        font=ctk.CTkFont(size=11, weight="bold"),
        anchor="w",
    )
    label_widget.grid(row=0, column=0, sticky="w", pady=(0, 7))

    input_frame = ctk.CTkFrame(
        group,
        height=46,
        corner_radius=4,
        fg_color="#010F1F",
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
        text_color=TEXT_MUTED,
        font=ctk.CTkFont(size=12, weight="bold", family="Consolas"),
    )
    icon.grid(row=0, column=0, sticky="ns")

    entry = ctk.CTkEntry(
        input_frame,
        height=42,
        border_width=0,
        corner_radius=0,
        fg_color="#010F1F",
        text_color=TEXT,
        placeholder_text=placeholder,
        placeholder_text_color="#708093",
        show=show or "",
        font=ctk.CTkFont(size=14),
    )
    entry.grid(row=0, column=1, sticky="ew", padx=(0, 10), pady=1)
    return entry


def _build_strength_meter(ctk, parent, *, row: int):
    meter = ctk.CTkFrame(parent, fg_color="transparent")
    meter.grid(row=row, column=0, sticky="ew", pady=(-7, 16))
    for column in range(4):
        meter.grid_columnconfigure(column, weight=1, uniform="strength")

    bars = []
    for index in range(4):
        bar = ctk.CTkFrame(
            meter,
            height=4,
            corner_radius=0,
            fg_color=SURFACE_HIGHEST,
        )
        bar.grid(row=0, column=index, sticky="ew", padx=(0 if index == 0 else 2, 0))
        bars.append(bar)

    label = ctk.CTkLabel(
        meter,
        text="Password strength",
        text_color=TEXT_MUTED,
        font=ctk.CTkFont(size=11, family="Consolas"),
        anchor="w",
    )
    label.grid(row=1, column=0, columnspan=2, sticky="w", pady=(6, 0))

    requirement = ctk.CTkLabel(
        meter,
        text="Min. 12 chars + upper/lower/digit/symbol",
        text_color=TEXT_MUTED,
        font=ctk.CTkFont(size=11, family="Consolas"),
        anchor="e",
    )
    requirement.grid(row=1, column=2, columnspan=2, sticky="e", pady=(6, 0))

    return label, tuple(bars)


def _build_recovery_warning(ctk, parent, acknowledged, *, row: int) -> None:
    warning = ctk.CTkFrame(
        parent,
        corner_radius=4,
        fg_color="#211C12",
        border_width=1,
        border_color=AMBER_DARK,
    )
    warning.grid(row=row, column=0, sticky="ew", pady=(4, 0))
    warning.grid_columnconfigure(2, weight=1)

    accent = ctk.CTkFrame(warning, width=4, corner_radius=0, fg_color=AMBER)
    accent.grid(row=0, column=0, rowspan=3, sticky="nsw")

    icon = ctk.CTkLabel(
        warning,
        text="!",
        width=28,
        text_color=AMBER,
        font=ctk.CTkFont(size=20, weight="bold", family="Consolas"),
    )
    icon.grid(row=0, column=1, sticky="nw", padx=(14, 8), pady=(14, 0))

    title = ctk.CTkLabel(
        warning,
        text=PASSWORD_LOSS_WARNING_TITLE,
        text_color=AMBER,
        font=ctk.CTkFont(size=17, weight="bold"),
        anchor="w",
    )
    title.grid(row=0, column=2, sticky="ew", padx=(0, 14), pady=(14, 4))

    body = ctk.CTkLabel(
        warning,
        text=(
            "RiffLock is a local-first encryption system. We do not store your "
            "master password. If it is lost, protected files may be unrecoverable. "
            "There is no password reset process."
        ),
        text_color=TEXT_MUTED,
        font=ctk.CTkFont(size=12),
        anchor="w",
        justify="left",
        wraplength=360,
    )
    body.grid(row=1, column=1, columnspan=2, sticky="ew", padx=(14, 14), pady=(0, 12))

    acknowledgement = ctk.CTkCheckBox(
        warning,
        text=PASSWORD_LOSS_ACKNOWLEDGEMENT_TEXT,
        variable=acknowledged,
        onvalue=True,
        offvalue=False,
        checkbox_width=18,
        checkbox_height=18,
        border_width=1,
        corner_radius=3,
        fg_color=TEAL,
        hover_color="#63F7FF",
        border_color=OUTLINE,
        text_color=TEXT,
        font=ctk.CTkFont(size=12),
    )
    acknowledgement.grid(
        row=2,
        column=1,
        columnspan=2,
        sticky="ew",
        padx=(14, 14),
        pady=(0, 14),
    )


def _password_strength(password: str) -> int:
    if not password:
        return 0

    strength = 1
    if len(password) >= 8:
        strength = 2
    if (
        len(password) >= 12
        and any(character.islower() for character in password)
        and any(character.isupper() for character in password)
        and any(character.isdigit() for character in password)
    ):
        strength = 3
    if strength == 3 and any(not character.isalnum() for character in password):
        strength = 4
    return strength


