import os
import shutil
import sys
import tkinter as tk
from tkinter import filedialog, scrolledtext
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from PIL import Image
import subprocess
import configparser

CONFIG_FILE = "config.ini"
LOG_FILE = "log.txt"

def get_app_data_path():
    if sys.platform == "win32":
        return os.getenv("APPDATA")
    elif sys.platform == "darwin":
        return os.path.expanduser("~/Library/Application Support")
    else:
        return os.path.expanduser("~/.local/share")

APP_DATA_DIR = os.path.join(get_app_data_path(), "MayaPSDUnity")
if not os.path.exists(APP_DATA_DIR):
    os.makedirs(APP_DATA_DIR)

CONFIG_FILE_PATH = os.path.join(APP_DATA_DIR, CONFIG_FILE)
LOG_FILE_PATH = os.path.join(APP_DATA_DIR, LOG_FILE)

if hasattr(sys, '_MEIPASS'):
    ICON_PATH = os.path.join(sys._MEIPASS, 'eye.ico')
else:
    ICON_PATH = 'eye.ico'

class FileChangeHandler(FileSystemEventHandler):
    def __init__(self, src_folder, dest_folder, log_callback):
        self.src_folder = src_folder
        self.dest_folder = dest_folder
        self.log_callback = log_callback

    def on_modified(self, event):
        if event.src_path.endswith(".psd"):
            self.convert_and_sync_texture(event.src_path)
        elif event.src_path.endswith(".ma"):
            self.convert_and_sync_model(event.src_path)

    def convert_and_sync_texture(self, src_path):
        relative_path = os.path.relpath(src_path, self.src_folder)
        dest_path = os.path.join(self.dest_folder, relative_path)
        dest_dir = os.path.dirname(dest_path)
        
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)
        
        base_name = os.path.basename(src_path)
        name, _ = os.path.splitext(base_name)
        tga_name = name + ".tga"
        
        # Convert PSD to TGA
        im = Image.open(src_path)
        tga_src_path = os.path.join(os.path.dirname(src_path), tga_name)
        tga_dest_path = os.path.join(dest_dir, tga_name)
        im.save(tga_src_path, format='TGA')
        shutil.copy(tga_src_path, tga_dest_path)

        # Log the file change
        self.log_file_change(tga_src_path)

    def convert_and_sync_model(self, src_path):
        relative_path = os.path.relpath(src_path, self.src_folder)
        dest_path = os.path.join(self.dest_folder, relative_path)
        dest_dir = os.path.dirname(dest_path)
        
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)
        
        base_name = os.path.basename(src_path)
        name, _ = os.path.splitext(base_name)
        fbx_name = name + ".fbx"
        
        # Path to the Maya script for conversion
        maya_script_path = "path/to/your/maya_fbx_export.py"
        
        # Run Maya to export .ma to .fbx
        fbx_src_path = os.path.join(os.path.dirname(src_path), fbx_name)
        fbx_dest_path = os.path.join(dest_dir, fbx_name)
        subprocess.call(['mayapy', maya_script_path, src_path, fbx_src_path])
        shutil.copy(fbx_src_path, fbx_dest_path)

        # Log the file change
        self.log_file_change(fbx_src_path)

    def log_file_change(self, file_path):
        self.log_callback(file_path)

def start_watcher(src_folder, dest_folder, log_callback):
    event_handler = FileChangeHandler(src_folder, dest_folder, log_callback)
    observer = Observer()
    observer.schedule(event_handler, path=src_folder, recursive=True)
    observer.start()
    return observer

