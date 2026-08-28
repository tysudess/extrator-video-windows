import json
import re
from pathlib import Path

from PySide6.QtCore import QThread, QTimer, QUrl, Signal
from PySide6.QtWebEngineCore import QWebEngineUrlRequestInterceptor
from PySide6.QtWidgets import QMessageBox

import refined_layout_v212 as v212

APP_VERSION = 'Windows Portable v2.0.13 — Globoplay Browser Auth + Download Direto'
SIDEBAR_VERSION = 'v2.0.13  •  GLOBOPLAY BROWSER AUTH'

core = v212.core
v211 = v212.v211
v210 = v212.v210
v209 = v212.v209
v208 = v212.v208
v207 = v212.v207
v202 = v212.v202
v201 = v212.v201

BROWSER_AUTH_BLOB = Path(v202.SESSION_DIR) / 'globoplay-browser-auth.dpapi'
PLAYBACK_ENDPOINT = 'playback.video.globo.com/v4/video-session'


def _normalize_browser_authorization(value):
    text = str(value or '').strip()
    if not text:
        return ''
    if not text.lower().startswith('bearer '):
        return ''
    token = text.split(' ', 1)[1].strip()
    if len(token) < 12:
        return ''
    return 'Bearer ' + token


def _save_browser_authorization(value):
    auth = _normalize_browser_authorization(value)
    if not auth:
        raise RuntimeError('A autorização capturada do player Globoplay é inválida.')
    BROWSER_AUTH_BLOB.parent.mkdir(parents=True, exist_ok=True)
    protected = v202._protect_bytes(auth.encode('utf-8'))
    tmp = BROWSER_AUTH_BLOB.with_suffix('.tmp')
    tmp.write_bytes(protected)
    tmp.replace(BROWSER_AUTH_BLOB)


def _load_browser_authorization():
    if not BROWSER_AUTH_BLOB.exists():
        return ''
    try:
        raw = v202._unprotect_bytes(BROWSER_AUTH_BLOB.read_bytes())
        return _normalize_browser_authorization(raw.decode('utf-8', 'ignore'))
    except Exception:
        return ''


def _delete_browser_authorization():
    try:
        BROWSER_AUTH_BLOB.unlink(missing_ok=True)
    except Exception:
        pass


_original_delete_secure_session = v202._delete_secure_session
_original_secure_session_exists = v202._secure_session_exists


def _delete_secure_session_v213():
    _delete_browser_authorization()
    return _original_delete_secure_session()


def _secure_session_exists_v213():
    return bool(_load_browser_authorization()) or bool(_original_secure_session_exists())


v202._delete_secure_session = _delete_secure_session_v213
v202._secure_session_exists = _secure_session_exists_v213


def _header_text(headers, wanted):
    target = str(wanted or '').lower()
    try:
        items = headers.items()
    except Exception:
        items = []
    for key, value in items:
        try:
            key_text = bytes(key).decode('utf-8', 'ignore').lower()
        except Exception:
            key_text = str(key or '').lower()
        if key_text != target:
            continue
        try:
            return bytes(value).decode('utf-8', 'ignore')
        except Exception:
            return str(value or '')
    return ''


def _request_body_bytes(info):
    try:
        body = info.requestBody()
    except Exception:
        return b''
    if body is None:
        return b''
    # peek() não avança a posição do QIODevice e, portanto, não consome o POST
    # que o Chromium ainda precisa enviar ao Globoplay.
    try:
        return bytes(body.peek(2_000_000))
    except Exception:
        return b''


def _authorization_from_request_info(info):
    try:
        url = info.requestUrl().toString()
    except Exception:
        url = ''
    if PLAYBACK_ENDPOINT not in str(url or '').lower():
        return ''

    # O player atual envia Authorization dentro do JSON do POST de video-session.
    raw = _request_body_bytes(info)
    if raw:
        text = raw.decode('utf-8', 'ignore')
        try:
            payload = json.loads(text)
        except Exception:
            payload = None
        if isinstance(payload, dict):
            auth = _normalize_browser_authorization(
                payload.get('Authorization') or payload.get('authorization')
            )
            if auth:
                return auth
        match = re.search(
            r'["\']authorization["\']\s*:\s*["\'](Bearer\s+[^"\']+)["\']',
            text,
            re.I,
        )
        if match:
            auth = _normalize_browser_authorization(match.group(1))
            if auth:
                return auth

    # Compatibilidade caso o front-end passe a mandar o token no cabeçalho HTTP.
    try:
        headers = info.httpHeaders()
    except Exception:
        headers = {}
    auth = _normalize_browser_authorization(_header_text(headers, 'authorization'))
    if auth:
        return auth

    # Último fallback: se GLBID estiver apenas no cabeçalho Cookie da requisição,
    # converte para o mesmo Bearer esperado pelo endpoint de playback.
    cookie = _header_text(headers, 'cookie')
    if cookie:
        match = re.search(r'(?:^|;\s*)GLBID=([^;]+)', cookie, re.I)
        if match:
            return _normalize_browser_authorization('Bearer ' + match.group(1).strip())
    return ''


