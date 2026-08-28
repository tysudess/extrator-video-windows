import re
import time
import urllib.request

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QMessageBox, QPushButton, QVBoxLayout

import refined_layout_v213 as v213

APP_VERSION = 'Windows Portable v2.0.14 — Globoplay Android Flow + Download Direto'
SIDEBAR_VERSION = 'v2.0.14  •  GLOBOPLAY ANDROID FLOW'

core = v213.core
v210 = v213.v210
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


def _qt_cookie_name_value(cookie):
    try:
        name_raw, value_raw = v210._cookie_bytes(cookie)
        name = name_raw.decode('utf-8', 'replace').replace('\t', '').replace('\r', '').replace('\n', '').strip()
        value = value_raw.decode('utf-8', 'replace').replace('\t', '').replace('\r', '').replace('\n', '').strip()
        return name, value
    except Exception:
        return '', ''


def _android_cookie_priority(cookie):
    domain = str(cookie.domain() or '').lower().lstrip('.')
    if domain == 'globoplay.globo.com' or domain.endswith('.globoplay.globo.com'):
        return 0
    if domain == 'play.globo.com' or domain.endswith('.play.globo.com'):
        return 1
    if domain == 'login.globo.com' or domain.endswith('.login.globo.com'):
        return 2
    if domain == 'globo.com' or domain.endswith('.globo.com'):
        return 3
    return 99


def _android_cookie_jar_from_qt(cookies):
    """Replica o GloboplayLoginActivity.java da Android v1.9.17.

    O Android coleta os cookies das páginas Globo e grava todos como .globo.com,
    TRUE, /, TRUE, com validade artificial de 30 dias. A senha nunca é salva.
    """
    merged = {}
    ordered = sorted(list(cookies or []), key=_android_cookie_priority)
    for cookie in ordered:
        if _android_cookie_priority(cookie) >= 99:
            continue
        name, value = _qt_cookie_name_value(cookie)
        if not name:
            continue
        merged[name] = value

    if not merged:
        raise RuntimeError(
            'Nenhum cookie Globo/Globoplay foi encontrado. Faça o login na página principal e tente salvar novamente.'
        )

    expiry = int(time.time()) + (30 * 24 * 60 * 60)
    lines = ['# Netscape HTTP Cookie File']
    for name, value in merged.items():
        lines.append(
            '\t'.join(['.globo.com', 'TRUE', '/', 'TRUE', str(expiry), name, value])
        )
    return ('\n'.join(lines) + '\n').encode('utf-8'), len(merged)


def _cookie_header_from_jar(raw):
    values = []
    try:
        text = bytes(raw or b'').decode('utf-8', 'ignore')
    except Exception:
        return ''
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith('#'):
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


class GloboplayAndroidLoginDialog(QDialog):
    """Login igual ao Android: página principal -> salvar cookies -> voltar."""

    def __init__(self, parent=None, test_url='', proxy_url=''):
        super().__init__(parent)
        self.cookies = {}
        self.setWindowTitle('Globoplay — Login dentro do Extrator')
        self.resize(1080, 780)

        root = QVBoxLayout(self)
        info = QLabel(
            'Entre normalmente na sua conta pela página principal do Globoplay. '
            'A senha fica somente na página oficial da Globo. Quando terminar, clique em '
            'SALVAR SESSÃO E VOLTAR. Não é necessário abrir vídeo, dar Play, obter GLBID ou validar um vídeo.'
        )
        info.setWordWrap(True)
        root.addWidget(info)

        self.status = QLabel('Status: faça o login na página principal do Globoplay.')
        self.status.setWordWrap(True)
        root.addWidget(self.status)

        v210.PROFILE_ROOT.mkdir(parents=True, exist_ok=True)
        v210.PROFILE_CACHE.mkdir(parents=True, exist_ok=True)
        self.profile = QWebEngineProfile('ExtratorVideosGloboplay', self)
        self.profile.setPersistentStoragePath(str(v210.PROFILE_ROOT))
        self.profile.setCachePath(str(v210.PROFILE_CACHE))
        try:
            self.profile.setPersistentCookiesPolicy(
                QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies
            )
        except Exception:
            pass

        self.view = QWebEngineView(self)
        self.page = QWebEnginePage(self.profile, self.view)
        self.view.setPage(self.page)
        root.addWidget(self.view, 1)

        store = self.profile.cookieStore()
        store.cookieAdded.connect(self._cookie_added)
        store.loadAllCookies()

        actions = QHBoxLayout()
        self.btn_home = QPushButton('ABRIR GLOBOPLAY')
        self.btn_save = QPushButton('SALVAR SESSÃO E VOLTAR')
        self.btn_close = QPushButton('FECHAR')
        actions.addWidget(self.btn_home)
        actions.addWidget(self.btn_save)
        actions.addStretch(1)
        actions.addWidget(self.btn_close)
        root.addLayout(actions)

        self.btn_home.clicked.connect(lambda: self.view.setUrl(QUrl('https://globoplay.globo.com/')))
        self.btn_save.clicked.connect(self._save_session)
        self.btn_close.clicked.connect(self.reject)
        self.view.setUrl(QUrl('https://globoplay.globo.com/'))

    def _cookie_added(self, cookie):
        try:
            name, _value = _qt_cookie_name_value(cookie)
            if not name:
                return
            key = (str(cookie.domain() or ''), str(cookie.path() or '/'), name)
            self.cookies[key] = cookie
        except Exception:
            pass

    def _save_session(self):
        self.btn_save.setEnabled(False)
        self.status.setText('Status: coletando cookies da sessão, como no Android…')
        try:
            self.profile.cookieStore().loadAllCookies()
        except Exception:
            pass
        QTimer.singleShot(1200, self._finish_save)

    def _finish_save(self):
        try:
            raw, count = _android_cookie_jar_from_qt(list(self.cookies.values()))
            # Remove autorização de player antiga; v2.0.14 volta a depender apenas do cookie jar do login.
            try:
                v213._delete_browser_authorization()
            except Exception:
                pass
            v202._save_secure_session(raw)
            v202._write_runtime_cookie_file()
            try:
                self.profile.cookieStore().loadAllCookies()
            except Exception:
                pass
            self.status.setText(f'Status: sessão salva ({count} cookies). Pronta para download.')
            QMessageBox.information(
                self,
                core.APP_NAME,
                'Sessão do Globoplay salva com sucesso.\n\n'
                'Agora é só colar o link, escolher a qualidade e baixar, exatamente como no Android.'
            )
            self.accept()
        except Exception as exc:
            self.btn_save.setEnabled(True)
            self.status.setText('Status: não foi possível salvar a sessão.')
            QMessageBox.warning(self, core.APP_NAME, str(exc))


