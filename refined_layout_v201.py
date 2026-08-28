import os
import subprocess
import sys
import urllib.parse
from pathlib import Path

from PySide6.QtCore import QSettings, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication, QGroupBox, QHBoxLayout, QLabel, QMessageBox, QPushButton, QVBoxLayout
)

import refined_layout as base

APP_VERSION = 'Windows Portable v2.0.1 — Globoplay Login + Evolução Consolidada'
SIDEBAR_VERSION = 'v2.0.1  •  GLOBOPLAY LOGIN'
SETTINGS_ORG = 'ExtratorVideos'
SETTINGS_APP = 'ExtratorVideos'
GLOBOPLAY_HOME = 'https://globoplay.globo.com/'


def _settings():
    return QSettings(SETTINGS_ORG, SETTINGS_APP)


def _is_globoplay_url(url):
    try:
        host = (urllib.parse.urlparse(str(url or '')).hostname or '').lower()
    except Exception:
        return False
    return host == 'globoplay.globo.com' or host.endswith('.globoplay.globo.com')


def _detect_default_browser():
    if os.name == 'nt':
        try:
            import winreg
            key_path = r'Software\Microsoft\Windows\Shell\Associations\UrlAssociations\https\UserChoice'
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                prog_id = str(winreg.QueryValueEx(key, 'ProgId')[0] or '').lower()
            mappings = (
                ('msedge', 'edge'),
                ('chrome', 'chrome'),
                ('brave', 'brave'),
                ('firefox', 'firefox'),
                ('vivaldi', 'vivaldi'),
                ('opera', 'opera'),
            )
            for marker, browser in mappings:
                if marker in prog_id:
                    return browser
        except Exception:
            pass

        local = Path(os.environ.get('LOCALAPPDATA', ''))
        roaming = Path(os.environ.get('APPDATA', ''))
        candidates = (
            ('edge', local / 'Microsoft/Edge/User Data'),
            ('chrome', local / 'Google/Chrome/User Data'),
            ('brave', local / 'BraveSoftware/Brave-Browser/User Data'),
            ('vivaldi', local / 'Vivaldi/User Data'),
            ('firefox', roaming / 'Mozilla/Firefox/Profiles'),
        )
        for browser, folder in candidates:
            try:
                if folder.exists():
                    return browser
            except Exception:
                pass

    return ''


def _globoplay_session_enabled():
    return bool(_settings().value('globoplay/session_enabled', False, type=bool))


def _globoplay_browser():
    saved = str(_settings().value('globoplay/browser', '') or '').strip().lower()
    return saved or _detect_default_browser()


def _globoplay_cookie_args(url):
    if not _is_globoplay_url(url) or not _globoplay_session_enabled():
        return []
    browser = _globoplay_browser()
    if not browser:
        return []
    return ['--cookies-from-browser', browser]


def _activate_globoplay_session(window):
    browser = _detect_default_browser()
    if not browser:
        QMessageBox.warning(
            window,
            base.core.APP_NAME,
            'Não foi possível identificar um navegador compatível para reutilizar a sessão do Globoplay.'
        )
        return

    s = _settings()
    s.setValue('globoplay/browser', browser)
    s.setValue('globoplay/session_enabled', True)
    s.sync()

    QDesktopServices.openUrl(QUrl(GLOBOPLAY_HOME))
    QMessageBox.information(
        window,
        base.core.APP_NAME,
        'O Globoplay foi aberto no seu navegador padrão.\n\n'
        '1. Faça login normalmente na sua conta Globo.\n'
        '2. Depois de concluir o login, volte ao aplicativo.\n'
        '3. Ao clicar em ANALISAR em um link do Globoplay, o aplicativo reutilizará '
        'a sessão desse navegador somente para links do Globoplay.\n\n'
        'Sua senha não é salva no aplicativo. Conteúdo com DRM continua sendo apenas '
        'identificado; o aplicativo não tenta contornar DRM.'
    )
    if hasattr(window, 'globoplay_session_status'):
        window.globoplay_session_status.setText(
            f'Sessão Globoplay: ATIVA via {browser.upper()}'
        )


def _disable_globoplay_session(window):
    s = _settings()
    s.setValue('globoplay/session_enabled', False)
    s.sync()
    if hasattr(window, 'globoplay_session_status'):
        window.globoplay_session_status.setText('Sessão Globoplay: desativada')


