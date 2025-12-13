"""
Students Views Module
Imports all view functions for backward compatibility with URLs
"""
from .dashboard import (
    student_dashboard,
    student_subject_detail,
    magnify_learning,
)
from .pdf import (
    pdf_chat,
    ask_question,
    upload_and_chat,
    flashcards,
    generate_flashcards,
)
from .summarizer import (
    summarizer,
    generate_summary,
)
from .quiz import (
    quiz,
    take_quiz,
    quiz_report,
    submit_quiz,
)
from .chat import (
    student_chat,
    student_chat_with,
)
from .knowledge_bot import (
    knowledge_bot,
    knowledge_bot_ask,
)
from .leaderboard import (
    leaderboard,
)
from .proctoring import (
    save_proctoring_snapshot,
)
from .practice_quiz import (
    practice_quiz,
    generate_practice_quiz,
    take_practice_quiz,
    submit_practice_quiz,
    practice_quiz_history,
)
from .profile import (
    student_profile,
)
from . import coding

__all__ = [
    # Dashboard
    'student_dashboard',
    'student_subject_detail',
    'magnify_learning',
    # PDF
    'pdf_chat',
    'ask_question',
    'upload_and_chat',
    'flashcards',
    'generate_flashcards',
    # Summarizer
    'summarizer',
    'generate_summary',
    # Quiz
    'quiz',
    'take_quiz',
    'quiz_report',
    'submit_quiz',
    # Chat
    'student_chat',
    'student_chat_with',
    # Knowledge Bot
    'knowledge_bot',
    'knowledge_bot_ask',
    # Leaderboard
    'leaderboard',
    # Proctoring
    'save_proctoring_snapshot',
    # Practice Quiz
    'practice_quiz',
    'generate_practice_quiz',
    'take_practice_quiz',
    'submit_practice_quiz',
    'practice_quiz_history',
    # Profile
    'student_profile',
]
