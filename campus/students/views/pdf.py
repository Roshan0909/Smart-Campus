"""
Student PDF Chat & Document Views
Handles: PDF interactions, asking questions, uploading documents
"""
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
from django.views.decorators.http import require_POST
import json
from teachers.models import Subject, PDFNote
from students.models import ChatHistory
from students.utils import get_answer_for_pdf
from django.shortcuts import render


@login_required
def pdf_chat(request, pdf_id):
    """Display PDF chat interface for a specific document"""
    if not request.user.is_student():
        return HttpResponseForbidden("You don't have permission to access this page.")
    
    pdf_note = get_object_or_404(PDFNote, id=pdf_id)
    chat_history = ChatHistory.objects.filter(student=request.user, pdf_note=pdf_note)
    
    return render(request, 'students/pdf_chat.html', {
        'pdf_note': pdf_note,
        'chat_history': chat_history
    })


@login_required
@require_POST
def ask_question(request, pdf_id):
    """Ask a question about a PDF document"""
    if not request.user.is_student():
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    try:
        pdf_note = get_object_or_404(PDFNote, id=pdf_id)
        data = json.loads(request.body)
        question = data.get('question', '').strip()
        
        if not question:
            return JsonResponse({'error': 'Question is required'}, status=400)
        
        # Get previous chat history for context
        previous_chats = ChatHistory.objects.filter(
            student=request.user, 
            pdf_note=pdf_note
        ).order_by('-created_at')[:5]
        
        # Build chat history string
        history_text = ""
        for chat in reversed(previous_chats):
            history_text += f"Q: {chat.question}\nA: {chat.answer}\n\n"
        
        # Get PDF file path
        pdf_path = pdf_note.pdf_file.path
        
        # Get answer using the utility function
        answer = get_answer_for_pdf(pdf_path, question, history_text)
        
        # Save to chat history
        chat = ChatHistory.objects.create(
            student=request.user,
            pdf_note=pdf_note,
            question=question,
            answer=answer
        )
        
        return JsonResponse({
            'success': True,
            'answer': answer,
            'question': question,
            'timestamp': chat.created_at.strftime('%Y-%m-%d %H:%M:%S')
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_POST
def upload_and_chat(request):
    """Upload a PDF file and create chat session"""
    if not request.user.is_student():
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    try:
        pdf_file = request.FILES.get('pdf_file')
        
        if not pdf_file:
            return JsonResponse({'error': 'No file uploaded'}, status=400)
        
        if not pdf_file.name.endswith('.pdf'):
            return JsonResponse({'error': 'Only PDF files are allowed'}, status=400)
        
        # Check file size (200MB limit)
        if pdf_file.size > 200 * 1024 * 1024:
            return JsonResponse({'error': 'File size exceeds 200MB limit'}, status=400)
        
        # Try to get or create a personal subject for this student
        personal_subject, created = Subject.objects.get_or_create(
            name=f"Personal Uploads - {request.user.username}",
            teacher=request.user,
            defaults={'description': 'Files uploaded for personal learning'}
        )
        
        # Create the PDFNote
        pdf_note = PDFNote.objects.create(
            subject=personal_subject,
            title=pdf_file.name.replace('.pdf', ''),
            pdf_file=pdf_file,
            uploaded_by=request.user
        )
        
        return JsonResponse({
            'success': True,
            'redirect_url': f'/student/pdf-chat/{pdf_note.id}/',
            'message': 'File uploaded successfully'
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def flashcards(request, pdf_id):
    """Flashcards page for a specific PDF note"""
    if not request.user.is_student():
        return HttpResponseForbidden("You don't have permission to access this page.")

    note = get_object_or_404(PDFNote, id=pdf_id)

    return render(request, 'students/flashcards.html', {
        'note': note,
    })


@login_required
@require_POST
def generate_flashcards(request, pdf_id):
    """Generate flashcards from a PDF/Doc/PPT using Gemini"""
    if not request.user.is_student():
        return JsonResponse({'error': 'Permission denied'}, status=403)

    try:
        note = get_object_or_404(PDFNote, id=pdf_id)
        num_cards = int(request.POST.get('num_cards', 10))
        num_cards = max(3, min(num_cards, 30))

        from teachers.views.quiz_generator import extract_text_from_file
        import os
        from dotenv import load_dotenv
        
        # Add campus directory to path for ai_fallback import
        import sys
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        from utils.ai_fallback import generate_content

        # Load .env from the campus directory
        env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
        load_dotenv(env_path)

        # Extract text from the note file
        file_text = extract_text_from_file(note.pdf_file.path)
        if not file_text or len(file_text.strip()) < 100:
            return JsonResponse({'error': 'Could not extract sufficient text from the document'}, status=400)

        # Trim text for token safety
        max_chars = 15000
        if len(file_text) > max_chars:
            file_text = file_text[:max_chars]

        prompt = f"""Create {num_cards} high-quality study flashcards from the provided content.

Return ONLY valid JSON array with this exact shape (no extra text):
[
  {{"front": "Concise question or term", "back": "Clear answer in 1-3 sentences"}}
]

Guidelines:
- Front: short question/term. Back: concise answer, 1-3 sentences max.
- Cover diverse, important concepts from the text.
- Keep language simple and precise.
- No markdown, no numbering, no code fences, JSON only.

CONTENT:
{file_text}
"""

        try:
            response_text = generate_content(prompt).strip()
        except Exception as ai_err:
            return JsonResponse({'error': f'AI generation failed: {ai_err}'}, status=500)

        # Remove markdown fences if present
        if "```" in response_text:
            lines = response_text.split('\n')
            json_lines = []
            in_code = False
            for line in lines:
                if line.strip().startswith('```'):
                    in_code = not in_code
                    continue
                if in_code or line.strip().startswith('['):
                    json_lines.append(line)
            response_text = '\n'.join(json_lines).strip()

        response_text = response_text.replace('```json', '').replace('```', '').strip()

        if not response_text:
            return JsonResponse({'error': 'AI returned empty content for flashcards.'}, status=500)

        try:
            flashcards = json.loads(response_text)
        except json.JSONDecodeError:
            # Fallback: try to extract JSON array between first [ and last ]
            start = response_text.find('[')
            end = response_text.rfind(']')
            if start != -1 and end != -1 and end > start:
                try:
                    flashcards = json.loads(response_text[start:end+1])
                except Exception as e:
                    return JsonResponse({'error': f'Failed to parse AI response: {str(e)}', 'raw': response_text[:500]}, status=500)
            else:
                return JsonResponse({'error': 'Failed to parse AI response (no JSON array found).', 'raw': response_text[:500]}, status=500)

        # Validate structure
        cleaned = []
        if isinstance(flashcards, list):
            for card in flashcards:
                if isinstance(card, dict) and 'front' in card and 'back' in card:
                    cleaned.append({
                        'front': str(card['front']).strip(),
                        'back': str(card['back']).strip(),
                    })

        if not cleaned:
            return JsonResponse({'error': 'Failed to generate valid flashcards'}, status=500)

        return JsonResponse({'success': True, 'flashcards': cleaned[:num_cards]})

    except json.JSONDecodeError as e:
        return JsonResponse({'error': f'Failed to parse AI response: {str(e)}'}, status=500)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
