import html
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QThread, QTimer, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QApplication, QComboBox, QFileDialog, QFormLayout, QGridLayout, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox, QProgressBar,
    QPushButton, QRadioButton, QScrollArea, QTabWidget, QVBoxLayout, QWidget,
    QListWidget,
)

from range_slider import RangeSlider
from advanced_editor import AdvancedVideoEditorWidget

APP_NAME = 'Extrator de Vídeos'
APP_VERSION = 'Windows Portable v1.9.18 — Refino Visual Etapa 2 — Editor/Timeline'

# A ordem precisa ser exatamente a mesma exibida no layout refinado.
# Isso evita que 720p solicite 1080p (ou outra qualidade) por engano.
QUALIDADES = ('2160p (4K)', '1440p (2K)', '1080p Full HD', '720p HD', '480p', '360p')
FORMATS = (
    'bv*[height<=2160]+ba/b[height<=2160]/b',
    'bv*[height<=1440]+ba/b[height<=1440]/b',
    'bv*[height<=1080]+ba/b[height<=1080]/b',
    'bv*[height<=720]+ba/b[height<=720]/b',
    'bv*[height<=480]+ba/b[height<=480]/b',
    'bv*[height<=360]+ba/b[height<=360]/b',
)
COMPAT_FORMATS = (
    'b[height<=2160]/b',
    'b[height<=1440]/b',
    'b[height<=1080]/b',
    'b[height<=720]/b',
    'b[height<=480]/b',
    'b[height<=360]/b',
)


FUTURE_STYLESHEET = r"""
QWidget {
    background-color: #0b0f17;
    color: #e8eef8;
    font-family: "Segoe UI";
    font-size: 10pt;
}
QMainWindow, QScrollArea, QScrollArea > QWidget > QWidget {
    background-color: #0b0f17;
}
QScrollArea { border: none; }
QLabel#AppTitle, QLabel#EditorTitle, QLabel#PageTitle {
    color: #f7fbff;
    font-size: 20pt;
    font-weight: 700;
}
QLabel#Subtitle {
    color: #94a3b8;
    font-size: 10pt;
}
QLabel#StatusBadge {
    background-color: #0f2d3e;
    color: #67e8f9;
    border: 1px solid #155e75;
    border-radius: 10px;
    padding: 5px 10px;
    font-weight: 600;
}
QLabel#InfoBanner {
    background-color: #101827;
    color: #b9c6d8;
    border: 1px solid #223149;
    border-left: 3px solid #22d3ee;
    border-radius: 9px;
    padding: 10px 12px;
}
QLabel#MetricCard {
    background-color: #101827;
    color: #e8eef8;
    border: 1px solid #223149;
    border-radius: 12px;
    padding: 10px 14px;
    font-size: 10pt;
    font-weight: 600;
}
QLabel#MetricCard[accent="true"] {
    background-color: #0f2736;
    color: #67e8f9;
    border: 1px solid #155e75;
}
QGroupBox {
    background-color: #101621;
    border: 1px solid #243147;
    border-radius: 14px;
    margin-top: 14px;
    padding: 14px 12px 12px 12px;
    font-weight: 650;
    color: #dce7f5;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 14px;
    padding: 0 7px;
    color: #7dd3fc;
    background-color: #101621;
}
QLineEdit, QComboBox {
    background-color: #0b111b;
    color: #eef6ff;
    border: 1px solid #2a3950;
    border-radius: 9px;
    padding: 8px 10px;
    min-height: 18px;
    selection-background-color: #0891b2;
}
QLineEdit:focus, QComboBox:focus {
    border: 1px solid #22d3ee;
}
QLineEdit:disabled, QComboBox:disabled {
    background-color: #111827;
    color: #64748b;
    border-color: #1f2937;
}
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QComboBox QAbstractItemView {
    background-color: #111827;
    color: #eef6ff;
    border: 1px solid #334155;
    selection-background-color: #0e7490;
    selection-color: white;
}
QPushButton {
    background-color: #172033;
    color: #dbe7f5;
    border: 1px solid #31405a;
    border-radius: 9px;
    padding: 8px 12px;
    font-weight: 600;
    min-height: 18px;
}
QPushButton:hover {
    background-color: #202d44;
    border-color: #49617f;
}
QPushButton:pressed { background-color: #0f172a; }
QPushButton:disabled {
    background-color: #111827;
    color: #526178;
    border-color: #1e293b;
}
QPushButton[role="primary"] {
    background-color: #0891b2;
    color: #f8fdff;
    border: 1px solid #22d3ee;
}
QPushButton[role="primary"]:hover { background-color: #0e7490; }
QPushButton[role="danger"] {
    background-color: #3a1720;
    color: #fecdd3;
    border: 1px solid #7f1d1d;
}
QPushButton[role="danger"]:hover { background-color: #541b28; }
QPushButton[role="success"] {
    background-color: #123126;
    color: #bbf7d0;
    border: 1px solid #166534;
}
QProgressBar {
    background-color: #09111d;
    color: #dbeafe;
    border: 1px solid #27364c;
    border-radius: 8px;
    text-align: center;
    min-height: 17px;
}
QProgressBar::chunk {
    background-color: #06b6d4;
    border-radius: 7px;
}
QTabWidget::pane {
    border: none;
    background-color: #0b0f17;
    top: -1px;
}
QTabBar::tab {
    background-color: #0e1522;
    color: #8292a8;
    border: 1px solid #1f2b3d;
    border-bottom: none;
    padding: 10px 20px;
    margin-right: 4px;
    border-top-left-radius: 9px;
    border-top-right-radius: 9px;
    min-width: 110px;
}
QTabBar::tab:selected {
    background-color: #101b2b;
    color: #67e8f9;
    border-color: #155e75;
}
QTabBar::tab:hover { color: #e2f7fb; }
QRadioButton, QCheckBox { spacing: 8px; color: #dbe7f5; }
QRadioButton::indicator, QCheckBox::indicator { width: 16px; height: 16px; }
QRadioButton::indicator:unchecked, QCheckBox::indicator:unchecked {
    background-color: #09111d;
    border: 1px solid #526178;
}
QRadioButton::indicator:checked, QCheckBox::indicator:checked {
    background-color: #06b6d4;
    border: 1px solid #67e8f9;
}
QSlider::groove:horizontal {
    height: 6px;
    background: #1f2a3d;
    border-radius: 3px;
}
QSlider::sub-page:horizontal {
    background: #06b6d4;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #dffcff;
    border: 2px solid #06b6d4;
    width: 16px;
    margin: -6px 0;
    border-radius: 8px;
}
QScrollBar:horizontal, QScrollBar:vertical {
    background: #0b111b;
    border: none;
    margin: 0;
}
QScrollBar:horizontal { height: 10px; }
QScrollBar:vertical { width: 10px; }
QScrollBar::handle:horizontal, QScrollBar::handle:vertical {
    background: #334155;
    border-radius: 5px;
    min-width: 28px;
    min-height: 28px;
}
QScrollBar::handle:horizontal:hover, QScrollBar::handle:vertical:hover { background: #475569; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QVideoWidget { background-color: #02050a; border-radius: 10px; }
QMessageBox { background-color: #0f172a; }
QToolTip {
    background-color: #111827;
    color: #f8fafc;
    border: 1px solid #334155;
    padding: 5px;
}
"""



def app_dir():
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


ROOT_DIR = app_dir()
VIDEOS_DIR = ROOT_DIR / 'Videos'
BIN_DIR = ROOT_DIR / 'bin'
YTDLP_EXE = BIN_DIR / 'yt-dlp.exe'
FFMPEG_EXE = BIN_DIR / 'ffmpeg.exe'
FFPROBE_EXE = BIN_DIR / 'ffprobe.exe'
DENO_EXE = BIN_DIR / 'deno.exe'
CONFIG_PROXY = ROOT_DIR / 'config-proxy.json'
VIDEOS_DIR.mkdir(parents=True, exist_ok=True)


def format_ms(ms):
    """Formata milissegundos como HH:MM:SS.mmm."""
    ms = max(0, int(round(ms)))
    total_sec, millis = divmod(ms, 1000)
    h, rem = divmod(total_sec, 3600)
    m, sec = divmod(rem, 60)
    return f'{h:02d}:{m:02d}:{sec:02d}.{millis:03d}'


def parse_time(text):
    """Aceita MM:SS(.mmm) ou HH:MM:SS(.mmm), com ponto ou vírgula."""
    value = (text or '').strip().replace(',', '.')
    if not value:
        raise ValueError('Informe um tempo. Ex.: 00:00:12.350')
    parts = value.split(':')
    if len(parts) not in (2, 3):
        raise ValueError('Use MM:SS.mmm ou HH:MM:SS.mmm')
    try:
        if len(parts) == 2:
            h = 0
            m = int(parts[0])
            sec = float(parts[1])
        else:
            h = int(parts[0])
            m = int(parts[1])
            sec = float(parts[2])
    except Exception as exc:
        raise ValueError('Tempo inválido. Use HH:MM:SS.mmm') from exc
    if h < 0 or m < 0 or sec < 0 or m >= 60 or sec >= 60:
        raise ValueError('Tempo inválido. Use HH:MM:SS.mmm')
    return max(0, int(round((h * 3600 + m * 60 + sec) * 1000)))


def is_youtube(url):
    return bool(re.search(r'(?i)(?:youtube\.com|youtu\.be)', url or ''))


def looks_like_compat_error(message):
    msg = (message or '').lower()
    keys = ('403', 'forbidden', 'requested format', 'format is not available', 'sign in', 'player response')
    return any(k in msg for k in keys)


