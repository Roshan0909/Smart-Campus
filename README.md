# Smart Campus

A comprehensive Django-based learning management system with AI-powered features for student and teacher interactions.

## Project Overview

Smart Campus is a full-featured LMS built with Django that includes:
- Student dashboard and learning management
- Teacher tools for quiz creation and grading
- AI-powered study aids (summarizer, knowledge bot, flashcards)
- Coding arena with problem generation and auto-grading
- Real-time chat between students and teachers
- Exam proctoring with violation detection
- Quiz analytics and reporting

## Technology Stack

- **Backend**: Django 4.x
- **Database**: SQLite/PostgreSQL
- **AI Integration**: Google Generative AI (Gemini)
- **Authentication**: Django built-in
- **File Processing**: PyPDF2, python-docx, python-pptx
- **Code Execution**: Judge0 API integration
- **Reporting**: ReportLab (PDF generation)

## Project Structure

```
Smart-Campus/
├── README.md
└── campus/
   ├── manage.py
   ├── requirements.txt
   ├── db.sqlite3
   ├── .env                  # Create locally (not tracked)
   ├── authentication/
   │   ├── admin.py
   │   ├── apps.py
   │   ├── forms.py
   │   ├── models.py
   │   ├── urls.py
   │   └── views.py
   ├── students/
   │   ├── models.py
   │   ├── urls.py
   │   ├── utils.py
   │   ├── views/
   │   │   ├── dashboard.py
   │   │   ├── chat.py
   │   │   ├── coding.py
   │   │   ├── knowledge_bot.py
   │   │   ├── leaderboard.py
   │   │   ├── leaderboard_utils.py
   │   │   ├── pdf.py
   │   │   ├── practice_quiz.py
   │   │   ├── proctoring.py
   │   │   ├── profile.py
   │   │   ├── quiz.py
   │   │   ├── summarizer.py
   │   │   └── summarizer_utils.py
   │   └── migrations/
   ├── teachers/
   │   ├── admin.py
   │   ├── apps.py
   │   ├── forms.py
   │   ├── models.py
   │   ├── urls.py
   │   ├── views.py
   │   ├── views/             # Feature-specific views if used
   │   └── migrations/
   ├── student_campus/        # Django project settings
   │   ├── settings.py
   │   ├── urls.py
   │   ├── wsgi.py
   │   └── asgi.py
   ├── templates/
   │   ├── base.html
   │   ├── authentication/
   │   ├── students/
   │   │   ├── base_student.html
   │   │   ├── dashboard.html
   │   │   ├── pdf_chat.html
   │   │   ├── quiz.html
   │   │   ├── quiz_report.html
   │   │   ├── practice_quiz.html
   │   │   ├── practice_quiz_history.html
   │   │   ├── take_practice_quiz.html
   │   │   ├── take_quiz.html
   │   │   ├── knowledge_bot.html
   │   │   ├── leaderboard.html
   │   │   ├── coding/
   │   │   └── chat*.html
   │   └── teachers/
   │       ├── base_teacher.html
   │       ├── dashboard.html
   │       ├── create_quiz.html
   │       ├── quiz_reports.html
   │       ├── quiz_analytics.html
   │       ├── subject_detail.html
   │       ├── proctoring_report.html
   │       ├── coding/
   │       └── chat*.html
   ├── media/
   │   ├── chat_files/2025/
   │   ├── notes/2025/
   │   └── proctoring/2025/
   ├── faiss_indices/
   │   ├── faiss_index/
   │   └── faiss_index_*/index.faiss
   ├── tests/
   │   ├── app.py
   │   ├── files.py
   │   └── test_proctoring.py
   ├── utils/
   │   └── ai_fallback.py
   └── venv/                 # Local virtualenv (not committed)
```
```

## Module Organization

### Students Module (14 view files)
- **dashboard.py** - Student dashboard, subject listings
- **pdf.py** - PDF interaction, flashcard generation
- **quiz.py** - Quiz taking and reporting
- **chat.py** - Direct messaging with teachers
- **coding.py** - Coding problem solving
- **summarizer.py** - Text summarization
- **knowledge_bot.py** - AI-powered Q&A assistant
- **leaderboard.py** - Student rankings
- **practice_quiz.py** - Student-created quizzes
- **proctoring.py** - Exam monitoring snapshots
- **profile.py** - Student profile management
- **coding.py** (utility functions)
- **summarizer_utils.py** - Text extraction utilities
- **leaderboard_utils.py** - Ranking calculations

### Teachers Module (11 view files)
- **dashboard.py** - Teacher dashboard, subject management
- **quiz.py** - Quiz creation and management
- **reports.py** - Quiz analytics and reporting
- **chat.py** - Messaging with students
- **coding.py** - Coding problem creation and assignment
- **proctoring.py** - Exam proctoring reports
- **quiz_generator.py** - AI quiz generation from documents
- **reports_generator.py** - Report generation utilities
- **code_executor.py** - Code execution engine
- **coding_problem_generator.py** - AI problem generation
- **__init__.py** - Module re-exports

## Key Features

### For Students
- 📚 **Document Learning**: Upload and chat with PDFs, Word docs, PowerPoint
- 🤖 **AI Study Tools**: Automatic summarization, flashcard generation
- 💬 **Knowledge Bot**: AI-powered Q&A assistant
- 🏆 **Leaderboard**: Competition and progress tracking
- 🧠 **Practice Quizzes**: Create and take custom quizzes
- 💻 **Coding Arena**: Solve programming problems with auto-grading
- 📊 **Quiz Reports**: Detailed performance analytics
- 🔍 **Exam Proctoring**: Secure exam environment with violation detection

### For Teachers
- 📝 **Quiz Management**: Create, generate, and analyze quizzes
- 🤖 **AI Assistance**: Auto-generate quizzes from documents
- 💻 **Coding Problems**: Create and assign coding problems
- 🧪 **Code Execution**: Judge0 integration for secure execution
- 📊 **Advanced Reports**: Student performance analytics
- 📈 **Question Analytics**: Identify difficult questions
- 👥 **Student Progress**: Track individual student improvement
- 💬 **Direct Messaging**: Communicate with students
- 👀 **Exam Proctoring**: Monitor and review exam violations

## Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/Roshan0909/Smart-Campus.git
   cd Smart-Campus
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   # Windows (PowerShell)
   .\venv\Scripts\activate
   # macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r campus/requirements.txt
   ```

