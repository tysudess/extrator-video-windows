import urllib.parse

from PySide6.QtNetwork import QNetworkProxy
from PySide6.QtWidgets import QFrame, QLabel, QWidget

import refined_layout_v214 as v214

APP_VERSION = 'Windows Portable v3.0.1 — Globoplay Proxy Login Fix'
SIDEBAR_VERSION = 'v3.0.1  •  PROXY LOGIN FIX'
EXTRACTOR_ONLY = True

core = v214.core


class _ExtractorOnlyPlaceholder(QWidget):
    """Placeholder leve para manter compatibilidade interna sem expor/carregar o Editor na interface."""

    def __init__(self, videos_dir=None, ffmpeg_exe=None, ffprobe_exe=None, parent=None):
        super().__init__(parent)

    def shutdown(self):
        pass


# A construção histórica da interface espera uma classe de editor. Nesta edição
# independente ela é substituída por um placeholder mínimo e removida da pilha
# visual logo após a montagem da janela.
core.AdvancedVideoEditorWidget = _ExtractorOnlyPlaceholder


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
    """Login Android Flow com o mesmo proxy configurado no Extrator."""

    def __init__(self, parent=None, test_url='', proxy_url=''):
        self._previous_application_proxy = QNetworkProxy.applicationProxy()
        self._proxy_restored = False
        self._active_web_proxy = None

        if str(proxy_url or '').strip():
            self._active_web_proxy = _proxy_from_url(proxy_url)
            QNetworkProxy.setApplicationProxy(self._active_web_proxy)

        try:
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


# Configurações > Globoplay usa a implementação proxy-aware, mantendo o Android Flow.
v214.v210.GloboplayLoginDialog = ProxyAwareGloboplayLoginDialog
v214.GloboplayAndroidLoginDialog = ProxyAwareGloboplayLoginDialog


_previous_build_ui = core.MainWindow._build_ui


def _build_ui_extractor_only(self):
    _previous_build_ui(self)

    # Coluna lateral direita da referência antiga: totalmente oculta e largura zero.
    for frame in self.findChildren(QFrame):
        if frame.objectName() == 'RefinedRight':
            frame.hide()
            frame.setMinimumWidth(0)
            frame.setMaximumWidth(0)
            frame.setFixedWidth(0)

    # Remove a navegação do Editor desta aplicação independente.
    editor_button = getattr(self, 'ref_nav', {}).get('editor')
    if editor_button is not None:
        try:
            self.ref_nav_group.removeButton(editor_button)
        except Exception:
            pass
        editor_button.hide()
        editor_button.setEnabled(False)
        editor_button.setMaximumHeight(0)

    # Remove a página placeholder do Editor e corrige os índices restantes.
    stack = getattr(self, 'ref_stack', None)
    editor_page = getattr(self, 'editor_page', None)
    if stack is not None and editor_page is not None:
        idx = stack.indexOf(editor_page)
        if idx >= 0:
            stack.removeWidget(editor_page)
            editor_page.hide()

    def _rebind_nav(key, index):
        button = getattr(self, 'ref_nav', {}).get(key)
        if button is None:
            return
        try:
            button.clicked.disconnect()
        except Exception:
            pass
        button.clicked.connect(lambda _checked=False, i=index, k=key: (
            self.ref_stack.setCurrentIndex(i), self.ref_nav[k].setChecked(True)
        ))

    _rebind_nav('home', 0)
    _rebind_nav('download', 0)
    _rebind_nav('history', 1)
    _rebind_nav('settings', 2)
    if stack is not None:
        stack.setCurrentIndex(0)

    # Nenhuma menção visual ao Editor/Timeline nesta edição.
    replacements = {
        'Baixe, edite e salve com qualidade': 'Baixe e salve vídeos com qualidade',
        'Editor integrado': 'Compatibilidade MP4',
        'Corte e edite vídeos': 'Saída pronta para Windows',
        'Timeline visual': 'Downloads portáteis',
        'Reordene os clipes': 'Tudo organizado na pasta Videos',
        'Área reservada para os downloads e exportações recentes.': 'Área reservada para os downloads e resultados recentes.',
    }
    for label in self.findChildren(QLabel):
        text = label.text()
        if text in replacements:
            label.setText(replacements[text])
        if label.objectName() == 'RefinedVersion':
            label.setText(SIDEBAR_VERSION)


core.MainWindow._build_ui = _build_ui_extractor_only
core.APP_VERSION = APP_VERSION
v214.APP_VERSION = APP_VERSION
v214.SIDEBAR_VERSION = SIDEBAR_VERSION


def main():
    core.APP_VERSION = APP_VERSION
    v214.APP_VERSION = APP_VERSION
    v214.SIDEBAR_VERSION = SIDEBAR_VERSION
    return v214.main()


if __name__ == '__main__':
    main()
