# AI Travel Planner

This is a Flask application that generates travel itineraries using an AI model and provides an interactive UI. The project includes an optional 3D background (Spline) and a fallback canvas background.

## Quick start (local)

1. Create a Python virtual environment and activate it:

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and fill in the required keys (at minimum provide `SECRET_KEY`):

```bash
cp .env.example .env
# edit .env and add your keys
```

4. Initialize the database (creates `database.db`):

```bash
python init_db.py
```

5. Run the app:

```bash
python app.py
```

Open http://127.0.0.1:5000/ and register a user.

## Environment variables

- `GEMINI_API_KEY` — (optional) API key for the Gemini model. If not set, AI features will be disabled.
- `UNSPLASH_ACCESS_KEY` — (optional) access key for Unsplash image search.
- `SECRET_KEY` — Flask secret key (required for production).
- `ADMIN_PASSWORD` — password for accessing admin pages.

## Deployment notes

- You can push this repo to GitHub and deploy to Vercel using the provided `Dockerfile`, or deploy to Render, Railway, or any host that supports Python/Docker.

- Vercel: this repo includes a `Dockerfile` so you can deploy the project as a container on Vercel (select "Import Project" → "Use Dockerfile" or configure your project to use the Dockerfile). Alternatively, you can convert the Flask app to serverless functions if you prefer using Vercel Functions but that requires restructuring the app.

### Production server
For a simple production setup (or for local production testing), run with Gunicorn:

```bash
pip install gunicorn
gunicorn app:app
```

### Recommended GitHub -> Vercel workflow
1. Push the code to a GitHub repository.
2. On Vercel, import the project and choose to deploy from Git (select your repo).
3. Configure environment variables in Vercel (GEMINI_API_KEY, UNSPLASH_ACCESS_KEY, SECRET_KEY, ADMIN_PASSWORD).
4. If using the Dockerfile option, Vercel will build the container and deploy it.

### Vercel specifics and notes
- This repository includes a `Dockerfile` and a `vercel.json` that instruct Vercel to build the project using Docker (no additional changes required).
- A `.vercelignore` file is included to avoid uploading environment files, local DB files, and large assets (e.g., `AITRIP.zip`). Remove or relocate large files ( > 50MB ) before deploying for faster builds and a smaller repo.
- If you prefer automatic GitHub -> Vercel deployments, use Vercel's "Import Project" flow and configure your environment variables in the Vercel dashboard. You can also deploy manually by building the Docker image locally and pushing it to a container registry.

### Note about large files
The repo currently contains `AITRIP.zip` which exceeds GitHub's recommended 50MB. If you plan to keep the repository lightweight and avoid build issues, consider removing it and placing the asset in Releases, an external storage host, or using Git LFS.


## Contributing

Open a PR and include tests if adding behavior.

## License

MIT — see `LICENSE` file.
