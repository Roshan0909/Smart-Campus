"""
Views for quiz reports module - separate from main views to avoid collision
"""
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden
from django.views.decorators.http import require_POST
from django.db.models import Q
from ..models import Quiz, QuizAttempt, Subject
from .reports_generator import QuizReportFilter, QuizReportGenerator, QuizAnalytics
from authentication.models import User
from django.utils import timezone
from datetime import timedelta
import csv
from io import StringIO
import json


@login_required
def quiz_reports(request):
    """Main reports page with filters"""
    if not request.user.is_teacher():
        return HttpResponseForbidden("You don't have permission to access this page.")
    
    # Get teacher's quizzes and subjects
    subjects = Subject.objects.filter(teacher=request.user)
    quizzes = Quiz.objects.filter(created_by=request.user)
    students = User.objects.filter(role='student')
    
    # Get initial data
    recent_attempts = QuizAttempt.objects.filter(
        quiz__created_by=request.user
    ).select_related('quiz', 'student').order_by('-completed_at')[:10]
    
    return render(request, 'teachers/quiz_reports.html', {
        'subjects': subjects,
        'quizzes': quizzes,
        'students': students,
        'recent_attempts': recent_attempts,
        'difficulty_choices': [('easy', 'Easy'), ('medium', 'Medium'), ('hard', 'Hard')],
    })


