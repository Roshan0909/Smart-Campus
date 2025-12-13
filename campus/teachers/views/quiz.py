"""
Teacher Quiz Management Views
Handles: Quiz creation, generation, editing, analytics, and attempt management
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
from django.contrib import messages
from django.db.models import Q, Max, Count, Case, When
from django.db import models
from django.utils import timezone
from datetime import datetime
import json
from ..models import Subject, PDFNote, Quiz, Question, QuizAttempt, ProctoringSnapshot


@login_required
def create_quiz(request):
    """Display form to create a new quiz"""
    if not request.user.is_teacher():
        return HttpResponseForbidden("You don't have permission to access this page.")
    
    subjects = Subject.objects.filter(teacher=request.user).prefetch_related('notes')
    return render(request, 'teachers/create_quiz.html', {'subjects': subjects})


@login_required
def generate_quiz(request, pdf_id):
    """Generate quiz questions from a PDF document"""
    if not request.user.is_teacher():
        return HttpResponseForbidden("You don't have permission to access this page.")
    
    pdf_note = get_object_or_404(PDFNote, id=pdf_id)
    
    if request.method == 'POST':
        try:
            from .quiz_generator import generate_quiz_from_pdf
            
            num_questions = int(request.POST.get('num_questions', 10))
            duration = int(request.POST.get('duration', 30))
            topics = request.POST.get('topics', '').strip()
            difficulty = request.POST.get('difficulty', 'medium')
            
            # Validate input
            if num_questions < 1 or num_questions > 100:
                messages.error(request, 'Number of questions must be between 1 and 100.')
                return render(request, 'teachers/generate_quiz.html', {
                    'pdf_note': pdf_note,
                    'subject': pdf_note.subject
                })
            
            if duration < 5 or duration > 240:
                messages.error(request, 'Duration must be between 5 and 240 minutes.')
                return render(request, 'teachers/generate_quiz.html', {
                    'pdf_note': pdf_note,
                    'subject': pdf_note.subject
                })
            
            # Generate questions from PDF
            questions_data, error = generate_quiz_from_pdf(pdf_note.pdf_file.path, num_questions, topics, difficulty)
            
            if error:
                messages.error(request, f'Error generating quiz: {error}')
                return render(request, 'teachers/generate_quiz.html', {
                    'pdf_note': pdf_note,
                    'subject': pdf_note.subject
                })
            
            if not questions_data:
                messages.error(request, 'Could not generate quiz questions. Please ensure the document has sufficient content.')
                return render(request, 'teachers/generate_quiz.html', {
                    'pdf_note': pdf_note,
                    'subject': pdf_note.subject
                })
            
            # Create quiz
            quiz_description = f"Auto-generated quiz from {pdf_note.title}"
            if topics:
                quiz_description += f" (Topics: {topics})"
            quiz_description += f" | Difficulty: {difficulty.capitalize()}"
            
            quiz = Quiz.objects.create(
                title=f"Quiz: {pdf_note.title}",
                subject=pdf_note.subject,
                pdf_note=pdf_note,
                description=quiz_description,
                duration=duration,
                num_questions=num_questions,
                topics=topics,
                difficulty=difficulty,
                created_by=request.user,
                is_active=True
            )
            
            # Create questions
            for idx, q_data in enumerate(questions_data, start=1):
                Question.objects.create(
                    quiz=quiz,
                    text=q_data['question'],
                    question_type='multiple_choice',
                    options=q_data['options'],
                    correct_answer=str(q_data['correct_answer']),
                    points=1,
                    order=idx
                )
            
            messages.success(request, f'Quiz "{quiz.title}" created successfully with {len(questions_data)} questions!')
            return redirect('quiz_detail', quiz_id=quiz.id)
            
        except Exception as e:
            import traceback
            error_msg = str(e)
            print(f"Quiz generation error: {error_msg}")
            print(traceback.format_exc())
            messages.error(request, f'Error generating quiz: {error_msg}')
            return render(request, 'teachers/generate_quiz.html', {
                'pdf_note': pdf_note,
                'subject': pdf_note.subject
            })
    
    return render(request, 'teachers/generate_quiz.html', {
        'pdf_note': pdf_note,
        'subject': pdf_note.subject
    })


@login_required
def quiz_detail(request, quiz_id):
    """Display and edit quiz details"""
    if not request.user.is_teacher():
        return HttpResponseForbidden("You don't have permission to access this page.")
    
    quiz = get_object_or_404(Quiz, id=quiz_id, created_by=request.user)
    questions = quiz.questions.all().order_by('order')
    
    if request.method == 'POST':
        # Handle quiz metadata update
        quiz.title = request.POST.get('title', quiz.title)
        quiz.description = request.POST.get('description', quiz.description)
        quiz.duration = int(request.POST.get('duration', quiz.duration))
        
        deadline_str = request.POST.get('deadline')
        if deadline_str:
            quiz.deadline = timezone.make_aware(datetime.fromisoformat(deadline_str))
        
        quiz.save()
        
        # Handle question updates
        for question in questions:
            q_text = request.POST.get(f'question_{question.id}')
            q_answer = request.POST.get(f'answer_{question.id}')
            
            if q_text:
                question.text = q_text
            if q_answer:
                question.correct_answer = q_answer
            
            # Update options for multiple choice
            if question.question_type == 'multiple_choice':
                options = []
                for i in range(4):
                    option = request.POST.get(f'option_{question.id}_{i}')
                    if option:
                        options.append(option)
                question.options = options
            
            question.save()
        
        messages.success(request, 'Quiz updated successfully!')
        return redirect('quiz_detail', quiz_id=quiz.id)
    
    # Get completed attempts with proctoring data
    attempts = QuizAttempt.objects.filter(
        quiz=quiz,
        completed_at__isnull=False
    ).select_related('student').prefetch_related('snapshots').order_by('-completed_at')
    
    # Add violation count to each attempt
    total_violations = 0
    for attempt in attempts:
        attempt.violation_count = attempt.snapshots.count()
        total_violations += attempt.violation_count
        if quiz.questions.count() > 0:
            attempt.percentage = round((attempt.score / quiz.questions.count()) * 100, 2)
        else:
            attempt.percentage = 0
    
    return render(request, 'teachers/quiz_detail.html', {
        'quiz': quiz,
        'questions': questions,
        'attempts': attempts,
        'total_violations': total_violations
    })


@login_required
def toggle_quiz_active(request, quiz_id):
    """Toggle quiz active status"""
    if not request.user.is_teacher():
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    if request.method == 'POST':
        quiz = get_object_or_404(Quiz, id=quiz_id, created_by=request.user)
        quiz.is_active = not quiz.is_active
        quiz.save()
        
        return JsonResponse({
            'success': True,
            'is_active': quiz.is_active,
            'message': f'Quiz {"activated" if quiz.is_active else "deactivated"} successfully!'
        })
    
    return JsonResponse({'error': 'Invalid request'}, status=400)


@login_required
def quiz_analytics(request):
    """Display comprehensive quiz analytics"""
    if not request.user.is_teacher():
        return HttpResponseForbidden("You don't have permission to access this page.")
    
    quizzes = Quiz.objects.filter(created_by=request.user).prefetch_related('attempts', 'questions', 'attempts__student')
    
    # Calculate statistics for each quiz
    quiz_stats = []
    total_attempts_all = 0
    unique_students_set = set()
    all_percentages = []
    
    for quiz in quizzes:
        attempts = quiz.attempts.filter(completed_at__isnull=False)
        total_attempts = attempts.count()
        total_attempts_all += total_attempts
        
        # Get unique students for this quiz
        students_in_quiz = set(attempt.student.id for attempt in attempts)
        unique_students_set.update(students_in_quiz)
        
        if total_attempts > 0:
            scores = [a.score for a in attempts]
            avg_score = sum(scores) / total_attempts
            highest_score = max(scores)
            lowest_score = min(scores)
            
            if quiz.questions.count() > 0:
                avg_percentage = (avg_score / quiz.questions.count()) * 100
                all_percentages.append(avg_percentage)
            else:
                avg_percentage = 0
        else:
            avg_score = 0
            avg_percentage = 0
            highest_score = 0
            lowest_score = 0
        
        quiz_stats.append({
            'quiz': quiz,
            'total_attempts': total_attempts,
            'avg_score': round(avg_score, 2),
            'avg_percentage': round(avg_percentage, 2),
            'total_questions': quiz.questions.count(),
            'highest_score': highest_score,
            'lowest_score': lowest_score,
            'unique_students': len(students_in_quiz)
        })
    
    # Calculate overall statistics
    overall_avg = round(sum(all_percentages) / len(all_percentages), 2) if all_percentages else 0
    
    # Prepare proctoring data for all quizzes
    proctoring_data = []
    for quiz in quizzes:
        # Get all attempts with violations for this quiz
        attempts_with_violations = quiz.attempts.prefetch_related(
            'snapshots', 'student'
        ).annotate(
            snapshot_count=Count('snapshots')
        ).filter(snapshot_count__gt=0).order_by(
            # Order by completed status (completed first), then by date (most recent first)
            models.Case(
                models.When(completed_at__isnull=False, then=0),
                models.When(completed_at__isnull=True, then=1),
                output_field=models.IntegerField(),
            ),
            '-completed_at',
            '-started_at'
        )
        
        if attempts_with_violations.exists():
            # Calculate total violations for this quiz
            total_violations = sum(attempt.snapshots.count() for attempt in attempts_with_violations)
            
            proctoring_data.append({
                'quiz': quiz,
                'total_violations': total_violations,
                'attempts_with_violations': attempts_with_violations
            })
    
    return render(request, 'teachers/quiz_analytics.html', {
        'quiz_stats': quiz_stats,
        'total_attempts': total_attempts_all,
        'unique_students': len(unique_students_set),
        'overall_avg': overall_avg,
        'proctoring_data': proctoring_data
    })
