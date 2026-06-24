"""Riff verification screen UI helpers."""

from __future__ import annotations

from typing import Callable

BACKGROUND = "#051424"
SURFACE = "#051424"
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
ERROR_BG = "#2A1116"
SIDEBAR_WIDTH = 260


def build_riff_verification_screen(
    app,
    ctk,
    *,
    owner_email: str,
    on_verify: Callable[[], None],
    on_reset_attempts: Callable[[], None],
    on_cancel: Callable[[], None],
    recording_duration_seconds: int | None = None,
) -> None:
    """Render the login-time riff verification screen."""

    duration_seconds = max(int(recording_duration_seconds or 5), 1)

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
        owner_email=owner_email,
        on_cancel=on_cancel,
        on_reset_attempts=on_reset_attempts,
    )

    main = ctk.CTkFrame(root, corner_radius=0, fg_color=BACKGROUND)
    main.grid(row=0, column=1, sticky="nsew")
    main.grid_columnconfigure(0, weight=1)
    main.grid_rowconfigure(1, weight=1)

    _build_topbar(ctk, main, on_cancel=on_cancel)

    content = ctk.CTkFrame(main, corner_radius=0, fg_color=BACKGROUND)
    content.grid(row=1, column=0, sticky="nsew", padx=24, pady=24)
    content.grid_columnconfigure(0, weight=1)
    content.grid_columnconfigure(1, weight=2)
    content.grid_rowconfigure(0, weight=1)

    _build_steps(ctk, content, owner_email=owner_email, duration_seconds=duration_seconds)
    _build_interaction_panel(
        ctk,
        content,
        duration_seconds=duration_seconds,
        on_verify=on_verify,
        on_reset_attempts=on_reset_attempts,
        on_cancel=on_cancel,
    )


def _build_sidebar(
    ctk,
    parent,
    *,
    owner_email: str,
    on_cancel: Callable[[], None],
    on_reset_attempts: Callable[[], None],
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

    _nav_button(ctk, nav, "Dashboard", row=0, disabled=True)
    _nav_button(ctk, nav, "Protect", row=1, disabled=True)
    _nav_button(ctk, nav, "Restore", row=2, disabled=True)
    _nav_button(ctk, nav, "Riff 2FA", row=3, active=True)
    _nav_button(ctk, nav, "Activity", row=4, disabled=True)
    _nav_button(ctk, nav, "Settings", row=5, disabled=True)

    session = ctk.CTkFrame(
        sidebar,
        fg_color=SURFACE_LOW,
        border_width=1,
        border_color=OUTLINE,
        corner_radius=0,
    )
    session.grid(row=2, column=0, sticky="sew")
    session.grid_columnconfigure(0, weight=1)

    ctk.CTkButton(
        session,
        text="Cancel Sign In",
        height=34,
        corner_radius=4,
        fg_color=TEAL,
        hover_color="#63F7FF",
        text_color=TEAL_DARK,
        font=ctk.CTkFont(size=12, weight="bold"),
        command=on_cancel,
    ).grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 12))

    ctk.CTkButton(
        session,
        text="Reset Riff Tries",
        height=30,
        corner_radius=4,
        fg_color="transparent",
        hover_color=SURFACE_HIGHEST,
        border_width=1,
        border_color=OUTLINE,
        text_color=TEXT,
        font=ctk.CTkFont(size=11, family="Consolas"),
        command=on_reset_attempts,
    ).grid(row=1, column=0, sticky="ew", padx=24, pady=(0, 14))

    ctk.CTkLabel(
        session,
        text=owner_email,
        text_color=TEXT_MUTED,
        font=ctk.CTkFont(size=11, family="Consolas"),
        anchor="w",
    ).grid(row=2, column=0, sticky="ew", padx=24, pady=(0, 8))
    ctk.CTkLabel(
        session,
        text="PASSWORD VERIFIED",
        text_color=TEAL,
        font=ctk.CTkFont(size=11, weight="bold", family="Consolas"),
        anchor="w",
    ).grid(row=3, column=0, sticky="ew", padx=24, pady=(0, 6))
    ctk.CTkLabel(
        session,
        text="RIFF REQUIRED",
        text_color=AMBER,
        font=ctk.CTkFont(size=11, weight="bold", family="Consolas"),
        anchor="w",
    ).grid(row=4, column=0, sticky="ew", padx=24, pady=(0, 20))


