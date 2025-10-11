import os
import sys
import sqlite3
import logging
from werkzeug.security import generate_password_hash, check_password_hash
from quart import Quart, render_template, request, session, redirect, url_for, flash
from dotenv import load_dotenv
from starlette.datastructures import UploadFile
from .config import DB_PATH, DATA_DIR, TEMPLATES_DIR

# Load environment variables from .env file for local development
load_dotenv()

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- App Setup ---
app = Quart(__name__, template_folder=TEMPLATES_DIR)
app.secret_key = os.environ.get("APP_SECRET_KEY", "your-default-secret-key")


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
    """
    env_users = {}
    for i in range(1, 11):  # Checks for USER_1 to USER_10
        user_var = os.environ.get(f'USER_{i}')
        if user_var and ':' in user_var:
            username, password = user_var.split(':', 1)
            env_users[username] = password

    if not env_users:
        return

    with get_db_conn() as conn:
        cursor = conn.cursor()
        for username, password in env_users.items():
            password_hash = generate_password_hash(password)
            cursor.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
            user_row = cursor.fetchone()
            if user_row is None:
                cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, password_hash))
                print(f"User '{username}' created.")
            elif not check_password_hash(user_row['password_hash'], password):
                cursor.execute("UPDATE users SET password_hash = ? WHERE username = ?", (password_hash, username))
                print(f"Password for user '{username}' updated.")
        conn.commit()

# --- Middleware to protect routes ---
@app.before_request
async def before_request():
    """Checks if a user is logged in before serving most pages."""
    # List of endpoints that do not require login
    exempt_endpoints = ['login', 'static', 'logout']

    if request.endpoint not in exempt_endpoints and 'user_id' not in session:
        await flash("Pro zobrazení této stránky se musíte přihlásit.", 'error')
        return redirect(url_for('login'))

# --- Application Routes ---

@app.route("/login", methods=['GET', 'POST'])
async def login():
    """Handles login for both GET and POST requests."""
    if 'user_id' in session:
        return redirect(url_for('home'))

    if request.method == 'POST':
        form = await request.form
        username = form.get('username')
        password = form.get('password')

        with get_db_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
            user = cursor.fetchone()

        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            await flash("Přihlášení proběhlo úspěšně!", 'success')
            return redirect(url_for('home'))
        else:
            await flash("Neplatné uživatelské jméno nebo heslo.", 'error')
            return redirect(url_for('login'))

    return await render_template('login.html')

@app.route("/logout")
async def logout():
    """Clears the session and redirects to login."""
    session.clear()
    await flash("Byli jste odhlášeni.", 'success')
    return redirect(url_for('login'))

@app.route("/")
async def home():
    """Serves the main dashboard page."""
    return await render_template('index.html')

# --- Routes for serving action pages ---
@app.route("/add-note-page")
async def add_note_page():
    return await render_template('add_note.html')

@app.route("/add-image-page")
async def add_image_page():
    return await render_template('add_image.html')

@app.route("/add-document-page")
async def add_document_page():
    return await render_template('add_document.html')

@app.route("/add-photo-page")
async def add_photo_page():
    return await render_template('add_photo.html')

# --- Helper function for saving items ---
def save_item(user_id: int, item_type: str, content: bytes):
    """Saves an item to the database."""
    with get_db_conn() as conn:
        conn.execute("INSERT INTO items (user_id, type, content) VALUES (?, ?, ?)", (user_id, item_type, content))
        conn.commit()

# --- Routes for handling form submissions ---
@app.route("/add/note", methods=['POST'])
async def add_note():
    form = await request.form
    content = form.get('content')
    if not content or not content.strip():
        await flash("Obsah poznámky nemůže být prázdný.", 'error')
        return redirect(url_for('add_note_page'))

    save_item(session['user_id'], 'note', content.encode('utf-8'))
    await flash("Poznámka byla úspěšně uložena!", 'success')
    return redirect(url_for('home'))

async def handle_upload(item_type: str, redirect_route: str):
    """Generic handler for file uploads with improved logging."""
    logging.info(f"Starting upload for item_type: {item_type}")
    try:
        files = await request.files
        file = files.get('file')

        if not file or not file.filename:
            await flash("Nebyl vybrán žádný soubor.", 'error')
            logging.warning("Upload attempt with no file selected.")
            return redirect(url_for(redirect_route))

        MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB

        # Read the file in synchronous chunks to be memory-efficient
        # without causing a TypeError with the FileStorage object.
        content = bytearray()
        chunk_size = 1024 * 1024  # 1MB chunks
        while True:
            chunk = file.read(chunk_size)
            if not chunk:
                break
            content.extend(chunk)
            if len(content) > MAX_FILE_SIZE:
                await flash(f"Soubor je příliš velký (max. {MAX_FILE_SIZE // 1024 // 1024} MB).", 'error')
                logging.warning(f"Upload failed: File '{file.filename}' exceeded max size.")
                return redirect(url_for(redirect_route))

        content = bytes(content)

        logging.info(f"File '{file.filename}' read successfully, total size: {len(content)} bytes.")

        save_item(session['user_id'], item_type, content)
        logging.info(f"Item '{file.filename}' of type '{item_type}' saved to database.")

        item_type_map = {
            'image': 'Obrázek',
            'document': 'Dokument',
            'photo': 'Fotka'
        }
        item_type_cz = item_type_map.get(item_type, item_type.capitalize())
        await flash(f"{item_type_cz} '{file.filename}' byl úspěšně uložen!", 'success')
        return redirect(url_for('home'))

    except Exception as e:
        logging.error(f"An unexpected error occurred during upload: {e}", exc_info=True)
        await flash("Během nahrávání souboru došlo k neočekávané chybě.", 'error')
        return redirect(url_for(redirect_route))

@app.route("/add/image", methods=['POST'])
async def add_image():
    return await handle_upload('image', 'add_image_page')

@app.route("/add/document", methods=['POST'])
async def add_document():
    return await handle_upload('document', 'add_document_page')

@app.route("/add/photo", methods=['POST'])
async def add_photo():
    return await handle_upload('photo', 'add_photo_page')

# --- Startup event ---
@app.before_serving
async def startup_event():
    """Handles database initialization and user loading on startup."""
    print("Application startup: Initializing database and loading users...")
    check_data_directory_permissions()
    init_db()
    load_users_from_env()
    print("Application startup complete.")

# This part is for local development.
# The production server will use a command like `hypercorn main:app`.
if __name__ == '__main__':
    app.run(debug=True, port=5000)