4. **Configure environment variables**
   - Copy `.env.example` to `.env`
   - Set `GEMINI_API_KEY` for AI features
   - Configure database settings

5. **Run migrations**
   ```bash
   cd campus
   python manage.py migrate
   ```

6. **Create superuser**
   ```bash
   python manage.py createsuperuser
   ```

7. **Run development server**
   ```bash
   python manage.py runserver
   ```

## Configuration

### Environment Variables
Create a `.env` in the `campus` folder (same level as `manage.py`). Example:

```
DEBUG=True
SECRET_KEY=your_secret_key

# Database (SQLite default)
DATABASE_URL=sqlite:///db.sqlite3

# AI / External Services
GEMINI_API_KEY=your_api_key_here
JUDGE0_BASE_URL=https://judge0-ce.p.rapidapi.com
JUDGE0_API_KEY=your_rapidapi_key
```

### Key Settings
- **AI Model**: Google Generative AI (Gemini)
- **Code Execution**: Judge0 Community Edition API
- **File Upload**: Supports PDF, DOCX, PPTX
- **Session Timeout**: Configurable in settings.py

## API Integration

### Gemini API
Used for:
- Quiz generation from documents
- Problem statement generation
- Text summarization
- AI-powered Q&A responses

### Judge0 API
Used for:
- Secure code execution
- Multi-language support (Python, Java, C++, JavaScript, C)
- Execution result parsing
- Configure `JUDGE0_BASE_URL` and `JUDGE0_API_KEY` in `.env`

## Data & Models

### Core Models
- **User** - Extended authentication model
- **Subject** - Course/subject management
- **PDFNote** - Document storage
- **ChatMessage** - Direct messaging

### Quiz Models
- **Quiz** - Quiz configuration
- **Question** - Quiz questions
- **QuizAttempt** - Student quiz attempts
- **ProctoringSnapshot** - Exam violation records

### Coding Models
- **CodingProblem** - Programming problems
- **CodingAssignment** - Problem assignments
- **TestCase** - Problem test cases
- **CodingSubmission** - Student code submissions

## Development

### Code Organization
- Views are organized by feature (dashboard, quiz, chat, etc.)
- Utilities are co-located with their dependent views
- Models are consolidated in single files
- URL routing is clean and hierarchical

### Adding New Features
1. Create new view module in appropriate `views/` folder
2. Add route in `urls.py`
3. Add function export in `views/__init__.py`
4. Create templates if needed in `templates/`

### Testing
From the `campus` directory:

```bash
python manage.py test
pytest -q  # if pytest is installed
```

Key tests:
- `tests/test_proctoring.py`: validates image snapshot handling
- `tests/files.py`: helpers for file-based tests

## Performance & Storage

- Database query optimization with `select_related()` and `prefetch_related()`
- FAISS indices for vector search (knowledge bot)
- Media directories are date-namespaced (e.g., `media/proctoring/2025/`)
- Large FAISS indices are stored in `faiss_indices/*/index.faiss`
- Caching for frequently accessed data
- Lazy loading of PDF content

## Security

- CSRF protection on all forms
- SQL injection protection via ORM
- Password hashing (Django default)
- Rate limiting for API endpoints
- Secure file upload handling
- Session-based authentication

## Troubleshooting

### Common Issues

**Import Errors**
- Ensure all view functions are exported in `__init__.py`
- Check relative import paths (use `..` for parent packages)

**Database Errors**
- Run migrations: `python manage.py migrate`
- Check database connection in settings

**Static/Media Files Not Appearing**
- Ensure `MEDIA_ROOT` and `MEDIA_URL` are set in `student_campus/settings.py`
- During development, use `django.conf.urls.static` for media serving

**API Integration Issues**
- Verify API keys in environment variables
- Check Judge0 API availability
- Ensure Gemini API is enabled

**FAISS Index Errors**
- Verify the presence of `faiss_indices/*/index.faiss`
- Ensure compatible FAISS version in `requirements.txt`

---

**Last Updated**: December 2025 (reflects current workspace structure)
