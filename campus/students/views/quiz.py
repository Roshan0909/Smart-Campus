"""
Student Quiz Views
Handles: Quiz browsing, taking quizzes, submitting answers, and viewing reports
"""
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
import json
from teachers.models import Quiz, QuizAttempt, Question


@login_required
def quiz(request):
    """Display list of available quizzes"""
    if not request.user.is_student():
        return HttpResponseForbidden("You don't have permission to access this page.")
    
    quizzes = Quiz.objects.filter(is_active=True).select_related('subject', 'pdf_note').prefetch_related('attempts', 'questions')
    
    # Attach user's attempt and calculate percentage for each quiz
    completed_count = 0
    for quiz_obj in quizzes:
        attempt = quiz_obj.attempts.filter(student=request.user, completed_at__isnull=False).first()
        quiz_obj.user_attempt = attempt
        if attempt:
            completed_count += 1
            total_questions = quiz_obj.questions.count()
            if total_questions > 0:
                quiz_obj.percentage = round((attempt.score / total_questions) * 100, 2)
            else:
                quiz_obj.percentage = 0
        else:
            quiz_obj.percentage = 0
    
    return render(request, 'students/quiz.html', {
        'quizzes': quizzes,
        'completed_count': completed_count
    })


@login_required
def take_quiz(request, quiz_id):
    """Display quiz interface for taking a quiz"""
    if not request.user.is_student():
        return HttpResponseForbidden("You don't have permission to access this page.")
    
    quiz = get_object_or_404(Quiz, id=quiz_id, is_active=True)
    questions = quiz.questions.all()
    
    # Check if already attempted
    existing_attempt = QuizAttempt.objects.filter(student=request.user, quiz=quiz, completed_at__isnull=False).first()
    
    # Create or get current attempt for proctoring
    current_attempt = None
    if not existing_attempt:
        current_attempt, created = QuizAttempt.objects.get_or_create(
            student=request.user,
            quiz=quiz,
            completed_at__isnull=True,
            defaults={'total_points': questions.count()}
        )
    
    return render(request, 'students/take_quiz.html', {
        'quiz': quiz,
        'questions': questions,
        'already_attempted': existing_attempt,
        'attempt_id': current_attempt.id if current_attempt else None
    })


@login_required
def quiz_report(request, attempt_id):
    """Display detailed report of a quiz attempt"""
    if not request.user.is_student():
        return HttpResponseForbidden("You don't have permission to access this page.")
    
    attempt = get_object_or_404(QuizAttempt, id=attempt_id, student=request.user, completed_at__isnull=False)
    
    quiz = attempt.quiz
    questions = quiz.questions.all()
    
    # Build detailed results
    question_results = []
    for question in questions:
        question_id = str(question.id)
        student_answer = attempt.answers.get(question_id)
        is_correct = student_answer == question.correct_answer
        
        result = {
            'question': question,
            'student_answer': student_answer,
            'is_correct': is_correct
        }
        question_results.append(result)
    
    total_questions = quiz.questions.count()
    correct_count = attempt.score
    wrong_count = total_questions - correct_count
    percentage = (attempt.score / total_questions * 100) if total_questions > 0 else 0
    wrong_percentage = (wrong_count / total_questions * 100) if total_questions > 0 else 0
    
    # Calculate risk assessment
    risk_data = attempt.calculate_risk_score()
    
    # Calculate stroke-dasharray for SVG circle (circumference = 2πr, r=50, so circumference ≈ 314)
    risk_stroke = (risk_data['risk_score'] / 100) * 314
    
    return render(request, 'students/quiz_report.html', {
        'attempt': attempt,
        'quiz': quiz,
        'question_results': question_results,
        'percentage': round(percentage, 2),
        'total_questions': total_questions,
        'correct_count': correct_count,
        'wrong_count': wrong_count,
        'wrong_percentage': round(wrong_percentage, 2),
        'risk_data': risk_data,
        'risk_stroke': round(risk_stroke, 2)
    })


@login_required
@require_POST
def submit_quiz(request, quiz_id):
    """Submit quiz answers and calculate score"""
    if not request.user.is_student():
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    try:
        quiz = get_object_or_404(Quiz, id=quiz_id, is_active=True)
        data = json.loads(request.body)
        answers = data.get('answers', {})
        
        # Calculate score and build detailed results
        score = 0
        total_questions = quiz.questions.count()
        correct_answers = {}
        question_details = []
        
        for question in quiz.questions.all():
            question_id = str(question.id)
            student_answer = answers.get(question_id)
            correct_answer = question.correct_answer
            
            is_correct = student_answer == correct_answer
            if is_correct:
                score += 1
                correct_answers[question_id] = True
            else:
                correct_answers[question_id] = False
            
            # Build question detail for report
            question_detail = {
                'id': question.id,
                'text': question.text,
                'student_answer': student_answer,
                'correct_answer': correct_answer,
                'is_correct': is_correct,
                'type': question.question_type
            }
            
            # Add options for multiple choice
            if question.question_type == 'multiple_choice':
                question_detail['options'] = question.options
            
            question_details.append(question_detail)
        
        # Get proctoring counts from request
        tab_switch_count = data.get('tab_switch_count', 0)
        fullscreen_exit_count = data.get('fullscreen_exit_count', 0)
        
        # Update existing attempt or create new one
        attempt, created = QuizAttempt.objects.update_or_create(
            quiz=quiz,
            student=request.user,
            completed_at__isnull=True,
            defaults={
                'completed_at': timezone.now(),
                'score': score,
                'total_points': total_questions,
                'answers': answers,
                'tab_switch_count': tab_switch_count,
                'fullscreen_exit_count': fullscreen_exit_count
            }
        )
        
        # If no in-progress attempt exists, this means we need to create a new completed one
        if not created and attempt.completed_at is None:
            attempt.completed_at = timezone.now()
            attempt.score = score
            attempt.total_points = total_questions
            attempt.answers = answers
            attempt.tab_switch_count = tab_switch_count
            attempt.fullscreen_exit_count = fullscreen_exit_count
            attempt.save()
        
        percentage = (score / total_questions * 100) if total_questions > 0 else 0
        
        return JsonResponse({
            'success': True,
            'score': score,
            'total': total_questions,
            'percentage': round(percentage, 2),
            'correct_answers': correct_answers,
            'question_details': question_details
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
