import os
import shutil
import sys
import time
import configparser
import argparse
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QFileDialog, QLineEdit, QMessageBox
from PyQt5.QtCore import QThread, pyqtSignal
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

CONFIG_FILE = "file_sorter_config.ini"

class FileSorterThread(QThread):
    folder_updated = pyqtSignal(str)

    def __init__(self, downloads_path):
        super().__init__()
        self.downloads_path = downloads_path
        self.folders = {
            "PDFs": os.path.join(downloads_path, "PDFs"),
            "Images": os.path.join(downloads_path, "Images"),
            "Software": os.path.join(downloads_path, "Software"),
            "Documents": os.path.join(downloads_path, "Documents"),
            "Audio": os.path.join(downloads_path, "Audio"),
            "Video": os.path.join(downloads_path, "Video"),
            "Archives": os.path.join(downloads_path, "Archives"),
            "Others": os.path.join(downloads_path, "Others")
        }
        self.observer = Observer()
        self.event_handler = DownloadEventHandler(self.folders, self.folder_updated)

    def run(self):
        for folder in self.folders.values():
            os.makedirs(folder, exist_ok=True)
        self.observer.schedule(self.event_handler, self.downloads_path, recursive=False)
        self.observer.start()
        print(f"Started observer on {self.downloads_path}")
        self.exec_()

    def stop(self):
        self.observer.stop()
        self.observer.join()
        print("Observer stopped")

class DownloadEventHandler(FileSystemEventHandler):
    def __init__(self, folders, folder_updated_signal):
        super().__init__()
        self.folders = folders
        self.folder_updated_signal = folder_updated_signal

    def on_created(self, event):
        if event.is_directory:
            return
        print(f"File created: {event.src_path}")
        # Check if it's a temp file
        if event.src_path.endswith('.tmp'):
            print(f"Skipping temp file: {event.src_path}")
            return
        # Wait for the file to be fully downloaded
        time.sleep(2)
        self.move_file(event.src_path)

    def move_file(self, src_path):
        try:
            ext = os.path.splitext(src_path)[1].lower()
            if ext in ['.pdf']:
                shutil.move(src_path, self.folders["PDFs"])
                self.folder_updated_signal.emit("PDFs")
                print(f"Moved {src_path} to PDFs folder")
            elif ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif', '.raw', '.cr2', '.nef', '.orf', '.sr2']:
                shutil.move(src_path, self.folders["Images"])
                self.folder_updated_signal.emit("Images")
                print(f"Moved {src_path} to Images folder")
            elif ext in ['.exe', '.msi', '.bat', '.sh', '.py', '.js']:
                shutil.move(src_path, self.folders["Software"])
                self.folder_updated_signal.emit("Software")
                print(f"Moved {src_path} to Software folder")
            elif ext in ['.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt', '.rtf', '.odt']:
                shutil.move(src_path, self.folders["Documents"])
                self.folder_updated_signal.emit("Documents")
                print(f"Moved {src_path} to Documents folder")
            elif ext in ['.mp3', '.wav', '.aac', '.flac', '.ogg', '.m4a']:
                shutil.move(src_path, self.folders["Audio"])
                self.folder_updated_signal.emit("Audio")
                print(f"Moved {src_path} to Audio folder")
            elif ext in ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.mpg', '.mpeg']:
                shutil.move(src_path, self.folders["Video"])
                self.folder_updated_signal.emit("Video")
                print(f"Moved {src_path} to Video folder")
            elif ext in ['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2']:
                shutil.move(src_path, self.folders["Archives"])
                self.folder_updated_signal.emit("Archives")
                print(f"Moved {src_path} to Archives folder")
            else:
                shutil.move(src_path, self.folders["Others"])
                self.folder_updated_signal.emit("Others")
                print(f"Moved {src_path} to Others folder")
        except Exception as e:
            print(f"Error moving file {src_path}: {e}")

class FileSorterApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.load_config()
        self.file_sorter_thread = None

    def initUI(self):
        self.setWindowTitle('File Sorter')
        self.setGeometry(100, 100, 500, 200)
        
        layout = QVBoxLayout()

        self.label = QLabel("Downloads Folder:")
        layout.addWidget(self.label)
        
        self.downloads_folder_input = QLineEdit(self)
        layout.addWidget(self.downloads_folder_input)
        
        self.browse_button = QPushButton("Browse", self)
        self.browse_button.clicked.connect(self.browse_folder)
        layout.addWidget(self.browse_button)
        
        self.start_button = QPushButton("Start Sorting", self)
        self.start_button.clicked.connect(self.start_sorting)
        layout.addWidget(self.start_button)
        
        self.stop_button = QPushButton("Stop Sorting", self)
        self.stop_button.clicked.connect(self.stop_sorting)
        layout.addWidget(self.stop_button)
        
        self.status_label = QLabel("")
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)

    def load_config(self):
        config = configparser.ConfigParser()
        if os.path.exists(CONFIG_FILE):
            config.read(CONFIG_FILE)
            if 'Settings' in config and 'downloads_folder' in config['Settings']:
                self.downloads_folder_input.setText(config['Settings']['downloads_folder'])

    def save_config(self):
        config = configparser.ConfigParser()
        config['Settings'] = {'downloads_folder': self.downloads_folder_input.text()}
        with open(CONFIG_FILE, 'w') as configfile:
            config.write(configfile)

    def browse_folder(self):
        folder_selected = QFileDialog.getExistingDirectory(self, "Select Downloads Folder")
        if folder_selected:
            self.downloads_folder_input.setText(folder_selected)
            self.save_config()

    def start_sorting(self):
        downloads_path = self.downloads_folder_input.text()
        if not downloads_path:
            QMessageBox.critical(self, "Error", "Please select a downloads folder.")
            return
        
        self.file_sorter_thread = FileSorterThread(downloads_path)
        self.file_sorter_thread.folder_updated.connect(self.update_status)
        self.file_sorter_thread.start()
        
        self.status_label.setText("File sorting started...")

    def stop_sorting(self):
        if self.file_sorter_thread:
            self.file_sorter_thread.stop()
            self.file_sorter_thread = None
            self.status_label.setText("File sorting stopped.")

    def update_status(self, folder):
        self.status_label.setText(f"File moved to {folder} folder")

def run_silent_mode():
    config = configparser.ConfigParser()
    if os.path.exists(CONFIG_FILE):
        config.read(CONFIG_FILE)
        if 'Settings' in config and 'downloads_folder' in config['Settings']:
            downloads_path = config['Settings']['downloads_folder']
            file_sorter_thread = FileSorterThread(downloads_path)
            file_sorter_thread.start()
            file_sorter_thread.exec_()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--silent", action="store_true", help="Run in silent mode without UI")
    args = parser.parse_args()

    if args.silent:
        run_silent_mode()
    else:
        app = QApplication(sys.argv)
        ex = FileSorterApp()
        ex.show()
        sys.exit(app.exec_())
