from django.contrib import admin
from .models import Subject, PDFNote, Quiz, Question, QuizAttempt
from .models_coding import CodingProblem, CodingAssignment, TestCase, CodingSubmission

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'teacher', 'created_at']
    list_filter = ['teacher', 'created_at']
    search_fields = ['name', 'description']

@admin.register(PDFNote)
class PDFNoteAdmin(admin.ModelAdmin):
    list_display = ['title', 'subject', 'uploaded_by', 'created_at']
    list_filter = ['subject', 'uploaded_by', 'created_at']
    search_fields = ['title']

@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ['title', 'subject', 'created_by', 'duration', 'is_active', 'created_at']
    list_filter = ['subject', 'created_by', 'is_active', 'created_at']
    search_fields = ['title', 'description']

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['quiz', 'question_type', 'text', 'points', 'order']
    list_filter = ['quiz', 'question_type']
    search_fields = ['text']

@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ['quiz', 'student', 'started_at', 'completed_at', 'score', 'total_points']
    list_filter = ['quiz', 'student', 'started_at']
    search_fields = ['student__username', 'quiz__title']

@admin.register(CodingProblem)
class CodingProblemAdmin(admin.ModelAdmin):
    list_display = ['title', 'difficulty', 'topic', 'teacher', 'is_active', 'created_at']
    list_filter = ['difficulty', 'teacher', 'is_active', 'created_at']
    search_fields = ['title', 'description', 'topic']
    readonly_fields = ['created_at']

@admin.register(CodingAssignment)
class CodingAssignmentAdmin(admin.ModelAdmin):
    list_display = ['title', 'problem', 'teacher', 'deadline', 'is_active', 'assigned_date']
    list_filter = ['teacher', 'is_active', 'assigned_date', 'deadline']
    search_fields = ['title', 'problem__title', 'teacher__username']
    readonly_fields = ['assigned_date']

@admin.register(TestCase)
class TestCaseAdmin(admin.ModelAdmin):
    list_display = ['problem', 'is_hidden', 'points']
    list_filter = ['problem', 'is_hidden']
    search_fields = ['problem__title']

@admin.register(CodingSubmission)
class CodingSubmissionAdmin(admin.ModelAdmin):
    list_display = ['student', 'problem', 'status', 'score', 'test_cases_passed', 'submitted_at']
    list_filter = ['student', 'status', 'submitted_at']
    search_fields = ['student__username', 'problem__title']
    readonly_fields = ['submitted_at']
