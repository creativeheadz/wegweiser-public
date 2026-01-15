# GEMINI.md

## Project Overview

Wegweiser is a Python-based web application that serves as a management and control plane (MCP) for a fleet of agents. It appears to be designed for Managed Service Providers (MSPs) to interact with and manage endpoints.

The core of the project is a Flask web application with the following key features:

*   **Web Interface:** A Flask-based web application provides the user interface for managing agents and viewing data.
*   **Agent Communication:** The system uses a NATS messaging for communication between the server and the agents.
*   **Extensible Tool Framework (MCP):** A key feature is the Model Context Protocol (MCP) framework, which allows agents to expose system capabilities (like running osquery commands) as "tools" that can be used through a chat interface or automated workflows. This is a powerful and flexible way to interact with managed endpoints.
*   **Database:** A PostgreSQL database is used for data persistence, managed with SQLAlchemy and Flask-Migrate.
*   **Background Tasks:** Celery is used for running background tasks.
*   **Security:** The application uses Azure Key Vault for secret management, implements security headers, and has features for IP blocking.
*   **Loki Integration:** The project includes an integration with Loki, a scanner for Indicators of Compromise (IOCs).

## Building and Running

### Dependencies

The project uses Python and its dependencies are listed in `requirements.txt`. To install them, you would typically use pip:

```bash
pip install -r requirements.txt
```

### Running the Application

The web application is served using Gunicorn. The configuration is in `gunicorn.conf.py`. To run the application, you would use a command like this:

```bash
gunicorn --config gunicorn.conf.py wsgi:app
```

The application will be available on a Unix socket at `/opt/wegweiser/wegweiser.sock`.

### Running the MCP Server

The MCP server can be run as a standalone process for testing:

```bash
cd /opt/wegweiser/mcp
python3 agent_mcp_server.py
```

## Loki IOC Scanner

The project includes Loki, a simple IOC (Indicator of Compromise) and YARA scanner. Loki is used to detect malicious files and processes on a system. It uses the following detection methods:

*   **File Name IOC:** Regex matching on full file paths.
*   **YARA Rule Check:** YARA signature matching on file data and process memory.
*   **Hash Check:** Comparing MD5, SHA1, and SHA256 hashes of scanned files against known malicious hashes.
*   **C2 Back Connect Check:** Comparing process connection endpoints with C2 IOCs.

Loki is a separate Python project within the `Loki` directory. It has its own dependencies managed with Poetry and its own development conventions.

### Running the Loki Scanner

To run the Loki scanner, you first need to install its dependencies using Poetry:

```bash
cd Loki
poetry install
```

Then, you can run the scanner using the `loki_wrapper.py` script:

```bash
poetry run python loki_wrapper.py [options]
```

## Development Conventions

*   **Code Style:** The main project appears to follow standard Python coding conventions. The Loki sub-project uses `black` for code formatting and `isort` for import sorting.
*   **Database Migrations:** Database schema changes are managed using Flask-Migrate. To apply migrations, you would use the `flask db upgrade` command.
*   **Configuration:** The application is configured through environment variables and secrets stored in Azure Key Vault. The `.env.example` file shows the required environment variables.
*   **Blueprints:** The Flask application is organized using Blueprints, with routes defined in the `app/routes` directory.
*   **Static Assets:** Static assets like CSS and JavaScript are likely located in the `app/static` directory.
*   **Templates:** HTML templates are located in the `app/templates` directory.
*   **Static Typing:** The Loki sub-project uses `mypy` for static type checking.
*   **Testing:** The Loki sub-project uses `pytest` for testing.
