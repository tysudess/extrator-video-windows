import os
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMainWindow, QScrollArea

from advanced_editor_v300 import AdvancedVideoEditorWidget300


APP_NAME = 'Editor de Vídeo'
APP_VERSION = 'v3.0.1 Split — Editor'


def _base_dir():
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _paths():
    base = _base_dir()
    videos = base / 'Videos'
    videos.mkdir(parents=True, exist_ok=True)
    ffmpeg = base / 'bin' / ('ffmpeg.exe' if os.name == 'nt' else 'ffmpeg')
    ffprobe = base / 'bin' / ('ffprobe.exe' if os.name == 'nt' else 'ffprobe')
    return videos, ffmpeg, ffprobe


class EditorWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        videos, ffmpeg, ffprobe = _paths()
        self.setWindowTitle(f'{APP_NAME} — {APP_VERSION}')
        self.resize(1260, 860)
        self.setMinimumSize(900, 650)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        self.editor_page = AdvancedVideoEditorWidget300(videos, ffmpeg, ffprobe, self)
        scroll.setWidget(self.editor_page)
        self.setCentralWidget(scroll)

    def closeEvent(self, event):
        try:
            self.editor_page.shutdown()
        except Exception:
            pass
        super().closeEvent(event)


def main():
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    window = EditorWindow()
    window.show()
    return app.exec()


if __name__ == '__main__':
    raise SystemExit(main())
