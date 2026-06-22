"""Minimal desktop UI bootstrap."""

from __future__ import annotations

from rifflock.auth import OwnerSetupRequest, OwnerSetupService
from rifflock.config import AppConfig
from rifflock.settings import SettingsService
from rifflock.ui.dashboard import (
    DashboardDataService,
    ProtectFileFlowService,
    ProtectFolderFlowService,
    RestoreFileFlowService,
    build_dashboard_screen,
)
from rifflock.ui.routes import AppRoute
from rifflock.ui.setup import build_setup_screen
from rifflock.ui.settings import build_settings_screen


def launch_app(
    config: AppConfig,
    route: AppRoute,
    *,
    dashboard_data_service: DashboardDataService | None = None,
    protect_file_flow_service: ProtectFileFlowService | None = None,
    protect_folder_flow_service: ProtectFolderFlowService | None = None,
    restore_file_flow_service: RestoreFileFlowService | None = None,
    settings_service: SettingsService | None = None,
    owner_setup_service: OwnerSetupService | None = None,
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

    def render_placeholder(name: str) -> None:
        for child in app.winfo_children():
            child.destroy()
        label = ctk.CTkLabel(app, text=f"Current screen: {name}")
        label.pack(expand=True)

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
            app.title(f"{config.app_name} - Login")
            render_placeholder("login")

        build_setup_screen(
            app,
            ctk,
            on_submit=on_submit,
        )
    elif route.name == "dashboard" and dashboard_data_service is not None:
        def render_dashboard() -> None:
            for child in app.winfo_children():
                child.destroy()

            state = dashboard_data_service.load()

            def on_protect_file() -> None:
                if protect_file_flow_service is None or session_data_key is None:
                    messagebox.showerror("Protect File", "File protection is not available.")
                    return

                source_path = filedialog.askopenfilename(
                    title="Select file to protect",
                )
                if not source_path:
                    return

                use_default_output = messagebox.askyesno(
                    "Protect File",
                    "Use the default vault location for the protected file?",
                )
                output_path = None
                if not use_default_output:
                    default_output = protect_file_flow_service.get_default_output_path(source_path)
                    output_path = filedialog.asksaveasfilename(
                        title="Choose protected file output",
                        defaultextension=".rifflock",
                        initialdir=str(default_output.parent),
                        initialfile=default_output.name,
                        filetypes=[("RiffLock files", "*.rifflock")],
                    )
                    if not output_path:
                        return

                result = protect_file_flow_service.protect_file(
                    source_path=source_path,
                    data_key=session_data_key,
                    output_path=output_path,
                )
                if result.succeeded:
                    messagebox.showinfo("Protect File", result.message)
                else:
                    messagebox.showerror("Protect File", result.message)
                render_dashboard()

            def on_restore_file() -> None:
                if restore_file_flow_service is None or session_data_key is None:
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
                    data_key=session_data_key,
                    output_path=output_path,
                )
                if result.succeeded:
                    messagebox.showinfo("Restore File", result.message)
                else:
                    messagebox.showerror("Restore File", result.message)
                render_dashboard()

            def on_protect_folder() -> None:
                if protect_folder_flow_service is None or session_data_key is None:
                    messagebox.showerror("Protect Folder", "Folder protection is not available.")
                    return

                source_path = filedialog.askdirectory(
                    title="Select folder to protect",
                    mustexist=True,
                )
                if not source_path:
                    return

                confirmed = messagebox.askyesno(
                    "Protect Folder",
                    "Protect all supported files in this folder recursively?",
                )
                if not confirmed:
                    return

                default_output = protect_folder_flow_service.get_default_output_path(source_path)
                result = protect_folder_flow_service.protect_folder(
                    source_path=source_path,
                    data_key=session_data_key,
                    output_path=default_output,
                )
                if result.succeeded:
                    messagebox.showinfo("Protect Folder", result.message)
                else:
                    messagebox.showerror("Protect Folder", result.message)
                render_dashboard()

            def render_settings() -> None:
                if settings_service is None:
                    messagebox.showerror("Settings", "Settings are not available.")
                    return

                for child in app.winfo_children():
                    child.destroy()

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
                        updated = settings_service.start_riff_enrollment(
                            password_confirmation=password_confirmation,
                        )
                    except Exception as error:
                        messagebox.showerror("Riff Enrollment", str(getattr(error, "user_message", error)))
                        return

                    messagebox.showinfo("Riff Enrollment", "Riff 2FA is now enabled.")
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
                        messagebox.showerror("Change Password", str(getattr(error, "user_message", error)))
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
                        messagebox.showerror("Disable Riff 2FA", str(getattr(error, "user_message", error)))
                        return

                    messagebox.showinfo("Disable Riff 2FA", "Riff 2FA has been disabled.")
                    render_settings_with_state(updated)

                def on_open_app_data_folder() -> None:
                    try:
                        path = settings_service.open_app_data_folder()
                    except Exception as error:
                        messagebox.showerror("Settings", str(getattr(error, "user_message", error)))
                        return
                    messagebox.showinfo("Settings", f"Opened {path}.")

                def render_settings_with_state(current_state) -> None:
                    for child in app.winfo_children():
                        child.destroy()
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
                    )

                render_settings_with_state(state)

            build_dashboard_screen(
                app,
                ctk,
                state=state,
                on_protect_file=on_protect_file,
                on_protect_folder=on_protect_folder,
                on_restore_file=on_restore_file,
                on_settings=render_settings,
                on_logout=lambda: messagebox.showinfo("Logout", "Logout flow is available from the dashboard."),
            )

        render_dashboard()
    else:
        render_placeholder(route.name)
    app.mainloop()
