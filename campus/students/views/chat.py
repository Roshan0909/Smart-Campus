"""
Student Chat Views
Handles: Direct messaging with teachers
"""
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.db.models import Q
from authentication.models import User
from teachers.models import PDFNote, ChatMessage


@login_required
def student_chat(request):
    """Display list of teachers for chat"""
    if not request.user.is_student():
        return HttpResponseForbidden("You don't have permission to access this page.")
    
    # Get all teachers
    teachers = User.objects.filter(role='teacher').order_by('username')
    
    # Get recent conversations with last message
    conversations = []
    for teacher in teachers:
        last_message = ChatMessage.objects.filter(
            Q(sender=request.user, receiver=teacher) | Q(sender=teacher, receiver=request.user)
        ).order_by('-created_at').first()
        
        unread_count = ChatMessage.objects.filter(
            sender=teacher, receiver=request.user, is_read=False
        ).count()
        
        conversations.append({
            'user': teacher,
            'last_message': last_message,
            'unread_count': unread_count
        })
    
    # Sort by last message time (most recent first)
    conversations.sort(key=lambda x: x['last_message'].created_at if x['last_message'] else x['user'].date_joined, reverse=True)
    
    return render(request, 'students/chat.html', {
        'conversations': conversations
    })


@login_required
def student_chat_with(request, user_id):
    """Display chat conversation with a specific teacher"""
    if not request.user.is_student():
        return HttpResponseForbidden("You don't have permission to access this page.")
    
    other_user = get_object_or_404(User, id=user_id, role='teacher')
    
    # Get all messages between student and teacher
    messages_list = ChatMessage.objects.filter(
        Q(sender=request.user, receiver=other_user) | Q(sender=other_user, receiver=request.user)
    ).select_related('attached_note', 'attached_note__subject').order_by('created_at')
    
    # Mark messages as read
    ChatMessage.objects.filter(sender=other_user, receiver=request.user, is_read=False).update(is_read=True)
    
    # Get all available notes (teacher's notes or subject notes)
    available_notes = PDFNote.objects.filter(subject__teacher=other_user).select_related('subject')
    
    return render(request, 'students/chat_conversation.html', {
        'other_user': other_user,
        'messages': messages_list,
        'available_notes': available_notes
    })
