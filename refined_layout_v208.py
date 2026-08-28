import json
import os
import subprocess

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QMessageBox

import refined_layout_v207 as v207

APP_VERSION = 'Windows Portable v2.0.8 — Download Direto estilo Android + R7 Android Flow + Sessão Globoplay Persistente'
SIDEBAR_VERSION = 'v2.0.8  •  DOWNLOAD DIRETO'

core = v207.core
base = v207.base

DIRECT_QUALITIES = (
    ('360p', 360,
     'bv*[height<=360][ext=mp4]+ba[ext=m4a]/b[height<=360][ext=mp4]/bv*[height<=360]+ba/b[height<=360]/b',
     'b[height<=360][ext=mp4]/b[height<=360]/b'),
    ('480p', 480,
     'bv*[height<=480][ext=mp4]+ba[ext=m4a]/b[height<=480][ext=mp4]/bv*[height<=480]+ba/b[height<=480]/b',
     'b[height<=480][ext=mp4]/b[height<=480]/b'),
    ('720p HD', 720,
     'bv*[height<=720][ext=mp4]+ba[ext=m4a]/b[height<=720][ext=mp4]/bv*[height<=720]+ba/b[height<=720]/b',
     'b[height<=720][ext=mp4]/b[height<=720]/b'),
    ('1080p Full HD', 1080,
     'bv*[height<=1080][ext=mp4]+ba[ext=m4a]/b[height<=1080][ext=mp4]/bv*[height<=1080]+ba/b[height<=1080]/b',
     'b[height<=1080][ext=mp4]/b[height<=1080]/b'),
    ('Melhor disponível', 2160,
     'bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/bv*+ba/b',
     'b[ext=mp4]/b'),
)


class R7DirectDownloadWorker(v207.OriginalDownloadWorker):
    """Fluxo R7 igual ao Android: matéria -> HTML -> candidatos, sem DRM prematuro."""

    def _base_cmd(self, fmt, referer='', extractor_args='', force_ipv4=False):
        cmd = super()._base_cmd(
            fmt,
            referer=referer,
            extractor_args=extractor_args,
            force_ipv4=(True if v207._is_r7_url(self.url) else force_ipv4),
        )
        if not v207._is_r7_url(self.url):
            return cmd

        def add_pair(option, value=None):
            if option in cmd:
                return
            cmd.append(option)
            if value is not None:
                cmd.append(str(value))

        add_pair('--no-mtime')
        add_pair('--retries', '10')
        add_pair('--fragment-retries', '10')
        if '--socket-timeout' in cmd:
            try:
                idx = cmd.index('--socket-timeout')
                if idx + 1 < len(cmd):
                    cmd[idx + 1] = '30'
            except Exception:
                pass
        else:
            add_pair('--socket-timeout', '30')
        return cmd

    def run(self):
        if not v207._is_r7_url(self.url):
            return super().run()

        self.url = v207._clean_r7_url(self.url)

        if not core.YTDLP_EXE.exists():
            self.failed.emit('yt-dlp.exe não encontrado na pasta bin.')
            return
        if not core.FFMPEG_EXE.exists():
            self.failed.emit('ffmpeg.exe não encontrado na pasta bin.')
            return

        fmt = self.format_selector or core.FORMATS[self.quality_index]
        self.progress.emit(0)

        ok, final_file, last_error = self._attempt(
            self.url,
            fmt,
            label='R7: tentativa principal pela matéria...',
            force_ipv4=True,
        )
        if ok and self._finish_if_ok(ok, final_file, last_error):
            return
        if self._cancel_requested:
            self.canceled.emit()
            return

        # Igual ao Android: uma mensagem de DRM/Generic na página NÃO encerra
        # a busca por candidatos. Só encerramos depois de testar o HTML.
        self.message.emit(
            'R7: método principal falhou. Procurando vídeos dentro da página...'
        )
        try:
            candidates = v207._r7_candidates_from_page(self.url, self.proxy_url)
        except Exception as exc:
            self._fail_with_diagnostic(str(exc))
            return

        for index, candidate in enumerate(candidates[:15], 1):
            ok, final_file, last_error = self._attempt(
                candidate,
                fmt,
                referer=self.url,
                label=f'R7: tentativa alternativa {index}/{min(15, len(candidates))}...',
                force_ipv4=True,
            )
            if ok and self._finish_if_ok(ok, final_file, last_error):
                return
            if self._cancel_requested:
                self.canceled.emit()
                return

        self._fail_with_diagnostic(
            last_error or
            'R7: nenhum dos candidatos encontrados na página concluiu o download.'
        )


