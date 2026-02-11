# core/parser.py
import re
from typing import Optional, List
from pathlib import Path
from models.project import Project, ProjectFile, ProjectMetadata
from core.prompt_manager import restore_code
import logging

logger = logging.getLogger(__name__)


class AIFormatParser:

    def parse(self, text: str) -> Project:
        text = text.strip()
        if "PROJSTART" in text:
            return self._parse_plain(text)
        if "===PROJECT_START===" in text:
            return self._parse_legacy_strict(text)
        if "[PROJECT_BEGIN]" in text:
            return self._parse_legacy_bracket(text)
        return self._parse_markdown(text)

    def _parse_plain(self, text: str) -> Project:
        project = Project()
        start = text.find("PROJSTART")
        end = text.find("PROJEND")
        if start != -1:
            text = text[start + 9:]
        if end != -1:
            text = text[:text.find("PROJEND")]
        meta_start = text.find("METASTART")
        meta_end = text.find("METAEND")
        if meta_start != -1 and meta_end != -1:
            meta_text = text[meta_start + 9:meta_end]
            project.metadata = self._parse_meta(meta_text)
        struct_start = text.find("STRUCTSTART")
        struct_end = text.find("STRUCTEND")
        if struct_start != -1 and struct_end != -1:
            raw_struct = text[struct_start + 11:struct_end].strip()
            project.structure_description = restore_code(raw_struct)
        file_chunks = text.split("FILESTART")
        for chunk in file_chunks[1:]:
            end_pos = chunk.find("FILEEND")
            if end_pos != -1:
                chunk = chunk[:end_pos]
            pf = self._parse_plain_file(chunk)
            if pf:
                project.files.append(pf)
        logger.info("Parsed: " + project.metadata.name + " " + str(len(project.files)) + " files")
        return project

    def _parse_meta(self, text: str) -> ProjectMetadata:
        meta = ProjectMetadata()
        field_map = {
            "PROJECT_NAME": "name",
            "DESCRIPTION": "description",
            "VERSION": "version",
            "AUTHOR": "author",
            "LANGUAGE": "language",
            "FRAMEWORK": "framework",
            "PYTHON_VERSION": "python_version",
            "NODE_VERSION": "node_version",
            "RUN_COMMAND": "run_command",
            "BUILD_COMMAND": "build_command",
            "INSTALL_COMMAND": "install_command",
        }
        restored = restore_code(text)
        for line in restored.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            colon = line.find(":")
            if colon == -1:
                continue
            key = line[:colon].strip().upper()
            value = line[colon + 1:].strip()
            if key in field_map:
                setattr(meta, field_map[key], value)
            else:
                meta.extra[key] = value
        return meta

    def _parse_plain_file(self, chunk: str) -> Optional[ProjectFile]:
        lines = chunk.strip().splitlines()
        path = ""
        filetype = ""
        description = ""
        code_lines = []
        in_code = False
        for line in lines:
            stripped = line.strip()
            if stripped == "CODESTART":
                in_code = True
                continue
            if stripped == "CODEEND":
                in_code = False
                continue
            if in_code:
                code_lines.append(line)
                continue
            if stripped.startswith("FILEPATH:"):
                path = stripped[9:].strip()
            elif stripped.startswith("FILETYPE:"):
                filetype = stripped[9:].strip()
            elif stripped.startswith("FILEDESC:"):
                description = stripped[9:].strip()
        if not path:
            return None
        # восстанавливаем плейсхолдеры в пути
        path = restore_code(path)
        # если путь gitignore без точки то добавляем точку
        if path.endswith("gitignore") and not path.endswith(".gitignore"):
            parts = path.rsplit("gitignore", 1)
            path = parts[0] + ".gitignore"
        description = restore_code(description)
        filetype = restore_code(filetype)
        raw_code = "\n".join(code_lines)
        restored_code = restore_code(raw_code)
        pf = ProjectFile(relative_path=path, content=restored_code, language=filetype, description=description)
        if not pf.language:
            pf.auto_detect_language()
        return pf

    def _parse_legacy_strict(self, text: str) -> Project:
        project = Project()
        match = re.search(r'===PROJECT_START===(.*?)===PROJECT_END===', text, re.DOTALL)
        if match:
            text = match.group(1)
        meta_match = re.search(r'---META_START---(.*?)---META_END---', text, re.DOTALL)
        if meta_match:
            project.metadata = self._parse_meta(meta_match.group(1))
        struct_match = re.search(r'---STRUCTURE_START---(.*?)---STRUCTURE_END---', text, re.DOTALL)
        if struct_match:
            project.structure_description = struct_match.group(1).strip()
        file_blocks = re.findall(r'---FILE_START---(.*?)---FILE_END---', text, re.DOTALL)
        for block in file_blocks:
            pf = self._parse_legacy_file(block)
            if pf:
                project.files.append(pf)
        return project

    def _parse_legacy_bracket(self, text: str) -> Project:
        project = Project()
        match = re.search(r'\[PROJECT_BEGIN\](.*?)\[PROJECT_FINISH\]', text, re.DOTALL)
        if match:
            text = match.group(1)
        meta_match = re.search(r'\[META_BEGIN\](.*?)\[META_FINISH\]', text, re.DOTALL)
        if meta_match:
            project.metadata = self._parse_meta(meta_match.group(1))
        struct_match = re.search(r'\[STRUCT_BEGIN\](.*?)\[STRUCT_FINISH\]', text, re.DOTALL)
        if struct_match:
            project.structure_description = struct_match.group(1).strip()
        file_blocks = re.findall(r'\[FILE_BEGIN\](.*?)\[FILE_FINISH\]', text, re.DOTALL)
        for block in file_blocks:
            pf = self._parse_legacy_file(block)
            if pf:
                project.files.append(pf)
        return project

    def _parse_legacy_file(self, block: str) -> Optional[ProjectFile]:
        lines = block.strip().splitlines()
        path = ""
        description = ""
        content_lines = []
        in_code = False
        for line in lines:
            stripped = line.strip()
            if not in_code:
                if stripped.startswith("PATH:"):
                    path = stripped[5:].strip()
                elif stripped.startswith("FILEPATH:"):
                    path = stripped[9:].strip()
                elif stripped.startswith("DESCRIPTION:"):
                    description = stripped[12:].strip()
                elif stripped.startswith("FILEDESC:"):
                    description = stripped[9:].strip()
                elif stripped.startswith("```") or stripped == "CODESTART" or stripped == "[CODE_BEGIN]":
                    in_code = True
            else:
                if stripped.startswith("```") or stripped == "CODEEND" or stripped == "[CODE_FINISH]":
                    in_code = False
                else:
                    content_lines.append(line)
        if not path:
            return None
        pf = ProjectFile(relative_path=path, content="\n".join(content_lines), description=description)
        pf.auto_detect_language()
        return pf

    def _parse_markdown(self, text: str) -> Project:
        project = Project()
        title_match = re.search(r'^#\s+(.+)$', text, re.MULTILINE)
        if title_match:
            name = title_match.group(1).strip()
            name = re.sub(r'[*_`]', '', name)
            project.metadata.name = self._slugify(name)
        pattern = re.compile(
            r'(?:^|\n)(?:#{1,6}\s+[`*]*([^\n`*]+\.\w+)[`*]*|[`*]{1,3}([^\n`*]+\.\w+)[`*]{1,3}|(?:файл|file|create)\s*[:\-]?\s*[`*]*([^\n`*]+\.\w+)[`*]*).*?\n```(\w*)\n(.*?)\n```',
            re.DOTALL | re.IGNORECASE | re.MULTILINE
        )
        for match in pattern.finditer(text):
            path = match.group(1) or match.group(2) or match.group(3)
            lang = match.group(4) or ""
            content = match.group(5)
            if path:
                path = path.strip().strip('`*"\'')
                pf = ProjectFile(relative_path=path, content=content, language=lang)
                if not pf.language:
                    pf.auto_detect_language()
                project.files.append(pf)
        if not project.files:
            project.files = self._parse_simple_codeblocks(text)
        if not project.metadata.name and project.files:
            first = project.files[0].relative_path
            if '/' in first:
                project.metadata.name = Path(first).parts[0]
            else:
                project.metadata.name = Path(first).stem
        return project

    def _parse_simple_codeblocks(self, text: str) -> List[ProjectFile]:
        files = []
        parts = re.split(r'```(\w*)\n', text)
        i = 0
        while i < len(parts) - 2:
            before = parts[i]
            lang = parts[i + 1]
            code_and_rest = parts[i + 2]
            code_end = code_and_rest.find('\n```')
            if code_end == -1:
                code = code_and_rest
            else:
                code = code_and_rest[:code_end]
            path = self._extract_filename(before)
            if path:
                pf = ProjectFile(relative_path=path, content=code, language=lang)
                if not pf.language:
                    pf.auto_detect_language()
                files.append(pf)
            i += 3
        return files

    def _extract_filename(self, text: str) -> str:
        lines = text.strip().splitlines()[-3:]
        for line in reversed(lines):
            line = line.strip()
            match = re.search(r'[`*]*([a-zA-Z0-9_/\\.-]+\.[a-zA-Z0-9]+)[`*]*', line)
            if match:
                candidate = match.group(1)
                if len(candidate) < 100:
                    return candidate.replace('\\', '/')
        return ""

    def _slugify(self, text: str) -> str:
        text = text.lower().strip()
        text = re.sub(r'[^\w\s-]', '', text)
        text = re.sub(r'[\s_]+', '_', text)
        return text[:50] or "project"