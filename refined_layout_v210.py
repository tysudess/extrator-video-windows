import json
import os
import re
import subprocess
from pathlib import Path

from PySide6.QtCore import QTimer, QThread, QUrl, Signal
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import (
    QDialog, QGroupBox, QHBoxLayout, QLabel, QMessageBox, QPushButton,
    QVBoxLayout,
)

import refined_layout_v209 as v209

APP_VERSION = 'Windows Portable v2.0.10 — Globoplay Login Interno Persistente + Download Direto'
SIDEBAR_VERSION = 'v2.0.10  •  GLOBOPLAY LOGIN INTERNO'

core = v209.core
v208 = v209.v208
v207 = v208.v207
v202 = v207.v202
v201 = v207.v201

PROFILE_ROOT = Path(os.environ.get('APPDATA') or Path.home()) / 'ExtratorVideos' / 'globoplay-web-profile'
PROFILE_CACHE = PROFILE_ROOT / 'cache'
DEFAULT_GLOBOPLAY_TEST_URL = 'https://globoplay.globo.com/v/14907582/?s=0'


def _extract_globo_id(url):
    match = re.search(r'(?i)globoplay\.globo\.com/v/(\d+)', str(url or ''))
    return match.group(1) if match else ''


_previous_cookie_args = v201._globoplay_cookie_args


def _globoplay_cookie_args_v210(url):
    text = str(url or '').strip()
    if text.lower().startswith('globo:'):
        runtime = v202._write_runtime_cookie_file()
        return ['--cookies', str(runtime)] if runtime else []
    return _previous_cookie_args(url)


v201._globoplay_cookie_args = _globoplay_cookie_args_v210


def _cookie_bytes(cookie):
    try:
        return bytes(cookie.name()), bytes(cookie.value())
    except Exception:
        return b'', b''


def _cookie_jar_from_qt(cookies):
    lines = [
        '# Netscape HTTP Cookie File',
        '# Gerado pelo Extrator de Videos - Globoplay Login Interno',
        '',
    ]
    count = 0
    seen = set()
    for cookie in cookies:
        try:
            domain = str(cookie.domain() or '').strip()
            low_domain = domain.lower().lstrip('.')
            if not (
                low_domain == 'globo.com'
                or low_domain.endswith('.globo.com')
                or low_domain == 'globoplay.com'
                or low_domain.endswith('.globoplay.com')
            ):
                continue
            name_raw, value_raw = _cookie_bytes(cookie)
            if not name_raw:
                continue
            name = name_raw.decode('utf-8', 'replace')
            value = value_raw.decode('utf-8', 'replace')
            path = str(cookie.path() or '/')
            secure = 'TRUE' if bool(cookie.isSecure()) else 'FALSE'
            include_subdomains = 'TRUE' if domain.startswith('.') else 'FALSE'
            expiry = 0
            try:
                dt = cookie.expirationDate()
                if dt.isValid():
                    expiry = max(0, int(dt.toSecsSinceEpoch()))
            except Exception:
                expiry = 0
            if bool(cookie.isHttpOnly()) and not domain.startswith('#HttpOnly_'):
                domain_out = '#HttpOnly_' + domain
            else:
                domain_out = domain
            key = (domain_out, path, name)
            if key in seen:
                continue
            seen.add(key)
            lines.append(
                '\t'.join([
                    domain_out,
                    include_subdomains,
                    path,
                    secure,
                    str(expiry),
                    name,
                    value,
                ])
            )
            count += 1
        except Exception:
            continue
    if count == 0:
        raise RuntimeError(
            'Nenhum cookie do domínio Globo/Globoplay foi encontrado. Conclua o login dentro da janela e tente novamente.'
        )
    return ('\n'.join(lines) + '\n').encode('utf-8'), count


def _has_confirmed_drm(data):
    formats = (data or {}).get('formats') or []
    drm_video = 0
    free_video = 0
    for fmt in formats:
        if not isinstance(fmt, dict):
            continue
        vcodec = str(fmt.get('vcodec') or 'none').lower()
        if vcodec == 'none':
            continue
        if fmt.get('has_drm') is True or fmt.get('drm_family'):
            drm_video += 1
        elif fmt.get('url'):
            free_video += 1
    return drm_video > 0 and free_video == 0


