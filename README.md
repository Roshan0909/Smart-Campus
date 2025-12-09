# Smart Campus (Student Campus) – AI-Powered Learning Management System

A Django-based learning platform that layers Google Gemini-powered search, summarization, and quiz generation on top of PDF/Docx/PPT course materials. It supports teacher workflows (content upload, quiz creation, messaging) and student learning tools (PDF chat, summaries, knowledge bot, quizzes, chat).

## Prerequisites
- Python 3.11+ (Django 5.2.x)
- Build tools (gcc/clang on Linux/Mac, Build Tools for Visual Studio on Windows) for some wheels if binaries are unavailable.
- External binaries for document processing:
  - **Poppler** (for `pdf2image`): install via `choco install poppler` on Windows or your package manager.
  - **Tesseract OCR** (for `pytesseract`): install via `choco install tesseract` on Windows or your package manager; ensure `tesseract` is on PATH.
  - **Ghostscript** (for some PDF conversions) recommended but not strictly required.

## Quick Start (local)
1. Clone and enter the repo:
   ```bash
   git clone https://github.com/Roshan0909/LangChain-PDF-Processor.git
   cd LangChain-PDF-Processor/campus
   ```
2. Create and activate a virtualenv (Windows PowerShell example):
   ```bash
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
3. Install Python deps (requirements file lives one level up):
   ```bash
   pip install -r ../requirements.txt
   ```
4. Create a `.env` in the `campus/` folder (same place as `manage.py`):
   ```env
   API_KEY=your_gemini_api_key                      # Required for AI (quiz, PDF chat, summarizer, knowledge bot)
   WIKIPEDIA_CLIENT_ID=your_wikipedia_client_id     # Optional, improves Knowledge Bot headers
   WIKIPEDIA_CLIENT_SECRET=your_wikipedia_client_secret
   ```
   For production, also set `SECRET_KEY`, `DEBUG=False`, and `ALLOWED_HOSTS=yourdomain.com` in `student_campus/settings.py` or via environment.
5. Initialize the database and admin user:
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```
6. Run the app:
   ```bash
   python manage.py runserver
   ```
   Visit http://localhost:8000 and log in with the superuser you created.

## Features
- **Teacher tools**: subject management, PDF/Docx/PPT uploads, Gemini-powered quiz generator, quiz analytics, messaging with attachments.
- **Student tools**: dashboard, AI PDF chat (vector search + Gemini), document summarizer, timed quizzes with review, knowledge bot (Wikipedia + Gemini), messaging with teachers.
- **Storage**: uploaded files in `media/`, FAISS indexes for PDFs in `faiss_indices/` folder (hashed per file).

## Project Layout (key paths)
```
README.md
requirements.txt
campus/
├── manage.py
├── app.py
├── authentication/   # Auth models, forms, views, urls
├── students/         # PDF chat, summaries, knowledge bot, quizzes
├── teachers/         # Quiz generation, subjects, reports, messaging
├── templates/        # Django templates (base, auth, teachers, students)
├── media/            # Uploads: notes/, chat_files/, proctoring/
├── faiss_indices/    # FAISS vector indexes (one per PDF, hashed by content)
└── student_campus/   # Django settings, urls, wsgi
```

## Full Directory Reference (trimmed)
```
.
├── README.md
├── requirements.txt
└── campus/
   ├── app.py
   ├── db.sqlite3
   ├── manage.py
   ├── authentication/
   │   ├── __init__.py
   │   ├── admin.py
   │   ├── apps.py
   │   ├── forms.py
   │   ├── models.py
   │   ├── tests.py
   │   ├── urls.py
   │   └── views.py
   ├── students/
   │   ├── __init__.py
   │   ├── admin.py
   │   ├── apps.py
   │   ├── leaderboard_utils.py
   │   ├── models.py
   │   ├── summarizer_utils.py
   │   ├── tests.py
   │   ├── urls.py
   │   ├── utils.py
   │   └── views.py
   ├── teachers/
   │   ├── __init__.py
   │   ├── admin.py
   │   ├── apps.py
   │   ├── forms.py
   │   ├── models.py
   │   ├── quiz_generator.py
   │   ├── reports_generator.py
   │   ├── reports_views.py
   │   ├── tests.py
   │   ├── urls.py
   │   └── views.py
   ├── student_campus/
   │   ├── __init__.py
   │   ├── asgi.py
   │   ├── settings.py
   │   ├── urls.py
   │   └── wsgi.py
   ├── templates/
   │   ├── base.html
   │   ├── authentication/
   │   │   ├── loading.html
   │   │   ├── login.html
   │   │   └── signup.html
   │   ├── students/
   │   │   └── ...
   │   └── teachers/
   │       └── ...
   ├── media/
   │   ├── chat_files/
   │   │   ├── 2025/
   │   │   └── notes/
   │   ├── notes/
   │   │   └── 2025/
   │   └── proctoring/
   │       └── 2025/
   ├── faiss_indices/
   │   ├── faiss_index/
   │   ├── faiss_index_<hash>/
   │   │   └── index.faiss
   │   └── ...
   └── tests/
      ├── files.py
      └── test_proctoring.py
```

## Configuration Notes
- `API_KEY` is required; without it quiz generation, PDF chat, summarization, and Knowledge Bot will fail.
- Wikipedia credentials are optional but recommended to provide better headers for the Knowledge Bot requests.
- Static/media paths default to local storage; adjust in `student_campus/settings.py` for production (add `STATIC_ROOT`, configure media/CDN as needed).
- Logging for Django server requests is set to `ERROR` only (see `student_campus/settings.py`).

## Operating the App
- Run tests: `python manage.py test`
- Rebuild a PDF's FAISS index: delete its `faiss_indices/faiss_index_<pdf_hash>/` directory; the next PDF chat request will recreate it.
- Large PDFs: text is split into 15k-character chunks with 2k overlap for retrieval (see `students/utils.py`).
- File locations: course notes under `media/notes/YYYY/MM/DD/`, chat uploads under `media/chat_files/YYYY/MM/DD/`, proctoring assets under `media/proctoring/`.

## Troubleshooting
- **AI features returning errors**: ensure `API_KEY` is set and valid; verify outbound network access.
- **PDF chat returns empty/irrelevant answers**: delete the corresponding `faiss_indices/faiss_index_<pdf_hash>/` folder to force re-indexing; confirm the PDF has extractable text (scans need Tesseract OCR).
- **OCR/`pdf2image` errors**: confirm Poppler and Tesseract are installed and on PATH; restart the shell after install.
- **Static files in production**: set `DEBUG=False`, define `ALLOWED_HOSTS`, add `STATIC_ROOT`, and run `python manage.py collectstatic`.

## License & Contributions
- MIT License. Contributions via pull requests are welcome.

## Support
Open an issue on GitHub if you run into problems or have feature requests.
