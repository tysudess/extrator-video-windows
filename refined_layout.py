import json
import os
import re
import subprocess
import sys
import time
import urllib.request
import urllib.parse
import tempfile
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

core.APP_VERSION = 'Windows Portable v1.9.22 — Qualidades Reais + Globoplay Status'

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
            kwargs = dict(
                capture_output=True, text=True, encoding='utf-8', errors='replace',
                creationflags=flags, timeout=90,
            )
            # No Ubuntu o projeto injeta os certificados/proxy no ambiente.
            if hasattr(core, 'subprocess_environment'):
                kwargs['env'] = core.subprocess_environment(self.proxy_url)
            result = subprocess.run(cmd, **kwargs)
            if result.returncode != 0:
                raw = (result.stderr or result.stdout or 'Falha ao analisar o vídeo.')[-2500:]
                low = raw.lower()
                if 'drm' in low:
                    raise RuntimeError('INDISPONÍVEL: este vídeo está protegido por DRM. O aplicativo não tenta contornar essa proteção.')
                if any(k in low for k in ('login required', 'sign in', 'cookies', 'subscriber', 'subscription', 'assinatura')):
                    raise RuntimeError('INDISPONÍVEL: o site exige autenticação/assinatura para este vídeo. Nenhuma qualidade pública foi confirmada para download.')
                if any(k in low for k in ('geo', 'not available in your country', 'region')):
                    raise RuntimeError('INDISPONÍVEL: o vídeo não está disponível nesta região/conexão.')
                raise RuntimeError(raw)

            data = json.loads(result.stdout)
            duration = float(data.get('duration') or 0)
            formats = data.get('formats') or []

            # Só consideramos formatos que o próprio yt-dlp confirmou com URL de mídia,
            # vídeo real e sem indicação de DRM. Assim a tela não promete qualidades
            # que existem apenas no layout, mas não na fonte.
            video_formats = []
            audio_formats = []
            for fmt in formats:
                if not isinstance(fmt, dict) or not fmt.get('url'):
                    continue
                if fmt.get('has_drm') is True or fmt.get('drm_family'):
                    continue
                vcodec = str(fmt.get('vcodec') or 'none').lower()
                acodec = str(fmt.get('acodec') or 'none').lower()
                if vcodec != 'none':
                    h = int(fmt.get('height') or 0)
                    if h > 0:
                        video_formats.append(fmt)
                elif acodec != 'none':
                    audio_formats.append(fmt)

            if not video_formats:
                availability = str(data.get('availability') or '').lower()
                if availability in ('subscriber_only', 'premium_only', 'needs_auth'):
                    raise RuntimeError('INDISPONÍVEL: este conteúdo exige autenticação/assinatura e não apresentou formato público para download.')
                raise RuntimeError('INDISPONÍVEL: o yt-dlp não confirmou nenhum formato de vídeo sem DRM realmente disponível para download.')

            def score(fmt):
                combined = str(fmt.get('acodec') or 'none').lower() != 'none'
                size = float(fmt.get('filesize') or fmt.get('filesize_approx') or 0)
                tbr = float(fmt.get('tbr') or 0)
                return (1 if combined else 0, tbr, size)

            best_audio = None
            if audio_formats:
                best_audio = max(audio_formats, key=lambda f: (float(f.get('abr') or 0), float(f.get('tbr') or 0), float(f.get('filesize') or f.get('filesize_approx') or 0)))

            grouped = {}
            for fmt in video_formats:
                grouped.setdefault(int(fmt.get('height') or 0), []).append(fmt)

            available = []
            label_map = {2160:'2160p (4K)', 1440:'1440p (2K)', 1080:'1080p (Full HD)', 720:'720p (HD)', 480:'480p', 360:'360p'}
            for height in sorted(grouped, reverse=True):
                selected = max(grouped[height], key=score)
                fid = str(selected.get('format_id') or '').strip()
                if not fid:
                    continue
                acodec = str(selected.get('acodec') or 'none').lower()
                selector = fid
                if acodec == 'none' and best_audio:
                    aid = str(best_audio.get('format_id') or '').strip()
                    if aid:
                        selector = f'{fid}+{aid}/{fid}'
                compat_selector = f'bv*[height={height}]+ba/b[height={height}]/b[height<={height}]/b'
                size = selected.get('filesize') or selected.get('filesize_approx')
                if not size and selected.get('tbr') and duration:
                    size = float(selected.get('tbr')) * 1000.0 * duration / 8.0
                if acodec == 'none' and best_audio:
                    asize = best_audio.get('filesize') or best_audio.get('filesize_approx')
                    if not asize and best_audio.get('tbr') and duration:
                        asize = float(best_audio.get('tbr')) * 1000.0 * duration / 8.0
                    if size and asize:
                        size = float(size) + float(asize)
                available.append({
                    'height': height,
                    'label': label_map.get(height, f'{height}p'),
                    'selector': selector,
                    'compat_selector': compat_selector,
                    'estimate': float(size or 0),
                    'ext': str(selected.get('ext') or 'video').upper(),
                    'format_id': fid,
                })

            # A interface possui seis slots. Mostramos apenas as seis melhores
            # resoluções que realmente vieram na análise; as demais ficam invisíveis.
            available = available[:6]
            if not available:
                raise RuntimeError('INDISPONÍVEL: nenhuma resolução utilizável foi confirmada para download.')

            estimates = {int(q['height']): q.get('estimate') or 0 for q in available}
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
            snapshot_timestamp = int(time.time()) if 'time' in globals() else 0
            live_elapsed = 0
            if is_live and start_timestamp and snapshot_timestamp:
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
                'available_qualities': available,
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

    def _urlopen(self, url, headers=None, timeout=45):
        req = urllib.request.Request(url, headers=headers or {})
        if self.proxy_url:
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({'http': self.proxy_url, 'https': self.proxy_url}))
            return opener.open(req, timeout=timeout)
        return urllib.request.urlopen(req, timeout=timeout)

    @staticmethod
    def _safe_name(text):
        text = re.sub(r'[<>:"/\\|?*\\x00-\\x1f]', '_', str(text or 'Live YouTube')).strip(' .')
        return (text[:145] or 'Live YouTube')

    @staticmethod
    def _format_has_av(fmt):
        return str(fmt.get('vcodec') or 'none') != 'none' and str(fmt.get('acodec') or 'none') != 'none'

    def _select_hls_format(self, data, wanted_height):
        """Escolhe uma variante HLS muxada sem usar --live-from-start.

        O URL de uma variante HLS representa a janela DVR que o player do YouTube
        consegue rebobinar. Vamos congelar essa janela em um arquivo m3u8 local,
        impedindo que o FFmpeg continue acompanhando a transmissão.
        """
        candidates = []
        for fmt in (data.get('formats') or []):
            url = str(fmt.get('url') or '')
            proto = str(fmt.get('protocol') or '').lower()
            if not url:
                continue
            if 'm3u8' not in proto and '.m3u8' not in url.lower() and 'manifest/hls' not in url.lower():
                continue
            if not self._format_has_av(fmt):
                continue
            try:
                h = int(float(fmt.get('height') or 0))
            except Exception:
                h = 0
            try:
                tbr = float(fmt.get('tbr') or 0)
            except Exception:
                tbr = 0.0
            # Primeiro prefere <= altura solicitada. Se não houver, aceita a mais próxima.
            over = 1 if (h and h > wanted_height) else 0
            distance = abs((h or wanted_height) - wanted_height)
            candidates.append((over, distance, -h, -tbr, fmt))
        if not candidates:
            return None
        candidates.sort(key=lambda x: x[:4])
        return candidates[0][4]

    @staticmethod
    def _rewrite_uri_attributes(line, base_url):
        def repl(match):
            raw = match.group(1)
            return 'URI="' + urllib.parse.urljoin(base_url, raw) + '"'
        return re.sub(r'URI="([^"]+)"', repl, line)

    def _freeze_media_playlist(self, playlist_url, headers, target_seconds):
        """Baixa uma única fotografia do m3u8 e transforma em playlist VOD local."""
        with self._urlopen(playlist_url, headers=headers, timeout=45) as resp:
            raw = resp.read().decode('utf-8', 'replace')
        if '#EXTM3U' not in raw:
            raise RuntimeError('O YouTube não retornou uma playlist HLS válida para esta live.')

        # Caso recebamos master playlist por alguma variação do extractor, escolhemos
        # a primeira variante. Normalmente o yt-dlp já fornece a media playlist.
        lines = raw.splitlines()
        if any('#EXT-X-STREAM-INF' in ln for ln in lines):
            variant = None
            for i, ln in enumerate(lines):
                if ln.startswith('#EXT-X-STREAM-INF'):
                    for j in range(i + 1, min(i + 4, len(lines))):
                        cand = lines[j].strip()
                        if cand and not cand.startswith('#'):
                            variant = urllib.parse.urljoin(playlist_url, cand)
                            break
                    if variant:
                        break
            if not variant:
                raise RuntimeError('Não foi possível localizar a variante HLS da live.')
            playlist_url = variant
            with self._urlopen(playlist_url, headers=headers, timeout=45) as resp:
                raw = resp.read().decode('utf-8', 'replace')
            lines = raw.splitlines()

        total = 0.0
        for ln in lines:
            if ln.startswith('#EXTINF:'):
                try:
                    total += float(ln.split(':', 1)[1].split(',', 1)[0])
                except Exception:
                    pass

        # O timestamp de início do YouTube pode divergir alguns segundos do primeiro
        # segmento. Uma diferença grande indica que a janela DVR já perdeu o começo.
        tolerance = max(90.0, min(300.0, target_seconds * 0.04))
        if total <= 0:
            raise RuntimeError('A playlist DVR não informou a duração dos segmentos.')
        if total + tolerance < target_seconds:
            raise RuntimeError(
                f'A janela DVR disponível contém cerca de {self._time_arg(int(total))}, '
                f'mas a live já tem aproximadamente {self._time_arg(target_seconds)}. '
                'O início não está mais disponível nessa janela HLS.'
            )

        base = playlist_url
        frozen = []
        for ln in lines:
            stripped = ln.strip()
            if not stripped:
                frozen.append(ln)
                continue
            if stripped.startswith('#'):
                frozen.append(self._rewrite_uri_attributes(ln, base))
            else:
                frozen.append(urllib.parse.urljoin(base, stripped))
        # Marca como encerrada localmente: o FFmpeg NÃO recarrega a playlist e,
        # portanto, não acompanha novos segmentos que aparecerem no YouTube.
        if not any(ln.startswith('#EXT-X-ENDLIST') for ln in frozen):
            frozen.append('#EXT-X-ENDLIST')

        tmp_dir = Path(tempfile.mkdtemp(prefix='extrator-live-'))
        local_m3u8 = tmp_dir / 'snapshot.m3u8'
        local_m3u8.write_text('\n'.join(frozen) + '\n', encoding='utf-8')
        return local_m3u8, total, tmp_dir

    def _run_hls_snapshot(self, target_seconds, data):
        """Método principal v1.9.20.2: congela o DVR e baixa a janela congelada."""
        heights = [2160, 1440, 1080, 720, 480, 360]
        wanted = heights[self.quality_index]
        fmt = self._select_hls_format(data, wanted)
        if not fmt:
            return False, '', 'Nenhuma variante HLS muxada com áudio e vídeo foi encontrada para congelar o DVR.'

        actual_h = int(float(fmt.get('height') or 0) or 0)
        headers = dict(fmt.get('http_headers') or {})
        headers.setdefault('User-Agent', 'Mozilla/5.0')
        headers.setdefault('Referer', 'https://www.youtube.com/')
        self.message.emit(f'🔴 Congelando a janela DVR em {actual_h or wanted}p…')

        local_m3u8 = None
        tmp_dir = None
        try:
            local_m3u8, playlist_duration, tmp_dir = self._freeze_media_playlist(
                str(fmt.get('url')), headers, target_seconds
            )
            self.message.emit(
                f'Janela DVR congelada: ~{self._time_arg(int(playlist_duration))}. '
                'Novos minutos da live não serão adicionados.'
            )
            title = self._safe_name(data.get('title') or 'Live YouTube')
            vid = self._safe_name(data.get('id') or 'live')
            stamp = time.strftime('%Y%m%d-%H%M%S')
            out_path = core.VIDEOS_DIR / f'{title} [LIVE-ATE-AGORA {stamp}] [{vid}].mp4'
            # Evita colisão rara de nomes.
            n = 2
            while out_path.exists():
                out_path = core.VIDEOS_DIR / f'{title} [LIVE-ATE-AGORA {stamp}-{n}] [{vid}].mp4'
                n += 1

            header_blob = ''.join(f'{k}: {v}\\r\\n' for k, v in headers.items())
            cmd = [
                str(core.FFMPEG_EXE), '-y', '-hide_banner', '-loglevel', 'warning',
                '-protocol_whitelist', 'file,http,https,tcp,tls,crypto',
            ]
            if header_blob:
                cmd += ['-headers', header_blob]
            cmd += [
                '-i', str(local_m3u8), '-t', str(max(1, int(target_seconds))),
                '-map', '0:v:0?', '-map', '0:a:0?', '-c', 'copy',
                '-movflags', '+faststart', '-progress', 'pipe:1', '-nostats', str(out_path)
            ]
            flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            env = os.environ.copy()
            if self.proxy_url:
                env['http_proxy'] = self.proxy_url
                env['https_proxy'] = self.proxy_url
            self._process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                encoding='utf-8', errors='replace', creationflags=flags, env=env
            )
            tail = []
            assert self._process.stdout is not None
            for raw_line in self._process.stdout:
                if self._cancel_requested:
                    try: self._process.terminate()
                    except Exception: pass
                    return False, '', 'Download cancelado.'
                line = raw_line.strip()
                if line:
                    tail.append(line); tail = tail[-80:]
                m = re.match(r'out_time_(?:ms|us)=(\d+)', line)
                if m:
                    # ffmpeg chama esse campo de *_ms em algumas versões embora a
                    # unidade prática seja microssegundos; ambos são tratados igual.
                    sec = int(m.group(1)) / 1_000_000.0
                    self.progress.emit(max(1, min(99, int(sec * 100 / max(1, target_seconds)))))
            code = self._process.wait(); self._process = None
            if code == 0 and out_path.exists() and out_path.stat().st_size > 1024:
                return True, str(out_path), ''

            # Alguns HLS usam codecs que não podem ser apenas remuxados para MP4.
            # Nesse caso fazemos uma segunda passagem transcodificando para H.264/AAC.
            out_path.unlink(missing_ok=True)
            self.message.emit('Remux direto não funcionou; tentando H.264/AAC…')
            cmd2 = [
                str(core.FFMPEG_EXE), '-y', '-hide_banner', '-loglevel', 'warning',
                '-protocol_whitelist', 'file,http,https,tcp,tls,crypto',
            ]
            if header_blob:
                cmd2 += ['-headers', header_blob]
            cmd2 += [
                '-i', str(local_m3u8), '-t', str(max(1, int(target_seconds))),
                '-map', '0:v:0?', '-map', '0:a:0?', '-c:v', 'libx264', '-preset', 'veryfast',
                '-crf', '20', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '160k',
                '-movflags', '+faststart', '-progress', 'pipe:1', '-nostats', str(out_path)
            ]
            self._process = subprocess.Popen(
                cmd2, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                encoding='utf-8', errors='replace', creationflags=flags, env=env
            )
            tail2 = []
            assert self._process.stdout is not None
            for raw_line in self._process.stdout:
                if self._cancel_requested:
                    try: self._process.terminate()
                    except Exception: pass
                    return False, '', 'Download cancelado.'
                line = raw_line.strip()
                if line:
                    tail2.append(line); tail2 = tail2[-80:]
                m = re.match(r'out_time_(?:ms|us)=(\d+)', line)
                if m:
                    sec = int(m.group(1)) / 1_000_000.0
                    self.progress.emit(max(1, min(99, int(sec * 100 / max(1, target_seconds)))))
            code2 = self._process.wait(); self._process = None
            if code2 == 0 and out_path.exists() and out_path.stat().st_size > 1024:
                return True, str(out_path), ''
            out_path.unlink(missing_ok=True)
            return False, '', '\n'.join((tail + tail2)[-80:]) or 'FFmpeg não conseguiu processar a playlist DVR congelada.'
        except Exception as exc:
            return False, '', str(exc)
        finally:
            try:
                if tmp_dir and tmp_dir.exists():
                    import shutil
                    shutil.rmtree(tmp_dir, ignore_errors=True)
            except Exception:
                pass

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

            # Método principal: congela a playlist HLS/DVR no instante do clique.
            # Isso evita a combinação problemática --live-from-start + --download-sections.
            ok, path, err = self._run_hls_snapshot(target, _data)

            # Fallback legado apenas se a live não expuser uma janela HLS DVR completa.
            if not ok and not self._cancel_requested:
                self.message.emit('O snapshot HLS não ficou disponível. Tentando modo compatível do yt-dlp…')
                heights = [2160, 1440, 1080, 720, 480, 360]
                height = heights[self.quality_index]
                attempts = [
                    (f'b[height<={height}]/b', f'Tentando LIVE compatível até {height}p…'),
                    ('b', 'Tentando melhor formato LIVE disponível…'),
                ]
                legacy_errors = [err] if err else []
                for fmt, label in attempts:
                    if self._cancel_requested:
                        break
                    ok, path, current_err = self._run_attempt(fmt, target, label)
                    if ok:
                        break
                    if current_err:
                        legacy_errors.append(current_err)
                if legacy_errors:
                    err = '\n\n'.join(legacy_errors[-3:])
            if self._cancel_requested:
                self.canceled.emit(); return
            if not ok:
                low = (err or '').lower()
                if 'requested format is not available' in low:
                    reason = ('A live possui DVR, mas nem a janela HLS congelada nem o modo compatível do yt-dlp conseguiram recuperar o início. '                               'Isso pode ocorrer quando a janela DVR já não contém o começo da transmissão.')
                else:
                    reason = ('Não foi possível recortar esta live do início até agora. Algumas transmissões não expõem DVR/range compatível para o yt-dlp.')
                raise RuntimeError(reason + '\n\n' + (err[-1800:] if err else ''))
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
    ver = QLabel('v1.9.22  •  QUALIDADES REAIS + GLOBOPLAY'); ver.setObjectName('RefinedVersion'); ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
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
    self.quality_row_widgets = []
    self.quality_format_labels = []
    labels = [('2160p (4K)','MP4'),('1440p (2K)','MP4'),('1080p (Full HD)','MP4'),('720p (HD)','MP4'),('480p','MP4'),('360p','MP4')]
    for idx, (name, fmt) in enumerate(labels):
        row_widget = QWidget(); row = QHBoxLayout(row_widget); row.setContentsMargins(0,0,0,0); row.setSpacing(8)
        rb = QRadioButton(name); rb.setObjectName('RefinedQuality'); self.quality_group.addButton(rb, idx); self.quality_buttons.append(rb)
        fmt_l = QLabel(fmt); fmt_l.setObjectName('RefinedMuted'); fmt_l.setFixedWidth(45)
        est = QLabel('—'); est.setObjectName('RefinedMuted'); est.setAlignment(Qt.AlignmentFlag.AlignRight); est.setMinimumWidth(55)
        self.quality_format_labels.append(fmt_l); self.quality_estimate_labels.append(est); self.quality_row_widgets.append(row_widget)
        row.addWidget(rb,1); row.addWidget(fmt_l); row.addWidget(est); ql.addWidget(row_widget)
        row_widget.hide()
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
    self.btn_download = QPushButton('↓  BAIXAR'); self.btn_download.setObjectName('RefinedPrimary'); self.btn_download.setEnabled(False); sl.addWidget(self.btn_download)
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

    def invalidate_analysis(_text):
        self.analysis_data = {}
        self.btn_download.setEnabled(False)
        for row in getattr(self, 'quality_row_widgets', []):
            row.hide()
        self.download_status.setText('Link alterado. Clique em ANALISAR para verificar disponibilidade real.')
    self.url_edit.textChanged.connect(invalidate_analysis)

    def quality_changed(qid, checked):
        if not checked:
            return
        qualities = self.analysis_data.get('available_qualities') or []
        if qid < 0 or qid >= len(qualities):
            return
        self.quality_combo.setCurrentIndex(qid)
        q = qualities[qid]
        self.summary_quality.setText(f"Qualidade:                      {q.get('label') or (str(q.get('height')) + 'p')}")
        self.summary_size.setText(f"Tamanho estimado:              {_format_size(q.get('estimate'))}")
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
        if hasattr(self, 'live_badge'):
            self.live_badge.show()
        if hasattr(self, 'live_mode_info'):
            self.live_mode_info.setText(f'🔴 MODO LIVE SNAPSHOT\nSerá baixado 00:00:00 → aproximadamente {_format_duration(elapsed)}.')
            self.live_mode_info.show()
        self.btn_download.setText('🔴  BAIXAR DO INÍCIO ATÉ AGORA')
        self.summary_format.setText('Modo:                            LIVE • INÍCIO → AGORA')
    else:
        self.video_meta.setText('  •  '.join(x for x in (_format_duration(data.get('duration')), res) if x))
        if hasattr(self, 'live_badge'):
            self.live_badge.hide()
        if hasattr(self, 'live_mode_info'):
            self.live_mode_info.hide()
        self.btn_download.setText('↓  BAIXAR')
        self.summary_format.setText('Formato:                         MP4')

    raw = data.get('thumbnail_bytes') or b''
    if raw:
        pm = QPixmap(); pm.loadFromData(QByteArray(raw))
        if not pm.isNull():
            self.video_thumb.setPixmap(pm.scaled(self.video_thumb.size(), Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation))

    qualities = data.get('available_qualities') or []
    for row in self.quality_row_widgets:
        row.hide()
    for idx, q in enumerate(qualities[:len(self.quality_row_widgets)]):
        self.quality_buttons[idx].setText(q.get('label') or f"{q.get('height')}p")
        self.quality_format_labels[idx].setText(q.get('ext') or 'VIDEO')
        self.quality_estimate_labels[idx].setText(_format_size(q.get('estimate')))
        self.quality_row_widgets[idx].show()

    if not qualities:
        self.btn_download.setEnabled(False)
        self.summary_quality.setText('Qualidade:                      nenhuma disponível')
        self.summary_size.setText('Tamanho estimado:              —')
        self.download_status.setText('Nenhum formato realmente disponível para download.')
        return

    # Preferimos 720p como padrão quando existe; caso contrário, a melhor disponível.
    selected = next((i for i,q in enumerate(qualities) if int(q.get('height') or 0) == 720), 0)
    self.quality_buttons[selected].setChecked(True)
    self.quality_combo.setCurrentIndex(selected)
    q = qualities[selected]
    self.summary_quality.setText(f"Qualidade:                      {q.get('label')}")
    self.summary_size.setText(f"Tamanho estimado:              {_format_size(q.get('estimate'))}")
    self.btn_download.setEnabled(True)
    if is_live:
        self.download_status.setText(f'🔴 Live detectada. {len(qualities)} qualidade(s) realmente disponível(is).')
    else:
        self.download_status.setText(f'Análise concluída: {len(qualities)} qualidade(s) realmente disponível(is) para download.')


