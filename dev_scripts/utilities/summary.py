# Filepath: tools/summary.py
import os
import psycopg2

def read_file_content(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()

def write_document(doc_path, content):
    with open(doc_path, 'w', encoding='utf-8') as doc:
        doc.write(content)

def build_sitemap(dir_path, ignore_dirs):
    sitemap = {}
    for root, dirs, files in os.walk(dir_path):
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        current_dir = sitemap
        path = root.split(os.path.sep)
        for i, component in enumerate(path[1:]):  # Skip root directory
            if component not in current_dir:
                current_dir[component] = {}
            current_dir = current_dir[component]
        # Add files directly under current directory to sitemap
        current_dir['__files__'] = files
    return sitemap

def traverse_directory(directory):
    ignore_dirs = ['____garbage', 'venv', 'migrations', '.git', 'static', '__pycache__', 'ophanedCollectors', 'sucessfulImport', 'flask_session', 'deviceFiles', 'logs', 'payloads', 'tools', 'wlog' ]
    sitemap = build_sitemap(directory, ignore_dirs)

    file_structure = {}
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        for file in files:
            if file.endswith('.py') or file.endswith('.html'):
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, directory)
                file_structure[relative_path] = read_file_content(file_path)
    return sitemap, file_structure

def format_content(file_structure):
    formatted_content = ""
    for path, content in file_structure.items():
        formatted_content += f"############ {path}:\n\n{content}\n############ {path}############END############\n\n"
    return formatted_content

def get_db_structure():
    db_url = os.environ.get('DATABASE_URL', 'postgresql://user:password@localhost/dbname')
    query = """
    SELECT
        c.table_schema,
        c.table_name,
        c.column_name,
        c.data_type,
        c.character_maximum_length,
        c.numeric_precision,
        c.numeric_scale,
        c.is_nullable,
        c.column_default
    FROM
        information_schema.columns c
    JOIN
        information_schema.tables t
        ON c.table_name = t.table_name
        AND c.table_schema = t.table_schema
    WHERE
        t.table_type = 'BASE TABLE' and c.table_schema like 'public'
    ORDER BY
        c.table_schema, c.table_name, c.ordinal_position;
    """
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    cur.execute(query)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    header = f"############ Current DB structure:\n\n"
    db_structure = header
    for row in rows:
        db_structure += f"Schema: {row[0]}, Table: {row[1]}, Column: {row[2]}, Type: {row[3]}, Max Length: {row[4]}, Precision: {row[5]}, Scale: {row[6]}, Nullable: {row[7]}, Default: {row[8]}\n"
    return db_structure

def print_sitemap(sitemap, current_path="", indent=0):
    sitemap_content = ""
    for key, value in sitemap.items():
        if key == '__files__':
            # Print files directly under current directory
            if value:
                for file in value:
                    sitemap_content += '  ' * (indent + 1) + '- ' + file + '\n'
        else:
            sitemap_content += '  ' * indent + '- ' + key + '\n'
            sitemap_content += print_sitemap(value, current_path + key + "/", indent + 1)
    return sitemap_content

def sync_code_with_document(project_directory, document_path):
    sitemap, file_structure = traverse_directory(project_directory)
    db_structure = get_db_structure()
    formatted_content = format_content(file_structure)
    
    sitemap_content = "### Directory Sitemap:\n\n"
    sitemap_content += print_sitemap(sitemap, indent=1)
    
    final_content = sitemap_content + "\n\n" + db_structure + "\n\n" + formatted_content
    
    # Adjust document_path to use the correct absolute path
    absolute_document_path = os.path.join(project_directory, document_path)
    
    # Write final_content to the document
    write_document(absolute_document_path, final_content)
    
    print(f"Document {absolute_document_path} has been updated successfully with the enhanced sitemap.")

if __name__ == "__main__":
    project_directory = "/opt/wegweiser/"  # Absolute path to project directory
    document_path = "routes.txt"  # Document path relative to the project directory
    sync_code_with_document(project_directory, document_path)
