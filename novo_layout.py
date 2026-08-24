import main as core

# Novo visual v1.9.14. O motor e as funções continuam vindo integralmente da v1.9.13.
core.APP_VERSION = 'Windows Portable v1.9.14 — Novo Layout — Timeline + compressão inteligente'

core.FUTURE_STYLESHEET = r"""
QWidget {
    background-color: #080912;
    color: #F4F5FF;
    font-family: "Segoe UI";
    font-size: 10pt;
}
QMainWindow, QScrollArea, QScrollArea > QWidget > QWidget {
    background-color: #080912;
}
QScrollArea { border: none; }

QLabel#AppTitle, QLabel#EditorTitle, QLabel#PageTitle {
    color: #FFFFFF;
    font-size: 21pt;
    font-weight: 750;
}
QLabel#Subtitle {
    color: #9B9DB4;
    font-size: 10pt;
}
QLabel#StatusBadge {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #251A4A, stop:0.52 #1B2356, stop:1 #152B55);
    color: #C8BBFF;
    border: 1px solid #5548A7;
    border-radius: 11px;
    padding: 5px 11px;
    font-weight: 700;
}
QLabel#InfoBanner {
    background-color: #10111E;
    color: #B8BAD0;
    border: 1px solid #26283C;
    border-left: 3px solid #7B55FF;
    border-radius: 12px;
    padding: 11px 13px;
}
QLabel#MetricCard {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                stop:0 #141523, stop:1 #10111B);
    color: #F0F1FA;
    border: 1px solid #292B40;
    border-radius: 14px;
    padding: 11px 15px;
    font-size: 10pt;
    font-weight: 650;
}
QLabel#MetricCard[accent="true"] {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #23194A, stop:1 #172148);
    color: #D7CEFF;
    border: 1px solid #5548A7;
}

QGroupBox {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                stop:0 #11121F, stop:0.55 #10111C, stop:1 #0D0E18);
    border: 1px solid #27293C;
    border-radius: 18px;
    margin-top: 16px;
    padding: 17px 14px 14px 14px;
    font-weight: 700;
    color: #F2F2FB;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 16px;
    padding: 0 8px;
    color: #B8A7FF;
    background-color: #11121F;
}

QLineEdit, QComboBox {
    background-color: #0B0C15;
    color: #F6F6FC;
    border: 1px solid #303247;
    border-radius: 11px;
    padding: 9px 11px;
    min-height: 20px;
    selection-background-color: #6547E8;
}
QLineEdit:hover, QComboBox:hover { border-color: #484B67; }
QLineEdit:focus, QComboBox:focus {
    border: 1px solid #7A59FF;
    background-color: #0E0F1A;
}
QLineEdit:disabled, QComboBox:disabled {
    background-color: #10111A;
    color: #5F6174;
    border-color: #1E2030;
}
QComboBox::drop-down { border: none; width: 26px; }
QComboBox QAbstractItemView {
    background-color: #11121E;
    color: #F2F2FA;
    border: 1px solid #36384E;
    selection-background-color: #4934A5;
    selection-color: white;
    outline: 0;
}

QPushButton {
    background-color: #151623;
    color: #E8E8F3;
    border: 1px solid #323449;
    border-radius: 11px;
    padding: 9px 13px;
    font-weight: 650;
    min-height: 20px;
}
QPushButton:hover {
    background-color: #1C1D2C;
    border-color: #555873;
}
QPushButton:pressed { background-color: #10111B; }
QPushButton:disabled {
    background-color: #10111A;
    color: #555769;
    border-color: #1F2130;
}
QPushButton[role="primary"] {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #8A38EA, stop:0.48 #6A43F0, stop:1 #2E72FF);
    color: #FFFFFF;
    border: 1px solid #8A6DFF;
    font-weight: 750;
}
QPushButton[role="primary"]:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #9A49F3, stop:0.48 #7651FF, stop:1 #3B7FFF);
    border-color: #A996FF;
}
QPushButton[role="danger"] {
    background-color: #2A141D;
    color: #FFB5C3;
    border: 1px solid #733044;
}
QPushButton[role="danger"]:hover { background-color: #3B1825; }
QPushButton[role="success"] {
    background-color: #10281F;
    color: #9FE4C1;
    border: 1px solid #275C49;
}

QProgressBar {
    background-color: #0B0C14;
    color: #ECECF7;
    border: 1px solid #282A3E;
    border-radius: 9px;
    text-align: center;
    min-height: 18px;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #8A38EA, stop:0.5 #6C48F5, stop:1 #2E72FF);
    border-radius: 8px;
}

QTabWidget::pane {
    border: none;
    background-color: #080912;
    top: -1px;
}
QTabBar::tab {
    background-color: #10111C;
    color: #82849A;
    border: 1px solid #25273A;
    padding: 11px 22px;
    margin-right: 6px;
    border-radius: 11px;
    min-width: 118px;
}
QTabBar::tab:selected {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #271C52, stop:1 #17234A);
    color: #E2DCFF;
    border-color: #5B4AB7;
}
QTabBar::tab:hover { color: #FFFFFF; border-color: #464961; }

QListWidget {
    background-color: #0B0C14;
    color: #E8E8F3;
    border: 1px solid #2B2D41;
    border-radius: 12px;
    padding: 6px;
    outline: 0;
}
QListWidget::item {
    background-color: #12131F;
    border: 1px solid #24263A;
    border-radius: 9px;
    padding: 9px;
    margin: 3px;
}
QListWidget::item:selected {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #2B2057, stop:1 #18264D);
    border-color: #6E55DD;
    color: #FFFFFF;
}

QRadioButton, QCheckBox { spacing: 8px; color: #DEDFEA; }
QRadioButton::indicator, QCheckBox::indicator { width: 17px; height: 17px; }
QRadioButton::indicator:unchecked, QCheckBox::indicator:unchecked {
    background-color: #0C0D16;
    border: 1px solid #55586E;
}
QRadioButton::indicator:checked, QCheckBox::indicator:checked {
    background-color: #6E4EF1;
    border: 1px solid #A18BFF;
}

QSlider::groove:horizontal {
    height: 7px;
    background: #202234;
    border-radius: 3px;
}
QSlider::sub-page:horizontal {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #8A38EA, stop:1 #2E72FF);
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #F7F4FF;
    border: 2px solid #7A59FF;
    width: 17px;
    margin: -6px 0;
    border-radius: 8px;
}

QScrollBar:horizontal, QScrollBar:vertical {
    background: #090A12;
    border: none;
    margin: 0;
}
QScrollBar:horizontal { height: 10px; }
QScrollBar:vertical { width: 10px; }
QScrollBar::handle:horizontal, QScrollBar::handle:vertical {
    background: #33354A;
    border-radius: 5px;
    min-width: 28px;
    min-height: 28px;
}
QScrollBar::handle:horizontal:hover, QScrollBar::handle:vertical:hover { background: #4B4E68; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }

QVideoWidget {
    background-color: #020207;
    border: 1px solid #282A3E;
    border-radius: 14px;
}
QMessageBox { background-color: #10111C; }
QToolTip {
    background-color: #171824;
    color: #FFFFFF;
    border: 1px solid #45475D;
    padding: 6px;
}
"""

if __name__ == '__main__':
    core.main()
