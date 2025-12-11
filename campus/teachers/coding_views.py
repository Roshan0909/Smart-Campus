"""
Teacher Code Arena Views
Handles: Problem creation, AI generation, preview, assignment management
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_POST
from django.utils import timezone
from datetime import timedelta
import json
import google.generativeai as genai
from django.conf import settings

from .models_coding import CodingProblem, CodingAssignment, TestCase
from .models import Subject


# ============================================
# PROBLEM LISTING & MANAGEMENT
# ============================================

@login_required
def problems_list(request):
    """List all problems created by teacher"""
    if not request.user.is_teacher():
        return HttpResponseForbidden("Only teachers can access this page.")
    
    problems = CodingProblem.objects.filter(
        teacher=request.user,
        is_active=True
    ).prefetch_related('test_cases', 'assignments')
    
    context = {
        'problems': problems,
        'total_problems': problems.count(),
    }
    return render(request, 'teachers/coding/problems_list.html', context)


@login_required
def create_problem_form(request):
    """Show form to create/generate problem"""
    if not request.user.is_teacher():
        return HttpResponseForbidden("Only teachers can access this page.")
    
    subjects = Subject.objects.filter(teacher=request.user)
    
    context = {
        'subjects': subjects,
        'difficulties': CodingProblem.DIFFICULTY_CHOICES,
        'languages': CodingProblem.LANGUAGE_CHOICES,
    }
    return render(request, 'teachers/coding/create_problem.html', context)


# ============================================
# AI PROBLEM GENERATION
# ============================================

@login_required
@require_POST
def generate_problem_ai(request):
    """Generate problem using Google Gemini AI"""
    if not request.user.is_teacher():
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    
    try:
        data = json.loads(request.body)
        topic = data.get('topic', '').strip()
        difficulty = data.get('difficulty', 'easy')
        language = data.get('language', 'python')
        
        if not topic:
            return JsonResponse({'success': False, 'error': 'Topic is required'})
        
        # Configure Gemini
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Create detailed prompt
        prompt = f"""Generate a {difficulty} level coding problem about {topic} for {language}.

Return ONLY valid JSON with this exact structure:
{{
    "title": "Problem title",
    "description": "Detailed problem description with examples",
    "constraints": "Input constraints and limits",
    "sample_input": "Example input",
    "sample_output": "Example output",
    "explanation": "Explanation of the example",
    "test_cases": [
        {{"input": "test input 1", "output": "expected output 1", "is_hidden": false}},
        {{"input": "test input 2", "output": "expected output 2", "is_hidden": false}},
        {{"input": "test input 3", "output": "expected output 3", "is_hidden": true}},
        {{"input": "test input 4", "output": "expected output 4", "is_hidden": true}}
    ],
    "starter_code_python": "Python starter code with function signature",
    "starter_code_java": "Java starter code with class structure",
    "starter_code_cpp": "C++ starter code with includes",
    "starter_code_javascript": "JavaScript starter code with function",
    "starter_code_c": "C starter code with includes"
}}

