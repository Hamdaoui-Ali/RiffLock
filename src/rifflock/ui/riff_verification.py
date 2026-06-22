"""Riff verification screen UI helpers."""

from __future__ import annotations

from typing import Callable


def build_riff_verification_screen(
    app,
    ctk,
    *,
    owner_email: str,
    on_verify: Callable[[], None],
    on_reset_attempts: Callable[[], None],
    on_cancel: Callable[[], None],
) -> None:
    """Render the riff verification screen."""

    container = ctk.CTkFrame(app, corner_radius=0, fg_color="transparent")
    container.pack(fill="both", expand=True, padx=20, pady=20)

    header = ctk.CTkFrame(container, fg_color="transparent")
    header.pack(fill="x")

    title = ctk.CTkLabel(
        header,
        text="Riff Verification",
        font=ctk.CTkFont(size=28, weight="bold"),
    )
    title.pack(anchor="w")

    subtitle = ctk.CTkLabel(
        header,
        text=f"Password accepted for {owner_email}. Record your riff to finish signing in.",
        anchor="w",
        justify="left",
        wraplength=680,
    )
    subtitle.pack(fill="x", pady=(6, 0))

    instructions = ctk.CTkFrame(container)
    instructions.pack(fill="x", pady=(20, 0))

    body = ctk.CTkLabel(
        instructions,
        text=(
            "When you press Verify, the app will record one riff sample from your microphone. "
            "Perform the same short riff you used during enrollment."
        ),
        anchor="w",
        justify="left",
        wraplength=680,
    )
    body.pack(fill="x", padx=16, pady=16)

    footer = ctk.CTkFrame(container, fg_color="transparent")
    footer.pack(fill="x", pady=(16, 0))

    cancel_button = ctk.CTkButton(
        footer,
        text="Cancel",
        width=100,
        command=on_cancel,
    )
    cancel_button.pack(side="left")

    reset_button = ctk.CTkButton(
        footer,
        text="Reset Tries",
        width=110,
        height=30,
        command=on_reset_attempts,
    )
    reset_button.pack(side="left", padx=(12, 0))

    verify_button = ctk.CTkButton(
        footer,
        text="Verify Riff",
        command=on_verify,
    )
    verify_button.pack(side="right")
