# ui/main_window.py
import os
import sys
import time
import traceback
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTextEdit, QLabel, QFileDialog,
    QComboBox, QMessageBox, QTabWidget, QGroupBox,
    QStatusBar, QFrame, QApplication, QCheckBox,
    QSplitter, QSizePolicy, QListWidget, QListWidgetItem,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize
from PyQt6.QtGui import QFont, QAction, QKeySequence, QShortcut, QPalette, QColor, QIcon

from core.parser import AIFormatParser
from core.deployer import ProjectDeployer
from core.exporter import ProjectExporter
from core.project_scanner import ProjectScanner
from core.prompt_manager import PromptManager
from models.project import Project
from ui.localization import Localization

import logging

logger = logging.getLogger(__name__)


# ──────────────────────────── Workers ────────────────────────────

class ParseWorker(QThread):
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, text):
        super().__init__()
        self.text = text

    def run(self):
        try:
            parser = AIFormatParser()
            project = parser.parse(self.text)
            self.finished.emit(project)
        except Exception as e:
            self.error.emit(str(e) + "\n\n" + traceback.format_exc())


class DeployWorker(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, project, target_dir, overwrite):
        super().__init__()
        self.project = project
        self.target_dir = target_dir
        self.overwrite = overwrite

    def run(self):
        try:
            deployer = ProjectDeployer()
            path = deployer.deploy(self.project, self.target_dir, self.overwrite)
            self.finished.emit(path)
        except Exception as e:
            self.error.emit(str(e))


class ExportPDFWorker(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, project, output_path):
        super().__init__()
        self.project = project
        self.output_path = output_path

    def run(self):
        try:
            exporter = ProjectExporter()
            exporter.export_pdf(self.project, self.output_path)
            self.finished.emit(self.output_path)
        except Exception as e:
            self.error.emit(str(e))


# ──────────────────────────── Theme ────────────────────────────

