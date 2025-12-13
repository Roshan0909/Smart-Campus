"""
Teacher Chat Views
Handles: Direct messaging with students, file sharing, note attachments
"""
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Q
import json
from authentication.models import User
from teachers.models import PDFNote, ChatMessage


@login_required
def teacher_chat(request):
    """Display list of students for chat"""
    if not request.user.is_teacher():
        return HttpResponseForbidden("You don't have permission to access this page.")
    
    # Get all students
    students = User.objects.filter(role='student').order_by('username')
    
    # Get recent conversations with last message
    conversations = []
    for student in students:
        last_message = ChatMessage.objects.filter(
            Q(sender=request.user, receiver=student) | Q(sender=student, receiver=request.user)
        ).order_by('-created_at').first()
        
        unread_count = ChatMessage.objects.filter(
            sender=student, receiver=request.user, is_read=False
        ).count()
        
        conversations.append({
            'user': student,
            'last_message': last_message,
            'unread_count': unread_count
        })
    
    # Sort by last message time (most recent first)
    conversations.sort(key=lambda x: x['last_message'].created_at if x['last_message'] else x['user'].date_joined, reverse=True)
    
    return render(request, 'teachers/chat.html', {
        'conversations': conversations
    })


@login_required
def teacher_chat_with(request, user_id):
    """Display chat conversation with a specific student"""
    if not request.user.is_teacher():
        return HttpResponseForbidden("You don't have permission to access this page.")
    
    other_user = get_object_or_404(User, id=user_id, role='student')
    
    # Get all messages between teacher and student
    messages_list = ChatMessage.objects.filter(
        Q(sender=request.user, receiver=other_user) | Q(sender=other_user, receiver=request.user)
    ).select_related('attached_note', 'attached_note__subject').order_by('created_at')
    
    # Mark messages as read
    ChatMessage.objects.filter(sender=other_user, receiver=request.user, is_read=False).update(is_read=True)
    
    # Get all notes from teacher's subjects
    available_notes = PDFNote.objects.filter(subject__teacher=request.user).select_related('subject')
    
    return render(request, 'teachers/chat_conversation.html', {
        'other_user': other_user,
        'messages': messages_list,
        'available_notes': available_notes
    })


@login_required
@require_POST
def send_message(request, user_id):
    """Send a message to a student"""
    if request.method == 'POST':
        try:
            other_user = get_object_or_404(User, id=user_id)
            
            # Check if it's a file upload or JSON data
            if request.FILES:
                message_text = request.POST.get('message', '').strip()
                file = request.FILES.get('file')
                note_id = request.POST.get('note_id')
            else:
                data = json.loads(request.body)
                message_text = data.get('message', '').strip()
                file = None
                note_id = data.get('note_id')
            
            # Validate that there's either a message or a file
            if not message_text and not file and not note_id:
                return JsonResponse({'error': 'Message, file, or note attachment is required'}, status=400)
            
            # Get attached note if provided
            attached_note = None
            if note_id:
                attached_note = PDFNote.objects.filter(id=note_id).first()
            
            message = ChatMessage.objects.create(
                sender=request.user,
                receiver=other_user,
                message=message_text,
                file=file,
                attached_note=attached_note
            )
            
            response_data = {
                'id': message.id,
                'text': message.message,
                'created_at': message.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'sender': message.sender.username,
                'file_url': message.file.url if message.file else None,
                'is_image': message.is_image(),
                'file_name': message.file.name.split('/')[-1] if message.file else None,
                'attached_note': {
                    'id': message.attached_note.id,
                    'title': message.attached_note.title,
                    'subject': message.attached_note.subject.name
                } if message.attached_note else None
            }
            
            return JsonResponse({
                'success': True,
                'message': response_data
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Invalid request'}, status=400)


@login_required
def get_messages(request, user_id):
    """Retrieve messages with a specific student"""
    try:
        other_user = get_object_or_404(User, id=user_id)
        
        # Get messages since a certain time if provided
        since_id = request.GET.get('since_id')
        
        messages_query = ChatMessage.objects.filter(
            Q(sender=request.user, receiver=other_user) | Q(sender=other_user, receiver=request.user)
        )
        
        if since_id:
            messages_query = messages_query.filter(id__gt=since_id)
        
        messages_list = messages_query.order_by('created_at')
        
        # Mark new messages as read
        ChatMessage.objects.filter(sender=other_user, receiver=request.user, is_read=False).update(is_read=True)
        
        messages_data = [{
            'id': msg.id,
            'text': msg.message,
            'created_at': msg.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'sender': msg.sender.username,
            'sender_id': msg.sender.id,
            'is_own': msg.sender.id == request.user.id,
            'file_url': msg.file.url if msg.file else None,
            'is_image': msg.is_image(),
            'file_name': msg.file.name.split('/')[-1] if msg.file else None,
            'attached_note': {
                'id': msg.attached_note.id,
                'title': msg.attached_note.title,
                'subject': msg.attached_note.subject.name,
                'pdf_url': msg.attached_note.pdf_file.url
            } if msg.attached_note else None
        } for msg in messages_list]
        
        return JsonResponse({
            'success': True,
            'messages': messages_data
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
