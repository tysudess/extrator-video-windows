import json
import re

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtWidgets import QMessageBox

import refined_layout_v213 as v213

APP_VERSION = 'Windows Portable v2.0.14 — Globoplay Auto Player + Browser Auth + Download Direto'
SIDEBAR_VERSION = 'v2.0.14  •  GLOBOPLAY AUTO PLAYER'

core = v213.core
v212 = v213.v212
v211 = v213.v211
v210 = v213.v210
v209 = v213.v209
v208 = v213.v208
v207 = v213.v207
v202 = v213.v202
v201 = v213.v201


AUTO_PLAY_JS = r"""
(() => {
  const result = {video:false, clicked:false, label:'', center:false};
  const visible = (el) => {
    if (!el) return false;
    const r = el.getBoundingClientRect();
    const s = getComputedStyle(el);
    return r.width > 8 && r.height > 8 && s.display !== 'none' && s.visibility !== 'hidden' && s.opacity !== '0';
  };
  const clean = (v) => String(v || '').toLowerCase();
  const words = ['play','reproduzir','assistir','iniciar','continuar'];
  const score = (el) => {
    const text = [
      el.getAttribute && el.getAttribute('aria-label'),
      el.getAttribute && el.getAttribute('title'),
      el.getAttribute && el.getAttribute('data-testid'),
      el.getAttribute && el.getAttribute('data-test'),
      el.getAttribute && el.getAttribute('class'),
      el.innerText,
      el.textContent,
    ].map(clean).join(' ');
    let n = 0;
    for (const w of words) if (text.includes(w)) n += 4;
    if (text.includes('pause') || text.includes('pausar')) n -= 8;
    if (el.tagName === 'BUTTON') n += 2;
    return [n, text.slice(0,160)];
  };

  const video = document.querySelector('video');
  if (video) {
    result.video = true;
    try { video.muted = true; } catch (e) {}
    try { video.playsInline = true; } catch (e) {}
    try {
      const p = video.play();
      if (p && p.catch) p.catch(() => {});
    } catch (e) {}
  }

  const candidates = Array.from(document.querySelectorAll('button,[role="button"],a,[aria-label],[title],[data-testid],[data-test]'))
    .filter(visible)
    .map(el => [el, ...score(el)])
    .filter(x => x[1] > 0)
    .sort((a,b) => b[1]-a[1]);
  if (candidates.length) {
    const [el, n, label] = candidates[0];
    try { el.click(); result.clicked = true; result.label = label; } catch (e) {}
  }

  if (!result.clicked) {
    const vw = Math.max(document.documentElement.clientWidth || 0, window.innerWidth || 0);
    const vh = Math.max(document.documentElement.clientHeight || 0, window.innerHeight || 0);
    const points = [
      [Math.round(vw*0.40), Math.round(vh*0.45)],
      [Math.round(vw*0.35), Math.round(vh*0.50)],
      [Math.round(vw*0.45), Math.round(vh*0.50)],
    ];
    for (const [x,y] of points) {
      const el = document.elementFromPoint(x,y);
      if (!el) continue;
      const tag = clean(el.tagName);
      const txt = clean((el.innerText || el.textContent || '')).slice(0,120);
      if (txt.includes('edição') || txt.includes('edicoes') || tag === 'input') continue;
      try {
        el.dispatchEvent(new MouseEvent('mousedown',{bubbles:true,clientX:x,clientY:y}));
        el.dispatchEvent(new MouseEvent('mouseup',{bubbles:true,clientX:x,clientY:y}));
        el.dispatchEvent(new MouseEvent('click',{bubbles:true,clientX:x,clientY:y}));
        result.center = true;
        break;
      } catch (e) {}
    }
  }
  return result;
})();
"""