Requirements:
- Make it educational and clear
- Include at least 2 visible test cases and 2 hidden test cases
- Starter code should have proper function signatures
- {difficulty} difficulty level
- Related to {topic}
"""
        
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        
        # Clean JSON (remove markdown formatting if present)
        if '```json' in response_text:
            response_text = response_text.split('```json')[1].split('```')[0].strip()
        elif '```' in response_text:
            response_text = response_text.split('```')[1].split('```')[0].strip()
        
        problem_data = json.loads(response_text)
        
        return JsonResponse({
            'success': True,
            'problem': problem_data
        })
        
    except json.JSONDecodeError as e:
        return JsonResponse({
            'success': False,
            'error': f'Failed to parse AI response: {str(e)}',
            'raw_response': response_text[:500] if 'response_text' in locals() else ''
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


# ============================================
# SAVE PROBLEM
# ============================================

@login_required
@require_POST
def save_problem(request):
    """Save generated or manually created problem"""
    if not request.user.is_teacher():
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    
    try:
        data = json.loads(request.body)
        
        # Create problem
        problem = CodingProblem.objects.create(
            teacher=request.user,
            title=data.get('title'),
            description=data.get('description'),
            difficulty=data.get('difficulty', 'easy'),
            topic=data.get('topic'),
            subject_id=data.get('subject_id') if data.get('subject_id') else None,
            constraints=data.get('constraints', ''),
            sample_input=data.get('sample_input', ''),
            sample_output=data.get('sample_output', ''),
            explanation=data.get('explanation', ''),
            starter_code_python=data.get('starter_code_python', ''),
            starter_code_java=data.get('starter_code_java', ''),
            starter_code_cpp=data.get('starter_code_cpp', ''),
            starter_code_javascript=data.get('starter_code_javascript', ''),
            starter_code_c=data.get('starter_code_c', ''),
            time_limit=data.get('time_limit', 2),
            memory_limit=data.get('memory_limit', 128),
        )
        
        # Create test cases
        test_cases = data.get('test_cases', [])
        print(f"Creating {len(test_cases)} test cases for problem: {problem.title}")
        for idx, tc in enumerate(test_cases):
            test_case = TestCase.objects.create(
                problem=problem,
                input_data=tc.get('input', ''),
                expected_output=tc.get('output', ''),
                is_hidden=tc.get('is_hidden', False),
                points=tc.get('points', 25)  # Distribute points evenly
            )
            print(f"  Test {idx+1}: hidden={test_case.is_hidden}, points={test_case.points}")
        
        return JsonResponse({
            'success': True,
            'problem_id': problem.id,
            'message': 'Problem created successfully!'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


# ============================================
# ASSIGNMENT MANAGEMENT
# ============================================

@login_required
def assign_problem(request, problem_id):
    """Show form to assign problem to students"""
    if not request.user.is_teacher():
        return HttpResponseForbidden("Only teachers can access this page.")
    
    problem = get_object_or_404(CodingProblem, id=problem_id, teacher=request.user)
    subjects = Subject.objects.filter(teacher=request.user)
    
    context = {
        'problem': problem,
        'subjects': subjects,
    }
    return render(request, 'teachers/coding/assign_problem.html', context)


@login_required
@require_POST
def create_assignment(request):
    """Create assignment from problem"""
    if not request.user.is_teacher():
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    
    try:
        data = json.loads(request.body)
        problem_id = data.get('problem_id')
        
        problem = get_object_or_404(CodingProblem, id=problem_id, teacher=request.user)
        
        # Create assignment
        assignment = CodingAssignment.objects.create(
            problem=problem,
            teacher=request.user,
            subject_id=data.get('subject_id') if data.get('subject_id') else None,
            title=data.get('title'),
            instructions=data.get('instructions', ''),
            deadline=data.get('deadline'),
            is_active=True
        )
        
        return JsonResponse({
            'success': True,
            'assignment_id': assignment.id,
            'message': 'Assignment created successfully!'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
def assignments_list(request):
    """List all assignments created by teacher"""
    if not request.user.is_teacher():
        return HttpResponseForbidden("Only teachers can access this page.")
    
    assignments = CodingAssignment.objects.filter(
        teacher=request.user
    ).select_related('problem', 'subject').prefetch_related('submissions')
    
    context = {
        'assignments': assignments,
    }
    return render(request, 'teachers/coding/assignments_list.html', context)


@login_required
def assignment_submissions(request, assignment_id):
    """View all submissions for an assignment"""
    if not request.user.is_teacher():
        return HttpResponseForbidden("Only teachers can access this page.")
    
    assignment = get_object_or_404(
        CodingAssignment, 
        id=assignment_id, 
        teacher=request.user
    )
    
    submissions = assignment.submissions.select_related('student').order_by('-submitted_at')
    
    context = {
        'assignment': assignment,
        'submissions': submissions,
    }
    return render(request, 'teachers/coding/assignment_submissions.html', context)


@login_required
@require_POST
def delete_problem(request, problem_id):
    """Soft delete a problem"""
    if not request.user.is_teacher():
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    
    try:
        problem = get_object_or_404(CodingProblem, id=problem_id, teacher=request.user)
        problem.is_active = False
        problem.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Problem deleted successfully'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
@require_POST
def toggle_assignment(request, assignment_id):
    """Toggle assignment active status"""
    if not request.user.is_teacher():
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    
    try:
        assignment = get_object_or_404(CodingAssignment, id=assignment_id, teacher=request.user)
        assignment.is_active = not assignment.is_active
        assignment.save()
        
        return JsonResponse({
            'success': True,
            'is_active': assignment.is_active
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })
