import json
import os
import re
import sys
import urllib.parse
import urllib.request

import refined_layout_v202 as v202

APP_VERSION = 'Windows Portable v2.0.3 — R7 Player Fix + Sessão Globoplay Persistente'
SIDEBAR_VERSION = 'v2.0.3  •  R7 PLAYER FIX'

base = v202.v201.base
core = base.core


def _is_r7_url(url):
    try:
        host = (urllib.parse.urlparse(str(url or '')).hostname or '').lower()
    except Exception:
        return False
    return host == 'r7.com' or host.endswith('.r7.com')


def _unescape_url(value):
    text = str(value or '').strip()
    return (
        text.replace('\\u0026', '&')
        .replace('\\u003d', '=')
        .replace('\\u002f', '/')
        .replace('\\/', '/')
        .replace('&amp;', '&')
    )


def _r7_video_ids(page_html):
    text = str(page_html or '')
    patterns = (
        r'(?i)player(?:-api)?\.r7\.com/video/i/([0-9a-f]{24})',
        r'(?i)/idmedia/([0-9a-f]{24})',
        r'(?is)<div[^>]+(?:id=["\']player-|class=["\']embed["\'][^>]+id=["\'])([0-9a-f]{24})',
        r'(?i)["\'](?:idMedia|id_media|videoId|video_id|idVideo)["\']\s*[:=]\s*["\']([0-9a-f]{24})',
        r'(?i)data-(?:video-id|id-media)=["\']([0-9a-f]{24})["\']',
    )
    result = []
    seen = set()
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            video_id = match.group(1).lower()
            if video_id not in seen:
                seen.add(video_id)
                result.append(video_id)
    return result


def _request_json(url, proxy_url='', referer=''):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/151.0.0.0 Safari/537.36',
        'Accept': 'application/json,text/plain,*/*',
        'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
    }
    if referer:
        headers['Referer'] = referer
    request = urllib.request.Request(url, headers=headers)
    if hasattr(core, '_proxy_opener'):
        opener = core._proxy_opener(proxy_url)
    elif proxy_url:
        opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({'http': proxy_url, 'https': proxy_url})
        )
    else:
        opener = urllib.request.build_opener()
    with opener.open(request, timeout=35) as response:
        raw = response.read().decode('utf-8', 'replace')
    return json.loads(raw)


def _media_urls_from_object(value):
    preferred = []
    others = []

    def add(raw):
        url = _unescape_url(raw)
        if not re.match(r'(?i)^https?://', url):
            return
        low = url.lower().split('?', 1)[0]
        if '.m3u8' in low:
            preferred.append(url)
        elif any(ext in low for ext in ('.mp4', '.mpd', '.m4v')):
            others.append(url)

    def walk(obj):
        if isinstance(obj, dict):
            for key in (
                'media_url_hls', 'mediaUrlHls', 'hls_url', 'hlsUrl', 'url_hls',
                'media_url', 'mediaUrl', 'video_url', 'videoUrl', 'file', 'src', 'url',
            ):
                if key in obj and isinstance(obj.get(key), str):
                    add(obj.get(key))
            for item in obj.values():
                walk(item)
        elif isinstance(obj, (list, tuple)):
            for item in obj:
                walk(item)
        elif isinstance(obj, str):
            add(obj)

    walk(value)
    return preferred + others


def _r7_direct_urls_from_html(page_html):
    text = _unescape_url(page_html)
    result = []
    seen = set()
    for match in re.finditer(r'https?://[^\s"\'<>]+', text, re.I):
        url = match.group(0).rstrip('),;]')
        low = url.lower().split('?', 1)[0]
        if not any(ext in low for ext in ('.m3u8', '.mp4', '.mpd', '.m4v')):
            continue
        if url not in seen:
            seen.add(url)
            result.append(url)
    result.sort(key=lambda u: (0 if '.m3u8' in u.lower() else 1, len(u)))
    return result


