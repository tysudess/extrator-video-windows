import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import main as core
import novo_layout  # mantém a identidade visual premium e o editor já aprovado

from PySide6.QtCore import QByteArray, Qt, QThread, Signal
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication, QButtonGroup, QComboBox, QFormLayout, QFrame, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QMessageBox, QProgressBar, QPushButton,
    QRadioButton, QScrollArea, QSizePolicy, QStackedWidget, QVBoxLayout,
    QWidget,
)

core.APP_VERSION = 'Windows Portable v1.9.20 — Live do início até agora'

# A referência visual usa seis níveis explícitos. O motor passa a suportá-los de verdade.
core.QUALIDADES = (
    '2160p (4K)', '1440p (2K)', '1080p (Full HD)',
    '720p (HD)', '480p', '360p',
)
core.FORMATS = tuple(
    f'bv*[height<={h}][ext=mp4]+ba[ext=m4a]/b[height<={h}][ext=mp4]/bv*[height<={h}]+ba/b[height<={h}]/b'
    for h in (2160, 1440, 1080, 720, 480, 360)
)
core.COMPAT_FORMATS = tuple(
    f'b[height<={h}][ext=mp4]/b[height<={h}]/b'
    for h in (2160, 1440, 1080, 720, 480, 360)
)

REFINED_STYLE = r'''
QWidget#RefinedRoot { background-color:#070A12; }
QFrame#RefinedSidebar {
    background:qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #080D19, stop:1 #070A12);
    border-right:1px solid #202942;
}
QFrame#RefinedContent { background-color:#080C15; }
QFrame#RefinedRight { background-color:#070A12; }
QFrame#RefinedCard, QFrame#RefinedHero, QFrame#RefinedSideCard {
    background:qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #0D1421, stop:1 #0A111D);
    border:1px solid #25314A;
    border-radius:15px;
}
QLabel#RefinedBrandMark {
    color:#FFFFFF;
    background:qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #8C30F3, stop:.52 #4F48FF, stop:1 #16A0F6);
    border:1px solid #7366FF;
    border-radius:11px;
    font-size:18pt;
    font-weight:900;
}
QLabel#RefinedBrandTitle { color:#FFFFFF; font-size:14pt; font-weight:850; }
QLabel#RefinedBrandSub { color:#A8B2C7; font-size:9pt; }
QPushButton#RefinedNav {
    background:transparent; color:#C2CAD8; border:1px solid transparent;
    border-radius:10px; padding:10px 12px; text-align:left; font-size:10pt; font-weight:650;
}
QPushButton#RefinedNav:hover { background:#10182A; border-color:#273653; color:#FFFFFF; }
QPushButton#RefinedNav:checked {
    background:qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #4D2AC0, stop:.55 #3131A6, stop:1 #1B518D);
    border:1px solid #6158D6; color:#FFFFFF;
}
QPushButton#RefinedSmallButton {
    background:#0D1421; color:#DAE2F1; border:1px solid #27344D;
    border-radius:9px; padding:8px;
}
QPushButton#RefinedSmallButton:hover { border-color:#5C55C6; background:#141D30; }
QLabel#RefinedVersion { color:#8D98AD; font-size:8pt; }
QLabel#RefinedMainTitle { color:#FFFFFF; font-size:20pt; font-weight:850; }
QLabel#RefinedMainSub { color:#ABB4C6; font-size:10pt; }
QLabel#RefinedCardTitle { color:#F1F5FB; font-size:11pt; font-weight:800; }
QLabel#RefinedText { color:#B3BDCF; font-size:9pt; }
QLabel#RefinedMuted { color:#8390A6; font-size:8.5pt; }
QLabel#RefinedAccentTitle { color:#A957FF; font-size:16pt; font-weight:850; }
QLineEdit#RefinedUrl {
    background:#0A101B; color:#F4F7FB; border:1px solid #3A4256; border-radius:9px;
    padding:10px 12px; min-height:26px; font-size:10pt;
}
QLineEdit#RefinedUrl:focus { border-color:#7364FF; }
QPushButton#RefinedPrimary {
    background:qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #7F26EB, stop:.52 #5B3AF5, stop:1 #256EFF);
    color:#FFFFFF; border:1px solid #7569FF; border-radius:10px;
    padding:10px 18px; min-height:26px; font-weight:800;
}
QPushButton#RefinedPrimary:hover {
    background:qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #9136F6, stop:.52 #6D4BFF, stop:1 #3782FF);
}
QPushButton#RefinedGhost {
    background:#0E1624; color:#D8E1F0; border:1px solid #293650; border-radius:9px; padding:8px 12px;
}
QProgressBar#RefinedProgress {
    background:#080E17; color:#F3F6FB; border:1px solid #232F45; border-radius:8px; min-height:18px; text-align:center;
}
QProgressBar#RefinedProgress::chunk {
    background:qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #7A2FE8, stop:.55 #5147F3, stop:1 #1B88F4);
    border-radius:7px;
}
QRadioButton#RefinedQuality { color:#ECF1F8; spacing:8px; padding:3px 0; }
QRadioButton#RefinedQuality::indicator { width:15px; height:15px; border-radius:7px; }
QRadioButton#RefinedQuality::indicator:unchecked { background:#0A111D; border:1px solid #5A667D; }
QRadioButton#RefinedQuality::indicator:checked { background:#623BEE; border:2px solid #A47AFF; }
QFrame#RefinedFeature { background:#0D1421; border:1px solid #243149; border-radius:11px; }
QLabel#RefinedFeatureIcon { color:#8C52FF; font-size:14pt; font-weight:900; }
QLabel#RefinedFeatureTitle { color:#EEF3FA; font-size:9pt; font-weight:750; }
QLabel#RefinedFeatureText { color:#8793A8; font-size:8pt; }
QScrollArea#RefinedScroll { border:none; background:transparent; }
QScrollArea#RefinedScroll > QWidget > QWidget { background:transparent; }

QLabel#LiveBadge {
    background:#3A1118; color:#FF6978; border:1px solid #8B2735;
    border-radius:9px; padding:5px 9px; font-weight:850;
}
QLabel#LiveInfo {
    background:#15111E; color:#EAD7FF; border:1px solid #4A315C;
    border-radius:9px; padding:7px 9px;
}
'''
core.FUTURE_STYLESHEET += '\n' + REFINED_STYLE


