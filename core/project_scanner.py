# core/project_scanner.py
import os
import platform
from pathlib import Path
from typing import List, Optional
from models.project import Project, ProjectFile
import logging

logger = logging.getLogger(__name__)


class ProjectScanner:
    """Поиск папок проектов и сканирование существующих проектов"""

    # Типичные папки для проектов
    COMMON_PROJECT_DIRS = [
        "Projects", "projects",
        "Dev", "dev",
        "Development", "development",
        "Code", "code",
        "Workspace", "workspace",
        "src", "repos",
        "GitHub", "github",
        "GitLab", "gitlab",
    ]

    # Файлы-индикаторы того, что папка — это проект
    PROJECT_INDICATORS = [
        "package.json", "requirements.txt", "setup.py", "pyproject.toml",
        "Cargo.toml", "go.mod", "pom.xml", "build.gradle",
        "Makefile", "CMakeLists.txt", "docker-compose.yml",
        ".git", "README.md", "main.py", "app.py", "index.html",
        "manage.py", ".gitignore",
    ]

    # Игнорируемые директории
    IGNORE_DIRS = {
        '__pycache__', 'node_modules', '.git', '.svn', '.hg',
        'venv', '.venv', 'env', '.env', '.idea', '.vscode',
        'dist', 'build', '.next', '.nuxt', 'target',
        '.pytest_cache', '.mypy_cache', '__MACOSX',
        'bin', 'obj',
    }

    # Игнорируемые расширения
    IGNORE_EXTENSIONS = {
        '.pyc', '.pyo', '.class', '.o', '.obj', '.exe',
        '.dll', '.so', '.dylib', '.bin', '.dat',
        '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.ico', '.svg',
        '.mp3', '.mp4', '.avi', '.mov', '.wav',
        '.zip', '.tar', '.gz', '.rar', '.7z',
        '.pdf', '.doc', '.docx', '.xls', '.xlsx',
        '.db', '.sqlite', '.sqlite3',
        '.woff', '.woff2', '.ttf', '.eot',
    }

    def find_project_directories(self) -> List[str]:
        """Найти вероятные директории с проектами"""
        home = Path.home()
        found = []

        # Проверяем стандартные пути
        for dirname in self.COMMON_PROJECT_DIRS:
            path = home / dirname
            if path.exists() and path.is_dir():
                found.append(str(path))

        # Desktop
        desktop = home / "Desktop"
        if desktop.exists():
            found.append(str(desktop))

        # Documents
        documents = home / "Documents"
        if documents.exists():
            found.append(str(documents))

        # Windows-specific
        if platform.system() == "Windows":
            for drive in ['C:', 'D:', 'E:']:
                for dirname in self.COMMON_PROJECT_DIRS:
                    path = Path(f"{drive}\\{dirname}")
                    if path.exists():
                        found.append(str(path))

        # macOS-specific
        if platform.system() == "Darwin":
            dev_path = home / "Developer"
            if dev_path.exists():
                found.append(str(dev_path))

        # Убираем дубли, сохраняя порядок
        seen = set()
        unique = []
        for p in found:
            normalized = os.path.normpath(p)
            if normalized not in seen:
                seen.add(normalized)
                unique.append(normalized)

        return unique

    def scan_project(self, project_path: str) -> Project:
        """
        Сканировать существующий проект и создать объект Project.
        """
        root = Path(project_path)

        if not root.exists():
            raise FileNotFoundError(f"Путь не найден: {project_path}")

        project = Project()
        project.metadata.name = root.name

        # Сканируем файлы
        for file_path in sorted(root.rglob('*')):
            if not file_path.is_file():
                continue

            # Проверяем, не в игнорируемой ли директории
            relative = file_path.relative_to(root)
            parts = relative.parts

            if any(part in self.IGNORE_DIRS for part in parts):
                continue

            # Проверяем расширение
            if file_path.suffix.lower() in self.IGNORE_EXTENSIONS:
                continue

            # Проверяем размер (пропускаем файлы > 500KB)
            if file_path.stat().st_size > 500 * 1024:
                logger.debug(f"Пропущен (слишком большой): {relative}")
                continue

            # Читаем содержимое
            try:
                content = file_path.read_text(encoding='utf-8')
            except (UnicodeDecodeError, PermissionError):
                try:
                    content = file_path.read_text(encoding='latin-1')
                except Exception:
                    logger.debug(f"Не удалось прочитать: {relative}")
                    continue

            pf = ProjectFile(
                relative_path=str(relative).replace('\\', '/'),
                content=content
            )
            pf.auto_detect_language()
            project.files.append(pf)

        # Пробуем определить метаданные из файлов проекта
        self._detect_metadata(project)

        logger.info(
            f"Просканирован проект '{project.metadata.name}': "
            f"{len(project.files)} файлов, "
            f"{project.total_lines} строк"
        )

        return project

    def _detect_metadata(self, project: Project):
        """Определить метаданные из содержимого файлов"""
        for pf in project.files:
            fname = pf.filename.lower()

            if fname == "package.json":
                self._parse_package_json(project, pf.content)
            elif fname in ("requirements.txt", "setup.py", "pyproject.toml"):
                project.metadata.language = "Python"
                if fname == "requirements.txt":
                    project.metadata.install_command = "pip install -r requirements.txt"
            elif fname == "cargo.toml":
                project.metadata.language = "Rust"
            elif fname == "go.mod":
                project.metadata.language = "Go"

    def _parse_package_json(self, project: Project, content: str):
        """Извлечь инфо из package.json"""
        import json
        try:
            data = json.loads(content)
            project.metadata.name = data.get("name", project.metadata.name)
            project.metadata.description = data.get("description", "")
            project.metadata.version = data.get("version", "1.0.0")
            project.metadata.language = "JavaScript"
            project.metadata.install_command = "npm install"

            scripts = data.get("scripts", {})
            if "start" in scripts:
                project.metadata.run_command = "npm start"
            if "dev" in scripts:
                project.metadata.run_command = "npm run dev"
            if "build" in scripts:
                project.metadata.build_command = "npm run build"
        except json.JSONDecodeError:
            pass