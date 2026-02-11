# core/exporter.py
import os
import sys
from pathlib import Path
from typing import Optional
from models.project import Project, ProjectFile, ProjectMetadata
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Preformatted,
    Table, TableStyle, PageBreak
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import logging

logger = logging.getLogger(__name__)


def _find_system_font():
    candidates = []
    if sys.platform == "win32":
        windir = os.environ.get("WINDIR", "C:\\Windows")
        fonts_dir = os.path.join(windir, "Fonts")
        candidates = [
            os.path.join(fonts_dir, "consola.ttf"),
            os.path.join(fonts_dir, "cour.ttf"),
            os.path.join(fonts_dir, "lucon.ttf"),
            os.path.join(fonts_dir, "arial.ttf"),
            os.path.join(fonts_dir, "segoeui.ttf"),
        ]
    elif sys.platform == "darwin":
        candidates = [
            "/System/Library/Fonts/Menlo.ttc",
            "/System/Library/Fonts/Courier.dfont",
            "/Library/Fonts/Arial.ttf",
        ]
    else:
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
            "/usr/share/fonts/truetype/ubuntu/UbuntuMono-R.ttf",
            "/usr/share/fonts/TTF/DejaVuSansMono.ttf",
        ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def _find_system_font_bold():
    if sys.platform == "win32":
        windir = os.environ.get("WINDIR", "C:\\Windows")
        fonts_dir = os.path.join(windir, "Fonts")
        candidates = [
            os.path.join(fonts_dir, "consolab.ttf"),
            os.path.join(fonts_dir, "courbd.ttf"),
            os.path.join(fonts_dir, "arialbd.ttf"),
            os.path.join(fonts_dir, "segoeuib.ttf"),
        ]
    elif sys.platform == "darwin":
        candidates = [
            "/System/Library/Fonts/Menlo.ttc",
            "/Library/Fonts/Arial Bold.ttf",
        ]
    else:
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf",
            "/usr/share/fonts/truetype/ubuntu/UbuntuMono-B.ttf",
        ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def _find_sans_font():
    if sys.platform == "win32":
        windir = os.environ.get("WINDIR", "C:\\Windows")
        fonts_dir = os.path.join(windir, "Fonts")
        candidates = [
            os.path.join(fonts_dir, "segoeui.ttf"),
            os.path.join(fonts_dir, "arial.ttf"),
            os.path.join(fonts_dir, "tahoma.ttf"),
        ]
    elif sys.platform == "darwin":
        candidates = [
            "/System/Library/Fonts/Helvetica.ttc",
            "/Library/Fonts/Arial.ttf",
        ]
    else:
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf",
        ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def _find_sans_font_bold():
    if sys.platform == "win32":
        windir = os.environ.get("WINDIR", "C:\\Windows")
        fonts_dir = os.path.join(windir, "Fonts")
        candidates = [
            os.path.join(fonts_dir, "segoeuib.ttf"),
            os.path.join(fonts_dir, "arialbd.ttf"),
            os.path.join(fonts_dir, "tahomabd.ttf"),
        ]
    elif sys.platform == "darwin":
        candidates = [
            "/Library/Fonts/Arial Bold.ttf",
        ]
    else:
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf",
        ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


