import os
import subprocess
import urllib.request

import refined_layout_v208 as v208

APP_VERSION = 'Windows Portable v2.0.9 — R7 Paridade Real Android + Download Direto'
SIDEBAR_VERSION = 'v2.0.9  •  R7 PARIDADE ANDROID'

core = v208.core

ANDROID_USER_AGENT = (
    'Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 '
    'Chrome/149.0.0.0 Mobile Safari/537.36'
)


def _fetch_r7_html_like_android(page_url, proxy_url=''):
    """Baixa o HTML do R7 com os mesmos cabeçalhos usados pelo Android funcional."""
    request = urllib.request.Request(
        page_url,
        headers={
            'User-Agent': ANDROID_USER_AGENT,
            'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
            'Accept': 'text/html,application/xhtml+xml,*/*;q=0.8',
        },
    )
    opener = core._proxy_opener(proxy_url)
    with opener.open(request, timeout=45) as response:
        content_type = str(response.headers.get('Content-Type') or '')
        if content_type and 'text/html' not in content_type.lower():
            return '', str(response.geturl() or page_url)
        raw = response.read()
        charset = 'utf-8'
        try:
            charset = response.headers.get_content_charset() or 'utf-8'
        except Exception:
            pass
        return raw.decode(charset, 'replace'), str(response.geturl() or page_url)


def _r7_candidates_android_network(page_url, proxy_url=''):
    page_url = v208.v207._clean_r7_url(page_url)
    html, final_url = _fetch_r7_html_like_android(page_url, proxy_url)
    # Se houve redirecionamento HTTP, usa a URL final como base para relativos.
    # Isso mantém o comportamento do Android e ainda evita candidatos quebrados
    # quando o R7 redireciona um slug antigo para a matéria canônica.
    return v208.v207._android_extract_candidates(html, final_url or page_url)


class R7AndroidParityDownloadWorker(v208.R7DirectDownloadWorker):
    """R7 com rede equivalente ao Android: comando enxuto + HTML Chrome Mobile."""

    def _base_cmd(self, fmt, referer='', extractor_args='', force_ipv4=False):
        if not v208.v207._is_r7_url(self.url):
            return super()._base_cmd(
                fmt,
                referer=referer,
                extractor_args=extractor_args,
                force_ipv4=force_ipv4,
            )

        output = str(core.VIDEOS_DIR / '%(title).100B [%(id)s].%(ext)s')
        cmd = [
            str(core.YTDLP_EXE),
            '--no-mtime',
            '--no-playlist',
            '--force-ipv4',
            '--retries', '10',
            '--fragment-retries', '10',
            '--socket-timeout', '30',
            '--ffmpeg-location', str(core.BIN_DIR),
            '-f', fmt,
            '--merge-output-format', 'mp4',
            '--remux-video', 'mp4',
        ]
        if self.proxy_url:
            cmd += ['--proxy', self.proxy_url]
        if referer:
            cmd += ['--referer', referer]
        cmd += [
            '-o', output,
            '--print', 'before_dl:VIDEO_TITLE:%(title)s',
            '--print', 'after_move:FINAL_FILE:%(filepath)s',
        ]
        return cmd

    def run(self):
        if not v208.v207._is_r7_url(self.url):
            return super().run()

        self.url = v208.v207._clean_r7_url(self.url)

        if not core.YTDLP_EXE.exists():
            self.failed.emit('yt-dlp.exe não encontrado na pasta bin.')
            return
        if not core.FFMPEG_EXE.exists():
            self.failed.emit('ffmpeg.exe não encontrado na pasta bin.')
            return

        fmt = self.format_selector or core.FORMATS[self.quality_index]
        self.progress.emit(0)

        # 1) Exatamente como no Android: tenta primeiro a própria matéria.
        ok, final_file, last_error = self._attempt(
            self.url,
            fmt,
            label='R7: tentativa principal igual ao Android...',
            force_ipv4=True,
        )
        if ok and self._finish_if_ok(ok, final_file, last_error):
            return
        if self._cancel_requested:
            self.canceled.emit()
            return

        # 2) Exatamente como no Android: HTML com Chrome Mobile -> até 15 candidatos.
        self.message.emit(
            'R7: tentativa principal falhou. Lendo a página como Android...'
        )
        try:
            candidates = _r7_candidates_android_network(self.url, self.proxy_url)
        except Exception as exc:
            self._fail_with_diagnostic(str(exc))
            return

        for index, candidate in enumerate(candidates[:15], 1):
            ok, final_file, last_error = self._attempt(
                candidate,
                fmt,
                referer=self.url,
                label=f'R7 Android: alternativa {index}/{min(15, len(candidates))}...',
                force_ipv4=True,
            )
            if ok and self._finish_if_ok(ok, final_file, last_error):
                return
            if self._cancel_requested:
                self.canceled.emit()
                return

        self._fail_with_diagnostic(
            last_error or
            'R7: nenhum candidato obtido com o mesmo fluxo de rede do Android concluiu o download.'
        )


class StableUpdateWorker(core.UpdateWorker):
    """Mantém o yt-dlp do Windows no canal estável, igual ao Android."""

    def run(self):
        if not core.YTDLP_EXE.exists():
            self.failed.emit('yt-dlp.exe não encontrado na pasta bin.')
            return
        cmd = [str(core.YTDLP_EXE), '--update-to', 'stable']
        if self.proxy_url:
            cmd += ['--proxy', self.proxy_url]
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                creationflags=(getattr(subprocess, 'CREATE_NO_WINDOW', 0) if os.name == 'nt' else 0),
            )
            text = '\n'.join(
                item for item in (result.stdout.strip(), result.stderr.strip()) if item
            ).strip()
            if result.returncode == 0:
                self.done.emit(text or 'yt-dlp estável atualizado.')
            else:
                self.failed.emit(core.friendly_network_error(text or 'Falha ao atualizar o yt-dlp.'))
        except Exception as exc:
            self.failed.emit(core.friendly_network_error(exc))


# O restante do aplicativo continua exatamente na v2.0.8.
core.DownloadWorker = R7AndroidParityDownloadWorker
core.UpdateWorker = StableUpdateWorker

core.APP_VERSION = APP_VERSION
v208.APP_VERSION = APP_VERSION
v208.SIDEBAR_VERSION = SIDEBAR_VERSION
v208.v207.APP_VERSION = APP_VERSION
v208.v207.SIDEBAR_VERSION = SIDEBAR_VERSION
v208.v207.v206.APP_VERSION = APP_VERSION
v208.v207.v206.SIDEBAR_VERSION = SIDEBAR_VERSION
v208.v207.v205.APP_VERSION = APP_VERSION
v208.v207.v205.SIDEBAR_VERSION = SIDEBAR_VERSION
v208.v207.v203.APP_VERSION = APP_VERSION
v208.v207.v203.SIDEBAR_VERSION = SIDEBAR_VERSION


def main():
    core.APP_VERSION = APP_VERSION
    v208.APP_VERSION = APP_VERSION
    v208.SIDEBAR_VERSION = SIDEBAR_VERSION
    v208.v207.APP_VERSION = APP_VERSION
    v208.v207.SIDEBAR_VERSION = SIDEBAR_VERSION
    return v208.main()


if __name__ == '__main__':
    main()
