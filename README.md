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
campus/
├── authentication/          # User authentication & authorization
├── students/               # Student module
│   ├── models.py          # Student-related models
│   ├── urls.py            # 34 student routes
│   ├── views/             # 14 view modules (organized by feature)
│   │   ├── dashboard.py       (Dashboard & subjects)
│   │   ├── pdf.py            (PDF chat & flashcards)
│   │   ├── quiz.py           (Quiz management)
│   │   ├── chat.py           (Messaging)
│   │   ├── coding.py         (Coding arena)
│   │   ├── summarizer.py     (Text summarization)
│   │   ├── knowledge_bot.py  (AI learning assistant)
│   │   ├── leaderboard.py    (Rankings)
│   │   ├── practice_quiz.py  (Practice quizzes)
│   │   ├── proctoring.py     (Exam monitoring)
│   │   ├── profile.py        (User profile)
│   │   └── utilities (summarizer_utils.py, leaderboard_utils.py)
│   └── migrations/
│
├── teachers/              # Teacher module
│   ├── models.py          # All models (quiz, coding, etc.)
│   ├── urls.py            # 37 teacher routes
│   ├── views/             # 11 view modules (organized by feature)
│   │   ├── dashboard.py       (Dashboard & subjects)
│   │   ├── quiz.py           (Quiz management)
│   │   ├── reports.py        (Quiz analytics & reports)
│   │   ├── chat.py           (Messaging)
│   │   ├── coding.py         (Coding problem management)
│   │   ├── proctoring.py     (Exam monitoring)
│   │   └── utilities (quiz_generator.py, reports_generator.py, etc.)
│   └── migrations/
│
├── student_campus/        # Django project settings
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
│
├── templates/             # HTML templates
├── media/                 # User uploads (PDFs, images, etc.)
├── faiss_indices/         # Vector search indices
├── tests/                 # Test files
├── manage.py              # Django management
└── requirements.txt       # Python dependencies
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

## Routes Overview

### Student Routes (34 total)
```
/student/dashboard/                    - Dashboard
/student/coding/*                      - Coding arena (6 routes)
/student/subject/<id>/                 - Subject detail
/student/pdf-chat/<id>/                - PDF interaction
/student/quiz/*                        - Quiz management (4 routes)
/student/chat/*                        - Messaging (2 routes)
/student/knowledge-bot/*               - AI assistant (2 routes)
/student/leaderboard/                  - Rankings
/student/practice-quiz/*               - Practice quizzes (5 routes)
```

### Teacher Routes (37 total)
```
/teacher/dashboard/                    - Dashboard
/teacher/coding/*                      - Coding management (10 routes)
/teacher/subject/*                     - Subject management (5 routes)
/teacher/quiz/*                        - Quiz management (5 routes)
/teacher/chat/*                        - Messaging (4 routes)
/teacher/proctoring/<id>/              - Exam monitoring
/teacher/reports/*                     - Analytics (6 routes)
```

## Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd smart_campus
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   - Copy `.env.example` to `.env`
   - Set `GEMINI_API_KEY` for AI features
   - Configure database settings

5. **Run migrations**
   ```bash
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
```
GEMINI_API_KEY=your_api_key_here
DEBUG=True
DATABASE_URL=sqlite:///db.sqlite3
SECRET_KEY=your_secret_key
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

## Database Models

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
```bash
python manage.py test
```

## Performance Optimization

- Database query optimization with `select_related()` and `prefetch_related()`
- FAISS indices for vector search (knowledge base)
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

**API Integration Issues**
- Verify API keys in environment variables
- Check Judge0 API availability
- Ensure Gemini API is enabled

## Support

For issues and feature requests, contact the development team or submit an issue on the repository.

## License

Proprietary - All rights reserved

## Contributors

Smart Campus Development Team

---

**Last Updated**: December 2025
