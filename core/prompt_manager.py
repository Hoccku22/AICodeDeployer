# core/prompt_manager.py

from dataclasses import dataclass
from typing import Dict


@dataclass
class PromptVariant:
    key: str
    title: str
    description: str
    icon: str
    content: str


# таблица замен: плейсхолдер -> реальный символ
REPLACEMENTS = {
    "DUNDER": "__",
    "USCORE": "_",
    "BACKTICK": "`",
    "TRIPLEBACKTICK": "```",
    "HASHSIGN": "#",
    "STARSIGN": "*",
    "TILDE": "~",
}

# точка в начале строки = пробел
INDENT_CHAR = "."


def restore_code(text: str) -> str:
    lines = text.split("\n")
    restored = []
    for line in lines:
        # восстанавливаем отступы: точки в начале строки -> пробелы
        indent_count = 0
        for ch in line:
            if ch == INDENT_CHAR:
                indent_count += 1
            else:
                break
        if indent_count > 0:
            line = " " * indent_count + line[indent_count:]
        # восстанавливаем плейсхолдеры
        # порядок важен: сначала длинные чтобы DUNDER не сломал USCORE
        line = line.replace("TRIPLEBACKTICK", "```")
        line = line.replace("DUNDER", "__")
        line = line.replace("BACKTICK", "`")
        line = line.replace("HASHSIGN", "#")
        line = line.replace("STARSIGN", "*")
        line = line.replace("TILDE", "~")
        line = line.replace("USCORE", "_")
        restored.append(line)
    return "\n".join(restored)