class YouTubeRouteWorker(QThread):
    """Detecta live silenciosamente para preservar LIVE do início até agora."""

    done = Signal(dict)

    def __init__(self, url, proxy_url=''):
        super().__init__()
        self.url = str(url or '').strip()
        self.proxy_url = str(proxy_url or '')

    def run(self):
        data = {'is_live': False, 'live_start_timestamp': 0}
        try:
            cmd = [
                str(core.YTDLP_EXE), '--no-playlist', '--dump-single-json',
                '--skip-download', '--socket-timeout', '25',
                '--ffmpeg-location', str(core.BIN_DIR),
            ]
            if core.DENO_EXE.exists():
                cmd += ['--js-runtimes', f'deno:{core.DENO_EXE}']
            if self.proxy_url:
                cmd += ['--proxy', self.proxy_url]
            cmd.append(self.url)
            flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0) if os.name == 'nt' else 0
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                creationflags=flags,
                timeout=90,
            )
            if result.returncode == 0 and result.stdout.strip():
                raw = json.loads(result.stdout)
                status = str(raw.get('live_status') or '')
                data['is_live'] = bool(raw.get('is_live') or status == 'is_live')
                start = raw.get('release_timestamp') or raw.get('timestamp') or 0
                try:
                    data['live_start_timestamp'] = int(float(start or 0))
                except Exception:
                    data['live_start_timestamp'] = 0
        except Exception:
            pass
        self.done.emit(data)


_previous_build_ui = core.MainWindow._build_ui


def _build_ui_v208(self):
    _previous_build_ui(self)

    # Remove o fluxo visível de análise.
    try:
        self.btn_analyze.hide()
    except Exception:
        pass
    try:
        self.url_edit.returnPressed.disconnect()
    except Exception:
        pass
    try:
        self.url_edit.textChanged.disconnect()
    except Exception:
        pass

    self.url_edit.setPlaceholderText('https://...')
    self.url_edit.setMinimumHeight(58)

    link_card = self.url_edit.parentWidget()
    link_layout = link_card.layout()

    self.direct_quality_label = QLabel('Qualidade do vídeo')
    self.direct_quality_label.setObjectName('RefinedCardTitle')
    link_layout.addWidget(self.direct_quality_label)

    self.direct_quality_combo = QComboBox()
    self.direct_quality_combo.setObjectName('RefinedUrl')
    self.direct_quality_combo.addItems([item[0] for item in DIRECT_QUALITIES])
    self.direct_quality_combo.setCurrentIndex(1)
    self.direct_quality_combo.setMinimumHeight(46)
    link_layout.addWidget(self.direct_quality_combo)

    self.direct_format_info = QLabel('Formato de saída: MP4')
    self.direct_format_info.setObjectName('RefinedMuted')
    link_layout.addWidget(self.direct_format_info)

    # Guarda os cards antigos antes de mover os controles necessários.
    info_frame = self.video_thumb.parentWidget()
    quality_frame = self.quality_combo.parentWidget()
    summary_frame = self.summary_format.parentWidget()

    self.btn_download.setParent(link_card)
    self.btn_download.setText('↓  BAIXAR VÍDEO')
    self.btn_download.setMinimumHeight(48)
    self.btn_download.setEnabled(False)
    link_layout.addWidget(self.btn_download)

    actions = QHBoxLayout()
    actions.setSpacing(6)
    for widget in (self.btn_folder, self.btn_update, self.btn_cancel):
        widget.setParent(link_card)
        actions.addWidget(widget)
    actions.addStretch(1)
    link_layout.addLayout(actions)

    self.download_progress.setParent(link_card)
    link_layout.addWidget(self.download_progress)

    status_row = QHBoxLayout()
    self.download_status.setParent(link_card)
    self.download_percent.setParent(link_card)
    status_row.addWidget(self.download_status, 1)
    status_row.addWidget(self.download_percent)
    link_layout.addLayout(status_row)

    self.binary_status.setParent(link_card)
    link_layout.addWidget(self.binary_status)

    for frame in (info_frame, quality_frame, summary_frame):
        try:
            frame.hide()
        except Exception:
            pass

    self.analysis_data = {}
    self.download_status.setText('Cole o link, escolha a qualidade e clique em BAIXAR VÍDEO.')

    def url_changed(text):
        enabled = bool(str(text or '').strip())
        if not (getattr(self, 'download_worker', None) and self.download_worker.isRunning()):
            self.btn_download.setEnabled(enabled)

    self.url_edit.textChanged.connect(url_changed)
    self.url_edit.returnPressed.connect(self.download_video)

    # Corrige textos antigos nas Configurações que ainda mencionavam ANALISAR.
    for label in self.findChildren(QLabel):
        text = label.text()
        if 'pelo ANALISAR e BAIXAR' in text:
            label.setText(text.replace('pelo ANALISAR e BAIXAR', 'pelo BAIXAR'))
        elif 'tente ANALISAR novamente' in text:
            label.setText(text.replace('tente ANALISAR novamente', 'tente BAIXAR novamente'))

    url_changed(self.url_edit.text())


