"""Owner login screen UI helpers."""

from __future__ import annotations

from typing import Callable


def build_login_screen(
    app,
    ctk,
    *,
    on_submit: Callable[[str, str], None],
    on_reset_attempts: Callable[[str], None],
) -> None:
    """Render the owner login screen."""

    container = ctk.CTkFrame(app, corner_radius=0, fg_color="transparent")
    container.pack(fill="both", expand=True, padx=20, pady=20)

    header = ctk.CTkFrame(container, fg_color="transparent")
    header.pack(fill="x")

    title = ctk.CTkLabel(
        header,
        text="Owner Login",
        font=ctk.CTkFont(size=28, weight="bold"),
    )
    title.pack(anchor="w")

    subtitle = ctk.CTkLabel(
        header,
        text="Sign in with the local owner account you created on this device.",
        anchor="w",
    )
    subtitle.pack(fill="x", pady=(6, 0))

    form_card = ctk.CTkFrame(container)
    form_card.pack(fill="x", pady=(20, 0))

    email_entry = _entry_row(ctk, form_card, "Email")
    password_entry = _entry_row(ctk, form_card, "Password", show="*")

    actions = ctk.CTkFrame(container, fg_color="transparent")
    actions.pack(fill="x", pady=(16, 0))

    reset_button = ctk.CTkButton(
        actions,
        text="Reset Tries",
        width=110,
        height=30,
        command=lambda: on_reset_attempts(email_entry.get()),
    )
    reset_button.pack(side="left")

    login_button = ctk.CTkButton(
        actions,
        text="Login",
        command=lambda: on_submit(email_entry.get(), password_entry.get()),
    )
    login_button.pack(side="right")


def _entry_row(ctk, parent, label: str, *, show: str | None = None):
    row = ctk.CTkFrame(parent, fg_color="transparent")
    row.pack(fill="x", padx=16, pady=(16 if label == "Email" else 0, 10))

    content = ctk.CTkLabel(row, text=label, anchor="w")
    content.pack(fill="x")

    entry = ctk.CTkEntry(row, show=show or "")
    entry.pack(fill="x", pady=(6, 0))
    return entry