def analysis_failed(self, message):
    self.btn_analyze.setEnabled(True); self.btn_analyze.setText('⌕  ANALISAR')
    self.analysis_data = {}
    for row in getattr(self, 'quality_row_widgets', []):
        row.hide()
    self.btn_download.setEnabled(False)
    self.video_title.setText('Vídeo indisponível para download')
    self.video_channel.setText('')
    self.video_meta.setText('')
    self.summary_quality.setText('Qualidade:                      nenhuma disponível')
    self.summary_size.setText('Tamanho estimado:              —')
    clean = str(message or 'Não foi possível analisar este vídeo.')
    if 'INDISPONÍVEL:' in clean:
        clean = clean.split('INDISPONÍVEL:',1)[1].strip()
    self.download_status.setText('Indisponível: ' + clean)
    QMessageBox.information(self, core.APP_NAME, 'Este link não apresentou vídeo realmente disponível para download.\n\n' + clean)


def download_video_liveaware(self):
    url = self.url_edit.text().strip()
    if not url.startswith(('http://','https://')):
        QMessageBox.warning(self, core.APP_NAME, 'Cole um link válido começando com http:// ou https://')
        return
    if self.download_worker and self.download_worker.isRunning():
        return
    analyzed_url = str(self.analysis_data.get('analyzed_input_url') or '')
    qualities = self.analysis_data.get('available_qualities') or []
    qid = self.quality_group.checkedId()
    if analyzed_url != url or qid < 0 or qid >= len(qualities):
        QMessageBox.information(self, core.APP_NAME, 'Clique em ANALISAR e escolha uma das qualidades realmente disponíveis antes de baixar.')
        return
    proxy = self._current_proxy_url(True)
    if proxy is None:
        return
    q = qualities[qid]
    self._update_proxy_status(); self._update_download_progress(0); self._set_download_busy(True)
    live = bool(self.analysis_data.get('is_live'))
    if live and core.is_youtube(url):
        heights = [2160,1440,1080,720,480,360]
        target = int(q.get('height') or 720)
        core_index = min(range(len(heights)), key=lambda i: abs(heights[i]-target))
        self.download_status.setText('🔴 Preparando live do início até o ponto atual…')
        self.download_worker = LiveSnapshotWorker(url, core_index, proxy, self.analysis_data.get('live_start_timestamp') or 0)
    else:
        self.download_status.setText('Iniciando download da qualidade confirmada…')
        self.download_worker = core.DownloadWorker(
            url, 0, proxy,
            format_selector=q.get('selector') or '',
            compat_selector=q.get('compat_selector') or '',
        )
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
