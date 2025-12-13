"""
Teacher Proctoring Report Views
Handles: Viewing proctoring violations and attempt details
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.contrib import messages
from teachers.models import QuizAttempt, ProctoringSnapshot


@login_required
def proctoring_report(request, attempt_id):
    """View proctoring report for a specific quiz attempt"""
    if not request.user.is_teacher():
        return HttpResponseForbidden("You don't have permission to access this page.")
    
    attempt = get_object_or_404(
        QuizAttempt.select_related('student', 'quiz'),
        id=attempt_id,
        quiz__created_by=request.user
    )
    
    # Get all proctoring snapshots for this attempt
    snapshots = ProctoringSnapshot.objects.filter(attempt=attempt).order_by('timestamp')
    
    # If no violations, redirect back with message
    if not snapshots.exists():
        messages.info(request, 'No proctoring violations detected for this attempt.')
        return redirect('quiz_detail', quiz_id=attempt.quiz.id)
    
    # Organize violations by type
    violations_summary = {
        'no_person': snapshots.filter(violation_type='no_person').count(),
        'multiple_persons': snapshots.filter(violation_type='multiple_persons').count(),
        'phone_detected': snapshots.filter(violation_type='phone_detected').count(),
    }
    
    total_violations = sum(violations_summary.values())
    
    return render(request, 'teachers/proctoring_report.html', {
        'attempt': attempt,
        'snapshots': snapshots,
        'violations_summary': violations_summary,
        'total_violations': total_violations,
    })