def _resolve_r7_candidates(page_url, proxy_url=''):
    page_html = core.fetch_html(page_url, proxy_url)
    candidates = []
    seen = set()

    def add(url):
        final = _unescape_url(url)
        if final and re.match(r'(?i)^https?://', final) and final not in seen:
            seen.add(final)
            candidates.append(final)

    # Primeiro priorizamos mídia já exposta no HTML atual do R7.
    for url in _r7_direct_urls_from_html(page_html):
        add(url)

    # O player do R7 historicamente usa um ID interno de 24 caracteres e a
    # player-api.r7.com para entregar media_url_hls/media_url. Mantemos HTTPS
    # como primeira tentativa e HTTP apenas como fallback de compatibilidade.
    for video_id in _r7_video_ids(page_html):
        payload = None
        for api_url in (
            f'https://player-api.r7.com/video/i/{video_id}',
            f'http://player-api.r7.com/video/i/{video_id}',
        ):
            try:
                payload = _request_json(api_url, proxy_url, page_url)
                if isinstance(payload, (dict, list)):
                    break
            except Exception:
                payload = None
        if payload is not None:
            for url in _media_urls_from_object(payload):
                add(url)
        # Também deixamos o player como último fallback caso a API mude o JSON.
        add(f'https://player.r7.com/video/i/{video_id}')

    # Candidatos genéricos ficam por último, para não vencerem um HLS real do R7.
    try:
        for url in core.extract_candidates_from_html(page_html, page_url):
            add(url)
    except Exception:
        pass

    return candidates[:20]


class R7AnalyzeWorker(v202.v201.GloboplayAnalyzeWorker):
    def run(self):
        if not _is_r7_url(self.url):
            return super().run()
        original_url = self.url
        try:
            candidates = _resolve_r7_candidates(original_url, self.proxy_url)
            media = next(
                (u for u in candidates if any(x in u.lower() for x in ('.m3u8', '.mp4', '.mpd', '.m4v'))),
                candidates[0] if candidates else '',
            )
            if not media:
                self.failed.emit(
                    'R7: o player foi localizado, mas nenhuma mídia HLS/MP4 utilizável foi encontrada.'
                )
                return
            self.url = media
            return super().run()
        except Exception as exc:
            self.failed.emit('R7: não foi possível resolver o player desta matéria.\n\n' + str(exc))
        finally:
            self.url = original_url


class R7DownloadWorker(core.DownloadWorker):
    def run(self):
        if not _is_r7_url(self.url):
            return super().run()
        if not core.YTDLP_EXE.exists():
            self.failed.emit('yt-dlp.exe não encontrado na pasta bin.')
            return
        if not core.FFMPEG_EXE.exists():
            self.failed.emit('ffmpeg.exe não encontrado na pasta bin.')
            return

        fmt = self.format_selector or core.FORMATS[self.quality_index]
        compat = self.compat_selector or core.COMPAT_FORMATS[self.quality_index]
        self.progress.emit(0)

        try:
            candidates = _resolve_r7_candidates(self.url, self.proxy_url)
        except Exception as exc:
            self._fail_with_diagnostic('R7: falha ao localizar o player. ' + str(exc))
            return

        if not candidates:
            self._fail_with_diagnostic(
                'R7: nenhuma URL de mídia foi encontrada no player desta matéria.'
            )
            return

        last_err = ''
        for index, candidate in enumerate(candidates, 1):
            label = f'R7: tentativa {index}/{len(candidates)} pelo player...'
            ok, file, last_err = self._attempt(
                candidate, fmt, referer=self.url, label=label
            )
            if ok and self._finish_if_ok(ok, file, last_err):
                return
            if self._cancel_requested:
                self.canceled.emit()
                return

            low = (last_err or '').lower()
            if any(k in low for k in ('requested format', 'format is not available', '403', 'forbidden')):
                ok, file, last_err = self._attempt(
                    candidate, compat, referer=self.url,
                    label=f'R7: modo compatibilidade {index}/{len(candidates)}...'
                )
                if ok and self._finish_if_ok(ok, file, last_err):
                    return
                if self._cancel_requested:
                    self.canceled.emit()
                    return

        self._fail_with_diagnostic(last_err or 'R7: o player foi encontrado, mas o download não foi concluído.')


base.AnalyzeWorker = R7AnalyzeWorker
core.DownloadWorker = R7DownloadWorker
core.APP_VERSION = APP_VERSION
v202.APP_VERSION = APP_VERSION
v202.SIDEBAR_VERSION = SIDEBAR_VERSION


def main():
    core.APP_VERSION = APP_VERSION
    v202.APP_VERSION = APP_VERSION
    v202.SIDEBAR_VERSION = SIDEBAR_VERSION
    return v202.main()


if __name__ == '__main__':
    main()
