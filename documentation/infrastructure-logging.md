### How-to: Implement Logging in Our Flask App Using the Custom Logging Utility with Message Type Control

This guide explains how to implement detailed logging in your Flask application using `app_logging_helper.py`, which captures contextual information such as client IP, user agent, and more. The utility also allows you to "sink" specific log levels (e.g., `INFO`, `DEBUG`, `ERROR`) by disabling logging for those levels as needed.

#### Prerequisites
- **Flask App**: Ensure you have a working Flask application.
- **Logging Directory**: The logging utility writes logs to a file in the `logs/` directory. Ensure this directory is writable by your Flask app.

#### Step 1: Configure Logging in Flask

Ensure your Flask app is set up to support logging. This typically involves configuring the app’s logger:

```python
if __name__ == '__main__':
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    logging.basicConfig(
        filename='logs/wegweiser.log',
        level=logging.INFO,
        format='%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    )
    app.run()
```

This configuration sets the logging level to `INFO`, logs messages to `wegweiser.log`, and includes details such as timestamps, file paths, and line numbers.

#### Step 2: Utilize the `log_with_route` Function with Message Type Control

The updated `log_with_route` function includes an option to sink messages of specific types, so you can prevent certain levels from being logged. To use this feature, import and use the `log_with_route` function from `app_logging_helper.py`. This function captures detailed information about each request, including:
- **Client IP**: Automatically extracted from the request context.
- **User Agent**: The device/browser making the request.
- **Route**: The endpoint and request method.
- **Custom Messages**: You can log messages at different levels (`INFO`, `WARNING`, `ERROR`, etc.).

##### Enable or Disable Logging for Specific Levels

The utility provides a `set_log_level_enabled` function, allowing you to turn logging on or off for specific levels dynamically. For example:

```python
from app.utilities.app_logging_helper import set_log_level_enabled

# Disable logging for INFO messages
set_log_level_enabled(logging.INFO, False)

# Enable logging for ERROR messages only
set_log_level_enabled(logging.ERROR, True)
```

This flexibility allows you to reduce noise in your logs by disabling lower-priority messages while still capturing critical events.

##### Example Usage

Here are two routes from `index.py` and `login.py` files demonstrating how to use `log_with_route` effectively.

###### Index Route (`index.py`)

```python
@index_bp.route('/')
def index():
    client_ip = get_client_ip(request)
    
    if 'user_id' in session:
        log_with_route(logging.INFO, f"Redirecting logged-in user from {client_ip} to dashboard")
        return redirect(url_for('dashboard_bp.dashboard'))
    else:
        log_with_route(logging.INFO, f"Rendering index page for client {client_ip} without active session")
        return render_template('index.html')
```

- **Purpose**: Logs whether a user is redirected to the dashboard or served the index page, along with the client IP.
- **Custom Message**: Logs with `INFO` level when users interact with the homepage, providing context such as IP address.

###### Login Route (`login.py`)

```python
@login_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def login():
    form = LoginForm()
    
    if request.method == 'POST':
        recaptcha_token = request.form.get('g-recaptcha-response')
        success, score, recaptcha_result = verify_recaptcha_v3(recaptcha_token)
        
        client_ip = get_client_ip()
        log_with_route(logging.INFO, f'reCAPTCHA result: {recaptcha_result} from IP: {client_ip}, session ID: {session.sid}')
        
        if not success or score < 0.5:
            flash('reCAPTCHA verification failed. Please try again.', 'danger')
            return redirect(url_for('login_bp.login'))

        email = form.email.data
        if bcrypt.check_password_hash(account.password, form.password.data):
            session['user_id'] = account.useruuid
            log_with_route(logging.INFO, f'Successful login from {client_ip} for email: {email}, session ID: {session.sid}')
            return redirect(url_for('dashboard_bp.dashboard'))
        else:
            log_with_route(logging.WARNING, f'Failed login attempt from {client_ip} for email: {email}, session ID: {session.sid}')
            return redirect(url_for('login_bp.login'))

    return render_template('login.html', form=form)
```

- **Purpose**: Logs key interactions during the login process, such as reCAPTCHA verification, successful login attempts, and failed logins.
- **Custom Message**: Logs reCAPTCHA results and login attempts at varying log levels (`INFO` for successful logins and `WARNING` for failed attempts).

#### Step 3: Understand the `log_with_route` Function

The `log_with_route` function is defined in `app_logging_helper.py` and takes the following parameters:

```python
def log_with_route(level, message, route=None, source_type="Application", exc_info=None):
```

- **level**: The logging level (e.g., `logging.INFO`, `logging.WARNING`, `logging.ERROR`).
- **message**: The message you want to log.
- **route**: (Optional) The route or endpoint for the log entry.
- **source_type**: (Optional) The type of source initiating the log (default: "Application").
- **exc_info**: (Optional) Pass exception details if logging an error.

The function automatically captures and logs additional context, such as:
- **Client IP**: Extracted from the request using `get_client_ip`.
- **User Agent**: The browser or client making the request.
- **Headers and Data**: Request headers and payload, if applicable.

#### Step 4: Ensure Proper Log File Management

The utility creates and writes to `wegweiser.log` within the `logs` directory. If the directory does not exist, it will be created. Ensure your application has write permissions to this directory.

### Conclusion

By following this guide, you can leverage the `log_with_route` utility to capture detailed logging information within your Flask app, with the added control of enabling or disabling specific logging levels. This setup helps monitor user interactions and diagnose issues while keeping log files clean and relevant.