import json
import os
import re
import subprocess
import urllib.parse
import urllib.request

import refined_layout_v206 as v206

APP_VERSION = 'Windows Portable v2.0.7 — R7 Android Flow + HLS/TS + Sessão Globoplay Persistente'
SIDEBAR_VERSION = 'v2.0.7  •  R7 ANDROID FLOW'

core = v206.core
v205 = v206.v205
v203 = v206.v203
v202 = v203.v202
v201 = v202.v201
base = v203.base

# Classe original do Windows v1.9.22, antes de a v2.0.3 substituir o R7
# por um worker dedicado. Ela já implementa o mesmo fluxo genérico usado
# pelo Android: URL da matéria -> yt-dlp -> HTML -> candidatos + Referer.
OriginalDownloadWorker = v203.R7DownloadWorker.__mro__[1]

_R7_ANALYZED_TARGETS = {}


def _clean_r7_url(value):
    return v205._clean_r7_url(value)


def _is_r7_url(value):
    return v203._is_r7_url(_clean_r7_url(value))


def _android_extract_candidates(page_html, page_url):
    """Replica a ordem e o limite do extrator Android v1.9.17."""
    text = str(page_html or '')
    text = (
        text.replace('\\u0026', '&')
        .replace('\\u003d', '=')
        .replace('\\u002f', '/')
        .replace('\\/', '/')
        .replace('&amp;', '&')
    )
    result = []
    seen = set()

    def is_video_candidate(url):
        low = str(url or '').lower()
        return any(key in low for key in (
            '.mp4', '.m3u8', '.mpd', 'player', 'video', 'embed', 'stream'
        ))

    def add(value, force=False):
        if value is None or len(result) >= 15:
            return
        raw = (
            str(value).strip()
            .replace('&amp;', '&')
            .replace('\\u0026', '&')
            .replace('\\u003d', '=')
            .replace('\\u002f', '/')
            .replace('\\/', '/')
        )
        try:
            url = urllib.parse.urljoin(page_url, raw)
        except Exception:
            return
        if not re.match(r'(?i)^https?://.+', url):
            return
        if not force and not is_video_candidate(url):
            return
        if url not in seen:
            seen.add(url)
            result.append(url)

    # Mesma ordem do Android.
    for match in re.finditer(r'https?://[^\s"\'<>]+', text, re.I):
        add(match.group(0))
        if len(result) >= 15:
            return result

    for match in re.finditer(
        r'\b(?:src|content|file|href)\s*=\s*["\']([^"\']+)["\']',
        text, re.I
    ):
        add(match.group(1))
        if len(result) >= 15:
            return result

    for match in re.finditer(
        r'["\'](?:contentUrl|embedUrl|videoUrl|streamUrl|file|src|url)["\']'
        r'\s*:\s*["\']([^"\']+)["\']',
        text, re.I
    ):
        add(match.group(1), True)
        if len(result) >= 15:
            return result

    for match in re.finditer(
        r'<meta[^>]+(?:property|name)=["\']'
        r'(?:og:video(?::url|:secure_url)?|twitter:player(?::stream)?)["\']'
        r'[^>]+content=["\']([^"\']+)["\'][^>]*>',
        text, re.I
    ):
        add(match.group(1), True)
        if len(result) >= 15:
            return result

    # O Android também aceita meta tags com content vindo antes de property/name.
    for match in re.finditer(
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\']'
        r'(?:og:video(?::url|:secure_url)?|twitter:player(?::stream)?)["\'][^>]*>',
        text, re.I
    ):
        add(match.group(1), True)
        if len(result) >= 15:
            return result

    for match in re.finditer(
        r'<iframe[^>]+src=["\']([^"\']+)["\'][^>]*>',
        text, re.I
    ):
        add(match.group(1), True)
        if len(result) >= 15:
            return result

    return result[:15]


def _r7_candidates_from_page(page_url, proxy_url=''):
    page_url = _clean_r7_url(page_url)
    page_html = core.fetch_html(page_url, proxy_url)
    return _android_extract_candidates(page_html, page_url)


