"""
Teachers Views Module
Imports all view functions for backward compatibility with URLs
"""
from .dashboard import (
    teacher_dashboard,
    create_subject,
    subject_detail,
    upload_pdf,
    delete_subject,
    delete_document,
)
from .quiz import (
    create_quiz,
    generate_quiz,
    quiz_detail,
    toggle_quiz_active,
    quiz_analytics,
)
from .chat import (
    teacher_chat,
    teacher_chat_with,
    send_message,
    get_messages,
)
from .proctoring import (
    proctoring_report,
)

# Import view modules for backward compatibility
from . import coding
from . import reports

__all__ = [
    # Dashboard
    'teacher_dashboard',
    'create_subject',
    'subject_detail',
    'upload_pdf',
    'delete_subject',
    'delete_document',
    # Quiz
    'create_quiz',
    'generate_quiz',
    'quiz_detail',
    'toggle_quiz_active',
    'quiz_analytics',
    # Chat
    'teacher_chat',
    'teacher_chat_with',
    'send_message',
    'get_messages',
    # Proctoring
    'proctoring_report',
    # Coding and Reports modules
    'coding',
    'reports',
]
