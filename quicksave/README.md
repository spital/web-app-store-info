# QuickSave

QuickSave is a simple, secure, and mobile-first web portal designed for clients of an accounting firm to easily upload documents, notes, and photos. The application is built with Python (FastHTML) and runs in Docker containers orchestrated by Docker Compose.

## Prerequisites

-   Docker
-   Docker Compose

## Getting Started

Follow these steps to set up and run the QuickSave application locally.

### 1. Configure Environment Variables

The application uses an `.env` file to manage user credentials and the application's secret key. You must create this file before starting the application.

1.  Copy the example file from the project root:
    ```bash
    cp .env.example .env
    ```
2.  Edit the `.env` file with a text editor.
    -   Define up to 10 users and their passwords using the format `USER_N=username:password`.
    -   Set a secret key for signing session cookies. This should be a long, random string.

    Your `.env` file should look like this:
    ```dotenv
    # User credentials (up to USER_10)
    USER_1=client_alpha:s3cure_p@ssw0rd_A
    USER_2=client_beta:s3cure_p@ssw0rd_B

    # Secret key for session signing
    APP_SECRET_KEY=your-super-secret-and-long-random-string
    ```
    You can generate a suitable secret key with this command: `openssl rand -hex 32`.

### 2. Set Up SSL Certificates

The Nginx service is configured to use HTTPS and requires an SSL certificate and a private key. For local development, you can generate a self-signed certificate.

1.  From the project root, create a directory to store the certificate and key:
    ```bash
    mkdir ssl
    ```
2.  **Place your SSL certificate and key inside the `ssl/` directory.** The files **must** be named exactly as follows:
    -   Certificate: `quicksave.pem`
    -   Private Key: `quicksave.key`

    If you need to generate a self-signed certificate for local testing, you can use OpenSSL:
    ```bash
    openssl req -x509 -newkey rsa:4096 -nodes -out ssl/quicksave.pem -keyout ssl/quicksave.key -days 365 \
      -subj "/C=US/ST=California/L=SanFrancisco/O=QuickSave/OU=Dev/CN=localhost"
    ```
    When you access the site in your browser, you will need to accept the security warning for the self-signed certificate.

### 3. Build and Run the Application

Once the `.env` file and SSL certificates are in place, you can build and run the application using Docker Compose from the project root.

```bash
docker-compose up --build -d
```

The `--build` flag rebuilds the images if the code has changed, and `-d` runs the containers in detached mode (in the background).

### 4. Access the Application

The QuickSave portal will be available at:

**https://localhost**

You can log in with any of the user credentials you defined in your `.env` file.

---

## Project Structure

-   `quicksave/`
    -   `docker-compose.yml`: Orchestrates the `app` and `nginx` services.
    -   `.env.example`: Template for environment variables.
    -   `app/`: The FastHTML Python application.
    -   `nginx/`: The Nginx reverse proxy configuration.
    -   `data/`: Persistent volume for the SQLite database.
    -   `ssl/`: Directory for SSL certificates (must be created by the user).
    -   `README.md`: This file.
