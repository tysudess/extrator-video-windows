import os
import re
import subprocess
import time
import urllib.parse
import urllib.request
from datetime import datetime

import refined_layout_v204 as v204

APP_VERSION = 'Windows Portable v2.0.5 — R7 HLS/TS Fix + Selection Fix + Sessão Globoplay Persistente'
SIDEBAR_VERSION = 'v2.0.5  •  R7 HLS/TS FIX'

core = v204.core
v203 = v204.v203

_original_resolver = v203._resolve_r7_candidates
_original_r7_attempt = v203.R7DownloadWorker._attempt
_original_analyze_video = core.MainWindow.analyze_video


def _clean_r7_url(value):
    """Remove uma segunda URL colada acidentalmente após a primeira URL R7."""
    text = str(value or '').strip()
    if not v203._is_r7_url(text):
        return text
    positions = []
    for token in ('https://', 'http://'):
        pos = text.find(token, len(token))
        if pos > 0:
            positions.append(pos)
    if positions:
        text = text[:min(positions)].strip()
    return text.rstrip(' /') + '/'


def _request_text(url, proxy_url='', referer=''):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/151.0.0.0 Safari/537.36',
        'Accept': 'application/json,text/plain,text/html,*/*',
        'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
    }
    if referer:
        headers['Referer'] = referer
        try:
            parsed = urllib.parse.urlparse(referer)
            if parsed.scheme and parsed.netloc:
                headers['Origin'] = f'{parsed.scheme}://{parsed.netloc}'
        except Exception:
            pass
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
        return response.read(6_000_000).decode('utf-8', 'replace')


def _extract_stream_urls(text, base_url):
    """Extrai HLS/MP4 mesmo quando a URL está escapada ou percent-encoded."""
    raw = v203._unescape_url(text)
    raw = raw.replace('\\x2F', '/').replace('\\x3A', ':').replace('\\x26', '&')
    for _ in range(2):
        try:
            decoded = urllib.parse.unquote(raw)
        except Exception:
            decoded = raw
        if decoded == raw:
            break
        raw = decoded

    result = []
    seen = set()

    def add(value):
        value = v203._unescape_url(value).strip().strip('"\'')
        if value.startswith('//'):
            value = 'https:' + value
        try:
            final = urllib.parse.urljoin(base_url, value)
        except Exception:
            return
        low = final.lower()
        if not re.match(r'(?i)^https?://', final):
            return
        if not any(ext in low for ext in ('.m3u8', '.mp4', '.m4v')):
            return
        if final not in seen:
            seen.add(final)
            result.append(final)

    for match in re.finditer(r'(?:(?:https?:)?//)[^\s"\'<>\\]+?\.(?:m3u8|mp4|m4v)(?:\?[^\s"\'<>\\]*)?', raw, re.I):
        add(match.group(0))
    for match in re.finditer(r'["\']([^"\']+?\.(?:m3u8|mp4|m4v)(?:\?[^"\']*)?)["\']', raw, re.I):
        add(match.group(1))

    result.sort(key=lambda u: (0 if '.m3u8' in u.lower() else 1, len(u)))
    return result


def _resolve_r7_candidates_v205(page_url, proxy_url=''):
    page_url = _clean_r7_url(page_url)
    result = []
    seen = set()

    def add(url):
        final = v203._unescape_url(url)
        if final.startswith('//'):
            final = 'https:' + final
        if final and re.match(r'(?i)^https?://', final) and final not in seen:
            seen.add(final)
            result.append(final)

    seed_pages = []
    seed_seen = set()

    def seed(url):
        final = v203._unescape_url(url)
        if final.startswith('//'):
            final = 'https:' + final
        if final and re.match(r'(?i)^https?://', final) and final not in seed_seen:
            seed_seen.add(final)
            seed_pages.append(final)

    article_html = ''
    try:
        article_html = core.fetch_html(page_url, proxy_url)
    except Exception:
        pass

    if article_html:
        for media in _extract_stream_urls(article_html, page_url):
            add(media)
        try:
            for candidate in core.extract_candidates_from_html(article_html, page_url):
                low = candidate.lower()
                if any(ext in low for ext in ('.m3u8', '.mp4', '.m4v')):
                    add(candidate)
                elif any(k in low for k in ('player', 'embed', 'video')):
                    seed(candidate)
        except Exception:
            pass
        for video_id in v203._r7_video_ids(article_html):
            seed(f'https://player-api.r7.com/video/i/{video_id}')
            seed(f'https://player.r7.com/video/i/{video_id}')

    try:
        for candidate in _original_resolver(page_url, proxy_url):
            low = candidate.lower()
            if any(ext in low for ext in ('.m3u8', '.mp4', '.m4v')):
                add(candidate)
            else:
                seed(candidate)
    except Exception:
        pass

    # O R7 pode carregar o manifesto apenas dentro do HTML/JSON do player.
    # Fazemos uma segunda leitura dos endpoints do player, semelhante ao que
    # gerenciadores de download enxergam quando o navegador inicia o HLS.
    extra_seeds = []
    for endpoint in seed_pages[:16]:
        try:
            raw = _request_text(endpoint, proxy_url, page_url)
        except Exception:
            continue
        for media in _extract_stream_urls(raw, endpoint):
            add(media)
        try:
            for candidate in core.extract_candidates_from_html(raw, endpoint):
                low = candidate.lower()
                if any(ext in low for ext in ('.m3u8', '.mp4', '.m4v')):
                    add(candidate)
                elif any(k in low for k in ('player', 'embed')):
                    extra_seeds.append(candidate)
        except Exception:
            pass
        for video_id in v203._r7_video_ids(raw):
            extra_seeds.append(f'https://player-api.r7.com/video/i/{video_id}')

    for endpoint in extra_seeds[:8]:
        try:
            raw = _request_text(endpoint, proxy_url, page_url)
            for media in _extract_stream_urls(raw, endpoint):
                add(media)
        except Exception:
            pass

    # Mantém os players como fallback depois das mídias reais.
    for endpoint in seed_pages:
        add(endpoint)

    return result[:30]