def _base_dir():
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _icon_path():
    return _base_dir() / 'ExtratorVideos-Icone.ico'


def _app_icon():
    return QIcon(str(_icon_path()))


def _frame(name='RefinedCard'):
    f = QFrame()
    f.setObjectName(name)
    return f


def _feature(icon, title, text):
    card = _frame('RefinedFeature')
    row = QHBoxLayout(card)
    row.setContentsMargins(12, 10, 12, 10)
    row.setSpacing(9)
    ic = QLabel(icon); ic.setObjectName('RefinedFeatureIcon'); ic.setFixedWidth(25)
    row.addWidget(ic)
    col = QVBoxLayout(); col.setSpacing(1)
    t = QLabel(title); t.setObjectName('RefinedFeatureTitle')
    s = QLabel(text); s.setObjectName('RefinedFeatureText'); s.setWordWrap(True)
    col.addWidget(t); col.addWidget(s)
    row.addLayout(col, 1)
    return card


class AnalyzeWorker(QThread):
    done = Signal(dict)
    failed = Signal(str)

    def __init__(self, url, proxy_url=''):
        super().__init__()
        self.url = url
        self.proxy_url = proxy_url or ''

    def run(self):
        try:
            cmd = [
                str(core.YTDLP_EXE), '--no-playlist', '--dump-single-json', '--skip-download',
                '--socket-timeout', '25', '--ffmpeg-location', str(core.BIN_DIR),
            ]
            if core.DENO_EXE.exists():
                cmd += ['--js-runtimes', f'deno:{core.DENO_EXE}']
            if self.proxy_url:
                cmd += ['--proxy', self.proxy_url]
            cmd.append(self.url)
            flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            result = subprocess.run(
                cmd, capture_output=True, text=True, encoding='utf-8', errors='replace',
                creationflags=flags, timeout=90,
            )
            if result.returncode != 0:
                raise RuntimeError((result.stderr or result.stdout or 'Falha ao analisar o vídeo.')[-1500:])
            data = json.loads(result.stdout)
            duration = float(data.get('duration') or 0)
            heights = (2160, 1440, 1080, 720, 480, 360)
            estimates = {}
            formats = data.get('formats') or []
            for target in heights:
                candidates = []
                for fmt in formats:
                    h = int(fmt.get('height') or 0)
                    if h <= 0 or h > target:
                        continue
                    size = fmt.get('filesize') or fmt.get('filesize_approx')
                    tbr = fmt.get('tbr')
                    if not size and tbr and duration:
                        size = float(tbr) * 1000.0 * duration / 8.0
                    if size:
                        candidates.append((h, float(size)))
                if candidates:
                    max_h = max(h for h, _ in candidates)
                    same = [s for h, s in candidates if h == max_h]
                    estimates[target] = max(same) if same else 0
            thumb_bytes = b''
            thumb = data.get('thumbnail') or ''
            if thumb:
                try:
                    req = urllib.request.Request(thumb, headers={'User-Agent':'Mozilla/5.0'})
                    with urllib.request.urlopen(req, timeout=12) as resp:
                        thumb_bytes = resp.read(2_000_000)
                except Exception:
                    pass
            live_status = str(data.get('live_status') or '')
            is_live = bool(data.get('is_live') or live_status == 'is_live')
            start_timestamp = data.get('release_timestamp') or data.get('timestamp')
            snapshot_timestamp = int(time.time())
            live_elapsed = 0
            if is_live and start_timestamp:
                try:
                    live_elapsed = max(0, snapshot_timestamp - int(float(start_timestamp)))
                except Exception:
                    live_elapsed = 0
            if is_live and live_elapsed <= 0 and duration:
                live_elapsed = int(duration)

            self.done.emit({
                'title': data.get('title') or 'Vídeo',
                'channel': data.get('channel') or data.get('uploader') or 'Fonte não informada',
                'duration': int(duration),
                'width': int(data.get('width') or 0),
                'height': int(data.get('height') or 0),
                'estimates': estimates,
                'thumbnail_bytes': thumb_bytes,
                'webpage_url': data.get('webpage_url') or self.url,
                'analyzed_input_url': self.url,
                'live_status': live_status,
                'is_live': is_live,
                'live_start_timestamp': int(float(start_timestamp)) if start_timestamp else 0,
                'analysis_snapshot_timestamp': snapshot_timestamp,
                'live_elapsed': int(live_elapsed),
            })
        except Exception as exc:
            self.failed.emit(str(exc))



