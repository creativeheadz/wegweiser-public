# Filepath: app/tasks/hardware/prompts/__init__.py
import os

def load_base_prompt() -> str:
    prompt_path = os.path.join(os.path.dirname(__file__), 'base.prompt')
    with open(prompt_path, 'r') as f:
        return f.read()