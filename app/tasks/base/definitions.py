# Filepath: app/tasks/base/definitions.py
from typing import Dict
from importlib import import_module
from pathlib import Path

class AnalysisDefinitions:
    _definitions: Dict = {}

    @classmethod
    def load_definitions(cls):
        if not cls._definitions:
            tasks_dir = Path(__file__).parent.parent
            for task_dir in tasks_dir.iterdir():
                if task_dir.is_dir() and (task_dir / 'definition.py').exists():
                    module = import_module(f'app.tasks.{task_dir.name}.definition')
                    if hasattr(module, 'ANALYSIS_CONFIG'):
                        cls._definitions[module.ANALYSIS_CONFIG['type']] = module.ANALYSIS_CONFIG

    @classmethod
    def get_cost(cls, analysis_type: str) -> int:
        cls.load_definitions()
        return cls._definitions.get(analysis_type, {}).get('cost', 1)  # Default to 1 if not found

    @classmethod
    def get_config(cls, analysis_type: str) -> Dict:
        cls.load_definitions()
        return cls._definitions.get(analysis_type, {})

    @classmethod
    def get_all_configs(cls) -> Dict:
        """Get all analysis configurations"""
        cls.load_definitions()
        return cls._definitions