DARK_STYLE = """
/* ═══ Main Window ═══ */
QMainWindow {
    background-color: #1a1b26;
}
QWidget {
    background-color: #1a1b26;
    color: #c0caf5;
    font-family: 'Segoe UI', 'SF Pro Display', 'Helvetica Neue', Arial, sans-serif;
    font-size: 13px;
}

/* ═══ Header Frame ═══ */
QFrame#headerFrame {
    background-color: #16161e;
    border-bottom: 1px solid #292e42;
}
QFrame#headerFrame QLabel {
    background: transparent;
    color: #7aa2f7;
    font-weight: bold;
    font-size: 14px;
}
QFrame#headerFrame QPushButton {
    background: transparent;
    border: none;
    color: #a9b1d6;
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 12px;
}
QFrame#headerFrame QPushButton:hover {
    background-color: #292e42;
    color: #c0caf5;
}

/* ═══ Directory Selector ═══ */
QComboBox#dirCombo {
    background-color: #1a1b26;
    border: 1px solid #292e42;
    border-radius: 4px;
    padding: 5px 10px;
    color: #a9b1d6;
    min-height: 24px;
    font-size: 12px;
}
QComboBox#dirCombo:hover {
    border-color: #414868;
}
QComboBox#dirCombo:focus {
    border-color: #7aa2f7;
}
QComboBox#dirCombo::drop-down {
    border: none;
    width: 24px;
}
QComboBox#dirCombo::down-arrow {
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid #565f89;
    margin-right: 8px;
}
QComboBox QAbstractItemView {
    background-color: #24283b;
    color: #c0caf5;
    selection-background-color: #414868;
    border: 1px solid #292e42;
    outline: none;
}

/* ═══ Tab Bar ═══ */
QTabWidget::pane {
    border: none;
    background: #1a1b26;
}
QTabBar {
    background: #1a1b26;
    border-bottom: 1px solid #292e42;
}
QTabBar::tab {
    padding: 8px 20px;
    font-size: 13px;
    font-weight: 600;
    border: none;
    border-bottom: 2px solid transparent;
    margin-right: 0px;
    background: transparent;
    color: #565f89;
}
QTabBar::tab:selected {
    color: #7aa2f7;
    border-bottom: 2px solid #7aa2f7;
    background: rgba(122, 162, 247, 0.05);
}
QTabBar::tab:hover:!selected {
    color: #a9b1d6;
    background: rgba(41, 46, 66, 0.5);
}

/* ═══ Quick Actions Bar ═══ */
QFrame#quickActionsBar {
    background-color: #1a1b26;
    border-bottom: 1px solid #292e42;
}
QFrame#quickActionsBar QLabel {
    background: transparent;
    color: #565f89;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1px;
}
QFrame#quickActionsBar QPushButton {
    background-color: #414868;
    color: #c0caf5;
    border: none;
    padding: 5px 12px;
    border-radius: 4px;
    font-size: 12px;
    font-weight: 500;
}
QFrame#quickActionsBar QPushButton:hover {
    background-color: #535d82;
}

/* ═══ Code Editor / Input Area ═══ */
QTextEdit#inputText {
    background-color: #1a1b26;
    color: #a9b1d6;
    border: none;
    border-right: 1px solid #292e42;
    padding: 12px;
    font-family: 'Consolas', 'Fira Code', 'JetBrains Mono', 'Courier New', monospace;
    font-size: 12px;
    selection-background-color: rgba(86, 95, 137, 0.4);
    line-height: 1.6;
}
QTextEdit#inputText:focus {
    border-right: 1px solid #292e42;
}

/* ═══ Results Panel ═══ */
QFrame#resultsPanel {
    background-color: #24283b;
    border: none;
}
QFrame#resultsPanelHeader {
    background-color: #1f2335;
    border-bottom: 1px solid #292e42;
}
QFrame#resultsPanelHeader QLabel {
    background: transparent;
    color: #a9b1d6;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1px;
}
QTextEdit#resultText {
    background-color: #24283b;
    color: #a9b1d6;
    border: none;
    padding: 12px;
    font-family: 'Consolas', 'Fira Code', 'JetBrains Mono', 'Courier New', monospace;
    font-size: 12px;
    selection-background-color: rgba(86, 95, 137, 0.4);
}

/* ═══ Bottom Action Bar ═══ */
QFrame#bottomBar {
    background-color: #1f2335;
    border-top: 1px solid #292e42;
}
QFrame#bottomBar QLabel {
    background: transparent;
    color: #565f89;
    font-size: 12px;
}

/* ═══ Primary Button ═══ */
QPushButton#btnPrimary {
    background-color: #7aa2f7;
    color: #1a1b26;
    border: none;
    padding: 8px 20px;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 600;
    min-width: 120px;
}
QPushButton#btnPrimary:hover {
    background-color: #5d8eea;
}
QPushButton#btnPrimary:pressed {
    background-color: #4c7bd4;
}
QPushButton#btnPrimary:disabled {
    background-color: #414868;
    color: #565f89;
}

/* ═══ Secondary Button ═══ */
QPushButton#btnSecondary {
    background-color: transparent;
    color: #a9b1d6;
    border: none;
    padding: 8px 16px;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 500;
}
QPushButton#btnSecondary:hover {
    background-color: #292e42;
    color: #c0caf5;
}

/* ═══ Success Button ═══ */
QPushButton#btnSuccess {
    background-color: #9ece6a;
    color: #1a1b26;
    border: none;
    padding: 8px 20px;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 600;
}
QPushButton#btnSuccess:hover {
    background-color: #89b856;
}

/* ═══ Danger Button ═══ */
QPushButton#btnDanger {
    background-color: #f7768e;
    color: #1a1b26;
    border: none;
    padding: 8px 20px;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 600;
}
QPushButton#btnDanger:hover {
    background-color: #e0606e;
}

/* ═══ Export Tab ═══ */
QFrame#exportPanel {
    background: #24283b;
    border: 1px solid #292e42;
    border-radius: 8px;
}

QListWidget {
    background-color: #1a1b26;
    color: #a9b1d6;
    border: 1px solid #292e42;
    border-radius: 6px;
    padding: 4px;
    outline: none;
    font-size: 12px;
}
QListWidget::item {
    padding: 8px 12px;
    border-radius: 4px;
    margin: 2px 0;
}
QListWidget::item:selected {
    background-color: rgba(122, 162, 247, 0.15);
    color: #7aa2f7;
}
QListWidget::item:hover:!selected {
    background-color: #292e42;
}

/* ═══ Help Tab ═══ */
QTextEdit#helpText {
    background-color: #1a1b26;
    color: #a9b1d6;
    border: none;
    padding: 24px;
    font-size: 13px;
    line-height: 1.6;
}

/* ═══ Check Box ═══ */
QCheckBox {
    color: #a9b1d6;
    font-size: 12px;
    spacing: 6px;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 2px solid #414868;
    border-radius: 4px;
    background: #1a1b26;
}
QCheckBox::indicator:checked {
    background: #7aa2f7;
    border-color: #7aa2f7;
}
QCheckBox::indicator:hover {
    border-color: #7aa2f7;
}

/* ═══ Status Bar ═══ */
QStatusBar {
    background: #7aa2f7;
    border: none;
    min-height: 22px;
    max-height: 22px;
}
QStatusBar QLabel {
    color: #1a1b26;
    font-size: 11px;
    font-weight: 600;
    padding: 0 6px;
    background: transparent;
}

/* ═══ Scrollbar ═══ */
QScrollBar:vertical {
    background: #1a1b26;
    width: 10px;
    border: none;
}
QScrollBar::handle:vertical {
    background: #414868;
    border-radius: 5px;
    min-height: 20px;
    border: 2px solid #1a1b26;
}
QScrollBar::handle:vertical:hover {
    background: #565f89;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar:horizontal {
    background: #1a1b26;
    height: 10px;
    border: none;
}
QScrollBar::handle:horizontal {
    background: #414868;
    border-radius: 5px;
    min-width: 20px;
    border: 2px solid #1a1b26;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}

/* ═══ Splitter ═══ */
QSplitter::handle {
    background: #292e42;
}
QSplitter::handle:horizontal {
    width: 1px;
}
QSplitter::handle:vertical {
    height: 1px;
}

/* ═══ Message Box ═══ */
QMessageBox {
    background-color: #24283b;
    color: #c0caf5;
}
QMessageBox QPushButton {
    background-color: #414868;
    color: #c0caf5;
    border: none;
    padding: 6px 16px;
    border-radius: 4px;
    min-width: 80px;
}
QMessageBox QPushButton:hover {
    background-color: #535d82;
}

/* ═══ Group Box (Export) ═══ */
QGroupBox {
    font-weight: 600;
    font-size: 12px;
    border: 1px solid #292e42;
    border-radius: 8px;
    margin-top: 12px;
    padding: 16px 12px 12px 12px;
    background-color: #24283b;
    color: #a9b1d6;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: #a9b1d6;
}

/* ═══ Separator ═══ */
QFrame#separator {
    background-color: #292e42;
    max-height: 1px;
    min-height: 1px;
}

/* ═══ Editor Header ═══ */
QFrame#editorHeader {
    background-color: #1f2335;
    border-bottom: 1px solid #292e42;
}
QFrame#editorHeader QLabel {
    background: transparent;
    font-size: 11px;
}
"""

