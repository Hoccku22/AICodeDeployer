# ui/localization.py

TRANSLATIONS = {
    "ru": {
        # Window
        "app_title": "AI Code Deployer",

        # Directory panel
        "working_directory": "Рабочая директория",
        "browse": "Обзор",
        "refresh": "Обновить",

        # Tabs
        "tab_import": "Импорт",
        "tab_export": "Экспорт",
        "tab_help": "Помощь",

        # Import tab
        "copy_prompt_for_ai": "Скопировать промпт для ИИ:",
        "paste_ai_response": "Вставьте ответ ИИ:",
        "chars_count": "{} символов",
        "placeholder_input": (
            "Вставьте ответ ИИ сюда...\n\n"
            "Поддерживаемые форматы:\n"
            "  PROJSTART...PROJEND (из промпта)\n"
            "  Markdown блоки кода\n\n"
            "Совет: нажмите зелёную кнопку выше, чтобы скопировать промпт."
        ),
        "analyze": "Анализировать",
        "create_project": "Создать проект",
        "overwrite_existing": "Перезаписать существующий",
        "clear": "Очистить",
        "analysis_result": "Результат анализа:",

        # Export tab
        "select_project_to_export": "Выберите проект для экспорта",
        "find_projects": "Найти проекты",
        "browse_folder": "Выбрать папку",
        "export_pdf": "Экспорт PDF",
        "copy_ai_format": "Копировать AI формат",
        "export_preview": "Предпросмотр экспорта:",

        # Help tab
        "help_title": "Как использовать AI Code Deployer",
        "help_content": (
            "<h2>Быстрый старт</h2>"
            "<ol>"
            "<li><b>Скопируйте промпт</b> — нажмите зелёную кнопку на вкладке Импорт</li>"
            "<li><b>Отправьте промпт ИИ</b> — вместе с описанием вашего проекта</li>"
            "<li><b>Вставьте ответ</b> — в текстовое поле на вкладке Импорт</li>"
            "<li><b>Анализируйте</b> — нажмите кнопку Анализировать</li>"
            "<li><b>Создайте проект</b> — нажмите Создать проект</li>"
            "</ol>"
            "<h2>Экспорт</h2>"
            "<p>Вкладка Экспорт позволяет сканировать существующие проекты и экспортировать их в PDF или AI формат.</p>"
            "<h2>Горячие клавиши</h2>"
            "<ul>"
            "<li><b>Ctrl+V</b> — Вставить</li>"
            "<li><b>Ctrl+Enter</b> — Анализировать</li>"
            "<li><b>Ctrl+D</b> — Создать проект</li>"
            "<li><b>Ctrl+E</b> — Экспорт PDF</li>"
            "<li><b>Ctrl+T</b> — Сменить тему</li>"
            "</ul>"
        ),

        # Theme button
        "theme_dark": "Тема: Тёмная",
        "theme_light": "Тема: Светлая",

        # Language button
        "lang_label": "Язык: Русский",

        # Status
        "ready": "Готово",
        "analyzing": "Анализ...",
        "deploying": "Создание проекта...",
        "exporting_pdf": "Экспорт PDF...",
        "scanning": "Сканирование...",

        # Messages
        "no_text_to_analyze": "Нет текста для анализа",
        "paste_text_first": "Сначала вставьте текст ответа ИИ.",
        "analysis_complete": "Анализ завершён",
        "project_name": "Проект: {}",
        "files_count": "Файлов: {}",
        "total_lines": "Строк: {}",
        "file_list": "Файлы:",
        "analysis_error": "Ошибка анализа",
        "no_project_analyzed": "Нет проанализированного проекта",
        "analyze_first": "Сначала проанализируйте ответ ИИ.",
        "no_directory_selected": "Директория не выбрана",
        "select_working_directory": "Выберите рабочую директорию.",
        "project_created": "Проект создан",
        "project_created_at": "Проект создан в:\n{}",
        "deploy_error": "Ошибка создания проекта",
        "prompt_copied": "Промпт '{}' скопирован в буфер обмена!",
        "text_cleared": "Текст очищен",
        "select_project_folder": "Выбрать папку проекта",
        "no_project_selected": "Проект не выбран",
        "select_project_first": "Выберите или найдите проект для экспорта.",
        "project_not_found": "Проект не найден",
        "path_not_exists": "Путь не существует: {}",
        "save_pdf": "Сохранить PDF",
        "pdf_exported": "PDF экспортирован",
        "pdf_saved_at": "PDF сохранён:\n{}",
        "pdf_export_error": "Ошибка экспорта PDF",
        "ai_format_copied": "AI формат скопирован в буфер обмена!",
        "scan_error": "Ошибка сканирования",
        "found_projects": "Найдено проектов: {}",
        "select_directory": "Выбрать директорию",

        # Prompt variants
        "prompt_full": "Полный промпт",
        "prompt_short": "Короткий промпт",
        "prompt_continue": "Продолжение",
        "prompt_refactor": "Рефакторинг",
        "prompt_add_feature": "Добавить фичу",
    },

    "en": {
        # Window
        "app_title": "AI Code Deployer",

        # Directory panel
        "working_directory": "Working Directory",
        "browse": "Browse",
        "refresh": "Refresh",

        # Tabs
        "tab_import": "Import",
        "tab_export": "Export",
        "tab_help": "Help",

        # Import tab
        "copy_prompt_for_ai": "Copy prompt for AI:",
        "paste_ai_response": "Paste AI response:",
        "chars_count": "{} chars",
        "placeholder_input": (
            "Paste AI response here...\n\n"
            "Supported formats:\n"
            "  PROJSTART...PROJEND (from prompt)\n"
            "  Markdown code blocks\n\n"
            "Tip: click green button above to copy prompt first."
        ),
        "analyze": "Analyze",
        "create_project": "Create Project",
        "overwrite_existing": "Overwrite existing",
        "clear": "Clear",
        "analysis_result": "Analysis Result:",

        # Export tab
        "select_project_to_export": "Select project to export",
        "find_projects": "Find Projects",
        "browse_folder": "Browse Folder",
        "export_pdf": "Export PDF",
        "copy_ai_format": "Copy AI Format",
        "export_preview": "Export Preview:",

        # Help tab
        "help_title": "How to use AI Code Deployer",
        "help_content": (
            "<h2>Quick Start</h2>"
            "<ol>"
            "<li><b>Copy prompt</b> — click the green button on the Import tab</li>"
            "<li><b>Send prompt to AI</b> — along with your project description</li>"
            "<li><b>Paste response</b> — into the text field on the Import tab</li>"
            "<li><b>Analyze</b> — click the Analyze button</li>"
            "<li><b>Create project</b> — click Create Project</li>"
            "</ol>"
            "<h2>Export</h2>"
            "<p>The Export tab allows you to scan existing projects and export them to PDF or AI format.</p>"
            "<h2>Keyboard Shortcuts</h2>"
            "<ul>"
            "<li><b>Ctrl+V</b> — Paste</li>"
            "<li><b>Ctrl+Enter</b> — Analyze</li>"
            "<li><b>Ctrl+D</b> — Deploy project</li>"
            "<li><b>Ctrl+E</b> — Export PDF</li>"
            "<li><b>Ctrl+T</b> — Toggle theme</li>"
            "</ul>"
        ),

        # Theme button
        "theme_dark": "Theme: Dark",
        "theme_light": "Theme: Light",

        # Language button
        "lang_label": "Lang: English",

        # Status
        "ready": "Ready",
        "analyzing": "Analyzing...",
        "deploying": "Deploying...",
        "exporting_pdf": "Exporting PDF...",
        "scanning": "Scanning...",

        # Messages
        "no_text_to_analyze": "No text to analyze",
        "paste_text_first": "Paste AI response text first.",
        "analysis_complete": "Analysis complete",
        "project_name": "Project: {}",
        "files_count": "Files: {}",
        "total_lines": "Lines: {}",
        "file_list": "Files:",
        "analysis_error": "Analysis error",
        "no_project_analyzed": "No project analyzed",
        "analyze_first": "Analyze AI response first.",
        "no_directory_selected": "No directory selected",
        "select_working_directory": "Select a working directory.",
        "project_created": "Project created",
        "project_created_at": "Project created at:\n{}",
        "deploy_error": "Deploy error",
        "prompt_copied": "Prompt '{}' copied to clipboard!",
        "text_cleared": "Text cleared",
        "select_project_folder": "Select project folder",
        "no_project_selected": "No project selected",
        "select_project_first": "Select or find a project to export.",
        "project_not_found": "Project not found",
        "path_not_exists": "Path does not exist: {}",
        "save_pdf": "Save PDF",
        "pdf_exported": "PDF exported",
        "pdf_saved_at": "PDF saved at:\n{}",
        "pdf_export_error": "PDF export error",
        "ai_format_copied": "AI format copied to clipboard!",
        "scan_error": "Scan error",
        "found_projects": "Found projects: {}",
        "select_directory": "Select directory",

        # Prompt variants
        "prompt_full": "Full Prompt",
        "prompt_short": "Short Prompt",
        "prompt_continue": "Continue",
        "prompt_refactor": "Refactor",
        "prompt_add_feature": "Add Feature",
    }
}


class Localization:
    _instance = None

    def __init__(self):
        self._lang = "ru"

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def lang(self):
        return self._lang

    @lang.setter
    def lang(self, value):
        if value in TRANSLATIONS:
            self._lang = value

    def t(self, key, *args):
        """Get translation for key, with optional format args"""
        text = TRANSLATIONS.get(self._lang, {}).get(key, key)
        if args:
            return text.format(*args)
        return text

    def toggle_lang(self):
        if self._lang == "ru":
            self._lang = "en"
        else:
            self._lang = "ru"
        return self._lang