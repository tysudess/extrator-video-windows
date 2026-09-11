import sys
import types

from PySide6.QtWidgets import QApplication, QLabel, QTabWidget, QVBoxLayout, QWidget


class _EditorPlaceholder(QWidget):
    """Placeholder mínimo para permitir reutilizar o downloader sem carregar o editor."""

    def __init__(self, *args, **kwargs):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel('Editor separado do Extrator.'))

    def shutdown(self):
        pass


# A árvore v3.0.1 importa o editor durante a inicialização. Para o executável
# EXTRATOR-ONLY substituímos somente esses módulos por placeholders leves.
_stub_base = types.ModuleType('advanced_editor')
_stub_base.AdvancedVideoEditorWidget = _EditorPlaceholder
sys.modules['advanced_editor'] = _stub_base

_stub_v300 = types.ModuleType('advanced_editor_v300')
_stub_v300.AdvancedVideoEditorWidget300 = _EditorPlaceholder
sys.modules['advanced_editor_v300'] = _stub_v300

import refined_layout_v301 as app_v301


APP_NAME = 'Extrator de Vídeos — Download'
APP_VERSION = 'v3.0.1 Split — Downloader'


def _remove_editor_tabs(window):
    for tabs in window.findChildren(QTabWidget):
        for index in range(tabs.count() - 1, -1, -1):
            title = (tabs.tabText(index) or '').lower()
            if 'editor' in title or 'timeline' in title:
                widget = tabs.widget(index)
                tabs.removeTab(index)
                if widget is not None:
                    widget.deleteLater()

    # Remove referências visuais ao editor integrado, sem alterar o motor de download.
    for label in window.findChildren(QLabel):
        text = label.text() or ''
        low = text.lower()
        if 'editor / timeline' in low or 'edição em timeline' in low:
            if 'fluxo recomendado' in low:
                label.setText('DOWNLOAD INDEPENDENTE  •  Os vídeos baixados ficam na pasta Videos e podem ser abertos no Editor de Vídeo separado.')
            elif 'download, edição' in low:
                label.setText('Download de vídeos com seleção de qualidade, proxy e compatibilidade preservados da v3.0.1.')


def main():
    app_v301.core.APP_VERSION = APP_VERSION
    app = QApplication.instance() or QApplication(sys.argv)
    window = app_v301.core.MainWindow()
    window.setWindowTitle(f'{APP_NAME} — {APP_VERSION}')
    _remove_editor_tabs(window)
    window.show()
    return app.exec()


if __name__ == '__main__':
    raise SystemExit(main())
