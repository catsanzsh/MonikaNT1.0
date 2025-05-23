import tkinter as tk
from tkinter import ttk, messagebox
import threading
import requests
import os
import subprocess
import tempfile
import shutil

class FlamesISOInstaller:
    def __init__(self, root):
        self.root = root
        self.root.title("Flames NT ISO Installer - DDLC HUD")
        self.root.geometry("600x400")
        self.root.configure(bg="#f0f0f0")

        self.status_var = tk.StringVar(value="Select a build to begin.")

        # Build Selector Label
        tk.Label(root, text="Select Windows Build:", font=("Segoe UI", 12), bg="#f0f0f0").pack(pady=10)

        # Build Selector Dropdown
        self.build_var = tk.StringVar()
        self.build_selector = ttk.Combobox(
            root,
            textvariable=self.build_var,
            state="readonly",
            values=["Canary Channel", "Dev Channel", "Beta Channel", "Stable Release"]
        )
        self.build_selector.current(0)
        self.build_selector.pack(pady=5)

        # Start Button
        self.start_button = tk.Button(
            root,
            text="Download & Install ISO 💾",
            command=self.start_process,
            font=("Segoe UI", 14),
            bg="#d0ffd0"
        )
        self.start_button.pack(pady=20)

        # Status Label
        self.status_label = tk.Label(
            root,
            textvariable=self.status_var,
            font=("Segoe UI", 10),
            bg="#f0f0f0"
        )
        self.status_label.pack(pady=10)

    def start_process(self):
        self.start_button.config(state='disabled')
        build = self.build_var.get()
        threading.Thread(
            target=self.download_and_install_iso,
            args=(build,),
            daemon=True
        ).start()

    def update_status(self, msg):
        self.root.after(0, lambda: self.status_var.set(msg))

    def download_and_install_iso(self, build):
        try:
            self.update_status(f"Preparing to download {build} script...")
            url_map = {
                "Canary Channel": "https://raw.githubusercontent.com/uup-dump/api/master/scripts/19045.3031/uup_download_windows.cmd",
                "Dev Channel": "https://raw.githubusercontent.com/uup-dump/api/master/scripts/23403.1000/uup_download_windows.cmd",
                "Beta Channel": "https://raw.githubusercontent.com/uup-dump/api/master/scripts/22621.1702/uup_download_windows.cmd",
                "Stable Release": "https://raw.githubusercontent.com/uup-dump/api/master/scripts/22000.194/uup_download_windows.cmd"
            }

            script_url = url_map.get(build)
            if not script_url:
                raise Exception("Invalid build selection")

            temp_dir = tempfile.mkdtemp()
            script_path = os.path.join(temp_dir, "uup_download_windows.cmd")

            # Download the UUP Dump script
            self.update_status("Downloading UUP Dump script...")
            r = requests.get(script_url)
            r.raise_for_status()
            with open(script_path, 'wb') as f:
                f.write(r.content)

            # Fetch aria2c for downloading
            files_dir = os.path.join(temp_dir, "files")
            os.makedirs(files_dir, exist_ok=True)
            aria2_url = (
                "https://github.com/eladkarako/aria2c_win/raw/master/"
                "patched_official_aria2-1.36.0-win-64bit-build1/aria2c.exe"
            )
            aria2_path = os.path.join(files_dir, "aria2c.exe")
            self.update_status("Downloading aria2c.exe for UUP Dump...")
            ar = requests.get(aria2_url, stream=True)
            ar.raise_for_status()
            with open(aria2_path, 'wb') as af:
                shutil.copyfileobj(ar.raw, af)

            # Generate ISO
            self.update_status("Generating ISO (this may take a while)...")
            proc = subprocess.run([
                "cmd.exe", "/c", script_path
            ], cwd=temp_dir, shell=True, capture_output=True, text=True)
            if proc.returncode != 0:
                raise Exception(f"Script failed: {proc.stderr}")

            # Locate ISO
            iso_file = next(
                (f for f in os.listdir(temp_dir) if f.lower().endswith(".iso")),
                None
            )
            if iso_file:
                iso_path = os.path.join(temp_dir, iso_file)
                self.mount_iso(iso_path)
            else:
                raise Exception("ISO generation failed. Check the UUP Dump script logs.")

        except Exception as e:
            self.update_status(f"❌ Error: {e}")
            messagebox.showerror("Error", str(e))
        finally:
            self.root.after(0, lambda: self.start_button.config(state='normal'))

    def mount_iso(self, iso_path):
        try:
            self.update_status("Mounting ISO...")
            subprocess.run([
                "powershell", "-Command",
                f"Mount-DiskImage -ImagePath '{iso_path}'"
            ], shell=True, check=True)
            self.update_status(
                "✅ ISO Mounted. Run setup.exe from mounted drive to continue installation."
            )
        except Exception as e:
            self.update_status(f"❌ Mounting failed: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = FlamesISOInstaller(root)
    root.mainloop()