class GloboplayPlaybackInterceptor(QWebEngineUrlRequestInterceptor):
    authorizationCaptured = Signal(str)
    playbackRequestSeen = Signal()

    def interceptRequest(self, info):
        try:
            url = info.requestUrl().toString()
        except Exception:
            url = ''
        if PLAYBACK_ENDPOINT not in str(url or '').lower():
            return
        self.playbackRequestSeen.emit()
        auth = _authorization_from_request_info(info)
        if auth:
            self.authorizationCaptured.emit(auth)


def _request_globo_playback_with_authorization(video_id, authorization, proxy_url=''):
    auth = _normalize_browser_authorization(authorization)
    if not auth:
        raise RuntimeError('Globoplay: autorização do player ausente ou inválida.')
    # A rotina v2.0.12 já faz a chamada oficial de video-session e valida DRM.
    token = auth.split(' ', 1)[1]
    return v212._request_globo_playback(video_id, token, proxy_url)


class GloboplayBrowserAuthProbeWorker213(QThread):
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

            authorization = _load_browser_authorization()
            if not authorization:
                # Compatibilidade com a v2.0.12 caso um GLBID tradicional exista.
                glbid = v212._glbid_from_cookie_jar(v202._load_secure_session())
                if glbid:
                    authorization = _normalize_browser_authorization('Bearer ' + glbid)
            if not authorization:
                raise RuntimeError(
                    'Globoplay: a autorização real do player ainda não foi capturada. '
                    'Abra o Login Globoplay dentro do aplicativo e deixe o vídeo carregar/reproduzir por alguns segundos.'
                )

            source_url = _request_globo_playback_with_authorization(
                video_id, authorization, self.proxy_url
            )
            data = v212._probe_manifest(source_url, self.url, self.proxy_url)
            payload = v207._analysis_payload(data, self.url, source_url)
            payload['globoplay_resolved_url'] = source_url
            payload['globoplay_auth_mode'] = 'autorização real do navegador interno'
            self.done.emit(payload)
        except Exception as exc:
            self.failed.emit(str(exc))


