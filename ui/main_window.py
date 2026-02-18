# ui/main_window.py
import os
import sys
import datetime
import subprocess
import traceback
import shutil
import string
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTextEdit, QLabel, QFileDialog,
    QComboBox, QMessageBox, QTabWidget, QGroupBox,
    QStatusBar, QFrame, QApplication, QCheckBox,
    QSplitter, QSizePolicy, QListWidget, QListWidgetItem,
    QTreeWidget, QTreeWidgetItem, QHeaderView, QMenu,
    QSizeGrip,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize, QMimeData, QUrl
from PyQt6.QtGui import QFont, QAction, QKeySequence, QShortcut, QPalette, QColor, QIcon, QDrag

from core.parser import AIFormatParser
from core.deployer import ProjectDeployer
from core.exporter import ProjectExporter
from core.project_scanner import ProjectScanner
from core.prompt_manager import PromptManager
from models.project import Project
from ui.localization import Localization
import logging

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Background workers
# ─────────────────────────────────────────────

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


class ReportSearchWorker(QThread):
    """Фоновый поиск PDF отчётов AI Code Deployer"""
    found = pyqtSignal(str, str)       # pdf_path, project_name
    finished_signal = pyqtSignal(int)  # total count
    progress = pyqtSignal(str)         # current directory being scanned

    SKIP_DIRS = {
        '__pycache__', 'node_modules', '.git', '.svn', '.hg',
        'venv', '.venv', 'env', '.env', '.idea', '.vscode',
        'dist', 'build', '.next', '.nuxt', 'target',
        '.pytest_cache', '.mypy_cache', '__MACOSX',
        'bin', 'obj', '.tox', '.eggs', 'site-packages',
        'Windows', 'Program Files', 'Program Files (x86)',
        '$Recycle.Bin', 'System Volume Information',
        'AppData', 'ProgramData', 'Recovery',
        '.Trash', '.cache', '.local', 'snap',
        'Library', 'Applications',
    }

    def __init__(self, search_root: str, search_all_drives: bool = False):
        super().__init__()
        self.search_root = search_root
        self.search_all_drives = search_all_drives
        self._stopped = False

    def stop(self):
        self._stopped = True

    def run(self):
        count = 0
        roots = []

        if self.search_all_drives:
            if sys.platform == "win32":
                for letter in string.ascii_uppercase:
                    drive = f"{letter}:\\"
                    if os.path.exists(drive):
                        roots.append(drive)
            elif sys.platform == "darwin":
                roots = ["/Users", "/Volumes"]
            else:
                roots = [str(Path.home()), "/home"]
        else:
            roots = [self.search_root]

        for root in roots:
            if self._stopped:
                break
            count += self._scan_directory(root)

        self.finished_signal.emit(count)

    # ── recursive walk ──────────────────────────
    def _scan_directory(self, root: str) -> int:
        count = 0
        try:
            for dirpath, dirnames, filenames in os.walk(root, topdown=True):
                if self._stopped:
                    break

                dirnames[:] = [
                    d for d in dirnames
                    if d not in self.SKIP_DIRS
                    and not d.startswith('$')
                ]

                self.progress.emit(dirpath)

                for filename in filenames:
                    if self._stopped:
                        break
                    if not filename.lower().endswith('.pdf'):
                        continue

                    pdf_path = os.path.join(dirpath, filename)
                    try:
                        if self._is_our_report(pdf_path):
                            project_name = Path(dirpath).name
                            self.found.emit(pdf_path, project_name)
                            count += 1
                    except Exception:
                        pass
        except PermissionError:
            pass
        except Exception as e:
            logger.debug(f"Scan error in {root}: {e}")
        return count

    # ── PDF signature check ─────────────────────
    @staticmethod
    def _is_our_report(pdf_path: str) -> bool:
        """Return True if the PDF was generated by AI Code Deployer."""
        try:
            file_size = os.path.getsize(pdf_path)
            if file_size < 500 or file_size > 50 * 1024 * 1024:
                return False

            with open(pdf_path, 'rb') as f:
                data = f.read()

            if b'AI Code Deployer' in data:
                return True

            for enc in ('utf-16-be', 'utf-16-le'):
                try:
                    if 'AI Code Deployer'.encode(enc) in data:
                        return True
                except Exception:
                    pass

            return False
        except Exception:
            return False


# ─────────────────────────────────────────────
# Draggable tree for reports
# ─────────────────────────────────────────────