LIGHT_STYLE = """
/* ═══ Main Window ═══ */
QMainWindow {
    background-color: #f0f2f5;
}
QWidget {
    background-color: #f0f2f5;
    color: #1e293b;
    font-family: 'Segoe UI', 'SF Pro Display', 'Helvetica Neue', Arial, sans-serif;
    font-size: 13px;
}

/* ═══ Header Frame ═══ */
QFrame#headerFrame {
    background-color: #ffffff;
    border-bottom: 1px solid #e2e8f0;
}
QFrame#headerFrame QLabel {
    background: transparent;
    color: #3b82f6;
    font-weight: bold;
    font-size: 14px;
}
QFrame#headerFrame QPushButton {
    background: transparent;
    border: none;
    color: #64748b;
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 12px;
}
QFrame#headerFrame QPushButton:hover {
    background-color: #f1f5f9;
    color: #1e293b;
}

/* ═══ Directory Selector ═══ */
QComboBox#dirCombo {
    background-color: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 4px;
    padding: 5px 10px;
    color: #475569;
    min-height: 24px;
    font-size: 12px;
}
QComboBox#dirCombo:hover {
    border-color: #cbd5e1;
}
QComboBox#dirCombo:focus {
    border-color: #3b82f6;
}
QComboBox#dirCombo::drop-down {
    border: none;
    width: 24px;
}
QComboBox#dirCombo::down-arrow {
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid #94a3b8;
    margin-right: 8px;
}
QComboBox QAbstractItemView {
    background-color: #ffffff;
    color: #1e293b;
    selection-background-color: #eff6ff;
    border: 1px solid #e2e8f0;
    outline: none;
}

/* ═══ Tab Bar ═══ */
QTabWidget::pane {
    border: none;
    background: #f0f2f5;
}
QTabBar {
    background: #ffffff;
    border-bottom: 1px solid #e2e8f0;
}
QTabBar::tab {
    padding: 8px 20px;
    font-size: 13px;
    font-weight: 600;
    border: none;
    border-bottom: 2px solid transparent;
    background: transparent;
    color: #94a3b8;
}
QTabBar::tab:selected {
    color: #3b82f6;
    border-bottom: 2px solid #3b82f6;
    background: rgba(59, 130, 246, 0.04);
}
QTabBar::tab:hover:!selected {
    color: #475569;
    background: #f8fafc;
}

/* ═══ Quick Actions Bar ═══ */
QFrame#quickActionsBar {
    background-color: #ffffff;
    border-bottom: 1px solid #e2e8f0;
}
QFrame#quickActionsBar QLabel {
    background: transparent;
    color: #94a3b8;
    font-size: 11px;
    font-weight: 600;
}
QFrame#quickActionsBar QPushButton {
    background-color: #f1f5f9;
    color: #475569;
    border: 1px solid #e2e8f0;
    padding: 5px 12px;
    border-radius: 4px;
    font-size: 12px;
    font-weight: 500;
}
QFrame#quickActionsBar QPushButton:hover {
    background-color: #e2e8f0;
    color: #1e293b;
}

/* ═══ Code Editor / Input Area ═══ */
QTextEdit#inputText {
    background-color: #ffffff;
    color: #334155;
    border: none;
    border-right: 1px solid #e2e8f0;
    padding: 12px;
    font-family: 'Consolas', 'Fira Code', 'JetBrains Mono', 'Courier New', monospace;
    font-size: 12px;
    selection-background-color: rgba(59, 130, 246, 0.2);
}

/* ═══ Results Panel ═══ */
QFrame#resultsPanel {
    background-color: #f8fafc;
    border: none;
}
QFrame#resultsPanelHeader {
    background-color: #f1f5f9;
    border-bottom: 1px solid #e2e8f0;
}
QFrame#resultsPanelHeader QLabel {
    background: transparent;
    color: #475569;
    font-size: 11px;
    font-weight: 600;
}
QTextEdit#resultText {
    background-color: #f8fafc;
    color: #334155;
    border: none;
    padding: 12px;
    font-family: 'Consolas', 'Fira Code', 'JetBrains Mono', 'Courier New', monospace;
    font-size: 12px;
}

/* ═══ Bottom Action Bar ═══ */
QFrame#bottomBar {
    background-color: #f1f5f9;
    border-top: 1px solid #e2e8f0;
}
QFrame#bottomBar QLabel {
    background: transparent;
    color: #94a3b8;
    font-size: 12px;
}

/* ═══ Primary Button ═══ */
QPushButton#btnPrimary {
    background-color: #3b82f6;
    color: #ffffff;
    border: none;
    padding: 8px 20px;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 600;
    min-width: 120px;
}
QPushButton#btnPrimary:hover {
    background-color: #2563eb;
}
QPushButton#btnPrimary:pressed {
    background-color: #1d4ed8;
}
QPushButton#btnPrimary:disabled {
    background-color: #e2e8f0;
    color: #94a3b8;
}

/* ═══ Secondary Button ═══ */
QPushButton#btnSecondary {
    background-color: transparent;
    color: #64748b;
    border: none;
    padding: 8px 16px;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 500;
}
QPushButton#btnSecondary:hover {
    background-color: #f1f5f9;
    color: #1e293b;
}

/* ═══ Success Button ═══ */
QPushButton#btnSuccess {
    background-color: #22c55e;
    color: #ffffff;
    border: none;
    padding: 8px 20px;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 600;
}
QPushButton#btnSuccess:hover {
    background-color: #16a34a;
}

/* ═══ Danger Button ═══ */
QPushButton#btnDanger {
    background-color: #ef4444;
    color: #ffffff;
    border: none;
    padding: 8px 20px;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 600;
}
QPushButton#btnDanger:hover {
    background-color: #dc2626;
}

/* ═══ Export Tab ═══ */
QFrame#exportPanel {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
}

QListWidget {
    background-color: #ffffff;
    color: #334155;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    padding: 4px;
    outline: none;
    font-size: 12px;
}
QListWidget::item {
    padding: 8px 12px;
    border-radius: 4px;
    margin: 2px 0;
}
QListWidget::item:selected {
    background-color: rgba(59, 130, 246, 0.1);
    color: #3b82f6;
}
QListWidget::item:hover:!selected {
    background-color: #f8fafc;
}

/* ═══ Help Tab ═══ */
QTextEdit#helpText {
    background-color: #ffffff;
    color: #334155;
    border: none;
    padding: 24px;
    font-size: 13px;
}

/* ═══ Check Box ═══ */
QCheckBox {
    color: #64748b;
    font-size: 12px;
    spacing: 6px;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 2px solid #cbd5e1;
    border-radius: 4px;
    background: #ffffff;
}
QCheckBox::indicator:checked {
    background: #3b82f6;
    border-color: #3b82f6;
}
QCheckBox::indicator:hover {
    border-color: #3b82f6;
}

/* ═══ Status Bar ═══ */
QStatusBar {
    background: #3b82f6;
    border: none;
    min-height: 22px;
    max-height: 22px;
}
QStatusBar QLabel {
    color: #ffffff;
    font-size: 11px;
    font-weight: 600;
    padding: 0 6px;
    background: transparent;
}

/* ═══ Scrollbar ═══ */
QScrollBar:vertical {
    background: #f0f2f5;
    width: 10px;
    border: none;
}
QScrollBar::handle:vertical {
    background: #cbd5e1;
    border-radius: 5px;
    min-height: 20px;
    border: 2px solid #f0f2f5;
}
QScrollBar::handle:vertical:hover {
    background: #94a3b8;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar:horizontal {
    background: #f0f2f5;
    height: 10px;
    border: none;
}
QScrollBar::handle:horizontal {
    background: #cbd5e1;
    border-radius: 5px;
    min-width: 20px;
    border: 2px solid #f0f2f5;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}

/* ═══ Splitter ═══ */
QSplitter::handle {
    background: #e2e8f0;
}
QSplitter::handle:horizontal {
    width: 1px;
}

/* ═══ Message Box ═══ */
QMessageBox {
    background-color: #ffffff;
    color: #1e293b;
}
QMessageBox QPushButton {
    background-color: #f1f5f9;
    color: #1e293b;
    border: 1px solid #e2e8f0;
    padding: 6px 16px;
    border-radius: 4px;
    min-width: 80px;
}
QMessageBox QPushButton:hover {
    background-color: #e2e8f0;
}

/* ═══ Group Box ═══ */
QGroupBox {
    font-weight: 600;
    font-size: 12px;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    margin-top: 12px;
    padding: 16px 12px 12px 12px;
    background-color: #ffffff;
    color: #475569;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: #475569;
}

/* ═══ Separator ═══ */
QFrame#separator {
    background-color: #e2e8f0;
    max-height: 1px;
    min-height: 1px;
}

/* ═══ Editor Header ═══ */
QFrame#editorHeader {
    background-color: #f1f5f9;
    border-bottom: 1px solid #e2e8f0;
}
QFrame#editorHeader QLabel {
    background: transparent;
    font-size: 11px;
}
"""