class GloboplayProbeWorker210(QThread):
    done = Signal(dict)
    failed = Signal(str)

    def __init__(self, url, proxy_url=''):
        super().__init__()
        self.url = str(url or '').strip()
        self.proxy_url = str(proxy_url or '')

    def _command(self, target):
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
        if self.proxy_url:
            cmd += ['--proxy', self.proxy_url]
        cmd += v201._globoplay_cookie_args(target)
        cmd.append(target)
        return cmd

    def run(self):
        try:
            if not core.YTDLP_EXE.exists():
                raise RuntimeError('yt-dlp.exe não encontrado na pasta bin.')
            if not v202._secure_session_exists():
                raise RuntimeError(
                    'A sessão interna do Globoplay ainda não foi salva. Abra Configurações > Globoplay > Login dentro do aplicativo.'
                )

            targets = [self.url]
            video_id = _extract_globo_id(self.url)
            if video_id:
                targets.append(f'globo:{video_id}')

            last_error = ''
            flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0) if os.name == 'nt' else 0
            for target in targets:
                try:
                    result = subprocess.run(
                        self._command(target),
                        capture_output=True,
                        text=True,
                        encoding='utf-8',
                        errors='replace',
                        creationflags=flags,
                        timeout=120,
                    )
                except Exception as exc:
                    last_error = str(exc)
                    continue

                if result.returncode != 0:
                    last_error = (result.stderr or result.stdout or 'Falha ao consultar o Globoplay.')[-3500:]
                    if 'drm' in last_error.lower():
                        raise RuntimeError(
                            'INDISPONÍVEL: este vídeo está protegido por DRM. O aplicativo não tenta contornar essa proteção.'
                        )
                    continue

                try:
                    data = json.loads(result.stdout)
                except Exception as exc:
                    last_error = f'Resposta inválida do yt-dlp: {exc}'
                    continue

                if _has_confirmed_drm(data):
                    raise RuntimeError(
                        'INDISPONÍVEL: os formatos retornados para este vídeo estão protegidos por DRM. O aplicativo não tenta contornar essa proteção.'
                    )

                try:
                    payload = v207._analysis_payload(data, self.url, target)
                    payload['globoplay_resolved_url'] = target
                    self.done.emit(payload)
                    return
                except Exception as exc:
                    last_error = str(exc)

            low = last_error.lower()
            if any(key in low for key in (
                'login', 'sign in', 'cookies', 'account', 'subscriber', 'subscription',
                'authentication', 'autentica', 'assinatura',
            )):
                raise RuntimeError(
                    'Globoplay: a sessão salva não foi aceita para este vídeo. Abra o Login Globoplay dentro do aplicativo, confirme que sua conta está conectada e salve/valide a sessão novamente.\n\n'
                    + last_error
                )
            raise RuntimeError(
                'Globoplay: não foi possível obter um formato utilizável pelo link normal nem pelo identificador interno do vídeo.\n\n'
                + (last_error or 'Nenhum detalhe adicional foi retornado.')
            )
        except Exception as exc:
            self.failed.emit(str(exc))