class GloboplayAnalyzeWorker(base.AnalyzeWorker):
    def run(self):
        try:
            cmd = [
                str(base.core.YTDLP_EXE), '--no-playlist', '--dump-single-json', '--skip-download',
                '--socket-timeout', '25', '--ffmpeg-location', str(base.core.BIN_DIR),
            ]
            if base.core.DENO_EXE.exists():
                cmd += ['--js-runtimes', f'deno:{base.core.DENO_EXE}']
            if self.proxy_url:
                cmd += ['--proxy', self.proxy_url]
            cmd += _globoplay_cookie_args(self.url)
            cmd.append(self.url)

            flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            kwargs = dict(
                capture_output=True, text=True, encoding='utf-8', errors='replace',
                creationflags=flags, timeout=90,
            )
            if hasattr(base.core, 'subprocess_environment'):
                kwargs['env'] = base.core.subprocess_environment(self.proxy_url)

            result = subprocess.run(cmd, **kwargs)
            if result.returncode != 0:
                raw = (result.stderr or result.stdout or 'Falha ao analisar o vídeo.')[-2500:]
                low = raw.lower()
                if any(k in low for k in (
                    'could not copy chrome cookie database',
                    'could not copy cookie database',
                    'failed to decrypt with dpapi',
                    'failed to decrypt cookies',
                )):
                    raise RuntimeError(
                        'INDISPONÍVEL: não foi possível ler a sessão do navegador. '
                        'Feche o navegador, abra novamente o aplicativo e tente ANALISAR de novo.'
                    )
                if 'drm' in low:
                    raise RuntimeError(
                        'INDISPONÍVEL: este vídeo está protegido por DRM. '
                        'O aplicativo não tenta contornar essa proteção.'
                    )
                if any(k in low for k in (
                    'login required', 'sign in', 'cookies', 'subscriber', 'subscription', 'assinatura'
                )):
                    raise RuntimeError(
                        'INDISPONÍVEL: o site exige autenticação/assinatura para este vídeo. '
                        'Use Configurações > Globoplay > Entrar / atualizar sessão Globoplay '
                        'e confirme que sua conta possui acesso ao conteúdo.'
                    )
                if any(k in low for k in ('geo', 'not available in your country', 'region')):
                    raise RuntimeError(
                        'INDISPONÍVEL: o vídeo não está disponível nesta região/conexão.'
                    )
                raise RuntimeError(raw)

            data = base.json.loads(result.stdout)
            duration = float(data.get('duration') or 0)
            formats = data.get('formats') or []

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
                    raise RuntimeError(
                        'INDISPONÍVEL: este conteúdo exige autenticação/assinatura e '
                        'não apresentou formato disponível para esta sessão.'
                    )
                raise RuntimeError(
                    'INDISPONÍVEL: o yt-dlp não confirmou nenhum formato de vídeo sem DRM '
                    'realmente disponível para download.'
                )

            def score(fmt):
                combined = str(fmt.get('acodec') or 'none').lower() != 'none'
                size = float(fmt.get('filesize') or fmt.get('filesize_approx') or 0)
                tbr = float(fmt.get('tbr') or 0)
                return (1 if combined else 0, tbr, size)

            best_audio = None
            if audio_formats:
                best_audio = max(
                    audio_formats,
                    key=lambda f: (
                        float(f.get('abr') or 0),
                        float(f.get('tbr') or 0),
                        float(f.get('filesize') or f.get('filesize_approx') or 0),
                    )
                )

            grouped = {}
            for fmt in video_formats:
                grouped.setdefault(int(fmt.get('height') or 0), []).append(fmt)

            available = []
            label_map = {
                2160: '2160p (4K)', 1440: '1440p (2K)', 1080: '1080p (Full HD)',
                720: '720p (HD)', 480: '480p', 360: '360p'
            }
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
                compat_selector = (
                    f'bv*[height={height}]+ba/b[height={height}]/'
                    f'b[height<={height}]/b'
                )
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

            available = available[:6]
            if not available:
                raise RuntimeError(
                    'INDISPONÍVEL: nenhuma resolução utilizável foi confirmada para download.'
                )

            estimates = {int(q['height']): q.get('estimate') or 0 for q in available}
            thumb_bytes = b''
            thumb = data.get('thumbnail') or ''
            if thumb:
                try:
                    req = base.urllib.request.Request(
                        thumb, headers={'User-Agent': 'Mozilla/5.0'}
                    )
                    with base.urllib.request.urlopen(req, timeout=12) as resp:
                        thumb_bytes = resp.read(2_000_000)
                except Exception:
                    pass

            live_status = str(data.get('live_status') or '')
            is_live = bool(data.get('is_live') or live_status == 'is_live')
            start_timestamp = data.get('release_timestamp') or data.get('timestamp')
            snapshot_timestamp = int(base.time.time()) if 'time' in base.__dict__ else 0
            live_elapsed = 0
            if is_live and start_timestamp and snapshot_timestamp:
                try:
                    live_elapsed = max(
                        0, snapshot_timestamp - int(float(start_timestamp))
                    )
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


