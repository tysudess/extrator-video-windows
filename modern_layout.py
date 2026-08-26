import sys
from pathlib import Path

import main as core
import novo_layout  # carrega a identidade visual premium v1.9.15 como base

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QComboBox,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)


core.APP_VERSION = 'Windows Portable v1.9.16 — Modern UI — Timeline Premium + compressão inteligente'


MODERN_EXTRA_STYLESHEET = r"""
QWidget#AppRoot {
    background-color: #070A12;
}
QFrame#Sidebar {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #0A0D18, stop:0.55 #090C16, stop:1 #070A12);
    border-right: 1px solid #1C2437;
}
QFrame#ContentArea {
    background-color: #0A0E17;
}
QFrame#TopBar {
    background-color: #0C111C;
    border-bottom: 1px solid #1B2638;
}
QLabel#BrandMark {
    color: #FFFFFF;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                stop:0 #8A31F2, stop:0.55 #4A4BFF, stop:1 #1597F7);
    border: 1px solid #7867FF;
    border-radius: 12px;
    font-size: 18pt;
    font-weight: 900;
    padding: 4px;
}
QLabel#BrandTitle {
    color: #FFFFFF;
    font-size: 13pt;
    font-weight: 850;
}
QLabel#BrandSubtitle {
    color: #7F8AA0;
    font-size: 8pt;
}
QLabel#HeaderTitle {
    color: #FFFFFF;
    font-size: 17pt;
    font-weight: 800;
}
QLabel#HeaderSubtitle {
    color: #8E99AC;
    font-size: 9pt;
}
QLabel#VersionBadge {
    background-color: #111827;
    color: #9CA8BF;
    border: 1px solid #26334A;
    border-radius: 9px;
    padding: 5px 9px;
    font-size: 8pt;
    font-weight: 650;
}
QPushButton#NavButton {
    background-color: transparent;
    color: #AEB8CB;
    border: 1px solid transparent;
    border-radius: 11px;
    padding: 11px 13px;
    text-align: left;
    font-size: 10pt;
    font-weight: 700;
    min-height: 25px;
}
QPushButton#NavButton:hover {
    background-color: #111827;
    color: #FFFFFF;
    border-color: #24324A;
}
QPushButton#NavButton:checked {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #302062, stop:0.52 #25246A, stop:1 #153F76);
    color: #FFFFFF;
    border: 1px solid #5B55C8;
}
QPushButton#SidebarAction {
    background-color: #0E1420;
    color: #D7DFEE;
    border: 1px solid #26334A;
    border-radius: 10px;
    padding: 9px 11px;
    text-align: left;
}
QPushButton#SidebarAction:hover {
    background-color: #151D2B;
    border-color: #425474;
}
QFrame#StatusCard {
    background-color: #0C1420;
    border: 1px solid #22314A;
    border-radius: 12px;
}
QLabel#StatusDot {
    color: #30D17C;
    font-size: 11pt;
    font-weight: 900;
}
QLabel#StatusText {
    color: #C6D1E4;
    font-size: 9pt;
    font-weight: 700;
}
QFrame#HeroCard {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                stop:0 #101827, stop:0.54 #101421, stop:1 #0D1220);
    border: 1px solid #24324A;
    border-radius: 17px;
}
QLabel#HeroKicker {
    color: #8F7CFF;
    font-size: 8pt;
    font-weight: 850;
    letter-spacing: 1px;
}
QLabel#HeroTitle {
    color: #FFFFFF;
    font-size: 19pt;
    font-weight: 850;
}
QLabel#HeroText {
    color: #93A0B5;
    font-size: 9pt;
}
QFrame#FeatureTile {
    background-color: #0D1420;
    border: 1px solid #202D42;
    border-radius: 12px;
}
QLabel#FeatureIcon {
    color: #9B79FF;
    font-size: 15pt;
    font-weight: 900;
}
QLabel#FeatureTitle {
    color: #EAF0FA;
    font-weight: 750;
    font-size: 9pt;
}
QLabel#FeatureText {
    color: #7F8DA4;
    font-size: 8pt;
}
QFrame#DownloadCard, QFrame#ProgressCard, QFrame#ProxyCard {
    background-color: #0D131F;
    border: 1px solid #223047;
    border-radius: 16px;
}
QLabel#CardTitle {
    color: #EDF3FC;
    font-size: 11pt;
    font-weight: 800;
}
QLabel#CardHint {
    color: #8390A5;
    font-size: 8pt;
}
QLineEdit#UrlInput {
    min-height: 29px;
    font-size: 10pt;
    padding: 10px 12px;
    border-radius: 11px;
}
QPushButton#PrimaryDownload {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #7D28E8, stop:0.48 #5D3AF4, stop:1 #2679FF);
    color: white;
    border: 1px solid #7F6CFF;
    border-radius: 11px;
    padding: 10px 18px;
    min-height: 29px;
    font-size: 10pt;
    font-weight: 850;
}
QPushButton#PrimaryDownload:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #9237F5, stop:0.48 #704BFF, stop:1 #3788FF);
    border-color: #B3A7FF;
}
QProgressBar#DownloadProgress {
    min-height: 21px;
    border-radius: 10px;
    background-color: #090E17;
    border: 1px solid #1E2A3E;
    color: #EAF0F8;
    font-weight: 750;
}
QProgressBar#DownloadProgress::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #7B2FE8, stop:0.5 #5B43F0, stop:1 #2385F7);
    border-radius: 9px;
}
QStackedWidget {
    background: transparent;
    border: none;
}
QScrollArea#PageScroll {
    background: transparent;
    border: none;
}
QScrollArea#PageScroll > QWidget > QWidget {
    background: transparent;
}
QPushButton:focus, QLineEdit:focus, QComboBox:focus, QRadioButton:focus {
    outline: none;
    border-color: #8B7AFF;
}
"""

