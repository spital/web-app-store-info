import os
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from fasthtml.fastapp import FastHTML, serve
from fasthtml.components import *
from dotenv import load_dotenv
from starlette.datastructures import UploadFile
from starlette.responses import Response, RedirectResponse

# Load environment variables from .env file for local development
load_dotenv()

# --- App Setup ---
# The 'secret' is used for signing session cookies
app = FastHTML(secret=os.environ.get("APP_SECRET_KEY", "your-default-secret-key"))
db_path = 'data/quicksave.db'

def smart_redirect(url: str, htmx: bool = False):
    """
    Redirects the user.
    Sends a standard 307 redirect for regular requests,
    and an HX-Redirect header for HTMX requests.
    """
    if htmx:
        return Response(headers={'HX-Redirect': url})
    return RedirectResponse(url=url)

# --- Database Connection ---
def get_db_conn():
    """Establishes a connection to the database."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

# --- Database Initialization ---
def init_db():
    """Initializes the database and creates tables if they don't exist."""
    # Ensure the data directory exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

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
    """Loads users from environment variables into the database."""
    with get_db_conn() as conn:
        cursor = conn.cursor()

        for i in range(1, 11): # Checks for USER_1 to USER_10
            user_var = os.environ.get(f'USER_{i}')
            if user_var and ':' in user_var:
                username, password = user_var.split(':', 1)

                # Check if user already exists
                cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
                if cursor.fetchone() is None:
                    # User does not exist, so insert them
                    password_hash = generate_password_hash(password)
                    cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, password_hash))
                    print(f"User '{username}' created.")
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
        with open('app/templates/login.html', 'r', encoding='utf-8') as f:
            # We return the raw HTML content. The browser will render it.
            return f.read()
    except FileNotFoundError:
        return P("Error: Login page not found."), 500

@app.post("/login")
def login_post(username: str, password: str, session, htmx: bool = False):
    """Handles the login form submission, designed to work with HTMX."""
    with get_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()

    if user and check_password_hash(user['password_hash'], password):
        # On successful login, set the user's ID and username in the session.
        session['user_id'] = user['id']
        session['username'] = user['username']

        # This header tells HTMX to perform a full page redirect to the home page.
        return smart_redirect('/', htmx=htmx)
    else:
        # On failure, return an HTML fragment with an error message.
        # HTMX will place this inside the '#error-message' div on the login page.
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
        with open('app/templates/index.html', 'r', encoding='utf-8') as f:
            content = f.read()

        username = session.get('username', 'User')
        # Simple template substitution for the username placeholder
        return content.replace('{{username}}', username)
    except FileNotFoundError:
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

# --- Startup Logic ---
# This code runs once when the application starts, whether with 'serve()' or Gunicorn.
init_db()
load_users_from_env()

# This is for running locally without Gunicorn
if __name__ == '__main__':
    # Get port from environment variable, default to 8888 if not set
    port = int(os.getenv("PORT", "8888"))
    serve(port=port)
