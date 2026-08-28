import re
import urllib.request

import refined_layout_v213 as v213

APP_VERSION = 'Windows Portable v2.0.14 — Globoplay Android Flow + Download Direto'
SIDEBAR_VERSION = 'v2.0.14  •  GLOBOPLAY ANDROID FLOW'

core = v213.core
v208 = v213.v208
v202 = v213.v202
v201 = v213.v201

STABLE_YTDLP = core.BIN_DIR / 'yt-dlp-stable.exe'


def _is_globoplay(url):
    return v201._is_globoplay_url(url) or bool(re.match(r'(?i)^globo:\d+$', str(url or '').strip()))


def _globo_id(url):
    m = re.search(r'(?i)(?:/v/|globo:)(\d{7,})', str(url or ''))
    return m.group(1) if m else ''


def _looks_drm(text):
    low = str(text or '').lower()
    return any(k in low for k in ('drm', 'widevine', 'protected by drm', 'copy-protected'))


def _looks_auth(text):
    low = str(text or '').lower()
    return any(k in low for k in (
        'login', 'sign in', 'cookies', 'subscription', 'subscriber', 'assinatura',
        'authentication', 'unauthorized', 'forbidden', 'http error 401', 'http error 403'
    ))


def _hls_selector(fmt):
    m = re.search(r'height<=([0-9]+)', str(fmt or ''))
    if m:
        h = int(m.group(1))
        return f'b[protocol=m3u8_native][height<={h}]/b[protocol=m3u8][height<={h}]/b[protocol=m3u8_native]/b[protocol=m3u8]'
    return 'b[protocol=m3u8_native]/b[protocol=m3u8]'


def _cookie_header_from_jar(raw):
    values = []
    try:
        text = bytes(raw or b'').decode('utf-8', 'ignore')
    except Exception:
        return ''
    for line in text.splitlines():
        s = line.strip()
        if not s or (s.startswith('#') and not s.startswith('#HttpOnly_')):
            continue
        parts = s.split('\t')
        if len(parts) >= 7 and parts[5].strip():
            values.append(f'{parts[5].strip()}={parts[6].strip()}')
    return '; '.join(values)


def _fetch_globoplay_html_android(url, proxy_url='', with_session=False):
    handlers = []
    if proxy_url:
        handlers.append(urllib.request.ProxyHandler({'http': proxy_url, 'https': proxy_url}))
    opener = urllib.request.build_opener(*handlers)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/149.0.0.0 Mobile Safari/537.36',
        'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
        'Accept': 'text/html,application/xhtml+xml,*/*;q=0.8',
    }
    if with_session:
        cookie = _cookie_header_from_jar(v202._load_secure_session())
        if cookie:
            headers['Cookie'] = cookie
    request = urllib.request.Request(url, headers=headers)
    with opener.open(request, timeout=30) as response:
        content_type = str(response.headers.get('Content-Type') or '').lower()
        if content_type and 'text/html' not in content_type:
            return ''
        return response.read().decode('utf-8', 'replace')


