
import os
import re
import importlib

# Define the root directory of your Flask project
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# Define directories to check
MODELS_DIR = os.path.join(PROJECT_ROOT, 'models')
ROUTES_DIR = os.path.join(PROJECT_ROOT, 'routes')
TEMPLATES_DIR = os.path.join(PROJECT_ROOT, 'templates')
STATIC_DIR = os.path.join(PROJECT_ROOT, 'static')

# Function to check if files in a directory are imported in __init__.py
def check_imports(directory):
    init_file = os.path.join(directory, '__init__.py')
    if not os.path.exists(init_file):
        print(f"__init__.py not found in {directory}")
        return

    with open(init_file, 'r') as file:
        content = file.read()

    files = [f[:-3] for f in os.listdir(directory) if f.endswith('.py') and f != '__init__.py']
    missing_imports = []

    for f in files:
        if f not in content:
            missing_imports.append(f)

    if missing_imports:
        print(f"Missing imports in {init_file}: {', '.join(missing_imports)}")
    else:
        print(f"All files are correctly imported in {init_file}")

# Function to check blueprints in routes
def check_blueprints(directory):
    blueprint_pattern = re.compile(r"Blueprint\('(\w+)'")
    registered_pattern = re.compile(r"app\.register_blueprint\((\w+)_bp")

    blueprints = {}
    registered_blueprints = []

    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                with open(file_path, 'r') as f:
                    content = f.read()
                    for match in blueprint_pattern.findall(content):
                        blueprints[match] = file_path
                    for match in registered_pattern.findall(content):
                        registered_blueprints.append(match)

    missing_blueprints = [bp for bp in blueprints.keys() if bp not in registered_blueprints]

    if missing_blueprints:
        print(f"Unregistered blueprints found: {', '.join(missing_blueprints)}")
    else:
        print("All blueprints are registered")

# Function to check template references
def check_templates(directory):
    template_pattern = re.compile(r"render_template\(['\"](\w+\.html)['\"]")
    templates = [f for f in os.listdir(TEMPLATES_DIR) if f.endswith('.html')]

    missing_templates = []

    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                with open(file_path, 'r') as f:
                    content = f.read()
                    for match in template_pattern.findall(content):
                        if match not in templates:
                            missing_templates.append(match)

    if missing_templates:
        print(f"Missing templates: {', '.join(missing_templates)}")
    else:
        print("All templates exist")

# Function to check static file references
def check_static_files(directory):
    static_pattern = re.compile(r"url_for\('static', filename=['\"](\w+\.js)['\"]")
    static_files = [f for f in os.listdir(STATIC_DIR) if f.endswith('.js')]

    missing_static_files = []

    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                with open(file_path, 'r') as f:
                    content = f.read()
                    for match in static_pattern.findall(content):
                        if match not in static_files:
                            missing_static_files.append(match)

    if missing_static_files:
        print(f"Missing static files: {', '.join(missing_static_files)}")
    else:
        print("All static files exist")

if __name__ == "__main__":
    print("Checking imports...")
    check_imports(MODELS_DIR)
    check_imports(ROUTES_DIR)

    print("\nChecking blueprints...")
    check_blueprints(ROUTES_DIR)

    print("\nChecking templates...")
    check_templates(ROUTES_DIR)

    print("\nChecking static files...")
    check_static_files(ROUTES_DIR)

    print("\nValidation complete.")