class GloboplayLoginDialog214(v213.GloboplayLoginDialog213):
    def __init__(self, parent=None, test_url='', proxy_url=''):
        super().__init__(parent, test_url, proxy_url)
        self._auto_player_attempts = 0
        self._auto_player_active = False
        self._last_auto_result = ''
        try:
            self.page.loadFinished.connect(self._page_loaded_v214)
        except Exception:
            pass
        if self.test_url:
            QTimer.singleShot(900, self._begin_auto_player)

    def _page_loaded_v214(self, ok):
        if not ok or not self.test_url:
            return
        QTimer.singleShot(700, self._begin_auto_player)

    def _begin_auto_player(self):
        if self._browser_authorization or v213._load_browser_authorization():
            return
        if self._auto_player_active:
            return
        self._auto_player_active = True
        self._auto_player_attempts = 0
        self.status.setText('Status: login ativo; procurando e iniciando o player do vídeo automaticamente…')
        self._auto_player_tick()

    def _auto_player_tick(self):
        if self._browser_authorization or v213._load_browser_authorization():
            self._auto_player_active = False
            self.status.setText('Status: autorização real do player capturada. Pronta para validação.')
            return
        self._auto_player_attempts += 1

        def got_result(result):
            try:
                if isinstance(result, dict):
                    bits = []
                    if result.get('video'):
                        bits.append('vídeo encontrado')
                    if result.get('clicked'):
                        bits.append('botão Play acionado')
                    elif result.get('center'):
                        bits.append('área do player acionada')
                    self._last_auto_result = ', '.join(bits)
            except Exception:
                pass

        try:
            self.page.runJavaScript(AUTO_PLAY_JS, got_result)
        except TypeError:
            try:
                self.page.runJavaScript(AUTO_PLAY_JS)
            except Exception:
                pass
        except Exception:
            pass

        if self._auto_player_attempts < 24:
            detail = self._last_auto_result or 'aguardando controles do player'
            self.status.setText(
                f'Status: ativando player automaticamente… {detail} '
                f'({self._auto_player_attempts}/24)'
            )
            QTimer.singleShot(700, self._auto_player_tick)
            return

        self._auto_player_active = False
        self.status.setText('Status: login ativo; o player não iniciou automaticamente.')

    def _try_start_video(self):
        try:
            self.page.runJavaScript(AUTO_PLAY_JS)
        except Exception:
            pass

    def _save_session(self):
        if self._browser_authorization or v213._load_browser_authorization():
            return self._validate_browser_authorization()

        self.btn_save.setEnabled(False)
        self._browser_wait_attempt = 0
        self._validation_running = False
        self._playback_request_seen = False
        self.status.setText('Status: ativando o player do Globoplay e capturando a sessão de reprodução…')

        if self.test_url:
            current = ''
            try:
                current = self.view.url().toString()
            except Exception:
                pass
            if self.test_url not in current:
                self.view.setUrl(QUrl(self.test_url))

        self._auto_player_active = False
        QTimer.singleShot(500, self._begin_auto_player)
        QTimer.singleShot(1200, self._wait_for_browser_authorization_v214)

    def _wait_for_browser_authorization_v214(self):
        if self._browser_authorization or v213._load_browser_authorization():
            self._auto_player_active = False
            self._validate_browser_authorization()
            return

        self._browser_wait_attempt += 1
        self._try_start_video()

        if self._browser_wait_attempt < 28:
            if self._playback_request_seen:
                detail = 'requisição de playback detectada; aguardando autorização'
            else:
                detail = self._last_auto_result or 'procurando o botão/área Play'
            self.status.setText(
                f'Status: login ativo; {detail} ({self._browser_wait_attempt}/28)'
            )
            QTimer.singleShot(700, self._wait_for_browser_authorization_v214)
            return

        self.btn_save.setEnabled(True)
        self._auto_player_active = False
        self.status.setText('Status: login ativo, mas o player não gerou uma sessão de reprodução.')
        QMessageBox.warning(
            self,
            core.APP_NAME,
            'A conta está conectada, mas esta página do Globoplay não iniciou o player nem gerou a sessão de reprodução.\n\n'
            'A v2.0.14 já tentou automaticamente o elemento <video>, botões Play/Reproduzir/Assistir e a área central do player. '
            'Se esta mensagem continuar aparecendo, envie uma nova captura desta janela para verificarmos o tipo específico de player da página.'
        )


v210.GloboplayLoginDialog = GloboplayLoginDialog214

core.APP_VERSION = APP_VERSION
v213.APP_VERSION = APP_VERSION
v213.SIDEBAR_VERSION = SIDEBAR_VERSION
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
    v213.APP_VERSION = APP_VERSION
    v213.SIDEBAR_VERSION = SIDEBAR_VERSION
    v212.APP_VERSION = APP_VERSION
    v212.SIDEBAR_VERSION = SIDEBAR_VERSION
    v211.APP_VERSION = APP_VERSION
    v211.SIDEBAR_VERSION = SIDEBAR_VERSION
    v210.APP_VERSION = APP_VERSION
    v210.SIDEBAR_VERSION = SIDEBAR_VERSION
    v209.APP_VERSION = APP_VERSION
    v209.SIDEBAR_VERSION = SIDEBAR_VERSION
    return v213.main()


if __name__ == '__main__':
    main()