def _r7_probe_command(url, proxy_url='', referer=''):
    cmd = [
        str(core.YTDLP_EXE),
        '--no-playlist',
        '--dump-single-json',
        '--skip-download',
        '--no-mtime',
        '--force-ipv4',
        '--retries', '10',
        '--fragment-retries', '10',
        '--socket-timeout', '30',
        '--ffmpeg-location', str(core.BIN_DIR),
    ]
    if core.DENO_EXE.exists():
        cmd += ['--js-runtimes', f'deno:{core.DENO_EXE}']
    if proxy_url:
        cmd += ['--proxy', proxy_url]
    if referer:
        cmd += ['--referer', referer]
    cmd.append(url)
    return cmd


def _analysis_payload(data, original_url, resolved_url):
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
            height = int(fmt.get('height') or 0)
            if height > 0:
                video_formats.append(fmt)
        elif acodec != 'none':
            audio_formats.append(fmt)

    if not video_formats:
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
            key=lambda item: (
                float(item.get('abr') or 0),
                float(item.get('tbr') or 0),
                float(item.get('filesize') or item.get('filesize_approx') or 0),
            )
        )

    grouped = {}
    for fmt in video_formats:
        grouped.setdefault(int(fmt.get('height') or 0), []).append(fmt)

    label_map = {
        2160: '2160p (4K)',
        1440: '1440p (2K)',
        1080: '1080p (Full HD)',
        720: '720p (HD)',
        540: '540p',
        480: '480p',
        360: '360p',
        240: '240p',
    }
    available = []
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
            audio_size = best_audio.get('filesize') or best_audio.get('filesize_approx')
            if not audio_size and best_audio.get('tbr') and duration:
                audio_size = float(best_audio.get('tbr')) * 1000.0 * duration / 8.0
            if size and audio_size:
                size = float(size) + float(audio_size)
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
        raise RuntimeError('INDISPONÍVEL: nenhuma resolução utilizável foi confirmada.')

    thumb_bytes = b''
    thumb = data.get('thumbnail') or ''
    if thumb:
        try:
            request = urllib.request.Request(
                thumb, headers={'User-Agent': 'Mozilla/5.0'}
            )
            with urllib.request.urlopen(request, timeout=12) as response:
                thumb_bytes = response.read(2_000_000)
        except Exception:
            pass

    estimates = {int(item['height']): item.get('estimate') or 0 for item in available}
    return {
        'title': data.get('title') or 'Vídeo',
        'channel': data.get('channel') or data.get('uploader') or 'Fonte não informada',
        'duration': int(duration),
        'width': int(data.get('width') or 0),
        'height': int(data.get('height') or 0),
        'estimates': estimates,
        'available_qualities': available,
        'thumbnail_bytes': thumb_bytes,
        # A referência da análise permanece a matéria original para o botão BAIXAR.
        'webpage_url': original_url,
        'analyzed_input_url': original_url,
        'r7_resolved_url': resolved_url,
        'live_status': str(data.get('live_status') or ''),
        'is_live': bool(data.get('is_live') or False),
        'live_start_timestamp': 0,
        'analysis_snapshot_timestamp': 0,
        'live_elapsed': 0,
    }


def _probe_r7_candidate(candidate, original_url, proxy_url='', referer=''):
    cmd = _r7_probe_command(candidate, proxy_url, referer)
    flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0) if os.name == 'nt' else 0
    kwargs = dict(
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace',
        creationflags=flags,
        timeout=90,
    )
    if hasattr(core, 'subprocess_environment'):
        kwargs['env'] = core.subprocess_environment(proxy_url)
    result = subprocess.run(cmd, **kwargs)
    if result.returncode != 0:
        return None, (result.stderr or result.stdout or 'Falha ao analisar o R7.')[-3000:]
    try:
        data = json.loads(result.stdout)
        return _analysis_payload(data, original_url, candidate), ''
    except Exception as exc:
        return None, str(exc)


