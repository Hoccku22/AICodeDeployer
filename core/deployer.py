# core/deployer.py
import os
import shutil
from pathlib import Path
from typing import Optional
from models.project import Project
import logging

logger = logging.getLogger(__name__)


class ProjectDeployer:
    """Создание проекта на диске из модели Project"""

    def deploy(self, project: Project, target_dir: str, overwrite: bool = False) -> str:
        project_dir = Path(target_dir) / project.metadata.name

        if project_dir.exists():
            if not overwrite:
                counter = 1
                while project_dir.exists():
                    project_dir = Path(target_dir) / f"{project.metadata.name}_{counter}"
                    counter += 1
            else:
                logger.warning(f"Перезаписываю: {project_dir}")

        logger.info(f"Создаю проект: {project_dir}")

        project_dir.mkdir(parents=True, exist_ok=True)

        created_files = 0
        for pf in project.files:
            file_path = project_dir / pf.relative_path
            file_path.parent.mkdir(parents=True, exist_ok=True)

            try:
                file_path.write_text(pf.content, encoding='utf-8')
                created_files += 1
                logger.debug(f"  Создан: {pf.relative_path}")
            except Exception as e:
                logger.error(f"  Ошибка создания {pf.relative_path}: {e}")

        readme_exists = any(
            f.relative_path.lower() in ('readme.md', 'readme.txt', 'readme')
            for f in project.files
        )
        if not readme_exists:
            self._create_readme(project, project_dir)

        logger.info(
            f"Проект создан: {created_files}/{len(project.files)} файлов "
            f"в {project_dir}"
        )

        return str(project_dir)

    def _create_readme(self, project: Project, project_dir: Path):
        meta = project.metadata
        lines = [f"# {meta.name}"]

        if meta.description:
            lines.extend(["", meta.description])

        lines.extend(["", "## Структура", "```"])
        lines.append(project.get_tree())
        lines.append("```")

        if meta.install_command:
            lines.extend(["", "## Установка", f"```bash\n{meta.install_command}\n```"])

        if meta.run_command:
            lines.extend(["", "## Запуск", f"```bash\n{meta.run_command}\n```"])

        if meta.build_command:
            lines.extend(["", "## Сборка", f"```bash\n{meta.build_command}\n```"])

        lines.extend([
            "", "---",
            f"*Сгенерировано AI Code Deployer*"
        ])

        readme_path = project_dir / "README.md"
        readme_path.write_text("\n".join(lines), encoding='utf-8')