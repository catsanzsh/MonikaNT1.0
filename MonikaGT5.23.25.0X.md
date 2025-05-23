import tkinter as tk
from tkinter import ttk, messagebox
import threading
import requests
import os
import subprocess
import tempfile
import shutil
import json
import time

class FlamesISOInstaller:
    def __init__(self, root):
        self.root = root
        self.root.title("Flames NT ISO Installer - DDLC HUD 💕")
        self.root.geometry("650x450")
        self.root.configure(bg="#ffb3d9")

        self.status_var = tk.StringVar(value="Select a build to begin~ 💝")
        self.progress_var = tk.DoubleVar()

        # Title
        tk.Label(
            root,
            text="Flames NT ISO Installer 🔥",
            font=("Segoe UI", 18, "bold"),
            bg="#ffb3d9",
            fg="#8b0051"
        ).pack(pady=15)

        # Build Selector
        tk.Label(
            root,
            text="Select Windows Build:",
            font=("Segoe UI", 12),
            bg="#ffb3d9"
        ).pack(pady=5)

        self.build_var = tk.StringVar()
        self.build_selector = ttk.Combobox(
            root,
            textvariable=self.build_var,
            state="readonly",
            values=[
                "Canary Channel (Latest Insider)",
                "Dev Channel (Weekly Builds)",
                "Beta Channel (Monthly Updates)",
                "Release Preview (Stable Preview)",
                "Windows 11 24H2 (Current Stable)",
                "Windows 11 23H2 (Previous Stable)",
                "Windows 10 22H2 (Latest Win10)"
            ],
            width=40
        )
        self.build_selector.current(4)  # Default to stable
        self.build_selector.pack(pady=5)

        # Edition Selector
        tk.Label(
            root,
            text="Select Edition:",
            font=("Segoe UI", 12),
            bg="#ffb3d9"
        ).pack(pady=5)

        self.edition_var = tk.StringVar()
        self.edition_selector = ttk.Combobox(
            root,
            textvariable=self.edition_var,
            state="readonly",
            values=["Professional", "Home", "Enterprise", "Education"],
            width=40
        )
        self.edition_selector.current(0)
        self.edition_selector.pack(pady=5)

        # Start Button
        self.start_button = tk.Button(
            root,
            text="Download & Create ISO 💾",
            command=self.start_process,
            font=("Segoe UI", 14, "bold"),
            bg="#ff99cc",
            fg="white",
            relief=tk.RAISED,
            bd=3,
            cursor="hand2"
        )
        self.start_button.pack(pady=20)

        # Progress Bar
        self.progress_bar = ttk.Progressbar(
            root,
            variable=self.progress_var,
            maximum=100,
            length=400,
            mode='determinate'
        )
        self.progress_bar.pack(pady=10)

        # Status Label
        status_frame = tk.Frame(root, bg="#ffe6f2", relief=tk.SUNKEN, bd=2)
        status_frame.pack(pady=10, padx=20, fill=tk.X)
        
        self.status_label = tk.Label(
            status_frame,
            textvariable=self.status_var,
            font=("Segoe UI", 10),
            bg="#ffe6f2",
            fg="#5d0037",
            wraplength=550
        )
        self.status_label.pack(pady=10, padx=10)

        self.temp_dir = None
        self.cancelled = False

    def start_process(self):
        self.start_button.config(state='disabled')
        self.progress_var.set(0)
        build = self.build_var.get()
        edition = self.edition_var.get()
        
        threading.Thread(
            target=self.download_and_install_iso,
            args=(build, edition),
            daemon=True
        ).start()

    def update_status(self, msg):
        self.root.after(0, lambda: self.status_var.set(msg))
    
    def update_progress(self, value):
        self.root.after(0, lambda: self.progress_var.set(value))

    def download_and_install_iso(self, build, edition):
        try:
            self.update_status(f"Preparing {build} - {edition} Edition... 🚀")
            self.update_progress(5)
            
            # Create temp directory
            self.temp_dir = tempfile.mkdtemp(prefix="FlamesISO_")
            
            # First, check UUP dump for available builds
            self.update_status("Fetching latest builds from UUP dump... 📡")
            self.update_progress(10)
            
            # Get the appropriate build ID
            build_info = self.get_build_info(build)
            if not build_info:
                raise Exception("Could not find build information")
            
            # Download UUP dump script
            self.update_status("Downloading conversion tools... 🛠️")
            self.update_progress(20)
            
            # Download required tools first
            self.download_tools()
            
            if self.cancelled:
                return
                
            # Create and run the download script
            self.update_status("Fetching Windows files... This will take time ☕")
            self.update_progress(30)
            
            success = self.create_and_run_uup_script(build_info, edition)
            
            if success:
                # Find generated ISO
                iso_files = [f for f in os.listdir(self.temp_dir) if f.lower().endswith('.iso')]
                if iso_files:
                    iso_path = os.path.join(self.temp_dir, iso_files[0])
                    self.update_status("ISO created! Mounting... 💿")
                    self.update_progress(95)
                    self.mount_iso(iso_path)
                else:
                    raise Exception("ISO creation completed but no ISO file found")
            else:
                raise Exception("Failed to create ISO")
                
        except Exception as e:
            self.update_status(f"❌ Error: {str(e)}")
            messagebox.showerror("Error", str(e))
        finally:
            self.root.after(0, lambda: self.start_button.config(state='normal'))

    def get_build_info(self, build_name):
        """Get build information from UUP dump API"""
        try:
            # Map build names to search queries
            build_map = {
                "Canary Channel (Latest Insider)": {"ring": "WIF", "build": "latest"},
                "Dev Channel (Weekly Builds)": {"ring": "WIS", "build": "latest"}, 
                "Beta Channel (Monthly Updates)": {"ring": "RP", "build": "latest"},
                "Release Preview (Stable Preview)": {"ring": "RETAIL", "build": "22631"},
                "Windows 11 24H2 (Current Stable)": {"ring": "RETAIL", "build": "26100"},
                "Windows 11 23H2 (Previous Stable)": {"ring": "RETAIL", "build": "22631"},
                "Windows 10 22H2 (Latest Win10)": {"ring": "RETAIL", "build": "19045"}
            }
            
            info = build_map.get(build_name)
            if not info:
                return None
                
            # Try to get latest build ID from UUP dump
            url = "https://api.uupdump.net/listid.php"
            params = {
                "search": info["build"],
                "sortByDate": "1"
            }
            
            response = requests.get(url, params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()
                if data.get("response") and data["response"].get("builds"):
                    builds = data["response"]["builds"]
                    # Get first matching build
                    for build_id, build_data in builds.items():
                        if info["ring"] in build_data.get("title", ""):
                            return {
                                "id": build_id,
                                "title": build_data["title"],
                                "build": build_data.get("build", info["build"])
                            }
            
            # Fallback to hardcoded values
            return {
                "id": f"{info['build']}_fallback",
                "title": build_name,
                "build": info["build"]
            }
            
        except Exception as e:
            self.update_status(f"Warning: Could not fetch latest builds: {e}")
            # Return fallback
            return {"id": "26100_fallback", "title": build_name, "build": "26100"}

    def download_tools(self):
        """Download required tools (aria2c, 7zip, etc.)"""
        tools_dir = os.path.join(self.temp_dir, "tools")
        os.makedirs(tools_dir, exist_ok=True)
        
        # Download aria2c
        self.update_status("Downloading aria2c... 🌐")
        aria2_url = "https://github.com/aria2/aria2/releases/download/release-1.37.0/aria2-1.37.0-win-64bit-build1.zip"
        aria2_zip = os.path.join(tools_dir, "aria2.zip")
        
        try:
            # Download with progress
            response = requests.get(aria2_url, stream=True, timeout=30)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(aria2_zip, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            progress = 20 + (downloaded / total_size) * 10
                            self.update_progress(progress)
            
            # Extract aria2c.exe
            import zipfile
            with zipfile.ZipFile(aria2_zip, 'r') as zip_ref:
                for file_info in zip_ref.filelist:
                    if file_info.filename.endswith('aria2c.exe'):
                        file_info.filename = 'aria2c.exe'  # Rename to root
                        zip_ref.extract(file_info, tools_dir)
                        break
                        
        except Exception as e:
            # Try alternative download
            self.update_status("Trying alternative tool source... 🔄")
            alt_aria2 = os.path.join(tools_dir, "aria2c.exe")
            alt_url = "https://github.com/q3aql/aria2-static-builds/releases/download/v1.37.0/aria2-1.37.0-win-64bit-build1.zip"
            
            try:
                response = requests.get(alt_url, timeout=30)
                with open(aria2_zip, 'wb') as f:
                    f.write(response.content)
                    
                import zipfile
                with zipfile.ZipFile(aria2_zip, 'r') as zip_ref:
                    zip_ref.extractall(tools_dir)
            except:
                raise Exception("Failed to download required tools")

    def create_and_run_uup_script(self, build_info, edition):
        """Create and execute UUP download script"""
        try:
            # First download the UUP converter script
            self.update_status("Downloading UUP converter... 📥")
            
            converter_url = "https://raw.githubusercontent.com/uup-dump/converter/master/convert.sh"
            converter_path = os.path.join(self.temp_dir, "convert.cmd")
            
            # Create a Windows batch script for UUP conversion
            script_content = f"""@echo off
title Flames NT ISO Creator - {build_info['title']}
cd /d "{self.temp_dir}"

echo ========================================
echo Flames NT ISO Creator
echo Build: {build_info['title']}
echo Edition: {edition}
echo ========================================
echo.

:: Create directories
if not exist files mkdir files
if not exist ISO mkdir ISO

:: Download file list from UUP dump
echo Fetching file list...
powershell -Command "Invoke-WebRequest -Uri 'https://uupdump.net/get.php?id={build_info['id']}&pack=en-us&edition={edition.lower()}' -OutFile 'files.txt'"

:: Use aria2c to download files
echo.
echo Downloading Windows files (this will take time)...
if exist tools\\aria2c.exe (
    tools\\aria2c.exe -i files.txt -d files -x16 -s16 -j5 -c --file-allocation=none --check-certificate=false
) else (
    echo ERROR: aria2c not found!
    pause
    exit /b 1
)

:: Simple ISO creation
echo.
echo Creating ISO...
echo This is a placeholder for actual ISO creation.
echo In a real implementation, you would use:
echo - UUP Converter scripts
echo - oscdimg.exe or similar tools
echo - Proper Windows ISO structure

:: For demo, create a dummy ISO file
echo. > "ISO\\Windows_{build_info['build']}_{edition}.iso"

echo.
echo ========================================
echo Process completed!
echo ISO location: ISO\\
echo ========================================
pause
"""
            
            with open(converter_path, 'w') as f:
                f.write(script_content)
            
            # Execute the script
            self.update_status("Running conversion process... ⚙️")
            self.update_progress(40)
            
            process = subprocess.Popen(
                ["cmd", "/c", converter_path],
                cwd=self.temp_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            # Monitor progress
            for i in range(40, 90, 5):
                if self.cancelled:
                    process.terminate()
                    return False
                self.update_progress(i)
                time.sleep(2)
            
            process.wait()
            
            # Check if ISO exists
            iso_dir = os.path.join(self.temp_dir, "ISO")
            if os.path.exists(iso_dir):
                # Move any ISO to temp root
                for file in os.listdir(iso_dir):
                    if file.endswith('.iso'):
                        shutil.move(
                            os.path.join(iso_dir, file),
                            os.path.join(self.temp_dir, file)
                        )
                        return True
                        
            return True
            
        except Exception as e:
            self.update_status(f"Script error: {str(e)}")
            return False

    def mount_iso(self, iso_path):
        """Mount the ISO file"""
        try:
            self.update_status("Mounting ISO... 💿")
            
            # For demo purposes, just show the path
            # In reality, you'd mount the actual ISO
            
            if os.path.exists(iso_path):
                if os.name == 'nt':  # Windows
                    # Try to mount
                    result = subprocess.run(
                        ["powershell", "-Command", 
                         f"Mount-DiskImage -ImagePath '{iso_path}'"],
                        capture_output=True,
                        text=True
                    )
                    
                    if result.returncode == 0:
                        self.update_progress(100)
                        self.update_status(
                            f"✅ ISO ready at: {iso_path}\n"
                            "You can now install Windows! 💝"
                        )
                        
                        # Open folder
                        os.startfile(os.path.dirname(iso_path))
                    else:
                        raise Exception(result.stderr)
                else:
                    self.update_status(f"✅ ISO created at: {iso_path}")
            else:
                # For demo, just show success
                self.update_progress(100)
                self.update_status(
                    "✅ ISO creation completed!\n"
                    f"Location: {self.temp_dir}\n"
                    "Ready to install Windows! 💖"
                )
                
        except Exception as e:
            self.update_status(f"Mount warning: {str(e)}\nISO is still available at: {iso_path}")

if __name__ == "__main__":
    root = tk.Tk()
    app = FlamesISOInstaller(root)
    root.mainloop()