core.FUTURE_STYLESHEET = core.FUTURE_STYLESHEET + '\n' + MODERN_EXTRA_STYLESHEET


def _icon_path():
    base = Path(__file__).resolve().parent
    candidate = base / 'ExtratorVideos-Icone.ico'
    if candidate.exists():
        return candidate
    if getattr(sys, 'frozen', False):
        return Path(sys.executable)
    return candidate


def _app_icon():
    return QIcon(str(_icon_path()))


def _card_layout(frame, margins=(18, 16, 18, 16), spacing=12):
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(*margins)
    layout.setSpacing(spacing)
    return layout


def _make_feature(icon_text, title_text, subtitle_text):
    tile = QFrame()
    tile.setObjectName('FeatureTile')
    tile.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    row = QHBoxLayout(tile)
    row.setContentsMargins(13, 10, 13, 10)
    row.setSpacing(10)

    icon = QLabel(icon_text)
    icon.setObjectName('FeatureIcon')
    icon.setFixedWidth(28)
    row.addWidget(icon)

    text_box = QVBoxLayout()
    text_box.setSpacing(1)
    title = QLabel(title_text)
    title.setObjectName('FeatureTitle')
    subtitle = QLabel(subtitle_text)
    subtitle.setObjectName('FeatureText')
    subtitle.setWordWrap(True)
    text_box.addWidget(title)
    text_box.addWidget(subtitle)
    row.addLayout(text_box, 1)
    return tile


def _make_nav_button(text, accessible_name):
    button = QPushButton(text)
    button.setObjectName('NavButton')
    button.setCheckable(True)
    button.setAccessibleName(accessible_name)
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    return button