def is_video_candidate(url):
    low = (url or '').lower()
    return any(k in low for k in ('.mp4', '.m3u8', '.mpd', 'player', 'video', 'embed', 'stream'))


def normalize_candidate(value, page_url, force=False):
    if not value:
        return ''
    value = html.unescape(str(value)).strip()
    value = value.replace('\\u0026', '&').replace('\\u003d', '=').replace('\\u002f', '/').replace('\\/', '/')
    value = value.rstrip('\\"\' ')
    try:
        final = urllib.parse.urljoin(page_url, value)
    except Exception:
        return ''
    if not re.match(r'(?i)^https?://', final):
        return ''
    if not force and not is_video_candidate(final):
        return ''
    return final


def extract_candidates_from_html(page_html, page_url):
    text = str(page_html or '').replace('\\u0026', '&').replace('\\u003d', '=').replace('\\u002f', '/').replace('\\/', '/')
    result, seen = [], set()

    def add(value, force=False):
        url = normalize_candidate(value, page_url, force)
        if url and url not in seen:
            seen.add(url)
            result.append(url)

    for m in re.finditer(r'https?://[^\s"\'<>]+', text, re.I):
        add(m.group(0))
    for m in re.finditer(r'\b(?:src|content|file|href)\s*=\s*["\']([^"\']+)["\']', text, re.I):
        add(m.group(1))
    for m in re.finditer(r'["\'](?:contentUrl|embedUrl|videoUrl|streamUrl|file|src|url)["\']\s*:\s*["\']([^"\']+)["\']', text, re.I):
        whole = m.group(0)
        add(m.group(1), bool(re.search(r'(?i)contentUrl|embedUrl|videoUrl|streamUrl', whole)))
    for m in re.finditer(r'<iframe[^>]+src=["\']([^"\']+)["\'][^>]*>', text, re.I):
        add(m.group(1), True)
    for m in re.finditer(r'<meta[^>]+(?:property|name)=["\'](?:og:video(?::url|:secure_url)?|twitter:player(?::stream)?)["\'][^>]+content=["\']([^"\']+)["\']', text, re.I):
        add(m.group(1), True)
    return result[:15]


def _proxy_opener(proxy_url=''):
    if not proxy_url:
        return urllib.request.build_opener()
    return urllib.request.build_opener(urllib.request.ProxyHandler({'http': proxy_url, 'https': proxy_url}))


def fetch_html(page_url, proxy_url=''):
    request = urllib.request.Request(page_url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/149.0.0.0 Safari/537.36',
        'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
        'Accept': 'text/html,application/xhtml+xml,*/*;q=0.8',
    })
    opener = _proxy_opener(proxy_url)
    with opener.open(request, timeout=45) as response:
        ctype = (response.headers.get('content-type') or '').lower()
        if 'text/html' not in ctype:
            return ''
        charset = response.headers.get_content_charset() or 'utf-8'
        return response.read().decode(charset, 'replace')


def _probe_video_codec(path):
    try:
        proc = subprocess.run(
            [str(FFMPEG_EXE), '-hide_banner', '-i', str(path)],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            encoding='utf-8', errors='replace',
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
        )
        m = re.search(r'Video:\s*([^,\s]+)', proc.stdout or '', re.I)
        return (m.group(1).lower() if m else '')
    except Exception:
        return ''


def _seconds_from_ffmpeg_time(value):
    try:
        h, m, s = value.strip().split(':')
        return int(h) * 3600 + int(m) * 60 + float(s)
    except Exception:
        return 0.0


def _probe_media_info(path):
    """Retorna informações úteis do arquivo para o editor de múltiplos vídeos."""
    path = Path(path)
    info = {
        'duration_ms': 0,
        'width': 0,
        'height': 0,
        'fps': 30.0,
        'has_audio': False,
    }

    if FFPROBE_EXE.exists():
        try:
            cmd = [
                str(FFPROBE_EXE), '-v', 'error', '-show_entries',
                'format=duration:stream=codec_type,width,height,r_frame_rate',
                '-of', 'json', str(path),
            ]
            result = subprocess.run(
                cmd, capture_output=True, text=True, encoding='utf-8', errors='replace',
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
            )
            if result.returncode == 0 and result.stdout.strip():
                data = json.loads(result.stdout)
                try:
                    info['duration_ms'] = max(0, int(round(float(data.get('format', {}).get('duration', 0)) * 1000)))
                except Exception:
                    pass
                for stream in data.get('streams', []) or []:
                    if stream.get('codec_type') == 'video' and not info['width']:
                        info['width'] = int(stream.get('width') or 0)
                        info['height'] = int(stream.get('height') or 0)
                        rate = str(stream.get('r_frame_rate') or '')
                        try:
                            if '/' in rate:
                                a, b = rate.split('/', 1)
                                fps = float(a) / float(b) if float(b) else 0.0
                            else:
                                fps = float(rate)
                            if 1 <= fps <= 120:
                                info['fps'] = fps
                        except Exception:
                            pass
                    elif stream.get('codec_type') == 'audio':
                        info['has_audio'] = True
                if info['duration_ms'] > 0 and info['width'] > 0 and info['height'] > 0:
                    return info
        except Exception:
            pass

    # Compatibilidade com portables antigos sem ffprobe.exe.
    try:
        proc = subprocess.run(
            [str(FFMPEG_EXE), '-hide_banner', '-i', str(path)],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            encoding='utf-8', errors='replace',
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
        )
        text = proc.stdout or ''
        md = re.search(r'Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)', text, re.I)
        if md:
            sec = int(md.group(1)) * 3600 + int(md.group(2)) * 60 + float(md.group(3))
            info['duration_ms'] = max(info['duration_ms'], int(round(sec * 1000)))
        mv = re.search(r'Video:.*?(\d{2,5})x(\d{2,5}).*?(\d+(?:\.\d+)?)\s*fps', text, re.I | re.S)
        if not mv:
            mv = re.search(r'Video:.*?(\d{2,5})x(\d{2,5})', text, re.I | re.S)
        if mv:
            info['width'] = int(mv.group(1))
            info['height'] = int(mv.group(2))
            if len(mv.groups()) >= 3 and mv.group(3):
                try:
                    fps = float(mv.group(3))
                    if 1 <= fps <= 120:
                        info['fps'] = fps
                except Exception:
                    pass
        info['has_audio'] = bool(re.search(r'Audio:\s*', text, re.I))
    except Exception:
        pass
    return info


def _safe_output_name(text, default='video_editado.mp4'):
    name = (text or '').strip() or default
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name).strip(' .')
    if not name:
        name = default
    if not name.lower().endswith('.mp4'):
        name += '.mp4'
    return name[:180]


def load_proxy_config():
    default = {'ATIVADO': False, 'SERVIDOR': '', 'PORTA': ''}
    try:
        if CONFIG_PROXY.exists():
            data = json.loads(CONFIG_PROXY.read_text(encoding='utf-8-sig'))
            if isinstance(data, dict):
                default.update(data)
    except Exception:
        pass
    return default


def save_proxy_config(enabled, server, port):
    data = {'ATIVADO': bool(enabled), 'SERVIDOR': server.strip(), 'PORTA': port.strip()}
    CONFIG_PROXY.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def build_proxy_url(server, port, username='', password=''):
    server = (server or '').strip()
    port = (port or '').strip()
    if not server:
        raise ValueError('Informe o servidor do proxy.')
    if not port:
        raise ValueError('Informe a porta do proxy.')
    if not re.fullmatch(r'\d{1,5}', port) or not (1 <= int(port) <= 65535):
        raise ValueError('A porta do proxy é inválida.')
    if not re.match(r'(?i)^https?://', server):
        server = 'http://' + server
    parsed = urllib.parse.urlsplit(server)
    host = parsed.hostname or ''
    scheme = parsed.scheme or 'http'
    if not host:
        raise ValueError('Servidor de proxy inválido.')
    auth = ''
    if username:
        auth = urllib.parse.quote(username, safe='')
        if password:
            auth += ':' + urllib.parse.quote(password, safe='')
        auth += '@'
    return f'{scheme}://{auth}{host}:{port}'


def friendly_network_error(text):
    msg = str(text or '')
    low = msg.lower()
    if '407' in low or 'proxy authentication required' in low:
        return 'O proxy recusou a autenticação (HTTP 407). Confira usuário e senha.'
    if 'timed out' in low or 'timeout' in low:
        return 'Tempo esgotado ao acessar a internet. Confira o proxy e a conexão.'
    if 'name or service not known' in low or 'getaddrinfo' in low or 'enotfound' in low:
        return 'Não foi possível localizar o servidor do proxy.'
    if 'connection refused' in low or 'econnrefused' in low:
        return 'A conexão foi recusada pelo servidor do proxy.'
    if 'certificate' in low or 'self signed' in low or 'unable to verify' in low:
        return 'A rede bloqueou a conexão por certificado. Pode ser necessário instalar o certificado CA corporativo no Windows.'
    return msg.strip() or 'Falha de rede.'


def _redact_proxy_in_command(cmd):
    safe = []
    hide_next = False
    for item in cmd:
        if hide_next:
            text = str(item)
            try:
                u = urllib.parse.urlsplit(text)
                if u.username:
                    host = u.hostname or ''
                    port = f':{u.port}' if u.port else ''
                    safe.append(f'{u.scheme}://***:***@{host}{port}')
                else:
                    safe.append(text)
            except Exception:
                safe.append('***')
            hide_next = False
            continue
        safe.append(str(item))
        if str(item) == '--proxy':
            hide_next = True
    return safe


