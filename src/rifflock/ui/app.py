"""Desktop UI bootstrap and screen routing."""

from __future__ import annotations

import os

from rifflock.audio import REQUIRED_RIFF_RECORDINGS
from rifflock.auth import (
    LoginService,
    OwnerSetupRequest,
    OwnerSetupService,
    PendingRiffVerification,
)
from rifflock.auth.riff_verification import RiffVerificationService
from rifflock.config import AppConfig
from rifflock.settings import SettingsService
from rifflock.ui.activity import ActivityDataService, ActivityEvent, build_activity_screen
from rifflock.ui.dashboard import (
    DashboardDataService,
    DeleteProtectedItemFlowService,
    ProtectFileFlowService,
    ProtectFolderFlowService,
    RestoreFileFlowService,
    build_dashboard_screen,
)
from rifflock.ui.login import build_login_screen
from rifflock.ui.protect import ProtectScreenState, build_protect_screen
from rifflock.ui.riff_verification import build_riff_verification_screen
from rifflock.ui.routes import AppRoute
from rifflock.ui.setup import build_setup_screen
from rifflock.ui.settings import build_settings_screen
from rifflock.utils import to_user_message


def launch_app(
    config: AppConfig,
    route: AppRoute,
    *,
    dashboard_data_service: DashboardDataService | None = None,
    activity_data_service: ActivityDataService | None = None,
    protect_file_flow_service: ProtectFileFlowService | None = None,
    protect_folder_flow_service: ProtectFolderFlowService | None = None,
    restore_file_flow_service: RestoreFileFlowService | None = None,
    delete_protected_item_flow_service: DeleteProtectedItemFlowService | None = None,
    settings_service: SettingsService | None = None,
    owner_setup_service: OwnerSetupService | None = None,
    login_service: LoginService | None = None,
    riff_verification_service: RiffVerificationService | None = None,
    session_data_key: bytes | None = None,
) -> None:
    import customtkinter as ctk
    from tkinter import filedialog, messagebox, simpledialog

    ctk.set_appearance_mode("system")
    ctk.set_default_color_theme("blue")

    app = ctk.CTk()
    app.title(f"{config.app_name} - {route.name.title()}")
    app.geometry("800x500")
    app.minsize(640, 400)
    current_session_data_key = session_data_key
    current_session_owner_email: str | None = None
    current_session_riff_2fa_enabled = False
    pending_riff_verification: PendingRiffVerification | None = None

    def clear_screen() -> None:
        for child in app.winfo_children():
            child.destroy()

    def render_placeholder(name: str) -> None:
        clear_screen()
        label = ctk.CTkLabel(app, text=f"Current screen: {name}")
        label.pack(expand=True)

    def show_recording_countdown(title: str, description: str) -> None:
        countdown = ctk.CTkToplevel(app)
        countdown.title(title)
        countdown.geometry("360x220")
        countdown.resizable(False, False)
        countdown.transient(app)
        countdown.grab_set()

        frame = ctk.CTkFrame(countdown)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        heading = ctk.CTkLabel(
            frame,
            text=title,
            font=ctk.CTkFont(size=24, weight="bold"),
        )
        heading.pack(pady=(8, 12))

        body = ctk.CTkLabel(
            frame,
            text=description,
            justify="center",
            wraplength=280,
        )
        body.pack(pady=(0, 12))

        counter = ctk.CTkLabel(
            frame,
            text="3",
            font=ctk.CTkFont(size=56, weight="bold"),
        )
        counter.pack(expand=True)

        countdown.update_idletasks()
        parent_x = app.winfo_rootx()
        parent_y = app.winfo_rooty()
        parent_width = app.winfo_width()
        parent_height = app.winfo_height()
        width = countdown.winfo_width()
        height = countdown.winfo_height()
        offset_x = parent_x + max((parent_width - width) // 2, 0)
        offset_y = parent_y + max((parent_height - height) // 2, 0)
        countdown.geometry(f"{width}x{height}+{offset_x}+{offset_y}")

        def tick(value: int) -> None:
            if value > 0:
                counter.configure(text=str(value))
                countdown.after(1000, lambda: tick(value - 1))
                return
            countdown.destroy()

        tick(3)
        countdown.wait_window()

    def render_login() -> None:
        if login_service is None:
            render_placeholder("login")
            return

        clear_screen()
        app.title(f"{config.app_name} - Login")

        def on_submit(email: str, password: str) -> None:
            nonlocal current_session_data_key, current_session_owner_email, current_session_riff_2fa_enabled, pending_riff_verification

            try:
                result = login_service.login(email, password)
            except Exception as error:
                messagebox.showerror("Login", to_user_message(error))
                return

            if result.next_screen == "dashboard" and result.session is not None:
                current_session_data_key = result.session.unlocked_data_key
                current_session_owner_email = result.session.owner_email
                current_session_riff_2fa_enabled = result.session.riff_2fa_enabled
                render_dashboard()
                return

            if result.next_screen == "riff_verification" and result.pending_riff_verification is not None:
                pending_riff_verification = result.pending_riff_verification
                render_riff_verification()
                return

            render_placeholder(result.next_screen)

        def on_reset_attempts(email: str) -> None:
            normalized_email = email.strip().lower()
            if not normalized_email:
                messagebox.showerror("Login", "Enter your email before resetting tries.")
                return
            login_service.reset_failed_attempts(normalized_email)
            messagebox.showinfo("Login", "Login tries have been reset.")

        build_login_screen(
            app,
            ctk,
            on_submit=on_submit,
            on_reset_attempts=on_reset_attempts,
        )

    def render_dashboard() -> None:
        if dashboard_data_service is None:
            render_placeholder("dashboard")
            return

        clear_screen()
        app.title(f"{config.app_name} - Dashboard")

        state = dashboard_data_service.load()
        dashboard_owner_email = current_session_owner_email
        dashboard_riff_2fa_enabled = current_session_riff_2fa_enabled
        if settings_service is not None:
            try:
                settings_state = settings_service.load()
                dashboard_owner_email = settings_state.owner_email
                dashboard_riff_2fa_enabled = settings_state.riff_2fa_enabled
            except Exception:
                pass

        def default_protect_output(current_mode: str, source_path: str | None) -> str | None:
            if not source_path:
                return None
            if current_mode == "folder" and protect_folder_flow_service is not None:
                return str(protect_folder_flow_service.get_default_output_path(source_path))
            if current_mode == "file" and protect_file_flow_service is not None:
                return str(protect_file_flow_service.get_default_output_path(source_path))
            return None

        def render_protect_workspace(
            mode: str = "file",
            source_path: str | None = None,
            output_path: str | None = None,
            result_message: str | None = None,
            result_succeeded: bool | None = None,
        ) -> None:
            normalized_mode = "folder" if mode == "folder" else "file"
            selected_output = output_path or default_protect_output(normalized_mode, source_path)

            def select_file_source() -> None:
                selected = filedialog.askopenfilename(title="Select file to protect")
                if not selected:
                    return
                render_protect_workspace(
                    "file",
                    selected,
                    default_protect_output("file", selected),
                )

            def select_folder_source() -> None:
                selected = filedialog.askdirectory(
                    title="Select folder to protect",
                    mustexist=True,
                )
                if not selected:
                    return
                render_protect_workspace(
                    "folder",
                    selected,
                    default_protect_output("folder", selected),
                )

            def select_output() -> None:
                if not source_path:
                    messagebox.showerror("Protect", "Select a source before choosing an output path.")
                    return
                default_output = default_protect_output(normalized_mode, source_path)
                initial_dir = None
                initial_file = None
                if default_output is not None:
                    default_path = os.path.abspath(default_output)
                    initial_dir = os.path.dirname(default_path)
                    initial_file = os.path.basename(default_path)
                if normalized_mode == "folder":
                    selected = filedialog.askdirectory(
                        title="Choose protected folder output",
                        initialdir=initial_dir,
                    )
                else:
                    selected = filedialog.asksaveasfilename(
                        title="Choose protected file output",
                        defaultextension=".rifflock",
                        initialdir=initial_dir,
                        initialfile=initial_file,
                        filetypes=[("RiffLock files", "*.rifflock")],
                    )
                if not selected:
                    return
                render_protect_workspace(normalized_mode, source_path, selected)

            def use_default_output() -> None:
                if not source_path:
                    messagebox.showerror("Protect", "Select a source before calculating the default output path.")
                    return
                render_protect_workspace(
                    normalized_mode,
                    source_path,
                    default_protect_output(normalized_mode, source_path),
                )

            def submit() -> None:
                if current_session_data_key is None:
                    messagebox.showerror("Protect", "File protection is not available.")
                    return
                if not source_path:
                    messagebox.showerror("Protect", "Select a source before starting protection.")
                    return
                if normalized_mode == "folder":
                    if protect_folder_flow_service is None:
                        messagebox.showerror("Protect Folder", "Folder protection is not available.")
                        return
                    result = protect_folder_flow_service.protect_folder(
                        source_path=source_path,
                        data_key=current_session_data_key,
                        output_path=selected_output,
                    )
                else:
                    if protect_file_flow_service is None:
                        messagebox.showerror("Protect File", "File protection is not available.")
                        return
                    result = protect_file_flow_service.protect_file(
                        source_path=source_path,
                        data_key=current_session_data_key,
                        output_path=selected_output,
                    )
                render_protect_workspace(
                    normalized_mode,
                    source_path,
                    selected_output,
                    result.message,
                    result.succeeded,
                )

            clear_screen()
            app.title(f"{config.app_name} - Protect")
            build_protect_screen(
                app,
                ctk,
                state=ProtectScreenState(
                    mode=normalized_mode,
                    owner_email=dashboard_owner_email,
                    riff_2fa_enabled=dashboard_riff_2fa_enabled,
                    source_path=source_path,
                    output_path=selected_output,
                    result_message=result_message,
                    result_succeeded=result_succeeded,
                ),
                on_back=render_dashboard,
                on_settings=render_settings,
                on_activity=render_activity,
                on_logout=on_logout,
                on_switch_mode=lambda next_mode: render_protect_workspace(next_mode),
                on_select_file_source=select_file_source,
                on_select_folder_source=select_folder_source,
                on_select_output=select_output,
                on_use_default_output=use_default_output,
                on_submit=submit,
            )

        def on_protect_file() -> None:
            render_protect_workspace("file")
        def on_restore_file() -> None:
            if restore_file_flow_service is None or current_session_data_key is None:
                messagebox.showerror("Restore File", "File restore is not available.")
                return

            protected_path = filedialog.askopenfilename(
                title="Select .rifflock file to restore",
                filetypes=[("RiffLock files", "*.rifflock")],
            )
            if not protected_path:
                return

            try:
                default_output = restore_file_flow_service.get_default_output_path(protected_path)
            except Exception:
                messagebox.showerror(
                    "Restore File",
                    "The selected .rifflock file could not be restored.",
                )
                return

            output_path = filedialog.asksaveasfilename(
                title="Choose restored file output",
                initialdir=str(default_output.parent),
                initialfile=default_output.name,
            )
            if not output_path:
                return

            result = restore_file_flow_service.restore_file(
                protected_path=protected_path,
                data_key=current_session_data_key,
                output_path=output_path,
            )
            if result.succeeded:
                messagebox.showinfo("Restore File", result.message)
            else:
                messagebox.showerror("Restore File", result.message)
            render_dashboard()

        def on_restore_item(item) -> None:
            if restore_file_flow_service is None or current_session_data_key is None:
                messagebox.showerror("Restore File", "File restore is not available.")
                return
            if not item.protected_exists:
                messagebox.showerror("Restore File", "The encrypted artifact is missing.")
                return
            try:
                default_output = restore_file_flow_service.get_default_output_path(item.record.artifact_path)
            except Exception:
                messagebox.showerror(
                    "Restore File",
                    "The selected .rifflock file could not be restored.",
                )
                return
            output_path = filedialog.asksaveasfilename(
                title="Choose restored file output",
                initialdir=str(default_output.parent),
                initialfile=default_output.name,
            )
            if not output_path:
                return
            result = restore_file_flow_service.restore_file(
                protected_path=item.record.artifact_path,
                data_key=current_session_data_key,
                output_path=output_path,
            )
            if result.succeeded:
                messagebox.showinfo("Restore File", result.message)
            else:
                messagebox.showerror("Restore File", result.message)
            render_dashboard()

        def on_protect_folder() -> None:
            render_protect_workspace("folder")
        def on_open_item(item) -> None:
            if restore_file_flow_service is None or current_session_data_key is None:
                messagebox.showerror("Open File", "File opening is not available.")
                return

            try:
                result = restore_file_flow_service.prepare_file_for_opening(
                    protected_path=item.record.artifact_path,
                    data_key=current_session_data_key,
                )
                os.startfile(str(result.viewing_path))
            except Exception as error:
                messagebox.showerror("Open File", to_user_message(error))

        def on_delete_item(item) -> None:
            if delete_protected_item_flow_service is None:
                messagebox.showerror("Delete File", "Protected file deletion is not available.")
                return

            confirmed = messagebox.askyesno(
                "Delete File",
                "Remove this file from protection? The encrypted .rifflock artifact will be deleted.",
            )
            if not confirmed:
                return

            result = delete_protected_item_flow_service.delete_item(item)
            if result.succeeded:
                messagebox.showinfo("Delete File", result.message)
            else:
                messagebox.showerror("Delete File", result.message)
            render_dashboard()

        def render_settings() -> None:
            if settings_service is None:
                messagebox.showerror("Settings", "Settings are not available.")
                return

            clear_screen()

            state = settings_service.load()

            def on_save(duration_text: str, threshold_text: str) -> None:
                try:
                    updated = settings_service.save_audio_settings(
                        recording_duration_seconds=int(duration_text),
                        similarity_threshold=float(threshold_text),
                    )
                except Exception as error:
                    messagebox.showerror("Settings", str(getattr(error, "user_message", error)))
                    return

                messagebox.showinfo("Settings", "Settings saved.")
                render_settings_with_state(updated)

            def on_start_riff_enrollment() -> None:
                password_confirmation = simpledialog.askstring(
                    "Riff Enrollment",
                    "Confirm your password to start riff enrollment:",
                    show="*",
                )
                if not password_confirmation:
                    return
                try:
                    messagebox.showinfo(
                        "Riff Enrollment",
                        (
                            f"Riff enrollment will capture {REQUIRED_RIFF_RECORDINGS} recordings. "
                            "You will be prompted before each one."
                        ),
                    )
                    updated = settings_service.start_riff_enrollment(
                        password_confirmation=password_confirmation,
                        before_recording=lambda attempt, total: show_recording_countdown(
                            f"Riff Enrollment {attempt}/{total}",
                            "Recording will start when the countdown reaches 1. "
                            "Play the same short riff into your microphone.",
                        ),
                    )
                except Exception as error:
                    messagebox.showerror("Riff Enrollment", to_user_message(error))
                    return

                messagebox.showinfo(
                    "Riff Enrollment",
                    "Riff enrollment completed and 2FA is now enabled.",
                )
                render_settings_with_state(updated)

            def on_change_password() -> None:
                current_password = simpledialog.askstring(
                    "Change Password",
                    "Enter your current password:",
                    show="*",
                )
                if not current_password:
                    return
                new_password = simpledialog.askstring(
                    "Change Password",
                    "Enter your new password:",
                    show="*",
                )
                if not new_password:
                    return
                new_password_confirmation = simpledialog.askstring(
                    "Change Password",
                    "Confirm your new password:",
                    show="*",
                )
                if not new_password_confirmation:
                    return
                try:
                    updated = settings_service.change_password(
                        current_password=current_password,
                        new_password=new_password,
                        new_password_confirmation=new_password_confirmation,
                    )
                except Exception as error:
                    messagebox.showerror("Change Password", to_user_message(error))
                    return

                messagebox.showinfo("Change Password", "Password updated.")
                render_settings_with_state(updated)

            def on_disable_riff_2fa() -> None:
                password_confirmation = simpledialog.askstring(
                    "Disable Riff 2FA",
                    "Confirm your password to disable riff 2FA:",
                    show="*",
                )
                if not password_confirmation:
                    return
                try:
                    updated = settings_service.disable_riff_2fa(
                        password_confirmation=password_confirmation,
                    )
                except Exception as error:
                    messagebox.showerror("Disable Riff 2FA", to_user_message(error))
                    return

                messagebox.showinfo("Disable Riff 2FA", "Riff 2FA has been disabled.")
                render_settings_with_state(updated)

            def on_open_app_data_folder() -> None:
                try:
                    path = settings_service.open_app_data_folder()
                except Exception as error:
                    messagebox.showerror("Settings", to_user_message(error))
                    return
                messagebox.showinfo("Settings", f"Opened {path}.")

            def render_settings_with_state(current_state) -> None:
                clear_screen()
                build_settings_screen(
                    app,
                    ctk,
                    state=current_state,
                    on_save=on_save,
                    on_change_password=on_change_password,
                    on_start_riff_enrollment=on_start_riff_enrollment,
                    on_disable_riff_2fa=on_disable_riff_2fa,
                    on_open_app_data_folder=on_open_app_data_folder,
                    on_back=render_dashboard,
                    on_protect_file=on_protect_file,
                    on_restore_file=on_restore_file,
                    on_activity=render_activity,
                    on_logout=on_logout,
                )

            render_settings_with_state(state)


        def render_activity() -> None:
            if activity_data_service is None:
                messagebox.showerror("Activity", "Activity data is not available.")
                return

            try:
                activity_state = activity_data_service.load(owner_email=dashboard_owner_email)
            except Exception as error:
                messagebox.showerror("Activity", to_user_message(error))
                return

            def on_export(events: list[ActivityEvent]) -> None:
                if not events:
                    messagebox.showinfo("Activity", "There are no visible activity rows to export.")
                    return
                output_path = filedialog.asksaveasfilename(
                    title="Export audit trail",
                    defaultextension=".log",
                    initialfile="rifflock-audit-trail.log",
                    filetypes=[("Log files", "*.log"), ("Text files", "*.txt"), ("All files", "*.*")],
                )
                if not output_path:
                    return
                lines = ["RiffLock local audit trail", ""]
                for event in events:
                    lines.append(
                        " | ".join(
                            (
                                event.timestamp,
                                event.event_type.upper(),
                                event.title,
                                event.identifier,
                                event.status.upper(),
                                event.detail,
                                event.secondary,
                            )
                        )
                    )
                try:
                    with open(output_path, "w", encoding="utf-8") as audit_file:
                        audit_file.write("\n".join(lines) + "\n")
                except Exception as error:
                    messagebox.showerror("Activity", to_user_message(error))
                    return
                messagebox.showinfo("Activity", f"Audit trail exported to {output_path}.")

            clear_screen()
            app.title(f"{config.app_name} - Activity")
            build_activity_screen(
                app,
                ctk,
                state=activity_state,
                owner_email=dashboard_owner_email,
                riff_2fa_enabled=dashboard_riff_2fa_enabled,
                on_dashboard=render_dashboard,
                on_protect_file=on_protect_file,
                on_restore_file=on_restore_file,
                on_settings=render_settings,
                on_logout=on_logout,
                on_export=on_export,
            )
        build_dashboard_screen(
            app,
            ctk,
            state=state,
            on_protect_file=on_protect_file,
            on_protect_folder=on_protect_folder,
            on_restore_file=on_restore_file,
            on_open_item=on_open_item,
            on_restore_item=on_restore_item,
            on_delete_item=on_delete_item,
            on_settings=render_settings,
            on_activity=render_activity,
            on_logout=on_logout,
            owner_email=dashboard_owner_email,
            riff_2fa_enabled=dashboard_riff_2fa_enabled,
        )

    def render_riff_verification() -> None:
        nonlocal pending_riff_verification

        if pending_riff_verification is None or riff_verification_service is None:
            render_placeholder("riff_verification")
            return

        clear_screen()
        app.title(f"{config.app_name} - Riff Verification")

        def on_verify() -> None:
            nonlocal current_session_data_key, current_session_owner_email, current_session_riff_2fa_enabled, pending_riff_verification

            try:
                show_recording_countdown(
                    "Riff Verification",
                    "Recording will start when the countdown reaches 1. "
                    "Play your enrolled riff into your microphone.",
                )
                session = riff_verification_service.verify(pending_riff_verification)
            except Exception as error:
                messagebox.showerror("Riff Verification", to_user_message(error))
                return

            current_session_data_key = session.unlocked_data_key
            current_session_owner_email = session.owner_email
            current_session_riff_2fa_enabled = session.riff_2fa_enabled
            pending_riff_verification = None
            render_dashboard()

        def on_reset_attempts() -> None:
            riff_verification_service.reset_failed_attempts(
                pending_riff_verification.owner_email,
            )
            messagebox.showinfo("Riff Verification", "Riff tries have been reset.")

        recording_duration_seconds = None
        if settings_service is not None:
            try:
                recording_duration_seconds = settings_service.load().recording_duration_seconds
            except Exception:
                recording_duration_seconds = None

        build_riff_verification_screen(
            app,
            ctk,
            owner_email=pending_riff_verification.owner_email,
            on_verify=on_verify,
            on_reset_attempts=on_reset_attempts,
            on_cancel=on_logout,
            recording_duration_seconds=recording_duration_seconds,
        )

    def on_logout() -> None:
        nonlocal current_session_data_key, current_session_owner_email, current_session_riff_2fa_enabled, pending_riff_verification

        if login_service is not None:
            login_service.logout()
        current_session_data_key = None
        current_session_owner_email = None
        current_session_riff_2fa_enabled = False
        pending_riff_verification = None
        messagebox.showinfo("Logout", "You have been logged out.")
        render_login()

    if route.name == "setup" and owner_setup_service is not None:
        def on_submit(email: str, password: str, password_confirmation: str, acknowledged: bool) -> None:
            try:
                owner_setup_service.create_owner_account(
                    OwnerSetupRequest(
                        email=email,
                        password=password,
                        password_confirmation=password_confirmation,
                        password_loss_acknowledged=acknowledged,
                    )
                )
            except Exception as error:
                messagebox.showerror("Create Account", str(getattr(error, "user_message", error)))
                return

            messagebox.showinfo(
                "Create Account",
                "Account created. Continue from the login screen.",
            )
            render_login()

        build_setup_screen(
            app,
            ctk,
            on_submit=on_submit,
        )
    elif route.name == "login":
        render_login()
    elif route.name == "dashboard":
        render_dashboard()
    elif route.name == "riff_verification":
        render_riff_verification()
    else:
        render_placeholder(route.name)
    app.mainloop()