class GloboplayAndroidFlowWorker(v208.R7DirectDownloadWorker):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._globo_use_session = False
        self._globo_hls_mode = False

    def _base_cmd(self, fmt, referer='', extractor_args='', force_ipv4=False):
        if not _is_globoplay(self.url):
            return super()._base_cmd(fmt, referer, extractor_args, force_ipv4)

        # Para Globoplay, não usa a camada v2.0.9 de pré-autenticação.
        # Reproduz o Android: yt-dlp direto, IPv4, retries e sessão apenas quando necessária.
        cmd = v201._original_download_base_cmd(
            self, fmt, referer, extractor_args, True
        )
        if STABLE_YTDLP.exists():
            cmd[0] = str(STABLE_YTDLP)
        if '--no-mtime' not in cmd:
            cmd.insert(1, '--no-mtime')
        if '--ignore-config' not in cmd:
            cmd.insert(1, '--ignore-config')

        if self._globo_use_session:
            runtime = v202._write_runtime_cookie_file()
            if runtime:
                cmd += ['--cookies', str(runtime)]

        if self._globo_hls_mode:
            cmd += ['--hls-use-mpegts', '--downloader', 'm3u8:native']
        return cmd

    def _attempt_mode(self, url, fmt, label, referer='', use_session=False, hls=False):
        self._globo_use_session = bool(use_session)
        self._globo_hls_mode = bool(hls)
        try:
            return self._attempt(
                url, fmt, referer=referer, label=label, force_ipv4=True
            )
        finally:
            self._globo_use_session = False
            self._globo_hls_mode = False

    def run(self):
        if not _is_globoplay(self.url):
            return super().run()
        if not core.YTDLP_EXE.exists():
            self.failed.emit('yt-dlp.exe não encontrado na pasta bin.')
            return
        if not core.FFMPEG_EXE.exists():
            self.failed.emit('ffmpeg.exe não encontrado na pasta bin.')
            return

        fmt = self.format_selector or core.FORMATS[self.quality_index]
        hls_fmt = _hls_selector(fmt)
        original_url = self.url
        gid = _globo_id(original_url)
        self.progress.emit(0)

        # 1) Android: link original, SEM exigir login.
        ok, file, last_err = self._attempt_mode(
            original_url, fmt, 'Globoplay: tentativa pública pelo link...', use_session=False
        )
        if ok and self._finish_if_ok(ok, file, last_err):
            return
        if self._cancel_requested:
            self.canceled.emit(); return

        # 2) Android: globo:<ID>, ainda sem login.
        if gid:
            ok, file, last_err = self._attempt_mode(
                f'globo:{gid}', fmt, f'Globoplay: tentativa pública direta {gid}...',
                referer=original_url, use_session=False
            )
            if ok and self._finish_if_ok(ok, file, last_err):
                return
            if self._cancel_requested:
                self.canceled.emit(); return

        if _looks_drm(last_err):
            self._fail_with_diagnostic(last_err)
            return

        has_cookie_session = bool(v202._load_secure_session())

        # 3) Android: HLS/TS público quando a falha não é de login.
        if not _looks_auth(last_err):
            target = f'globo:{gid}' if gid else original_url
            ok, file, last_err = self._attempt_mode(
                target, hls_fmt, 'Globoplay: HLS/TS público...',
                referer=original_url, use_session=False, hls=True
            )
            if ok and self._finish_if_ok(ok, file, last_err):
                return
            if _looks_drm(last_err):
                self._fail_with_diagnostic(last_err); return

            self.message.emit('Globoplay: procurando playlist HLS como no Android...')
            try:
                html = _fetch_globoplay_html_android(original_url, self.proxy_url, False)
                candidates = core.extract_candidates_from_html(html, original_url)
            except Exception:
                candidates = []
            for index, candidate in enumerate([c for c in candidates if '.m3u8' in c.lower()][:15], 1):
                ok, file, last_err = self._attempt_mode(
                    candidate, hls_fmt, f'Globoplay HLS/TS público {index}...',
                    referer=original_url, use_session=False, hls=True
                )
                if ok and self._finish_if_ok(ok, file, last_err):
                    return
                if self._cancel_requested:
                    self.canceled.emit(); return
                if _looks_drm(last_err):
                    self._fail_with_diagnostic(last_err); return

        # 4) Só agora usa sessão salva, se existir. Login deixa de ser obrigatório.
        if has_cookie_session:
            self.message.emit('Globoplay: tentativa pública falhou; testando sessão salva...')
            for target in [original_url] + ([f'globo:{gid}'] if gid else []):
                ok, file, last_err = self._attempt_mode(
                    target, fmt, 'Globoplay: tentativa com sessão salva...',
                    referer=original_url if target != original_url else '', use_session=True
                )
                if ok and self._finish_if_ok(ok, file, last_err):
                    return
                if _looks_drm(last_err):
                    self._fail_with_diagnostic(last_err); return

            target = f'globo:{gid}' if gid else original_url
            ok, file, last_err = self._attempt_mode(
                target, hls_fmt, 'Globoplay: HLS/TS com sessão salva...',
                referer=original_url, use_session=True, hls=True
            )
            if ok and self._finish_if_ok(ok, file, last_err):
                return

        self._fail_with_diagnostic(last_err)


# Remove a pré-validação obrigatória introduzida na v2.0.9.
# A tela continua Download Direto, mas Globoplay volta ao fluxo funcional do Android.
core.DownloadWorker = GloboplayAndroidFlowWorker
core.MainWindow.download_video = v208.direct_download_video

core.APP_VERSION = APP_VERSION
v213.APP_VERSION = APP_VERSION
v213.SIDEBAR_VERSION = SIDEBAR_VERSION


def main():
    core.APP_VERSION = APP_VERSION
    v213.APP_VERSION = APP_VERSION
    v213.SIDEBAR_VERSION = SIDEBAR_VERSION
    return v213.main()


if __name__ == '__main__':
    main()