def _start_direct_worker(self, url, proxy, quality_index, route=None):
    label, target_height, fmt, compat = DIRECT_QUALITIES[quality_index]
    route = route or {}

    if bool(route.get('is_live')) and core.is_youtube(url):
        heights = [2160, 1440, 1080, 720, 480, 360]
        core_index = min(
            range(len(heights)),
            key=lambda idx: abs(heights[idx] - int(target_height or 2160))
        )
        self.download_status.setText('🔴 Live detectada. Baixando do início até o ponto atual...')
        self.download_worker = base.LiveSnapshotWorker(
            url,
            core_index,
            proxy,
            route.get('live_start_timestamp') or 0,
        )
    else:
        self.download_status.setText(
            f'Iniciando download direto em {label}...'
        )
        self.download_worker = core.DownloadWorker(
            url,
            0,
            proxy,
            format_selector=fmt,
            compat_selector=compat,
        )

    self.download_worker.progress.connect(self._update_download_progress)
    self.download_worker.message.connect(self.download_status.setText)
    self.download_worker.done.connect(self.download_finished)
    self.download_worker.failed.connect(self.download_failed)
    self.download_worker.canceled.connect(self.download_canceled)
    self.download_worker.start()


def direct_download_video(self):
    url = self.url_edit.text().strip()
    if v207._is_r7_url(url):
        url = v207._clean_r7_url(url)
        if self.url_edit.text().strip() != url:
            self.url_edit.setText(url)

    if not url.startswith(('http://', 'https://')):
        QMessageBox.warning(
            self,
            core.APP_NAME,
            'Cole um link válido começando com http:// ou https://'
        )
        return

    if getattr(self, 'download_worker', None) and self.download_worker.isRunning():
        return
    if getattr(self, 'direct_route_worker', None) and self.direct_route_worker.isRunning():
        return

    proxy = self._current_proxy_url(True)
    if proxy is None:
        return

    quality_index = max(
        0,
        min(len(DIRECT_QUALITIES) - 1, self.direct_quality_combo.currentIndex())
    )

    self._update_proxy_status()
    self._update_download_progress(0)
    self._set_download_busy(True)

    if core.is_youtube(url):
        self.download_status.setText('Preparando download do YouTube...')
        self.direct_route_worker = YouTubeRouteWorker(url, proxy)
        self.direct_route_worker.done.connect(
            lambda route: _start_direct_worker(
                self, url, proxy, quality_index, route
            )
        )
        self.direct_route_worker.start()
        return

    _start_direct_worker(self, url, proxy, quality_index, {})


# A nova versão usa o mesmo downloader direto em todos os sites.
core.DownloadWorker = R7DirectDownloadWorker
core.MainWindow.download_video = direct_download_video
core.MainWindow._build_ui = _build_ui_v208

# Mantém o versionamento correto através das camadas anteriores.
core.APP_VERSION = APP_VERSION
v207.APP_VERSION = APP_VERSION
v207.SIDEBAR_VERSION = SIDEBAR_VERSION
v207.v206.APP_VERSION = APP_VERSION
v207.v206.SIDEBAR_VERSION = SIDEBAR_VERSION
v207.v205.APP_VERSION = APP_VERSION
v207.v205.SIDEBAR_VERSION = SIDEBAR_VERSION
v207.v203.APP_VERSION = APP_VERSION
v207.v203.SIDEBAR_VERSION = SIDEBAR_VERSION


def main():
    core.APP_VERSION = APP_VERSION
    v207.APP_VERSION = APP_VERSION
    v207.SIDEBAR_VERSION = SIDEBAR_VERSION
    v207.v206.APP_VERSION = APP_VERSION
    v207.v206.SIDEBAR_VERSION = SIDEBAR_VERSION
    v207.v205.APP_VERSION = APP_VERSION
    v207.v205.SIDEBAR_VERSION = SIDEBAR_VERSION
    v207.v203.APP_VERSION = APP_VERSION
    v207.v203.SIDEBAR_VERSION = SIDEBAR_VERSION
    return v207.main()


if __name__ == '__main__':
    main()
