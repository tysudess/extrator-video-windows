import json
import os
import subprocess
import urllib.error
import urllib.request
import uuid

from PySide6.QtCore import QThread, QTimer, QUrl, Signal
from PySide6.QtWidgets import QMessageBox

import refined_layout_v211 as v211

APP_VERSION = 'Windows Portable v2.0.12 — Globoplay GLBID Direto + Cookie Fix + Download Direto'
SIDEBAR_VERSION = 'v2.0.12  •  GLOBOPLAY GLBID DIRETO'

core = v211.core
v210 = v211.v210
v209 = v211.v209
v208 = v211.v208
v207 = v211.v207
v202 = v211.v202
v201 = v211.v201


def _cookie_name_value(cookie):
    try:
        name_raw, value_raw = v210._cookie_bytes(cookie)
        return (
            name_raw.decode('utf-8', 'replace'),
            value_raw.decode('utf-8', 'replace'),
        )
    except Exception:
        return '', ''


def _cookie_expiry(cookie):
    try:
        dt = cookie.expirationDate()
        if dt.isValid():
            return max(0, int(dt.toSecsSinceEpoch()))
    except Exception:
        pass
    return 0


def _select_glbid_cookie(cookies):
    candidates = []
    for index, cookie in enumerate(list(cookies or [])):
        try:
            name, value = _cookie_name_value(cookie)
            if name.upper() != 'GLBID' or not value:
                continue
            domain = str(cookie.domain() or '').strip().lower()
            path = str(cookie.path() or '/')
            # O token pode chegar por subdomínios da Globo. Para a API de playback
            # interessa o valor GLBID; a preferência é o cookie raiz .globo.com.
            domain_score = 3 if domain in ('.globo.com', 'globo.com') else (
                2 if 'globo.com' in domain else 1 if 'globo' in domain else 0
            )
            candidates.append((
                domain_score,
                1 if path == '/' else 0,
                _cookie_expiry(cookie),
                index,
                cookie,
            ))
        except Exception:
            continue
    if not candidates:
        return None
    return max(candidates, key=lambda item: item[:4])[-1]


def _glbid_from_cookie_jar(raw):
    """Lê GLBID de um cookie jar Netscape, inclusive linhas #HttpOnly_."""
    text = bytes(raw or b'').decode('utf-8', 'ignore')
    values = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith('#') and not stripped.startswith('#HttpOnly_'):
            continue
        parts = stripped.split('\t')
        if len(parts) < 7:
            continue
        name = parts[5].strip()
        value = parts[6].strip()
        if name.upper() == 'GLBID' and value:
            values.append(value)
    return values[-1] if values else ''


def _glbid_line(cookie):
    name, value = _cookie_name_value(cookie)
    if name.upper() != 'GLBID' or not value:
        raise RuntimeError('Cookie GLBID inválido.')
    secure = 'TRUE' if bool(cookie.isSecure()) else 'FALSE'
    domain = '#HttpOnly_.globo.com' if bool(cookie.isHttpOnly()) else '.globo.com'
    return '\t'.join([
        domain,
        'TRUE',
        '/',
        secure,
        str(_cookie_expiry(cookie)),
        'GLBID',
        value,
    ])


def _cookie_jar_with_preferred_glbid(cookies):
    cookies = list(cookies or [])
    glbid_cookie = _select_glbid_cookie(cookies)
    if glbid_cookie is None:
        raise RuntimeError(
            'A conta aparece conectada, mas o cookie de autorização GLBID não foi encontrado. '
            'O aplicativo vai abrir o vídeo dentro do navegador interno para atualizar a sessão.'
        )

    try:
        raw, count = v210._cookie_jar_from_qt(cookies)
        lines = raw.decode('utf-8', 'replace').splitlines()
    except Exception:
        lines = [
            '# Netscape HTTP Cookie File',
            '# Gerado pelo Extrator de Videos - Globoplay GLBID Direto',
            '',
        ]
        count = 0

    filtered = []
    removed_glbid = 0
    for line in lines:
        stripped = line.strip()
        if not stripped:
            filtered.append(line)
            continue
        parts = stripped.split('\t')
        if len(parts) >= 7 and parts[5].strip().upper() == 'GLBID':
            removed_glbid += 1
            continue
        filtered.append(line)

    filtered.append(_glbid_line(glbid_cookie))
    filtered.append('')
    raw = '\n'.join(filtered).encode('utf-8')
    if not _glbid_from_cookie_jar(raw):
        raise RuntimeError('Falha interna ao normalizar o cookie GLBID.')
    return raw, max(1, count - removed_glbid + 1)


def _build_opener(proxy_url=''):
    handlers = []
    proxy = str(proxy_url or '').strip()
    if proxy:
        handlers.append(urllib.request.ProxyHandler({'http': proxy, 'https': proxy}))
    return urllib.request.build_opener(*handlers)