class GloboplayLoginDialog213(v212.GloboplayLoginDialog212):
    def __init__(self, parent=None, test_url='', proxy_url=''):
        super().__init__(parent, test_url, proxy_url)
        self._browser_authorization = _load_browser_authorization()
        self._playback_request_seen = False
        self._browser_wait_attempt = 0
        self._validation_running = False

        self.playback_interceptor = GloboplayPlaybackInterceptor(self)
        self.playback_interceptor.authorizationCaptured.connect(self._authorization_captured)
        self.playback_interceptor.playbackRequestSeen.connect(self._playback_seen)
        try:
            self.page.setUrlRequestInterceptor(self.playback_interceptor)
        except Exception:
            try:
                self.profile.setUrlRequestInterceptor(self.playback_interceptor)
            except Exception:
                pass

        # Recarrega o vídeo somente depois que o interceptor já está instalado.
        if self.test_url:
            QTimer.singleShot(250, lambda: self.view.setUrl(QUrl(self.test_url)))

    def _playback_seen(self):
        self._playback_request_seen = True
        if not self._browser_authorization:
            self.status.setText('Status: pedido de playback detectado; aguardando autorização do player…')

    def _authorization_captured(self, authorization):
        auth = _normalize_browser_authorization(authorization)
        if not auth:
            return
        self._browser_authorization = auth
        try:
            _save_browser_authorization(auth)
        except Exception:
            pass
        self.status.setText('Status: autorização real do player capturada. Pronta para validação.')

    def _try_start_video(self):
        # O play mudo costuma ser permitido pelo Chromium sem gesto adicional e serve
        # apenas para fazer o próprio player emitir sua requisição normal de playback.
        script = """
        (() => {
          const v = document.querySelector('video');
          if (!v) return false;
          try { v.muted = true; } catch (e) {}
          try { const p = v.play(); if (p && p.catch) p.catch(() => {}); } catch (e) {}
          return true;
        })();
        """
        try:
            self.page.runJavaScript(script)
        except Exception:
            pass

    def _save_session(self):
        self.btn_save.setEnabled(False)
        self._browser_wait_attempt = 0
        self._validation_running = False

        if self._browser_authorization or _load_browser_authorization():
            self._validate_browser_authorization()
            return

        self.status.setText(
            'Status: abrindo o vídeo e aguardando a autorização usada pelo próprio player…'
        )
        if self.test_url:
            self.view.setUrl(QUrl(self.test_url))
        QTimer.singleShot(1200, self._wait_for_browser_authorization)

    def _wait_for_browser_authorization(self):
        if self._browser_authorization or _load_browser_authorization():
            self._validate_browser_authorization()
            return

        self._browser_wait_attempt += 1
        if self._browser_wait_attempt in (2, 5, 8):
            self._try_start_video()

        if self._browser_wait_attempt < 18:
            detail = 'pedido de playback já detectado' if self._playback_request_seen else 'aguardando o player iniciar'
            self.status.setText(
                f'Status: capturando autorização do navegador… {detail} '
                f'({self._browser_wait_attempt}/18)'
            )
            QTimer.singleShot(800, self._wait_for_browser_authorization)
            return

        self.btn_save.setEnabled(True)
        self.status.setText('Status: login ativo, mas a autorização do playback ainda não apareceu na rede.')
        QMessageBox.warning(
            self,
            core.APP_NAME,
            'A conta está conectada, mas o player ainda não enviou a autorização de playback.\n\n'
            'Clique em OK, pressione PLAY no vídeo dentro desta janela e depois clique novamente em '
            'SALVAR E VALIDAR SESSÃO. O aplicativo agora captura a requisição real do player, sem depender do cookie GLBID.'
        )

    def _validate_browser_authorization(self):
        if self._validation_running:
            return
        authorization = self._browser_authorization or _load_browser_authorization()
        if not authorization:
            self.btn_save.setEnabled(True)
            self.status.setText('Status: autorização do player ainda não capturada.')
            return

        try:
            _save_browser_authorization(authorization)
        except Exception as exc:
            self.btn_save.setEnabled(True)
            QMessageBox.warning(self, core.APP_NAME, str(exc))
            return

        # Mantém também os cookies normais da conta para que o navegador interno
        # continue logado entre execuções. Não exige GLBID.
        try:
            raw, _count = v210._cookie_jar_from_qt(list(self.cookies.values()))
            v202._save_secure_session(raw)
            v202._write_runtime_cookie_file()
        except Exception:
            pass

        self._validation_running = True
        self.status.setText('Status: autorização do player capturada; validando com o Globoplay…')
        self.validation_worker = GloboplayBrowserAuthProbeWorker213(self.test_url, self.proxy_url)

        def validated(_payload):
            self._validation_running = False
            self.btn_save.setEnabled(True)
            self.status.setText('Status: SESSÃO DO PLAYER VALIDADA E SALVA. Download direto liberado.')
            QMessageBox.information(
                self,
                core.APP_NAME,
                'Login do Globoplay validado com sucesso.\n\n'
                'O Extrator capturou a autorização que o próprio player interno usou e salvou essa sessão protegida neste Windows.'
            )
            self.accept()

        def validation_failed(message):
            self._validation_running = False
            self.btn_save.setEnabled(True)
            text = str(message or '')
            if '401' in text or '403' in text or 'recusada' in text.lower():
                _delete_browser_authorization()
                self._browser_authorization = ''
            self.status.setText('Status: autorização capturada, mas a validação não foi concluída.')
            QMessageBox.warning(
                self,
                core.APP_NAME,
                'A autorização do player foi capturada, mas o teste do Globoplay falhou.\n\n' + text
            )

        self.validation_worker.done.connect(validated)
        self.validation_worker.failed.connect(validation_failed)
        self.validation_worker.start()


# Substitui apenas a camada de autenticação do Globoplay. Todo o restante permanece
# no fluxo aprovado das versões anteriores.
v210.GloboplayProbeWorker210 = GloboplayBrowserAuthProbeWorker213
v210.GloboplayLoginDialog = GloboplayLoginDialog213

core.APP_VERSION = APP_VERSION
v212.APP_VERSION = APP_VERSION
v212.SIDEBAR_VERSION = SIDEBAR_VERSION
v211.APP_VERSION = APP_VERSION
v211.SIDEBAR_VERSION = SIDEBAR_VERSION
v210.APP_VERSION = APP_VERSION
v210.SIDEBAR_VERSION = SIDEBAR_VERSION
v209.APP_VERSION = APP_VERSION
v209.SIDEBAR_VERSION = SIDEBAR_VERSION


def main():
    core.APP_VERSION = APP_VERSION
    v212.APP_VERSION = APP_VERSION
    v212.SIDEBAR_VERSION = SIDEBAR_VERSION
    v211.APP_VERSION = APP_VERSION
    v211.SIDEBAR_VERSION = SIDEBAR_VERSION
    v210.APP_VERSION = APP_VERSION
    v210.SIDEBAR_VERSION = SIDEBAR_VERSION
    v209.APP_VERSION = APP_VERSION
    v209.SIDEBAR_VERSION = SIDEBAR_VERSION
    return v212.main()


if __name__ == '__main__':
    main()
