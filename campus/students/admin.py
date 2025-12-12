from django.contrib import admin
from .models import ChatHistory, KnowledgeBotHistory, PracticeQuiz, PracticeQuizAttempt, StudentProfile

@admin.register(ChatHistory)
class ChatHistoryAdmin(admin.ModelAdmin):
    list_display = ['student', 'pdf_note', 'question', 'created_at']
    list_filter = ['student', 'pdf_note', 'created_at']
    search_fields = ['question', 'answer', 'student__username']
    readonly_fields = ['created_at']

@admin.register(KnowledgeBotHistory)
class KnowledgeBotHistoryAdmin(admin.ModelAdmin):
    list_display = ['student', 'question', 'created_at']
    list_filter = ['student', 'created_at']
    search_fields = ['question', 'answer', 'student__username']
    readonly_fields = ['created_at', 'sources']

@admin.register(PracticeQuiz)
class PracticeQuizAdmin(admin.ModelAdmin):
    list_display = ['title', 'student', 'difficulty', 'num_questions', 'created_at']
    list_filter = ['student', 'difficulty', 'created_at']
    search_fields = ['title', 'student__username']
    readonly_fields = ['created_at']

@admin.register(PracticeQuizAttempt)
class PracticeQuizAttemptAdmin(admin.ModelAdmin):
    list_display = ['practice_quiz', 'student', 'score', 'total_questions', 'completed_at']
    list_filter = ['student', 'completed_at']
    search_fields = ['student__username', 'practice_quiz__title']
    readonly_fields = ['completed_at']

@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ['student', 'full_name', 'class_name', 'roll_number', 'department']
    list_filter = ['student', 'class_name', 'department']
    search_fields = ['student__username', 'full_name', 'roll_number', 'registration_number']
    readonly_fields = ['created_at', 'updated_at']
