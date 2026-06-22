"""Owner setup screen UI helpers."""

from __future__ import annotations

from typing import Callable

from rifflock.ui.copy import (
    PASSWORD_LOSS_ACKNOWLEDGEMENT_TEXT,
    PASSWORD_LOSS_WARNING_TEXT,
    PASSWORD_LOSS_WARNING_TITLE,
)


def build_setup_screen(
    app,
    ctk,
    *,
    on_submit: Callable[[str, str, str, bool], None],
) -> None:
    """Render the first-run owner setup screen."""

    container = ctk.CTkFrame(app, corner_radius=0, fg_color="transparent")
    container.pack(fill="both", expand=True, padx=20, pady=20)

    header = ctk.CTkFrame(container, fg_color="transparent")
    header.pack(fill="x")

    title = ctk.CTkLabel(
        header,
        text="Create Owner Account",
        font=ctk.CTkFont(size=28, weight="bold"),
    )
    title.pack(anchor="w")

    subtitle = ctk.CTkLabel(
        header,
        text="Set up the single local RiffLock owner account.",
        anchor="w",
    )
    subtitle.pack(fill="x", pady=(6, 0))

    warning_card = ctk.CTkFrame(container, fg_color="#3F2B1B")
    warning_card.pack(fill="x", pady=(20, 16))

    warning_title = ctk.CTkLabel(
        warning_card,
        text=PASSWORD_LOSS_WARNING_TITLE,
        font=ctk.CTkFont(size=18, weight="bold"),
        anchor="w",
    )
    warning_title.pack(fill="x", padx=16, pady=(16, 8))

    warning_body = ctk.CTkLabel(
        warning_card,
        text=PASSWORD_LOSS_WARNING_TEXT,
        anchor="w",
        justify="left",
        wraplength=680,
    )
    warning_body.pack(fill="x", padx=16, pady=(0, 16))

    form_card = ctk.CTkFrame(container)
    form_card.pack(fill="x")

    email_entry = _entry_row(ctk, form_card, "Email")
    password_entry = _entry_row(ctk, form_card, "Password", show="*")
    password_confirmation_entry = _entry_row(
        ctk,
        form_card,
        "Confirm Password",
        show="*",
    )

    acknowledged = ctk.BooleanVar(value=False)
    acknowledgement_row = ctk.CTkFrame(form_card, fg_color="transparent")
    acknowledgement_row.pack(fill="x", padx=16, pady=(8, 16))

    acknowledgement = ctk.CTkCheckBox(
        acknowledgement_row,
        text="",
        variable=acknowledged,
        onvalue=True,
        offvalue=False,
        width=24,
    )
    acknowledgement.pack(side="left", anchor="n", pady=(2, 0))

    acknowledgement_label = ctk.CTkLabel(
        acknowledgement_row,
        text=PASSWORD_LOSS_ACKNOWLEDGEMENT_TEXT,
        anchor="w",
        justify="left",
        wraplength=660,
    )
    acknowledgement_label.pack(fill="x", padx=(12, 0))
    acknowledgement_label.bind(
        "<Button-1>",
        lambda _event: acknowledgement.toggle(),
    )

    create_button = ctk.CTkButton(
        container,
        text="Create Account",
        command=lambda: on_submit(
            email_entry.get(),
            password_entry.get(),
            password_confirmation_entry.get(),
            bool(acknowledged.get()),
        ),
    )
    create_button.pack(anchor="e", pady=(16, 0))


def _entry_row(ctk, parent, label: str, *, show: str | None = None):
    row = ctk.CTkFrame(parent, fg_color="transparent")
    row.pack(fill="x", padx=16, pady=(16 if label == "Email" else 0, 10))

    content = ctk.CTkLabel(row, text=label, anchor="w")
    content.pack(fill="x")

    entry = ctk.CTkEntry(row, show=show or "")
    entry.pack(fill="x", pady=(6, 0))
    return entry
