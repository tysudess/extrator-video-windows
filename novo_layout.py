import main as core

# Visual v1.9.15 Timeline Premium. O motor e as funções continuam preservados da base funcional anterior.
core.APP_VERSION = 'Windows Portable v1.9.15 — Timeline Premium — controles integrados + compressão inteligente'

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
QLabel { background-color: transparent; }

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
QWidget#TimelinePrecisionPanel {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                stop:0 #0F1020, stop:0.55 #111329, stop:1 #0C1323);
    border: 1px solid #323653;
    border-radius: 15px;
}
QLabel#SectionKicker {
    color: #8F93AF;
    font-size: 8pt;
    font-weight: 750;
    letter-spacing: 1px;
}
QLabel#TimelineSelectedClip {
    color: #FFFFFF;
    font-size: 11pt;
    font-weight: 750;
}
QLabel#TimelineClipInfo {
    color: #979AB3;
    font-size: 9pt;
}
QLabel#PlayheadBadge, QLabel#ZoomBadge {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #1B1740, stop:1 #14254B);
    color: #DCD7FF;
    border: 1px solid #4A4E82;
    border-radius: 10px;
    padding: 6px 10px;
    font-size: 9pt;
    font-weight: 700;
}
QLabel#FieldTag {
    background-color: #191A2B;
    color: #BEB6F8;
    border: 1px solid #343650;
    border-radius: 8px;
    padding: 7px 9px;
    font-size: 8pt;
    font-weight: 800;
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
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                stop:0 #1A1B2A, stop:1 #12131F);
    color: #ECECF7;
    border: 1px solid #373A53;
    border-radius: 12px;
    padding: 9px 14px;
    font-weight: 700;
    min-height: 22px;
}
QPushButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                stop:0 #24263A, stop:1 #181A2A);
    border-color: #65698B;
    color: #FFFFFF;
}
QPushButton:pressed {
    background-color: #0E0F18;
    border-color: #4E5272;
    padding-top: 10px;
    padding-bottom: 8px;
}
QPushButton:disabled {
    background-color: #10111A;
    color: #555769;
    border-color: #1F2130;
}
QPushButton[role="primary"] {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #A43AF0, stop:0.45 #7447F4, stop:1 #2E79FF);
    color: #FFFFFF;
    border: 1px solid #A98BFF;
    font-weight: 800;
    min-height: 25px;
}
QPushButton[role="primary"]:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #B34BFA, stop:0.45 #8258FF, stop:1 #4388FF);
    border-color: #D0C0FF;
}
QPushButton[role="tool"] {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #191B2A, stop:1 #121420);
    color: #D7D9E8;
    border-color: #343750;
}
QPushButton[role="tool"]:hover {
    background-color: #222537;
    border-color: #656A8E;
    color: #FFFFFF;
}
QPushButton[role="accent"] {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #241B48, stop:1 #172B55);
    color: #DDD6FF;
    border: 1px solid #6554C7;
}
QPushButton[role="accent"]:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #32235F, stop:1 #1D376A);
    border-color: #927BFF;
    color: #FFFFFF;
}
QPushButton[role="danger"] {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #30151F, stop:1 #25141C);
    color: #FFC1CE;
    border: 1px solid #7B334A;
}
QPushButton[role="danger"]:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #461B2A, stop:1 #321722);
    border-color: #AF4B69;
    color: #FFE6EB;
}
QPushButton[role="success"] {
    background-color: #10281F;
    color: #9FE4C1;
    border: 1px solid #275C49;
}
QPushButton[role="nudge"] {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #191A2B, stop:1 #11121D);
    color: #C9CBE0;
    border: 1px solid #353852;
    border-radius: 10px;
    padding: 6px 10px;
    min-width: 54px;
    min-height: 18px;
    font-size: 9pt;
    font-weight: 700;
}
QPushButton[role="nudge"]:hover {
    background-color: #252741;
    color: #FFFFFF;
    border-color: #7668C9;
}
QPushButton[role="mark"] {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #1C183C, stop:1 #142442);
    color: #D8D2FF;
    border: 1px solid #514E88;
    border-radius: 11px;
    padding: 7px 12px;
    min-height: 20px;
}
QPushButton[role="mark"]:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #2B2259, stop:1 #1B3157);
    border-color: #8276E6;
    color: #FFFFFF;
}
QPushButton[role="transport"] {
    background-color: #121520;
    color: #BCC0D7;
    border: 1px solid #30344D;
    min-width: 62px;
}
QPushButton[role="transport"]:hover {
    background-color: #1D2131;
    border-color: #5E6489;
    color: #FFFFFF;
}
QPushButton[role="transportPrimary"] {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #38266E, stop:1 #1C4A7D);
    color: #FFFFFF;
    border: 1px solid #6A62C8;
    min-width: 92px;
    font-weight: 800;
}
QPushButton[role="transportPrimary"]:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #4B338D, stop:1 #245F9E);
    border-color: #9A8CFF;
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