class ProjectExporter:

    MONO_FONT = "Courier"
    MONO_FONT_BOLD = "Courier-Bold"
    SANS_FONT = "Helvetica"
    SANS_FONT_BOLD = "Helvetica-Bold"

    def __init__(self):
        self._register_fonts()
        self.styles = self._create_styles()

    def _register_fonts(self):
        mono = _find_system_font()
        if mono:
            try:
                pdfmetrics.registerFont(TTFont("MonoCyr", mono))
                self.MONO_FONT = "MonoCyr"
                logger.info("Mono font registered: " + mono)
            except Exception as e:
                logger.warning("Failed to register mono font: " + str(e))

        mono_bold = _find_system_font_bold()
        if mono_bold:
            try:
                pdfmetrics.registerFont(TTFont("MonoCyrBold", mono_bold))
                self.MONO_FONT_BOLD = "MonoCyrBold"
            except Exception:
                self.MONO_FONT_BOLD = self.MONO_FONT

        sans = _find_sans_font()
        if sans:
            try:
                pdfmetrics.registerFont(TTFont("SansCyr", sans))
                self.SANS_FONT = "SansCyr"
                logger.info("Sans font registered: " + sans)
            except Exception as e:
                logger.warning("Failed to register sans font: " + str(e))

        sans_bold = _find_sans_font_bold()
        if sans_bold:
            try:
                pdfmetrics.registerFont(TTFont("SansCyrBold", sans_bold))
                self.SANS_FONT_BOLD = "SansCyrBold"
            except Exception:
                self.SANS_FONT_BOLD = self.SANS_FONT

    def _create_styles(self):
        styles = getSampleStyleSheet()

        # override built-in styles to use our fonts
        styles["Title"].fontName = self.SANS_FONT_BOLD
        styles["Title"].fontSize = 20
        styles["Title"].leading = 26

        styles["Heading1"].fontName = self.SANS_FONT_BOLD
        styles["Heading1"].fontSize = 14
        styles["Heading1"].leading = 18

        styles["Normal"].fontName = self.SANS_FONT
        styles["Normal"].fontSize = 10
        styles["Normal"].leading = 13

        styles.add(ParagraphStyle(
            name='CodeBlock',
            fontName=self.MONO_FONT,
            fontSize=7,
            leading=9,
            leftIndent=10,
            rightIndent=10,
            backColor=colors.Color(0.95, 0.95, 0.95),
            borderColor=colors.Color(0.8, 0.8, 0.8),
            borderWidth=0.5,
            borderPadding=5,
            spaceBefore=5,
            spaceAfter=10,
        ))

        styles.add(ParagraphStyle(
            name='FilePath',
            fontName=self.MONO_FONT_BOLD,
            fontSize=10,
            leading=14,
            textColor=colors.Color(0.1, 0.3, 0.6),
            spaceBefore=15,
            spaceAfter=5,
        ))

        styles.add(ParagraphStyle(
            name='MetaKey',
            fontName=self.SANS_FONT_BOLD,
            fontSize=9,
            textColor=colors.Color(0.3, 0.3, 0.3),
        ))

        styles.add(ParagraphStyle(
            name='MetaValue',
            fontName=self.SANS_FONT,
            fontSize=9,
        ))

        styles.add(ParagraphStyle(
            name='TreeStyle',
            fontName=self.MONO_FONT,
            fontSize=8,
            leading=11,
            leftIndent=15,
            backColor=colors.Color(0.97, 0.97, 1.0),
            borderPadding=8,
            spaceBefore=5,
            spaceAfter=10,
        ))

        return styles

    def export_pdf(self, project, output_path):
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=1.5 * cm,
            leftMargin=1.5 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
            title="Project: " + project.metadata.name,
            author="AI Code Deployer"
        )

        story = []

        # title page
        story.append(Spacer(1, 4 * cm))
        story.append(Paragraph(
            self._escape(project.metadata.name),
            self.styles['Title']
        ))

        if project.metadata.description:
            story.append(Spacer(1, 0.5 * cm))
            story.append(Paragraph(
                self._escape(project.metadata.description),
                self.styles['Normal']
            ))

        story.append(Spacer(1, 1 * cm))

        meta_data = self._build_meta_table(project.metadata)
        if meta_data:
            table = Table(meta_data, colWidths=[4 * cm, 12 * cm])
            table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (0, -1), self.SANS_FONT_BOLD),
                ('FONTNAME', (1, 0), (1, -1), self.SANS_FONT),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('TEXTCOLOR', (0, 0), (0, -1), colors.Color(0.3, 0.3, 0.3)),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
            ]))
            story.append(table)

        story.append(Spacer(1, 0.5 * cm))
        stats_text = "Files: " + str(project.file_count) + " | Lines: " + str(project.total_lines)
        story.append(Paragraph(stats_text, self.styles['Normal']))

        story.append(PageBreak())

        # structure
        story.append(Paragraph("Project Structure", self.styles['Heading1']))
        story.append(Preformatted(project.get_tree(), self.styles['TreeStyle']))
        story.append(Spacer(1, 0.5 * cm))
        story.append(PageBreak())

        # files
        story.append(Paragraph("Project Files", self.styles['Heading1']))
        story.append(Spacer(1, 0.3 * cm))

        for i, pf in enumerate(project.files):
            story.append(Paragraph("=" * 60, self.styles['Normal']))
            story.append(Paragraph(
                self._escape(pf.relative_path),
                self.styles['FilePath']
            ))

            if pf.description:
                story.append(Paragraph(
                    "<i>" + self._escape(pf.description) + "</i>",
                    self.styles['Normal']
                ))

            lang_info = "[" + pf.language + "]" if pf.language else ""
            lines_count = len(pf.content.splitlines())
            info_text = lang_info + " " + str(lines_count) + " lines"
            story.append(Paragraph(
                "<font size=7 color='gray'>" + info_text + "</font>",
                self.styles['Normal']
            ))

            code_text = pf.content
            if len(code_text) > 15000:
                code_text = code_text[:15000] + "\n\n... (truncated)"

            story.append(Preformatted(code_text, self.styles['CodeBlock']))
            story.append(Spacer(1, 0.5 * cm))

            if (i + 1) % 3 == 0 and i < len(project.files) - 1:
                story.append(PageBreak())

        # ai format section
        story.append(PageBreak())
        story.append(Paragraph("AI Format (for reimport)", self.styles['Heading1']))
        story.append(Paragraph(
            "Copy text below into AI Code Deployer to recreate this project:",
            self.styles['Normal']
        ))
        story.append(Spacer(1, 0.3 * cm))

        ai_text = project.to_ai_format()
        if len(ai_text) > 30000:
            ai_text = ai_text[:30000] + "\n\n... (truncated)"

        story.append(Preformatted(ai_text, self.styles['CodeBlock']))

        doc.build(story)
        logger.info("PDF created: " + output_path)
        return output_path

    def export_text(self, project):
        return project.to_ai_format()

    def _build_meta_table(self, meta):
        rows = []
        fields = [
            ("Version:", meta.version),
            ("Author:", meta.author),
            ("Language:", meta.language),
            ("Framework:", meta.framework),
            ("Run:", meta.run_command),
            ("Build:", meta.build_command),
            ("Install:", meta.install_command),
        ]
        for label, value in fields:
            if value:
                rows.append([label, value])
        return rows

    def _escape(self, text):
        return (text
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
        )