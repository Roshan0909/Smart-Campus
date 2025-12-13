"""
Student Practice Quiz Views
Handles: Student-generated practice quizzes, taking quizzes, and tracking history
"""
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
from django.views.decorators.http import require_POST
import json
import tempfile
import os as os_module
from teachers.models import PDFNote
from teachers.views.quiz_generator import extract_text_from_file, generate_quiz_questions


@login_required
def practice_quiz(request):
    """Practice quiz main page where students can create their own quizzes"""
    if not request.user.is_student():
        return HttpResponseForbidden("You don't have permission to access this page.")
    
    from students.models import PracticeQuiz
    from teachers.models import Subject
    
    # Get recent practice quizzes
    recent_quizzes = PracticeQuiz.objects.filter(student=request.user).prefetch_related('attempts')[:10]
    
    # Calculate total attempts across all quizzes
    total_attempts = 0
    
    # Add attempt statistics to each quiz
    for quiz in recent_quizzes:
        quiz.attempt_count = quiz.attempts.count()
        total_attempts += quiz.attempt_count
        if quiz.attempt_count > 0:
            latest_attempt = quiz.attempts.first()
            quiz.latest_score = latest_attempt.score
            quiz.latest_percentage = round((latest_attempt.score / latest_attempt.total_questions * 100), 2)
        else:
            quiz.latest_score = None
            quiz.latest_percentage = None
    
    # Get all subjects with their notes for selection
    subjects = Subject.objects.all().prefetch_related('notes')
    
    return render(request, 'students/practice_quiz.html', {
        'recent_quizzes': recent_quizzes,
        'subjects': subjects,
        'total_attempts': total_attempts
    })


@login_required
@require_POST
def generate_practice_quiz(request):
    """Generate a practice quiz from uploaded file or course material"""
    if not request.user.is_student():
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    try:
        from students.models import PracticeQuiz
        
        # Handle both POST data and FILES
        if request.method == 'POST':
            difficulty = request.POST.get('difficulty', 'medium')
            num_questions = int(request.POST.get('num_questions', 5))
            topics = request.POST.get('topics', '').strip()
            pdf_note_id = request.POST.get('pdf_note_id')
            uploaded_file = request.FILES.get('file')
            
            if num_questions < 3 or num_questions > 20:
                return JsonResponse({'error': 'Number of questions must be between 3 and 20'}, status=400)
            
            # Determine file source
            file_text = None
            title = None
            pdf_note = None
            saved_file = None
            
            if pdf_note_id:
                # Using existing course material
                pdf_note = get_object_or_404(PDFNote, id=pdf_note_id)
                file_text = extract_text_from_file(pdf_note.pdf_file.path)
                title = f"Practice: {pdf_note.title}"
            elif uploaded_file:
                # Using uploaded file
                # Create a temporary file
                file_ext = uploaded_file.name.split('.')[-1].lower()
                temp_path = os_module.path.join(tempfile.gettempdir(), f"practice_{request.user.id}_{uploaded_file.name}")
                
                with open(temp_path, 'wb+') as destination:
                    for chunk in uploaded_file.chunks():
                        destination.write(chunk)
                
                file_text = extract_text_from_file(temp_path)
                title = f"Practice: {uploaded_file.name.replace('.' + file_ext, '')}"
                
                # Clean up temp file
                try:
                    os_module.remove(temp_path)
                except:
                    pass
                
                # Save file for future reference
                saved_file = uploaded_file
            else:
                return JsonResponse({'error': 'Please select a course file or upload your own file'}, status=400)
            
            if not file_text or len(file_text) < 100:
                return JsonResponse({'error': 'Could not extract sufficient text from file'}, status=500)
            
            # Generate questions using AI (same as teacher's quiz generator)
            questions_data = generate_quiz_questions(file_text, num_questions, topics, difficulty)
            
            if not questions_data:
                return JsonResponse({'error': 'Could not generate questions from file content'}, status=500)
            
            # Create practice quiz
            practice_quiz = PracticeQuiz.objects.create(
                student=request.user,
                title=title,
                pdf_note=pdf_note,
                uploaded_file=saved_file,
                topic=topics if topics else "General",
                difficulty=difficulty,
                num_questions=len(questions_data),
                questions_data=questions_data
            )
            
            return JsonResponse({
                'success': True,
                'quiz_id': practice_quiz.id,
                'num_questions': len(questions_data),
                'message': f'Practice quiz created with {len(questions_data)} questions!'
            })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def take_practice_quiz(request, quiz_id):
    """Take a practice quiz"""
    if not request.user.is_student():
        return HttpResponseForbidden("You don't have permission to access this page.")
    
    from students.models import PracticeQuiz
    
    practice_quiz = get_object_or_404(PracticeQuiz, id=quiz_id, student=request.user)
    
    return render(request, 'students/take_practice_quiz.html', {
        'quiz': practice_quiz,
        'questions': practice_quiz.questions_data
    })


@login_required
@require_POST
def submit_practice_quiz(request, quiz_id):
    """Submit a practice quiz attempt"""
    if not request.user.is_student():
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    try:
        from students.models import PracticeQuiz, PracticeQuizAttempt
        
        practice_quiz = get_object_or_404(PracticeQuiz, id=quiz_id, student=request.user)
        data = json.loads(request.body)
        answers = data.get('answers', {})
        
        # Calculate score
        score = 0
        total_questions = len(practice_quiz.questions_data)
        results = []
        
        for idx, question in enumerate(practice_quiz.questions_data):
            question_id = str(idx)
            student_answer = answers.get(question_id)
            correct_answer = question['correct_answer']
            
            is_correct = int(student_answer) == int(correct_answer) if student_answer is not None else False
            if is_correct:
                score += 1
            
            results.append({
                'question': question['question'],
                'options': question['options'],
                'student_answer': int(student_answer) if student_answer is not None else None,
                'correct_answer': correct_answer,
                'is_correct': is_correct,
                'explanation': question.get('explanation', '')
            })
        
        # Save attempt
        attempt = PracticeQuizAttempt.objects.create(
            practice_quiz=practice_quiz,
            student=request.user,
            score=score,
            total_questions=total_questions,
            answers=answers
        )
        
        percentage = round((score / total_questions * 100), 2) if total_questions > 0 else 0
        
        return JsonResponse({
            'success': True,
            'score': score,
            'total': total_questions,
            'percentage': percentage,
            'results': results,
            'attempt_id': attempt.id
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def practice_quiz_history(request):
    """View practice quiz history"""
    if not request.user.is_student():
        return HttpResponseForbidden("You don't have permission to access this page.")
    
    from students.models import PracticeQuizAttempt
    
    attempts = PracticeQuizAttempt.objects.filter(student=request.user).select_related('practice_quiz').order_by('-completed_at')
    
    # Calculate statistics
    total_attempts = attempts.count()
    if total_attempts > 0:
        total_score = sum([a.score for a in attempts])
        total_questions = sum([a.total_questions for a in attempts])
        overall_percentage = round((total_score / total_questions * 100), 2) if total_questions > 0 else 0
    else:
        overall_percentage = 0
    
    return render(request, 'students/practice_quiz_history.html', {
        'attempts': attempts[:50],  # Show last 50 attempts
        'total_attempts': total_attempts,
        'overall_percentage': overall_percentage
    })