class Application(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MayaPSDUnity")
        self.geometry("600x450")
        self.minsize(500, 450)
        self.iconbitmap(ICON_PATH)  # Set the window icon

        self.src_folder = tk.StringVar()
        self.dest_folder = tk.StringVar()
        self.observer = None

        self.load_config()
        
        self.create_widgets()

    def create_widgets(self):
        self.border_frame = tk.Frame(self, highlightbackground="white", highlightcolor="white", highlightthickness=5)
        self.border_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        top_frame = tk.Frame(self.border_frame)
        top_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(top_frame, text="Source Folder:").grid(row=0, column=0, sticky='w')
        self.src_entry = tk.Entry(top_frame, textvariable=self.src_folder)
        self.src_entry.grid(row=0, column=1, padx=5, sticky='ew')
        tk.Button(top_frame, text="Browse", command=self.browse_src_folder).grid(row=0, column=2)

        tk.Label(top_frame, text="Destination Folder:").grid(row=1, column=0, sticky='w')
        self.dest_entry = tk.Entry(top_frame, textvariable=self.dest_folder)
        self.dest_entry.grid(row=1, column=1, padx=5, sticky='ew')
        tk.Button(top_frame, text="Browse", command=self.browse_dest_folder).grid(row=1, column=2)

        self.watch_button = tk.Button(top_frame, text="Start Watching", command=self.toggle_watching)
        self.watch_button.grid(row=2, column=0, pady=10, sticky='w')

        self.resync_button = tk.Button(top_frame, text="Resync", command=self.resync)
        self.resync_button.grid(row=2, column=1, pady=10, sticky='w')

        self.error_label = tk.Label(self.border_frame, text="", fg="red")
        self.error_label.pack(pady=5)

        top_frame.grid_columnconfigure(1, weight=1)

        log_frame = tk.Frame(self.border_frame)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.log_text = scrolledtext.ScrolledText(log_frame, state=tk.DISABLED, height=10)
        self.log_text.pack(fill=tk.BOTH, expand=True)

        button_frame = tk.Frame(self.border_frame)
        button_frame.pack(fill=tk.X, padx=10, pady=5)

        self.clear_log_button = tk.Button(button_frame, text="Clear Log", command=self.clear_log)
        self.clear_log_button.pack(side=tk.RIGHT)

        self.load_log()

    def browse_src_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.src_folder.set(folder)
    
    def browse_dest_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.dest_folder.set(folder)
    
    def toggle_watching(self):
        if self.observer:
            self.stop_watching()
        else:
            self.start_watching()
    
    def start_watching(self):
        src = self.src_folder.get()
        dest = self.dest_folder.get()
        if src and dest:
            self.observer = start_watcher(src, dest, self.log_file_change)
            self.save_config()
            self.watch_button.config(text="Stop Watching")
            self.border_frame.config(highlightbackground="red", highlightcolor="red")
        else:
            self.error_label.config(text="Please select both source and destination folders.")
            self.after(3000, self.clear_error_label)  # Clear the error message after 3 seconds

    def stop_watching(self):
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.observer = None
            self.watch_button.config(text="Start Watching")
            self.border_frame.config(highlightbackground="white", highlightcolor="white")

    def clear_error_label(self):
        self.error_label.config(text="")

    def log_file_change(self, file_path):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, file_path + "\n")
        self.log_text.config(state=tk.DISABLED)
        self.save_log()

    def clear_log(self):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.save_log()

    def load_config(self):
        config = configparser.ConfigParser()
        if os.path.exists(CONFIG_FILE_PATH):
            config.read(CONFIG_FILE_PATH)
            self.src_folder.set(config.get("Folders", "src_folder", fallback=""))
            self.dest_folder.set(config.get("Folders", "dest_folder", fallback=""))
    
    def save_config(self):
        config = configparser.ConfigParser()
        config['Folders'] = {
            'src_folder': self.src_folder.get(),
            'dest_folder': self.dest_folder.get()
        }
        with open(CONFIG_FILE_PATH, 'w') as configfile:
            config.write(configfile)

    def load_log(self):
        if os.path.exists(LOG_FILE_PATH):
            with open(LOG_FILE_PATH, 'r') as log_file:
                log_content = log_file.read()
                self.log_text.config(state=tk.NORMAL)
                self.log_text.insert(tk.END, log_content)
                self.log_text.config(state=tk.DISABLED)

    def save_log(self):
        with open(LOG_FILE_PATH, 'w') as log_file:
            log_file.write(self.log_text.get(1.0, tk.END))

    def resync(self):
        src = self.src_folder.get()
        dest = self.dest_folder.get()
        if src and dest:
            for root, dirs, files in os.walk(src):
                for file in files:
                    file_path = os.path.join(root, file)
                    if file_path.endswith(".psd"):
                        self.convert_and_sync_texture(file_path)
                    elif file_path.endswith(".ma"):
                        self.convert_and_sync_model(file_path)

    def convert_and_sync_texture(self, src_path):
        relative_path = os.path.relpath(src_path, self.src_folder.get())
        dest_path = os.path.join(self.dest_folder.get(), relative_path)
        dest_dir = os.path.dirname(dest_path)
        
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)
        
        base_name = os.path.basename(src_path)
        name, _ = os.path.splitext(base_name)
        tga_name = name + ".tga"
        
        # Convert PSD to TGA
        im = Image.open(src_path)
        tga_src_path = os.path.join(os.path.dirname(src_path), tga_name)
        tga_dest_path = os.path.join(dest_dir, tga_name)
        im.save(tga_src_path, format='TGA')
        shutil.copy(tga_src_path, tga_dest_path)

        # Log the file change
        self.log_file_change(tga_src_path)

    def convert_and_sync_model(self, src_path):
        relative_path = os.path.relpath(src_path, self.src_folder.get())
        dest_path = os.path.join(self.dest_folder.get(), relative_path)
        dest_dir = os.path.dirname(dest_path)
        
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)
        
        base_name = os.path.basename(src_path)
        name, _ = os.path.splitext(base_name)
        fbx_name = name + ".fbx"
        
        # Path to the Maya script for conversion
        maya_script_path = "path/to/your/maya_fbx_export.py"
        
        # Run Maya to export .ma to .fbx
        fbx_src_path = os.path.join(os.path.dirname(src_path), fbx_name)
        fbx_dest_path = os.path.join(dest_dir, fbx_name)
        subprocess.call(['mayapy', maya_script_path, src_path, fbx_src_path])
        shutil.copy(fbx_src_path, fbx_dest_path)

        # Log the file change
        self.log_file_change(fbx_src_path)

if __name__ == "__main__":
    app = Application()
    app.mainloop()
