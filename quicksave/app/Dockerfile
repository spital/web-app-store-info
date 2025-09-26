# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory for the application
WORKDIR /code

# Copy only the requirements file first to leverage Docker cache
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire application source code into an 'app' subdirectory
# This makes the 'app' directory a package that can be imported from.
COPY . ./app

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Run the application as a module
# This ensures that relative imports within the 'app' package work correctly.
# The working directory is /code, so Python can find the 'app' package.
CMD ["hypercorn", "app.main:app", "--bind", "0.0.0.0:8000", "--workers", "2"]