class GloboplayLoginDialog(QDialog):
    def __init__(self, parent=None, test_url='', proxy_url=''):
        super().__init__(parent)
        self.test_url = str(test_url or '').strip()
        if not v201._is_globoplay_url(self.test_url):
            self.test_url = DEFAULT_GLOBOPLAY_TEST_URL
        self.proxy_url = str(proxy_url or '')
        self.cookies = {}
        self.validation_worker = None

        self.setWindowTitle('Globoplay — Login dentro do Extrator')
        self.resize(1080, 780)

        root = QVBoxLayout(self)
        info = QLabel(
            'Faça o login normalmente nesta janela do Globoplay. A página é a própria página da Globo. '
            'O Extrator não recebe nem grava sua senha: ele mantém apenas a sessão/cookies do navegador interno. '
            'Depois do login, clique em SALVAR E VALIDAR SESSÃO.'
        )
        info.setWordWrap(True)
        root.addWidget(info)

        self.status = QLabel('Status: aguardando login no Globoplay…')
        self.status.setWordWrap(True)
        root.addWidget(self.status)

        PROFILE_ROOT.mkdir(parents=True, exist_ok=True)
        PROFILE_CACHE.mkdir(parents=True, exist_ok=True)
        self.profile = QWebEngineProfile('ExtratorVideosGloboplay', self)
        self.profile.setPersistentStoragePath(str(PROFILE_ROOT))
        self.profile.setCachePath(str(PROFILE_CACHE))
        try:
            self.profile.setPersistentCookiesPolicy(
                QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies
            )
        except Exception:
            pass

        self.view = QWebEngineView(self)
        self.page = QWebEnginePage(self.profile, self.view)
        self.view.setPage(self.page)
        root.addWidget(self.view, 1)

        cookie_store = self.profile.cookieStore()
        cookie_store.cookieAdded.connect(self._cookie_added)
        cookie_store.loadAllCookies()

        actions = QHBoxLayout()
        self.btn_home = QPushButton('ABRIR GLOBOPLAY')
        self.btn_save = QPushButton('SALVAR E VALIDAR SESSÃO')
        self.btn_close = QPushButton('FECHAR')
        actions.addWidget(self.btn_home)
        actions.addWidget(self.btn_save)
        actions.addStretch(1)
        actions.addWidget(self.btn_close)
        root.addLayout(actions)

        self.btn_home.clicked.connect(
            lambda: self.view.setUrl(QUrl('https://globoplay.globo.com/'))
        )
        self.btn_save.clicked.connect(self._save_session)
        self.btn_close.clicked.connect(self.reject)

        self.view.setUrl(QUrl('https://globoplay.globo.com/'))

    def _cookie_added(self, cookie):
        try:
            name_raw, _value_raw = _cookie_bytes(cookie)
            key = (
                str(cookie.domain() or ''),
                str(cookie.path() or '/'),
                bytes(name_raw),
            )
            self.cookies[key] = cookie
        except Exception:
            pass

    def _save_session(self):
        self.btn_save.setEnabled(False)
        self.status.setText('Status: coletando a sessão do navegador interno…')
        self.cookies.clear()
        try:
            self.profile.cookieStore().loadAllCookies()
        except Exception:
            pass
        QTimer.singleShot(1400, self._finish_export)

    def _finish_export(self):
        try:
            raw, count = _cookie_jar_from_qt(list(self.cookies.values()))
            v202._save_secure_session(raw)
            v202._write_runtime_cookie_file()
            self.status.setText(
                f'Status: {count} cookies Globo/Globoplay salvos e protegidos pelo Windows. Validando a sessão…'
            )
        except Exception as exc:
            self.btn_save.setEnabled(True)
            self.status.setText('Status: não foi possível salvar a sessão.')
            QMessageBox.warning(self, core.APP_NAME, str(exc))
            return

        self.validation_worker = GloboplayProbeWorker210(self.test_url, self.proxy_url)

        def validated(_payload):
            self.btn_save.setEnabled(True)
            self.status.setText('Status: SESSÃO VALIDADA E SALVA. O download direto pode usar esta conta.')
            QMessageBox.information(
                self,
                core.APP_NAME,
                'Login do Globoplay validado e sessão salva com sucesso.\n\nO aplicativo continuará usando essa sessão nos próximos downloads enquanto ela permanecer válida.'
            )
            self.accept()

        def validation_failed(message):
            self.btn_save.setEnabled(True)
            self.status.setText('Status: sessão salva, mas a validação do vídeo não foi concluída.')
            QMessageBox.warning(
                self,
                core.APP_NAME,
                'A sessão foi capturada, mas o teste do Globoplay ainda falhou.\n\n' + str(message)
            )

        self.validation_worker.done.connect(validated)
        self.validation_worker.failed.connect(validation_failed)
        self.validation_worker.start()


_previous_build_ui = core.MainWindow._build_ui


def _build_ui_v210(self):
    _previous_build_ui(self)
    try:
        # Esconde os cartões antigos que dependiam do navegador externo para não confundir.
        for box in self.findChildren(QGroupBox):
            title = str(box.title() or '').lower()
            if title.startswith('globoplay —'):
                box.setVisible(False)

        settings_scroll = self.ref_stack.widget(3)
        settings_page = settings_scroll.widget()
        layout = settings_page.layout()

        box = QGroupBox('Globoplay — login dentro do aplicativo')
        col = QVBoxLayout(box)

        info = QLabel(
            'Use este login para o Globoplay. A sessão fica em um navegador interno persistente e é exportada '
            'automaticamente para o yt-dlp. Não é mais necessário fechar Chrome/Edge nem copiar cookies do navegador externo.'
        )
        info.setWordWrap(True)
        info.setObjectName('RefinedText')
        col.addWidget(info)

        self.globoplay_internal_status = QLabel()
        self.globoplay_internal_status.setObjectName('RefinedText')
        col.addWidget(self.globoplay_internal_status)

        def refresh_status():
            if v202._secure_session_exists():
                self.globoplay_internal_status.setText('Sessão Globoplay: SALVA — login interno disponível para download')
            else:
                self.globoplay_internal_status.setText('Sessão Globoplay: ainda não validada')

        refresh_status()

        actions = QHBoxLayout()
        self.btn_globoplay_internal_login = QPushButton('ABRIR LOGIN GLOBOPLAY')
        self.btn_globoplay_internal_login.setObjectName('RefinedPrimary')
        self.btn_globoplay_internal_forget = QPushButton('APAGAR SESSÃO')
        self.btn_globoplay_internal_forget.setObjectName('RefinedGhost')
        actions.addWidget(self.btn_globoplay_internal_login)
        actions.addWidget(self.btn_globoplay_internal_forget)
        actions.addStretch(1)
        col.addLayout(actions)

        note = QLabel(
            'A senha é digitada somente na página oficial da Globo dentro da janela de login. '
            'O Extrator salva apenas a sessão/cookies e continua respeitando DRM, assinatura e permissões da conta.'
        )
        note.setWordWrap(True)
        note.setObjectName('RefinedMuted')
        col.addWidget(note)

        def open_login():
            proxy = self._current_proxy_url(True)
            if proxy is None:
                return
            url = self.url_edit.text().strip()
            dialog = GloboplayLoginDialog(self, url, proxy)
            dialog.exec()
            refresh_status()

        def forget_login():
            v202._delete_secure_session()
            try:
                import shutil
                if PROFILE_ROOT.exists():
                    shutil.rmtree(PROFILE_ROOT, ignore_errors=True)
            except Exception:
                pass
            refresh_status()
            QMessageBox.information(self, core.APP_NAME, 'A sessão interna do Globoplay foi apagada.')

        self.btn_globoplay_internal_login.clicked.connect(open_login)
        self.btn_globoplay_internal_forget.clicked.connect(forget_login)
        layout.insertWidget(max(0, layout.count() - 1), box)
    except Exception:
        pass