class LiveSnapshotWorker(QThread):
    """Baixa uma live do início até o instante capturado ao iniciar o download.

    O primeiro método usa o recorte temporal nativo do yt-dlp em conjunto com
    --live-from-start. Como esse recurso ainda é experimental para lives, há uma
    segunda tentativa com formato MP4 combinado mais compatível. Nunca cai
    silenciosamente para "a partir de agora", porque isso mudaria o pedido do usuário.
    """
    progress = Signal(int)
    message = Signal(str)
    done = Signal(str)
    failed = Signal(str)
    canceled = Signal()

    def __init__(self, url, quality_index, proxy_url='', known_start_timestamp=0):
        super().__init__()
        self.url = url
        self.quality_index = max(0, min(len(core.FORMATS)-1, int(quality_index)))
        self.proxy_url = proxy_url or ''
        self.known_start_timestamp = int(known_start_timestamp or 0)
        self._cancel_requested = False
        self._process = None

    def cancel(self):
        self._cancel_requested = True
        try:
            if self._process and self._process.poll() is None:
                self._process.terminate()
        except Exception:
            pass

    def _base_common(self):
        cmd = [
            str(core.YTDLP_EXE), '--no-playlist', '--newline', '--progress',
            '--windows-filenames', '--trim-filenames', '180', '--retries', '10',
            '--fragment-retries', '10', '--retry-sleep', 'fragment:linear=1::3',
            '--socket-timeout', '30', '--ffmpeg-location', str(core.BIN_DIR),
        ]
        if core.DENO_EXE.exists():
            cmd += ['--js-runtimes', f'deno:{core.DENO_EXE}']
        if self.proxy_url:
            cmd += ['--proxy', self.proxy_url]
        return cmd

    def _refresh_target(self):
        """Confirma que continua ao vivo e captura o ponto final neste instante."""
        cmd = [
            str(core.YTDLP_EXE), '--no-playlist', '--dump-single-json', '--skip-download',
            '--socket-timeout', '25', '--ffmpeg-location', str(core.BIN_DIR),
        ]
        if core.DENO_EXE.exists():
            cmd += ['--js-runtimes', f'deno:{core.DENO_EXE}']
        if self.proxy_url:
            cmd += ['--proxy', self.proxy_url]
        cmd.append(self.url)
        flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', creationflags=flags, timeout=90)
        if result.returncode != 0:
            raise RuntimeError((result.stderr or result.stdout or 'Falha ao confirmar a live.')[-1600:])
        data = json.loads(result.stdout)
        status = str(data.get('live_status') or '')
        if not (data.get('is_live') or status == 'is_live'):
            raise RuntimeError('O link não está mais ao vivo. Analise novamente; se a transmissão terminou, baixe como vídeo normal.')
        start_ts = data.get('release_timestamp') or data.get('timestamp') or self.known_start_timestamp
        if not start_ts:
            duration = int(float(data.get('duration') or 0))
            if duration <= 0:
                raise RuntimeError('Não foi possível identificar quando a live começou. Esta transmissão pode estar sem DVR desde o início.')
            target = duration
        else:
            target = int(time.time() - float(start_ts))
        # Dá uma pequena margem para evitar cortar o último fragmento no meio.
        target = max(5, target - 2)
        return target, data

    @staticmethod
    def _time_arg(seconds):
        seconds = max(1, int(seconds))
        h, rem = divmod(seconds, 3600)
        m, s = divmod(rem, 60)
        return f'{h:02d}:{m:02d}:{s:02d}'

    def _run_attempt(self, fmt, target_seconds, label):
        self.message.emit(label)
        stamp = time.strftime('%Y%m%d-%H%M%S')
        out_tmpl = str(core.VIDEOS_DIR / f'%(title).150B [LIVE-ATE-AGORA {stamp}] [%(id)s].%(ext)s')
        section = f'*00:00:00-{self._time_arg(target_seconds)}'
        cmd = self._base_common() + [
            '--live-from-start',
            '--download-sections', section,
            '--force-keyframes-at-cuts',
            '--concurrent-fragments', '4',
            '-f', fmt,
            '--merge-output-format', 'mp4', '--remux-video', 'mp4',
            '-o', out_tmpl,
            '--print', 'after_move:FINAL_FILE:%(filepath)s',
            self.url,
        ]
        flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        before = set()
        try:
            for path in core.VIDEOS_DIR.iterdir():
                if path.is_file():
                    before.add(str(path.resolve()).lower())
        except Exception:
            pass
        self._process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                         encoding='utf-8', errors='replace', creationflags=flags)
        final_file = ''
        tail = []
        assert self._process.stdout is not None
        for raw in self._process.stdout:
            if self._cancel_requested:
                try: self._process.terminate()
                except Exception: pass
                return False, '', 'Download cancelado.'
            line = raw.rstrip('\r\n')
            if line.startswith('FINAL_FILE:'):
                final_file = line.split(':',1)[1].strip().strip('"')
            m = re.search(r'(\d{1,3}(?:\.\d+)?)%', line)
            if m:
                self.progress.emit(max(0, min(99, int(float(m.group(1))))))
            if line.strip():
                tail.append(line.strip()); tail = tail[-100:]
                low = line.lower()
                if any(x in low for x in ('[download]', '[youtube]', '[merger]', '[ffmpeg]', 'warning', 'error')):
                    self.message.emit(line.strip()[-220:])
        code = self._process.wait(); self._process = None
        if code == 0:
            candidate = Path(final_file) if final_file else None
            if candidate and candidate.exists() and candidate.stat().st_size > 1024:
                return True, str(candidate), ''
            newest = []
            for ext in ('*.mp4','*.mkv','*.webm','*.mov'):
                for path in core.VIDEOS_DIR.glob(ext):
                    try:
                        if str(path.resolve()).lower() not in before and path.stat().st_size > 1024:
                            newest.append(path)
                    except Exception:
                        pass
            if newest:
                newest.sort(key=lambda x:x.stat().st_mtime, reverse=True)
                return True, str(newest[0]), ''
        return False, final_file, '\n'.join(tail[-80:]) or f'yt-dlp encerrou com código {code}'

    def _ensure_h264(self, path):
        path = Path(path)
        codec = core._probe_video_codec(path)
        if codec in ('h264','avc1'):
            return str(path)
        temp = path.with_name(path.stem + '.h264-temp.mp4')
        self.message.emit('Finalizando o trecho ao vivo em H.264 para máxima compatibilidade…')
        cmd = [str(core.FFMPEG_EXE), '-y', '-hide_banner', '-loglevel', 'error', '-i', str(path),
               '-map','0:v:0','-map','0:a?','-c:v','libx264','-preset','veryfast','-crf','20',
               '-pix_fmt','yuv420p','-c:a','aac','-b:a','160k','-movflags','+faststart', str(temp)]
        flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', creationflags=flags)
        if result.returncode == 0 and temp.exists() and temp.stat().st_size > 1024:
            path.unlink(missing_ok=True); temp.replace(path)
            return str(path)
        temp.unlink(missing_ok=True)
        return str(path)

    def run(self):
        try:
            if not core.YTDLP_EXE.exists() or not core.FFMPEG_EXE.exists():
                raise RuntimeError('yt-dlp/FFmpeg não encontrados na pasta bin.')
            if core.is_youtube(self.url) and not core.DENO_EXE.exists():
                raise RuntimeError('Deno não encontrado. O YouTube atual precisa de runtime JavaScript.')
            self.progress.emit(0)
            self.message.emit('🔴 Confirmando a live e congelando o ponto final…')
            target, _data = self._refresh_target()
            self.message.emit(f'🔴 LIVE: baixar 00:00:00 → {self._time_arg(target)}. A transmissão continuará, mas o arquivo parará nesse ponto.')
            fmt = core.FORMATS[self.quality_index]
            ok, path, err = self._run_attempt(fmt, target, 'Baixando a live desde o início até o ponto congelado…')
            if not ok and not self._cancel_requested:
                compat = core.COMPAT_FORMATS[self.quality_index]
                ok, path, err2 = self._run_attempt(compat, target, 'Tentando modo LIVE compatível (MP4 combinado)…')
                if not ok:
                    err = err2 or err
            if self._cancel_requested:
                self.canceled.emit(); return
            if not ok:
                raise RuntimeError(
                    'Não foi possível recortar esta live do início até agora. O YouTube/yt-dlp ainda trata esse recurso como experimental e algumas lives não expõem DVR/range compatível.\n\n'
                    + (err[-1800:] if err else '')
                )
            path = self._ensure_h264(path)
            self.progress.emit(100)
            self.message.emit('Live salva do início até o ponto em que o download foi iniciado.')
            self.done.emit(path)
        except Exception as exc:
            if self._cancel_requested:
                self.canceled.emit()
            else:
                self.failed.emit(str(exc))

