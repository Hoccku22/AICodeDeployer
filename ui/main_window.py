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
    QSplitter, QSizePolicy,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize
from PyQt6.QtGui import QFont, QAction, QKeySequence, QShortcut, QPalette, QColor

from core.parser import AIFormatParser
from core.deployer import ProjectDeployer
from core.exporter import ProjectExporter
from core.project_scanner import ProjectScanner
from core.prompt_manager import PromptManager
from models.project import Project
from ui.localization import Localization

import logging

logger = logging.getLogger(__name__)


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


DARK_STYLE = """
QMainWindow { background-color: #1e1e2e; }
QWidget { background-color: #1e1e2e; color: #cdd6f4; }
QGroupBox {
    font-weight: bold; font-size: 13px;
    border: 1px solid #45475a; border-radius: 8px;
    margin-top: 12px; padding: 15px 10px 10px 10px;
    background-color: #313244; color: #cdd6f4;
}
QGroupBox::title {
    subcontrol-origin: margin; left: 15px;
    padding: 0 8px; color: #cdd6f4;
}
QTabWidget::pane {
    border: 1px solid #45475a; border-radius: 6px;
    background: #313244;
}
QTabBar::tab {
    padding: 10px 24px; font-size: 13px; font-weight: 600;
    border: 1px solid transparent; border-bottom: none;
    border-top-left-radius: 6px; border-top-right-radius: 6px;
    margin-right: 2px; background: #45475a; color: #a6adc8;
}
QTabBar::tab:selected { background: #313244; color: #89b4fa; border-color: #45475a; }
QTabBar::tab:hover:!selected { background: #585b70; color: #cdd6f4; }
QTextEdit {
    border: 2px solid #45475a; border-radius: 8px; padding: 10px;
    background-color: #1e1e2e; color: #cdd6f4;
    font-family: 'Consolas', 'Fira Code', 'Courier New', monospace; font-size: 11px;
    selection-background-color: #585b70;
}
QTextEdit:focus { border-color: #89b4fa; }
QTextEdit[readOnly="true"] {
    background-color: #11111b; color: #a6e3a1;
    border: none; border-radius: 8px; padding: 12px;
}
QComboBox {
    border: 1px solid #45475a; border-radius: 6px;
    padding: 6px 12px; background: #313244; color: #cdd6f4;
    min-height: 28px; font-size: 12px;
}
QComboBox:focus { border-color: #89b4fa; }
QComboBox::drop-down { border: none; width: 30px; }
QComboBox QAbstractItemView {
    background-color: #313244; color: #cdd6f4;
    selection-background-color: #45475a; border: 1px solid #585b70;
}
QCheckBox { color: #a6adc8; font-size: 12px; }
QCheckBox::indicator { width: 16px; height: 16px; }
QLabel { color: #cdd6f4; }
QStatusBar { background: #11111b; border-top: 1px solid #45475a; }
QStatusBar QLabel { color: #a6adc8; font-size: 12px; padding: 2px 8px; }
QMessageBox { background-color: #313244; color: #cdd6f4; }
QScrollBar:vertical {
    background: #1e1e2e; width: 10px; border: none;
}
QScrollBar::handle:vertical {
    background: #45475a; border-radius: 5px; min-height: 20px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
"""