class DraggableReportsTree(QTreeWidget):
    """QTreeWidget that supports dragging PDF files out of the app."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setDragDropMode(QTreeWidget.DragDropMode.DragOnly)
        self.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)
        self._drag_start_pos = None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            super().mouseMoveEvent(event)
            return
        if self._drag_start_pos is None:
            super().mouseMoveEvent(event)
            return

        diff = event.pos() - self._drag_start_pos
        if diff.manhattanLength() < QApplication.startDragDistance():
            super().mouseMoveEvent(event)
            return

        item = self.currentItem()
        if not item:
            return

        file_path = item.data(0, Qt.ItemDataRole.UserRole)
        if not file_path or not os.path.isfile(file_path):
            return

        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setUrls([QUrl.fromLocalFile(file_path)])
        drag.setMimeData(mime_data)
        drag.exec(Qt.DropAction.CopyAction | Qt.DropAction.MoveAction)

    def mouseReleaseEvent(self, event):
        self._drag_start_pos = None
        super().mouseReleaseEvent(event)


# ─────────────────────────────────────────────
# Stylesheets
# ─────────────────────────────────────────────

DARK_STYLE = """
QMainWindow { background-color: #1a1b26; }
QWidget { background-color: #1a1b26; color: #c0caf5; font-family: 'Segoe UI', sans-serif; font-size: 13px; }
QFrame#headerFrame { background-color: #16161e; border-bottom: 1px solid #292e42; }
QFrame#headerFrame QLabel { background: transparent; color: #7aa2f7; font-weight: bold; font-size: 14px; }
QFrame#headerFrame QPushButton { background: transparent; border: none; color: #a9b1d6; padding: 4px 8px; border-radius: 4px; font-size: 12px; }
QFrame#headerFrame QPushButton:hover { background-color: #292e42; color: #c0caf5; }
QComboBox#dirCombo { background-color: #1a1b26; border: 1px solid #292e42; border-radius: 4px; padding: 5px 10px; color: #a9b1d6; min-height: 28px; }
QComboBox#dirCombo:hover { border-color: #414868; }
QComboBox#dirCombo:focus { border-color: #7aa2f7; }
QComboBox#dirCombo::drop-down { border: none; width: 24px; }
QComboBox#dirCombo::down-arrow { image: none; border-left: 4px solid transparent; border-right: 4px solid transparent; border-top: 5px solid #a9b1d6; margin-right: 8px; }
QComboBox QAbstractItemView { background-color: #24283b; color: #c0caf5; selection-background-color: #414868; border: 1px solid #292e42; outline: none; }
QTabWidget::pane { border: none; background: #1a1b26; }
QTabBar { background: #1a1b26; border-bottom: 1px solid #292e42; }
QTabBar::tab { padding: 8px 20px; font-size: 13px; font-weight: 600; border: none; border-bottom: 2px solid transparent; background: transparent; color: #565f89; margin-right: 4px; }
QTabBar::tab:selected { color: #7aa2f7; border-bottom: 2px solid #7aa2f7; background: rgba(122, 162, 247, 0.05); }
QTabBar::tab:hover:!selected { color: #a9b1d6; background: rgba(41, 46, 66, 0.5); }
QFrame#quickActionsBar { background-color: #1a1b26; border-bottom: 1px solid #292e42; }
QFrame#quickActionsBar QLabel { background: transparent; color: #565f89; font-size: 11px; font-weight: 600; }
QFrame#quickActionsBar QPushButton { background-color: #414868; color: #c0caf5; border: none; padding: 5px 12px; border-radius: 4px; font-size: 11px; font-weight: 600; }
QFrame#quickActionsBar QPushButton:hover { background-color: #535d82; }
QTextEdit#inputText { background-color: #1a1b26; color: #a9b1d6; border: none; border-right: 1px solid #292e42; padding: 12px; font-family: 'Consolas', monospace; font-size: 12px; }
QFrame#resultsPanel { background-color: #24283b; border: none; }
QFrame#resultsPanelHeader { background-color: #1f2335; border-bottom: 1px solid #292e42; }
QFrame#resultsPanelHeader QLabel { background: transparent; color: #a9b1d6; font-size: 11px; font-weight: 600; }
QTextEdit#resultText { background-color: #24283b; color: #a9b1d6; border: none; padding: 12px; font-family: 'Consolas', monospace; font-size: 11px; }
QFrame#bottomBar { background-color: #1f2335; border-top: 1px solid #292e42; }
QFrame#bottomBar QLabel { background: transparent; color: #565f89; font-size: 12px; }
QPushButton#btnPrimary { background-color: #7aa2f7; color: #1a1b26; border: none; padding: 8px 20px; border-radius: 6px; font-size: 13px; font-weight: 600; }
QPushButton#btnPrimary:hover { background-color: #5d8eea; }
QPushButton#btnPrimary:disabled { background-color: #414868; color: #565f89; }
QPushButton#btnSecondary { background-color: transparent; color: #a9b1d6; border: none; padding: 8px 16px; border-radius: 6px; font-size: 13px; }
QPushButton#btnSecondary:hover { background-color: #292e42; color: #c0caf5; }
QPushButton#btnSuccess { background-color: #9ece6a; color: #1a1b26; border: none; padding: 8px 20px; border-radius: 6px; font-size: 13px; font-weight: 600; }
QPushButton#btnSuccess:hover { background-color: #89b856; }
QPushButton#btnDanger { background-color: #f7768e; color: #1a1b26; border: none; padding: 8px 20px; border-radius: 6px; font-size: 13px; font-weight: 600; }
QPushButton#btnDanger:hover { background-color: #e0606e; }
QListWidget { background-color: #1a1b26; color: #a9b1d6; border: 1px solid #292e42; border-radius: 6px; padding: 4px; outline: none; font-size: 12px; }
QListWidget::item { padding: 8px 12px; border-radius: 4px; margin: 2px 0; }
QListWidget::item:selected { background-color: rgba(122, 162, 247, 0.15); color: #7aa2f7; }
QListWidget::item:hover:!selected { background-color: #292e42; }
QTextEdit#helpText { background-color: #1a1b26; color: #a9b1d6; border: none; padding: 24px; font-size: 13px; }
QCheckBox { color: #a9b1d6; font-size: 12px; spacing: 6px; }
QCheckBox::indicator { width: 16px; height: 16px; border: 2px solid #414868; border-radius: 4px; background: #1a1b26; }
QCheckBox::indicator:checked { background: #7aa2f7; border-color: #7aa2f7; }
QStatusBar { background: #7aa2f7; border: none; min-height: 22px; max-height: 22px; }
QStatusBar QLabel { color: #1a1b26; font-size: 11px; font-weight: 600; padding: 0 6px; background: transparent; }
QScrollBar:vertical { background: #1a1b26; width: 10px; border: none; }
QScrollBar::handle:vertical { background: #414868; border-radius: 5px; min-height: 20px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { background: #1a1b26; height: 10px; border: none; }
QScrollBar::handle:horizontal { background: #414868; border-radius: 5px; min-width: 20px; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QSplitter::handle { background: #292e42; }
QSplitter::handle:horizontal { width: 1px; }
QMessageBox { background-color: #24283b; color: #c0caf5; }
QMessageBox QPushButton { background-color: #414868; color: #c0caf5; border: none; padding: 6px 16px; border-radius: 4px; min-width: 80px; }
QGroupBox { font-weight: 600; font-size: 12px; border: 1px solid #292e42; border-radius: 8px; margin-top: 12px; padding: 16px 12px 12px 12px; }
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; color: #a9b1d6; }
QFrame#editorHeader { background-color: #1f2335; border-bottom: 1px solid #292e42; }
QFrame#editorHeader QLabel { background: transparent; font-size: 11px; }
QTreeWidget#reportsTree { background-color: #1a1b26; color: #a9b1d6; border: none; outline: none; font-size: 12px; }
QTreeWidget#reportsTree::item { padding: 6px 8px; border-bottom: 1px solid #292e42; }
QTreeWidget#reportsTree::item:selected { background-color: rgba(122, 162, 247, 0.15); color: #7aa2f7; }
QTreeWidget#reportsTree::item:hover:!selected { background-color: #292e42; }
QTreeWidget#reportsTree::item:alternate { background-color: #1e2030; }
QHeaderView::section { background-color: #1f2335; color: #a9b1d6; border: none; border-bottom: 1px solid #292e42; border-right: 1px solid #292e42; padding: 6px 8px; font-size: 11px; font-weight: 600; }
QSizeGrip { background: transparent; width: 16px; height: 16px; }
"""

LIGHT_STYLE = """
QMainWindow { background-color: #f0f2f5; }
QWidget { background-color: #f0f2f5; color: #1e293b; font-family: 'Segoe UI', sans-serif; font-size: 13px; }
QFrame#headerFrame { background-color: #ffffff; border-bottom: 1px solid #e2e8f0; }
QFrame#headerFrame QLabel { background: transparent; color: #3b82f6; font-weight: bold; font-size: 14px; }
QFrame#headerFrame QPushButton { background: transparent; border: none; color: #64748b; padding: 4px 8px; border-radius: 4px; font-size: 12px; }
QFrame#headerFrame QPushButton:hover { background-color: #f1f5f9; color: #1e293b; }
QComboBox#dirCombo { background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 4px; padding: 5px 10px; color: #475569; min-height: 28px; }
QComboBox#dirCombo:hover { border-color: #cbd5e1; }
QComboBox#dirCombo:focus { border-color: #3b82f6; }
QComboBox#dirCombo::drop-down { border: none; width: 24px; }
QComboBox#dirCombo::down-arrow { image: none; border-left: 4px solid transparent; border-right: 4px solid transparent; border-top: 5px solid #64748b; margin-right: 8px; }
QComboBox QAbstractItemView { background-color: #ffffff; color: #1e293b; selection-background-color: #eff6ff; border: 1px solid #e2e8f0; outline: none; }
QTabWidget::pane { border: none; background: #f0f2f5; }
QTabBar { background: #ffffff; border-bottom: 1px solid #e2e8f0; }
QTabBar::tab { padding: 8px 20px; font-size: 13px; font-weight: 600; border: none; border-bottom: 2px solid transparent; background: transparent; color: #94a3b8; margin-right: 4px; }
QTabBar::tab:selected { color: #3b82f6; border-bottom: 2px solid #3b82f6; background: rgba(59, 130, 246, 0.04); }
QTabBar::tab:hover:!selected { color: #475569; background: #f8fafc; }
QFrame#quickActionsBar { background-color: #ffffff; border-bottom: 1px solid #e2e8f0; }
QFrame#quickActionsBar QLabel { background: transparent; color: #94a3b8; font-size: 11px; font-weight: 600; }
QFrame#quickActionsBar QPushButton { background-color: #f1f5f9; color: #475569; border: 1px solid #e2e8f0; padding: 5px 12px; border-radius: 4px; font-size: 11px; font-weight: 600; }
QFrame#quickActionsBar QPushButton:hover { background-color: #e2e8f0; color: #1e293b; }
QTextEdit#inputText { background-color: #ffffff; color: #334155; border: none; border-right: 1px solid #e2e8f0; padding: 12px; font-family: 'Consolas', monospace; font-size: 12px; }
QFrame#resultsPanel { background-color: #f8fafc; border: none; }
QFrame#resultsPanelHeader { background-color: #f1f5f9; border-bottom: 1px solid #e2e8f0; }
QFrame#resultsPanelHeader QLabel { background: transparent; color: #475569; font-size: 11px; font-weight: 600; }
QTextEdit#resultText { background-color: #f8fafc; color: #334155; border: none; padding: 12px; font-family: 'Consolas', monospace; font-size: 11px; }
QFrame#bottomBar { background-color: #f1f5f9; border-top: 1px solid #e2e8f0; }
QFrame#bottomBar QLabel { background: transparent; color: #94a3b8; font-size: 12px; }
QPushButton#btnPrimary { background-color: #3b82f6; color: #ffffff; border: none; padding: 8px 20px; border-radius: 6px; font-size: 13px; font-weight: 600; }
QPushButton#btnPrimary:hover { background-color: #2563eb; }
QPushButton#btnPrimary:disabled { background-color: #cbd5e1; color: #94a3b8; }
QPushButton#btnSecondary { background-color: transparent; color: #475569; border: none; padding: 8px 16px; border-radius: 6px; font-size: 13px; }
QPushButton#btnSecondary:hover { background-color: #f1f5f9; color: #1e293b; }
QPushButton#btnSuccess { background-color: #22c55e; color: #ffffff; border: none; padding: 8px 20px; border-radius: 6px; font-size: 13px; font-weight: 600; }
QPushButton#btnSuccess:hover { background-color: #16a34a; }
QPushButton#btnDanger { background-color: #ef4444; color: #ffffff; border: none; padding: 8px 20px; border-radius: 6px; font-size: 13px; font-weight: 600; }
QPushButton#btnDanger:hover { background-color: #dc2626; }
QListWidget { background-color: #ffffff; color: #334155; border: 1px solid #e2e8f0; border-radius: 6px; padding: 4px; outline: none; font-size: 12px; }
QListWidget::item { padding: 8px 12px; border-radius: 4px; margin: 2px 0; }
QListWidget::item:selected { background-color: rgba(59, 130, 246, 0.1); color: #3b82f6; }
QListWidget::item:hover:!selected { background-color: #f8fafc; }
QTextEdit#helpText { background-color: #ffffff; color: #334155; border: none; padding: 24px; font-size: 13px; }
QCheckBox { color: #475569; font-size: 12px; spacing: 6px; }
QCheckBox::indicator { width: 16px; height: 16px; border: 2px solid #cbd5e1; border-radius: 4px; background: #ffffff; }
QCheckBox::indicator:checked { background: #3b82f6; border-color: #3b82f6; }
QStatusBar { background: #3b82f6; border: none; min-height: 22px; max-height: 22px; }
QStatusBar QLabel { color: #ffffff; font-size: 11px; font-weight: 600; padding: 0 6px; background: transparent; }
QScrollBar:vertical { background: #f0f2f5; width: 10px; border: none; }
QScrollBar::handle:vertical { background: #cbd5e1; border-radius: 5px; min-height: 20px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { background: #f0f2f5; height: 10px; border: none; }
QScrollBar::handle:horizontal { background: #cbd5e1; border-radius: 5px; min-width: 20px; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QSplitter::handle { background: #e2e8f0; }
QSplitter::handle:horizontal { width: 1px; }
QMessageBox { background-color: #ffffff; color: #1e293b; }
QMessageBox QPushButton { background-color: #f1f5f9; color: #1e293b; border: 1px solid #e2e8f0; padding: 6px 16px; border-radius: 4px; min-width: 80px; }
QGroupBox { font-weight: 600; font-size: 12px; border: 1px solid #e2e8f0; border-radius: 8px; margin-top: 12px; padding: 16px 12px 12px 12px; }
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; color: #475569; }
QFrame#editorHeader { background-color: #f1f5f9; border-bottom: 1px solid #e2e8f0; }
QFrame#editorHeader QLabel { background: transparent; font-size: 11px; }
QTreeWidget#reportsTree { background-color: #ffffff; color: #334155; border: none; outline: none; font-size: 12px; }
QTreeWidget#reportsTree::item { padding: 6px 8px; border-bottom: 1px solid #e2e8f0; }
QTreeWidget#reportsTree::item:selected { background-color: rgba(59, 130, 246, 0.1); color: #3b82f6; }
QTreeWidget#reportsTree::item:hover:!selected { background-color: #f8fafc; }
QTreeWidget#reportsTree::item:alternate { background-color: #f8fafc; }
QHeaderView::section { background-color: #f1f5f9; color: #475569; border: none; border-bottom: 1px solid #e2e8f0; border-right: 1px solid #e2e8f0; padding: 6px 8px; font-size: 11px; font-weight: 600; }
QSizeGrip { background: transparent; width: 16px; height: 16px; }
"""


# ─────────────────────────────────────────────
# Main window
# ─────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.loc = Localization.instance()
        self.dark_mode = True
        self.current_project = None
        self.export_project = None
        self._export_project_path = None
        self.scanner = ProjectScanner()
        self._workers = []
        self._report_search_worker = None
        self._report_found_count = 0

        self._setup_ui()
        self._apply_theme()
        self._setup_shortcuts()
        self._populate_directories()

    # ════════════════════════════════════════════
    #  UI SETUP
    # ════════════════════════════════════════════

    def _setup_ui(self):
        self.setWindowTitle(self.loc.t("app_title"))
        self.setMinimumSize(1000, 700)
        self.resize(1280, 800)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── header ──
        header = QFrame()
        header.setObjectName("headerFrame")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 8, 16, 8)

        title = QLabel("⚡ " + self.loc.t("app_title"))
        header_layout.addWidget(title)
        header_layout.addStretch()

        dir_label = QLabel(self.loc.t("working_directory") + ":")
        dir_label.setStyleSheet("font-weight: normal; font-size: 12px; color: #a9b1d6;")
        header_layout.addWidget(dir_label)

        self.dir_combo = QComboBox()
        self.dir_combo.setObjectName("dirCombo")
        self.dir_combo.setMinimumWidth(300)
        self.dir_combo.setEditable(True)
        header_layout.addWidget(self.dir_combo)

        browse_btn = QPushButton("📁 " + self.loc.t("browse"))
        browse_btn.clicked.connect(self._browse_directory)
        header_layout.addWidget(browse_btn)

        self.theme_btn = QPushButton()
        self.theme_btn.clicked.connect(self._toggle_theme)
        header_layout.addWidget(self.theme_btn)

        self.lang_btn = QPushButton()
        self.lang_btn.clicked.connect(self._toggle_language)
        header_layout.addWidget(self.lang_btn)

        main_layout.addWidget(header)

        # ── tabs ──
        self.tabs = QTabWidget()
        self.tabs.addTab(self._create_import_tab(), self.loc.t("tab_import"))
        self.tabs.addTab(self._create_export_tab(), self.loc.t("tab_export"))
        self.tabs.addTab(self._create_reports_tab(), self.loc.t("tab_reports"))
        self.tabs.addTab(self._create_help_tab(), self.loc.t("tab_help"))
        main_layout.addWidget(self.tabs)

        # ── bottom bar ──
        bottom = QFrame()
        bottom.setObjectName("bottomBar")
        bottom_layout = QHBoxLayout(bottom)
        bottom_layout.setContentsMargins(16, 4, 16, 4)

        self.status_label = QLabel(self.loc.t("ready"))
        bottom_layout.addWidget(self.status_label)
        bottom_layout.addStretch()

        self.char_count_label = QLabel(self.loc.t("chars_count", 0))
        bottom_layout.addWidget(self.char_count_label)

        size_grip = QSizeGrip(self)
        size_grip.setFixedSize(16, 16)
        bottom_layout.addWidget(size_grip, 0,
                                Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight)

        main_layout.addWidget(bottom)
        self._update_theme_buttons()

    # ── Import tab ──────────────────────────────

    def _create_import_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # quick-action bar (fixed height)
        actions_bar = QFrame()
        actions_bar.setObjectName("quickActionsBar")
        actions_bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        actions_bar.setFixedHeight(44)
        actions_layout = QHBoxLayout(actions_bar)
        actions_layout.setContentsMargins(16, 6, 16, 6)
        actions_layout.setSpacing(6)

        prompt_label = QLabel(self.loc.t("copy_prompt_for_ai"))
        actions_layout.addWidget(prompt_label)

        prompt_keys = PromptManager.get_variant_keys()
        prompt_names = {
            "full": "prompt_full",
            "short": "prompt_short",
            "continue": "prompt_continue",
            "refactor": "prompt_refactor",
            "add_feature": "prompt_add_feature",
        }
        for key in prompt_keys:
            name = self.loc.t(prompt_names.get(key, key))
            btn = QPushButton(name)
            btn.setProperty("prompt_key", key)
            btn.clicked.connect(lambda checked, k=key: self._copy_prompt(k))
            actions_layout.addWidget(btn)

        actions_layout.addStretch()
        layout.addWidget(actions_bar)

        # splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # left — input
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        editor_header = QFrame()
        editor_header.setObjectName("editorHeader")
        editor_header.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        editor_header.setFixedHeight(32)
        eh_layout = QHBoxLayout(editor_header)
        eh_layout.setContentsMargins(12, 4, 12, 4)
        paste_label = QLabel("📝 " + self.loc.t("paste_ai_response"))
        paste_label.setStyleSheet("color: #a9b1d6;")
        eh_layout.addWidget(paste_label)
        eh_layout.addStretch()
        left_layout.addWidget(editor_header)

        self.input_text = QTextEdit()
        self.input_text.setObjectName("inputText")
        self.input_text.setPlaceholderText(self.loc.t("placeholder_input"))
        self.input_text.textChanged.connect(self._on_text_changed)
        left_layout.addWidget(self.input_text)

        btn_frame = QFrame()
        btn_frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        btn_frame.setFixedHeight(50)
        btn_layout = QHBoxLayout(btn_frame)
        btn_layout.setContentsMargins(12, 6, 12, 6)

        self.analyze_btn = QPushButton("🔍 " + self.loc.t("analyze"))
        self.analyze_btn.setObjectName("btnPrimary")
        self.analyze_btn.clicked.connect(self._analyze)
        btn_layout.addWidget(self.analyze_btn)

        self.deploy_btn = QPushButton("🚀 " + self.loc.t("create_project"))
        self.deploy_btn.setObjectName("btnSuccess")
        self.deploy_btn.clicked.connect(self._deploy)
        btn_layout.addWidget(self.deploy_btn)

        self.overwrite_cb = QCheckBox(self.loc.t("overwrite_existing"))
        btn_layout.addWidget(self.overwrite_cb)

        btn_layout.addStretch()

        clear_btn = QPushButton(self.loc.t("clear"))
        clear_btn.setObjectName("btnSecondary")
        clear_btn.clicked.connect(self._clear_input)
        btn_layout.addWidget(clear_btn)

        left_layout.addWidget(btn_frame)
        splitter.addWidget(left_widget)

        # right — results
        right_widget = QFrame()
        right_widget.setObjectName("resultsPanel")
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        result_header = QFrame()
        result_header.setObjectName("resultsPanelHeader")
        result_header.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        result_header.setFixedHeight(32)
        rh_layout = QHBoxLayout(result_header)
        rh_layout.setContentsMargins(12, 4, 12, 4)
        result_title = QLabel("📋 " + self.loc.t("analysis_result"))
        rh_layout.addWidget(result_title)
        right_layout.addWidget(result_header)

        self.result_text = QTextEdit()
        self.result_text.setObjectName("resultText")
        self.result_text.setReadOnly(True)
        right_layout.addWidget(self.result_text)
        splitter.addWidget(right_widget)

        splitter.setSizes([600, 400])
        layout.addWidget(splitter)
        return widget

    # ── Export tab ──────────────────────────────

    def _create_export_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        top_layout = QHBoxLayout()
        self.export_label = QLabel(self.loc.t("select_project_to_export"))
        self.export_label.setStyleSheet("font-size: 14px; font-weight: 600;")
        top_layout.addWidget(self.export_label)
        top_layout.addStretch()

        find_btn = QPushButton("🔍 " + self.loc.t("find_projects"))
        find_btn.setObjectName("btnPrimary")
        find_btn.clicked.connect(self._find_projects)
        top_layout.addWidget(find_btn)

        browse_btn = QPushButton("📁 " + self.loc.t("browse_folder"))
        browse_btn.setObjectName("btnSecondary")
        browse_btn.clicked.connect(self._browse_project_folder)
        top_layout.addWidget(browse_btn)

        layout.addLayout(top_layout)

        self.project_list = QListWidget()
        self.project_list.currentItemChanged.connect(self._on_project_selected)
        layout.addWidget(self.project_list)

        export_btn_layout = QHBoxLayout()
        self.pdf_btn = QPushButton("📄 " + self.loc.t("export_pdf"))
        self.pdf_btn.setObjectName("btnPrimary")
        self.pdf_btn.clicked.connect(self._export_pdf)
        export_btn_layout.addWidget(self.pdf_btn)

        self.copy_format_btn = QPushButton("📋 " + self.loc.t("copy_ai_format"))
        self.copy_format_btn.setObjectName("btnSecondary")
        self.copy_format_btn.clicked.connect(self._copy_ai_format)
        export_btn_layout.addWidget(self.copy_format_btn)
        export_btn_layout.addStretch()
        layout.addLayout(export_btn_layout)

        preview_label = QLabel(self.loc.t("export_preview"))
        preview_label.setStyleSheet("font-weight: 600; margin-top: 8px;")
        layout.addWidget(preview_label)

        self.export_preview = QTextEdit()
        self.export_preview.setObjectName("resultText")
        self.export_preview.setReadOnly(True)
        layout.addWidget(self.export_preview)

        return widget

    # ── Reports tab ─────────────────────────────

    def _create_reports_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        # buttons
        btn_layout = QHBoxLayout()

        refresh_btn = QPushButton("🔍 " + self.loc.t("reports_refresh"))
        refresh_btn.setObjectName("btnPrimary")
        refresh_btn.setToolTip("Поиск в рабочей директории и подпапках")
        refresh_btn.clicked.connect(self._refresh_reports)
        btn_layout.addWidget(refresh_btn)

        scan_all_btn = QPushButton("💽 Поиск по дискам")
        scan_all_btn.setObjectName("btnSecondary")
        scan_all_btn.setToolTip("Глубокий поиск по всем дискам")
        scan_all_btn.clicked.connect(self._refresh_reports_all_drives)
        btn_layout.addWidget(scan_all_btn)

        self.stop_search_btn = QPushButton("⏹ Стоп")
        self.stop_search_btn.setObjectName("btnDanger")
        self.stop_search_btn.clicked.connect(self._stop_report_search)
        self.stop_search_btn.setVisible(False)
        btn_layout.addWidget(self.stop_search_btn)

        btn_layout.addStretch()

        open_btn = QPushButton("📂 " + self.loc.t("reports_open"))
        open_btn.setObjectName("btnSecondary")
        open_btn.clicked.connect(self._open_report)
        btn_layout.addWidget(open_btn)

        copy_path_btn = QPushButton("📋 " + self.loc.t("reports_copy_path"))
        copy_path_btn.setObjectName("btnSecondary")
        copy_path_btn.clicked.connect(self._copy_report_path)
        btn_layout.addWidget(copy_path_btn)

        copy_file_btn = QPushButton("📄 Копировать файл")
        copy_file_btn.setObjectName("btnSecondary")
        copy_file_btn.clicked.connect(self._copy_report_file)
        btn_layout.addWidget(copy_file_btn)

        open_folder_btn = QPushButton("📁 " + self.loc.t("reports_open_folder"))
        open_folder_btn.setObjectName("btnSecondary")
        open_folder_btn.clicked.connect(self._open_report_folder)
        btn_layout.addWidget(open_folder_btn)

        delete_btn = QPushButton("🗑 " + self.loc.t("reports_delete"))
        delete_btn.setObjectName("btnDanger")
        delete_btn.clicked.connect(self._delete_report)
        btn_layout.addWidget(delete_btn)

        layout.addLayout(btn_layout)

        # tree
        self.reports_tree = DraggableReportsTree()
        self.reports_tree.setObjectName("reportsTree")
        self.reports_tree.setAlternatingRowColors(True)
        self.reports_tree.setRootIsDecorated(False)
        self.reports_tree.setHeaderLabels([
            self.loc.t("reports_col_name"),
            self.loc.t("reports_col_project"),
            self.loc.t("reports_col_size"),
            self.loc.t("reports_col_date"),
            "Путь",
        ])
        h = self.reports_tree.header()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)

        self.reports_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.reports_tree.customContextMenuRequested.connect(self._reports_context_menu)
        layout.addWidget(self.reports_tree)

        # status + progress
        status_layout = QHBoxLayout()
        self.reports_status = QLabel("")
        status_layout.addWidget(self.reports_status)
        status_layout.addStretch()
        self.reports_progress = QLabel("")
        self.reports_progress.setStyleSheet("color: #565f89; font-size: 11px;")
        status_layout.addWidget(self.reports_progress)
        layout.addLayout(status_layout)

        return widget

    # ── Help tab ────────────────────────────────

    def _create_help_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        help_text = QTextEdit()
        help_text.setObjectName("helpText")
        help_text.setReadOnly(True)
        help_text.setHtml(self.loc.t("help_content"))
        layout.addWidget(help_text)
        return widget

    # ════════════════════════════════════════════
    #  SHORTCUTS / THEME / LANGUAGE
    # ════════════════════════════════════════════

    def _setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+Return"), self, self._analyze)
        QShortcut(QKeySequence("Ctrl+D"), self, self._deploy)
        QShortcut(QKeySequence("Ctrl+E"), self, self._export_pdf)
        QShortcut(QKeySequence("Ctrl+T"), self, self._toggle_theme)

    def _populate_directories(self):
        dirs = self.scanner.find_project_directories()
        home = str(Path.home())
        if home not in dirs:
            dirs.insert(0, home)
        self.dir_combo.clear()
        for d in dirs:
            self.dir_combo.addItem(d)

    def _apply_theme(self):
        self.setStyleSheet(DARK_STYLE if self.dark_mode else LIGHT_STYLE)
        self._update_theme_buttons()

    def _update_theme_buttons(self):
        if self.dark_mode:
            self.theme_btn.setText("☀️ " + self.loc.t("theme_light"))
        else:
            self.theme_btn.setText("🌙 " + self.loc.t("theme_dark"))
        self.lang_btn.setText("🌐 " + self.loc.t("lang_label"))

    def _toggle_theme(self):
        self.dark_mode = not self.dark_mode
        self._apply_theme()

    def _toggle_language(self):
        self.loc.toggle_lang()
        self._update_all_texts()

    def _update_all_texts(self):
        self.setWindowTitle(self.loc.t("app_title"))
        self._update_theme_buttons()
        self.status_label.setText(self.loc.t("ready"))
        self.tabs.setTabText(0, self.loc.t("tab_import"))
        self.tabs.setTabText(1, self.loc.t("tab_export"))
        self.tabs.setTabText(2, self.loc.t("tab_reports"))
        self.tabs.setTabText(3, self.loc.t("tab_help"))
        self.analyze_btn.setText("🔍 " + self.loc.t("analyze"))
        self.deploy_btn.setText("🚀 " + self.loc.t("create_project"))
        self.overwrite_cb.setText(self.loc.t("overwrite_existing"))
        self.pdf_btn.setText("📄 " + self.loc.t("export_pdf"))
        self.copy_format_btn.setText("📋 " + self.loc.t("copy_ai_format"))
        self.export_label.setText(self.loc.t("select_project_to_export"))

    def _browse_directory(self):
        path = QFileDialog.getExistingDirectory(self, self.loc.t("select_directory"))
        if path:
            idx = self.dir_combo.findText(path)
            if idx == -1:
                self.dir_combo.insertItem(0, path)
            self.dir_combo.setCurrentText(path)

    def _on_text_changed(self):
        text = self.input_text.toPlainText()
        self.char_count_label.setText(self.loc.t("chars_count", len(text)))

    # ════════════════════════════════════════════
    #  IMPORT  — analyse / deploy
    # ════════════════════════════════════════════

    def _copy_prompt(self, key):
        try:
            prompt = PromptManager.get_prompt(key)
            QApplication.clipboard().setText(prompt)
            variant = PromptManager.get_variant(key)
            self.status_label.setText(self.loc.t("prompt_copied", variant.title))
        except Exception as e:
            self.status_label.setText(str(e))

    def _clear_input(self):
        self.input_text.clear()
        self.result_text.clear()
        self.current_project = None
        self.status_label.setText(self.loc.t("text_cleared"))

    def _analyze(self):
        text = self.input_text.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, self.loc.t("no_text_to_analyze"),
                                self.loc.t("paste_text_first"))
            return
        self.status_label.setText(self.loc.t("analyzing"))
        self.analyze_btn.setEnabled(False)

        worker = ParseWorker(text)
        worker.finished.connect(self._on_parse_done)
        worker.error.connect(self._on_parse_error)
        self._workers.append(worker)
        worker.start()

    def _on_parse_done(self, project):
        self.current_project = project
        self.analyze_btn.setEnabled(True)

        r = []
        r.append(self.loc.t("project_name", project.metadata.name))
        r.append(self.loc.t("files_count", project.file_count))
        r.append(self.loc.t("total_lines", project.total_lines))
        r.append("")
        if project.metadata.version:
            r.append(f"Version: {project.metadata.version}")
        if project.metadata.language:
            r.append(f"Language: {project.metadata.language}")
        if project.metadata.framework:
            r.append(f"Framework: {project.metadata.framework}")
        if project.metadata.install_command:
            r.append(f"Install: {project.metadata.install_command}")
        if project.metadata.run_command:
            r.append(f"Run: {project.metadata.run_command}")
        r.append("")
        r.append("─" * 40)
        r.append(self.loc.t("file_list"))
        for f in project.files:
            r.append(f"  {f.relative_path} ({len(f.content.splitlines())} lines)")
        r.append("")
        r.append("─" * 40)
        r.append("Structure:")
        r.append(project.get_tree())

        self.result_text.setPlainText("\n".join(r))
        self.status_label.setText(self.loc.t("analysis_complete"))

    def _on_parse_error(self, error):
        self.analyze_btn.setEnabled(True)
        self.result_text.setPlainText(error)
        self.status_label.setText(self.loc.t("analysis_error"))
        QMessageBox.critical(self, self.loc.t("analysis_error"), error)

    def _deploy(self):
        if not self.current_project:
            QMessageBox.warning(self, self.loc.t("no_project_analyzed"),
                                self.loc.t("analyze_first"))
            return
        target_dir = self.dir_combo.currentText().strip()
        if not target_dir:
            QMessageBox.warning(self, self.loc.t("no_directory_selected"),
                                self.loc.t("select_working_directory"))
            return
        self.status_label.setText(self.loc.t("deploying"))
        self.deploy_btn.setEnabled(False)

        worker = DeployWorker(self.current_project, target_dir,
                              self.overwrite_cb.isChecked())
        worker.finished.connect(self._on_deploy_done)
        worker.error.connect(self._on_deploy_error)
        self._workers.append(worker)
        worker.start()

    def _on_deploy_done(self, path):
        self.deploy_btn.setEnabled(True)
        self.status_label.setText(self.loc.t("project_created"))
        QMessageBox.information(self, self.loc.t("project_created"),
                                self.loc.t("project_created_at", path))

    def _on_deploy_error(self, error):
        self.deploy_btn.setEnabled(True)
        self.status_label.setText(self.loc.t("deploy_error"))
        QMessageBox.critical(self, self.loc.t("deploy_error"), error)

    # ════════════════════════════════════════════
    #  EXPORT
    # ════════════════════════════════════════════

    def _find_projects(self):
        target_dir = self.dir_combo.currentText().strip()
        if not target_dir or not os.path.isdir(target_dir):
            QMessageBox.warning(self, self.loc.t("no_directory_selected"),
                                self.loc.t("select_working_directory"))
            return
        self.status_label.setText(self.loc.t("scanning"))
        self.project_list.clear()
        try:
            for entry in sorted(Path(target_dir).iterdir()):
                if entry.is_dir() and not entry.name.startswith('.'):
                    if any((entry / ind).exists()
                           for ind in self.scanner.PROJECT_INDICATORS):
                        item = QListWidgetItem(f"📁 {entry.name}")
                        item.setData(Qt.ItemDataRole.UserRole, str(entry))
                        self.project_list.addItem(item)
        except Exception as e:
            QMessageBox.critical(self, self.loc.t("scan_error"), str(e))
        self.status_label.setText(
            self.loc.t("found_projects", self.project_list.count()))

    def _browse_project_folder(self):
        path = QFileDialog.getExistingDirectory(
            self, self.loc.t("select_project_folder"))
        if path:
            item = QListWidgetItem(f"📁 {Path(path).name}")
            item.setData(Qt.ItemDataRole.UserRole, path)
            self.project_list.addItem(item)
            self.project_list.setCurrentItem(item)

    def _on_project_selected(self, current, previous):
        if not current:
            return
        path = current.data(Qt.ItemDataRole.UserRole)
        if not path or not os.path.isdir(path):
            return
        try:
            self.status_label.setText(self.loc.t("scanning"))
            project = self.scanner.scan_project(path)
            self.export_project = project
            self._export_project_path = path

            preview = [
                f"Project: {project.metadata.name}",
                f"Files: {project.file_count}",
                f"Lines: {project.total_lines}",
            ]
            if project.metadata.language:
                preview.append(f"Language: {project.metadata.language}")
            preview.append("")
            preview.append(project.get_tree())
            self.export_preview.setPlainText("\n".join(preview))
            self.status_label.setText(self.loc.t("ready"))
        except Exception as e:
            self.export_preview.setPlainText(str(e))
            self.status_label.setText(self.loc.t("scan_error"))

    def _export_pdf(self):
        if not self.export_project:
            QMessageBox.warning(self, self.loc.t("no_project_selected"),
                                self.loc.t("select_project_first"))
            return
        project_path = self._export_project_path
        if not project_path or not os.path.isdir(project_path):
            QMessageBox.warning(self, self.loc.t("no_project_selected"),
                                self.loc.t("select_project_first"))
            return

        filename = f"{self.export_project.metadata.name}.pdf"
        output_path = os.path.join(project_path, filename)
        if os.path.exists(output_path):
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.export_project.metadata.name}_{ts}.pdf"
            output_path = os.path.join(project_path, filename)

        self.status_label.setText(self.loc.t("exporting_pdf"))
        self.pdf_btn.setEnabled(False)

        worker = ExportPDFWorker(self.export_project, output_path)
        worker.finished.connect(self._on_pdf_done)
        worker.error.connect(self._on_pdf_error)
        self._workers.append(worker)
        worker.start()

    def _on_pdf_done(self, path):
        self.pdf_btn.setEnabled(True)
        self.status_label.setText(self.loc.t("pdf_exported"))
        QMessageBox.information(self, self.loc.t("pdf_exported"),
                                self.loc.t("pdf_saved_at", path))
        self._refresh_reports()

    def _on_pdf_error(self, error):
        self.pdf_btn.setEnabled(True)
        self.status_label.setText(self.loc.t("pdf_export_error"))
        QMessageBox.critical(self, self.loc.t("pdf_export_error"), error)

    def _copy_ai_format(self):
        if not self.export_project:
            QMessageBox.warning(self, self.loc.t("no_project_selected"),
                                self.loc.t("select_project_first"))
            return
        exporter = ProjectExporter()
        text = exporter.export_text(self.export_project)
        QApplication.clipboard().setText(text)
        self.status_label.setText(self.loc.t("ai_format_copied"))

    # ════════════════════════════════════════════
    #  REPORTS — search / open / copy / delete
    # ════════════════════════════════════════════

    def _refresh_reports(self):
        """Рекурсивный поиск отчётов в рабочей директории."""
        work_dir = self.dir_combo.currentText().strip()
        if not work_dir or not os.path.isdir(work_dir):
            self.reports_status.setText(self.loc.t("reports_no_dir"))
            return
        self._start_report_search(work_dir, all_drives=False)

    def _refresh_reports_all_drives(self):
        reply = QMessageBox.question(
            self, "Поиск по всем дискам",
            "Поиск по всем дискам может занять несколько минут.\nПродолжить?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        self._start_report_search("", all_drives=True)

    def _start_report_search(self, search_root: str, all_drives: bool):
        self._stop_report_search()

        self.reports_tree.clear()
        self.reports_status.setText("🔍 Поиск отчётов...")
        self.reports_progress.setText("")
        self.stop_search_btn.setVisible(True)
        self._report_found_count = 0

        worker = ReportSearchWorker(search_root, all_drives)
        worker.found.connect(self._on_report_found)
        worker.progress.connect(self._on_search_progress)
        worker.finished_signal.connect(self._on_search_finished)
        self._report_search_worker = worker
        self._workers.append(worker)
        worker.start()

    def _on_report_found(self, pdf_path: str, project_name: str):
        try:
            stat = os.stat(pdf_path)
            size = stat.st_size
            if size < 1024:
                size_str = f"{size} B"
            elif size < 1024 * 1024:
                size_str = f"{size / 1024:.1f} KB"
            else:
                size_str = f"{size / (1024 * 1024):.1f} MB"

            mod_time = datetime.datetime.fromtimestamp(stat.st_mtime)
            date_str = mod_time.strftime("%Y-%m-%d %H:%M")

            item = QTreeWidgetItem([
                Path(pdf_path).name,
                project_name,
                size_str,
                date_str,
                pdf_path,
            ])
            item.setData(0, Qt.ItemDataRole.UserRole, pdf_path)
            self.reports_tree.addTopLevelItem(item)

            self._report_found_count += 1
            self.reports_status.setText(
                f"🔍 Найдено отчётов: {self._report_found_count}...")
        except Exception:
            pass

    def _on_search_progress(self, current_dir: str):
        display = current_dir
        if len(display) > 70:
            display = "..." + display[-67:]
        self.reports_progress.setText(display)

    def _on_search_finished(self, total: int):
        self.stop_search_btn.setVisible(False)
        self.reports_progress.setText("")
        if total == 0:
            self.reports_status.setText(self.loc.t("reports_empty"))
        else:
            self.reports_status.setText(self.loc.t("reports_found", total))
        self._report_search_worker = None

    def _stop_report_search(self):
        if (self._report_search_worker
                and self._report_search_worker.isRunning()):
            self._report_search_worker.stop()
            self._report_search_worker.wait(3000)
        self.stop_search_btn.setVisible(False)
        self.reports_progress.setText("")
        self._report_search_worker = None

    # ── report helpers ──────────────────────────

    def _get_selected_report_path(self) -> Optional[str]:
        item = self.reports_tree.currentItem()
        if item:
            return item.data(0, Qt.ItemDataRole.UserRole)
        return None

    def _open_report(self):
        path = self._get_selected_report_path()
        if not path:
            return
        try:
            if sys.platform == "win32":
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.run(["open", path])
            else:
                subprocess.run(["xdg-open", path])
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _copy_report_path(self):
        path = self._get_selected_report_path()
        if path:
            QApplication.clipboard().setText(path)
            self.status_label.setText(self.loc.t("reports_path_copied"))

    def _copy_report_file(self):
        """Копирует файл в буфер обмена (как Ctrl+C в проводнике)."""
        path = self._get_selected_report_path()
        if not path or not os.path.isfile(path):
            return
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(path)])
        QApplication.clipboard().setMimeData(mime)
        self.status_label.setText(
            f"Файл скопирован в буфер: {Path(path).name}")

    def _open_report_folder(self):
        path = self._get_selected_report_path()
        if not path:
            return
        folder = str(Path(path).parent)
        try:
            if sys.platform == "win32":
                subprocess.run(["explorer", "/select,",
                                path.replace("/", "\\")])
            elif sys.platform == "darwin":
                subprocess.run(["open", "-R", path])
            else:
                subprocess.run(["xdg-open", folder])
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _delete_report(self):
        path = self._get_selected_report_path()
        if not path:
            return
        reply = QMessageBox.question(
            self,
            self.loc.t("reports_delete_confirm"),
            self.loc.t("reports_delete_confirm_text", Path(path).name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                os.remove(path)
                self.status_label.setText(
                    self.loc.t("reports_deleted", Path(path).name))
                self._refresh_reports()
            except Exception as e:
                QMessageBox.critical(
                    self, self.loc.t("reports_delete_error"), str(e))

    def _reports_context_menu(self, pos):
        menu = QMenu(self)
        item = self.reports_tree.itemAt(pos)
        if item:
            menu.addAction("📂 " + self.loc.t("reports_open"),
                           self._open_report)
            menu.addAction("📋 " + self.loc.t("reports_copy_path"),
                           self._copy_report_path)
            menu.addAction("📄 Копировать файл",
                           self._copy_report_file)
            menu.addAction("📁 " + self.loc.t("reports_open_folder"),
                           self._open_report_folder)
            menu.addSeparator()
            menu.addAction("🗑 " + self.loc.t("reports_delete"),
                           self._delete_report)
            menu.addSeparator()

        menu.addAction("🔍 Обновить", self._refresh_reports)
        menu.addAction("💽 Поиск по дискам",
                       self._refresh_reports_all_drives)

        if (self._report_search_worker
                and self._report_search_worker.isRunning()):
            menu.addAction("⏹ Остановить поиск",
                           self._stop_report_search)

        menu.exec(self.reports_tree.viewport().mapToGlobal(pos))