def save_ytdlp_diagnostic(url, attempts):
    try:
        out = ROOT_DIR / 'ultimo-erro-yt-dlp.txt'
        lines = [
            f'{APP_NAME} - {APP_VERSION}',
            f'Data: {datetime.now().isoformat(timespec="seconds")}',
            f'URL: {url}',
            f'yt-dlp: {YTDLP_EXE}',
            f'FFmpeg: {FFMPEG_EXE}',
            f'Deno: {DENO_EXE}',
            '',
        ]
        for i, item in enumerate(attempts, 1):
            lines += [
                '=' * 72,
                f'TENTATIVA {i}: {item.get("label", "")}',
                f'Código: {item.get("code", "")}',
                'Comando: ' + ' '.join(_redact_proxy_in_command(item.get('cmd', []))),
                '--- SAÍDA ---',
                item.get('output', '') or '',
                '',
            ]
        out.write_text('\n'.join(lines), encoding='utf-8')
        return out
    except Exception:
        return None


class DownloadWorker(QThread):
    progress = Signal(int)
    message = Signal(str)
    done = Signal(str)
    failed = Signal(str)
    canceled = Signal()

    def __init__(self, url, quality_index, proxy_url=''):
        super().__init__()
        self.url = url
        self.quality_index = max(0, min(len(FORMATS) - 1, int(quality_index)))
        self.proxy_url = proxy_url or ''
        self._cancel_requested = False
        self._process = None
        self._attempt_logs = []

    def cancel(self):
        self._cancel_requested = True
        try:
            if self._process and self._process.poll() is None:
                self._process.terminate()
        except Exception:
            pass

    def _base_cmd(self, fmt, referer='', extractor_args='', force_ipv4=False):
        output = str(VIDEOS_DIR / '%(title).180B [%(id)s].%(ext)s')
        cmd = [
            str(YTDLP_EXE), '--no-playlist', '--newline', '--progress', '--windows-filenames',
            '--trim-filenames', '180', '--continue', '--retries', '10', '--fragment-retries', '10',
            '--retry-sleep', 'http:linear=1::3', '--retry-sleep', 'fragment:linear=1::3',
            '--socket-timeout', '30', '--ffmpeg-location', str(BIN_DIR),
        ]
        # O yt-dlp.exe oficial já traz o EJS necessário. Deno é usado apenas como runtime.
        # Não usamos --remote-components ejs:github, porque isso cria uma dependência extra
        # do GitHub em tempo de execução e pode falhar atrás de proxy corporativo.
        if DENO_EXE.exists():
            cmd += ['--js-runtimes', f'deno:{DENO_EXE}']
        if self.proxy_url:
            cmd += ['--proxy', self.proxy_url]
        if force_ipv4:
            cmd += ['--force-ipv4']
        if extractor_args:
            cmd += ['--extractor-args', extractor_args]
        cmd += ['-f', fmt, '--merge-output-format', 'mp4', '--remux-video', 'mp4']
        if referer:
            cmd += ['--referer', referer]
        cmd += [
            '-o', output,
            '--print', 'before_dl:VIDEO_TITLE:%(title)s',
            '--print', 'after_move:FINAL_FILE:%(filepath)s',
        ]
        return cmd

    def _newest_new_video(self, before):
        candidates = []
        for ext in ('*.mp4', '*.mkv', '*.webm', '*.mov'):
            for path in VIDEOS_DIR.glob(ext):
                try:
                    key = str(path.resolve()).lower()
                    if key not in before and path.is_file() and path.stat().st_size > 1024:
                        candidates.append(path)
                except Exception:
                    pass
        if not candidates:
            return ''
        candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return str(candidates[0])

    def _attempt(self, url, fmt, referer='', label='', extractor_args='', force_ipv4=False):
        if self._cancel_requested:
            return False, '', 'Download cancelado'
        self.message.emit(label)
        before = set()
        try:
            for path in VIDEOS_DIR.iterdir():
                if path.is_file():
                    before.add(str(path.resolve()).lower())
        except Exception:
            pass

        cmd = self._base_cmd(fmt, referer, extractor_args, force_ipv4) + [url]
        flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        try:
            self._process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                encoding='utf-8', errors='replace', creationflags=flags,
            )
        except Exception as exc:
            self._attempt_logs.append({'label': label, 'code': -1, 'cmd': cmd, 'output': str(exc)})
            return False, '', str(exc)

        final_file = ''
        all_lines = []
        assert self._process.stdout is not None
        for raw in self._process.stdout:
            if self._cancel_requested:
                try:
                    self._process.terminate()
                except Exception:
                    pass
                return False, '', 'Download cancelado'
            line = raw.rstrip('\r\n')
            if line.startswith('FINAL_FILE:'):
                final_file = line.split(':', 1)[1].strip().strip('"')
            match = re.search(r'(\d{1,3}(?:\.\d+)?)%', line)
            if match:
                self.progress.emit(max(0, min(100, int(float(match.group(1))))))
            if line.strip():
                all_lines.append(line.strip())
                if any(tag in line.lower() for tag in ('[download]', '[merger]', '[youtube]', 'warning', 'error')):
                    self.message.emit(line.strip()[-220:])

        code = self._process.wait()
        self._process = None
        output_text = '\n'.join(all_lines[-120:])
        self._attempt_logs.append({'label': label, 'code': code, 'cmd': cmd, 'output': output_text})

        if code == 0:
            candidate = Path(final_file) if final_file else None
            if candidate and candidate.exists() and candidate.is_file() and candidate.stat().st_size > 1024:
                return True, str(candidate), ''
            discovered = self._newest_new_video(before)
            if discovered:
                return True, discovered, ''
            return False, '', 'O yt-dlp terminou sem erro, mas nenhum arquivo de vídeo foi criado.'

        return False, final_file, output_text or 'O yt-dlp encerrou com erro.'

    def _ensure_youtube_preview_compatible(self, final_file):
        path = Path(final_file)
        if not path.exists() or not path.is_file():
            return False, final_file, 'O arquivo baixado não foi encontrado.'
        codec = _probe_video_codec(path)
        if codec in ('h264', 'avc1'):
            return True, final_file, ''

        temp = path.with_name(path.stem + '.compat-temp.mp4')
        self.message.emit(f'YouTube baixado em {codec or "codec não identificado"}. Convertendo para H.264 para a prévia...')
        cmd = [
            str(FFMPEG_EXE), '-y', '-hide_banner', '-loglevel', 'error', '-i', str(path),
            '-map', '0:v:0', '-map', '0:a?', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20',
            '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '160k', '-movflags', '+faststart',
            '-progress', 'pipe:1', '-nostats', str(temp),
        ]
        flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        try:
            self._process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                encoding='utf-8', errors='replace', creationflags=flags,
            )
            assert self._process.stdout is not None
            for raw in self._process.stdout:
                if self._cancel_requested:
                    self._process.terminate()
                    temp.unlink(missing_ok=True)
                    return False, final_file, 'Download cancelado'
                if raw.startswith('out_time='):
                    self.progress.emit(95)
            code = self._process.wait()
            self._process = None
            if code != 0 or not temp.exists() or temp.stat().st_size < 1024:
                temp.unlink(missing_ok=True)
                return False, final_file, 'Falha ao converter o vídeo do YouTube para H.264.'
            path.unlink(missing_ok=True)
            temp.replace(path)
            self.progress.emit(100)
            self.message.emit('Vídeo convertido para H.264. Pré-visualização pronta.')
            return True, str(path), ''
        except Exception as exc:
            temp.unlink(missing_ok=True)
            return False, final_file, str(exc)

    def _finish_if_ok(self, ok, final_file, error):
        if not ok:
            return False
        if is_youtube(self.url):
            ok, final_file, error = self._ensure_youtube_preview_compatible(final_file)
        if ok:
            self.progress.emit(100)
            self.done.emit(final_file)
            return True
        return False

    def _fail_with_diagnostic(self, error):
        diag = save_ytdlp_diagnostic(self.url, self._attempt_logs)
        text = friendly_network_error(error or 'Não foi possível baixar este vídeo.')
        if diag:
            text += f'\n\nDiagnóstico salvo em:\n{diag}'
        self.failed.emit(text)

    def run(self):
        if not YTDLP_EXE.exists():
            self.failed.emit('yt-dlp.exe não encontrado na pasta bin.')
            return
        if not FFMPEG_EXE.exists():
            self.failed.emit('ffmpeg.exe não encontrado na pasta bin.')
            return
        if is_youtube(self.url) and not DENO_EXE.exists():
            self.failed.emit('Deno não foi encontrado. O YouTube atual precisa de um runtime JavaScript.')
            return

        fmt = FORMATS[self.quality_index]
        compat = COMPAT_FORMATS[self.quality_index]
        self.progress.emit(0)

        ok, file, err = self._attempt(
            self.url, fmt,
            label='YouTube: tentativa principal...' if is_youtube(self.url) else 'Tentativa principal...'
        )
        if ok and self._finish_if_ok(ok, file, err):
            return
        if self._cancel_requested:
            self.canceled.emit()
            return

        if is_youtube(self.url):
            last_err = err
            low = (err or '').lower()
            if '403' in low or 'forbidden' in low:
                ok, file, last_err = self._attempt(
                    self.url, fmt, label='YouTube: repetindo com IPv4...', force_ipv4=True
                )
                if ok and self._finish_if_ok(ok, file, last_err):
                    return
                if self._cancel_requested:
                    self.canceled.emit()
                    return

            low = (last_err or '').lower()
            if any(k in low for k in ('403', 'forbidden', 'requested format', 'format is not available', 'nenhum arquivo')):
                ok, file, last_err = self._attempt(
                    self.url, compat, label='YouTube: modo compatibilidade MP4...', force_ipv4=True
                )
                if ok and self._finish_if_ok(ok, file, last_err):
                    return
                if self._cancel_requested:
                    self.canceled.emit()
                    return

            self._fail_with_diagnostic(last_err)
            return

        self.message.emit('Método principal falhou. Procurando vídeos dentro da página...')
        try:
            page_html = fetch_html(self.url, self.proxy_url)
        except Exception as exc:
            self._fail_with_diagnostic(str(exc))
            return
        candidates = extract_candidates_from_html(page_html, self.url)
        last_err = err
        for i, candidate in enumerate(candidates, 1):
            ok, file, last_err = self._attempt(
                candidate, fmt, referer=self.url,
                label=f'Tentativa alternativa {i}/{len(candidates)}...'
            )
            if ok and self._finish_if_ok(ok, file, last_err):
                return
            if self._cancel_requested:
                self.canceled.emit()
                return
        self._fail_with_diagnostic(last_err)