LIGHT_STYLE = """
QMainWindow { background-color: #f0f2f5; }
QWidget { background-color: #f0f2f5; color: #1e293b; }
QGroupBox {
    font-weight: bold; font-size: 13px;
    border: 1px solid #d1d5db; border-radius: 8px;
    margin-top: 12px; padding: 15px 10px 10px 10px;
    background-color: white; color: #1e293b;
}
QGroupBox::title {
    subcontrol-origin: margin; left: 15px;
    padding: 0 8px; color: #374151;
}
QTabWidget::pane {
    border: 1px solid #d1d5db; border-radius: 6px; background: white;
}
QTabBar::tab {
    padding: 10px 24px; font-size: 13px; font-weight: 600;
    border: 1px solid transparent; border-bottom: none;
    border-top-left-radius: 6px; border-top-right-radius: 6px;
    margin-right: 2px; background: #e5e7eb; color: #6b7280;
}
QTabBar::tab:selected { background: white; color: #1d4ed8; border-color: #d1d5db; }
QTabBar::tab:hover:!selected { background: #f3f4f6; color: #374151; }
QTextEdit {
    border: 2px solid #d1d5db; border-radius: 8px; padding: 10px;
    background-color: #fafbfc; color: #1e293b;
    font-family: 'Consolas', 'Fira Code', 'Courier New', monospace; font-size: 11px;
    selection-background-color: #bfdbfe;
}
QTextEdit:focus { border-color: #3b82f6; background-color: white; }
QTextEdit[readOnly="true"] {
    background-color: #1e293b; color: #e2e8f0;
    border: none; border-radius: 8px; padding: 12px;
}
QComboBox {
    border: 1px solid #d1d5db; border-radius: 6px;
    padding: 6px 12px; background: white; color: #1e293b;
    min-height: 28px; font-size: 12px;
}
QComboBox:focus { border-color: #3b82f6; }
QComboBox::drop-down { border: none; width: 30px; }
QComboBox QAbstractItemView {
    background-color: white; color: #1e293b;
    selection-background-color: #e0e7ff; border: 1px solid #d1d5db;
}
QCheckBox { color: #64748b; font-size: 12px; }
QLabel { color: #1e293b; }
QStatusBar { background: #f8fafc; border-top: 1px solid #e2e8f0; }
QStatusBar QLabel { color: #64748b; font-size: 12px; padding: 2px 8px; }
QScrollBar:vertical {
    background: #f0f2f5; width: 10px; border: none;
}
QScrollBar::handle:vertical {
    background: #cbd5e1; border-radius: 5px; min-height: 20px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
"""


def _btn_style(bg, fg="white"):
    return (
        "QPushButton { background-color: " + bg + "; color: " + fg + ";"
        " border: none; padding: 10px 22px; border-radius: 6px;"
        " font-size: 13px; font-weight: 600; min-width: 100px; }"
        "QPushButton:hover { background-color: " + bg + "cc; }"
        "QPushButton:pressed { background-color: " + bg + "aa; }"
        "QPushButton:disabled { background-color: #888888; color: #bbbbbb; }"
    )


def _small_btn(bg):
    return (
        "QPushButton { background-color: " + bg + "; color: white;"
        " border: none; padding: 6px 14px; border-radius: 5px;"
        " font-size: 12px; font-weight: 600; }"
        "QPushButton:hover { background-color: " + bg + "dd; }"
    )


