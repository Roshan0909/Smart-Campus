"""
Student Knowledge Bot Views
Handles: AI-powered question answering using Wikipedia and Gemini
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
from django.views.decorators.http import require_POST
import json
import requests
import os
import sys


@login_required
def knowledge_bot(request):
    """Display knowledge chatbot interface"""
    if not request.user.is_student():
        return HttpResponseForbidden("You don't have permission to access this page.")
    
    from students.models import KnowledgeBotHistory
    
    # Get chat history for current student
    chat_history = KnowledgeBotHistory.objects.filter(student=request.user).order_by('created_at')
    
    return render(request, 'students/knowledge_bot.html', {'chat_history': chat_history})


@login_required
@require_POST
def knowledge_bot_ask(request):
    """Handle knowledge bot questions and generate answers"""
    if not request.user.is_student():
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=400)
    
    try:
        from students.models import KnowledgeBotHistory
        
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
        
        # Generate answer using AI
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
        # Add campus directory to path for ai_fallback import
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        from utils.ai_fallback import generate_content
        
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
            search_query = generate_content(topic_prompt).strip().strip('"\'').lower()
        except:
            # Fallback to original query if AI fails
            search_query = query
        
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
    """Format answer using AI with Wikipedia content"""
    try:
        import os
        from dotenv import load_dotenv
        
        # Add campus directory to path for ai_fallback import
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        from utils.ai_fallback import generate_content
        
        # Load .env from the campus directory
        env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
        load_dotenv(env_path)
        
        context = wiki_context.get('context', '').strip()
        
        if context and len(context) > 50:
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
            
            answer = generate_content(prompt).strip()
            
            return answer
        else:
            return ("I couldn't find relevant information on Wikipedia for your question. "
                   "Please try:\n\n"
                   "• Using simpler keywords\n"
                   "• Checking your spelling\n"
                   "• Asking about a different topic\n\n"
                   "Examples: 'photosynthesis', 'Albert Einstein', 'solar system', 'Python programming'")
        
    except Exception as e:
        # Fallback to Wikipedia content if AI fails
        context = wiki_context.get('context', '').strip()
        if context and len(context) > 50:
            return context
        return f"I apologize, but I encountered an error: {str(e)}"