def _globo_playback_payload(video_id, glbid):
    return {
        'player_type': 'mirakulo_8k_hdr',
        'video_id': str(video_id),
        'quality': 'max',
        'content_protection': 'widevine',
        'vsid': str(uuid.uuid4()),
        'consumption': 'streaming',
        'capabilities': {'low_latency': True},
        'tz': '-03:00',
        'Authorization': f'Bearer {glbid}',
        'version': 1,
    }


def _request_globo_playback(video_id, glbid, proxy_url=''):
    if not video_id:
        raise RuntimeError('Globoplay: não foi possível identificar o ID do vídeo.')
    if not glbid:
        raise RuntimeError('Globoplay: sessão GLBID ausente. Faça o login interno novamente.')

    body = json.dumps(_globo_playback_payload(video_id, glbid)).encode('utf-8')
    request = urllib.request.Request(
        'https://playback.video.globo.com/v4/video-session',
        data=body,
        method='POST',
        headers={
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        },
    )
    try:
        with _build_opener(proxy_url).open(request, timeout=35) as response:
            data = json.loads(response.read().decode('utf-8', 'replace'))
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            raise RuntimeError(
                f'Globoplay: a sessão GLBID foi recusada pelo servidor (HTTP {exc.code}). '
                'Abra o Login Globoplay, deixe o vídeo carregar dentro da janela e salve a sessão novamente.'
            ) from exc
        raise RuntimeError(f'Globoplay: erro HTTP {exc.code} ao consultar a sessão de reprodução.') from exc
    except Exception as exc:
        raise RuntimeError(f'Globoplay: falha ao consultar a sessão de reprodução: {exc}') from exc

    resource = data.get('resource') or {}
    if resource.get('drm_protection_enabled') is True:
        raise RuntimeError(
            'INDISPONÍVEL: este vídeo está protegido por DRM. O aplicativo não tenta contornar essa proteção.'
        )

    sources = data.get('sources') or []
    source_url = ''
    for source in sources:
        if isinstance(source, dict) and source.get('url'):
            source_url = str(source.get('url')).strip()
            if source_url:
                break
    if not source_url:
        raise RuntimeError('Globoplay: a sessão foi aceita, mas nenhum manifesto de vídeo foi retornado.')
    return source_url


def _probe_manifest(source_url, original_url, proxy_url=''):
    cmd = [
        str(core.YTDLP_EXE),
        '--no-playlist',
        '--dump-single-json',
        '--skip-download',
        '--socket-timeout', '30',
        '--retries', '5',
        '--fragment-retries', '5',
        '--ffmpeg-location', str(core.BIN_DIR),
    ]
    if core.DENO_EXE.exists():
        cmd += ['--js-runtimes', f'deno:{core.DENO_EXE}']
    if proxy_url:
        cmd += ['--proxy', proxy_url]
    cmd += ['--referer', original_url, source_url]

    flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0) if os.name == 'nt' else 0
    kwargs = dict(
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace',
        creationflags=flags,
        timeout=120,
    )
    if hasattr(core, 'subprocess_environment'):
        kwargs['env'] = core.subprocess_environment(proxy_url)
    result = subprocess.run(cmd, **kwargs)
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or 'Falha ao ler o manifesto do Globoplay.')[-3500:])
    try:
        return json.loads(result.stdout)
    except Exception as exc:
        raise RuntimeError(f'Globoplay: resposta inválida ao ler o manifesto: {exc}') from exc


class GloboplayDirectProbeWorker212(QThread):
    done = Signal(dict)
    failed = Signal(str)

    def __init__(self, url, proxy_url=''):
        super().__init__()
        self.url = str(url or '').strip()
        self.proxy_url = str(proxy_url or '')

    def run(self):
        try:
            video_id = v210._extract_globo_id(self.url)
            if not video_id:
                raise RuntimeError('Globoplay: não foi possível identificar o ID do vídeo no link informado.')

            raw = v202._load_secure_session()
            glbid = _glbid_from_cookie_jar(raw)
            if not glbid:
                raise RuntimeError(
                    'Globoplay: a sessão salva não contém o GLBID necessário para autorização do vídeo. '
                    'Abra o Login Globoplay e salve a sessão novamente.'
                )

            source_url = _request_globo_playback(video_id, glbid, self.proxy_url)
            data = _probe_manifest(source_url, self.url, self.proxy_url)
            payload = v207._analysis_payload(data, self.url, source_url)
            payload['globoplay_resolved_url'] = source_url
            payload['globoplay_auth_mode'] = 'GLBID direto'
            self.done.emit(payload)
        except Exception as exc:
            self.failed.emit(str(exc))