def _format_duration(sec):
    sec = max(0, int(sec or 0))
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f'{h}:{m:02d}:{s:02d}' if h else f'{m:02d}:{s:02d}'


def _format_size(size):
    if not size:
        return '—'
    mb = size / (1024 * 1024)
    if mb >= 1024:
        return f'{mb/1024:.2f} GB'
    return f'{mb:.0f} MB'


def build_refined_ui(self):
    self.setWindowIcon(_app_icon())
    self.setMinimumSize(1180, 720)
    screen = QApplication.primaryScreen()
    if screen:
        g = screen.availableGeometry()
        self.resize(min(1540, int(g.width() * .94)), min(920, int(g.height() * .93)))

    self.analysis_worker = None
    self.analysis_data = {}
    self.quality_estimate_labels = []

    # Compatibilidade com o motor original: _load_proxy_ui() chama
    # _update_proxy_status() logo após a montagem da interface e esse método
    # espera que o selo de conexão já exista.
    self.connection_badge = QLabel('● CONEXÃO DIRETA')
    self.connection_badge.setObjectName('StatusBadge')
    self.connection_badge.hide()

    root = QWidget(); root.setObjectName('RefinedRoot')
    self.setCentralWidget(root)
    root_layout = QHBoxLayout(root); root_layout.setContentsMargins(0,0,0,0); root_layout.setSpacing(0)

    # Sidebar igual à referência
    sidebar = QFrame(); sidebar.setObjectName('RefinedSidebar'); sidebar.setFixedWidth(205)
    sb = QVBoxLayout(sidebar); sb.setContentsMargins(18,20,18,16); sb.setSpacing(6)
    brand = QHBoxLayout(); brand.setSpacing(10)
    mark = QLabel('▶'); mark.setObjectName('RefinedBrandMark'); mark.setAlignment(Qt.AlignmentFlag.AlignCenter); mark.setFixedSize(42,42)
    brand.addWidget(mark)
    bt = QVBoxLayout(); bt.setSpacing(0)
    ttl = QLabel('EXTRATOR'); ttl.setObjectName('RefinedBrandTitle')
    sub = QLabel('DE VÍDEOS'); sub.setObjectName('RefinedBrandSub')
    bt.addWidget(ttl); bt.addWidget(sub); brand.addLayout(bt,1)
    sb.addLayout(brand); sb.addSpacing(13)

    self.ref_nav_group = QButtonGroup(self); self.ref_nav_group.setExclusive(True)
    nav_specs = [
        ('home','⌂   Início'), ('download','↓   Download'), ('editor','✂   Editor'),
        ('history','◷   Histórico'), ('settings','⚙   Configurações'),
    ]
    self.ref_nav = {}
    for key, text in nav_specs:
        b = QPushButton(text); b.setObjectName('RefinedNav'); b.setCheckable(True); b.setCursor(Qt.CursorShape.PointingHandCursor)
        self.ref_nav_group.addButton(b); self.ref_nav[key] = b; sb.addWidget(b)
    self.ref_nav['home'].setChecked(True)
    sb.addStretch(1)

    mini = QHBoxLayout(); mini.setSpacing(8)
    btn_sidebar_folder = QPushButton('▣'); btn_sidebar_folder.setObjectName('RefinedSmallButton'); btn_sidebar_folder.setToolTip('Abrir pasta de vídeos')
    btn_sidebar_folder.clicked.connect(self.open_videos_folder)
    btn_help = QPushButton('?'); btn_help.setObjectName('RefinedSmallButton'); btn_help.setToolTip('Ajuda')
    btn_theme = QPushButton('☾'); btn_theme.setObjectName('RefinedSmallButton'); btn_theme.setToolTip('Tema escuro')
    mini.addWidget(btn_sidebar_folder); mini.addWidget(btn_help); mini.addWidget(btn_theme)
    sb.addLayout(mini)
    ver = QLabel('v1.9.20  •  LIVE + TIMELINE'); ver.setObjectName('RefinedVersion'); ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
    sb.addWidget(ver)
    root_layout.addWidget(sidebar)

    # Centro
    center = QFrame(); center.setObjectName('RefinedContent')
    center_layout = QVBoxLayout(center); center_layout.setContentsMargins(18,16,18,16); center_layout.setSpacing(0)
    self.ref_stack = QStackedWidget(); center_layout.addWidget(self.ref_stack)
    root_layout.addWidget(center, 1)

    # Painel direito permanente, como na referência
    right = QFrame(); right.setObjectName('RefinedRight'); right.setFixedWidth(300)
    rl = QVBoxLayout(right); rl.setContentsMargins(10,16,16,16); rl.setSpacing(12)
    design = _frame('RefinedSideCard'); dl = QVBoxLayout(design); dl.setContentsMargins(18,16,18,16); dl.setSpacing(9)
    dt = QLabel('NOVO DESIGN'); dt.setObjectName('RefinedAccentTitle'); dt.setAlignment(Qt.AlignmentFlag.AlignCenter)
    ds = QLabel('Moderno, intuitivo e acessível'); ds.setObjectName('RefinedMainSub'); ds.setAlignment(Qt.AlignmentFlag.AlignCenter)
    dl.addWidget(dt); dl.addWidget(ds); dl.addSpacing(6)
    for icon, text in [('◫','Interface moderna e limpa'),('▦','Navegação intuitiva'),('◔','Modo claro e escuro'),('⌁','Acessível e responsivo'),('✂','Editor de vídeo completo'),('↓','Download com qualidade'),('◎','Suporte a proxy'),('↔','Reordenação na timeline')]:
        row = QHBoxLayout(); row.setSpacing(9)
        ic = QLabel(icon); ic.setObjectName('RefinedFeatureIcon'); ic.setFixedWidth(25)
        tx = QLabel(text); tx.setObjectName('RefinedText')
        row.addWidget(ic); row.addWidget(tx,1); dl.addLayout(row)
    rl.addWidget(design)

    icon_card = _frame('RefinedSideCard'); il = QVBoxLayout(icon_card); il.setContentsMargins(18,16,18,16); il.setSpacing(10)
    it = QLabel('ÍCONE DO APLICATIVO'); it.setObjectName('RefinedAccentTitle'); it.setAlignment(Qt.AlignmentFlag.AlignCenter); il.addWidget(it)
    self.ref_icon_preview = QLabel(); self.ref_icon_preview.setAlignment(Qt.AlignmentFlag.AlignCenter); self.ref_icon_preview.setMinimumHeight(180)
    pm = QPixmap(str(_icon_path()))
    if not pm.isNull():
        self.ref_icon_preview.setPixmap(pm.scaled(170,170,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation))
    else:
        self.ref_icon_preview.setText('▶')
    il.addWidget(self.ref_icon_preview)
    variants = QLabel('256×256    128×128    64×64    32×32    16×16'); variants.setObjectName('RefinedMuted'); variants.setAlignment(Qt.AlignmentFlag.AlignCenter)
    il.addWidget(variants)
    colors = QLabel('CORES   ■  ■  ■  ■  ■  ■'); colors.setObjectName('RefinedText'); colors.setAlignment(Qt.AlignmentFlag.AlignCenter)
    colors.setStyleSheet('color:#9A5CFF;')
    il.addWidget(colors)
    rl.addWidget(icon_card); rl.addStretch(1)
    root_layout.addWidget(right)

    # ---------------- Página principal / download ----------------
    download_scroll = QScrollArea(); download_scroll.setObjectName('RefinedScroll'); download_scroll.setWidgetResizable(True)
    download_page = QWidget(); download_scroll.setWidget(download_page)
    page = QVBoxLayout(download_page); page.setContentsMargins(0,0,0,0); page.setSpacing(10)

    title = QLabel('EXTRATOR DE VÍDEOS'); title.setObjectName('RefinedMainTitle'); title.setAlignment(Qt.AlignmentFlag.AlignCenter)
    subtitle = QLabel('Baixe, edite e salve com qualidade'); subtitle.setObjectName('RefinedMainSub'); subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
    page.addWidget(title); page.addWidget(subtitle)

    link_card = _frame('RefinedHero'); lc = QVBoxLayout(link_card); lc.setContentsMargins(18,14,18,14); lc.setSpacing(8)
    link_label = QLabel('Cole o link do vídeo'); link_label.setObjectName('RefinedCardTitle'); lc.addWidget(link_label)
    link_row = QHBoxLayout(); link_row.setSpacing(10)
    self.url_edit = QLineEdit(); self.url_edit.setObjectName('RefinedUrl'); self.url_edit.setPlaceholderText('https://www.youtube.com/watch?v=exemplo'); self.url_edit.setClearButtonEnabled(True)
    self.btn_analyze = QPushButton('⌕  ANALISAR'); self.btn_analyze.setObjectName('RefinedPrimary'); self.btn_analyze.setMinimumWidth(135)
    link_row.addWidget(self.url_edit,1); link_row.addWidget(self.btn_analyze); lc.addLayout(link_row)
    page.addWidget(link_card)

    cards = QHBoxLayout(); cards.setSpacing(10)
    # Informação do vídeo
    info = _frame(); info.setMinimumWidth(250); info_l = QVBoxLayout(info); info_l.setContentsMargins(15,14,15,14); info_l.setSpacing(8)
    info_title = QLabel('Informações do vídeo'); info_title.setObjectName('RefinedCardTitle'); info_l.addWidget(info_title)
    info_body = QHBoxLayout(); info_body.setSpacing(10)
    self.video_thumb = QLabel('PRÉVIA'); self.video_thumb.setAlignment(Qt.AlignmentFlag.AlignCenter); self.video_thumb.setFixedSize(125,82)
    self.video_thumb.setStyleSheet('background:#111B2C; color:#586B89; border:1px solid #263852; border-radius:8px;')
    info_body.addWidget(self.video_thumb)
    meta_col = QVBoxLayout(); meta_col.setSpacing(4)
    self.video_title = QLabel('Cole um link e clique em ANALISAR'); self.video_title.setObjectName('RefinedText'); self.video_title.setWordWrap(True)
    self.video_channel = QLabel(''); self.video_channel.setObjectName('RefinedMuted')
    self.video_meta = QLabel(''); self.video_meta.setObjectName('RefinedMuted')
    self.live_badge = QLabel('🔴 AO VIVO  •  DO INÍCIO ATÉ AGORA')
    self.live_badge.setObjectName('LiveBadge'); self.live_badge.hide()
    meta_col.addWidget(self.video_title); meta_col.addWidget(self.video_channel); meta_col.addWidget(self.video_meta); meta_col.addWidget(self.live_badge); meta_col.addStretch(1)
    info_body.addLayout(meta_col,1); info_l.addLayout(info_body); info_l.addStretch(1)
    cards.addWidget(info, 3)

    # Qualidade
    quality = _frame(); ql = QVBoxLayout(quality); ql.setContentsMargins(15,14,15,14); ql.setSpacing(4)
    qtitle = QLabel('Escolha a qualidade'); qtitle.setObjectName('RefinedCardTitle'); ql.addWidget(qtitle)
    self.quality_combo = QComboBox(); self.quality_combo.addItems(core.QUALIDADES); self.quality_combo.setCurrentIndex(1); self.quality_combo.hide(); ql.addWidget(self.quality_combo)
    self.quality_group = QButtonGroup(self); self.quality_group.setExclusive(True)
    self.quality_buttons = []
    labels = [('2160p (4K)','MP4'),('1440p (2K)','MP4'),('1080p (Full HD)','MP4'),('720p (HD)','MP4'),('480p','MP4'),('360p','MP4')]
    for idx, (name, fmt) in enumerate(labels):
        row = QHBoxLayout(); row.setSpacing(8)
        rb = QRadioButton(name); rb.setObjectName('RefinedQuality'); self.quality_group.addButton(rb, idx); self.quality_buttons.append(rb)
        if idx == 1: rb.setChecked(True)
        fmt_l = QLabel(fmt); fmt_l.setObjectName('RefinedMuted'); fmt_l.setFixedWidth(35)
        est = QLabel('—'); est.setObjectName('RefinedMuted'); est.setAlignment(Qt.AlignmentFlag.AlignRight); est.setMinimumWidth(55)
        self.quality_estimate_labels.append(est)
        row.addWidget(rb,1); row.addWidget(fmt_l); row.addWidget(est); ql.addLayout(row)
    ql.addStretch(1); cards.addWidget(quality,3)

    # Resumo
    summary = _frame(); sl = QVBoxLayout(summary); sl.setContentsMargins(15,14,15,14); sl.setSpacing(8)
    stitle = QLabel('Resumo do download'); stitle.setObjectName('RefinedCardTitle'); sl.addWidget(stitle)
    self.summary_format = QLabel('Formato:                         MP4'); self.summary_format.setObjectName('RefinedText')
    self.summary_quality = QLabel('Qualidade:                      1440p (2K)'); self.summary_quality.setObjectName('RefinedText')
    self.summary_size = QLabel('Tamanho estimado:              —'); self.summary_size.setObjectName('RefinedText')
    self.summary_folder = QLabel(f'Pasta de destino:               {core.VIDEOS_DIR.name}'); self.summary_folder.setObjectName('RefinedText')
    sl.addWidget(self.summary_format); sl.addWidget(self.summary_quality); sl.addWidget(self.summary_size); sl.addWidget(self.summary_folder)
    self.live_mode_info = QLabel('')
    self.live_mode_info.setObjectName('LiveInfo'); self.live_mode_info.setWordWrap(True); self.live_mode_info.hide(); sl.addWidget(self.live_mode_info)
    self.btn_download = QPushButton('↓  BAIXAR'); self.btn_download.setObjectName('RefinedPrimary'); sl.addWidget(self.btn_download)
    small_actions = QHBoxLayout(); small_actions.setSpacing(6)
    self.btn_folder = QPushButton('▣ Pasta'); self.btn_folder.setObjectName('RefinedGhost')
    self.btn_update = QPushButton('↻ yt-dlp'); self.btn_update.setObjectName('RefinedGhost')
    self.btn_cancel = QPushButton('Cancelar'); self.btn_cancel.setProperty('role','danger'); self.btn_cancel.setEnabled(False)
    small_actions.addWidget(self.btn_folder); small_actions.addWidget(self.btn_update); small_actions.addWidget(self.btn_cancel); sl.addLayout(small_actions)
    self.download_progress = QProgressBar(); self.download_progress.setObjectName('RefinedProgress'); self.download_progress.setRange(0,100); self.download_progress.setFormat('%p%'); sl.addWidget(self.download_progress)
    prog_line = QHBoxLayout(); self.download_status = QLabel('Pronto para analisar.'); self.download_status.setObjectName('RefinedMuted'); self.download_status.setWordWrap(True)
    self.download_percent = QLabel('0%'); self.download_percent.setObjectName('RefinedMuted')
    prog_line.addWidget(self.download_status,1); prog_line.addWidget(self.download_percent); sl.addLayout(prog_line)
    self.binary_status = QLabel(''); self.binary_status.setObjectName('RefinedMuted'); self.binary_status.setWordWrap(True); sl.addWidget(self.binary_status)
    sl.addStretch(1); cards.addWidget(summary,3)
    page.addLayout(cards)

    feature_row = QHBoxLayout(); feature_row.setSpacing(8)
    for args in [('↓','Download rápido','Alta velocidade'),('◎','Suporte a proxy','Conexão via proxy'),('▷','Pré-visualização','Confira antes de baixar'),('✂','Editor integrado','Corte e edite vídeos'),('↔','Timeline visual','Reordene os clipes')]:
        feature_row.addWidget(_feature(*args))
    page.addLayout(feature_row)
    page.addStretch(1)
    self.ref_stack.addWidget(download_scroll)

    # ---------------- Editor ----------------
    editor_scroll = QScrollArea(); editor_scroll.setObjectName('RefinedScroll'); editor_scroll.setWidgetResizable(True)
    self.editor_page = core.AdvancedVideoEditorWidget(core.VIDEOS_DIR, core.FFMPEG_EXE, core.FFPROBE_EXE, self)
    editor_scroll.setWidget(self.editor_page); self.ref_stack.addWidget(editor_scroll)

    # ---------------- Histórico ----------------
    hist_page = QWidget(); hp = QVBoxLayout(hist_page); hp.setContentsMargins(0,0,0,0); hp.setSpacing(12)
    hcard = _frame('RefinedHero'); hcl = QVBoxLayout(hcard); hcl.setContentsMargins(22,18,22,18); hcl.setSpacing(8)
    ht = QLabel('HISTÓRICO'); ht.setObjectName('RefinedMainTitle'); hs = QLabel('Área reservada para os downloads e exportações recentes.'); hs.setObjectName('RefinedMainSub')
    hcl.addWidget(ht); hcl.addWidget(hs); hp.addWidget(hcard); hp.addStretch(1); self.ref_stack.addWidget(hist_page)

    # ---------------- Configurações / proxy ----------------
    settings_scroll = QScrollArea(); settings_scroll.setObjectName('RefinedScroll'); settings_scroll.setWidgetResizable(True)
    settings_page = QWidget(); settings_scroll.setWidget(settings_page); sp = QVBoxLayout(settings_page); sp.setContentsMargins(0,0,0,0); sp.setSpacing(12)
    shead = _frame('RefinedHero'); sh = QVBoxLayout(shead); sh.setContentsMargins(22,18,22,18); sh.setSpacing(6)
    sht = QLabel('CONFIGURAÇÕES'); sht.setObjectName('RefinedMainTitle'); shs = QLabel('Conexão direta, proxy e preferências do aplicativo.'); shs.setObjectName('RefinedMainSub')
    sh.addWidget(sht); sh.addWidget(shs); sp.addWidget(shead)
    mode = QGroupBox('Modo de conexão'); ml = QVBoxLayout(mode)
    self.radio_direct = QRadioButton('Conexão direta (sem proxy)'); self.radio_proxy = QRadioButton('Usar proxy')
    ml.addWidget(self.radio_direct); ml.addWidget(self.radio_proxy); sp.addWidget(mode)
    pbox = QGroupBox('Dados do proxy'); form = QFormLayout(pbox)
    self.proxy_server = QLineEdit(); self.proxy_server.setPlaceholderText('Servidor do proxy')
    self.proxy_port = QLineEdit(); self.proxy_port.setPlaceholderText('Porta')
    self.proxy_user = QLineEdit(); self.proxy_user.setPlaceholderText('Usuário, se necessário')
    self.proxy_password = QLineEdit(); self.proxy_password.setEchoMode(QLineEdit.EchoMode.Password); self.proxy_password.setPlaceholderText('Senha — não é salva')
    form.addRow('Servidor:',self.proxy_server); form.addRow('Porta:',self.proxy_port); form.addRow('Usuário:',self.proxy_user); form.addRow('Senha:',self.proxy_password); sp.addWidget(pbox)
    actions = QHBoxLayout(); self.btn_save_proxy = QPushButton('Salvar configuração'); self.btn_save_proxy.setObjectName('RefinedPrimary')
    self.btn_clear_proxy = QPushButton('Usar conexão direta'); self.btn_clear_proxy.setObjectName('RefinedGhost')
    actions.addWidget(self.btn_save_proxy); actions.addWidget(self.btn_clear_proxy); actions.addStretch(1); sp.addLayout(actions)
    self.proxy_status = QLabel('Conexão atual: DIRETA'); self.proxy_status.setObjectName('RefinedText'); sp.addWidget(self.proxy_status); sp.addStretch(1)
    self.ref_stack.addWidget(settings_scroll)

    # Navegação
    def nav(index, key):
        self.ref_stack.setCurrentIndex(index)
        self.ref_nav[key].setChecked(True)
    self.ref_nav['home'].clicked.connect(lambda: nav(0,'home'))
    self.ref_nav['download'].clicked.connect(lambda: nav(0,'download'))
    self.ref_nav['editor'].clicked.connect(lambda: nav(1,'editor'))
    self.ref_nav['history'].clicked.connect(lambda: nav(2,'history'))
    self.ref_nav['settings'].clicked.connect(lambda: nav(3,'settings'))

    # Sinais funcionais existentes
    self.btn_download.clicked.connect(self.download_video)
    self.btn_cancel.clicked.connect(self.cancel_download)
    self.btn_update.clicked.connect(self.update_ytdlp)
    self.btn_folder.clicked.connect(self.open_videos_folder)
    self.btn_save_proxy.clicked.connect(self.save_proxy_settings)
    self.btn_clear_proxy.clicked.connect(self.use_direct_connection)
    self.radio_direct.toggled.connect(self._proxy_mode_changed)
    self.radio_proxy.toggled.connect(self._proxy_mode_changed)
    self.url_edit.returnPressed.connect(self.analyze_video)
    self.btn_analyze.clicked.connect(self.analyze_video)

    def quality_changed(qid, checked):
        if not checked:
            return
        self.quality_combo.setCurrentIndex(qid)
        names = ['2160p (4K)','1440p (2K)','1080p (Full HD)','720p (HD)','480p','360p']
        heights = [2160,1440,1080,720,480,360]
        self.summary_quality.setText(f'Qualidade:                      {names[qid]}')
        est = (self.analysis_data.get('estimates') or {}).get(heights[qid])
        self.summary_size.setText(f'Tamanho estimado:              {_format_size(est)}')
    self.quality_group.idToggled.connect(quality_changed)