# ──────────────────────────── Main Window ────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.loc = Localization.instance()
        self.parser = AIFormatParser()
        self.scanner = ProjectScanner()
        self.exporter = ProjectExporter()

        self.current_project = None
        self.export_project = None
        self.export_project_path = None
        self._workers = []
        self._dark_mode = True

        self._build_ui()
        self._build_shortcuts()
        self._detect_directories()
        self._apply_theme()

    def t(self, key, *args):
        return self.loc.t(key, *args)

    # ═══════════════════════ Theme ═══════════════════════

    def _apply_theme(self):
        if self._dark_mode:
            self.setStyleSheet(DARK_STYLE)
        else:
            self.setStyleSheet(LIGHT_STYLE)

    def _toggle_theme(self):
        self._dark_mode = not self._dark_mode
        self._apply_theme()
        icon = "☀️" if self._dark_mode else "🌙"
        self.theme_btn.setText(icon)

    def _toggle_language(self):
        self.loc.toggle_lang()
        self._refresh_all_texts()

    # ═══════════════════════ Build UI ═══════════════════════

    def _build_ui(self):
        self.setWindowTitle(self.t("app_title"))
        self.setMinimumSize(950, 700)
        self.resize(1200, 850)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ─── Header ───
        root.addWidget(self._build_header())

        # ─── Tabs ───
        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_import_tab(), "📥  " + self.t("tab_import"))
        self.tabs.addTab(self._build_export_tab(), "📤  " + self.t("tab_export"))
        self.tabs.addTab(self._build_help_tab(), "❓  " + self.t("tab_help"))
        root.addWidget(self.tabs)

        # ─── Status bar ───
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self._set_status("● " + self.t("ready"))

    def _build_header(self):
        header = QFrame()
        header.setObjectName("headerFrame")
        header.setFixedHeight(44)

        lay = QHBoxLayout(header)
        lay.setContentsMargins(12, 0, 12, 0)
        lay.setSpacing(8)

        # App icon & title
        title_label = QLabel("⬡  AI Code Deployer")
        title_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        lay.addWidget(title_label)

        # Separator
        sep = QFrame()
        sep.setFixedSize(1, 20)
        sep.setStyleSheet("background-color: #292e42;")
        lay.addWidget(sep)

        # Directory selector
        self.dir_combo = QComboBox()
        self.dir_combo.setObjectName("dirCombo")
        self.dir_combo.setEditable(True)
        self.dir_combo.setMinimumWidth(300)
        lay.addWidget(self.dir_combo, stretch=1)

        # Browse button
        self.btn_browse_dir = QPushButton("📁")
        self.btn_browse_dir.setToolTip(self.t("browse"))
        self.btn_browse_dir.setFixedSize(32, 32)
        self.btn_browse_dir.clicked.connect(self._on_browse_directory)
        lay.addWidget(self.btn_browse_dir)

        lay.addStretch()

        # Language toggle
        self.lang_btn = QPushButton("EN")
        self.lang_btn.setToolTip("Toggle Language")
        self.lang_btn.setFixedSize(36, 28)
        self.lang_btn.clicked.connect(self._toggle_language)
        lay.addWidget(self.lang_btn)

        # Theme toggle
        self.theme_btn = QPushButton("☀️")
        self.theme_btn.setToolTip("Toggle Theme")
        self.theme_btn.setFixedSize(32, 32)
        self.theme_btn.clicked.connect(self._toggle_theme)
        lay.addWidget(self.theme_btn)

        return header

    # ─────────────── Import Tab ───────────────

    def _build_import_tab(self):
        tab = QWidget()
        lay = QVBoxLayout(tab)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # ─── Quick Actions Bar ───
        actions_bar = QFrame()
        actions_bar.setObjectName("quickActionsBar")
        actions_bar.setFixedHeight(48)
        actions_lay = QHBoxLayout(actions_bar)
        actions_lay.setContentsMargins(12, 0, 12, 0)
        actions_lay.setSpacing(8)

        lbl = QLabel(self.t("copy_prompt_for_ai").upper())
        self.prompt_label = lbl
        actions_lay.addWidget(lbl)

        # Prompt variant buttons
        variants = PromptManager.get_all_variants()
        prompt_icons = ["✨", "⚡", "🔄", "🔧", "➕"]
        prompt_t_keys = ["prompt_full", "prompt_short", "prompt_continue", "prompt_refactor", "prompt_add_feature"]

        self.prompt_buttons = []
        for i, (key, variant) in enumerate(variants.items()):
            icon = prompt_icons[i] if i < len(prompt_icons) else "📋"
            t_key = prompt_t_keys[i] if i < len(prompt_t_keys) else variant.title
            label = self.t(t_key) if i < len(prompt_t_keys) else variant.title

            btn = QPushButton(f"{icon}  {label}")
            btn.setToolTip(variant.description)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, k=key: self._copy_prompt(k))
            actions_lay.addWidget(btn)
            self.prompt_buttons.append(btn)

        actions_lay.addStretch()
        lay.addWidget(actions_bar)

        # ─── Main content: Splitter (input | results) ───
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: input area with header
        input_container = QWidget()
        input_vlay = QVBoxLayout(input_container)
        input_vlay.setContentsMargins(0, 0, 0, 0)
        input_vlay.setSpacing(0)

        # Editor header
        editor_header = QFrame()
        editor_header.setObjectName("editorHeader")
        editor_header.setFixedHeight(28)
        eh_lay = QHBoxLayout(editor_header)
        eh_lay.setContentsMargins(12, 0, 12, 0)

        self.input_header_label = QLabel("📄  " + self.t("paste_ai_response"))
        self.input_header_label.setStyleSheet("color: #a9b1d6; font-size: 11px;")
        eh_lay.addWidget(self.input_header_label)

        eh_lay.addStretch()

        self.char_count_label = QLabel(self.t("chars_count", 0))
        self.char_count_label.setStyleSheet("color: #565f89; font-size: 11px;")
        eh_lay.addWidget(self.char_count_label)

        # Dots decoration
        for color in ["#f7768e", "#e0af68", "#9ece6a"]:
            dot = QLabel("●")
            dot.setStyleSheet(f"color: {color}; font-size: 10px; background: transparent;")
            eh_lay.addWidget(dot)

        input_vlay.addWidget(editor_header)

        # Text input
        self.input_text = QTextEdit()
        self.input_text.setObjectName("inputText")
        self.input_text.setPlaceholderText(self.t("placeholder_input"))
        self.input_text.setFont(QFont("Consolas", 11))
        self.input_text.textChanged.connect(self._on_input_changed)
        input_vlay.addWidget(self.input_text)

        splitter.addWidget(input_container)

        # Right: results panel
        results_container = QFrame()
        results_container.setObjectName("resultsPanel")
        results_vlay = QVBoxLayout(results_container)
        results_vlay.setContentsMargins(0, 0, 0, 0)
        results_vlay.setSpacing(0)

        # Results header
        results_header = QFrame()
        results_header.setObjectName("resultsPanelHeader")
        results_header.setFixedHeight(28)
        rh_lay = QHBoxLayout(results_header)
        rh_lay.setContentsMargins(12, 0, 12, 0)

        self.result_label = QLabel("📊  " + self.t("analysis_result").upper())
        rh_lay.addWidget(self.result_label)
        rh_lay.addStretch()

        results_vlay.addWidget(results_header)

        # Results text
        self.result_text = QTextEdit()
        self.result_text.setObjectName("resultText")
        self.result_text.setReadOnly(True)
        self.result_text.setFont(QFont("Consolas", 11))
        results_vlay.addWidget(self.result_text)

        splitter.addWidget(results_container)

        # Set sizes: 60% input, 40% results
        splitter.setSizes([600, 400])
        lay.addWidget(splitter, stretch=1)

        # ─── Bottom Action Bar ───
        bottom_bar = QFrame()
        bottom_bar.setObjectName("bottomBar")
        bottom_bar.setFixedHeight(56)
        bb_lay = QHBoxLayout(bottom_bar)
        bb_lay.setContentsMargins(16, 0, 16, 0)
        bb_lay.setSpacing(12)

        # Status indicator
        self.analysis_status_label = QLabel("")
        bb_lay.addWidget(self.analysis_status_label)

        bb_lay.addStretch()

        # Overwrite checkbox
        self.overwrite_check = QCheckBox(self.t("overwrite_existing"))
        bb_lay.addWidget(self.overwrite_check)

        # Clear button
        self.btn_clear = QPushButton(self.t("clear"))
        self.btn_clear.setObjectName("btnSecondary")
        self.btn_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear.clicked.connect(self._on_clear)
        bb_lay.addWidget(self.btn_clear)

        # Analyze button
        self.btn_parse = QPushButton("🔍  " + self.t("analyze"))
        self.btn_parse.setObjectName("btnSecondary")
        self.btn_parse.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_parse.setStyleSheet("""
            QPushButton {
                background-color: #414868;
                color: #c0caf5;
                border: none;
                padding: 8px 20px;
                border-radius: 6px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover { background-color: #535d82; }
        """)
        self.btn_parse.clicked.connect(self._on_analyze)
        bb_lay.addWidget(self.btn_parse)

        # Deploy button
        self.btn_deploy = QPushButton("🚀  " + self.t("create_project"))
        self.btn_deploy.setObjectName("btnPrimary")
        self.btn_deploy.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_deploy.clicked.connect(self._on_deploy)
        bb_lay.addWidget(self.btn_deploy)

        lay.addWidget(bottom_bar)

        return tab

    # ─────────────── Export Tab ───────────────

    def _build_export_tab(self):
        tab = QWidget()
        lay = QVBoxLayout(tab)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(12)

        # ─── Top: project selection ───
        sel_group = QGroupBox("📂  " + self.t("select_project_to_export"))
        self.sel_group = sel_group
        sel_lay = QVBoxLayout(sel_group)

        # Buttons row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.btn_scan = QPushButton("🔍  " + self.t("find_projects"))
        self.btn_scan.setObjectName("btnSecondary")
        self.btn_scan.setStyleSheet("""
            QPushButton {
                background-color: #414868;
                color: #c0caf5;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover { background-color: #535d82; }
        """)
        self.btn_scan.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_scan.clicked.connect(self._on_scan_projects)
        btn_row.addWidget(self.btn_scan)

        self.btn_browse_proj = QPushButton("📁  " + self.t("browse_folder"))
        self.btn_browse_proj.setObjectName("btnSecondary")
        self.btn_browse_proj.setStyleSheet("""
            QPushButton {
                background-color: #414868;
                color: #c0caf5;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover { background-color: #535d82; }
        """)
        self.btn_browse_proj.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_browse_proj.clicked.connect(self._on_browse_project)
        btn_row.addWidget(self.btn_browse_proj)

        btn_row.addStretch()

        self.btn_pdf = QPushButton("📄  " + self.t("export_pdf"))
        self.btn_pdf.setObjectName("btnPrimary")
        self.btn_pdf.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_pdf.clicked.connect(self._on_export_pdf)
        btn_row.addWidget(self.btn_pdf)

        self.btn_copy_ai = QPushButton("📋  " + self.t("copy_ai_format"))
        self.btn_copy_ai.setObjectName("btnSuccess")
        self.btn_copy_ai.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_copy_ai.clicked.connect(self._on_copy_ai_format)
        btn_row.addWidget(self.btn_copy_ai)

        sel_lay.addLayout(btn_row)

        # Project list
        self.project_list = QListWidget()
        self.project_list.setMaximumHeight(150)
        self.project_list.itemClicked.connect(self._on_project_selected)
        sel_lay.addWidget(self.project_list)

        lay.addWidget(sel_group)

        # ─── Bottom: preview ───
        preview_group = QGroupBox("📊  " + self.t("export_preview"))
        self.export_preview_label = preview_group
        preview_lay = QVBoxLayout(preview_group)

        self.export_preview = QTextEdit()
        self.export_preview.setObjectName("resultText")
        self.export_preview.setReadOnly(True)
        self.export_preview.setFont(QFont("Consolas", 11))
        preview_lay.addWidget(self.export_preview)

        lay.addWidget(preview_group, stretch=1)

        return tab

    # ─────────────── Help Tab ───────────────

    def _build_help_tab(self):
        tab = QWidget()
        lay = QVBoxLayout(tab)
        lay.setContentsMargins(0, 0, 0, 0)

        self.help_text = QTextEdit()
        self.help_text.setObjectName("helpText")
        self.help_text.setReadOnly(True)
        self.help_text.setHtml(self.t("help_content"))
        lay.addWidget(self.help_text)

        return tab

    # ═══════════════════════ Shortcuts ═══════════════════════

    def _build_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+Return"), self, self._on_analyze)
        QShortcut(QKeySequence("Ctrl+D"), self, self._on_deploy)
        QShortcut(QKeySequence("Ctrl+E"), self, self._on_export_pdf)
        QShortcut(QKeySequence("Ctrl+T"), self, self._toggle_theme)

    # ═══════════════════════ Directory ═══════════════════════

    def _detect_directories(self):
        dirs = self.scanner.find_project_directories()
        self.dir_combo.clear()
        for d in dirs:
            self.dir_combo.addItem(d)

    def _on_browse_directory(self):
        path = QFileDialog.getExistingDirectory(
            self, self.t("select_directory")
        )
        if path:
            idx = self.dir_combo.findText(path)
            if idx == -1:
                self.dir_combo.insertItem(0, path)
            self.dir_combo.setCurrentText(path)

    # ═══════════════════════ Import Actions ═══════════════════════

    def _on_input_changed(self):
        text = self.input_text.toPlainText()
        count = len(text)
        self.char_count_label.setText(self.t("chars_count", count))

    def _copy_prompt(self, variant_key):
        try:
            prompt = PromptManager.get_prompt(variant_key)
            clipboard = QApplication.clipboard()
            clipboard.setText(prompt)
            variant = PromptManager.get_variant(variant_key)
            self._set_status("✅ " + self.t("prompt_copied", variant.title))
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))

    def _on_analyze(self):
        text = self.input_text.toPlainText().strip()
        if not text:
            QMessageBox.information(
                self,
                self.t("no_text_to_analyze"),
                self.t("paste_text_first")
            )
            return

        self._set_status("⏳ " + self.t("analyzing"))
        self.btn_parse.setEnabled(False)

        worker = ParseWorker(text)
        worker.finished.connect(self._on_parse_done)
        worker.error.connect(self._on_parse_error)
        self._workers.append(worker)
        worker.start()

    def _on_parse_done(self, project):
        self.current_project = project
        self.btn_parse.setEnabled(True)

        lines = []
        lines.append(f"✅  {self.t('analysis_complete')}")
        lines.append(f"")
        lines.append(f"📦  {self.t('project_name', project.metadata.name)}")
        lines.append(f"📄  {self.t('files_count', project.file_count)}")
        lines.append(f"📏  {self.t('total_lines', project.total_lines)}")
        lines.append(f"")

        if project.metadata.language:
            lines.append(f"🔤  Language: {project.metadata.language}")
        if project.metadata.version:
            lines.append(f"🏷️  Version: {project.metadata.version}")
        if project.metadata.install_command:
            lines.append(f"📦  Install: {project.metadata.install_command}")
        if project.metadata.run_command:
            lines.append(f"▶️  Run: {project.metadata.run_command}")

        lines.append(f"")
        lines.append(f"── {self.t('file_list')} ──")
        for f in project.files:
            lang_tag = f"[{f.language}]" if f.language else ""
            loc = len(f.content.splitlines())
            lines.append(f"  📄 {f.relative_path}  {lang_tag}  ({loc} lines)")

        self.result_text.setPlainText("\n".join(lines))

        self.analysis_status_label.setText(
            f"●  {self.t('analysis_complete')}  |  {project.file_count} files"
        )
        self._set_status("✅ " + self.t("analysis_complete"))

    def _on_parse_error(self, error_msg):
        self.btn_parse.setEnabled(True)
        self.result_text.setPlainText(f"❌ {self.t('analysis_error')}:\n\n{error_msg}")
        self._set_status("❌ " + self.t("analysis_error"))

    def _on_deploy(self):
        if not self.current_project:
            QMessageBox.information(
                self,
                self.t("no_project_analyzed"),
                self.t("analyze_first")
            )
            return

        target = self.dir_combo.currentText().strip()
        if not target:
            QMessageBox.information(
                self,
                self.t("no_directory_selected"),
                self.t("select_working_directory")
            )
            return

        self._set_status("⏳ " + self.t("deploying"))
        self.btn_deploy.setEnabled(False)

        overwrite = self.overwrite_check.isChecked()
        worker = DeployWorker(self.current_project, target, overwrite)
        worker.finished.connect(self._on_deploy_done)
        worker.error.connect(self._on_deploy_error)
        self._workers.append(worker)
        worker.start()

    def _on_deploy_done(self, path):
        self.btn_deploy.setEnabled(True)
        QMessageBox.information(
            self,
            self.t("project_created"),
            self.t("project_created_at", path)
        )
        self._set_status("✅ " + self.t("project_created"))

    def _on_deploy_error(self, error_msg):
        self.btn_deploy.setEnabled(True)
        QMessageBox.critical(
            self,
            self.t("deploy_error"),
            error_msg
        )
        self._set_status("❌ " + self.t("deploy_error"))

    def _on_clear(self):
        self.input_text.clear()
        self.result_text.clear()
        self.current_project = None
        self.analysis_status_label.setText("")
        self._set_status("● " + self.t("text_cleared"))

    # ═══════════════════════ Export Actions ═══════════════════════

    def _on_scan_projects(self):
        target = self.dir_combo.currentText().strip()
        if not target or not os.path.isdir(target):
            QMessageBox.information(
                self,
                self.t("no_directory_selected"),
                self.t("select_working_directory")
            )
            return

        self._set_status("⏳ " + self.t("scanning"))
        self.project_list.clear()

        try:
            found = []
            root = Path(target)
            for item in sorted(root.iterdir()):
                if item.is_dir():
                    # Check for project indicators
                    for indicator in self.scanner.PROJECT_INDICATORS:
                        if (item / indicator).exists():
                            found.append(str(item))
                            break

            if not found:
                # Try the directory itself
                for indicator in self.scanner.PROJECT_INDICATORS:
                    if (root / indicator).exists():
                        found.append(str(root))
                        break

            for p in found:
                item = QListWidgetItem("📁  " + os.path.basename(p))
                item.setData(Qt.ItemDataRole.UserRole, p)
                self.project_list.addItem(item)

            self._set_status("✅ " + self.t("found_projects", len(found)))
        except Exception as e:
            QMessageBox.critical(self, self.t("scan_error"), str(e))
            self._set_status("❌ " + self.t("scan_error"))

    def _on_browse_project(self):
        path = QFileDialog.getExistingDirectory(
            self, self.t("select_project_folder")
        )
        if path:
            try:
                self._set_status("⏳ " + self.t("scanning"))
                self.export_project = self.scanner.scan_project(path)
                self.export_project_path = path

                # Show preview
                preview_lines = []
                preview_lines.append(f"📦 {self.export_project.metadata.name}")
                preview_lines.append(f"📄 Files: {self.export_project.file_count}")
                preview_lines.append(f"📏 Lines: {self.export_project.total_lines}")
                preview_lines.append(f"")
                preview_lines.append(f"── Structure ──")
                preview_lines.append(self.export_project.get_tree())
                self.export_preview.setPlainText("\n".join(preview_lines))

                self._set_status("✅ " + self.t("analysis_complete"))
            except Exception as e:
                QMessageBox.critical(self, self.t("scan_error"), str(e))
                self._set_status("❌ " + self.t("scan_error"))

    def _on_project_selected(self, item):
        path = item.data(Qt.ItemDataRole.UserRole)
        if path and os.path.isdir(path):
            try:
                self._set_status("⏳ " + self.t("scanning"))
                self.export_project = self.scanner.scan_project(path)
                self.export_project_path = path

                preview_lines = []
                preview_lines.append(f"📦 {self.export_project.metadata.name}")
                preview_lines.append(f"📄 Files: {self.export_project.file_count}")
                preview_lines.append(f"📏 Lines: {self.export_project.total_lines}")
                preview_lines.append(f"")
                preview_lines.append(f"── Structure ──")
                preview_lines.append(self.export_project.get_tree())
                self.export_preview.setPlainText("\n".join(preview_lines))

                self._set_status("✅ " + self.t("analysis_complete"))
            except Exception as e:
                QMessageBox.critical(self, self.t("scan_error"), str(e))

    def _on_export_pdf(self):
        """Export PDF — ALWAYS saves to the project folder"""
        if not self.export_project:
            QMessageBox.warning(
                self,
                self.t("no_project_selected"),
                self.t("select_project_first")
            )
            return

        # Determine project folder
        project_path = None
        if self.export_project_path and os.path.isdir(self.export_project_path):
            project_path = self.export_project_path
        else:
            target = self.dir_combo.currentText().strip()
            if target and os.path.isdir(target):
                project_path = target

        if not project_path:
            QMessageBox.warning(
                self,
                self.t("no_directory_selected"),
                self.t("select_working_directory")
            )
            return

        # Build PDF path — ALWAYS in project folder
        pdf_name = self.export_project.metadata.name + ".pdf"
        output_path = os.path.join(project_path, pdf_name)

        # Avoid overwriting — add counter suffix
        if os.path.exists(output_path):
            counter = 1
            while os.path.exists(output_path):
                pdf_name = self.export_project.metadata.name + f"_{counter}.pdf"
                output_path = os.path.join(project_path, pdf_name)
                counter += 1

        self._set_status("⏳ " + self.t("exporting_pdf"))
        self.btn_pdf.setEnabled(False)

        worker = ExportPDFWorker(self.export_project, output_path)
        worker.finished.connect(self._on_pdf_done)
        worker.error.connect(self._on_pdf_error)
        self._workers.append(worker)
        worker.start()

    def _on_pdf_done(self, path):
        self.btn_pdf.setEnabled(True)
        QMessageBox.information(
            self,
            self.t("pdf_exported"),
            self.t("pdf_saved_at", path)
        )
        self._set_status("✅ " + self.t("pdf_exported"))

    def _on_pdf_error(self, error_msg):
        self.btn_pdf.setEnabled(True)
        QMessageBox.critical(
            self,
            self.t("pdf_export_error"),
            error_msg
        )
        self._set_status("❌ " + self.t("pdf_export_error"))

    def _on_copy_ai_format(self):
        if not self.export_project:
            QMessageBox.warning(
                self,
                self.t("no_project_selected"),
                self.t("select_project_first")
            )
            return

        ai_text = self.exporter.export_text(self.export_project)
        clipboard = QApplication.clipboard()
        clipboard.setText(ai_text)
        self._set_status("✅ " + self.t("ai_format_copied"))

    # ═══════════════════════ Status ═══════════════════════

    def _set_status(self, text):
        self.status_bar.showMessage(text)

    # ═══════════════════════ Refresh Texts ═══════════════════════

    def _refresh_all_texts(self):
        self.setWindowTitle(self.t("app_title"))

        # Tabs
        self.tabs.setTabText(0, "📥  " + self.t("tab_import"))
        self.tabs.setTabText(1, "📤  " + self.t("tab_export"))
        self.tabs.setTabText(2, "❓  " + self.t("tab_help"))

        # Import tab
        self.prompt_label.setText(self.t("copy_prompt_for_ai").upper())
        self.input_header_label.setText("📄  " + self.t("paste_ai_response"))
        self.input_text.setPlaceholderText(self.t("placeholder_input"))
        self.btn_parse.setText("🔍  " + self.t("analyze"))
        self.btn_deploy.setText("🚀  " + self.t("create_project"))
        self.overwrite_check.setText(self.t("overwrite_existing"))
        self.btn_clear.setText(self.t("clear"))
        self.result_label.setText("📊  " + self.t("analysis_result").upper())

        # Prompt buttons
        prompt_t_keys = ["prompt_full", "prompt_short", "prompt_continue", "prompt_refactor", "prompt_add_feature"]
        prompt_icons = ["✨", "⚡", "🔄", "🔧", "➕"]
        for i, btn in enumerate(self.prompt_buttons):
            if i < len(prompt_t_keys):
                icon = prompt_icons[i]
                btn.setText(f"{icon}  {self.t(prompt_t_keys[i])}")

        # Export tab
        self.sel_group.setTitle("📂  " + self.t("select_project_to_export"))
        self.btn_scan.setText("🔍  " + self.t("find_projects"))
        self.btn_browse_proj.setText("📁  " + self.t("browse_folder"))
        self.btn_pdf.setText("📄  " + self.t("export_pdf"))
        self.btn_copy_ai.setText("📋  " + self.t("copy_ai_format"))

        # Help tab
        self.help_text.setHtml(self.t("help_content"))

        # Lang button
        self.lang_btn.setText("RU" if self.loc.lang == "ru" else "EN")

        # Char count
        self._on_input_changed()

        # Status
        self._set_status("● " + self.t("ready"))