def _ffmpeg_hls_attempt(self, manifest_url, referer, proxy_url=''):
    if not core.FFMPEG_EXE.exists():
        return False, '', 'ffmpeg.exe não encontrado para o fallback HLS/TS do R7.'

    stamp = datetime.now().strftime('%Y%m%d-%H%M%S') + f'-{int(time.time() * 1000) % 1000:03d}'
    try:
        slug = urllib.parse.urlparse(referer).path.rstrip('/').split('/')[-1]
    except Exception:
        slug = 'video-r7'
    slug = re.sub(r'[^A-Za-z0-9._-]+', '-', slug).strip('-_.')[:90] or 'video-r7'
    output_mp4 = core.VIDEOS_DIR / f'{slug}_{stamp}.mp4'
    output_ts = core.VIDEOS_DIR / f'{slug}_{stamp}.ts'

    try:
        parsed = urllib.parse.urlparse(referer)
        origin = f'{parsed.scheme}://{parsed.netloc}' if parsed.scheme and parsed.netloc else 'https://www.r7.com'
    except Exception:
        origin = 'https://www.r7.com'

    header_blob = (
        f'Referer: {referer}\r\n'
        f'Origin: {origin}\r\n'
        'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/151.0.0.0 Safari/537.36\r\n'
    )

    env = os.environ.copy()
    if hasattr(core, 'subprocess_environment'):
        try:
            env = core.subprocess_environment(proxy_url)
        except Exception:
            env = os.environ.copy()
    if proxy_url:
        env['http_proxy'] = proxy_url
        env['https_proxy'] = proxy_url

    base_cmd = [
        str(core.FFMPEG_EXE), '-y', '-hide_banner', '-loglevel', 'warning',
        '-rw_timeout', '30000000',
        '-reconnect', '1', '-reconnect_streamed', '1', '-reconnect_delay_max', '5',
        '-headers', header_blob,
        '-i', manifest_url,
        '-map', '0:v:0?', '-map', '0:a:0?',
        '-c', 'copy',
    ]

    flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0) if os.name == 'nt' else 0

    def run_ffmpeg(output, extra):
        cmd = base_cmd + extra + [str(output)]
        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding='utf-8', errors='replace',
            creationflags=flags, env=env,
        )
        self._process = process
        while process.poll() is None:
            if self._cancel_requested:
                try:
                    process.terminate()
                except Exception:
                    pass
                return False, 'Download cancelado'
            time.sleep(0.25)
        _stdout, stderr = process.communicate()
        if process.returncode == 0 and output.exists() and output.stat().st_size > 1024:
            return True, ''
        return False, (stderr or 'FFmpeg não conseguiu concluir o HLS/TS.')[-3500:]

    self.message.emit('R7: baixando playlist HLS e juntando segmentos TS com FFmpeg...')
    self.progress.emit(5)
    ok, err = run_ffmpeg(output_mp4, ['-bsf:a', 'aac_adtstoasc', '-movflags', '+faststart'])
    if ok:
        self.progress.emit(95)
        return True, str(output_mp4), ''
    output_mp4.unlink(missing_ok=True)

    # Se o remux direto para MP4 não for aceito, preserva o transporte TS.
    self.message.emit('R7: MP4 direto não aceito; salvando fluxo MPEG-TS...')
    ok, err2 = run_ffmpeg(output_ts, ['-f', 'mpegts'])
    if ok:
        self.progress.emit(95)
        return True, str(output_ts), ''
    output_ts.unlink(missing_ok=True)
    return False, '', err2 or err


def _attempt_v205(self, url, fmt, referer='', label='', extractor_args='', force_ipv4=False):
    ok, final_file, error = _original_r7_attempt(
        self, url, fmt, referer=referer, label=label,
        extractor_args=extractor_args, force_ipv4=force_ipv4,
    )
    if ok or self._cancel_requested:
        return ok, final_file, error

    page_ref = referer or getattr(self, 'url', '')
    if v203._is_r7_url(page_ref) and '.m3u8' in str(url).lower():
        return _ffmpeg_hls_attempt(self, url, page_ref, getattr(self, 'proxy_url', '') or '')
    return ok, final_file, error


def analyze_video_v205(self):
    raw = self.url_edit.text().strip()
    clean = _clean_r7_url(raw)
    if clean != raw:
        self.url_edit.setText(clean)
        self.download_status.setText('R7: URL duplicada corrigida automaticamente. Iniciando análise...')
    return _original_analyze_video(self)


v203._resolve_r7_candidates = _resolve_r7_candidates_v205
v203.R7DownloadWorker._attempt = _attempt_v205
core.MainWindow.analyze_video = analyze_video_v205

core.APP_VERSION = APP_VERSION
v203.APP_VERSION = APP_VERSION
v203.SIDEBAR_VERSION = SIDEBAR_VERSION
v204.APP_VERSION = APP_VERSION
v204.SIDEBAR_VERSION = SIDEBAR_VERSION


def main():
    core.APP_VERSION = APP_VERSION
    v203.APP_VERSION = APP_VERSION
    v203.SIDEBAR_VERSION = SIDEBAR_VERSION
    v204.APP_VERSION = APP_VERSION
    v204.SIDEBAR_VERSION = SIDEBAR_VERSION
    return v204.main()


if __name__ == '__main__':
    main()