def analyze_video(self):
    url = self.url_edit.text().strip()
    if not url.startswith(('http://','https://')):
        QMessageBox.warning(self, core.APP_NAME, 'Cole um link válido começando com http:// ou https://')
        return
    if self.analysis_worker and self.analysis_worker.isRunning():
        return
    proxy = self._current_proxy_url(True)
    if proxy is None:
        return
    self.btn_analyze.setEnabled(False)
    self.btn_analyze.setText('ANALISANDO…')
    self.download_status.setText('Analisando informações e qualidades disponíveis…')
    self.analysis_worker = AnalyzeWorker(url, proxy)
    self.analysis_worker.done.connect(self.analysis_finished)
    self.analysis_worker.failed.connect(self.analysis_failed)
    self.analysis_worker.start()


def analysis_finished(self, data):
    self.btn_analyze.setEnabled(True); self.btn_analyze.setText('⌕  ANALISAR')
    self.analysis_data = data
    self.video_title.setText(data.get('title') or 'Vídeo')
    self.video_channel.setText(data.get('channel') or '')
    h = data.get('height') or 0; w = data.get('width') or 0
    res = f'{w}×{h}' if w and h else ''
    is_live = bool(data.get('is_live'))
    if is_live:
        elapsed = int(data.get('live_elapsed') or 0)
        self.video_meta.setText('  •  '.join(x for x in ('AO VIVO', _format_duration(elapsed), res) if x))
        self.live_badge.show()
        self.live_mode_info.setText(
            f'🔴 MODO LIVE SNAPSHOT\nSerá baixado 00:00:00 → aproximadamente {_format_duration(elapsed)}. '
            'Ao clicar em BAIXAR, o ponto final é atualizado e congelado novamente.'
        )
        self.live_mode_info.show()
        self.btn_download.setText('🔴  BAIXAR DO INÍCIO ATÉ AGORA')
        self.summary_format.setText('Modo:                            LIVE • INÍCIO → AGORA')
    else:
        self.video_meta.setText('  •  '.join(x for x in (_format_duration(data.get('duration')), res) if x))
        self.live_badge.hide(); self.live_mode_info.hide()
        self.btn_download.setText('↓  BAIXAR')
        self.summary_format.setText('Formato:                         MP4')
    raw = data.get('thumbnail_bytes') or b''
    if raw:
        pm = QPixmap(); pm.loadFromData(QByteArray(raw))
        if not pm.isNull():
            self.video_thumb.setPixmap(pm.scaled(self.video_thumb.size(), Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation))
    heights = [2160,1440,1080,720,480,360]
    ests = data.get('estimates') or {}
    for idx, height in enumerate(heights):
        self.quality_estimate_labels[idx].setText(_format_size(ests.get(height)))
    checked = self.quality_group.checkedId()
    if checked < 0:
        checked = 1
    self.quality_combo.setCurrentIndex(checked)
    self.summary_quality.setText(f'Qualidade:                      {core.QUALIDADES[checked]}')
    self.summary_size.setText(f'Tamanho estimado:              {_format_size(ests.get(heights[checked]))}')
    if is_live:
        self.download_status.setText('🔴 Live detectada. Clique para baixar desde o início somente até o ponto atual.')
    else:
        self.download_status.setText('Análise concluída. Escolha a qualidade e clique em BAIXAR.')


