"""
Student Summarizer Views
Handles: Text summarization, file extraction, and summary generation
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
from django.views.decorators.http import require_POST


@login_required
def summarizer(request):
    """Display summarizer interface"""
    if not request.user.is_student():
        return HttpResponseForbidden("You don't have permission to access this page.")
    
    return render(request, 'students/summarizer.html')


@login_required
@require_POST
def generate_summary(request):
    """Generate summary from uploaded file or text"""
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
