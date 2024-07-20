import os
import shutil
import sys
import tkinter as tk
from tkinter import filedialog
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from PIL import Image
import subprocess
from collections import deque
import configparser

CONFIG_FILE = "config.ini"
if hasattr(sys, '_MEIPASS'):
    ICON_PATH = os.path.join(sys._MEIPASS, 'eye.ico')
else:
    ICON_PATH = 'eye.ico'

class FileChangeHandler(FileSystemEventHandler):
    def __init__(self, src_folder, dest_folder, log_callback, log_size=10):
        self.src_folder = src_folder
        self.dest_folder = dest_folder
        self.log_callback = log_callback
        self.recent_files = deque(maxlen=log_size)

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
        self.recent_files.appendleft(file_path)
        self.log_callback(self.recent_files)

def start_watcher(src_folder, dest_folder, log_callback, log_size):
    event_handler = FileChangeHandler(src_folder, dest_folder, log_callback, log_size)
    observer = Observer()
    observer.schedule(event_handler, path=src_folder, recursive=True)
    observer.start()
    return observer

class Application(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Project Watcher Setup")
        self.geometry("500x450")
        self.minsize(500, 450)
        self.iconbitmap(ICON_PATH)  # Set the window icon

        self.src_folder = tk.StringVar()
        self.dest_folder = tk.StringVar()
        self.log_size = tk.IntVar(value=10)
        self.observer = None

        self.load_config()
        
        self.create_widgets()

    def create_widgets(self):
        self.border_frame = tk.Frame(self, highlightbackground="white", highlightcolor="white", highlightthickness=5)
        self.border_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        frame = tk.Frame(self.border_frame)
        frame.pack(pady=10, padx=10, anchor='w', fill=tk.X, expand=True)

        tk.Label(frame, text="Source Folder:").grid(row=0, column=0, sticky='w')
        self.src_entry = tk.Entry(frame, textvariable=self.src_folder)
        self.src_entry.grid(row=0, column=1, padx=5, sticky='ew')
        tk.Button(frame, text="Browse", command=self.browse_src_folder).grid(row=0, column=2)

        tk.Label(frame, text="Destination Folder:").grid(row=1, column=0, sticky='w')
        self.dest_entry = tk.Entry(frame, textvariable=self.dest_folder)
        self.dest_entry.grid(row=1, column=1, padx=5, sticky='ew')
        tk.Button(frame, text="Browse", command=self.browse_dest_folder).grid(row=1, column=2)

        tk.Label(frame, text="Log Size:").grid(row=2, column=0, sticky='w')
        tk.Entry(frame, textvariable=self.log_size, width=5).grid(row=2, column=1, padx=5, sticky='w')

        self.watch_button = tk.Button(frame, text="Start Watching", command=self.toggle_watching)
        self.watch_button.grid(row=3, column=0, pady=10, sticky='w')

        self.resync_button = tk.Button(frame, text="Resync", command=self.resync)
        self.resync_button.grid(row=3, column=1, pady=10, sticky='w')

        frame.grid_columnconfigure(1, weight=1)

        self.log_text = tk.Text(self.border_frame, state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True, pady=5, padx=10)

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
        log_size = self.log_size.get()
        if src and dest:
            self.observer = start_watcher(src, dest, self.update_log, log_size)
            self.save_config()
            self.watch_button.config(text="Stop Watching")
            self.border_frame.config(highlightbackground="red", highlightcolor="red")
        else:
            tk.Label(self, text="Please select both source and destination folders.").pack(pady=5)

    def stop_watching(self):
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.observer = None
            self.watch_button.config(text="Start Watching")
            self.border_frame.config(highlightbackground="white", highlightcolor="white")

    def update_log(self, recent_files):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.insert(tk.END, "\n".join(recent_files))
        self.log_text.config(state=tk.DISABLED)

    def load_config(self):
        config = configparser.ConfigParser()
        if os.path.exists(CONFIG_FILE):
            config.read(CONFIG_FILE)
            self.src_folder.set(config.get("Folders", "src_folder", fallback=""))
            self.dest_folder.set(config.get("Folders", "dest_folder", fallback=""))
            self.log_size.set(config.getint("Settings", "log_size", fallback=10))
    
    def save_config(self):
        config = configparser.ConfigParser()
        config['Folders'] = {
            'src_folder': self.src_folder.get(),
            'dest_folder': self.dest_folder.get()
        }
        config['Settings'] = {
            'log_size': self.log_size.get()
        }
        with open(CONFIG_FILE, 'w') as configfile:
            config.write(configfile)

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

    def log_file_change(self, file_path):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, file_path + "\n")
        self.log_text.config(state=tk.DISABLED)

if __name__ == "__main__":
    app = Application()
    app.mainloop()