def analysis_failed(self, message):
    self.btn_analyze.setEnabled(True); self.btn_analyze.setText('⌕  ANALISAR')
    self.download_status.setText('Não foi possível concluir a análise.')
    QMessageBox.warning(self, core.APP_NAME, core.friendly_network_error(message))



def download_video_liveaware(self):
    url = self.url_edit.text().strip()
    if not url.startswith(('http://','https://')):
        QMessageBox.warning(self, core.APP_NAME, 'Cole um link válido começando com http:// ou https://')
        return
    if self.download_worker and self.download_worker.isRunning():
        return
    proxy = self._current_proxy_url(True)
    if proxy is None:
        return
    self._update_proxy_status(); self._update_download_progress(0); self._set_download_busy(True)
    analyzed_url = str(self.analysis_data.get('analyzed_input_url') or '')
    live = bool(self.analysis_data.get('is_live')) and bool(analyzed_url) and analyzed_url == url
    if live and core.is_youtube(url):
        self.download_status.setText('🔴 Preparando live do início até o ponto atual…')
        self.download_worker = LiveSnapshotWorker(
            url, self.quality_combo.currentIndex(), proxy,
            self.analysis_data.get('live_start_timestamp') or 0,
        )
    else:
        self.download_status.setText('Analisando página…')
        self.download_worker = core.DownloadWorker(url, self.quality_combo.currentIndex(), proxy)
    self.download_worker.progress.connect(self._update_download_progress)
    self.download_worker.message.connect(self.download_status.setText)
    self.download_worker.done.connect(self.download_finished)
    self.download_worker.failed.connect(self.download_failed)
    self.download_worker.canceled.connect(self.download_canceled)
    self.download_worker.start()

# Substitui somente o layout da janela principal; o motor e o editor continuam os mesmos.
core.MainWindow._build_ui = build_refined_ui
core.MainWindow.analyze_video = analyze_video
core.MainWindow.analysis_finished = analysis_finished
core.MainWindow.analysis_failed = analysis_failed
core.MainWindow.download_video = download_video_liveaware


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(core.APP_NAME)
    app.setOrganizationName('ExtratorVideos')
    app.setStyle('Fusion')
    app.setStyleSheet(core.FUTURE_STYLESHEET)
    app.setWindowIcon(_app_icon())
    window = core.MainWindow()
    window.setWindowIcon(_app_icon())
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
