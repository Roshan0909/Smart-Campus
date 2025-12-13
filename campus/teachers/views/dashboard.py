"""
Teacher Dashboard & Subject Management Views
Handles: Dashboard, subject creation, PDF uploads, document management
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.contrib import messages
from teachers.models import Subject, PDFNote, Quiz
from teachers.forms import SubjectForm, PDFNoteForm


@login_required
def teacher_dashboard(request):
    """Display teacher dashboard with subjects and recent quizzes"""
    if not request.user.is_teacher():
        return HttpResponseForbidden("You don't have permission to access this page.")
    
    subjects = Subject.objects.filter(teacher=request.user)
    quizzes = Quiz.objects.filter(created_by=request.user).order_by('-created_at')[:10]
    return render(request, 'teachers/dashboard.html', {'subjects': subjects, 'quizzes': quizzes})


@login_required
def create_subject(request):
    """Create a new subject"""
    if not request.user.is_teacher():
        return HttpResponseForbidden("You don't have permission to access this page.")
    
    if request.method == 'POST':
        form = SubjectForm(request.POST)
        if form.is_valid():
            subject = form.save(commit=False)
            subject.teacher = request.user
            subject.save()
            messages.success(request, f'Subject "{subject.name}" created successfully!')
            return redirect('teacher_dashboard')
    else:
        form = SubjectForm()
    
    return render(request, 'teachers/create_subject.html', {'form': form})


@login_required
def subject_detail(request, subject_id):
    """Display detailed view of a subject"""
    if not request.user.is_teacher():
        return HttpResponseForbidden("You don't have permission to access this page.")
    
    subject = get_object_or_404(Subject, id=subject_id, teacher=request.user)
    notes = subject.notes.all()
    
    return render(request, 'teachers/subject_detail.html', {'subject': subject, 'notes': notes})


@login_required
def upload_pdf(request, subject_id):
    """Upload a PDF document to a subject"""
    if not request.user.is_teacher():
        return HttpResponseForbidden("You don't have permission to access this page.")
    
    subject = get_object_or_404(Subject, id=subject_id, teacher=request.user)
    
    if request.method == 'POST':
        form = PDFNoteForm(request.POST, request.FILES)
        if form.is_valid():
            pdf_note = form.save(commit=False)
            pdf_note.subject = subject
            pdf_note.uploaded_by = request.user
            pdf_note.save()
            messages.success(request, f'Document "{pdf_note.title}" uploaded successfully!')
            return redirect('teacher_subject_detail', subject_id=subject.id)
    else:
        form = PDFNoteForm()
    
    return render(request, 'teachers/upload_pdf.html', {'form': form, 'subject': subject})


@login_required
def delete_subject(request, subject_id):
    """Delete a subject"""
    if not request.user.is_teacher():
        return HttpResponseForbidden("You don't have permission to access this page.")
    
    subject = get_object_or_404(Subject, id=subject_id, teacher=request.user)
    
    if request.method == 'POST':
        subject_name = subject.name
        subject.delete()
        messages.success(request, f'Subject "{subject_name}" deleted successfully!')
        return redirect('teacher_dashboard')
    
    return redirect('teacher_subject_detail', subject_id=subject_id)


@login_required
def delete_document(request, document_id):
    """Delete a PDF document"""
    if not request.user.is_teacher():
        return HttpResponseForbidden("You don't have permission to access this page.")
    
    document = get_object_or_404(PDFNote, id=document_id, uploaded_by=request.user)
    subject_id = document.subject.id
    
    if request.method == 'POST':
        document_title = document.title
        # Delete the file from storage
        if document.pdf_file:
            document.pdf_file.delete()
        document.delete()
        messages.success(request, f'Document "{document_title}" deleted successfully!')
        return redirect('teacher_subject_detail', subject_id=subject_id)
    
    return redirect('teacher_subject_detail', subject_id=subject_id)
