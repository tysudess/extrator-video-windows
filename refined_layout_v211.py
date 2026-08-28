from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QMessageBox

import refined_layout_v210 as v210

APP_VERSION = 'Windows Portable v2.0.11 — Globoplay Cookie Capture Fix + Login Interno Persistente'
SIDEBAR_VERSION = 'v2.0.11  •  GLOBOPLAY COOKIE FIX'

core = v210.core
v209 = v210.v209
v208 = v210.v208
v207 = v210.v207
v202 = v210.v202
v201 = v210.v201


class GloboplayLoginDialog211(v210.GloboplayLoginDialog):
    """Corrige a coleta da sessão do navegador interno.

    A v2.0.10 já recebia os cookies pelo sinal cookieAdded durante a navegação,
    mas apagava self.cookies ao clicar em SALVAR E VALIDAR SESSÃO. Esta versão
    preserva os cookies já observados e usa loadAllCookies apenas como complemento.
    """

    def _save_session(self):
        self.btn_save.setEnabled(False)
        self.status.setText(
            f'Status: coletando a sessão do navegador interno… ({len(self.cookies)} cookies já observados)'
        )
        self._cookie_export_attempt = 0

        # NÃO limpar self.cookies aqui. Esses são exatamente os cookies capturados
        # durante o login que acabamos de confirmar no WebEngine.
        try:
            self.profile.cookieStore().loadAllCookies()
        except Exception:
            pass

        QTimer.singleShot(500, self._finish_export_when_ready)

    def _finish_export_when_ready(self):
        self._cookie_export_attempt = int(getattr(self, '_cookie_export_attempt', 0)) + 1

        # Primeiro tenta com tudo o que já foi capturado durante a navegação.
        try:
            v210._cookie_jar_from_qt(list(self.cookies.values()))
        except Exception:
            # loadAllCookies é assíncrono. Damos até ~6 s para o Qt emitir
            # cookieAdded de todos os cookies persistidos do perfil.
            if self._cookie_export_attempt < 8:
                try:
                    self.profile.cookieStore().loadAllCookies()
                except Exception:
                    pass
                self.status.setText(
                    f'Status: aguardando os cookies da sessão… tentativa {self._cookie_export_attempt}/8'
                )
                QTimer.singleShot(700, self._finish_export_when_ready)
                return

            self.btn_save.setEnabled(True)
            self.status.setText('Status: não foi possível localizar cookies Globo/Globoplay no perfil interno.')
            QMessageBox.warning(
                self,
                core.APP_NAME,
                'O Globoplay está aberto, mas o Qt WebEngine ainda não entregou os cookies da sessão ao Extrator.\n\n'
                'Feche esta janela de login, abra novamente e clique em SALVAR E VALIDAR SESSÃO sem sair da conta.'
            )
            return

        # A rotina original da v2.0.10 já faz: Netscape -> DPAPI -> validação yt-dlp.
        return v210.GloboplayLoginDialog._finish_export(self)


# O _build_ui_v210 e o download direto procuram este nome global no módulo v210.
# Substituindo a classe aqui, Configurações e o fluxo automático passam a usar o fix.
v210.GloboplayLoginDialog = GloboplayLoginDialog211

core.APP_VERSION = APP_VERSION
v210.APP_VERSION = APP_VERSION
v210.SIDEBAR_VERSION = SIDEBAR_VERSION
v209.APP_VERSION = APP_VERSION
v209.SIDEBAR_VERSION = SIDEBAR_VERSION


def main():
    core.APP_VERSION = APP_VERSION
    v210.APP_VERSION = APP_VERSION
    v210.SIDEBAR_VERSION = SIDEBAR_VERSION
    v209.APP_VERSION = APP_VERSION
    v209.SIDEBAR_VERSION = SIDEBAR_VERSION
    return v210.main()


if __name__ == '__main__':
    main()
