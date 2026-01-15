#!/usr/bin/env python3
# Filepath: tools/unused_static_files_checker.py
"""
Script to find unused static files in a Flask application.
This script scans template files and route handlers for references to static files and
reports which static files aren't referenced anywhere.
"""

import os
import re
import sys
import argparse
from collections import defaultdict
from datetime import datetime

def find_all_files(directory, extensions=None):
    """Find all files in a directory and its subdirectories with given extensions."""
    if not os.path.exists(directory):
        print(f"Warning: Directory does not exist: {directory}")
        return []
        
    all_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if extensions is None or any(file.endswith(ext) for ext in extensions):
                all_files.append(os.path.join(root, file))
    return all_files

def extract_static_references(template_files, route_files):
    """Extract references to static files from template files and route handlers."""
    static_references = set()
    references_by_file = defaultdict(set)  # Track which static files are referenced by each file
    file_references = defaultdict(set)     # Track which files reference each static file
    
    print(f"Scanning {len(template_files)} template files for static references...")
    
    # Regular expressions to match different patterns of static file references in templates
    template_patterns = [
        # url_for('static', filename='...')
        r"url_for\s*\(\s*['\"]static['\"]\s*,\s*filename\s*=\s*['\"]([^'\"]+)['\"]\s*\)",
        
        # {{ url_for('static', filename='...') }}
        r"{{\s*url_for\s*\(\s*['\"]static['\"]\s*,\s*filename\s*=\s*['\"]([^'\"]+)['\"]\s*\)\s*}}",
        
        # href="/static/..." or src="/static/..."
        r"(?:href|src)\s*=\s*['\"](?:/static|static)/([^'\"]+)['\"]",
        
        # {{ static_url_for('...') }}
        r"{{\s*static_url_for\s*\(\s*['\"]([^'\"]+)['\"]\s*\)\s*}}",
        
        # Direct path references like /static/css/file.css
        r"['\"](?:/static|static)/([^'\"]+)['\"]",
        
        # Relative paths without /static/ prefix like assets/css/style.css
        r"(?:href|src)\s*=\s*['\"]assets/([^'\"]+)['\"]",
        
        # Other relative paths that might reference static files
        r"(?:href|src)\s*=\s*['\"](?!http)(?!//)((?:(?!\.html|\.php)[^'\"#?])+\.(css|js|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot))['\"]"
    ]
    
    for template_file in template_files:
        try:
            with open(template_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
                for pattern in template_patterns:
                    matches = re.findall(pattern, content)
                    for match in matches:
                        # Handle the case where match is a tuple (from the last pattern)
                        if isinstance(match, tuple):
                            match = match[0]
                        
                        static_references.add(match)
                        # Track which template references which static file
                        references_by_file[template_file].add(match)
                        file_references[match].add(template_file)
                        
                # Look for Jinja includes that might contain references to static files
                jinja_includes = re.findall(r"{%\s*include\s+['\"]([^'\"]+)['\"]", content)
                # Note: We don't process these here as they're already in template_files
        except UnicodeDecodeError:
            print(f"Warning: Could not read {template_file} as text")
        except Exception as e:
            print(f"Error processing {template_file}: {e}")
    
    # Also look for static references in route handlers
    print(f"Scanning {len(route_files)} route files for static references...")
    
    # Regular expressions to match different patterns in route handlers
    route_patterns = [
        # url_for('static', filename='...')
        r"url_for\s*\(\s*['\"]static['\"]\s*,\s*filename\s*=\s*['\"]([^'\"]+)['\"]\s*\)",
        
        # send_from_directory('static', '...')
        r"send_from_directory\s*\(\s*['\"]static['\"]\s*,\s*['\"]([^'\"]+)['\"]\s*\)",
        
        # send_file('static/...')
        r"send_file\s*\(\s*['\"](?:static|app/static|app/static/)/([^'\"]+)['\"]\s*\)",
        
        # Flask's send_static_file('...')
        r"send_static_file\s*\(\s*['\"]([^'\"]+)['\"]\s*\)",
        
        # Direct path references like /static/css/file.css
        r"['\"](?:/static|static)/([^'\"]+)['\"]",
        
        # Serving files via @app.route('/path/to/file')
        r"@\w+\.route\s*\(\s*['\"](?:/static|static)/([^'\"]+)['\"]\s*[\),]",
        
        # References in blueprint definitions
        r"Blueprint\s*\(\s*[^,]+,\s*[^,]+,\s*static_folder\s*=\s*['\"]([^'\"]+)['\"]\s*\)",
        
        # References to assets/ path
        r"['\"]assets/([^'\"]+)['\"]"
    ]
    
    for route_file in route_files:
        try:
            with open(route_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
                for pattern in route_patterns:
                    matches = re.findall(pattern, content)
                    for match in matches:
                        static_references.add(match)
                        references_by_file[route_file].add(match)
                        file_references[match].add(route_file)
                
                # Check for render_template calls to track which templates are used
                template_matches = re.findall(r"render_template\s*\(\s*['\"]([^'\"]+)['\"]\s*[,\)]", content)
                for template_name in template_matches:
                    references_by_file[route_file].add(f"TEMPLATE:{template_name}")
                
                # Check for @app.route definitions to understand URL paths
                route_paths = re.findall(r"@\w+\.route\s*\(\s*['\"]([^'\"]+)['\"]\s*[,\)]", content)
                for route_path in route_paths:
                    # Check if this is a direct file serving route
                    if route_path.startswith('/') and '.' in route_path.split('/')[-1]:
                        potential_file = route_path[1:]  # Remove leading slash
                        references_by_file[route_file].add(f"ROUTE:{potential_file}")
        except UnicodeDecodeError:
            print(f"Warning: Could not read {route_file} as text")
        except Exception as e:
            print(f"Error processing {route_file}: {e}")
    
    return static_references, references_by_file, file_references

def is_referenced(static_file, static_dir, static_references, file_references):
    """Check if a static file is referenced in the template or route files and return referencing files."""
    # Convert the full path to a relative path from the static directory
    relative_path = os.path.relpath(static_file, static_dir)
    
    # Replace backslashes with forward slashes for Windows compatibility
    relative_path = relative_path.replace('\\', '/')
    
    referencing_files = set()
    
    # Check if the relative path is directly in the static references
    if relative_path in static_references:
        referencing_files.update(file_references[relative_path])
        return True, referencing_files
    
    # Check for assets/css/* style references (mapping from assets/ to static/)
    if relative_path.startswith('css/') or relative_path.startswith('js/') or relative_path.startswith('images/'):
        asset_path = relative_path  # e.g. "css/bootstrap-extended.css"
        if asset_path in static_references:
            referencing_files.update(file_references[asset_path])
            return True, referencing_files
    
    # JavaScript and CSS files might be referenced as minified versions
    if relative_path.endswith('.js') or relative_path.endswith('.css'):
        # Check for .min.js or .min.css references
        min_path = relative_path.replace('.js', '.min.js').replace('.css', '.min.css')
        if min_path in static_references:
            referencing_files.update(file_references[min_path])
            return True, referencing_files
    
    # Some files might be referenced with wildcards or by directory
    # For instance, all files in a directory might be loaded dynamically
    base_dir = os.path.dirname(relative_path)
    if base_dir in static_references:
        referencing_files.update(file_references[base_dir])
        return True, referencing_files
    
    if base_dir + '/' in static_references:
        referencing_files.update(file_references[base_dir + '/'])
        return True, referencing_files
    
    # Special handling for common files that might not be directly referenced
    special_files = {
        'favicon.ico', 'robots.txt', 'security.txt', '.well-known/security.txt',
        'sitemap.xml', 'manifest.json', 'browserconfig.xml'
    }
    
    if os.path.basename(relative_path) in special_files or relative_path in special_files:
        # These files are typically served directly by web servers or referenced in HTML headers
        print(f"Note: {relative_path} is a special file that might be served directly")
        return True, {f"SPECIAL_FILE: {relative_path}"}
    
    # Check for basename match - file may be referenced without its path
    filename = os.path.basename(relative_path)
    for reference in static_references:
        if os.path.basename(reference) == filename:
            referencing_files.update(file_references[reference])
            return True, referencing_files
    
    # Check for partial matches (this is less reliable but catches some cases)
    for reference in static_references:
        if relative_path in reference or reference in relative_path:
            referencing_files.update(file_references[reference])
            return True, referencing_files
    
    # Check if file is served via a direct route
    for reference in static_references:
        if reference.startswith("ROUTE:") and reference[6:] == relative_path:
            referencing_files.update(file_references[reference])
            return True, referencing_files
    
    return False, referencing_files

def main(app_dir, templates_dir, static_dir, routes_dir=None, output_file=None, verbose=False):
    """Main function to find unused static files."""
    # Set up output - either to file or stdout
    if output_file:
        orig_stdout = sys.stdout
        try:
            f_out = open(output_file, 'w', encoding='utf-8')
            sys.stdout = f_out
        except Exception as e:
            print(f"Error opening output file {output_file}: {e}")
            print("Output will be sent to console instead.")
            output_file = None
    
    try:
        # Check if directories exist
        if not os.path.isdir(static_dir):
            print(f"Error: Static directory not found: {static_dir}")
            print(f"Current working directory: {os.getcwd()}")
            print("Available directories in current location:")
            for item in os.listdir('.'):
                if os.path.isdir(item):
                    print(f"  - {item}/")
                    
            # Try to find static folder inside app directory
            app_static_dir = os.path.join(app_dir, "static")
            if os.path.isdir(app_static_dir):
                print(f"\nFound static directory at: {app_static_dir}")
                static_dir = app_static_dir
            else:
                return
            
        if not os.path.isdir(templates_dir):
            print(f"Error: Templates directory not found: {templates_dir}")
            print(f"Current working directory: {os.getcwd()}")
            print("Available directories in current location:")
            for item in os.listdir('.'):
                if os.path.isdir(item):
                    print(f"  - {item}/")
                    
            # Try to find templates folder inside app directory
            app_templates_dir = os.path.join(app_dir, "templates")
            if os.path.isdir(app_templates_dir):
                print(f"\nFound templates directory at: {app_templates_dir}")
                templates_dir = app_templates_dir
            else:
                return
        
        if not routes_dir:
            # Try to find routes folder inside app directory
            app_routes_dir = os.path.join(app_dir, "routes")
            if os.path.isdir(app_routes_dir):
                print(f"\nFound routes directory at: {app_routes_dir}")
                routes_dir = app_routes_dir
            else:
                # If no routes directory found, use app directory to scan all Python files
                print(f"\nNo routes directory found, using app directory for Python files: {app_dir}")
                routes_dir = app_dir
        
        print(f"Static Files Analysis - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"================================================")
        print(f"Using app directory: {app_dir}")
        print(f"Using templates directory: {templates_dir}")
        print(f"Using static directory: {static_dir}")
        print(f"Using routes directory: {routes_dir}")
        
        # Find all template files
        template_files = find_all_files(templates_dir, ['.html', '.htm', '.j2', '.jinja', '.jinja2'])
        if not template_files:
            print(f"Warning: No template files found in {templates_dir}")
            print(f"Check if the path is correct and contains HTML templates")
            return
        
        # Find all route files
        route_files = find_all_files(routes_dir, ['.py'])
        if not route_files:
            print(f"Warning: No Python files found in {routes_dir}")
            print(f"Check if the path is correct and contains route handlers")
        
        # Find all static files
        static_files = find_all_files(static_dir)
        if not static_files:
            print(f"Warning: No static files found in {static_dir}")
            print(f"Check if the path is correct and contains static assets")
            return
        
        # Extract static references from template files and route handlers
        static_references, references_by_file, file_references = extract_static_references(template_files, route_files)
        
        if verbose:
            print(f"\nFound {len(static_files)} static files")
            print(f"Found {len(static_references)} unique static file references")
            print(f"Found {len(references_by_file)} files with static references")
            
            print("\nReferences found:")
            for ref in sorted(static_references):
                print(f"  - {ref}")
            
            print("\nFiles that reference static content:")
            for file_path in sorted(references_by_file.keys()):
                rel_path = os.path.relpath(file_path, os.getcwd())
                ref_count = len(references_by_file[file_path])
                print(f"  - {rel_path} ({ref_count} references)")
        
        # Check which static files aren't referenced
        unused_files = []
        used_files = []
        file_usage_map = {}  # Map each used static file to the files that reference it
        special_files = []   # Track files that are considered special (like robots.txt)
        
        print("Analyzing which static files are used...")
        for static_file in static_files:
            is_used, referencing_files = is_referenced(static_file, static_dir, static_references, file_references)
            if not is_used:
                unused_files.append(static_file)
            else:
                used_files.append(static_file)
                file_usage_map[static_file] = referencing_files
                
                # Check if this is a special file
                for ref in referencing_files:
                    if isinstance(ref, str) and ref.startswith("SPECIAL_FILE:"):
                        rel_path = os.path.relpath(static_file, static_dir).replace('\\', '/')
                        special_files.append(rel_path)
        
        # Group unused files by directory for easier analysis
        unused_by_dir = defaultdict(list)
        for file in unused_files:
            dir_name = os.path.dirname(os.path.relpath(file, static_dir))
            unused_by_dir[dir_name].append(os.path.basename(file))
        
        # Calculate statistics
        total_files = len(static_files)
        unused_count = len(unused_files)
        used_count = len(used_files)
        special_count = len(special_files)
        
        # Print results
        print(f"\n===== RESULTS =====")
        print(f"Total static files: {total_files}")
        print(f"Used static files: {used_count} ({used_count/total_files*100:.1f}%)")
        print(f"Unused static files: {unused_count} ({unused_count/total_files*100:.1f}%)")
        print(f"Special files (might be served directly): {special_count}")
        
        # List special files
        if special_count > 0:
            print("\n===== SPECIAL FILES =====")
            print("These files are typically served directly by web servers or referenced in HTML headers:")
            for file in sorted(special_files):
                print(f"  - {file}")
        
        # Group used files by the templates/Python files that reference them
        referencing_files_map = defaultdict(list)
        
        for static_file, referencing_files in file_usage_map.items():
            relative_path = os.path.relpath(static_file, static_dir).replace('\\', '/')
            for ref_file in referencing_files:
                if isinstance(ref_file, str) and ref_file.startswith("SPECIAL_FILE:"):
                    # Skip special files as they're handled separately
                    continue
                rel_ref_file = os.path.relpath(ref_file, os.getcwd())
                referencing_files_map[rel_ref_file].append(relative_path)
        
        if used_count > 0:
            print("\n===== USED STATIC FILES BY REFERENCING FILE =====")
            for referencing_file, static_files_list in sorted(referencing_files_map.items()):
                print(f"\n{referencing_file} ({len(static_files_list)} files):")
                for static_file in sorted(static_files_list):
                    print(f"  - {static_file}")
        
        if unused_count > 0:
            print("\n===== UNUSED FILES BY DIRECTORY =====")
            for dir_name, files in sorted(unused_by_dir.items()):
                if dir_name == '':
                    dir_name = '[root]'
                print(f"\n{dir_name}/ ({len(files)} files):")
                for file in sorted(files):
                    print(f"  - {file}")
        else:
            print("\nAll static files are referenced in the templates or routes!")
    
    finally:
        # Restore stdout if we redirected to a file
        if output_file:
            sys.stdout = orig_stdout
            f_out.close()
            print(f"Results written to {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Find unused static files in a Flask application")
    parser.add_argument("--app-dir", default="app", help="Path to the Flask application directory")
    parser.add_argument("--templates-dir", default="app/templates", help="Path to the templates directory")
    parser.add_argument("--static-dir", default="app/static", help="Path to the static directory")
    parser.add_argument("--routes-dir", default=None, help="Path to the routes directory (defaults to app/routes)")
    parser.add_argument("-o", "--output", help="Output file to write results to")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    args = parser.parse_args()
    
    try:
        main(args.app_dir, args.templates_dir, args.static_dir, args.routes_dir, args.output, args.verbose)
    except Exception as e:
        import traceback
        print(f"Error: {e}")
        print(traceback.format_exc())