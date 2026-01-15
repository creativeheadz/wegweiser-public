# Filepath: comment_maker.py
import os

def add_comment_to_html(filepath, comment_text):
    with open(filepath, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    # Prepare the comment line
    comment_line = f"<!-- {comment_text} -->\n"

    # Find the first non-blank line that isn't a DOCTYPE declaration
    insert_index = 0
    for i, line in enumerate(lines):
        if line.strip() and not line.strip().startswith('<!DOCTYPE'):
            insert_index = i
            break

    # Insert the comment line after the DOCTYPE or at the start if no DOCTYPE
    if not lines or lines[insert_index].strip() != comment_line.strip():
        lines.insert(insert_index, comment_line)

        # Write the updated lines back to the file
        with open(filepath, 'w', encoding='utf-8') as file:
            file.writelines(lines)

        return True  # Indicate that the file was modified
    return False

def add_comment_to_py(filepath, comment_text):
    try:
        with open(filepath, 'r', encoding='utf-8') as file:
            lines = file.readlines()
    except UnicodeDecodeError as e:
        print(f"UnicodeDecodeError for file: {filepath}. Error: {e}")
        try:
            # Try opening the file with utf-16 encoding
            with open(filepath, 'r', encoding='utf-16') as file:
                lines = file.readlines()
        except UnicodeDecodeError as e:
            print(f"Skipping file due to encoding issues: {filepath}. Error: {e}")
            return False

    # Prepare the comment line
    comment_line = f"# {comment_text}\n"

    # Add the comment line at the top if it's not already there
    if not lines or lines[0].strip() != comment_line.strip():
        lines.insert(0, comment_line)

        # Write the updated lines back to the file
        try:
            with open(filepath, 'w', encoding='utf-8') as file:
                file.writelines(lines)
            return True  # Indicate that the file was modified
        except UnicodeEncodeError as e:
            print(f"UnicodeEncodeError for file: {filepath}. Error: {e}")
            try:
                with open(filepath, 'w', encoding='utf-16') as file:
                    file.writelines(lines)
                return True  # Indicate that the file was modified
            except Exception as e:
                print(f"Failed to write to file {filepath}: {e}")
    return False


def process_files(base_path, extensions_comments, log_file):
    with open(log_file, 'w', encoding='utf-8') as log:
        for root, _, files in os.walk(base_path):
            # Skip the 'venv' directory
            if 'venv' in root:
                continue
            for file in files:
                for ext, comment_marker in extensions_comments.items():
                    if file.endswith(ext):
                        filepath = os.path.join(root, file)
                        relative_path = os.path.relpath(filepath, base_path)
                        comment_text = f"Filepath: {relative_path}"

                        # Determine the correct function based on file extension
                        if ext == '.html':
                            modified = add_comment_to_html(filepath, comment_text)
                        elif ext == '.py':
                            modified = add_comment_to_py(filepath, comment_text)
                        else:
                            modified = add_comment_to_file(filepath, comment_marker, comment_text)

                        # If the file was modified, log it
                        if modified:
                            log.write(f"{relative_path}\n")


def add_comment_to_file(filepath, comment_marker, comment_text):
    try:
        with open(filepath, 'r', encoding='utf-8') as file:
            lines = file.readlines()
    except UnicodeDecodeError:
        # Try with a different encoding if UTF-8 fails
        try:
            with open(filepath, 'r', encoding='utf-16') as file:
                lines = file.readlines()
        except UnicodeDecodeError:
            print(f"Skipping file due to encoding issues: {filepath}")
            return False

    # Prepare the comment line
    comment_line = f"{comment_marker} {comment_text}\n"

    # Add the comment line at the top if it's not already there
    if not lines or lines[0].strip() != comment_line.strip():
        lines.insert(0, comment_line)

        # Write the updated lines back to the file
        try:
            with open(filepath, 'w', encoding='utf-8') as file:
                file.writelines(lines)
            return True  # Indicate that the file was modified
        except UnicodeEncodeError:
            try:
                with open(filepath, 'w', encoding='utf-16') as file:
                    file.writelines(lines)
                return True  # Indicate that the file was modified
            except Exception as e:
                print(f"Failed to write to file {filepath}: {e}")
    return False

def main():
    # Define the extensions and their respective comment markers
    extensions_comments = {
        '.py': '#',
        '.html': '<!--',
        # Add more extensions and comment markers here if needed
    }

    # Get the current directory
    current_path = os.getcwd()

    # Define the log file path
    log_file = os.path.join(current_path, 'file_changes.log')

    # Process the files
    process_files(current_path, extensions_comments, log_file)

    print(f"Log file created at: {log_file}")

if __name__ == "__main__":
    main()
