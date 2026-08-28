from PySide6.QtWidgets import QMessageBox

import refined_layout_v208 as v208

APP_VERSION = 'Windows Portable v2.0.9 — Download Direto + Globoplay Sessão Restaurada + R7 Android Flow'
SIDEBAR_VERSION = 'v2.0.9  •  GLOBOPLAY DIRECT FIX'

core = v208.core
v207 = v208.v207
v202 = v207.v202
v201 = v207.v201


def _select_globoplay_quality(payload, quality_index):
    available = [
        item for item in (payload or {}).get('available_qualities', [])
        if isinstance(item, dict) and int(item.get('height') or 0) > 0
    ]
    if not available:
        return None

    available.sort(key=lambda item: int(item.get('height') or 0), reverse=True)
    quality_index = max(0, min(len(v208.DIRECT_QUALITIES) - 1, int(quality_index)))
    label, target_height, _fmt, _compat = v208.DIRECT_QUALITIES[quality_index]

    if quality_index == len(v208.DIRECT_QUALITIES) - 1:
        return available[0]

    at_or_below = [
        item for item in available
        if int(item.get('height') or 0) <= int(target_height or 0)
    ]
    if at_or_below:
        return max(at_or_below, key=lambda item: int(item.get('height') or 0))

    # Mesmo princípio do fallback final /b usado pelo Android: se não houver
    # nenhuma resolução abaixo da escolhida, usa a menor resolução disponível.
    return min(available, key=lambda item: int(item.get('height') or 0))


def _start_globoplay_download(self, url, proxy, quality_index, payload):
    selected = _select_globoplay_quality(payload, quality_index)
    if not selected:
        self.download_failed(
            'Globoplay: a sessão foi consultada, mas nenhuma qualidade utilizável '
            'foi confirmada para download.'
        )
        return

    selector = str(selected.get('selector') or '').strip()
    compat = str(selected.get('compat_selector') or '').strip()
    if not selector:
        self.download_failed(
            'Globoplay: a qualidade selecionada não apresentou um formato de download válido.'
        )
        return

    chosen_label = str(selected.get('label') or f"{int(selected.get('height') or 0)}p")
    self.download_status.setText(
        f'Globoplay: sessão autenticada confirmada. Baixando em {chosen_label}...'
    )

    # Usa o DownloadWorker atual. A cadeia v2.0.2 mantém a injeção da sessão
    # persistente (--cookies) somente para URLs do Globoplay.
    self.download_worker = core.DownloadWorker(
        url,
        0,
        proxy,
        format_selector=selector,
        compat_selector=compat or selector,
    )
    self.download_worker.progress.connect(self._update_download_progress)
    self.download_worker.message.connect(self.download_status.setText)
    self.download_worker.done.connect(self.download_finished)
    self.download_worker.failed.connect(self.download_failed)
    self.download_worker.canceled.connect(self.download_canceled)
    self.download_worker.start()


def _globoplay_analysis_failed(self, message):
    text = str(message or 'Não foi possível validar a sessão do Globoplay.')
    low = text.lower()
    if any(key in low for key in ('login', 'sign in', 'cookies', 'sessão', 'assinatura', 'subscription')):
        text += (
            '\n\nAbra Configurações > Globoplay, faça login na sua conta e use '
            'Salvar sessão autenticada. Depois tente BAIXAR VÍDEO novamente.'
        )
    self.download_failed(text)


def direct_download_video_v209(self):
    url = self.url_edit.text().strip()

    # Mantém exatamente o fluxo da v2.0.8 para R7, YouTube e demais sites.
    if not v201._is_globoplay_url(url):
        return v208.direct_download_video(self)

    if not url.startswith(('http://', 'https://')):
        QMessageBox.warning(
            self,
            core.APP_NAME,
            'Cole um link válido começando com http:// ou https://'
        )
        return

    if getattr(self, 'download_worker', None) and self.download_worker.isRunning():
        return
    if getattr(self, 'direct_globoplay_worker', None) and self.direct_globoplay_worker.isRunning():
        return

    proxy = self._current_proxy_url(True)
    if proxy is None:
        return

    quality_index = max(
        0,
        min(len(v208.DIRECT_QUALITIES) - 1, self.direct_quality_combo.currentIndex())
    )

    self._update_proxy_status()
    self._update_download_progress(0)
    self._set_download_busy(True)
    try:
        self.direct_quality_combo.setEnabled(False)
    except Exception:
        pass

    self.download_status.setText(
        'Globoplay: validando a sessão persistente e preparando a qualidade...'
    )

    # O botão ANALISAR continua removido. A antiga análise autenticada agora é
    # executada silenciosamente apenas para Globoplay ao clicar em BAIXAR.
    self.direct_globoplay_worker = v201.GloboplayAnalyzeWorker(url, proxy)

    def done(payload):
        try:
            self.direct_quality_combo.setEnabled(True)
        except Exception:
            pass
        _start_globoplay_download(self, url, proxy, quality_index, payload)

    def failed(message):
        try:
            self.direct_quality_combo.setEnabled(True)
        except Exception:
            pass
        _globoplay_analysis_failed(self, message)

    self.direct_globoplay_worker.done.connect(done)
    self.direct_globoplay_worker.failed.connect(failed)
    self.direct_globoplay_worker.start()


core.MainWindow.download_video = direct_download_video_v209

# Mantém o versionamento correto através das camadas anteriores.
core.APP_VERSION = APP_VERSION
v208.APP_VERSION = APP_VERSION
v208.SIDEBAR_VERSION = SIDEBAR_VERSION


def main():
    core.APP_VERSION = APP_VERSION
    v208.APP_VERSION = APP_VERSION
    v208.SIDEBAR_VERSION = SIDEBAR_VERSION
    return v208.main()


if __name__ == '__main__':
    main()