class UpdateWorker(QThread):
    done = Signal(str)
    failed = Signal(str)

    def __init__(self, proxy_url=''):
        super().__init__()
        self.proxy_url = proxy_url or ''

    def run(self):
        if not YTDLP_EXE.exists():
            self.failed.emit('yt-dlp.exe não encontrado na pasta bin.')
            return
        cmd = [str(YTDLP_EXE), '--update-to', 'nightly']
        if self.proxy_url:
            cmd += ['--proxy', self.proxy_url]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace',
                                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            text = '\n'.join(x for x in (result.stdout.strip(), result.stderr.strip()) if x).strip()
            if result.returncode == 0:
                self.done.emit(text or 'yt-dlp atualizado.')
            else:
                self.failed.emit(friendly_network_error(text or 'Falha ao atualizar o yt-dlp.'))
        except Exception as exc:
            self.failed.emit(friendly_network_error(exc))


class CutWorker(QThread):
    progress = Signal(int)
    done = Signal(str)
    failed = Signal(str)

    def __init__(self, source, start_ms, end_ms):
        super().__init__()
        self.source = Path(source)
        self.start_ms = int(start_ms)
        self.end_ms = int(end_ms)

    def run(self):
        if not FFMPEG_EXE.exists():
            self.failed.emit('ffmpeg.exe não encontrado na pasta bin.')
            return
        if self.end_ms <= self.start_ms:
            self.failed.emit('O fim do corte precisa ser depois do início.')
            return

        stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        output = VIDEOS_DIR / f'{self.source.stem}_corte_{stamp}.mp4'
        start_sec = self.start_ms / 1000.0
        duration_sec = (self.end_ms - self.start_ms) / 1000.0
        cmd = [
            str(FFMPEG_EXE), '-y', '-hide_banner', '-loglevel', 'error',
            '-i', str(self.source), '-ss', f'{start_sec:.3f}', '-t', f'{duration_sec:.3f}',
            '-map', '0:v:0?', '-map', '0:a:0?', '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '18',
            '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-threads', '0',
            '-movflags', '+faststart', '-avoid_negative_ts', 'make_zero',
            '-progress', 'pipe:1', '-nostats', str(output),
        ]
        flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                    encoding='utf-8', errors='replace', bufsize=1, creationflags=flags)
            tail = []
            self.progress.emit(0)
            assert proc.stdout is not None
            for raw in proc.stdout:
                line = raw.strip()
                if line:
                    tail.append(line); tail = tail[-30:]
                seconds = None
                if line.startswith('out_time_us='):
                    try: seconds = float(line.split('=', 1)[1]) / 1_000_000.0
                    except Exception: pass
                elif line.startswith('out_time='):
                    seconds = _seconds_from_ffmpeg_time(line.split('=', 1)[1])
                if seconds is not None and duration_sec > 0:
                    pct = max(0, min(99, int(seconds * 100.0 / duration_sec)))
                    self.progress.emit(pct)
            code = proc.wait()
            if code != 0:
                output.unlink(missing_ok=True)
                self.failed.emit('\n'.join(tail[-30:]) or 'Falha no FFmpeg.')
                return
            if not output.exists() or output.stat().st_size < 1024:
                output.unlink(missing_ok=True)
                self.failed.emit('O FFmpeg terminou, mas o arquivo cortado não foi gerado corretamente.')
                return
            self.progress.emit(100)
            self.done.emit(str(output))
        except Exception as exc:
            output.unlink(missing_ok=True)
            self.failed.emit(str(exc))


class JoinWorker(QThread):
    progress = Signal(int)
    message = Signal(str)
    done = Signal(str)
    failed = Signal(str)

    def __init__(self, clips, output_name):
        super().__init__()
        self.clips = [dict(item) for item in clips]
        self.output_name = _safe_output_name(output_name)

    def _run_process(self, cmd, duration_sec, base_pct, span_pct):
        flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        tail = []
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            encoding='utf-8', errors='replace', bufsize=1, creationflags=flags,
        )
        assert proc.stdout is not None
        for raw in proc.stdout:
            line = raw.strip()
            if line:
                tail.append(line)
                tail = tail[-40:]
            seconds = None
            if line.startswith('out_time_us='):
                try:
                    seconds = float(line.split('=', 1)[1]) / 1_000_000.0
                except Exception:
                    pass
            elif line.startswith('out_time='):
                seconds = _seconds_from_ffmpeg_time(line.split('=', 1)[1])
            if seconds is not None and duration_sec > 0:
                frac = max(0.0, min(1.0, seconds / duration_sec))
                self.progress.emit(max(0, min(99, int(base_pct + frac * span_pct))))
        code = proc.wait()
        return code, '\n'.join(tail[-40:])

    def run(self):
        if not FFMPEG_EXE.exists():
            self.failed.emit('ffmpeg.exe não encontrado na pasta bin.')
            return
        if len(self.clips) < 2:
            self.failed.emit('Adicione pelo menos 2 vídeos ao editor.')
            return

        for clip in self.clips:
            source = Path(clip.get('path', ''))
            if not source.exists():
                self.failed.emit(f'Arquivo não encontrado: {source}')
                return
            if int(clip.get('end_ms', 0)) <= int(clip.get('start_ms', 0)):
                self.failed.emit(f'Intervalo inválido em: {source.name}')
                return

        first_info = dict(self.clips[0].get('info') or {})
        if not first_info.get('width') or not first_info.get('height'):
            first_info.update(_probe_media_info(self.clips[0]['path']))
        target_w = max(2, int(first_info.get('width') or 1280))
        target_h = max(2, int(first_info.get('height') or 720))
        target_w -= target_w % 2
        target_h -= target_h % 2
        fps = float(first_info.get('fps') or 30.0)
        if not (1 <= fps <= 60):
            fps = 30.0

        output = VIDEOS_DIR / self.output_name
        if output.exists():
            stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
            output = output.with_name(f'{output.stem}_{stamp}{output.suffix}')

        total_duration = sum((int(c['end_ms']) - int(c['start_ms'])) / 1000.0 for c in self.clips)
        if total_duration <= 0:
            self.failed.emit('A duração total selecionada é inválida.')
            return

        try:
            with tempfile.TemporaryDirectory(prefix='ExtratorVideos-editor-') as temp_root:
                temp_dir = Path(temp_root)
                temp_files = []
                segment_span = 82.0 / max(1, len(self.clips))
                vf = (
                    f'scale={target_w}:{target_h}:force_original_aspect_ratio=decrease,'
                    f'pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2,'
                    f'setsar=1,fps={fps:.3f},format=yuv420p'
                )

                for idx, clip in enumerate(self.clips):
                    source = Path(clip['path'])
                    start_sec = int(clip['start_ms']) / 1000.0
                    duration_sec = (int(clip['end_ms']) - int(clip['start_ms'])) / 1000.0
                    info = dict(clip.get('info') or {})
                    if 'has_audio' not in info:
                        info.update(_probe_media_info(source))
                    has_audio = bool(info.get('has_audio'))
                    temp_file = temp_dir / f'parte_{idx + 1:03d}.mp4'
                    temp_files.append(temp_file)

                    self.message.emit(
                        f'Preparando trecho {idx + 1}/{len(self.clips)} — {source.name}'
                    )
                    cmd = [
                        str(FFMPEG_EXE), '-y', '-hide_banner', '-loglevel', 'error',
                        '-i', str(source),
                    ]
                    if not has_audio:
                        cmd += [
                            '-f', 'lavfi', '-i', 'anullsrc=channel_layout=stereo:sample_rate=48000',
                        ]
                    cmd += [
                        '-ss', f'{start_sec:.3f}', '-t', f'{duration_sec:.3f}',
                        '-map', '0:v:0', '-map', '0:a:0' if has_audio else '1:a:0',
                        '-vf', vf,
                        '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18',
                        '-pix_fmt', 'yuv420p',
                        '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-ac', '2',
                        '-af', 'aresample=async=1:first_pts=0',
                        '-shortest', '-movflags', '+faststart', '-avoid_negative_ts', 'make_zero',
                        '-progress', 'pipe:1', '-nostats', str(temp_file),
                    ]
                    base = idx * segment_span
                    code, tail = self._run_process(cmd, duration_sec, base, segment_span)
                    if code != 0 or not temp_file.exists() or temp_file.stat().st_size < 1024:
                        self.failed.emit(tail or f'Falha ao preparar {source.name}.')
                        return

                concat_file = temp_dir / 'lista.txt'
                lines = []
                for item in temp_files:
                    safe_path = item.resolve().as_posix().replace("'", "\\'")
                    lines.append(f"file '{safe_path}'")
                concat_file.write_text('\n'.join(lines), encoding='utf-8')

                self.message.emit('Unindo os trechos selecionados...')
                cmd = [
                    str(FFMPEG_EXE), '-y', '-hide_banner', '-loglevel', 'error',
                    '-fflags', '+genpts', '-f', 'concat', '-safe', '0', '-i', str(concat_file),
                    '-vf', f'fps={fps:.3f},format=yuv420p',
                    '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18', '-pix_fmt', 'yuv420p',
                    '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-ac', '2',
                    '-af', 'aresample=async=1:first_pts=0', '-movflags', '+faststart',
                    '-progress', 'pipe:1', '-nostats', str(output),
                ]
                code, tail = self._run_process(cmd, total_duration, 82, 17)
                if code != 0 or not output.exists() or output.stat().st_size < 1024:
                    output.unlink(missing_ok=True)
                    self.failed.emit(tail or 'Falha ao unir os vídeos.')
                    return

            self.progress.emit(100)
            self.message.emit('Vídeo final concluído.')
            self.done.emit(str(output))
        except Exception as exc:
            output.unlink(missing_ok=True)
            self.failed.emit(str(exc))


