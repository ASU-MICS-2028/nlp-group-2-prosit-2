# How to run your API on your own computer

This folder is the API that Mesora API Builder made for you. Its tests passed before you downloaded it.
Pick **one** of the two ways below. When the API is running, open **http://localhost:8000/docs** in your
browser: you will see every endpoint, and "Try it out" lets you call them.

## Way 1: with Docker (easiest if you have Docker Desktop)

1. Install Docker Desktop from https://www.docker.com/products/docker-desktop/ and start it.
2. Unzip this file. Open a terminal in the unzipped folder
   (Windows: open the folder, click the address bar, type `cmd` and press Enter.
   Mac: right-click the folder and choose "New Terminal at Folder").
3. Type this and press Enter:

   ```
   docker compose up
   ```

   The first time takes a minute or two while Docker downloads Python and the libraries.
4. Open http://localhost:8000/docs.
5. To stop the API, go back to the terminal and press `Ctrl` + `C`.

## Way 2: with Python

1. Install Python 3.11 or newer from https://www.python.org/downloads/
   (on Windows, tick "Add python.exe to PATH" during the install).
2. Unzip this file and open a terminal in the unzipped folder (see Way 1, step 2).
3. Type these commands one at a time, pressing Enter after each:

   Windows:
   ```
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   uvicorn app.main:app
   ```

   Mac or Linux:
   ```
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   uvicorn app.main:app
   ```

4. Open http://localhost:8000/docs.
5. To stop the API, press `Ctrl` + `C` in the terminal.

## Check that it still works

With Way 2 set up, run the API's own tests:

```
python -m pytest -q
```

Every test should pass.

## Good to know

- Your data is saved in a file called `app.db` in this folder. Delete that file to start with an empty API.
  With Docker, the data is inside the container and is lost when the container is removed.
- If port 8000 is already in use, Way 2 can use another port: `uvicorn app.main:app --port 8001`,
  then open http://localhost:8001/docs.
