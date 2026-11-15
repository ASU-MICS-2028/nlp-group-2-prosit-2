# Runs this API in a container, so the only thing you need to install is Docker.
# Build and start it with:  docker compose up   (see HOW_TO_RUN.md)

# A small official image with Python 3.11 already installed.
FROM python:3.11-slim

# Everything below happens inside the folder /app in the container.
WORKDIR /app

# Install the libraries first. Docker keeps this step cached, so a rebuild after a code change is quick.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Then copy the rest of the project (app/, tests/, ...).
COPY . .

# The API listens on port 8000.
EXPOSE 8000

# Start the API. 0.0.0.0 lets your computer reach it from outside the container.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