def _nav_button(
    ctk,
    parent,
    label: str,
    *,
    row: int,
    active: bool = False,
    disabled: bool = False,
) -> None:
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
        command=lambda: None,
        state="disabled" if disabled else "normal",
    ).grid(row=row, column=0, sticky="ew")


def _build_topbar(ctk, parent, *, on_cancel: Callable[[], None]) -> None:
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
        text="Riff Verification",
        text_color=TEXT,
        font=ctk.CTkFont(size=18, weight="bold"),
    ).pack(side="left")
    ctk.CTkLabel(left, text="/", text_color=OUTLINE, font=ctk.CTkFont(size=16)).pack(side="left", padx=10)
    ctk.CTkLabel(
        left,
        text="STAGE: 2FA_RECORDING",
        text_color=TEXT_MUTED,
        font=ctk.CTkFont(size=11, family="Consolas"),
    ).pack(side="left")

    right = ctk.CTkFrame(topbar, fg_color="transparent")
    right.grid(row=0, column=1, sticky="e", padx=24)
    _top_pill(ctk, right, "ENGINE HEALTH", TEAL).pack(side="left", padx=(0, 10))
    _top_pill(ctk, right, "VAULT: LOCKED", AMBER).pack(side="left", padx=(0, 10))
    ctk.CTkButton(
        right,
        text="Cancel",
        height=30,
        width=90,
        corner_radius=4,
        fg_color="transparent",
        hover_color=ERROR_BG,
        border_width=1,
        border_color=OUTLINE,
        text_color=TEXT,
        font=ctk.CTkFont(size=11, family="Consolas"),
        command=on_cancel,
    ).pack(side="left")


def _top_pill(ctk, parent, label: str, color: str):
    pill = ctk.CTkFrame(parent, fg_color="transparent")
    dot = ctk.CTkFrame(pill, width=8, height=8, corner_radius=4, fg_color=color)
    dot.pack(side="left", padx=(0, 6))
    ctk.CTkLabel(
        pill,
        text=label,
        text_color=TEXT_MUTED,
        font=ctk.CTkFont(size=10, weight="bold", family="Consolas"),
    ).pack(side="left")
    return pill


def _build_steps(ctk, parent, *, owner_email: str, duration_seconds: int) -> None:
    steps = ctk.CTkFrame(parent, fg_color="transparent")
    steps.grid(row=0, column=0, sticky="nsew", padx=(0, 22))
    steps.grid_columnconfigure(0, weight=1)
    steps.grid_rowconfigure(1, weight=1)

    intro = ctk.CTkFrame(steps, fg_color="transparent")
    intro.grid(row=0, column=0, sticky="ew", pady=(26, 22))
    ctk.CTkLabel(
        intro,
        text="Identity Verification",
        text_color=TEXT,
        font=ctk.CTkFont(size=24, weight="bold"),
        anchor="w",
    ).grid(row=0, column=0, sticky="ew")
    ctk.CTkLabel(
        intro,
        text=(
            "Password accepted for "
            f"{owner_email}. Play your enrolled audio riff to unlock the secure session."
        ),
        text_color=TEXT_MUTED,
        font=ctk.CTkFont(size=13),
        anchor="w",
        justify="left",
        wraplength=300,
    ).grid(row=1, column=0, sticky="ew", pady=(8, 0))

    stack = ctk.CTkFrame(steps, fg_color="transparent")
    stack.grid(row=1, column=0, sticky="new")
    stack.grid_columnconfigure(0, weight=1)

    _step_card(
        ctk,
        stack,
        row=0,
        number="01",
        title="Waiting",
        detail="Password accepted",
        color=TEXT_MUTED,
        active=False,
    )
    _step_card(
        ctk,
        stack,
        row=1,
        number="02",
        title="Recording",
        detail=f"Capturing {duration_seconds}s input",
        color=TEAL,
        active=True,
    )
    _step_card(
        ctk,
        stack,
        row=2,
        number="03",
        title="Analyzing",
        detail="Matching local fingerprint",
        color=AMBER,
        active=False,
    )
    _step_card(
        ctk,
        stack,
        row=3,
        number="04",
        title="Verified",
        detail="Dashboard access granted",
        color=TEAL,
        active=False,
    )


