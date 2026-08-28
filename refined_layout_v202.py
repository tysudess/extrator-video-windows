import atexit
import ctypes
import os
import subprocess
import sys
import tempfile
from ctypes import wintypes
from pathlib import Path

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QApplication, QGroupBox, QHBoxLayout, QLabel, QMessageBox, QPushButton, QVBoxLayout
)

import refined_layout_v201 as v201

APP_VERSION = 'Windows Portable v2.0.2 — Sessão Globoplay Persistente + Evolução Consolidada'
SIDEBAR_VERSION = 'v2.0.2  •  SESSÃO GLOBOPLAY PERSISTENTE'

SESSION_DIR = Path(os.environ.get('APPDATA') or Path.home()) / 'ExtratorVideos' / 'secure'
SESSION_BLOB = SESSION_DIR / 'globoplay-session.dpapi'
TEMP_DIR = Path(tempfile.gettempdir()) / 'ExtratorVideos'
TEMP_COOKIE_FILE = TEMP_DIR / 'globoplay-session.txt'


class DATA_BLOB(ctypes.Structure):
    _fields_ = [
        ('cbData', wintypes.DWORD),
        ('pbData', ctypes.POINTER(ctypes.c_ubyte)),
    ]


def _protect_bytes(data):
    if os.name != 'nt':
        raise RuntimeError('A proteção segura desta versão requer Windows.')
    raw = bytes(data or b'')
    if not raw:
        return b''
    buf = ctypes.create_string_buffer(raw)
    in_blob = DATA_BLOB(len(raw), ctypes.cast(buf, ctypes.POINTER(ctypes.c_ubyte)))
    out_blob = DATA_BLOB()
    ok = ctypes.windll.crypt32.CryptProtectData(
        ctypes.byref(in_blob),
        'ExtratorVideos Globoplay Session',
        None,
        None,
        None,
        0x01,
        ctypes.byref(out_blob),
    )
    if not ok:
        raise ctypes.WinError()
    try:
        return ctypes.string_at(out_blob.pbData, out_blob.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(out_blob.pbData)


def _unprotect_bytes(data):
    if os.name != 'nt':
        raise RuntimeError('A proteção segura desta versão requer Windows.')
    raw = bytes(data or b'')
    if not raw:
        return b''
    buf = ctypes.create_string_buffer(raw)
    in_blob = DATA_BLOB(len(raw), ctypes.cast(buf, ctypes.POINTER(ctypes.c_ubyte)))
    out_blob = DATA_BLOB()
    ok = ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(in_blob),
        None,
        None,
        None,
        None,
        0x01,
        ctypes.byref(out_blob),
    )
    if not ok:
        raise ctypes.WinError()
    try:
        return ctypes.string_at(out_blob.pbData, out_blob.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(out_blob.pbData)


def _looks_like_cookie_jar(data):
    try:
        text = bytes(data or b'').decode('utf-8', 'ignore').lower()
    except Exception:
        return False
    return (
        '# netscape http cookie file' in text
        and ('globo.com' in text or 'globoplay' in text)
    )


def _save_secure_session(raw_cookie_bytes):
    raw = bytes(raw_cookie_bytes or b'')
    if not _looks_like_cookie_jar(raw):
        raise RuntimeError('A sessão capturada não contém cookies válidos do Globoplay/Globo.')
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    protected = _protect_bytes(raw)
    tmp = SESSION_BLOB.with_suffix('.tmp')
    tmp.write_bytes(protected)
    tmp.replace(SESSION_BLOB)


def _load_secure_session():
    if not SESSION_BLOB.exists():
        return b''
    try:
        raw = _unprotect_bytes(SESSION_BLOB.read_bytes())
    except Exception:
        return b''
    return raw if _looks_like_cookie_jar(raw) else b''


def _secure_session_exists():
    return bool(_load_secure_session())


def _write_runtime_cookie_file():
    raw = _load_secure_session()
    if not raw:
        return None
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    TEMP_COOKIE_FILE.write_bytes(raw)
    return TEMP_COOKIE_FILE


def _persist_runtime_cookie_file():
    try:
        if TEMP_COOKIE_FILE.exists():
            raw = TEMP_COOKIE_FILE.read_bytes()
            if _looks_like_cookie_jar(raw):
                _save_secure_session(raw)
    except Exception:
        pass
    finally:
        try:
            TEMP_COOKIE_FILE.unlink(missing_ok=True)
        except Exception:
            pass


def _delete_secure_session():
    try:
        SESSION_BLOB.unlink(missing_ok=True)
    except Exception:
        pass
    try:
        TEMP_COOKIE_FILE.unlink(missing_ok=True)
    except Exception:
        pass


_original_cookie_args = v201._globoplay_cookie_args


def _globoplay_cookie_args_v202(url):
    if not v201._is_globoplay_url(url):
        return []
    runtime = _write_runtime_cookie_file()
    if runtime:
        return ['--cookies', str(runtime)]
    return _original_cookie_args(url)


v201._globoplay_cookie_args = _globoplay_cookie_args_v202


class SessionCaptureWorker(QThread):
    done = Signal(str)
    failed = Signal(str)

    def __init__(self, url, browser, proxy_url=''):
        super().__init__()
        self.url = str(url or '').strip()
        self.browser = str(browser or '').strip().lower()
        self.proxy_url = str(proxy_url or '')

    def run(self):
        capture_file = None
        try:
            if not v201._is_globoplay_url(self.url):
                raise RuntimeError('Cole primeiro um link de vídeo do Globoplay na tela Download.')
            if not self.browser:
                raise RuntimeError('Não foi possível identificar o navegador usado no login do Globoplay.')
            if not v201.base.core.YTDLP_EXE.exists():
                raise RuntimeError('yt-dlp.exe não encontrado na pasta bin.')

            TEMP_DIR.mkdir(parents=True, exist_ok=True)
            fd, path = tempfile.mkstemp(
                prefix='globoplay-capture-', suffix='.txt', dir=str(TEMP_DIR)
            )
            os.close(fd)
            capture_file = Path(path)

            cmd = [
                str(v201.base.core.YTDLP_EXE), '--no-playlist', '--skip-download',
                '--dump-single-json', '--socket-timeout', '25',
                '--ffmpeg-location', str(v201.base.core.BIN_DIR),
                '--cookies-from-browser', self.browser,
                '--cookies', str(capture_file),
            ]
            if self.proxy_url:
                cmd += ['--proxy', self.proxy_url]
            cmd.append(self.url)

            flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            result = subprocess.run(
                cmd, capture_output=True, text=True, encoding='utf-8', errors='replace',
                creationflags=flags, timeout=120,
            )

            raw = capture_file.read_bytes() if capture_file.exists() else b''
            if _looks_like_cookie_jar(raw):
                _save_secure_session(raw)
                _write_runtime_cookie_file()
                self.done.emit(self.browser)
                return

            output = (result.stderr or result.stdout or '').lower()
            if any(k in output for k in (
                'could not copy chrome cookie database', 'could not copy cookie database',
                'failed to decrypt with dpapi', 'failed to decrypt cookies',
            )):
                raise RuntimeError(
                    'O navegador bloqueou a leitura dos cookies. Feche completamente o navegador '
                    'e clique novamente em Salvar sessão autenticada.'
                )
            raise RuntimeError(
                'Não foi possível capturar a sessão autenticada. Confirme o login no Globoplay '
                'e tente novamente com o navegador fechado.'
            )
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            try:
                if capture_file:
                    capture_file.unlink(missing_ok=True)
            except Exception:
                pass


_original_build_ui = v201._build_refined_ui_v201


def _build_refined_ui_v202(self):
    _original_build_ui(self)
    try:
        settings_scroll = self.ref_stack.widget(3)
        settings_page = settings_scroll.widget()
        layout = settings_page.layout()

        box = QGroupBox('Globoplay — sessão persistente protegida pelo Windows')
        col = QVBoxLayout(box)

        info = QLabel(
            'Depois de fazer login no Globoplay, salve a sessão autenticada uma vez. '
            'Ela fica criptografada para este usuário do Windows e passa a ser usada '
            'pelo ANALISAR e BAIXAR, evitando depender da leitura do navegador em cada tentativa.'
        )
        info.setWordWrap(True)
        info.setObjectName('RefinedText')
        col.addWidget(info)

        self.globoplay_secure_status = QLabel()
        self.globoplay_secure_status.setObjectName('RefinedText')
        col.addWidget(self.globoplay_secure_status)

        def refresh_status():
            if _secure_session_exists():
                self.globoplay_secure_status.setText(
                    'Sessão autenticada: SALVA E PROTEGIDA pelo Windows (DPAPI)'
                )
            else:
                self.globoplay_secure_status.setText('Sessão autenticada: ainda não salva')

        refresh_status()

        actions = QHBoxLayout()
        self.btn_globoplay_capture_session = QPushButton('Salvar sessão autenticada')
        self.btn_globoplay_capture_session.setObjectName('RefinedPrimary')
        self.btn_globoplay_forget_session = QPushButton('Apagar sessão salva')
        self.btn_globoplay_forget_session.setObjectName('RefinedGhost')
        actions.addWidget(self.btn_globoplay_capture_session)
        actions.addWidget(self.btn_globoplay_forget_session)
        actions.addStretch(1)
        col.addLayout(actions)

        note = QLabel(
            'Fluxo recomendado: Entrar / atualizar sessão Globoplay → concluir o login no navegador '
            '→ colar o link do vídeo → Salvar sessão autenticada. O downloader realmente utiliza '
            'a sessão/cookies autenticados; DRM e conteúdos sem autorização continuam bloqueados.'
        )
        note.setWordWrap(True)
        note.setObjectName('RefinedMuted')
        col.addWidget(note)

        def capture_session():
            if getattr(self, 'globoplay_capture_worker', None) and self.globoplay_capture_worker.isRunning():
                return
            url = self.url_edit.text().strip()
            if not v201._is_globoplay_url(url):
                QMessageBox.information(
                    self, v201.base.core.APP_NAME,
                    'Cole primeiro, na tela Download, o link de um vídeo do Globoplay que sua conta tenha acesso.'
                )
                return
            browser = v201._globoplay_browser()
            if not browser:
                QMessageBox.warning(
                    self, v201.base.core.APP_NAME,
                    'Não foi possível identificar o navegador usado no login do Globoplay.'
                )
                return
            proxy = self._current_proxy_url(True)
            if proxy is None:
                return

            self.btn_globoplay_capture_session.setEnabled(False)
            self.btn_globoplay_capture_session.setText('SALVANDO SESSÃO…')
            self.globoplay_capture_worker = SessionCaptureWorker(url, browser, proxy)

            def capture_done(_used_browser):
                self.btn_globoplay_capture_session.setEnabled(True)
                self.btn_globoplay_capture_session.setText('Salvar sessão autenticada')
                refresh_status()
                QMessageBox.information(
                    self, v201.base.core.APP_NAME,
                    'Sessão do Globoplay salva com sucesso e protegida pelo Windows.\n\n'
                    'A partir de agora, ANALISAR e BAIXAR usarão essa sessão persistente '
                    'sem precisar reler os cookies do navegador a cada download.'
                )

            def capture_failed(message):
                self.btn_globoplay_capture_session.setEnabled(True)
                self.btn_globoplay_capture_session.setText('Salvar sessão autenticada')
                refresh_status()
                QMessageBox.warning(
                    self, v201.base.core.APP_NAME,
                    'Não foi possível salvar a sessão do Globoplay.\n\n' + str(message)
                )

            self.globoplay_capture_worker.done.connect(capture_done)
            self.globoplay_capture_worker.failed.connect(capture_failed)
            self.globoplay_capture_worker.start()

        def forget_session():
            _delete_secure_session()
            refresh_status()
            QMessageBox.information(
                self, v201.base.core.APP_NAME,
                'A sessão persistente do Globoplay foi apagada deste computador.'
            )

        self.btn_globoplay_capture_session.clicked.connect(capture_session)
        self.btn_globoplay_forget_session.clicked.connect(forget_session)
        layout.insertWidget(max(0, layout.count() - 1), box)
    except Exception:
        pass


v201.base.build_refined_ui = _build_refined_ui_v202
v201.base.core.MainWindow._build_ui = _build_refined_ui_v202
v201.base.core.APP_VERSION = APP_VERSION


def main():
    v201.base.core.APP_VERSION = APP_VERSION
    app = QApplication(sys.argv)
    app.setApplicationName(v201.base.core.APP_NAME)
    app.setOrganizationName('ExtratorVideos')
    app.setStyle('Fusion')
    app.setStyleSheet(v201.base.core.FUTURE_STYLESHEET)
    app.setWindowIcon(v201.base._app_icon())
    app.aboutToQuit.connect(_persist_runtime_cookie_file)

    window = v201.base.core.MainWindow()
    window.setWindowIcon(v201.base._app_icon())
    for label in window.findChildren(QLabel):
        if label.objectName() == 'RefinedVersion':
            label.setText(SIDEBAR_VERSION)
            break

    window.show()
    sys.exit(app.exec())


atexit.register(_persist_runtime_cookie_file)


if __name__ == '__main__':
    main()