_original_download_base_cmd = base.core.DownloadWorker._base_cmd


def _download_base_cmd_with_globoplay_session(
    self, fmt, referer='', extractor_args='', force_ipv4=False
):
    cmd = _original_download_base_cmd(
        self, fmt, referer, extractor_args, force_ipv4
    )
    cmd += _globoplay_cookie_args(self.url)
    return cmd


_original_build_refined_ui = base.build_refined_ui


def _build_refined_ui_v201(self):
    _original_build_refined_ui(self)

    try:
        settings_scroll = self.ref_stack.widget(3)
        settings_page = settings_scroll.widget()
        layout = settings_page.layout()

        box = QGroupBox('Globoplay — sessão de login')
        col = QVBoxLayout(box)
        info = QLabel(
            'Use sua própria conta Globo no navegador padrão. '
            'O aplicativo reutiliza essa sessão somente ao analisar/baixar links do Globoplay. '
            'A senha não é salva no aplicativo.'
        )
        info.setWordWrap(True)
        info.setObjectName('RefinedText')
        col.addWidget(info)

        browser = _globoplay_browser()
        active = _globoplay_session_enabled()
        status_text = (
            f'Sessão Globoplay: ATIVA via {browser.upper()}'
            if active and browser else
            'Sessão Globoplay: desativada'
        )
        self.globoplay_session_status = QLabel(status_text)
        self.globoplay_session_status.setObjectName('RefinedText')
        col.addWidget(self.globoplay_session_status)

        actions = QHBoxLayout()
        self.btn_globoplay_login = QPushButton('Entrar / atualizar sessão Globoplay')
        self.btn_globoplay_login.setObjectName('RefinedPrimary')
        self.btn_globoplay_login.clicked.connect(
            lambda: _activate_globoplay_session(self)
        )

        self.btn_globoplay_disable = QPushButton('Desativar sessão')
        self.btn_globoplay_disable.setObjectName('RefinedGhost')
        self.btn_globoplay_disable.clicked.connect(
            lambda: _disable_globoplay_session(self)
        )

        actions.addWidget(self.btn_globoplay_login)
        actions.addWidget(self.btn_globoplay_disable)
        actions.addStretch(1)
        col.addLayout(actions)

        note = QLabel(
            'Se o navegador impedir a leitura da sessão, feche o navegador e tente ANALISAR novamente. '
            'DRM, assinatura e outras restrições continuam sendo respeitados.'
        )
        note.setWordWrap(True)
        note.setObjectName('RefinedMuted')
        col.addWidget(note)

        layout.insertWidget(max(0, layout.count() - 1), box)
    except Exception:
        pass


base.AnalyzeWorker = GloboplayAnalyzeWorker
base.core.DownloadWorker._base_cmd = _download_base_cmd_with_globoplay_session
base.build_refined_ui = _build_refined_ui_v201
base.core.MainWindow._build_ui = _build_refined_ui_v201
base.core.APP_VERSION = APP_VERSION


def main():
    base.core.APP_VERSION = APP_VERSION
    app = QApplication(sys.argv)
    app.setApplicationName(base.core.APP_NAME)
    app.setOrganizationName('ExtratorVideos')
    app.setStyle('Fusion')
    app.setStyleSheet(base.core.FUTURE_STYLESHEET)
    app.setWindowIcon(base._app_icon())

    window = base.core.MainWindow()
    window.setWindowIcon(base._app_icon())

    for label in window.findChildren(QLabel):
        if label.objectName() == 'RefinedVersion':
            label.setText(SIDEBAR_VERSION)
            break

    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