def _step_card(
    ctk,
    parent,
    *,
    row: int,
    number: str,
    title: str,
    detail: str,
    color: str,
    active: bool,
) -> None:
    card = ctk.CTkFrame(
        parent,
        fg_color=SURFACE_CONTAINER,
        border_width=1,
        border_color=color if active else OUTLINE,
        corner_radius=8,
    )
    card.grid(row=row, column=0, sticky="ew", pady=(0, 14))
    card.grid_columnconfigure(1, weight=1)

    marker = ctk.CTkFrame(
        card,
        width=34,
        height=34,
        corner_radius=17,
        fg_color=color if active else "transparent",
        border_width=0 if active else 2,
        border_color=OUTLINE,
    )
    marker.grid(row=0, column=0, rowspan=2, padx=(16, 12), pady=16)
    marker.grid_propagate(False)
    ctk.CTkLabel(
        marker,
        text=number,
        text_color=TEAL_DARK if active else TEXT_MUTED,
        font=ctk.CTkFont(size=10, weight="bold", family="Consolas"),
    ).place(relx=0.5, rely=0.5, anchor="center")

    ctk.CTkLabel(
        card,
        text=title,
        text_color=color if active else TEXT,
        font=ctk.CTkFont(size=14, weight="bold"),
        anchor="w",
    ).grid(row=0, column=1, sticky="ew", padx=(0, 16), pady=(14, 0))
    ctk.CTkLabel(
        card,
        text=detail,
        text_color=TEXT_MUTED,
        font=ctk.CTkFont(size=11),
        anchor="w",
    ).grid(row=1, column=1, sticky="ew", padx=(0, 16), pady=(2, 14))


