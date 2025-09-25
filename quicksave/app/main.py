import os
import sys
import sqlite3
import logging
from werkzeug.security import generate_password_hash, check_password_hash
from fasthtml.fastapp import FastHTML, serve
from fasthtml.components import *
from dotenv import load_dotenv
from starlette.datastructures import UploadFile
from starlette.responses import Response, RedirectResponse
from config import DB_PATH, DATA_DIR, TEMPLATES_DIR

# Load environment variables from .env file for local development
load_dotenv()

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- App Setup ---
# The 'secret' is used for signing session cookies
app = FastHTML(secret=os.environ.get("APP_SECRET_KEY", "your-default-secret-key"))

def smart_redirect(url: str, htmx: bool = False):
    """
    Redirects the user.
    Sends a standard 303 redirect for regular requests,
    and an HX-Redirect header for HTMX requests.
    A 303 redirect instructs the browser to change the request method to GET.
    """
    if htmx:
        return Response(headers={'HX-Redirect': url})
    return RedirectResponse(url=url, status_code=303)

# --- Database Connection ---
def get_db_conn():
    """Establishes a connection to the database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def check_data_directory_permissions():
    """
    Checks if the application has write permissions to the data directory.
    If not, it prints a helpful error message and exits. This is a common
    issue when switching between Docker (runs as root) and local dev.
    """
    os.makedirs(DATA_DIR, exist_ok=True)

    if not os.access(DATA_DIR, os.W_OK):
        user = os.getenv('USER', 'your_user')
        error_message = (
            f"\\n!!! PERMISSION ERROR !!!\\n"
            f"The application does not have write permissions for the data directory: {DATA_DIR}\n"
            f"This is likely because the directory was created by Docker with root permissions.\\n\\n"
            f"To fix this, please run the following command in your terminal:\\n"
            f"sudo chown -R {user}:{user} {DATA_DIR}\n"
        )
        print(error_message, file=sys.stderr)
        sys.exit(1)

# --- Database Initialization ---
def init_db():
    """Initializes the database and creates tables if they don't exist."""
    with get_db_conn() as conn:
        cursor = conn.cursor()

        # Create 'users' table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL
            )
        ''')

        # Create 'items' table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                type TEXT NOT NULL,
                content BLOB NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')

        conn.commit()
        print("Database initialized successfully.")

# --- User Loading ---
def load_users_from_env():
    """
    Synchronizes users from environment variables with the database.
    - Adds users from .env that are not in the database.
    - Deletes users from the database that are not in the .env file.
    - Updates passwords for existing users if they have changed in .env.
    """
    env_users = {}
    for i in range(1, 11):  # Checks for USER_1 to USER_10
        user_var = os.environ.get(f'USER_{i}')
        if user_var and ':' in user_var:
            username, password = user_var.split(':', 1)
            env_users[username] = password

    with get_db_conn() as conn:
        cursor = conn.cursor()

        # Get all users from the database
        cursor.execute("SELECT id, username, password_hash FROM users")
        db_users = {row['username']: {'id': row['id'], 'hash': row['password_hash']} for row in cursor.fetchall()}

        # Users to add/update
        for username, password in env_users.items():
            password_hash = generate_password_hash(password)
            if username not in db_users:
                cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, password_hash))
                print(f"User '{username}' created.")
            elif not check_password_hash(db_users[username]['hash'], password):
                cursor.execute("UPDATE users SET password_hash = ? WHERE username = ?", (password_hash, username))
                print(f"Password for user '{username}' updated.")

        # Users to delete
        for username in db_users:
            if username not in env_users:
                cursor.execute("DELETE FROM users WHERE username = ?", (username,))
                print(f"User '{username}' deleted.")

        conn.commit()

# --- Application Routes ---

@app.get("/login")
def login_get(session, htmx: bool = False):
    """Serves the static login HTML page."""
    # If user is already logged in, redirect them to the home page.
    if session.get('user_id'):
        return smart_redirect('/', htmx=htmx)

    # This is a simple way to serve a static file. For a larger app,
    # serving static assets should be handled by Nginx.
    try:
        login_path = os.path.join(TEMPLATES_DIR, 'login.html')
        with open(login_path, 'r', encoding='utf-8') as f:
            # We return the raw HTML content. The browser will render it.
            return f.read()
    except FileNotFoundError:
        logging.error(f"Template file not found at path: {login_path}")
        return P("Error: Login page not found."), 500

@app.post("/login")
def login_post(username: str, password: str, session, htmx: bool = False):
    """Handles the login form submission, designed to work with HTMX."""
    logging.info(f"Login attempt for username: '{username}'")
    with get_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()

    if user:
        logging.info(f"User '{username}' found in the database.")
        password_match = check_password_hash(user['password_hash'], password)
        logging.info(f"Password check for user '{username}': {'Success' if password_match else 'Failed'}")
        if password_match:
            # On successful login, set the user's ID and username in the session.
            session['user_id'] = user['id']
            session['username'] = user['username']
            logging.info(f"Login successful for user '{username}'.")
            # Upon successful login, we send back a script that performs a client-side redirect.
            # This is a reliable way to ensure redirection after a successful HTMX form submission.
            return """<script>
                        document.getElementById('login-form-message').innerHTML = '<p style="color: var(--pico-color-green-500);">Login successful! Redirecting...</p>';
                        window.location.href = '/';
                    </script>"""
    else:
        logging.warning(f"User '{username}' not found in the database.")

    # On failure, return an HTML fragment with an error message.
    # HTMX will place this inside the '#error-message' div on the login page.
    logging.warning(f"Invalid login attempt for username: '{username}'")
    return P('Invalid username or password.', style="color: var(--pico-color-red-500);")

@app.get("/logout")
def logout(session, htmx: bool = False):
    """Clears the session and redirects the user to the login page."""
    session.clear()
    return smart_redirect('/login', htmx=htmx)


@app.get("/")
def home(session, htmx: bool = False):
    """
    The main application page. Requires login.
    Renders the index.html template with dynamic data.
    """
    if not session.get('user_id'):
        return smart_redirect('/login', htmx=htmx)

    try:
        index_path = os.path.join(TEMPLATES_DIR, 'index.html')
        with open(index_path, 'r', encoding='utf-8') as f:
            content = f.read()

        username = session.get('username', 'User')
        # Simple template substitution for the username placeholder
        return content.replace('{{username}}', username)
    except FileNotFoundError:
        logging.error(f"Template file not found at path: {index_path}")
        return P("Error: Main page template not found."), 500

def save_item(user_id: int, item_type: str, content: bytes):
    """Helper function to save an item to the database."""
    with get_db_conn() as conn:
        conn.execute(
            "INSERT INTO items (user_id, type, content) VALUES (?, ?, ?)",
            (user_id, item_type, content)
        )
        conn.commit()

@app.post("/add/note")
def add_note(content: str, session, htmx: bool = False):
    """Saves a text note."""
    if not (user_id := session.get('user_id')):
        return smart_redirect('/login', htmx=htmx)

    if not content or not content.strip():
        return P("Note content cannot be empty.", style="color: var(--pico-color-red-500);")

    save_item(user_id, 'note', content.encode('utf-8'))
    return P("Note saved successfully!", style="color: var(--pico-color-green-500);")

async def handle_upload(file: UploadFile, item_type: str, session, htmx: bool = False):
    """Generic handler for file uploads."""
    if not (user_id := session.get('user_id')):
        return smart_redirect('/login', htmx=htmx)

    if not file or not file.filename:
        return P("File not provided.", style="color: var(--pico-color-red-500);")

    # Read the file content in chunks to handle large files gracefully
    MAX_FILE_SIZE = 50 * 1024 * 1024 # 50 MB limit
    content = bytearray()
    while chunk := await file.read(8192):
        content.extend(chunk)
        if len(content) > MAX_FILE_SIZE:
            return P(f"File exceeds the {MAX_FILE_SIZE // 1024 // 1024}MB size limit.", style="color: var(--pico-color-red-500);")

    save_item(user_id, item_type, bytes(content))
    return P(f"{item_type.capitalize()} '{file.filename}' saved successfully!", style="color: var(--pico-color-green-500);")

@app.post("/add/image")
async def add_image(file: UploadFile):
    """Saves an uploaded image."""
    return await handle_upload(file, 'image')

@app.post("/add/document")
async def add_document(file: UploadFile):
    """Saves an uploaded document."""
    return await handle_upload(file, 'document')

@app.post("/add/photo")
async def add_photo(file: UploadFile):
    """Saves a photo taken with the camera."""
    return await handle_upload(file, 'photo')

@app.on_event("startup")
async def startup_event():
    """
    This function runs once when the application starts.
    It handles database initialization and user loading.
    """
    print("Application startup: Initializing database and loading users...")
    check_data_directory_permissions()
    init_db()
    load_users_from_env()
    print("Application startup complete.")