class GloboplayLoginDialog212(v211.GloboplayLoginDialog211):
    def __init__(self, parent=None, test_url='', proxy_url=''):
        super().__init__(parent, test_url, proxy_url)
        self._glbid_refresh_started = False
        try:
            self.profile.cookieStore().cookieRemoved.connect(self._cookie_removed)
        except Exception:
            pass

    def _cookie_removed(self, cookie):
        try:
            name_raw, _ = v210._cookie_bytes(cookie)
            key = (
                str(cookie.domain() or ''),
                str(cookie.path() or '/'),
                bytes(name_raw),
            )
            self.cookies.pop(key, None)
        except Exception:
            pass

    def _save_session(self):
        self.btn_save.setEnabled(False)
        self.status.setText(
            f'Status: atualizando autorização Globoplay… ({len(self.cookies)} cookies observados)'
        )
        self._cookie_export_attempt = 0
        self._glbid_refresh_started = False
        try:
            self.profile.cookieStore().loadAllCookies()
        except Exception:
            pass
        QTimer.singleShot(400, self._finish_export_when_ready)

    def _finish_export_when_ready(self):
        self._cookie_export_attempt = int(getattr(self, '_cookie_export_attempt', 0)) + 1
        glbid_cookie = _select_glbid_cookie(list(self.cookies.values()))

        if glbid_cookie is None:
            # A conta pode aparecer conectada por outros cookies. Carregar o vídeo alvo
            # força o fluxo normal do Globoplay a atualizar a autorização de playback.
            if not self._glbid_refresh_started and self.test_url:
                self._glbid_refresh_started = True
                self.status.setText(
                    'Status: conta conectada; abrindo o vídeo para atualizar a autorização GLBID…'
                )
                self.view.setUrl(QUrl(self.test_url))
                QTimer.singleShot(2800, self._finish_export_when_ready)
                return
            if self._cookie_export_attempt < 12:
                try:
                    self.profile.cookieStore().loadAllCookies()
                except Exception:
                    pass
                self.status.setText(
                    f'Status: aguardando GLBID da sessão… tentativa {self._cookie_export_attempt}/12'
                )
                QTimer.singleShot(700, self._finish_export_when_ready)
                return
            self.btn_save.setEnabled(True)
            self.status.setText('Status: login visível, mas autorização GLBID não foi recebida.')
            QMessageBox.warning(
                self,
                core.APP_NAME,
                'A conta está conectada, mas o Globoplay não entregou o cookie GLBID necessário para o playback.\n\n'
                'Deixe o vídeo abrir nesta janela por alguns segundos e clique novamente em SALVAR E VALIDAR SESSÃO.'
            )
            return

        try:
            raw, count = _cookie_jar_with_preferred_glbid(list(self.cookies.values()))
            v202._save_secure_session(raw)
            v202._write_runtime_cookie_file()
            self.status.setText(
                f'Status: GLBID detectado; {count} cookies salvos. Validando diretamente com o Globoplay…'
            )
        except Exception as exc:
            self.btn_save.setEnabled(True)
            self.status.setText('Status: não foi possível salvar a sessão GLBID.')
            QMessageBox.warning(self, core.APP_NAME, str(exc))
            return

        self.validation_worker = GloboplayDirectProbeWorker212(self.test_url, self.proxy_url)

        def validated(_payload):
            self.btn_save.setEnabled(True)
            self.status.setText('Status: SESSÃO GLBID VALIDADA E SALVA. Download direto liberado.')
            QMessageBox.information(
                self,
                core.APP_NAME,
                'Login do Globoplay validado com sucesso.\n\nA autorização GLBID foi aceita pelo servidor e a sessão ficou salva neste Windows.'
            )
            self.accept()

        def validation_failed(message):
            self.btn_save.setEnabled(True)
            self.status.setText('Status: GLBID capturado, mas a autorização ainda foi recusada.')
            QMessageBox.warning(
                self,
                core.APP_NAME,
                'A sessão foi capturada, mas a validação direta do Globoplay falhou.\n\n' + str(message)
            )

        self.validation_worker.done.connect(validated)
        self.validation_worker.failed.connect(validation_failed)
        self.validation_worker.start()


# Substitui apenas a camada Globoplay da v2.0.11.
# A tela de download, R7, YouTube, Editor e timeline permanecem no código aprovado.
v210.GloboplayProbeWorker210 = GloboplayDirectProbeWorker212
v210.GloboplayLoginDialog = GloboplayLoginDialog212

core.APP_VERSION = APP_VERSION
v211.APP_VERSION = APP_VERSION
v211.SIDEBAR_VERSION = SIDEBAR_VERSION
v210.APP_VERSION = APP_VERSION
v210.SIDEBAR_VERSION = SIDEBAR_VERSION
v209.APP_VERSION = APP_VERSION
v209.SIDEBAR_VERSION = SIDEBAR_VERSION


def main():
    core.APP_VERSION = APP_VERSION
    v211.APP_VERSION = APP_VERSION
    v211.SIDEBAR_VERSION = SIDEBAR_VERSION
    v210.APP_VERSION = APP_VERSION
    v210.SIDEBAR_VERSION = SIDEBAR_VERSION
    v209.APP_VERSION = APP_VERSION
    v209.SIDEBAR_VERSION = SIDEBAR_VERSION
    return v211.main()


if __name__ == '__main__':
    main()
