import sys

from PySide6.QtWidgets import QApplication, QLabel

import refined_layout as base

APP_VERSION_V2 = 'Windows Portable v2.0 — Evolução Consolidada + Qualidades Reais + Globoplay'
SIDEBAR_VERSION_V2 = 'v2.0  •  EVOLUÇÃO CONSOLIDADA'

# A v2.0 usa integralmente o motor/layout aprovado da v1.9.22.
# Esta camada altera somente a identificação da versão exibida ao usuário.
base.core.APP_VERSION = APP_VERSION_V2


def main():
    base.core.APP_VERSION = APP_VERSION_V2
    app = QApplication(sys.argv)
    app.setApplicationName(base.core.APP_NAME)
    app.setOrganizationName('ExtratorVideos')
    app.setStyle('Fusion')
    app.setStyleSheet(base.core.FUTURE_STYLESHEET)
    app.setWindowIcon(base._app_icon())

    window = base.core.MainWindow()
    window.setWindowIcon(base._app_icon())

    # Atualiza apenas o texto de versão do rodapé; não altera o layout.
    for label in window.findChildren(QLabel):
        if label.objectName() == 'RefinedVersion':
            label.setText(SIDEBAR_VERSION_V2)
            break

    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