class GloboplayAndroidFlowWorker(v208.R7DirectDownloadWorker):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._globo_use_session = False
        self._globo_hls_mode = False

    def _base_cmd(self, fmt, referer='', extractor_args='', force_ipv4=False):
        if not _is_globoplay(self.url):
            return super()._base_cmd(fmt, referer, extractor_args, force_ipv4)

        cmd = v201._original_download_base_cmd(self, fmt, referer, extractor_args, True)
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
            return self._attempt(url, fmt, referer=referer, label=label, force_ipv4=True)
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
        has_session = bool(v202._load_secure_session())
        mode_text = 'com sessão salva' if has_session else 'sem sessão salva'
        self.progress.emit(0)

        # Android: se o cookie jar existe, ele é anexado já à PRIMEIRA tentativa.
        ok, file, last_err = self._attempt_mode(
            original_url, fmt, f'Globoplay: tentativa principal {mode_text}…',
            use_session=has_session
        )
        if ok and self._finish_if_ok(ok, file, last_err):
            return
        if self._cancel_requested:
            self.canceled.emit(); return

        # Android: depois tenta globo:<ID>, usando a MESMA sessão salva.
        if gid:
            ok, file, last_err = self._attempt_mode(
                f'globo:{gid}', fmt, f'Globoplay: modo direto {gid} {mode_text}…',
                referer=original_url, use_session=has_session
            )
            if ok and self._finish_if_ok(ok, file, last_err):
                return
            if self._cancel_requested:
                self.canceled.emit(); return

        if _looks_drm(last_err):
            self._fail_with_diagnostic(last_err)
            return

        # Android só evita HLS quando a falha pede login E não há sessão salva.
        if (not _looks_auth(last_err)) or has_session:
            target = f'globo:{gid}' if gid else original_url
            ok, file, last_err = self._attempt_mode(
                target, hls_fmt, f'Globoplay: HLS/TS {mode_text}…',
                referer=original_url, use_session=has_session, hls=True
            )
            if ok and self._finish_if_ok(ok, file, last_err):
                return
            if self._cancel_requested:
                self.canceled.emit(); return
            if _looks_drm(last_err):
                self._fail_with_diagnostic(last_err); return

            self.message.emit('Globoplay: procurando playlist HLS (.m3u8) na página…')
            try:
                html = _fetch_globoplay_html_android(original_url, self.proxy_url, has_session)
                candidates = core.extract_candidates_from_html(html, original_url)
            except Exception:
                candidates = []
            for index, candidate in enumerate([c for c in candidates if '.m3u8' in c.lower()][:15], 1):
                ok, file, last_err = self._attempt_mode(
                    candidate, hls_fmt, f'Globoplay HLS/TS: tentativa {index}…',
                    referer=original_url, use_session=has_session, hls=True
                )
                if ok and self._finish_if_ok(ok, file, last_err):
                    return
                if self._cancel_requested:
                    self.canceled.emit(); return
                if _looks_drm(last_err):
                    self._fail_with_diagnostic(last_err); return

        if (not has_session) and _looks_auth(last_err):
            self._fail_with_diagnostic(
                'Globoplay: este vídeo exige login. Abra Configurações > Globoplay, '
                'faça o login uma vez na página principal e clique em SALVAR SESSÃO E VOLTAR.\n\n'
                + str(last_err or '')
            )
            return
        self._fail_with_diagnostic(last_err)


# Igual ao Android: o status de sessão depende do cookie jar salvo, não de GLBID/player auth.
try:
    v202._secure_session_exists = v213._original_secure_session_exists
except Exception:
    pass

# A janela de Configurações já criada na v2.0.10 passa a abrir o login simples estilo Android.
v210.GloboplayLoginDialog = GloboplayAndroidLoginDialog

# Remove a pré-validação obrigatória introduzida na v2.0.9.
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