core.MainWindow._build_ui = _build_ui_v210


def _start_globoplay_download_v210(self, original_url, proxy, quality_index, payload):
    selected = v209._select_globoplay_quality(payload, quality_index)
    if not selected:
        self.download_failed('Globoplay: nenhuma qualidade utilizável foi confirmada para download.')
        return

    selector = str(selected.get('selector') or '').strip()
    compat = str(selected.get('compat_selector') or '').strip() or selector
    if not selector:
        self.download_failed('Globoplay: o formato confirmado não apresentou um seletor válido.')
        return

    target = str((payload or {}).get('globoplay_resolved_url') or original_url).strip()
    chosen_label = str(selected.get('label') or f"{int(selected.get('height') or 0)}p")
    self.download_status.setText(f'Globoplay: sessão validada. Baixando em {chosen_label}…')

    self.download_worker = core.DownloadWorker(
        target,
        0,
        proxy,
        format_selector=selector,
        compat_selector=compat,
    )
    self.download_worker.progress.connect(self._update_download_progress)
    self.download_worker.message.connect(self.download_status.setText)
    self.download_worker.done.connect(self.download_finished)
    self.download_worker.failed.connect(self.download_failed)
    self.download_worker.canceled.connect(self.download_canceled)
    self.download_worker.start()


_previous_download_video = core.MainWindow.download_video


def direct_download_video_v210(self):
    url = self.url_edit.text().strip()
    if not v201._is_globoplay_url(url):
        return _previous_download_video(self)

    if not url.startswith(('http://', 'https://')):
        QMessageBox.warning(self, core.APP_NAME, 'Cole um link válido começando com http:// ou https://')
        return
    if getattr(self, 'download_worker', None) and self.download_worker.isRunning():
        return
    if getattr(self, 'direct_globoplay_worker', None) and self.direct_globoplay_worker.isRunning():
        return

    proxy = self._current_proxy_url(True)
    if proxy is None:
        return

    if not v202._secure_session_exists():
        dialog = GloboplayLoginDialog(self, url, proxy)
        if dialog.exec() != QDialog.DialogCode.Accepted or not v202._secure_session_exists():
            self.download_status.setText('Globoplay: login interno ainda não validado.')
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
    self.download_status.setText('Globoplay: validando sessão interna e preparando o vídeo…')

    self.direct_globoplay_worker = GloboplayProbeWorker210(url, proxy)

    def done(payload):
        try:
            self.direct_quality_combo.setEnabled(True)
        except Exception:
            pass
        _start_globoplay_download_v210(self, url, proxy, quality_index, payload)

    def failed(message):
        try:
            self.direct_quality_combo.setEnabled(True)
        except Exception:
            pass
        self._set_download_busy(False)
        text = str(message or '')
        if any(key in text.lower() for key in ('login', 'sessão', 'cookies', 'autentica', 'account')):
            result = QMessageBox.question(
                self,
                core.APP_NAME,
                text + '\n\nDeseja abrir agora o Login Globoplay dentro do aplicativo?'
            )
            if result == QMessageBox.StandardButton.Yes:
                dialog = GloboplayLoginDialog(self, url, proxy)
                dialog.exec()
        else:
            QMessageBox.critical(self, core.APP_NAME, text)
        self.download_status.setText('Globoplay: não foi possível preparar o download.')

    self.direct_globoplay_worker.done.connect(done)
    self.direct_globoplay_worker.failed.connect(failed)
    self.direct_globoplay_worker.start()


core.MainWindow.download_video = direct_download_video_v210

core.APP_VERSION = APP_VERSION
v209.APP_VERSION = APP_VERSION
v209.SIDEBAR_VERSION = SIDEBAR_VERSION


def main():
    core.APP_VERSION = APP_VERSION
    v209.APP_VERSION = APP_VERSION
    v209.SIDEBAR_VERSION = SIDEBAR_VERSION
    return v209.main()


if __name__ == '__main__':
    main()