def build_modern_ui(self):
    self.setWindowIcon(_app_icon())
    self.setMinimumSize(900, 650)

    root = QWidget()
    root.setObjectName('AppRoot')
    self.setCentralWidget(root)
    root_layout = QHBoxLayout(root)
    root_layout.setContentsMargins(0, 0, 0, 0)
    root_layout.setSpacing(0)

    # ---------------- Sidebar ----------------
    sidebar = QFrame()
    sidebar.setObjectName('Sidebar')
    sidebar.setFixedWidth(224)
    sidebar_layout = QVBoxLayout(sidebar)
    sidebar_layout.setContentsMargins(18, 20, 18, 16)
    sidebar_layout.setSpacing(8)

    brand_row = QHBoxLayout()
    brand_row.setSpacing(10)
    brand_mark = QLabel('▶')
    brand_mark.setObjectName('BrandMark')
    brand_mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
    brand_mark.setFixedSize(42, 42)
    brand_row.addWidget(brand_mark)

    brand_text = QVBoxLayout()
    brand_text.setSpacing(0)
    brand_title = QLabel('EXTRATOR')
    brand_title.setObjectName('BrandTitle')
    brand_subtitle = QLabel('DE VÍDEOS')
    brand_subtitle.setObjectName('BrandSubtitle')
    brand_text.addWidget(brand_title)
    brand_text.addWidget(brand_subtitle)
    brand_row.addLayout(brand_text, 1)
    sidebar_layout.addLayout(brand_row)
    sidebar_layout.addSpacing(16)

    self.nav_group = QButtonGroup(self)
    self.nav_group.setExclusive(True)
    self.nav_download = _make_nav_button('⬇  Baixar', 'Abrir área de download')
    self.nav_editor = _make_nav_button('✂  Editor / Timeline', 'Abrir editor de vídeo e timeline')
    self.nav_proxy = _make_nav_button('◎  Proxy', 'Abrir configurações de proxy')
    for b in (self.nav_download, self.nav_editor, self.nav_proxy):
        self.nav_group.addButton(b)
        sidebar_layout.addWidget(b)
    self.nav_download.setChecked(True)

    sidebar_layout.addStretch(1)

    sidebar_folder = QPushButton('▣  Abrir pasta de vídeos')
    sidebar_folder.setObjectName('SidebarAction')
    sidebar_folder.setAccessibleName('Abrir pasta onde os vídeos são salvos')
    sidebar_folder.setCursor(Qt.CursorShape.PointingHandCursor)
    sidebar_folder.clicked.connect(self.open_videos_folder)
    sidebar_layout.addWidget(sidebar_folder)

    status_card = QFrame()
    status_card.setObjectName('StatusCard')
    status_row = QHBoxLayout(status_card)
    status_row.setContentsMargins(11, 8, 11, 8)
    status_row.setSpacing(7)
    dot = QLabel('●')
    dot.setObjectName('StatusDot')
    ready = QLabel('Pronto para usar')
    ready.setObjectName('StatusText')
    status_row.addWidget(dot)
    status_row.addWidget(ready, 1)
    sidebar_layout.addWidget(status_card)

    version = QLabel('v1.9.16  •  MODERN UI')
    version.setObjectName('VersionBadge')
    version.setAlignment(Qt.AlignmentFlag.AlignCenter)
    sidebar_layout.addWidget(version)

    root_layout.addWidget(sidebar)

    # ---------------- Conteúdo ----------------
    content = QFrame()
    content.setObjectName('ContentArea')
    content_layout = QVBoxLayout(content)
    content_layout.setContentsMargins(0, 0, 0, 0)
    content_layout.setSpacing(0)

    topbar = QFrame()
    topbar.setObjectName('TopBar')
    topbar_layout = QHBoxLayout(topbar)
    topbar_layout.setContentsMargins(24, 14, 24, 14)
    topbar_layout.setSpacing(14)

    head_text = QVBoxLayout()
    head_text.setSpacing(1)
    self.modern_page_title = QLabel('Baixar vídeo')
    self.modern_page_title.setObjectName('HeaderTitle')
    self.modern_page_subtitle = QLabel('Cole um link, escolha a qualidade e acompanhe o download.')
    self.modern_page_subtitle.setObjectName('HeaderSubtitle')
    head_text.addWidget(self.modern_page_title)
    head_text.addWidget(self.modern_page_subtitle)
    topbar_layout.addLayout(head_text, 1)

    self.connection_badge = QLabel('● CONEXÃO DIRETA')
    self.connection_badge.setObjectName('StatusBadge')
    self.connection_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
    self.connection_badge.setMinimumWidth(165)
    topbar_layout.addWidget(self.connection_badge)

    content_layout.addWidget(topbar)

    self.modern_stack = QStackedWidget()
    content_layout.addWidget(self.modern_stack, 1)
    root_layout.addWidget(content, 1)

    # ---------------- Página Download ----------------
    download_scroll = QScrollArea()
    download_scroll.setObjectName('PageScroll')
    download_scroll.setWidgetResizable(True)
    download_page = QWidget()
    download_scroll.setWidget(download_page)
    page_layout = QVBoxLayout(download_page)
    page_layout.setContentsMargins(24, 22, 24, 24)
    page_layout.setSpacing(14)

    hero = QFrame()
    hero.setObjectName('HeroCard')
    hero_layout = _card_layout(hero, (20, 17, 20, 17), 6)
    kicker = QLabel('VIDEO TOOLKIT  •  WINDOWS PORTABLE')
    kicker.setObjectName('HeroKicker')
    hero_title = QLabel('Baixe, edite e exporte em um único fluxo')
    hero_title.setObjectName('HeroTitle')
    hero_text = QLabel('Interface simplificada, editor de timeline com precisão de milissegundos e compressão inteligente H.264 / H.265.')
    hero_text.setObjectName('HeroText')
    hero_text.setWordWrap(True)
    hero_layout.addWidget(kicker)
    hero_layout.addWidget(hero_title)
    hero_layout.addWidget(hero_text)
    page_layout.addWidget(hero)

    download_card = QFrame()
    download_card.setObjectName('DownloadCard')
    d = _card_layout(download_card)
    card_title = QLabel('Baixar vídeo')
    card_title.setObjectName('CardTitle')
    card_hint = QLabel('Cole um endereço compatível e escolha a qualidade de saída.')
    card_hint.setObjectName('CardHint')
    d.addWidget(card_title)
    d.addWidget(card_hint)

    url_row = QHBoxLayout()
    url_row.setSpacing(10)
    self.url_edit = QLineEdit()
    self.url_edit.setObjectName('UrlInput')
    self.url_edit.setPlaceholderText('Cole o link do vídeo aqui…')
    self.url_edit.setAccessibleName('Link do vídeo')
    self.url_edit.setClearButtonEnabled(True)
    url_row.addWidget(self.url_edit, 1)
    self.btn_download = QPushButton('⬇  BAIXAR')
    self.btn_download.setObjectName('PrimaryDownload')
    self.btn_download.setAccessibleName('Iniciar download do vídeo')
    self.btn_download.setCursor(Qt.CursorShape.PointingHandCursor)
    url_row.addWidget(self.btn_download)
    d.addLayout(url_row)

    options = QHBoxLayout()
    options.setSpacing(10)
    options.addWidget(QLabel('Qualidade'))
    self.quality_combo = QComboBox()
    self.quality_combo.addItems(core.QUALIDADES)
    self.quality_combo.setCurrentIndex(2)
    self.quality_combo.setMinimumWidth(200)
    self.quality_combo.setAccessibleName('Qualidade do vídeo')
    options.addWidget(self.quality_combo)
    options.addStretch(1)
    self.btn_update = QPushButton('↻ Atualizar yt-dlp')
    self.btn_update.setProperty('role', 'tool')
    self.btn_update.setToolTip('Atualiza o motor de download yt-dlp')
    self.btn_folder = QPushButton('▣ Abrir pasta')
    self.btn_folder.setProperty('role', 'tool')
    self.btn_folder.setToolTip('Abre a pasta onde os vídeos são salvos')
    self.btn_cancel = QPushButton('Cancelar')
    self.btn_cancel.setProperty('role', 'danger')
    self.btn_cancel.setEnabled(False)
    options.addWidget(self.btn_update)
    options.addWidget(self.btn_folder)
    options.addWidget(self.btn_cancel)
    d.addLayout(options)
    page_layout.addWidget(download_card)

    progress_card = QFrame()
    progress_card.setObjectName('ProgressCard')
    pr_layout = _card_layout(progress_card)
    progress_head = QHBoxLayout()
    progress_title = QLabel('Progresso do download')
    progress_title.setObjectName('CardTitle')
    self.download_percent = QLabel('0%')
    self.download_percent.setObjectName('PlayheadBadge')
    progress_head.addWidget(progress_title)
    progress_head.addStretch(1)
    progress_head.addWidget(self.download_percent)
    pr_layout.addLayout(progress_head)
    self.download_progress = QProgressBar()
    self.download_progress.setObjectName('DownloadProgress')
    self.download_progress.setRange(0, 100)
    self.download_progress.setFormat('%p%')
    pr_layout.addWidget(self.download_progress)
    self.download_status = QLabel('Aguardando link. Escolha a qualidade e inicie o download.')
    self.download_status.setWordWrap(True)
    self.download_status.setObjectName('HeroText')
    pr_layout.addWidget(self.download_status)
    self.binary_status = QLabel('')
    self.binary_status.setWordWrap(True)
    self.binary_status.setObjectName('InfoBanner')
    pr_layout.addWidget(self.binary_status)
    page_layout.addWidget(progress_card)

    features = QHBoxLayout()
    features.setSpacing(10)
    features.addWidget(_make_feature('↓', 'Download rápido', 'Qualidade selecionável'))
    features.addWidget(_make_feature('✂', 'Timeline precisa', 'Cortes em milissegundos'))
    features.addWidget(_make_feature('⛓', 'Unir vídeos', 'Organize e combine clipes'))
    features.addWidget(_make_feature('HD', 'Compressão inteligente', 'H.264 e H.265 / HEVC'))
    page_layout.addLayout(features)

    editor_hint = QLabel('DICA  •  Depois do download, abra “Editor / Timeline” para cortar, excluir trechos, reordenar, unir e exportar.')
    editor_hint.setObjectName('InfoBanner')
    editor_hint.setWordWrap(True)
    page_layout.addWidget(editor_hint)
    page_layout.addStretch(1)
    self.modern_stack.addWidget(download_scroll)

    # ---------------- Página Editor ----------------
    editor_scroll = QScrollArea()
    editor_scroll.setObjectName('PageScroll')
    editor_scroll.setWidgetResizable(True)
    self.editor_page = core.AdvancedVideoEditorWidget(core.VIDEOS_DIR, core.FFMPEG_EXE, core.FFPROBE_EXE, self)
    editor_scroll.setWidget(self.editor_page)
    self.modern_stack.addWidget(editor_scroll)

    # ---------------- Página Proxy ----------------
    proxy_scroll = QScrollArea()
    proxy_scroll.setObjectName('PageScroll')
    proxy_scroll.setWidgetResizable(True)
    proxy_page = QWidget()
    proxy_scroll.setWidget(proxy_page)
    p = QVBoxLayout(proxy_page)
    p.setContentsMargins(24, 22, 24, 24)
    p.setSpacing(14)

    proxy_intro = QFrame()
    proxy_intro.setObjectName('HeroCard')
    pi = _card_layout(proxy_intro, (20, 17, 20, 17), 5)
    pk = QLabel('REDE E CONECTIVIDADE')
    pk.setObjectName('HeroKicker')
    pt = QLabel('Conexão direta ou proxy')
    pt.setObjectName('HeroTitle')
    pd = QLabel('Use conexão direta normalmente. Ative o proxy apenas quando a rede exigir. Usuário e senha permanecem somente nesta sessão.')
    pd.setObjectName('HeroText')
    pd.setWordWrap(True)
    pi.addWidget(pk)
    pi.addWidget(pt)
    pi.addWidget(pd)
    p.addWidget(proxy_intro)

    mode = QGroupBox('Modo de conexão')
    ml = QVBoxLayout(mode)
    self.radio_direct = QRadioButton('Conexão direta — recomendada quando disponível')
    self.radio_proxy = QRadioButton('Usar proxy')
    ml.addWidget(self.radio_direct)
    ml.addWidget(self.radio_proxy)
    p.addWidget(mode)

    box = QGroupBox('Dados do proxy')
    formp = QFormLayout(box)
    formp.setHorizontalSpacing(14)
    formp.setVerticalSpacing(10)
    self.proxy_server = QLineEdit(); self.proxy_server.setPlaceholderText('Ex.: proxy.empresa.local ou 10.0.0.10')
    self.proxy_port = QLineEdit(); self.proxy_port.setPlaceholderText('Ex.: 8080')
    self.proxy_user = QLineEdit(); self.proxy_user.setPlaceholderText('Usuário, se exigido')
    self.proxy_password = QLineEdit(); self.proxy_password.setEchoMode(QLineEdit.EchoMode.Password); self.proxy_password.setPlaceholderText('Senha — não é salva')
    formp.addRow('Servidor:', self.proxy_server)
    formp.addRow('Porta:', self.proxy_port)
    formp.addRow('Usuário:', self.proxy_user)
    formp.addRow('Senha:', self.proxy_password)
    p.addWidget(box)

    proxy_buttons = QHBoxLayout()
    self.btn_save_proxy = QPushButton('Salvar configuração')
    self.btn_save_proxy.setProperty('role', 'primary')
    self.btn_clear_proxy = QPushButton('Usar conexão direta')
    self.btn_clear_proxy.setProperty('role', 'tool')
    proxy_buttons.addWidget(self.btn_save_proxy)
    proxy_buttons.addWidget(self.btn_clear_proxy)
    proxy_buttons.addStretch(1)
    p.addLayout(proxy_buttons)
    self.proxy_status = QLabel('Conexão atual: DIRETA')
    self.proxy_status.setObjectName('InfoBanner')
    self.proxy_status.setWordWrap(True)
    p.addWidget(self.proxy_status)
    p.addStretch(1)
    self.modern_stack.addWidget(proxy_scroll)

    # ---------------- Navegação e sinais ----------------
    def change_page(index, title, subtitle):
        self.modern_stack.setCurrentIndex(index)
        self.modern_page_title.setText(title)
        self.modern_page_subtitle.setText(subtitle)

    self.nav_download.clicked.connect(lambda: change_page(0, 'Baixar vídeo', 'Cole um link, escolha a qualidade e acompanhe o download.'))
    self.nav_editor.clicked.connect(lambda: change_page(1, 'Editor / Timeline', 'Corte, exclua trechos, una clipes e exporte com precisão.'))
    self.nav_proxy.clicked.connect(lambda: change_page(2, 'Proxy', 'Configure a conexão somente quando a rede exigir.'))

    self.btn_download.clicked.connect(self.download_video)
    self.btn_cancel.clicked.connect(self.cancel_download)
    self.btn_update.clicked.connect(self.update_ytdlp)
    self.btn_folder.clicked.connect(self.open_videos_folder)
    self.btn_save_proxy.clicked.connect(self.save_proxy_settings)
    self.btn_clear_proxy.clicked.connect(self.use_direct_connection)
    self.radio_direct.toggled.connect(self._proxy_mode_changed)
    self.radio_proxy.toggled.connect(self._proxy_mode_changed)

    self.url_edit.returnPressed.connect(self.download_video)


# Mantém toda a lógica original e troca somente a construção visual da janela principal.
core.MainWindow._build_ui = build_modern_ui


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(core.APP_NAME)
    app.setOrganizationName('ExtratorVideos')
    app.setStyle('Fusion')
    app.setStyleSheet(core.FUTURE_STYLESHEET)
    app.setWindowIcon(_app_icon())
    window = core.MainWindow()
    window.setWindowIcon(_app_icon())
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