class PromptManager:

    _variants: Dict[str, PromptVariant] = {}

    @classmethod
    def _init_variants(cls):
        if cls._variants:
            return
        cls._variants["full"] = PromptVariant(key="full", title="Полный промпт", description="Максимально подробные инструкции", icon="P", content=cls._full())
        cls._variants["short"] = PromptVariant(key="short", title="Короткий промпт", description="Сжатая версия", icon="S", content=cls._short())
        cls._variants["continue"] = PromptVariant(key="continue", title="Продолжение", description="Когда ответ обрезан", icon="C", content=cls._cont())
        cls._variants["refactor"] = PromptVariant(key="refactor", title="Рефакторинг", description="Переписать проект", icon="R", content=cls._refactor())
        cls._variants["add_feature"] = PromptVariant(key="add_feature", title="Добавить фичу", description="Добавить функционал", icon="A", content=cls._add_feature())

    @classmethod
    def _full(cls) -> str:
        p = ""
        p += "You are a code generator. Output ONLY plain text.\n"
        p += "ABSOLUTELY NO MARKDOWN. No formatting of any kind.\n"
        p += "No triple backticks. No hash headers. No bold. No italic. No lists.\n"
        p += "\n"
        p += "CRITICAL: You must replace special characters in ALL code with safe placeholders.\n"
        p += "This is mandatory because the output will be copy-pasted through systems that break formatting.\n"
        p += "\n"
        p += "REPLACEMENT TABLE (memorize this, apply to ALL code you write):\n"
        p += "- Every underscore character must be written as USCORE\n"
        p += "- Every double underscore must be written as DUNDER (not USCOREUSCORE)\n"
        p += "- Every backtick must be written as BACKTICK\n"
        p += "- Every hash sign at start of line must be written as HASHSIGN\n"
        p += "- Every asterisk must be written as STARSIGN\n"
        p += "- Every tilde must be written as TILDE\n"
        p += "\n"
        p += "INDENTATION RULE:\n"
        p += "Do NOT use spaces or tabs for indentation in code.\n"
        p += "Instead use dots at the start of lines. Each dot = one space.\n"
        p += "Example: 4 space indent = 4 dots at start of line.\n"
        p += "\n"
        p += "EXAMPLE of how Python code must look in your output:\n"
        p += "\n"
        p += "import random\n"
        p += "\n"
        p += "class MyClass:\n"
        p += "....def DUNDERinitDUNDER(self, name):\n"
        p += "........self.name = name\n"
        p += "........self.USCOREprivate = 0\n"
        p += "\n"
        p += "....def getUSCOREvalue(self):\n"
        p += "........return self.USCOREprivate\n"
        p += "\n"
        p += "....def DUNDERstrDUNDER(self):\n"
        p += "........return self.name\n"
        p += "\n"
        p += "if DUNDERnameDUNDER == DUNDERmainDUNDER:\n"
        p += "....obj = MyClass(\"test\")\n"
        p += "....print(obj)\n"
        p += "\n"
        p += "Notice: DUNDER replaces double underscore. USCORE replaces single underscore.\n"
        p += "Dots at start of line replace spaces for indentation.\n"
        p += "The rest of the line (after dots) uses no special indentation.\n"
        p += "\n"
        p += "PROJECT FORMAT:\n"
        p += "\n"
        p += "PROJSTART\n"
        p += "METASTART\n"
        p += "PROJECTUSCORENAME: exampleUSCOREproject\n"
        p += "DESCRIPTION: one line description\n"
        p += "VERSION: 1.0.0\n"
        p += "LANGUAGE: Python\n"
        p += "FRAMEWORK: none\n"
        p += "RUNUSCORECOMMAND: python main.py\n"
        p += "BUILDUSCORECOMMAND: none\n"
        p += "INSTALLUSCORECOMMAND: pip install -r requirements.txt\n"
        p += "METAEND\n"
        p += "\n"
        p += "STRUCTSTART\n"
        p += "exampleUSCOREproject/\n"
        p += "..src/\n"
        p += "....DUNDERinitDUNDER.py\n"
        p += "....app.py\n"
        p += "..main.py\n"
        p += "..requirements.txt\n"
        p += "..gitignore\n"
        p += "STRUCTEND\n"
        p += "\n"
        p += "FILESTART\n"
        p += "FILEPATH: src/DUNDERinitDUNDER.py\n"
        p += "FILETYPE: python\n"
        p += "CODESTART\n"
        p += "HASHSIGNempty init\n"
        p += "CODEEND\n"
        p += "FILEEND\n"
        p += "\n"
        p += "FILESTART\n"
        p += "FILEPATH: src/app.py\n"
        p += "FILETYPE: python\n"
        p += "CODESTART\n"
        p += "def hello():\n"
        p += "....print(\"hello\")\n"
        p += "CODEEND\n"
        p += "FILEEND\n"
        p += "\n"
        p += "FILESTART\n"
        p += "FILEPATH: main.py\n"
        p += "FILETYPE: python\n"
        p += "CODESTART\n"
        p += "from src.app import hello\n"
        p += "hello()\n"
        p += "CODEEND\n"
        p += "FILEEND\n"
        p += "\n"
        p += "PROJEND\n"
        p += "\n"
        p += "RULES:\n"
        p += "1. EVERY underscore in code and filenames must be USCORE or DUNDER. No raw underscores anywhere.\n"
        p += "2. EVERY indent must be dots. No spaces or tabs at line start. 4 dots = 4 spaces.\n"
        p += "3. PROJSTART PROJEND METASTART METAEND STRUCTSTART STRUCTEND FILESTART FILEEND CODESTART CODEEND are markers. Each on its own line.\n"
        p += "4. Every file from STRUCT must have its own FILESTART block.\n"
        p += "5. FILEPATH must match path in STRUCT exactly.\n"
        p += "6. Code must be complete and working. No placeholders. No TODO.\n"
        p += "7. No text before PROJSTART or after PROJEND.\n"
        p += "8. No markdown formatting anywhere.\n"
        p += "9. Apply replacements even in strings, comments, everywhere.\n"
        p += "10. The structure tree uses dots for indentation too, 2 dots per level.\n"
        p += "11. For .gitignore file write gitignore without dot in STRUCT and FILEPATH. The dot will be added automatically.\n"
        return p

    @classmethod
    def _short(cls) -> str:
        p = ""
        p += "Output ONLY plain text. No markdown. No formatting.\n"
        p += "Replace underscores with USCORE, double underscores with DUNDER.\n"
        p += "Use dots for indentation (1 dot = 1 space).\n"
        p += "Replace hash at line start with HASHSIGN.\n"
        p += "\n"
        p += "PROJSTART\n"
        p += "METASTART\n"
        p += "PROJECTUSCORENAME: name\n"
        p += "DESCRIPTION: description\n"
        p += "LANGUAGE: language\n"
        p += "RUNUSCORECOMMAND: run command\n"
        p += "INSTALLUSCORECOMMAND: install command\n"
        p += "METAEND\n"
        p += "STRUCTSTART\n"
        p += "file tree with 2 dot indentation\n"
        p += "STRUCTEND\n"
        p += "For EACH file:\n"
        p += "FILESTART\n"
        p += "FILEPATH: path\n"
        p += "FILETYPE: language\n"
        p += "CODESTART\n"
        p += "complete code with dot indentation and USCORE/DUNDER replacements\n"
        p += "CODEEND\n"
        p += "FILEEND\n"
        p += "PROJEND\n"
        return p

    @classmethod
    def _cont(cls) -> str:
        p = ""
        p += "Previous response was cut off. Write the REMAINING files only.\n"
        p += "Same rules: dots for indent, USCORE for underscore, DUNDER for double underscore.\n"
        p += "No markdown. Start with FILESTART. End with PROJEND.\n"
        p += "\n"
        p += "FILESTART\n"
        p += "FILEPATH: path\n"
        p += "FILETYPE: language\n"
        p += "CODESTART\n"
        p += "complete code\n"
        p += "CODEEND\n"
        p += "FILEEND\n"
        p += "\n"
        p += "PROJEND\n"
        return p

    @classmethod
    def _refactor(cls) -> str:
        p = ""
        p += "Below is a project. Refactor it. Output in same format PROJSTART to PROJEND.\n"
        p += "Same rules: dots for indent, USCORE/DUNDER for underscores. No markdown.\n"
        p += "\n"
        p += "Source project:\n"
        p += "\n"
        return p

    @classmethod
    def _add_feature(cls) -> str:
        p = ""
        p += "Below is a project. Add new functionality. Output ENTIRE project PROJSTART to PROJEND.\n"
        p += "Same rules: dots for indent, USCORE/DUNDER for underscores. No markdown.\n"
        p += "\n"
        p += "Source project:\n"
        p += "\n"
        return p

    @classmethod
    def get_prompt(cls, variant: str = "full") -> str:
        cls._init_variants()
        v = cls._variants.get(variant)
        if v is None:
            raise KeyError("Unknown variant: " + variant)
        return v.content

    @classmethod
    def get_variant(cls, key: str) -> PromptVariant:
        cls._init_variants()
        v = cls._variants.get(key)
        if v is None:
            raise KeyError("Unknown variant: " + key)
        return v

    @classmethod
    def get_all_variants(cls) -> Dict[str, PromptVariant]:
        cls._init_variants()
        return dict(cls._variants)

    @classmethod
    def get_variant_keys(cls) -> list:
        cls._init_variants()
        return list(cls._variants.keys())

    @classmethod
    def build_project_request(cls, description, variant="full", language="", framework="", extra_requirements=""):
        prompt = cls.get_prompt(variant)
        parts = [prompt, "", "TASK:", description]
        if language:
            parts.append("Preferred language: " + language)
        if framework:
            parts.append("Preferred framework: " + framework)
        if extra_requirements:
            parts.append("Extra requirements: " + extra_requirements)
        return "\n".join(parts)

    @classmethod
    def build_continue_request(cls, missing_files=None):
        prompt = cls.get_prompt("continue")
        if missing_files:
            prompt += "\nFiles still needed:\n"
            for f in missing_files:
                prompt += f + "\n"
        return prompt

    @classmethod
    def build_refactor_request(cls, project_ai_text, instructions=""):
        prompt = cls.get_prompt("refactor")
        prompt += project_ai_text
        if instructions:
            prompt += "\n\nWhat to improve:\n" + instructions
        return prompt

    @classmethod
    def build_add_feature_request(cls, project_ai_text, feature_description):
        prompt = cls.get_prompt("add_feature")
        prompt += project_ai_text
        prompt += "\n\nNew feature:\n" + feature_description
        return prompt