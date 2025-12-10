from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Q
from teachers.models import Subject, PDFNote, ChatMessage
from .models import ChatHistory
from .utils import get_answer_for_pdf
from authentication.models import User
import json
import requests


@login_required
def student_dashboard(request):
    if not request.user.is_student():
        return HttpResponseForbidden("You don't have permission to access this page.")
    
    subjects = Subject.objects.all()
    return render(request, 'students/dashboard.html', {'subjects': subjects})

@login_required
def student_subject_detail(request, subject_id):
    if not request.user.is_student():
        return HttpResponseForbidden("You don't have permission to access this page.")
    
    subject = get_object_or_404(Subject, id=subject_id)
    notes = subject.notes.all()
    
    return render(request, 'students/subject_detail.html', {'subject': subject, 'notes': notes})

@login_required
def magnify_learning(request):
    if not request.user.is_student():
        return HttpResponseForbidden("You don't have permission to access this page.")
    
    subjects = Subject.objects.all().prefetch_related('notes')
    return render(request, 'students/magnify_learning.html', {'subjects': subjects})

@login_required
def pdf_chat(request, pdf_id):
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
        
        # Create a temporary PDFNote for the uploaded file
        # We'll create it under a special "Personal Uploads" subject
        from teachers.models import Subject
        
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
def summarizer(request):
    if not request.user.is_student():
        return HttpResponseForbidden("You don't have permission to access this page.")
    
    return render(request, 'students/summarizer.html')

