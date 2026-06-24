"""Protect file and folder workflow UI helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

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
class ProtectScreenState:
    mode: str
    owner_email: str | None = None
    riff_2fa_enabled: bool = False
    source_path: str | None = None
    output_path: str | None = None
    result_message: str | None = None
    result_succeeded: bool | None = None


def build_protect_screen(
    app,
    ctk,
    *,
    state: ProtectScreenState,
    on_back: Callable[[], None],
    on_settings: Callable[[], None] | None,
    on_activity: Callable[[], None] | None,
    on_logout: Callable[[], None] | None,
    on_switch_mode: Callable[[str], None],
    on_select_file_source: Callable[[], None],
    on_select_folder_source: Callable[[], None],
    on_select_output: Callable[[], None],
    on_use_default_output: Callable[[], None],
    on_submit: Callable[[], None],
) -> None:
    """Render the focused protect workflow screen."""

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
        owner_email=state.owner_email or "local owner",
        active_mode=state.mode,
        on_back=on_back,
        on_switch_mode=on_switch_mode,
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
        mode=state.mode,
        source_path=state.source_path,
        riff_2fa_enabled=state.riff_2fa_enabled,
        on_back=on_back,
        on_settings=on_settings,
    )

    canvas = ctk.CTkFrame(main, corner_radius=0, fg_color=BACKGROUND)
    canvas.grid(row=1, column=0, sticky="nsew", padx=24, pady=24)
    canvas.grid_columnconfigure(0, weight=1)
    canvas.grid_rowconfigure(1, weight=1)

    _build_step_indicator(ctk, canvas, state)

    if state.mode == "folder":
        _build_folder_flow(
            ctk,
            canvas,
            state=state,
            on_select_source=on_select_folder_source,
            on_select_output=on_select_output,
            on_use_default_output=on_use_default_output,
            on_submit=on_submit,
            on_back=on_back,
        )
    else:
        _build_file_flow(
            ctk,
            canvas,
            state=state,
            on_select_source=on_select_file_source,
            on_select_output=on_select_output,
            on_use_default_output=on_use_default_output,
            on_submit=on_submit,
            on_back=on_back,
        )


def _build_sidebar(
    ctk,
    parent,
    *,
    owner_email: str,
    active_mode: str,
    on_back: Callable[[], None],
    on_switch_mode: Callable[[str], None],
    on_settings: Callable[[], None] | None,
    on_activity: Callable[[], None] | None,
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

    _nav_button(ctk, nav, "Dashboard", row=0, command=on_back)
    _nav_button(ctk, nav, "Protect File", row=1, active=active_mode == "file", command=lambda: on_switch_mode("file"))
    _nav_button(ctk, nav, "Protect Folder", row=2, active=active_mode == "folder", command=lambda: on_switch_mode("folder"))
    _nav_button(ctk, nav, "Riff 2FA", row=3, command=on_settings)
    _nav_button(ctk, nav, "Activity", row=4, command=on_activity)
    _nav_button(ctk, nav, "Settings", row=5, command=on_settings)

    session = ctk.CTkFrame(sidebar, fg_color=SURFACE_LOW, border_width=1, border_color=OUTLINE, corner_radius=0)
    session.grid(row=2, column=0, sticky="sew")
    session.grid_columnconfigure(0, weight=1)
    ctk.CTkLabel(
        session,
        text=owner_email,
        text_color=TEXT_MUTED,
        font=ctk.CTkFont(size=11, family="Consolas"),
        anchor="w",
    ).grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 8))
    ctk.CTkLabel(
        session,
        text="UNLOCKED LOCALLY",
        text_color=TEAL,
        font=ctk.CTkFont(size=11, weight="bold", family="Consolas"),
        anchor="w",
    ).grid(row=1, column=0, sticky="ew", padx=24, pady=(0, 12))
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
    ).grid(row=2, column=0, sticky="ew", padx=24, pady=(0, 20))


def _nav_button(ctk, parent, label: str, *, row: int, command: Callable[[], None] | None = None, active: bool = False) -> None:
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
    )
    button.grid(row=row, column=0, sticky="ew")


def _build_topbar(
    ctk,
    parent,
    *,
    mode: str,
    source_path: str | None,
    riff_2fa_enabled: bool,
    on_back: Callable[[], None],
    on_settings: Callable[[], None] | None,
) -> None:
    topbar = ctk.CTkFrame(parent, height=64, corner_radius=0, fg_color=SURFACE_LOW, border_width=1, border_color=OUTLINE)
    topbar.grid(row=0, column=0, sticky="ew")
    topbar.grid_propagate(False)
    topbar.grid_columnconfigure(0, weight=1)

    label = "Protect Folder" if mode == "folder" else "Protect File"
    source_hint = _compact_path(source_path) if source_path else "No source selected"
    left = ctk.CTkFrame(topbar, fg_color="transparent")
    left.grid(row=0, column=0, sticky="w", padx=24)
    ctk.CTkLabel(left, text=label, text_color=TEAL, font=ctk.CTkFont(size=18, weight="bold")).pack(side="left")
    ctk.CTkLabel(left, text="/", text_color=OUTLINE, font=ctk.CTkFont(size=16)).pack(side="left", padx=10)
    ctk.CTkLabel(left, text=source_hint, text_color=TEXT_MUTED, font=ctk.CTkFont(size=11, family="Consolas")).pack(side="left")

    right = ctk.CTkFrame(topbar, fg_color="transparent")
    right.grid(row=0, column=1, sticky="e", padx=24)
    _top_pill(ctk, right, "2FA ENABLED" if riff_2fa_enabled else "2FA OPTIONAL", TEAL if riff_2fa_enabled else AMBER).pack(side="left", padx=(0, 10))
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
        text="Dashboard",
        height=30,
        width=100,
        corner_radius=4,
        fg_color=TEAL,
        hover_color="#63F7FF",
        text_color=TEAL_DARK,
        font=ctk.CTkFont(size=11, weight="bold", family="Consolas"),
        command=on_back,
    ).pack(side="left")


def _top_pill(ctk, parent, text: str, color: str):
    pill = ctk.CTkFrame(parent, fg_color=SURFACE_LOWEST, border_width=1, border_color=OUTLINE, corner_radius=4)
    ctk.CTkLabel(
        pill,
        text=text,
        text_color=color,
        font=ctk.CTkFont(size=10, weight="bold", family="Consolas"),
    ).pack(padx=10, pady=6)
    return pill


def _build_step_indicator(ctk, parent, state: ProtectScreenState) -> None:
    step = 3 if state.result_message else (2 if state.source_path and state.output_path else 1)
    bar = ctk.CTkFrame(parent, fg_color="transparent")
    bar.grid(row=0, column=0, sticky="ew", pady=(0, 16))
    for index, label in enumerate(("Select Source", "Configure Vault", "Finalize"), start=1):
        active = index <= step
        ctk.CTkLabel(
            bar,
            text=f"{index}  {label.upper()}",
            text_color=TEAL if active else TEXT_MUTED,
            font=ctk.CTkFont(size=10, weight="bold", family="Consolas"),
        ).pack(side="left", padx=(0, 14))
        if index < 3:
            ctk.CTkFrame(bar, width=42, height=1, fg_color=TEAL if active else OUTLINE).pack(side="left", padx=(0, 14), pady=10)


def _build_file_flow(ctk, parent, *, state: ProtectScreenState, on_select_source, on_select_output, on_use_default_output, on_submit, on_back) -> None:
    workspace = ctk.CTkFrame(parent, fg_color="transparent")
    workspace.grid(row=1, column=0, sticky="nsew")
    workspace.grid_columnconfigure(0, weight=2)
    workspace.grid_columnconfigure(1, weight=1)
    workspace.grid_rowconfigure(0, weight=1)

    left = ctk.CTkFrame(workspace, fg_color=SURFACE_CONTAINER, border_width=1, border_color=OUTLINE, corner_radius=4)
    left.grid(row=0, column=0, sticky="nsew", padx=(0, 18))
    left.grid_columnconfigure(0, weight=1)

    ctk.CTkLabel(left, text="Select Assets", text_color=TEXT, font=ctk.CTkFont(size=28, weight="bold"), anchor="w").grid(row=0, column=0, sticky="ew", padx=24, pady=(24, 6))
    ctk.CTkLabel(left, text="Choose one local file and create a .rifflock artifact. The original file remains unchanged.", text_color=TEXT_MUTED, font=ctk.CTkFont(size=13), anchor="w", wraplength=560).grid(row=1, column=0, sticky="ew", padx=24, pady=(0, 20))

    _source_drop_zone(ctk, left, row=2, mode="file", state=state, on_select_source=on_select_source)
    _output_config(ctk, left, row=3, state=state, on_select_output=on_select_output, on_use_default_output=on_use_default_output)
    _result_card(ctk, left, row=4, state=state, on_back=on_back, on_reset=lambda: None)

    _security_panel(ctk, workspace, state=state, on_submit=on_submit, title="Protect selected file", description="Encrypt the selected file into a versioned .rifflock container using the unlocked local data key.")


def _build_folder_flow(ctk, parent, *, state: ProtectScreenState, on_select_source, on_select_output, on_use_default_output, on_submit, on_back) -> None:
    workspace = ctk.CTkFrame(parent, fg_color="transparent")
    workspace.grid(row=1, column=0, sticky="nsew")
    workspace.grid_columnconfigure(0, weight=2)
    workspace.grid_columnconfigure(1, weight=1)
    workspace.grid_rowconfigure(0, weight=1)

    left = ctk.CTkFrame(workspace, fg_color=SURFACE_CONTAINER, border_width=1, border_color=OUTLINE, corner_radius=4)
    left.grid(row=0, column=0, sticky="nsew", padx=(0, 18))
    left.grid_columnconfigure(0, weight=1)

    ctk.CTkLabel(left, text="Verify Folder Contents", text_color=TEXT, font=ctk.CTkFont(size=26, weight="bold"), anchor="w").grid(row=0, column=0, sticky="ew", padx=24, pady=(24, 6))
    ctk.CTkLabel(left, text="Recursively protect supported files while preserving the source folder tree.", text_color=TEXT_MUTED, font=ctk.CTkFont(size=13), anchor="w", wraplength=560).grid(row=1, column=0, sticky="ew", padx=24, pady=(0, 20))

    _source_drop_zone(ctk, left, row=2, mode="folder", state=state, on_select_source=on_select_source)
    _folder_preview(ctk, left, row=3, source_path=state.source_path)
    _output_config(ctk, left, row=4, state=state, on_select_output=on_select_output, on_use_default_output=on_use_default_output)
    _result_card(ctk, left, row=5, state=state, on_back=on_back, on_reset=lambda: None)

    _security_panel(ctk, workspace, state=state, on_submit=on_submit, title="Protect folder recursively", description="RiffLock creates encrypted .rifflock artifacts in the selected output directory. Original files are preserved.")


def _source_drop_zone(ctk, parent, *, row: int, mode: str, state: ProtectScreenState, on_select_source: Callable[[], None]) -> None:
    selected = bool(state.source_path)
    card = ctk.CTkFrame(parent, fg_color=SURFACE_HIGHEST if selected else SURFACE_LOWEST, border_width=1, border_color=TEAL if selected else OUTLINE, corner_radius=5)
    card.grid(row=row, column=0, sticky="ew", padx=24, pady=(0, 16))
    card.grid_columnconfigure(0, weight=1)

    title = "Selected File" if mode == "file" else "Selected Folder"
    empty = "Choose a file to protect" if mode == "file" else "Choose a folder to scan and protect"
    display = state.source_path if selected else empty
    ctk.CTkLabel(card, text=title.upper(), text_color=TEAL if selected else TEXT_MUTED, font=ctk.CTkFont(size=10, weight="bold", family="Consolas"), anchor="w").grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 4))
    ctk.CTkLabel(card, text=_compact_path(display), text_color=TEXT if selected else TEXT_MUTED, font=ctk.CTkFont(size=14, weight="bold"), anchor="w", wraplength=520).grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 12))
    ctk.CTkButton(card, text="Browse Local Filesystem", height=34, corner_radius=4, fg_color=TEAL, hover_color="#63F7FF", text_color=TEAL_DARK, font=ctk.CTkFont(size=12, weight="bold"), command=on_select_source).grid(row=2, column=0, sticky="w", padx=18, pady=(0, 16))


def _output_config(ctk, parent, *, row: int, state: ProtectScreenState, on_select_output: Callable[[], None], on_use_default_output: Callable[[], None]) -> None:
    card = ctk.CTkFrame(parent, fg_color=SURFACE_LOW, border_width=1, border_color=OUTLINE, corner_radius=5)
    card.grid(row=row, column=0, sticky="ew", padx=24, pady=(0, 16))
    card.grid_columnconfigure(0, weight=1)

    ctk.CTkLabel(card, text="VAULT CONFIGURATION", text_color=TEXT_MUTED, font=ctk.CTkFont(size=10, weight="bold", family="Consolas"), anchor="w").grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 6))
    output = state.output_path or "Output path will be calculated from the selected source."
    ctk.CTkLabel(card, text=_compact_path(output), text_color=TEAL if state.output_path else TEXT_MUTED, font=ctk.CTkFont(size=11, family="Consolas"), anchor="w", wraplength=520).grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 12))

    actions = ctk.CTkFrame(card, fg_color="transparent")
    actions.grid(row=2, column=0, sticky="w", padx=18, pady=(0, 16))
    ctk.CTkButton(actions, text="Use Default", width=105, height=30, corner_radius=4, fg_color="transparent", hover_color=SURFACE_HIGHEST, border_width=1, border_color=OUTLINE, text_color=TEXT, font=ctk.CTkFont(size=11, family="Consolas"), command=on_use_default_output).pack(side="left", padx=(0, 8))
    ctk.CTkButton(actions, text="Choose Output", width=120, height=30, corner_radius=4, fg_color="transparent", hover_color=SURFACE_HIGHEST, border_width=1, border_color=OUTLINE, text_color=TEXT, font=ctk.CTkFont(size=11, family="Consolas"), command=on_select_output).pack(side="left")


def _folder_preview(ctk, parent, *, row: int, source_path: str | None) -> None:
    card = ctk.CTkFrame(parent, fg_color=SURFACE_LOW, border_width=1, border_color=OUTLINE, corner_radius=5)
    card.grid(row=row, column=0, sticky="ew", padx=24, pady=(0, 16))
    card.grid_columnconfigure(0, weight=1)

    snapshot = _folder_snapshot(source_path)
    ctk.CTkLabel(card, text="RECURSIVE SCAN PREVIEW", text_color=TEXT_MUTED, font=ctk.CTkFont(size=10, weight="bold", family="Consolas"), anchor="w").grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 4))
    ctk.CTkLabel(card, text=f"{snapshot['count']} files detected | {_format_size(snapshot['size'])}", text_color=TEXT, font=ctk.CTkFont(size=14, weight="bold"), anchor="w").grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 10))

    preview = ctk.CTkFrame(card, fg_color="transparent")
    preview.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 14))
    preview.grid_columnconfigure(0, weight=1)
    if not snapshot["files"]:
        ctk.CTkLabel(preview, text="Select a folder to preview protected contents.", text_color=TEXT_MUTED, font=ctk.CTkFont(size=12), anchor="w").grid(row=0, column=0, sticky="ew")
        return
    for index, file_info in enumerate(snapshot["files"]):
        ctk.CTkLabel(preview, text=file_info, text_color=TEXT_MUTED, font=ctk.CTkFont(size=11, family="Consolas"), anchor="w").grid(row=index, column=0, sticky="ew", pady=(0, 3))


def _security_panel(ctk, parent, *, state: ProtectScreenState, on_submit: Callable[[], None], title: str, description: str) -> None:
    panel = ctk.CTkFrame(parent, fg_color=SURFACE_CONTAINER, border_width=1, border_color=OUTLINE, corner_radius=5)
    panel.grid(row=0, column=1, sticky="nsew")
    panel.grid_columnconfigure(0, weight=1)

    ctk.CTkLabel(panel, text="Security Parameters", text_color=TEXT, font=ctk.CTkFont(size=18, weight="bold"), anchor="w").grid(row=0, column=0, sticky="ew", padx=22, pady=(22, 16))
    _parameter(ctk, panel, row=1, label="Encryption Standard", value="AES-256-GCM")
    _parameter(ctk, panel, row=2, label="Output Format", value=".rifflock artifact")
    _parameter(ctk, panel, row=3, label="Source Handling", value="Original files preserved")
    _parameter(ctk, panel, row=4, label="Key Scope", value="Unlocked session memory")

    warning = ctk.CTkFrame(panel, fg_color="#211C12", border_width=1, border_color="#4D2600", corner_radius=5)
    warning.grid(row=5, column=0, sticky="ew", padx=22, pady=(16, 18))
    ctk.CTkLabel(warning, text="RiffLock does not store your password or cloud recovery keys.", text_color=AMBER, font=ctk.CTkFont(size=12), anchor="w", wraplength=250).pack(fill="x", padx=14, pady=12)

    ctk.CTkLabel(panel, text=description, text_color=TEXT_MUTED, font=ctk.CTkFont(size=12), anchor="w", justify="left", wraplength=260).grid(row=6, column=0, sticky="ew", padx=22, pady=(0, 18))
    enabled = bool(state.source_path)
    ctk.CTkButton(panel, text=title, height=46, corner_radius=6, fg_color=TEAL, hover_color="#63F7FF", text_color=TEAL_DARK, font=ctk.CTkFont(size=14, weight="bold"), command=on_submit, state="normal" if enabled else "disabled").grid(row=7, column=0, sticky="ew", padx=22, pady=(0, 22))


def _parameter(ctk, parent, *, row: int, label: str, value: str) -> None:
    item = ctk.CTkFrame(parent, fg_color=SURFACE_LOW, border_width=1, border_color=OUTLINE, corner_radius=4)
    item.grid(row=row, column=0, sticky="ew", padx=22, pady=(0, 10))
    item.grid_columnconfigure(0, weight=1)
    ctk.CTkLabel(item, text=label.upper(), text_color=TEXT_MUTED, font=ctk.CTkFont(size=10, weight="bold", family="Consolas"), anchor="w").grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 2))
    ctk.CTkLabel(item, text=value, text_color=TEXT, font=ctk.CTkFont(size=12), anchor="w").grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 10))


def _result_card(ctk, parent, *, row: int, state: ProtectScreenState, on_back: Callable[[], None], on_reset: Callable[[], None]) -> None:
    if state.result_message is None:
        return
    success = bool(state.result_succeeded)
    card = ctk.CTkFrame(parent, fg_color=SURFACE_LOW if success else ERROR_BG, border_width=1, border_color=TEAL if success else ERROR, corner_radius=5)
    card.grid(row=row, column=0, sticky="ew", padx=24, pady=(0, 18))
    card.grid_columnconfigure(0, weight=1)

    title = "Protection finished" if success else "Protection failed"
    ctk.CTkLabel(card, text=title, text_color=TEAL if success else ERROR, font=ctk.CTkFont(size=18, weight="bold"), anchor="w").grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 6))
    ctk.CTkLabel(card, text=state.result_message, text_color=TEXT_MUTED, font=ctk.CTkFont(size=12), anchor="w", justify="left", wraplength=560).grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 14))
    ctk.CTkButton(card, text="View in Dashboard", width=150, height=32, corner_radius=4, fg_color=TEAL, hover_color="#63F7FF", text_color=TEAL_DARK, font=ctk.CTkFont(size=12, weight="bold"), command=on_back).grid(row=2, column=0, sticky="w", padx=18, pady=(0, 16))


def _folder_snapshot(source_path: str | None) -> dict[str, object]:
    if not source_path:
        return {"count": 0, "size": 0, "files": []}
    root = Path(source_path)
    if not root.exists() or not root.is_dir():
        return {"count": 0, "size": 0, "files": []}
    count = 0
    total_size = 0
    files: list[str] = []
    try:
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            count += 1
            try:
                total_size += path.stat().st_size
            except OSError:
                pass
            if len(files) < 5:
                try:
                    relative = path.relative_to(root)
                except ValueError:
                    relative = path
                files.append(str(relative))
    except OSError:
        pass
    return {"count": count, "size": total_size, "files": files}


def _format_size(size: int | float | None) -> str:
    if not size:
        return "0 B"
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return f"{value:.1f} GB"


def _compact_path(value: str | None) -> str:
    if not value:
        return ""
    return value if len(value) <= 78 else f"...{value[-75:]}"
