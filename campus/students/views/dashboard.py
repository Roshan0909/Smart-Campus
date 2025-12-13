"""
Student Dashboard & Subject Views
Handles: Dashboard, subject browsing, and learning magnification
"""
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from teachers.models import Subject


@login_required
def student_dashboard(request):
    """Display student dashboard with all subjects"""
    if not request.user.is_student():
        return HttpResponseForbidden("You don't have permission to access this page.")
    
    subjects = Subject.objects.all()
    return render(request, 'students/dashboard.html', {'subjects': subjects})


@login_required
def student_subject_detail(request, subject_id):
    """Display detailed view of a specific subject with its notes"""
    if not request.user.is_student():
        return HttpResponseForbidden("You don't have permission to access this page.")
    
    subject = get_object_or_404(Subject, id=subject_id)
    notes = subject.notes.all()
    
    return render(request, 'students/subject_detail.html', {'subject': subject, 'notes': notes})


@login_required
def magnify_learning(request):
    """Display magnified learning view with all subjects and their notes"""
    if not request.user.is_student():
        return HttpResponseForbidden("You don't have permission to access this page.")
    
    subjects = Subject.objects.all().prefetch_related('notes')
    return render(request, 'students/magnify_learning.html', {'subjects': subjects})