class R7AndroidAnalyzeWorker(v201.GloboplayAnalyzeWorker):
    """ANALISAR no R7 seguindo a mesma ordem do Android v1.9.17."""

    def run(self):
        if not _is_r7_url(self.url):
            return super().run()

        original_url = _clean_r7_url(self.url)
        last_error = ''

        # 1) Igual ao Android: primeiro o próprio link da matéria.
        payload, last_error = _probe_r7_candidate(
            original_url, original_url, self.proxy_url, ''
        )
        if payload:
            _R7_ANALYZED_TARGETS[original_url] = original_url
            self.done.emit(payload)
            return

        # DRM continua sendo respeitado; não tentamos contornar.
        if 'drm' in str(last_error).lower():
            self.failed.emit(
                'INDISPONÍVEL: este vídeo está protegido por DRM. '
                'O aplicativo não tenta contornar essa proteção.'
            )
            return

        # 2) Igual ao Android: HTML -> até 15 candidatos na ordem natural.
        try:
            candidates = _r7_candidates_from_page(original_url, self.proxy_url)
        except Exception as exc:
            self.failed.emit(str(exc))
            return

        for candidate in candidates:
            payload, last_error = _probe_r7_candidate(
                candidate, original_url, self.proxy_url, original_url
            )
            if payload:
                _R7_ANALYZED_TARGETS[original_url] = candidate
                self.done.emit(payload)
                return
            if 'drm' in str(last_error).lower():
                self.failed.emit(
                    'INDISPONÍVEL: o candidato de vídeo está protegido por DRM. '
                    'O aplicativo não tenta contornar essa proteção.'
                )
                return

        self.failed.emit(
            'R7: o link da matéria e os candidatos encontrados no HTML foram testados, '
            'mas nenhum formato realmente disponível foi confirmado.\n\n'
            + str(last_error or 'Nenhum candidato utilizável.')
        )


class R7AndroidDownloadWorker(OriginalDownloadWorker):
    """Restaura o R7 ao fluxo genérico comprovado no Android."""

    def _base_cmd(self, fmt, referer='', extractor_args='', force_ipv4=False):
        cmd = super()._base_cmd(
            fmt,
            referer=referer,
            extractor_args=extractor_args,
            force_ipv4=(True if _is_r7_url(self.url) else force_ipv4),
        )
        if not _is_r7_url(self.url):
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
        # Substitui timeout menor, se houver, pelo valor comprovado no Android.
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
        if not _is_r7_url(self.url):
            return super().run()

        # Limpa URL duplicada antes de qualquer tentativa.
        self.url = _clean_r7_url(self.url)

        if not core.YTDLP_EXE.exists():
            self.failed.emit('yt-dlp.exe não encontrado na pasta bin.')
            return
        if not core.FFMPEG_EXE.exists():
            self.failed.emit('ffmpeg.exe não encontrado na pasta bin.')
            return

        fmt = self.format_selector or core.FORMATS[self.quality_index]
        self.progress.emit(0)

        # 1) Android: tentativa principal diretamente na matéria.
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

        if 'drm' in str(last_error).lower():
            self._fail_with_diagnostic(last_error)
            return

        self.message.emit(
            'R7: método principal falhou. Procurando vídeos dentro da página...'
        )
        try:
            candidates = _r7_candidates_from_page(self.url, self.proxy_url)
        except Exception as exc:
            self._fail_with_diagnostic(str(exc))
            return

        # Se a análise já confirmou um candidato, testamos esse primeiro.
        cached = _R7_ANALYZED_TARGETS.get(self.url)
        if cached and cached != self.url:
            candidates = [cached] + [item for item in candidates if item != cached]

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
            if 'drm' in str(last_error).lower():
                self._fail_with_diagnostic(last_error)
                return

        self._fail_with_diagnostic(
            last_error or
            'R7: nenhum dos candidatos encontrados na página concluiu o download.'
        )


# Substitui somente o comportamento do R7. Globoplay, YouTube, Editor, timeline,
# proxy e demais recursos continuam nas mesmas classes/patches das versões anteriores.
base.AnalyzeWorker = R7AndroidAnalyzeWorker
core.DownloadWorker = R7AndroidDownloadWorker

core.APP_VERSION = APP_VERSION
v203.APP_VERSION = APP_VERSION
v203.SIDEBAR_VERSION = SIDEBAR_VERSION
v205.APP_VERSION = APP_VERSION
v205.SIDEBAR_VERSION = SIDEBAR_VERSION
v206.APP_VERSION = APP_VERSION
v206.SIDEBAR_VERSION = SIDEBAR_VERSION


def main():
    core.APP_VERSION = APP_VERSION
    v203.APP_VERSION = APP_VERSION
    v203.SIDEBAR_VERSION = SIDEBAR_VERSION
    v205.APP_VERSION = APP_VERSION
    v205.SIDEBAR_VERSION = SIDEBAR_VERSION
    v206.APP_VERSION = APP_VERSION
    v206.SIDEBAR_VERSION = SIDEBAR_VERSION
    return v206.main()


if __name__ == '__main__':
    main()