@login_required
@require_POST
def filter_quiz_reports(request):
    """Apply filters and return filtered data"""
    if not request.user.is_teacher():
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    try:
        data = json.loads(request.body)
        
        # Initialize filter
        report_filter = QuizReportFilter(request.user)
        
        # Apply filters
        if data.get('quiz_id'):
            report_filter.set_quiz_filter(data['quiz_id'])
        
        if data.get('subject_id'):
            report_filter.set_subject_filter(data['subject_id'])
        
        if data.get('student_id'):
            report_filter.set_student_filter(data['student_id'])
        
        if data.get('difficulty'):
            report_filter.set_difficulty_filter(data['difficulty'])
        
        # Date range
        if data.get('start_date'):
            start_date = timezone.datetime.fromisoformat(data['start_date'])
            report_filter.set_date_range_filter(start_date, None)
        
        if data.get('end_date'):
            end_date = timezone.datetime.fromisoformat(data['end_date'])
            if data.get('start_date'):
                start_date = timezone.datetime.fromisoformat(data['start_date'])
                report_filter.set_date_range_filter(start_date, end_date)
            else:
                report_filter.set_date_range_filter(None, end_date)
        
        # Score range
        if data.get('min_score') and data.get('min_score') != '':
            try:
                min_score = int(data.get('min_score', 0))
                max_score = int(data.get('max_score', 1000)) if data.get('max_score') and data.get('max_score') != '' else 1000
                report_filter.set_score_range_filter(min_score, max_score)
            except (ValueError, TypeError):
                pass  # Skip if conversion fails
        
        # Search
        if data.get('search'):
            report_filter.set_search_filter(data['search'])
        
        # Get filtered data
        attempts = report_filter.get_attempts()
        stats = report_filter.get_statistics()
        
        # Format attempts for JSON
        attempts_data = []
        for attempt in attempts[:100]:  # Limit to 100 for JSON response
            # Safely calculate percentage - handle None and zero cases
            score = attempt.score if attempt.score else 0
            total = attempt.total_points if attempt.total_points else 0
            if total and total > 0:
                percentage = (score / total * 100)
            else:
                percentage = 0
            
            # Get student name - use full name if available, otherwise username
            student_name = f"{attempt.student.first_name} {attempt.student.last_name}".strip()
            if not student_name:
                student_name = attempt.student.username
            
            # Calculate risk assessment
            risk_data = attempt.calculate_risk_score()
            
            attempts_data.append({
                'id': attempt.id,
                'quiz_title': attempt.quiz.title,
                'student_name': student_name,
                'score': score,
                'total': total,
                'percentage': round(percentage, 2),
                'completed_at': attempt.completed_at.strftime('%Y-%m-%d %H:%M') if attempt.completed_at else 'N/A',
                'status': 'Completed' if attempt.completed_at else 'In Progress',
                'risk_score': risk_data['risk_score'],
                'risk_level': risk_data['risk_level'],
                'risk_color': risk_data['risk_color'],
                'risk_status': risk_data['risk_status'],
                'violation_count': len(attempt.proctoring_violations) if attempt.proctoring_violations else 0,
                'tab_switch_count': attempt.tab_switch_count,
                'fullscreen_exit_count': attempt.fullscreen_exit_count
            })
        
        return JsonResponse({
            'success': True,
            'statistics': stats,
            'attempts': attempts_data,
            'total_records': attempts.count()
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def download_quiz_report_pdf(request):
    """Download filtered data as PDF"""
    if not request.user.is_teacher():
        return HttpResponseForbidden("You don't have permission to access this page.")
    
    try:
        # Get filter parameters from GET request
        report_filter = QuizReportFilter(request.user)
        
        if request.GET.get('quiz_id'):
            report_filter.set_quiz_filter(request.GET['quiz_id'])
        
        if request.GET.get('subject_id'):
            report_filter.set_subject_filter(request.GET['subject_id'])
        
        if request.GET.get('student_id'):
            report_filter.set_student_filter(request.GET['student_id'])
        
        # Date range
        if request.GET.get('start_date') and request.GET.get('end_date'):
            start_date = timezone.datetime.fromisoformat(request.GET['start_date'])
            end_date = timezone.datetime.fromisoformat(request.GET['end_date'])
            report_filter.set_date_range_filter(start_date, end_date)
        
        # Apply risk filter if specified
        risk_filter_value = request.GET.get('risk_filter')
        
        # Generate PDF
        generator = QuizReportGenerator(report_filter, risk_filter=risk_filter_value)
        pdf_buffer, filename = generator.generate_pdf()
        
        # Return PDF response
        response = HttpResponse(pdf_buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
        
    except Exception as e:
        return HttpResponse(f"Error generating PDF: {str(e)}", status=500)


@login_required
def download_quiz_report_excel(request):
    """Download filtered data as Excel-compatible CSV"""
    if not request.user.is_teacher():
        return HttpResponseForbidden("You don't have permission to access this page.")
    
    try:
        report_filter = QuizReportFilter(request.user)
        
        # Filters
        if request.GET.get('quiz_id'):
            report_filter.set_quiz_filter(request.GET['quiz_id'])
        if request.GET.get('subject_id'):
            report_filter.set_subject_filter(request.GET['subject_id'])
        if request.GET.get('student_id'):
            report_filter.set_student_filter(request.GET['student_id'])
        if request.GET.get('start_date'):
            start_date = timezone.datetime.fromisoformat(request.GET['start_date'])
        else:
            start_date = None
        if request.GET.get('end_date'):
            end_date = timezone.datetime.fromisoformat(request.GET['end_date'])
        else:
            end_date = None
        if start_date or end_date:
            report_filter.set_date_range_filter(start_date, end_date)
        if request.GET.get('risk_filter'):
            risk_filter_value = request.GET.get('risk_filter')
        else:
            risk_filter_value = None
        
        # Get attempts
        attempts = list(report_filter.get_attempts())

        # Apply risk filter client-side (same logic as PDF)
        if risk_filter_value:
            filtered_attempts = []
            for attempt in attempts:
                risk_score = attempt.calculate_risk_score()['risk_score']
                if risk_filter_value == 'accept' and risk_score < 25:
                    filtered_attempts.append(attempt)
                elif risk_filter_value == 'review' and 25 <= risk_score < 50:
                    filtered_attempts.append(attempt)
                elif risk_filter_value == 'reject' and risk_score >= 50:
                    filtered_attempts.append(attempt)
            attempts = filtered_attempts

        # Prepare CSV
        buffer = StringIO()
        writer = csv.writer(buffer)
        writer.writerow([
            'Quiz', 'Student', 'Score', 'Total', '%', 'Risk Score', 'Risk Level', 'Risk Status',
            'Violations', 'Tab Switches', 'Fullscreen Exits', 'Completed At', 'Status'
        ])

        for attempt in attempts:
            score = attempt.score or 0
            total = attempt.total_points or 0
            percentage = round((score / total * 100), 2) if total else 0
            student_name = attempt.student.get_full_name().strip() or attempt.student.username
            risk = attempt.calculate_risk_score()
            writer.writerow([
                attempt.quiz.title,
                student_name,
                score,
                total,
                percentage,
                risk['risk_score'],
                risk['risk_level'],
                risk['risk_status'],
                len(attempt.proctoring_violations) if attempt.proctoring_violations else 0,
                attempt.tab_switch_count,
                attempt.fullscreen_exit_count,
                attempt.completed_at.strftime('%Y-%m-%d %H:%M') if attempt.completed_at else 'N/A',
                'Completed' if attempt.completed_at else 'In Progress'
            ])

        # Build response
        response = HttpResponse(buffer.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="quiz_report.csv"'
        return response
    except Exception as e:
        return HttpResponse(f"Error generating Excel: {str(e)}", status=500)


@login_required
def question_performance(request, quiz_id):
    """Get performance metrics for each question"""
    if not request.user.is_teacher():
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    try:
        quiz = get_object_or_404(Quiz, id=quiz_id, created_by=request.user)
        performance_data = QuizAnalytics.get_performance_by_question(quiz_id)
        
        return JsonResponse({
            'success': True,
            'quiz_title': quiz.title,
            'performance': performance_data
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def student_progress(request, student_id):
    """Get student progress across quizzes"""
    if not request.user.is_teacher():
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    try:
        student = get_object_or_404(User, id=student_id, role='student')
        
        # Get quizzes created by teacher
        quiz_ids = Quiz.objects.filter(created_by=request.user).values_list('id', flat=True)
        
        progress_data = QuizAnalytics.get_student_progress(student_id, quiz_ids)
        
        # Get student name - use full name if available, otherwise username
        student_name = f"{student.first_name} {student.last_name}".strip()
        if not student_name:
            student_name = student.username
        
        return JsonResponse({
            'success': True,
            'student_name': student_name,
            'progress': progress_data
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
