from PySide6.QtWidgets import QFrame, QLabel

import refined_layout_v214 as v214
import advanced_editor_v300 as editor_v300

APP_VERSION = 'Windows Portable v3.0 — Final + Globoplay Android Flow + Timeline Undo'
SIDEBAR_VERSION = 'v3.0  •  FINAL'

core = v214.core

# O editor v3.0 é usado pela construção normal da interface, sem alterar o
# restante da arquitetura aprovada do aplicativo.
core.AdvancedVideoEditorWidget = editor_v300.AdvancedVideoEditorWidget300

_previous_build_ui = core.MainWindow._build_ui


def _build_ui_v300(self):
    _previous_build_ui(self)

    # Limpeza final solicitada: remove totalmente a coluna lateral direita
    # "NOVO DESIGN / ÍCONE DO APLICATIVO". Como o centro já está com stretch=1,
    # ele ocupa automaticamente todo o espaço liberado.
    for frame in self.findChildren(QFrame):
        if frame.objectName() == 'RefinedRight':
            frame.hide()
            frame.setMinimumWidth(0)
            frame.setMaximumWidth(0)
            frame.setFixedWidth(0)

    for label in self.findChildren(QLabel):
        if label.objectName() == 'RefinedVersion':
            label.setText(SIDEBAR_VERSION)
            break


core.MainWindow._build_ui = _build_ui_v300
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
