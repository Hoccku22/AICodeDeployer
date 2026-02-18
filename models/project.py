# models/project.py
from dataclasses import dataclass, field
from typing import List, Dict
from pathlib import Path


@dataclass
class ProjectFile:
    relative_path: str
    content: str
    language: str = ""
    description: str = ""

    @property
    def filename(self) -> str:
        return Path(self.relative_path).name

    @property
    def directory(self) -> str:
        parent = str(Path(self.relative_path).parent)
        return "" if parent == "." else parent

    @property
    def extension(self) -> str:
        return Path(self.relative_path).suffix.lstrip(".")

    def auto_detect_language(self):
        ext_map = {
            "py": "python", "js": "javascript", "ts": "typescript",
            "jsx": "jsx", "tsx": "tsx", "html": "html", "htm": "html",
            "css": "css", "scss": "scss", "sass": "sass",
            "java": "java", "kt": "kotlin", "swift": "swift",
            "c": "c", "cpp": "cpp", "h": "c", "hpp": "cpp",
            "cs": "csharp", "go": "go", "rs": "rust",
            "rb": "ruby", "php": "php", "lua": "lua",
            "sql": "sql", "sh": "bash", "bat": "batch",
            "json": "json", "xml": "xml", "yaml": "yaml",
            "yml": "yaml", "toml": "toml", "ini": "ini",
            "md": "markdown", "txt": "text",
            "dockerfile": "dockerfile", "gitignore": "text",
        }
        ext = self.extension.lower()
        fname = self.filename.lower()

        if fname == "dockerfile":
            self.language = "dockerfile"
        elif fname == ".gitignore":
            self.language = "text"
        elif ext in ext_map:
            self.language = ext_map[ext]
        else:
            self.language = "text"


@dataclass
class ProjectMetadata:
    name: str = "unnamed_project"
    description: str = ""
    version: str = "1.0.0"
    author: str = ""
    language: str = ""
    framework: str = ""
    python_version: str = ""
    node_version: str = ""
    run_command: str = ""
    build_command: str = ""
    install_command: str = ""
    extra: Dict[str, str] = field(default_factory=dict)


def encode_for_ai(text: str) -> str:
    text = text.replace("__", "DUNDER")
    text = text.replace("_", "USCORE")
    text = text.replace("`", "BACKTICK")
    text = text.replace("~", "TILDE")
    text = text.replace("*", "STARSIGN")

    lines = text.split("\n")
    encoded = []
    for line in lines:
        indent_count = 0
        for ch in line:
            if ch == " ":
                indent_count += 1
            else:
                break
        if indent_count > 0:
            line = "." * indent_count + line[indent_count:]

        stripped_after_dots = line.lstrip(".")
        if stripped_after_dots.startswith("#"):
            dot_part = line[:len(line) - len(stripped_after_dots)]
            line = dot_part + "HASHSIGN" + stripped_after_dots[1:]
        encoded.append(line)
    return "\n".join(encoded)


@dataclass
class Project:
    metadata: ProjectMetadata = field(default_factory=ProjectMetadata)
    files: List[ProjectFile] = field(default_factory=list)
    structure_description: str = ""

    @property
    def file_count(self) -> int:
        return len(self.files)

    @property
    def total_lines(self) -> int:
        return sum(len(f.content.splitlines()) for f in self.files)

    def get_tree(self) -> str:
        if not self.files:
            return "(empty)"

        lines = [self.metadata.name + "/"]
        paths = sorted(f.relative_path for f in self.files)
        seen_dirs = set()

        for p in paths:
            parts = Path(p).parts
            for i in range(len(parts) - 1):
                dir_path = "/".join(parts[:i + 1])
                if dir_path not in seen_dirs:
                    seen_dirs.add(dir_path)
                    indent = "  " * (i + 1)
                    lines.append(indent + parts[i] + "/")
            indent = "  " * len(parts)
            lines.append(indent + parts[-1])

        return "\n".join(lines)

    def to_ai_format(self) -> str:
        out = ""
        out += "PROJSTART\n"
        out += "METASTART\n"
        out += "PROJECT_NAME: " + self.metadata.name + "\n"

        if self.metadata.description:
            out += "DESCRIPTION: " + self.metadata.description + "\n"
        if self.metadata.version:
            out += "VERSION: " + self.metadata.version + "\n"
        if self.metadata.author:
            out += "AUTHOR: " + self.metadata.author + "\n"
        if self.metadata.language:
            out += "LANGUAGE: " + self.metadata.language + "\n"
        if self.metadata.framework:
            out += "FRAMEWORK: " + self.metadata.framework + "\n"
        if self.metadata.run_command:
            out += "RUN_COMMAND: " + self.metadata.run_command + "\n"
        if self.metadata.build_command:
            out += "BUILD_COMMAND: " + self.metadata.build_command + "\n"
        if self.metadata.install_command:
            out += "INSTALL_COMMAND: " + self.metadata.install_command + "\n"

        out += "METAEND\n"
        out += "\n"
        out += "STRUCTSTART\n"
        tree = self.get_tree()
        out += encode_for_ai(tree) + "\n"
        out += "STRUCTEND\n"

        for f in self.files:
            out += "\n"
            out += "FILESTART\n"
            filepath = f.relative_path
            if filepath.endswith(".gitignore"):
                filepath = filepath.replace(".gitignore", "gitignore")
            out += "FILEPATH: " + encode_for_ai(filepath) + "\n"
            if f.description:
                out += "FILEDESC: " + f.description + "\n"
            lang = f.language or f.extension or "text"
            out += "FILETYPE: " + lang + "\n"
            out += "CODESTART\n"
            out += encode_for_ai(f.content) + "\n"
            out += "CODEEND\n"
            out += "FILEEND\n"

        out += "\n"
        out += "PROJEND\n"
        return out