@login_required
@require_POST
def generate_summary(request):
    if not request.user.is_student():
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    try:
        from .summarizer_utils import summarize_text, extract_text_from_pdf_file, extract_text_from_docx_file, extract_text_from_pptx_file
        
        text = request.POST.get('text', '').strip()
        summary_type = request.POST.get('summary_type', 'concise')
        
        # Check if file was uploaded
        if request.FILES:
            uploaded_file = request.FILES.get('file')
            
            if uploaded_file:
                file_extension = uploaded_file.name.split('.')[-1].lower()
                
                if file_extension == 'pdf':
                    text = extract_text_from_pdf_file(uploaded_file)
                    if not text:
                        return JsonResponse({'error': 'Could not extract text from PDF'}, status=400)
                elif file_extension in ['docx', 'doc']:
                    text = extract_text_from_docx_file(uploaded_file)
                    if not text:
                        return JsonResponse({'error': 'Could not extract text from Word document'}, status=400)
                elif file_extension in ['pptx', 'ppt']:
                    text = extract_text_from_pptx_file(uploaded_file)
                    if not text:
                        return JsonResponse({'error': 'Could not extract text from PowerPoint'}, status=400)
                else:
                    return JsonResponse({'error': 'Unsupported file format. Please upload PDF, Word, or PowerPoint file.'}, status=400)
        
        if not text or len(text.strip()) < 50:
            return JsonResponse({'error': 'Text is too short. Please provide at least 50 characters.'}, status=400)
        
        # Limit text length
        if len(text) > 50000:
            text = text[:50000]
        
        # Generate summary
        summary = summarize_text(text, summary_type)
        
        return JsonResponse({
            'success': True,
            'summary': summary,
            'original_length': len(text),
            'summary_type': summary_type
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def quiz(request):
    if not request.user.is_student():
        return HttpResponseForbidden("You don't have permission to access this page.")
    
    from teachers.models import Quiz
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
    if not request.user.is_student():
        return HttpResponseForbidden("You don't have permission to access this page.")
    
    from teachers.models import Quiz, QuizAttempt
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
    if not request.user.is_student():
        return HttpResponseForbidden("You don't have permission to access this page.")
    
    from teachers.models import QuizAttempt
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
    
    return render(request, 'students/quiz_report.html', {
        'attempt': attempt,
        'quiz': quiz,
        'question_results': question_results,
        'percentage': round(percentage, 2),
        'total_questions': total_questions,
        'correct_count': correct_count,
        'wrong_count': wrong_count,
        'wrong_percentage': round(wrong_percentage, 2)
    })

@login_required
@require_POST
def submit_quiz(request, quiz_id):
    if not request.user.is_student():
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    try:
        from teachers.models import Quiz, QuizAttempt, Question
        from django.utils import timezone
        
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
            # This shouldn't happen, but just in case
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

@login_required
def student_chat(request):
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

@login_required
def knowledge_bot(request):
    """General knowledge chatbot using Wikipedia API and Gemini AI"""
    if not request.user.is_student():
        return HttpResponseForbidden("You don't have permission to access this page.")
    
    from .models import KnowledgeBotHistory
    
    # Get chat history for current student
    chat_history = KnowledgeBotHistory.objects.filter(student=request.user).order_by('created_at')
    
    return render(request, 'students/knowledge_bot.html', {'chat_history': chat_history})

@login_required
def knowledge_bot_ask(request):
    """Handle knowledge bot questions"""
    if not request.user.is_student():
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=400)
    
    try:
        from .models import KnowledgeBotHistory
        
        data = json.loads(request.body)
        question = data.get('question', '').strip()
        
        if not question:
            return JsonResponse({'success': False, 'error': 'Question cannot be empty'}, status=400)
        
        # Get recent chat history for context
        recent_history = KnowledgeBotHistory.objects.filter(
            student=request.user
        ).order_by('-created_at')[:5]
        
        history_context = ""
        for hist in reversed(recent_history):
            history_context += f"Previous Q: {hist.question}\nPrevious A: {hist.answer[:200]}...\n\n"
        
        # Search Wikipedia for relevant information
        wiki_context = search_wikipedia(question)
        
        # Check if we got any results
        if not wiki_context.get('context'):
            # Try a simplified search with just key words
            words = question.lower().replace('what is', '').replace('who is', '').replace('where is', '').replace('when is', '').replace('how', '').replace('?', '').strip()
            wiki_context = search_wikipedia(words)
        
        # Generate answer using Gemini AI
        answer = generate_knowledge_answer(question, wiki_context, history_context)
        
        # Save to history
        history_entry = KnowledgeBotHistory.objects.create(
            student=request.user,
            question=question,
            answer=answer,
            sources=wiki_context.get('sources', [])
        )
        
        return JsonResponse({
            'success': True,
            'answer': answer,
            'sources': wiki_context.get('sources', []),
            'timestamp': history_entry.created_at.strftime('%Y-%m-%d %H:%M:%S')
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

def search_wikipedia(query):
    """Search Wikipedia for relevant information using proper API"""
    try:
        import os
        from dotenv import load_dotenv
        import google.generativeai as genai
        
        # Load .env from the campus directory
        env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
        load_dotenv(env_path)
        
        # Use Gemini AI to extract the main search topic from the question
        api_key = os.getenv('API_KEY')
        if not api_key:
            raise ValueError(f"API_KEY not found in .env file at: {env_path}")
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        topic_prompt = f"""Extract the main topic/concept that should be searched on Wikipedia from this question.
Return ONLY the search term(s) that would find the most relevant Wikipedia article.

Examples:
"What is photosynthesis?" → "photosynthesis"
"Who was Albert Einstein?" → "Albert Einstein"
"Define mitosis" → "mitosis"
"Tell me about the pyramids" → "pyramids"
"History of the internet" → "internet history"
"Explain gravity" → "gravity"
"What is quantum physics?" → "quantum physics"

Question: "{query}"
Search term:"""
        
        try:
            topic_response = model.generate_content(topic_prompt)
            search_query = topic_response.text.strip().strip('"\'').lower()
        except:
            # Fallback to original query if AI fails
            search_query = query
        
        # Get credentials from environment
        client_id = os.getenv('WIKIPEDIA_CLIENT_ID')
        client_secret = os.getenv('WIKIPEDIA_CLIENT_SECRET')
        
        # Use Wikipedia API with proper headers
        search_url = "https://en.wikipedia.org/w/api.php"
        
        headers = {
            'User-Agent': 'StudentCampusApp/1.0 (Educational Purpose)'
        }
        
        # Search for relevant articles
        search_params = {
            'action': 'query',
            'format': 'json',
            'list': 'search',
            'srsearch': search_query,
            'srlimit': 5,
            'srprop': 'snippet'
        }
        
        search_response = requests.get(search_url, params=search_params, headers=headers, timeout=10)
        search_data = search_response.json()
        
        context = ""
        sources = []
        
        if 'query' in search_data and 'search' in search_data['query']:
            results = search_data['query']['search']
            
            if not results:
                return {'context': '', 'sources': []}
            
            # Get the first result's full content
            first_result = results[0]
            title = first_result['title']
            page_id = first_result['pageid']
            
            # Get full page content (not just intro)
            content_params = {
                'action': 'query',
                'format': 'json',
                'pageids': page_id,
                'prop': 'extracts',
                'explaintext': True,
                'exsectionformat': 'plain'
            }
            
            content_response = requests.get(search_url, params=content_params, headers=headers, timeout=10)
            content_data = content_response.json()
            
            if 'query' in content_data and 'pages' in content_data['query']:
                page_content = content_data['query']['pages'][str(page_id)].get('extract', '')
                if page_content:
                    # Get first 3000 characters for comprehensive answer
                    context = f"{title}\n\n{page_content[:3000]}"
                    if len(page_content) > 3000:
                        context += "..."
                    
                    sources.append({
                        'title': title,
                        'url': f"https://en.wikipedia.org/?curid={page_id}"
                    })
                    
                    # Add one more related article if available
                    if len(results) > 1:
                        second_result = results[1]
                        second_title = second_result['title']
                        second_page_id = second_result['pageid']
                        
                        content_params['pageids'] = second_page_id
                        content_response = requests.get(search_url, params=content_params, headers=headers, timeout=10)
                        content_data = content_response.json()
                        
                        if 'query' in content_data and 'pages' in content_data['query']:
                            second_content = content_data['query']['pages'][str(second_page_id)].get('extract', '')
                            if second_content:
                                context += f"\n\nRelated: {second_title}\n\n{second_content[:1000]}"
                                sources.append({
                                    'title': second_title,
                                    'url': f"https://en.wikipedia.org/?curid={second_page_id}"
                                })
        
        return {'context': context, 'sources': sources}
        
    except Exception as e:
        return {'context': '', 'sources': []}

def generate_knowledge_answer(question, wiki_context, history_context=""):
    """Format answer using Gemini AI with Wikipedia content"""
    try:
        import os
        from dotenv import load_dotenv
        import google.generativeai as genai
        
        # Load .env from the campus directory
        env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
        load_dotenv(env_path)
        
        context = wiki_context.get('context', '').strip()
        
        if context and len(context) > 50:
            # Use Gemini AI to format and improve the answer
            api_key = os.getenv('API_KEY')
            if not api_key:
                raise ValueError(f"API_KEY not found in .env file at: {env_path}")
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.0-flash-exp')
            
            prompt = f"""You are a knowledgeable educational assistant providing definitions, history, and informational content from Wikipedia.

Your role is to provide:
- Definitions and explanations of terms and concepts
- Historical information and background
- Biographical information about people
- General informational content

You should NOT provide:
- Step-by-step procedures or instructions
- Causes or reasons (just define the topic)
- Process explanations or "how to" guides

Student's Question: {question}

{f"Recent Conversation Context:\n{history_context}\n" if history_context else ""}Wikipedia Information:
{context}

Instructions:
1. Provide definitions, explanations, and informational content
2. Focus on WHAT something is, WHO someone was, and HISTORICAL context
3. If asked about causes, processes, or "how to" - politely explain you provide definitions and information only
4. Use clear structure with bullet points for key facts
5. Make it educational and conversational
6. Format with proper paragraphs (double line breaks)
7. Include interesting facts and context where helpful
8. Keep answers focused on defining and explaining the topic

Format properly with clear paragraphs and structure.

Provide the answer:"""
            
            response = model.generate_content(prompt)
            answer = response.text.strip()
            
            return answer
        else:
            return ("I couldn't find relevant information on Wikipedia for your question. "
                   "Please try:\n\n"
                   "• Using simpler keywords\n"
                   "• Checking your spelling\n"
                   "• Asking about a different topic\n\n"
                   "Examples: 'photosynthesis', 'Albert Einstein', 'solar system', 'Python programming'")
        
    except Exception as e:
        # Fallback to Wikipedia content if Gemini fails
        context = wiki_context.get('context', '').strip()
        if context and len(context) > 50:
            return context
        return f"I apologize, but I encountered an error: {str(e)}"

@login_required
def leaderboard(request):
    """Display creative leaderboard"""
    if not request.user.is_student():
        return HttpResponseForbidden("You don't have permission to access this page.")
    
    from .leaderboard_utils import get_leaderboard_data
    
    # Get leaderboard data
    leaderboard_data = get_leaderboard_data()
    
    # Find current student's data
    current_student_data = None
    for entry in leaderboard_data:
        if entry['student'].id == request.user.id:
            current_student_data = entry
            break
    
    return render(request, 'students/leaderboard.html', {
        'leaderboard': leaderboard_data,
        'current_student_data': current_student_data,
        'total_students': len(leaderboard_data)
    })

@login_required
@require_POST
def save_proctoring_snapshot(request, attempt_id):
    """Save proctoring snapshot with violation details"""
    print(f"📸 Proctoring snapshot request received for attempt {attempt_id}")
    print(f"User: {request.user}, Method: {request.method}")
    
    if not request.user.is_student():
        print("❌ Permission denied - user is not a student")
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    try:
        from teachers.models import QuizAttempt, ProctoringSnapshot
        from django.core.files.base import ContentFile
        import base64
        
        # Get the quiz attempt
        attempt = get_object_or_404(QuizAttempt, id=attempt_id, student=request.user)
        print(f"✓ Found attempt: {attempt.id} for quiz: {attempt.quiz.title}")
        
        # Parse the request data
        data = json.loads(request.body)
        image_data = data.get('image')  # Base64 image
        violation_type = data.get('violation_type')
        person_count = data.get('person_count', 0)
        phone_count = data.get('phone_count', 0)
        
        print(f"📊 Violation data: type={violation_type}, persons={person_count}, phones={phone_count}")
        
        if not image_data or not violation_type:
            print("❌ Missing required data")
            return JsonResponse({'error': 'Missing required data'}, status=400)
        
        # Decode base64 image
        format, imgstr = image_data.split(';base64,')
        ext = format.split('/')[-1]
        image_file = ContentFile(base64.b64decode(imgstr), name=f'snapshot_{attempt.id}_{violation_type}.{ext}')
        
        print(f"📷 Creating snapshot in database...")
        # Save snapshot
        snapshot = ProctoringSnapshot.objects.create(
            attempt=attempt,
            image=image_file,
            violation_type=violation_type,
            person_count=person_count,
            phone_count=phone_count
        )
        print(f"✓ Snapshot saved with ID: {snapshot.id}, image path: {snapshot.image.url}")
        
        # Update attempt violation log
        violation_log = {
            'type': violation_type,
            'timestamp': snapshot.timestamp.isoformat(),
            'person_count': person_count,
            'phone_count': phone_count
        }
        
        attempt.proctoring_violations.append(violation_log)
        attempt.save()
        
        print(f"✅ Successfully saved proctoring snapshot for attempt {attempt.id}")
        print(f"Total violations for this attempt: {len(attempt.proctoring_violations)}")
        
        return JsonResponse({
            'success': True,
            'snapshot_id': snapshot.id,
            'message': 'Snapshot saved successfully'
        })
        
    except Exception as e:
        print(f"❌ ERROR saving snapshot: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def practice_quiz(request):
    """Practice quiz main page where students can create their own quizzes"""
    if not request.user.is_student():
        return HttpResponseForbidden("You don't have permission to access this page.")
    
    from .models import PracticeQuiz
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
def generate_practice_quiz(request):
    """Generate a practice quiz from uploaded file or course material"""
    if not request.user.is_student():
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    try:
        from .models import PracticeQuiz
        from teachers.quiz_generator import extract_text_from_file, generate_quiz_questions
        
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
                # Save the file temporarily
                from django.core.files.storage import default_storage
                from django.core.files.base import ContentFile
                import tempfile
                import os as os_module
                
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
    
    from .models import PracticeQuiz
    
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
        from .models import PracticeQuiz, PracticeQuizAttempt
        
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
    
    from .models import PracticeQuizAttempt
    
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

        from teachers.quiz_generator import extract_text_from_file
        import os
        from dotenv import load_dotenv
        import google.generativeai as genai

        # Load .env from the campus directory
        env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
        load_dotenv(env_path)

        # Extract text from the note file
        file_text = extract_text_from_file(note.pdf_file.path)
        if not file_text or len(file_text.strip()) < 100:
            return JsonResponse({'error': 'Could not extract sufficient text from the document'}, status=400)

        # Trim text for token safety
        max_chars = 15000
        if len(file_text) > max_chars:
            file_text = file_text[:max_chars]

        api_key = os.getenv('API_KEY')
        if not api_key:
            raise ValueError(f"API_KEY not found in .env file at: {env_path}")
        genai.configure(api_key=api_key)

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

        # Try preferred model with graceful fallback on rate limits/quota
        model_preferences = [
            os.getenv('GENAI_FLASHCARDS_MODEL'),
            'gemini-2.5-flash',
            'gemini-1.5-flash'
        ]
        model_candidates = [m for m in model_preferences if m]

        response = None
        last_error = None
        for idx, model_name in enumerate(model_candidates):
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt)
                break
            except Exception as ai_err:
                last_error = ai_err
                err_text = str(ai_err).lower()
                is_quota = ('quota' in err_text) or ('rate limit' in err_text) or ('429' in err_text)
                is_last = idx == len(model_candidates) - 1
                if is_quota and not is_last:
                    # Try next model if available
                    continue
                status_code = 429 if is_quota else 500
                return JsonResponse({'error': f'AI generation failed ({model_name}): {ai_err}'}, status=status_code)

        if response is None:
            return JsonResponse({'error': f'AI generation failed: {last_error}'}, status=500)

        # Safely extract text from Gemini response
        response_text = ''
        if hasattr(response, 'text') and response.text:
            response_text = response.text.strip()
        elif getattr(response, 'candidates', None):
            for cand in response.candidates:
                if getattr(cand, 'content', None) and getattr(cand.content, 'parts', None):
                    for part in cand.content.parts:
                        if getattr(part, 'text', None):
                            response_text += part.text
            response_text = response_text.strip()

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

        import json
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

@login_required
def student_profile(request):
    """View and edit student profile"""
    if not request.user.is_student():
        return HttpResponseForbidden("You don't have permission to access this page.")
    
    # Get or create student profile
    from .models import StudentProfile
    profile, created = StudentProfile.objects.get_or_create(student=request.user)
    
    if request.method == 'POST':
        # Update profile
        profile.full_name = request.POST.get('full_name', '')
        profile.class_name = request.POST.get('class_name', '')
        profile.roll_number = request.POST.get('roll_number', '')
        profile.registration_number = request.POST.get('registration_number', '')
        profile.department = request.POST.get('department', '')
        profile.phone_number = request.POST.get('phone_number', '')
        profile.email_id = request.POST.get('email_id', '')
        profile.address = request.POST.get('address', '')
        
        profile.save()
        
        # Update user email if provided
        if request.POST.get('email_id'):
            request.user.email = request.POST.get('email_id')
            request.user.save()
        
        return JsonResponse({'success': True, 'message': 'Profile updated successfully'})
    
    return render(request, 'students/profile.html', {'profile': profile})

