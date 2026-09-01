import urllib.parse

from PySide6.QtNetwork import QNetworkProxy

import refined_layout_v300 as v300

APP_VERSION = 'Windows Portable v3.0.1 — Globoplay Proxy Login Fix + Timeline Undo'
SIDEBAR_VERSION = 'v3.0.1  •  PROXY LOGIN FIX'

core = v300.core
v214 = v300.v214


def _proxy_from_url(proxy_url):
    """Converte o proxy já montado pelo Extrator para QNetworkProxy/Qt WebEngine."""
    raw = str(proxy_url or '').strip()
    if not raw:
        return None
    if '://' not in raw:
        raw = 'http://' + raw

    parsed = urllib.parse.urlsplit(raw)
    host = parsed.hostname or ''
    if not host:
        raise ValueError('Servidor do proxy inválido.')

    scheme = (parsed.scheme or 'http').lower()
    if scheme in ('socks5', 'socks5h'):
        proxy_type = QNetworkProxy.ProxyType.Socks5Proxy
        default_port = 1080
    else:
        # HTTPS proxy também usa o tipo HTTP: o Chromium cria o túnel HTTPS pelo proxy.
        proxy_type = QNetworkProxy.ProxyType.HttpProxy
        default_port = 8080

    port = int(parsed.port or default_port)
    user = urllib.parse.unquote(parsed.username or '')
    password = urllib.parse.unquote(parsed.password or '')
    return QNetworkProxy(proxy_type, host, port, user, password)


def _proxy_public_label(proxy):
    if proxy is None:
        return 'conexão direta'
    try:
        return f'{proxy.hostName()}:{proxy.port()}'
    except Exception:
        return 'proxy configurado'


class ProxyAwareGloboplayLoginDialog(v214.GloboplayAndroidLoginDialog):
    """Mesmo login Android Flow, mas o WebEngine herda o proxy do Extrator."""

    def __init__(self, parent=None, test_url='', proxy_url=''):
        self._previous_application_proxy = QNetworkProxy.applicationProxy()
        self._proxy_restored = False
        self._active_web_proxy = None

        if str(proxy_url or '').strip():
            self._active_web_proxy = _proxy_from_url(proxy_url)
            QNetworkProxy.setApplicationProxy(self._active_web_proxy)

        try:
            # O QWebEngineProfile é criado dentro do construtor da classe-base.
            # O applicationProxy precisa estar ativo ANTES desse ponto para ser
            # encaminhado ao Chromium/Qt WebEngine.
            super().__init__(parent, test_url, proxy_url)
            self.proxy_url = str(proxy_url or '').strip()
            if self._active_web_proxy is not None:
                self.status.setText(
                    'Status: proxy ativo no navegador interno ('
                    + _proxy_public_label(self._active_web_proxy)
                    + '). Faça o login na página principal do Globoplay.'
                )
        except Exception:
            self._restore_application_proxy()
            raise

    def _restore_application_proxy(self):
        if self._proxy_restored:
            return
        self._proxy_restored = True
        try:
            QNetworkProxy.setApplicationProxy(self._previous_application_proxy)
        except Exception:
            pass

    def done(self, result):
        self._restore_application_proxy()
        return super().done(result)

    def closeEvent(self, event):
        self._restore_application_proxy()
        return super().closeEvent(event)


# A janela criada na página Configurações resolve este nome em tempo de execução.
# Substituímos apenas a implementação do login; o Android Flow de cookies e o
# motor de download da v3.0 permanecem intactos.
v214.v210.GloboplayLoginDialog = ProxyAwareGloboplayLoginDialog
v214.GloboplayAndroidLoginDialog = ProxyAwareGloboplayLoginDialog

core.APP_VERSION = APP_VERSION
v300.APP_VERSION = APP_VERSION
v300.SIDEBAR_VERSION = SIDEBAR_VERSION
v214.APP_VERSION = APP_VERSION
v214.SIDEBAR_VERSION = SIDEBAR_VERSION


def main():
    core.APP_VERSION = APP_VERSION
    v300.APP_VERSION = APP_VERSION
    v300.SIDEBAR_VERSION = SIDEBAR_VERSION
    v214.APP_VERSION = APP_VERSION
    v214.SIDEBAR_VERSION = SIDEBAR_VERSION
    return v300.main()


if __name__ == '__main__':
    main()