def _build_interaction_panel(
    ctk,
    parent,
    *,
    duration_seconds: int,
    on_verify: Callable[[], None],
    on_reset_attempts: Callable[[], None],
    on_cancel: Callable[[], None],
) -> None:
    panel = ctk.CTkFrame(
        parent,
        fg_color=SURFACE_CONTAINER,
        border_width=1,
        border_color=OUTLINE,
        corner_radius=12,
    )
    panel.grid(row=0, column=1, sticky="nsew")
    panel.grid_columnconfigure(0, weight=1)
    panel.grid_rowconfigure(1, weight=1)

    status = ctk.CTkFrame(panel, fg_color="transparent")
    status.grid(row=0, column=0, sticky="ew", padx=28, pady=(28, 8))
    status.grid_columnconfigure(0, weight=1)
    status.grid_columnconfigure(1, weight=1)

    signal = ctk.CTkFrame(status, fg_color="transparent")
    signal.grid(row=0, column=0, sticky="w")
    ctk.CTkLabel(
        signal,
        text="SIGNAL STATUS",
        text_color=TEXT_MUTED,
        font=ctk.CTkFont(size=10, weight="bold", family="Consolas"),
        anchor="w",
    ).grid(row=0, column=0, sticky="w")
    bars = ctk.CTkFrame(signal, fg_color="transparent")
    bars.grid(row=1, column=0, sticky="w", pady=(8, 0))
    for column, height in enumerate((18, 26, 14, 22, 10)):
        _signal_bar(ctk, bars, column=column, height=height, active=column < 4)

    duration = ctk.CTkFrame(status, fg_color="transparent")
    duration.grid(row=0, column=1, sticky="e")
    ctk.CTkLabel(
        duration,
        text="DURATION",
        text_color=TEXT_MUTED,
        font=ctk.CTkFont(size=10, weight="bold", family="Consolas"),
        anchor="e",
    ).grid(row=0, column=0, sticky="e")
    ctk.CTkLabel(
        duration,
        text=_format_duration(duration_seconds),
        text_color=TEAL,
        font=ctk.CTkFont(size=22, weight="bold", family="Consolas"),
        anchor="e",
    ).grid(row=1, column=0, sticky="e", pady=(5, 0))

    recorder = ctk.CTkFrame(panel, fg_color="transparent")
    recorder.grid(row=1, column=0, sticky="nsew", padx=28, pady=10)
    recorder.grid_columnconfigure(0, weight=1)
    recorder.grid_rowconfigure(0, weight=1)

    outer_ring = ctk.CTkFrame(
        recorder,
        width=280,
        height=280,
        corner_radius=140,
        fg_color=SURFACE_HIGH,
        border_width=2,
        border_color=OUTLINE,
    )
    outer_ring.grid(row=0, column=0)
    outer_ring.grid_propagate(False)

    mid_ring = ctk.CTkFrame(
        outer_ring,
        width=236,
        height=236,
        corner_radius=118,
        fg_color=SURFACE_CONTAINER,
        border_width=2,
        border_color=TEAL,
    )
    mid_ring.place(relx=0.5, rely=0.5, anchor="center")
    mid_ring.grid_propagate(False)

    verify_button = ctk.CTkButton(
        mid_ring,
        text="MIC\nVERIFY RIFF",
        width=178,
        height=178,
        corner_radius=89,
        fg_color=SURFACE_HIGH,
        hover_color=SURFACE_HIGHEST,
        border_width=2,
        border_color=TEAL,
        text_color=TEAL,
        font=ctk.CTkFont(size=14, weight="bold", family="Consolas"),
        command=on_verify,
    )
    verify_button.place(relx=0.5, rely=0.5, anchor="center")

    hint = ctk.CTkLabel(
        recorder,
        text=(
            "Press Verify Riff, wait for the countdown, then play the same short riff "
            "used during enrollment. Matching happens locally."
        ),
        text_color=TEXT_MUTED,
        font=ctk.CTkFont(size=12),
        justify="center",
        wraplength=500,
    )
    hint.grid(row=1, column=0, sticky="ew", pady=(18, 0))

    footer = ctk.CTkFrame(panel, fg_color="transparent")
    footer.grid(row=2, column=0, sticky="ew", padx=28, pady=(6, 22))
    footer.grid_columnconfigure(0, weight=1)
    footer.grid_columnconfigure(1, weight=1)
    footer.grid_columnconfigure(2, weight=1)

    ctk.CTkLabel(
        footer,
        text="ENGINE_LOCAL_AES_256",
        text_color=TEXT_MUTED,
        font=ctk.CTkFont(size=11, family="Consolas"),
    ).grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 12))

    ctk.CTkButton(
        footer,
        text="Cancel",
        height=40,
        corner_radius=4,
        fg_color="transparent",
        hover_color=ERROR_BG,
        border_width=1,
        border_color=OUTLINE,
        text_color=TEXT,
        font=ctk.CTkFont(size=13, weight="bold"),
        command=on_cancel,
    ).grid(row=1, column=0, sticky="ew", padx=(0, 10))
    ctk.CTkButton(
        footer,
        text="Reset Tries",
        height=40,
        corner_radius=4,
        fg_color="transparent",
        hover_color=SURFACE_HIGHEST,
        border_width=1,
        border_color=OUTLINE,
        text_color=TEXT,
        font=ctk.CTkFont(size=13, weight="bold"),
        command=on_reset_attempts,
    ).grid(row=1, column=1, sticky="ew", padx=5)
    ctk.CTkButton(
        footer,
        text="Verify Riff",
        height=40,
        corner_radius=4,
        fg_color=TEAL,
        hover_color="#63F7FF",
        text_color=TEAL_DARK,
        font=ctk.CTkFont(size=13, weight="bold"),
        command=on_verify,
    ).grid(row=1, column=2, sticky="ew", padx=(10, 0))


def _signal_bar(ctk, parent, *, column: int, height: int, active: bool) -> None:
    spacer = ctk.CTkFrame(parent, width=5, height=28, fg_color="transparent")
    spacer.grid(row=0, column=column, padx=(0, 5), sticky="s")
    bar = ctk.CTkFrame(
        spacer,
        width=5,
        height=height,
        corner_radius=0,
        fg_color=TEAL if active else OUTLINE,
    )
    bar.pack(side="bottom")


def _format_duration(seconds: int) -> str:
    minutes = seconds // 60
    remaining_seconds = seconds % 60
    return f"{minutes:02d}:{remaining_seconds:02d}.00"