def _toggle_btn(bg):
    return (
        "QPushButton { background-color: " + bg + "; color: white;"
        " border: none; padding: 6px 16px; border-radius: 5px;"
        " font-size: 11px; font-weight: 600; min-width: 120px; }"
        "QPushButton:hover { background-color: " + bg + "dd; }"
    )


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.loc = Localization.instance()
        self.parser = AIFormatParser()
        self.scanner = ProjectScanner()
        self.exporter = ProjectExporter()
        self.current_project = None
        self.export_project = None
        self._workers = []
        self._dark_mode = False
        self._build_ui()
        self._build_menu()
        self._build_shortcuts()
        self._detect_directories()
        self._apply_theme()

    def t(self, key, *args):
        return self.loc.t(key, *args)

    def _apply_theme(self):
        if self._dark_mode:
            self.setStyleSheet(DARK_STYLE)
        else:
            self.setStyleSheet(LIGHT_STYLE)

    def _toggle_theme(self):
        self._dark_mode = not self._dark_mode
        self._apply_theme()
        if self._dark_mode:
            self.theme_btn.setText(self.t("theme_dark"))
        else:
            self.theme_btn.setText(self.t("theme_light"))

    def _toggle_language(self):
        self.loc.toggle_lang()
        self._refresh_all_texts()

    def _refresh_all_texts(self):
        """Update all UI texts after language change"""
        self.setWindowTitle(self.t("app_title"))

        # Directory group
        self.dir_group.setTitle(self.t("working_directory"))
        self.btn_browse_dir.setText(self.t("browse"))
        self.btn_refresh_dir.setText(self.t("refresh"))

        # Tabs
        self.tabs.setTabText(0, self.t("tab_import"))
        self.tabs.setTabText(1, self.t("tab_export"))
        self.tabs.setTabText(2, self.t("tab_help"))

        # Import tab
        self.prompt_label.setText(self.t("copy_prompt_for_ai"))
        self.input_header_label.setText(self.t("paste_ai_response"))
        self.input_text.setPlaceholderText(self.t("placeholder_input"))
        self.btn_parse.setText(self.t("analyze"))
        self.btn_deploy.setText(self.t("create_project"))
        self.overwrite_check.setText(self.t("overwrite_existing"))
        self.btn_clear.setText(self.t("clear"))
        self.result_label.setText(self.t("analysis_result"))

        # Prompt buttons
        prompt_keys = ["full", "short", "continue", "refactor", "add_feature"]
        prompt_t_keys = ["prompt_full", "prompt_short", "prompt_continue", "prompt_refactor", "prompt_add_feature"]
        for i, btn in enumerate(self.prompt_buttons):
            if i < len(prompt_t_keys):
                btn.setText(self.t(prompt_t_keys[i]))

        # Export tab
        self.sel_group.setTitle(self.t("select_project_to_export"))
        self.btn_scan.setText(self.t("find_projects"))
        self.btn_browse_proj.setText(self.t("browse_folder"))
        self.btn_pdf.setText(self.t("export_pdf"))
        self.btn_copy_ai.setText(self.t("copy_ai_format"))
        self.export_preview_label.setText(self.t("export_preview"))

        # Help tab
        self.help_text.setHtml(self.t("help_content"))

        # Theme & language buttons
        if self._dark_mode:
            self.theme_btn.setText(self.t("theme_dark"))
        else:
            self.theme_btn.setText(self.t("theme_light"))
        self.lang_btn.setText(self.t("lang_label"))

        # Update char count
        self._on_input_changed()

        # Status
        self._set_status(self.t("ready"))

    def _build_ui(self):
        self.setWindowTitle(self.t("app_title"))
        self.setMinimumSize(950, 700)
        self.resize(1200, 850)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(12, 8, 12, 4)
        root.setSpacing(8)

        # top bar: directory + theme/lang buttons
        top_bar = QHBoxLayout()
        top_bar.setSpacing(8)

        # directory panel
        self.dir_group = QGroupBox(self.t("working_directory"))
        dir_lay = QHBoxLayout(self.dir_group)
        dir_lay.setContentsMargins(10, 5, 10, 5)

        self.dir_combo = QComboBox()
        self.dir_combo.setEditable(True)
        self.dir_combo.setMinimumWidth(400)
        dir_lay.addWidget(self.dir_combo, stretch=1)

        self.btn_browse_dir = QPushButton(self.t("browse"))
        self.btn_browse_dir.setStyleSheet(_small_btn("#6366f1"))
        self.btn_browse_dir.clicked.connect(self._on_browse_directory)
        dir_lay.addWidget(self.btn_browse_dir)

        self.btn_refresh_dir = QPushButton(self.t("refresh"))
        self.btn_refresh_dir.setStyleSheet(_small_btn("#64748b"))
        self.btn_refresh_dir.clicked.connect(self._detect_directories)
        dir_lay.addWidget(self.btn_refresh_dir)

        top_bar.addWidget(self.dir_group, stretch=1)

        # theme & language buttons (vertical stack)
        toggle_frame = QFrame()
        toggle_lay = QVBoxLayout(toggle_frame)
        toggle_lay.setContentsMargins(0, 12, 0, 0)
        toggle_lay.setSpacing(4)

        self.theme_btn = QPushButton(self.t("theme_light"))
        self.theme_btn.setStyleSheet(_toggle_btn("#7c3aed"))
        self.theme_btn.clicked.connect(self._toggle_theme)
        toggle_lay.addWidget(self.theme_btn)

        self.lang_btn = QPushButton(self.t("lang_label"))
        self.lang_btn.setStyleSheet(_toggle_btn("#0891b2"))
        self.lang_btn.clicked.connect(self._toggle_language)
        toggle_lay.addWidget(self.lang_btn)

        top_bar.addWidget(toggle_frame)

        root.addLayout(top_bar)

        # tabs
        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_import_tab(), self.t("tab_import"))
        self.tabs.addTab(self._build_export_tab(), self.t("tab_export"))
        self.tabs.addTab(self._build_help_tab(), self.t("tab_help"))
        root.addWidget(self.tabs)

        # status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self._set_status(self.t("ready"))

    def _build_import_tab(self):
        tab = QWidget()
        lay = QVBoxLayout(tab)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(8)

        # prompt panel
        prompt_frame = QFrame()
        prompt_frame.setStyleSheet(
            "QFrame { background-color: #166534; border-radius: 8px; padding: 6px; }"
            "QLabel { color: white; }"
        )
        prompt_lay = QHBoxLayout(prompt_frame)
        prompt_lay.setContentsMargins(10, 6, 10, 6)

        self.prompt_label = QLabel(self.t("copy_prompt_for_ai"))
        prompt_lay.addWidget(self.prompt_label)

        variants = PromptManager.get_all_variants()
        prompt_keys = list(variants.keys())
        prompt_t_keys = ["prompt_full", "prompt_short", "prompt_continue", "prompt_refactor", "prompt_add_feature"]

        self.prompt_buttons = []
        for i, (key, variant) in enumerate(variants.items()):
            t_key = prompt_t_keys[i] if i < len(prompt_t_keys) else variant.title
            btn = QPushButton(self.t(t_key) if i < len(prompt_t_keys) else variant.title)
            btn.setToolTip(variant.description)
            btn.setStyleSheet(_small_btn("#22c55e"))
            btn.clicked.connect(lambda checked, k=key: self._on_copy_prompt(k))
            prompt_lay.addWidget(btn)
            self.prompt_buttons.append(btn)

        prompt_lay.addStretch()
        lay.addWidget(prompt_frame)

        # splitter
        splitter = QSplitter(Qt.Orientation.Vertical)

        # input area
        input_w = QWidget()
        input_lay = QVBoxLayout(input_w)
        input_lay.setContentsMargins(0, 0, 0, 0)
        input_lay.setSpacing(4)

        header = QHBoxLayout()
        self.input_header_label = QLabel(self.t("paste_ai_response"))
        self.input_header_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        header.addWidget(self.input_header_label)

        self.char_label = QLabel(self.t("chars_count", 0))
        self.char_label.setStyleSheet("font-size: 11px;")
        header.addStretch()
        header.addWidget(self.char_label)
        input_lay.addLayout(header)

        self.input_text = QTextEdit()
        self.input_text.setPlaceholderText(self.t("placeholder_input"))
        self.input_text.textChanged.connect(self._on_input_changed)
        input_lay.addWidget(self.input_text)
        splitter.addWidget(input_w)

        # bottom: actions + result
        bottom_w = QWidget()
        bottom_lay = QVBoxLayout(bottom_w)
        bottom_lay.setContentsMargins(0, 0, 0, 0)
        bottom_lay.setSpacing(6)

        # action buttons
        act_frame = QFrame()
        act_lay = QHBoxLayout(act_frame)
        act_lay.setContentsMargins(0, 0, 0, 0)

        self.btn_parse = QPushButton(self.t("analyze"))
        self.btn_parse.setStyleSheet(_btn_style("#3b82f6"))
        self.btn_parse.clicked.connect(self._on_parse)
        act_lay.addWidget(self.btn_parse)

        self.btn_deploy = QPushButton(self.t("create_project"))
        self.btn_deploy.setStyleSheet(_btn_style("#dc2626"))
        self.btn_deploy.setEnabled(False)
        self.btn_deploy.clicked.connect(self._on_deploy)
        act_lay.addWidget(self.btn_deploy)

        self.overwrite_check = QCheckBox(self.t("overwrite_existing"))
        act_lay.addWidget(self.overwrite_check)

        act_lay.addStretch()

        self.btn_clear = QPushButton(self.t("clear"))
        self.btn_clear.setStyleSheet(_btn_style("#94a3b8"))
        self.btn_clear.clicked.connect(self._on_clear)
        act_lay.addWidget(self.btn_clear)

        bottom_lay.addWidget(act_frame)

        self.result_label = QLabel(self.t("analysis_result"))
        self.result_label.setStyleSheet("font-size: 12px; font-weight: 600;")
        bottom_lay.addWidget(self.result_label)

        self.parse_result = QTextEdit()
        self.parse_result.setReadOnly(True)
        self.parse_result.setMinimumHeight(120)
        bottom_lay.addWidget(self.parse_result)

        splitter.addWidget(bottom_w)
        splitter.setSizes([450, 300])
        lay.addWidget(splitter)

        return tab

    def _build_export_tab(self):
        tab = QWidget()
        lay = QVBoxLayout(tab)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(10)

        # project selection
        self.sel_group = QGroupBox(self.t("select_project_to_export"))
        sel_lay = QHBoxLayout(self.sel_group)

        self.project_combo = QComboBox()
        self.project_combo.setMinimumWidth(400)
        self.project_combo.setEditable(True)
        sel_lay.addWidget(self.project_combo, stretch=1)

        self.btn_scan = QPushButton(self.t("find_projects"))
        self.btn_scan.setStyleSheet(_small_btn("#6366f1"))
        self.btn_scan.clicked.connect(self._on_scan_projects)
        sel_lay.addWidget(self.btn_scan)

        self.btn_browse_proj = QPushButton(self.t("browse_folder"))
        self.btn_browse_proj.setStyleSheet(_small_btn("#64748b"))
        self.btn_browse_proj.clicked.connect(self._on_browse_project)
        sel_lay.addWidget(self.btn_browse_proj)

        lay.addWidget(self.sel_group)

        # export buttons
        exp_frame = QFrame()
        exp_lay = QHBoxLayout(exp_frame)
        exp_lay.setContentsMargins(0, 0, 0, 0)

        self.btn_pdf = QPushButton(self.t("export_pdf"))
        self.btn_pdf.setStyleSheet(_btn_style("#dc2626"))
        self.btn_pdf.clicked.connect(self._on_export_pdf)
        exp_lay.addWidget(self.btn_pdf)

        self.btn_copy_ai = QPushButton(self.t("copy_ai_format"))
        self.btn_copy_ai.setStyleSheet(_btn_style("#059669"))
        self.btn_copy_ai.clicked.connect(self._on_copy_ai_format)
        exp_lay.addWidget(self.btn_copy_ai)

        exp_lay.addStretch()
        lay.addWidget(exp_frame)

        # preview
        self.export_preview_label = QLabel(self.t("export_preview"))
        self.export_preview_label.setStyleSheet("font-size: 12px; font-weight: 600;")
        lay.addWidget(self.export_preview_label)

        self.export_preview = QTextEdit()
        self.export_preview.setReadOnly(True)
        lay.addWidget(self.export_preview)

        return tab

    def _build_help_tab(self):
        tab = QWidget()
        lay = QVBoxLayout(tab)
        lay.setContentsMargins(15, 15, 15, 15)

        self.help_text = QTextEdit()
        self.help_text.setReadOnly(True)
        self.help_text.setHtml(self.t("help_content"))
        self.help_text.setStyleSheet(
            "QTextEdit { font-size: 13px; line-height: 1.6; border: none; }"
        )
        lay.addWidget(self.help_text)
        return tab

    def _build_menu(self):
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("File")

        act_open = QAction("Open text file...", self)
        act_open.setShortcut(QKeySequence.StandardKey.Open)
        act_open.triggered.connect(self._on_open_file)
        file_menu.addAction(act_open)

        file_menu.addSeparator()

        act_quit = QAction("Exit", self)
        act_quit.setShortcut(QKeySequence("Ctrl+Q"))
        act_quit.triggered.connect(self.close)
        file_menu.addAction(act_quit)

    def _build_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+Return"), self, self._on_parse)
        QShortcut(QKeySequence("Ctrl+D"), self, self._on_deploy)
        QShortcut(QKeySequence("Ctrl+E"), self, self._on_export_pdf)
        QShortcut(QKeySequence("Ctrl+T"), self, self._toggle_theme)

    def _detect_directories(self):
        dirs = self.scanner.find_project_directories()
        current = self.dir_combo.currentText()
        self.dir_combo.clear()
        if dirs:
            self.dir_combo.addItems(dirs)
        if current:
            self.dir_combo.setCurrentText(current)
        elif dirs:
            home_docs = str(Path.home() / "Documents")
            for d in dirs:
                if "document" in d.lower():
                    self.dir_combo.setCurrentText(d)
                    break

    def _set_status(self, msg):
        self.status_bar.showMessage(msg)

    # --- event handlers ---

    def _on_input_changed(self):
        text = self.input_text.toPlainText()
        self.char_label.setText(self.t("chars_count", len(text)))

    def _on_parse(self):
        text = self.input_text.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, self.t("no_text_to_analyze"), self.t("paste_text_first"))
            return

        self._set_status(self.t("analyzing"))
        self.btn_parse.setEnabled(False)

        worker = ParseWorker(text)
        worker.finished.connect(self._on_parse_done)
        worker.error.connect(self._on_parse_error)
        self._workers.append(worker)
        worker.start()

    def _on_parse_done(self, project):
        self.current_project = project
        self.btn_deploy.setEnabled(True)
        self.btn_parse.setEnabled(True)

        info = self.t("project_name", project.metadata.name) + "\n"
        info += self.t("files_count", project.file_count) + "\n"
        info += self.t("total_lines", project.total_lines) + "\n\n"
        info += self.t("file_list") + "\n"
        for f in project.files:
            info += "  " + f.relative_path + "\n"

        self.parse_result.setPlainText(info)
        self._set_status(self.t("analysis_complete"))

    def _on_parse_error(self, error_msg):
        self.btn_parse.setEnabled(True)
        QMessageBox.critical(self, self.t("analysis_error"), error_msg)
        self._set_status(self.t("ready"))

    def _on_deploy(self):
        if not self.current_project:
            QMessageBox.warning(self, self.t("no_project_analyzed"), self.t("analyze_first"))
            return

        target_dir = self.dir_combo.currentText().strip()
        if not target_dir:
            QMessageBox.warning(self, self.t("no_directory_selected"), self.t("select_working_directory"))
            return

        overwrite = self.overwrite_check.isChecked()
        self._set_status(self.t("deploying"))
        self.btn_deploy.setEnabled(False)

        worker = DeployWorker(self.current_project, target_dir, overwrite)
        worker.finished.connect(self._on_deploy_done)
        worker.error.connect(self._on_deploy_error)
        self._workers.append(worker)
        worker.start()

    def _on_deploy_done(self, path):
        self.btn_deploy.setEnabled(True)
        QMessageBox.information(self, self.t("project_created"), self.t("project_created_at", path))
        self._set_status(self.t("ready"))

    def _on_deploy_error(self, error_msg):
        self.btn_deploy.setEnabled(True)
        QMessageBox.critical(self, self.t("deploy_error"), error_msg)
        self._set_status(self.t("ready"))

    def _on_copy_prompt(self, variant_key):
        prompt = PromptManager.get_prompt(variant_key)
        clipboard = QApplication.clipboard()
        clipboard.setText(prompt)
        variant = PromptManager.get_variant(variant_key)
        self._set_status(self.t("prompt_copied", variant.title))

    def _on_clear(self):
        self.input_text.clear()
        self.parse_result.clear()
        self.current_project = None
        self.btn_deploy.setEnabled(False)
        self._set_status(self.t("text_cleared"))

    def _on_browse_directory(self):
        directory = QFileDialog.getExistingDirectory(self, self.t("select_directory"))
        if directory:
            self.dir_combo.setCurrentText(directory)

    def _on_browse_project(self):
        directory = QFileDialog.getExistingDirectory(self, self.t("select_project_folder"))
        if directory:
            self.project_combo.setCurrentText(directory)

    def _on_scan_projects(self):
        target_dir = self.dir_combo.currentText().strip()
        if not target_dir or not os.path.isdir(target_dir):
            QMessageBox.warning(self, self.t("no_directory_selected"), self.t("select_working_directory"))
            return

        self._set_status(self.t("scanning"))
        try:
            projects = []
            for item in Path(target_dir).iterdir():
                if item.is_dir() and not item.name.startswith('.'):
                    # check if it looks like a project
                    for indicator in self.scanner.PROJECT_INDICATORS:
                        if (item / indicator).exists():
                            projects.append(str(item))
                            break

            self.project_combo.clear()
            self.project_combo.addItems(projects)
            self._set_status(self.t("found_projects", len(projects)))
        except Exception as e:
            QMessageBox.critical(self, self.t("scan_error"), str(e))
            self._set_status(self.t("ready"))

    def _on_export_pdf(self):
        project_path = self.project_combo.currentText().strip()
        if not project_path:
            QMessageBox.warning(self, self.t("no_project_selected"), self.t("select_project_first"))
            return

        if not os.path.isdir(project_path):
            QMessageBox.warning(self, self.t("project_not_found"), self.t("path_not_exists", project_path))
            return

        self._set_status(self.t("scanning"))
        try:
            project = self.scanner.scan_project(project_path)
            self.export_project = project
        except Exception as e:
            QMessageBox.critical(self, self.t("scan_error"), str(e))
            self._set_status(self.t("ready"))
            return

        default_name = project.metadata.name + "_project.pdf"
        output_path, _ = QFileDialog.getSaveFileName(
            self, self.t("save_pdf"), default_name, "PDF (*.pdf)"
        )
        if not output_path:
            self._set_status(self.t("ready"))
            return

        self._set_status(self.t("exporting_pdf"))
        worker = ExportPDFWorker(project, output_path)
        worker.finished.connect(self._on_pdf_done)
        worker.error.connect(self._on_pdf_error)
        self._workers.append(worker)
        worker.start()

    def _on_pdf_done(self, path):
        QMessageBox.information(self, self.t("pdf_exported"), self.t("pdf_saved_at", path))
        self._set_status(self.t("ready"))

    def _on_pdf_error(self, error_msg):
        QMessageBox.critical(self, self.t("pdf_export_error"), error_msg)
        self._set_status(self.t("ready"))

    def _on_copy_ai_format(self):
        project_path = self.project_combo.currentText().strip()
        if not project_path:
            QMessageBox.warning(self, self.t("no_project_selected"), self.t("select_project_first"))
            return

        if not os.path.isdir(project_path):
            QMessageBox.warning(self, self.t("project_not_found"), self.t("path_not_exists", project_path))
            return

        try:
            project = self.scanner.scan_project(project_path)
            ai_text = self.exporter.export_text(project)
            clipboard = QApplication.clipboard()
            clipboard.setText(ai_text)
            self.export_preview.setPlainText(ai_text[:5000] + "\n\n... (preview)")
            self._set_status(self.t("ai_format_copied"))
        except Exception as e:
            QMessageBox.critical(self, self.t("scan_error"), str(e))

    def _on_open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open File", "", "Text files (*.txt *.md);;All files (*)"
        )
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.input_text.setPlainText(content)
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))