class VideoEditorWidget(QWidget):
    """Editor simples para cortar e unir dois ou mais vídeos."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.clips = []
        self.current_index = -1
        self.worker = None
        self.preview_end_ms = 0
        self._refreshing_list = False

        self.player = QMediaPlayer(self)
        self.audio = QAudioOutput(self)
        self.player.setAudioOutput(self.audio)
        self.preview_timer = QTimer(self)
        self.preview_timer.setInterval(50)
        self.preview_timer.timeout.connect(self._check_preview_end)

        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 14, 14, 14)
        outer.setSpacing(10)

        title = QLabel('Editor — cortar e unir vários vídeos')
        f = title.font(); f.setPointSize(16); f.setBold(True); title.setFont(f)
        outer.addWidget(title)
        tip = QLabel(
            'Adicione 2 ou mais vídeos. Cada item pode ter início/fim próprios. '
            'A ordem da lista será a ordem do vídeo final.'
        )
        tip.setWordWrap(True)
        outer.addWidget(tip)

        list_box = QGroupBox('Vídeos / trechos')
        lb = QVBoxLayout(list_box)
        self.list_widget = QListWidget()
        self.list_widget.setMinimumHeight(130)
        lb.addWidget(self.list_widget)
        actions = QHBoxLayout()
        self.btn_add = QPushButton('+ ADICIONAR VÍDEOS')
        self.btn_remove = QPushButton('REMOVER')
        self.btn_up = QPushButton('↑ SUBIR')
        self.btn_down = QPushButton('↓ DESCER')
        actions.addWidget(self.btn_add); actions.addWidget(self.btn_remove)
        actions.addWidget(self.btn_up); actions.addWidget(self.btn_down); actions.addStretch(1)
        lb.addLayout(actions)
        outer.addWidget(list_box)

        edit_box = QGroupBox('Ajuste do trecho selecionado')
        eb = QVBoxLayout(edit_box)
        self.video_widget = QVideoWidget()
        self.video_widget.setMinimumHeight(230)
        self.video_widget.setMaximumHeight(380)
        self.player.setVideoOutput(self.video_widget)
        eb.addWidget(self.video_widget)

        playrow = QHBoxLayout()
        self.btn_play = QPushButton('▶ PLAY')
        self.position_label = QLabel('00:00:00.000 / 00:00:00.000')
        playrow.addWidget(self.btn_play); playrow.addWidget(self.position_label); playrow.addStretch(1)
        eb.addLayout(playrow)

        self.slider = RangeSlider()
        eb.addWidget(self.slider)
        info = QLabel('Bolinhas = início/fim. Linha com triângulo = posição atual do vídeo (independente).')
        info.setWordWrap(True)
        eb.addWidget(info)

        self.start_edit = QLineEdit('00:00:00.000')
        self.end_edit = QLineEdit('00:00:00.000')
        self.start_edit.setPlaceholderText('HH:MM:SS.mmm')
        self.end_edit.setPlaceholderText('HH:MM:SS.mmm')

        time_grid = QGridLayout()
        time_grid.addWidget(QLabel('Início do corte:'), 0, 0)
        time_grid.addWidget(self.start_edit, 0, 1)
        time_grid.addWidget(QLabel('Fim do corte:'), 1, 0)
        time_grid.addWidget(self.end_edit, 1, 1)

        self.start_buttons = []
        self.end_buttons = []
        deltas = [(-1000, '−1s'), (-100, '−100ms'), (-10, '−10ms'), (10, '+10ms'), (100, '+100ms'), (1000, '+1s')]
        start_adj = QHBoxLayout(); end_adj = QHBoxLayout()
        for delta, text in deltas:
            b1 = QPushButton(text); b1.setToolTip(f'Ajustar início em {text}')
            b1.clicked.connect(lambda _=False, d=delta: self._adjust_boundary('start', d))
            self.start_buttons.append(b1); start_adj.addWidget(b1)
            b2 = QPushButton(text); b2.setToolTip(f'Ajustar fim em {text}')
            b2.clicked.connect(lambda _=False, d=delta: self._adjust_boundary('end', d))
            self.end_buttons.append(b2); end_adj.addWidget(b2)
        time_grid.addLayout(start_adj, 0, 2)
        time_grid.addLayout(end_adj, 1, 2)
        eb.addLayout(time_grid)

        markrow = QHBoxLayout()
        self.btn_mark_start = QPushButton('MARCAR INÍCIO AQUI')
        self.btn_mark_end = QPushButton('MARCAR FIM AQUI')
        self.btn_preview = QPushButton('▶ PRÉ-VISUALIZAR TRECHO')
        markrow.addWidget(self.btn_mark_start); markrow.addWidget(self.btn_mark_end)
        markrow.addWidget(self.btn_preview); markrow.addStretch(1)
        eb.addLayout(markrow)
        outer.addWidget(edit_box)

        export_box = QGroupBox('Gerar vídeo final')
        ex = QVBoxLayout(export_box)
        name_row = QHBoxLayout()
        name_row.addWidget(QLabel('Nome:'))
        self.output_name = QLineEdit('video_editado.mp4')
        name_row.addWidget(self.output_name, 1)
        self.btn_export = QPushButton('CORTAR E UNIR VÍDEOS')
        self.btn_folder = QPushButton('ABRIR PASTA')
        name_row.addWidget(self.btn_export); name_row.addWidget(self.btn_folder)
        ex.addLayout(name_row)
        prog = QHBoxLayout()
        self.progress = QProgressBar(); self.progress.setRange(0, 100); self.progress.setFormat('Editor: %p%')
        self.percent = QLabel('0%'); self.percent.setMinimumWidth(44)
        prog.addWidget(self.progress, 1); prog.addWidget(self.percent)
        ex.addLayout(prog)
        self.status = QLabel('Adicione pelo menos 2 vídeos para começar.')
        self.status.setWordWrap(True)
        ex.addWidget(self.status)
        outer.addWidget(export_box)
        outer.addStretch(1)

        self.btn_add.clicked.connect(self.add_videos)
        self.btn_remove.clicked.connect(self.remove_current)
        self.btn_up.clicked.connect(lambda: self.move_current(-1))
        self.btn_down.clicked.connect(lambda: self.move_current(1))
        self.list_widget.currentRowChanged.connect(self.select_clip)
        self.btn_play.clicked.connect(self.toggle_play)
        self.slider.valuesChanged.connect(self._range_changed)
        self.slider.handleReleased.connect(lambda *_: self.player.pause())
        self.slider.handleMoved.connect(lambda _which, pos: self.seek_to(pos))
        self.slider.positionChanged.connect(self.seek_to)
        self.start_edit.editingFinished.connect(lambda: self._time_field_changed('start'))
        self.end_edit.editingFinished.connect(lambda: self._time_field_changed('end'))
        self.btn_mark_start.clicked.connect(lambda: self._mark_here('start'))
        self.btn_mark_end.clicked.connect(lambda: self._mark_here('end'))
        self.btn_preview.clicked.connect(self.preview_range)
        self.btn_export.clicked.connect(self.export_video)
        self.btn_folder.clicked.connect(self.open_folder)
        self._set_clip_controls(False)

    def _connect_player(self):
        self.player.durationChanged.connect(self._duration_changed)
        self.player.positionChanged.connect(self._position_changed)
        self.player.playbackStateChanged.connect(self._playback_state_changed)
        self.player.errorOccurred.connect(lambda _err, text: self.status.setText(f'Pré-visualização: {text}'))

    def _set_clip_controls(self, enabled):
        for widget in (
            self.btn_play, self.slider, self.start_edit, self.end_edit,
            self.btn_mark_start, self.btn_mark_end, self.btn_preview,
            *self.start_buttons, *self.end_buttons,
        ):
            widget.setEnabled(enabled)

    def _clip_text(self, idx, clip):
        return (
            f'{idx + 1}. {Path(clip["path"]).name}   '
            f'[{format_ms(clip["start_ms"])} → {format_ms(clip["end_ms"])}]'
        )

    def _refresh_list(self, selected=None):
        self._refreshing_list = True
        try:
            if selected is None:
                selected = self.current_index
            self.list_widget.clear()
            for idx, clip in enumerate(self.clips):
                self.list_widget.addItem(self._clip_text(idx, clip))
            if self.clips:
                selected = max(0, min(int(selected), len(self.clips) - 1))
                self.list_widget.setCurrentRow(selected)
                self.current_index = selected
            else:
                self.current_index = -1
        finally:
            self._refreshing_list = False
        if self.clips and self.current_index >= 0:
            self.select_clip(self.current_index)
        else:
            self.player.stop()
            self.player.setSource(QUrl())
            self._set_clip_controls(False)
            self.position_label.setText('00:00:00.000 / 00:00:00.000')

    def add_videos(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, 'Adicionar vídeos', str(VIDEOS_DIR),
            'Vídeos (*.mp4 *.mkv *.webm *.mov *.avi *.m4v);;Todos os arquivos (*)'
        )
        if not files:
            return
        self.status.setText('Analisando arquivos adicionados...')
        QApplication.processEvents()
        for file in files:
            path = Path(file)
            info = _probe_media_info(path)
            duration = max(1, int(info.get('duration_ms') or 1))
            self.clips.append({
                'path': str(path),
                'start_ms': 0,
                'end_ms': duration,
                'duration_ms': duration,
                'info': info,
            })
        self._refresh_list(len(self.clips) - len(files))
        self.status.setText(f'{len(self.clips)} vídeo(s) na lista. Ajuste os trechos e a ordem.')

    def remove_current(self):
        row = self.list_widget.currentRow()
        if row < 0 or row >= len(self.clips):
            return
        self.player.pause()
        del self.clips[row]
        self._refresh_list(min(row, len(self.clips) - 1))
        self.status.setText(f'{len(self.clips)} vídeo(s) na lista.')

    def move_current(self, direction):
        row = self.list_widget.currentRow()
        other = row + int(direction)
        if row < 0 or other < 0 or other >= len(self.clips):
            return
        self.clips[row], self.clips[other] = self.clips[other], self.clips[row]
        self._refresh_list(other)

    def select_clip(self, row):
        if self._refreshing_list:
            return
        if row < 0 or row >= len(self.clips):
            self.current_index = -1
            self._set_clip_controls(False)
            return
        self.preview_timer.stop()
        self.preview_end_ms = 0
        self.player.pause()
        self.current_index = row
        clip = self.clips[row]
        duration = max(1, int(clip.get('duration_ms') or clip.get('end_ms') or 1))
        start = max(0, min(int(clip.get('start_ms', 0)), duration))
        end = max(start + 1, min(int(clip.get('end_ms', duration)), duration))
        clip['start_ms'], clip['end_ms'], clip['duration_ms'] = start, end, duration
        self.slider.setRange(0, duration)
        self.slider.setValues(start, end, emit=False)
        self.slider.setPosition(start, emit=False)
        self.start_edit.setText(format_ms(start))
        self.end_edit.setText(format_ms(end))
        self.position_label.setText(f'{format_ms(start)} / {format_ms(duration)}')
        self.player.setSource(QUrl.fromLocalFile(str(Path(clip['path']))))
        self.player.setPosition(start)
        self._set_clip_controls(True)
        self.status.setText(f'Editando: {Path(clip["path"]).name}')

    def _duration_changed(self, duration):
        if self.current_index < 0 or self.current_index >= len(self.clips) or duration <= 0:
            return
        clip = self.clips[self.current_index]
        old_duration = max(1, int(clip.get('duration_ms') or 1))
        old_end = int(clip.get('end_ms') or old_duration)
        duration = int(duration)
        clip['duration_ms'] = duration
        if abs(old_end - old_duration) <= 1000:
            clip['end_ms'] = duration
        else:
            clip['end_ms'] = min(old_end, duration)
        clip['start_ms'] = min(int(clip.get('start_ms', 0)), max(0, clip['end_ms'] - 1))
        self.slider.setRange(0, max(1, duration))
        self.slider.setValues(clip['start_ms'], clip['end_ms'], emit=False)
        self.start_edit.setText(format_ms(clip['start_ms']))
        self.end_edit.setText(format_ms(clip['end_ms']))
        self._update_current_list_item()

    def _position_changed(self, position):
        duration = 0
        if 0 <= self.current_index < len(self.clips):
            duration = int(self.clips[self.current_index].get('duration_ms') or 0)
        self.slider.setPosition(position, emit=False)
        self.position_label.setText(f'{format_ms(position)} / {format_ms(duration)}')

    def _playback_state_changed(self, state):
        self.btn_play.setText('⏸ PAUSAR' if state == QMediaPlayer.PlaybackState.PlayingState else '▶ PLAY')

    def toggle_play(self):
        if self.current_index < 0:
            return
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            self.preview_timer.stop()
            self.preview_end_ms = 0
            self.player.play()

    def seek_to(self, position):
        if self.current_index < 0:
            return
        self.preview_timer.stop()
        self.preview_end_ms = 0
        self.player.pause()
        self.player.setPosition(int(position))

    def _range_changed(self, start, end):
        if self.current_index < 0 or self.current_index >= len(self.clips):
            return
        clip = self.clips[self.current_index]
        clip['start_ms'], clip['end_ms'] = int(start), int(end)
        self.start_edit.setText(format_ms(start))
        self.end_edit.setText(format_ms(end))
        self._update_current_list_item()

    def _update_current_list_item(self):
        row = self.current_index
        if 0 <= row < len(self.clips) and row < self.list_widget.count():
            self.list_widget.item(row).setText(self._clip_text(row, self.clips[row]))

    def _time_field_changed(self, which):
        if self.current_index < 0:
            return
        clip = self.clips[self.current_index]
        duration = int(clip.get('duration_ms') or 0)
        try:
            start = min(parse_time(self.start_edit.text()), duration)
            end = min(parse_time(self.end_edit.text()), duration)
            if end <= start:
                raise ValueError('O fim precisa ser depois do início.')
            clip['start_ms'], clip['end_ms'] = start, end
            self.slider.setValues(start, end, emit=False)
            self._range_changed(start, end)
            self.seek_to(start if which == 'start' else end)
        except ValueError as exc:
            QMessageBox.warning(self, APP_NAME, str(exc))
            self.start_edit.setText(format_ms(clip['start_ms']))
            self.end_edit.setText(format_ms(clip['end_ms']))

    def _adjust_boundary(self, which, delta):
        if self.current_index < 0:
            return
        clip = self.clips[self.current_index]
        duration = int(clip.get('duration_ms') or 0)
        start, end = int(clip['start_ms']), int(clip['end_ms'])
        if which == 'start':
            start = max(0, min(start + int(delta), end - 1))
            seek = start
        else:
            end = min(duration, max(end + int(delta), start + 1))
            seek = end
        self.slider.setValues(start, end, emit=False)
        self._range_changed(start, end)
        self.seek_to(seek)

    def _mark_here(self, which):
        if self.current_index < 0:
            return
        pos = int(self.player.position())
        clip = self.clips[self.current_index]
        start, end = int(clip['start_ms']), int(clip['end_ms'])
        if which == 'start':
            start = min(pos, end - 1)
        else:
            end = max(pos, start + 1)
        self.slider.setValues(start, end, emit=False)
        self._range_changed(start, end)
        self.player.pause()

    def preview_range(self):
        if self.current_index < 0:
            QMessageBox.warning(self, APP_NAME, 'Selecione um vídeo da lista.')
            return
        clip = self.clips[self.current_index]
        self.preview_end_ms = int(clip['end_ms'])
        self.player.setPosition(int(clip['start_ms']))
        self.player.play()
        self.preview_timer.start()

    def _check_preview_end(self):
        if self.preview_end_ms and self.player.position() >= self.preview_end_ms:
            self.preview_timer.stop()
            self.player.pause()
            self.player.setPosition(self.preview_end_ms)

    def _set_export_busy(self, busy):
        self.btn_export.setEnabled(not busy)
        self.btn_add.setEnabled(not busy)
        self.btn_remove.setEnabled(not busy)
        self.btn_up.setEnabled(not busy)
        self.btn_down.setEnabled(not busy)

    def _set_progress(self, value):
        value = max(0, min(100, int(value)))
        self.progress.setValue(value)
        self.percent.setText(f'{value}%')

    def export_video(self):
        if self.worker and self.worker.isRunning():
            return
        if len(self.clips) < 2:
            QMessageBox.warning(self, APP_NAME, 'Adicione pelo menos 2 vídeos para unir.')
            return
        for clip in self.clips:
            if int(clip['end_ms']) <= int(clip['start_ms']):
                QMessageBox.warning(self, APP_NAME, f'Intervalo inválido em {Path(clip["path"]).name}.')
                return
        self.player.pause()
        self.preview_timer.stop()
        self._set_progress(0)
        self._set_export_busy(True)
        self.status.setText('Preparando os trechos...')
        self.worker = JoinWorker(self.clips, self.output_name.text())
        self.worker.progress.connect(self._set_progress)
        self.worker.message.connect(self.status.setText)
        self.worker.done.connect(self._export_done)
        self.worker.failed.connect(self._export_failed)
        self.worker.start()

    def _export_done(self, path):
        self._set_export_busy(False)
        self._set_progress(100)
        self.status.setText(f'Vídeo final salvo: {Path(path).name}')
        if QMessageBox.question(self, APP_NAME, 'Vídeo final concluído. Abrir a pasta de vídeos?') == QMessageBox.StandardButton.Yes:
            self.open_folder()

    def _export_failed(self, message):
        self._set_export_busy(False)
        self.status.setText('Falha ao gerar o vídeo final.')
        QMessageBox.critical(self, APP_NAME, message)

    def open_folder(self):
        VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
        if os.name == 'nt':
            os.startfile(str(VIDEOS_DIR))
        else:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(VIDEOS_DIR)))

    def shutdown(self):
        self.preview_timer.stop()
        self.player.stop()
        if self.worker and self.worker.isRunning():
            self.worker.wait(3000)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f'{APP_NAME} — {APP_VERSION}')
        screen = QApplication.primaryScreen()
        if screen:
            g = screen.availableGeometry()
            self.resize(min(1180, int(g.width() * 0.9)), min(900, int(g.height() * 0.9)))
        else:
            self.resize(1100, 820)
        self.setMinimumSize(760, 620)

        self.download_worker = None
        self.update_worker = None
        self.cut_worker = None
        self.selected_video = None
        self.duration_ms = 0
        self.preview_end_ms = 0

        self.player = QMediaPlayer(self)
        self.audio = QAudioOutput(self)
        self.player.setAudioOutput(self.audio)
        self.preview_timer = QTimer(self)
        self.preview_timer.setInterval(80)
        self.preview_timer.timeout.connect(self._check_preview_end)

        self._build_ui()
        self._refresh_binary_status()
        self._load_proxy_ui()

    def _build_ui(self):
        tabs = QTabWidget()
        self.setCentralWidget(tabs)

        main_scroll = QScrollArea(); main_scroll.setWidgetResizable(True)
        main_page = QWidget(); main_scroll.setWidget(main_page)
        tabs.addTab(main_scroll, 'Baixar')
        main_layout = QVBoxLayout(main_page)
        main_layout.setContentsMargins(24, 22, 24, 24); main_layout.setSpacing(16)

        title = QLabel('EXTRATOR VIDEOS // PORTABLE STUDIO')
        title.setObjectName('AppTitle')
        main_layout.addWidget(title)
        subtitle = QLabel('Download, edição em timeline e compressão inteligente em um único fluxo.')
        subtitle.setObjectName('Subtitle'); subtitle.setWordWrap(True)
        main_layout.addWidget(subtitle)
        self.connection_badge = QLabel('● CONEXÃO DIRETA')
        self.connection_badge.setObjectName('StatusBadge')
        self.connection_badge.setMaximumWidth(250)
        main_layout.addWidget(self.connection_badge)

        download_box = QGroupBox('DOWNLOAD RÁPIDO')
        d = QVBoxLayout(download_box)
        self.url_edit = QLineEdit(); self.url_edit.setPlaceholderText('Cole aqui o link do vídeo')
        d.addWidget(self.url_edit)
        rowq = QHBoxLayout(); rowq.addWidget(QLabel('Qualidade:'))
        self.quality_combo = QComboBox(); self.quality_combo.addItems(QUALIDADES); self.quality_combo.setCurrentIndex(2)
        rowq.addWidget(self.quality_combo, 1); d.addLayout(rowq)
        rowb = QHBoxLayout()
        self.btn_download = QPushButton('↓ BAIXAR VÍDEO'); self.btn_download.setProperty('role', 'primary')
        self.btn_cancel = QPushButton('CANCELAR'); self.btn_cancel.setProperty('role', 'danger'); self.btn_cancel.setEnabled(False)
        self.btn_update = QPushButton('↻ ATUALIZAR yt-dlp')
        self.btn_folder = QPushButton('▣ ABRIR PASTA DE VÍDEOS')
        rowb.addWidget(self.btn_download); rowb.addWidget(self.btn_cancel); rowb.addWidget(self.btn_update); rowb.addWidget(self.btn_folder)
        d.addLayout(rowb)
        prog = QHBoxLayout(); self.download_progress = QProgressBar(); self.download_progress.setRange(0,100); self.download_progress.setFormat('Download: %p%')
        self.download_percent = QLabel('0%'); self.download_percent.setMinimumWidth(44)
        prog.addWidget(self.download_progress,1); prog.addWidget(self.download_percent); d.addLayout(prog)
        self.download_status = QLabel('Aguardando link. Escolha a qualidade.'); self.download_status.setWordWrap(True); d.addWidget(self.download_status)
        self.binary_status = QLabel(''); self.binary_status.setWordWrap(True); d.addWidget(self.binary_status)
        main_layout.addWidget(download_box)

        editor_hint = QLabel('FLUXO RECOMENDADO  •  Após baixar, abra o Editor / Timeline para cortar, unir, ajustar em milissegundos e exportar com compressão inteligente.')
        editor_hint.setObjectName('InfoBanner'); editor_hint.setWordWrap(True)
        main_layout.addWidget(editor_hint)
        main_layout.addStretch(1)

        editor_scroll = QScrollArea(); editor_scroll.setWidgetResizable(True)
        self.editor_page = AdvancedVideoEditorWidget(VIDEOS_DIR, FFMPEG_EXE, FFPROBE_EXE, self); editor_scroll.setWidget(self.editor_page)
        tabs.addTab(editor_scroll, 'Editor  /  Timeline')

        proxy_page = QWidget(); tabs.addTab(proxy_page, 'Proxy')
        p = QVBoxLayout(proxy_page); p.setContentsMargins(18,18,18,18); p.setSpacing(12)
        pt = QLabel('CONEXÃO // PROXY'); pt.setObjectName('PageTitle'); p.addWidget(pt)
        desc = QLabel('Use conexão direta normalmente. Ative o proxy apenas quando a rede exigir. Usuário e senha ficam somente nesta sessão e não são gravados.')
        desc.setWordWrap(True); p.addWidget(desc)
        mode = QGroupBox('Modo de conexão'); ml = QVBoxLayout(mode)
        self.radio_direct = QRadioButton('Conexão direta (sem proxy)')
        self.radio_proxy = QRadioButton('Usar proxy')
        ml.addWidget(self.radio_direct); ml.addWidget(self.radio_proxy); p.addWidget(mode)
        box = QGroupBox('Dados do proxy'); formp = QFormLayout(box)
        self.proxy_server = QLineEdit(); self.proxy_server.setPlaceholderText('Ex.: proxy.empresa.local ou 10.0.0.10')
        self.proxy_port = QLineEdit(); self.proxy_port.setPlaceholderText('Ex.: 8080')
        self.proxy_user = QLineEdit(); self.proxy_user.setPlaceholderText('Usuário (se exigido)')
        self.proxy_password = QLineEdit(); self.proxy_password.setEchoMode(QLineEdit.EchoMode.Password); self.proxy_password.setPlaceholderText('Senha (não é salva)')
        formp.addRow('Servidor:', self.proxy_server); formp.addRow('Porta:', self.proxy_port); formp.addRow('Usuário:', self.proxy_user); formp.addRow('Senha:', self.proxy_password)
        p.addWidget(box)
        pr = QHBoxLayout(); self.btn_save_proxy = QPushButton('SALVAR CONFIGURAÇÃO'); self.btn_save_proxy.setProperty('role', 'primary')
        self.btn_clear_proxy = QPushButton('USAR CONEXÃO DIRETA')
        pr.addWidget(self.btn_save_proxy); pr.addWidget(self.btn_clear_proxy); pr.addStretch(1); p.addLayout(pr)
        self.proxy_status = QLabel('Conexão atual: DIRETA'); self.proxy_status.setWordWrap(True); p.addWidget(self.proxy_status); p.addStretch(1)

        self.btn_download.clicked.connect(self.download_video); self.btn_cancel.clicked.connect(self.cancel_download)
        self.btn_update.clicked.connect(self.update_ytdlp); self.btn_folder.clicked.connect(self.open_videos_folder)
        self.btn_save_proxy.clicked.connect(self.save_proxy_settings); self.btn_clear_proxy.clicked.connect(self.use_direct_connection)
        self.radio_direct.toggled.connect(self._proxy_mode_changed); self.radio_proxy.toggled.connect(self._proxy_mode_changed)

    def _connect_player(self):
        self.player.durationChanged.connect(self.on_duration_changed)
        self.player.positionChanged.connect(self.on_position_changed)
        self.player.playbackStateChanged.connect(self.on_playback_state_changed)
        self.player.errorOccurred.connect(self.on_player_error)

    def _refresh_binary_status(self):
        items=[]
        items.append('yt-dlp: OK' if YTDLP_EXE.exists() else 'yt-dlp: AUSENTE')
        items.append('FFmpeg: OK' if FFMPEG_EXE.exists() else 'FFmpeg: AUSENTE')
        items.append('FFprobe: OK' if FFPROBE_EXE.exists() else 'FFprobe: opcional/ausente')
        items.append('Deno: OK' if DENO_EXE.exists() else 'Deno: AUSENTE')
        self.binary_status.setText(' | '.join(items))

    def _load_proxy_ui(self):
        cfg=load_proxy_config(); enabled=bool(cfg.get('ATIVADO'))
        self.proxy_server.setText(str(cfg.get('SERVIDOR') or '')); self.proxy_port.setText(str(cfg.get('PORTA') or ''))
        self.radio_proxy.setChecked(enabled); self.radio_direct.setChecked(not enabled); self._proxy_mode_changed()

    def _proxy_mode_changed(self):
        active=self.radio_proxy.isChecked()
        for w in (self.proxy_server,self.proxy_port,self.proxy_user,self.proxy_password): w.setEnabled(active)
        self._update_proxy_status()

    def _current_proxy_url(self, show_error=True):
        if not self.radio_proxy.isChecked(): return ''
        try:
            return build_proxy_url(self.proxy_server.text(),self.proxy_port.text(),self.proxy_user.text(),self.proxy_password.text())
        except Exception as exc:
            if show_error: QMessageBox.warning(self, APP_NAME, str(exc))
            return None

    def _update_proxy_status(self):
        if not self.radio_proxy.isChecked():
            text='Conexão atual: DIRETA'
            if hasattr(self, 'connection_badge'):
                self.connection_badge.setText('● CONEXÃO DIRETA')
        else:
            server=self.proxy_server.text().strip() or '(servidor não informado)'; port=self.proxy_port.text().strip() or '?'
            text=f'Conexão atual: PROXY ATIVO — {server}:{port}'
            if self.proxy_user.text().strip(): text += ' — autenticação nesta sessão'
            if hasattr(self, 'connection_badge'):
                self.connection_badge.setText('● PROXY ATIVO')
        self.proxy_status.setText(text)

    def save_proxy_settings(self):
        if self.radio_proxy.isChecked() and self._current_proxy_url(show_error=True) is None: return
        try:
            save_proxy_config(self.radio_proxy.isChecked(), self.proxy_server.text(), self.proxy_port.text())
            self._update_proxy_status()
            QMessageBox.information(self, APP_NAME, 'Configuração salva. Usuário e senha não foram gravados.')
        except Exception as exc:
            QMessageBox.critical(self, APP_NAME, f'Não foi possível salvar a configuração: {exc}')

    def use_direct_connection(self):
        self.radio_direct.setChecked(True); self.proxy_user.clear(); self.proxy_password.clear()
        try: save_proxy_config(False, self.proxy_server.text(), self.proxy_port.text())
        except Exception: pass
        self._proxy_mode_changed()

    def _set_download_busy(self, busy):
        self.btn_download.setEnabled(not busy); self.btn_cancel.setEnabled(busy); self.quality_combo.setEnabled(not busy)
        self.btn_update.setEnabled(not busy)

    def _update_download_progress(self, value):
        value=max(0,min(100,int(value))); self.download_progress.setValue(value); self.download_percent.setText(f'{value}%')

    def _update_cut_progress(self, value):
        value=max(0,min(100,int(value))); self.cut_progress.setValue(value); self.cut_percent.setText(f'{value}%')
        if value: self.cut_status.setText(f'Cortando vídeo... {value}%')

    def download_video(self):
        url=self.url_edit.text().strip()
        if not re.match(r'(?i)^https?://.+',url): QMessageBox.warning(self,APP_NAME,'Cole um link começando com http:// ou https://'); return
        if self.download_worker and self.download_worker.isRunning(): return
        proxy=self._current_proxy_url(True)
        if proxy is None: return
        self._update_proxy_status(); self._update_download_progress(0); self.download_status.setText('Analisando página...'); self._set_download_busy(True)
        self.download_worker=DownloadWorker(url,self.quality_combo.currentIndex(),proxy)
        self.download_worker.progress.connect(self._update_download_progress); self.download_worker.message.connect(self.download_status.setText)
        self.download_worker.done.connect(self.download_finished); self.download_worker.failed.connect(self.download_failed); self.download_worker.canceled.connect(self.download_canceled)
        self.download_worker.start()

    def cancel_download(self):
        if self.download_worker and self.download_worker.isRunning(): self.download_status.setText('Cancelando...'); self.download_worker.cancel()

    def download_finished(self,path):
        self._set_download_busy(False); self._update_download_progress(100); self.download_status.setText('Download concluído.')
        if QMessageBox.question(self,APP_NAME,'Vídeo salvo com sucesso. Abrir a pasta de vídeos?')==QMessageBox.StandardButton.Yes: self.open_videos_folder()

    def download_failed(self,message):
        self._set_download_busy(False); self.download_status.setText('Falha no download.'); QMessageBox.critical(self,APP_NAME,friendly_network_error(message))

    def download_canceled(self):
        self._set_download_busy(False); self.download_status.setText('Download cancelado.')

    def update_ytdlp(self):
        if self.update_worker and self.update_worker.isRunning(): return
        if self.download_worker and self.download_worker.isRunning(): return
        proxy=self._current_proxy_url(True)
        if proxy is None: return
        self.btn_update.setEnabled(False); self.download_status.setText('Atualizando yt-dlp...')
        self.update_worker=UpdateWorker(proxy); self.update_worker.done.connect(self.update_finished); self.update_worker.failed.connect(self.update_failed); self.update_worker.start()

    def update_finished(self,message):
        self.btn_update.setEnabled(True); self.download_status.setText('yt-dlp atualizado.'); QMessageBox.information(self,APP_NAME,message)

    def update_failed(self,message):
        self.btn_update.setEnabled(True); self.download_status.setText('Falha ao atualizar yt-dlp.'); QMessageBox.critical(self,APP_NAME,message)

    def open_videos_folder(self):
        VIDEOS_DIR.mkdir(parents=True,exist_ok=True)
        if os.name=='nt': os.startfile(str(VIDEOS_DIR))
        else: QDesktopServices.openUrl(QUrl.fromLocalFile(str(VIDEOS_DIR)))

    def select_video(self):
        file,_=QFileDialog.getOpenFileName(self,'Selecionar vídeo',str(VIDEOS_DIR),'Vídeos (*.mp4 *.mkv *.webm *.mov *.avi);;Todos os arquivos (*)')
        if file: self.load_video(Path(file))

    def load_video(self,path):
        self.preview_end_ms=0; self.player.stop(); self.selected_video=Path(path); self.selected_label.setText(self.selected_video.name)
        self.cut_status.setText('Vídeo carregado. Ajuste o início e o fim do corte.')
        self.player.setSource(QUrl.fromLocalFile(str(self.selected_video)))

    def on_duration_changed(self,duration):
        self.duration_ms=max(0,int(duration)); self.range_slider.setRange(0,max(1,self.duration_ms)); self.range_slider.setValues(0,max(1,self.duration_ms)); self.range_changed(0,self.duration_ms)

    def on_position_changed(self,position):
        self.range_slider.setPosition(position); self.position_label.setText(f'{format_ms(position)} / {format_ms(self.duration_ms)}')

    def on_playback_state_changed(self,state):
        self.btn_play.setText('⏸ PAUSAR' if state==QMediaPlayer.PlaybackState.PlayingState else '▶ PLAY')

    def on_player_error(self,error,error_string): self.cut_status.setText(f'Pré-visualização: {error_string}')

    def toggle_play(self):
        if not self.selected_video: return
        if self.player.playbackState()==QMediaPlayer.PlaybackState.PlayingState: self.player.pause()
        else: self.player.play()

    def preview_range(self):
        if not self.selected_video: QMessageBox.warning(self,APP_NAME,'Selecione um vídeo primeiro.'); return
        start,end=self.range_slider.values(); self.preview_end_ms=end; self.player.setPosition(start); self.player.play(); self.preview_timer.start()

    def _check_preview_end(self):
        if self.preview_end_ms and self.player.position()>=self.preview_end_ms:
            self.preview_timer.stop(); self.player.pause(); self.player.setPosition(self.preview_end_ms)

    def range_changed(self,start,end): self.start_edit.setText(format_ms(start)); self.end_edit.setText(format_ms(end))

    def seek_to(self,position):
        if self.selected_video:
            self.preview_timer.stop(); self.preview_end_ms=0
            self.player.pause(); self.player.setPosition(int(position))

    def time_field_changed(self, which):
        if self.duration_ms<=0: return
        old_start, old_end = self.range_slider.values()
        try:
            start=min(parse_time(self.start_edit.text()),self.duration_ms)
            end=min(parse_time(self.end_edit.text()),self.duration_ms)
            if end<=start: raise ValueError('O fim precisa ser depois do início.')
            self.range_slider.setValues(start,end,emit=True)
            self.seek_to(start if which == 'start' else end)
        except ValueError as exc:
            self.start_edit.setText(format_ms(old_start)); self.end_edit.setText(format_ms(old_end))
            QMessageBox.warning(self,APP_NAME,str(exc))

    def _adjust_cut_boundary(self, which, delta):
        if not self.selected_video or self.duration_ms<=0: return
        start,end=self.range_slider.values()
        if which=='start':
            start=max(0,min(start+int(delta),end-1)); seek=start
        else:
            end=min(self.duration_ms,max(end+int(delta),start+1)); seek=end
        self.range_slider.setValues(start,end,emit=True)
        self.seek_to(seek)

    def _mark_cut_here(self, which):
        if not self.selected_video or self.duration_ms<=0: return
        pos=max(0,min(int(self.player.position()),self.duration_ms))
        start,end=self.range_slider.values()
        if which=='start':
            start=min(pos,end-1)
        else:
            end=max(pos,start+1)
        self.range_slider.setValues(start,end,emit=True)
        self.player.pause()

    def cut_video(self):
        if not self.selected_video: QMessageBox.warning(self,APP_NAME,'Selecione um vídeo primeiro.'); return
        if self.cut_worker and self.cut_worker.isRunning(): return
        start,end=self.range_slider.values()
        if end<=start: QMessageBox.warning(self,APP_NAME,'Escolha um intervalo válido.'); return
        self.player.pause(); self._update_cut_progress(0); self.cut_status.setText('Preparando corte com sincronização precisa em milissegundos...'); self.btn_cut.setEnabled(False)
        self.cut_worker=CutWorker(self.selected_video,start,end); self.cut_worker.progress.connect(self._update_cut_progress); self.cut_worker.done.connect(self.cut_finished); self.cut_worker.failed.connect(self.cut_failed); self.cut_worker.start()

    def cut_finished(self,path):
        self.btn_cut.setEnabled(True); self._update_cut_progress(100); self.cut_status.setText(f'Corte salvo: {Path(path).name}')
        if QMessageBox.question(self,APP_NAME,'Corte concluído. Abrir a pasta de vídeos?')==QMessageBox.StandardButton.Yes: self.open_videos_folder()

    def cut_failed(self,message):
        self.btn_cut.setEnabled(True); self.cut_status.setText('Falha no corte.'); QMessageBox.critical(self,APP_NAME,message)

    def closeEvent(self,event):
        self.preview_timer.stop(); self.player.stop()
        if hasattr(self, 'editor_page'): self.editor_page.shutdown()
        if self.download_worker and self.download_worker.isRunning(): self.download_worker.cancel(); self.download_worker.wait(3000)
        super().closeEvent(event)


def main():
    app=QApplication(sys.argv); app.setApplicationName(APP_NAME); app.setOrganizationName('ExtratorVideos')
    app.setStyle('Fusion')
    app.setStyleSheet(FUTURE_STYLESHEET)
    window=MainWindow(); window.show(); sys.exit(app.exec())


if __name__=='__main__':
    main()
