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
import re
import sys
import os

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
    """Generate problem using AI with fallback support (Gemini → Claude → Local)"""
    if not request.user.is_teacher():
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    
    try:
        data = json.loads(request.body)
        topic = data.get('topic', '').strip()
        difficulty = data.get('difficulty', 'easy')
        language = data.get('language', 'python')
        
        if not topic:
            return JsonResponse({'success': False, 'error': 'Topic is required'})
        
        # Create prompt
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
- For functions with multiple parameters, provide inputs on separate lines (one parameter per line)
- Related to {topic}
"""
        
        # Try Primary AI: Google Gemini
        print("🤖 Attempting Gemini AI generation...")
        problem_data = try_gemini_generation(prompt)
        if problem_data:
            print("✅ Gemini succeeded")
            return JsonResponse({'success': True, 'problem': problem_data})
        
        # Try Fallback AI: Ollama (local LLM)
        print("⚠️ Gemini failed, trying Ollama fallback...")
        problem_data = try_ollama_generation(prompt)
        if problem_data:
            print("✅ Ollama succeeded")
            return JsonResponse({'success': True, 'problem': problem_data})
        
        # Try Local Template Fallback (no API needed!)
        print("⚠️ Ollama failed, using local template fallback...")
        problem_data = generate_template_problem(topic, difficulty, language)
        if problem_data:
            print("✅ Local template fallback succeeded")
            return JsonResponse({'success': True, 'problem': problem_data})
        
        # Both failed - return detailed error message
        gemini_status = "❌ GEMINI_API_KEY not configured" if not settings.GEMINI_API_KEY else "❌ API call failed"
        ollama_status = "❌ Ollama not running on http://localhost:11434"
        
        error_msg = f"""All AI services failed:
- {gemini_status}
- {ollama_status}

Quick Fix:
1. Set GEMINI_API_KEY in .env file, OR
2. Install & run Ollama:
   - Download: https://ollama.ai
   - Start: ollama serve
   - Then refresh this page
"""
        
        print(error_msg)
        return JsonResponse({
            'success': False,
            'error': error_msg
        })
        
    except Exception as e:
        print(f"❌ Error in generate_problem_ai: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


def try_gemini_generation(prompt):
    """Try to generate using Google Gemini"""
    try:
        if not settings.GEMINI_API_KEY:
            print("⚠️ GEMINI_API_KEY not found in settings")
            return None
        
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        
        # Clean JSON (remove markdown formatting if present)
        if '```json' in response_text:
            response_text = response_text.split('```json')[1].split('```')[0].strip()
        elif '```' in response_text:
            response_text = response_text.split('```')[1].split('```')[0].strip()
        
        # Try direct parse
        trimmed = response_text.strip()
        if trimmed.startswith('{') or trimmed.startswith('['):
            try:
                return json.loads(trimmed)
            except Exception:
                pass
        
        # Extract first JSON object
        json_match = re.search(r'(\{[\s\S]*\}|\[[\s\S]*\])', response_text)
        if json_match:
            json_str = json_match.group().strip()
            return json.loads(json_str)
        
        print("⚠️ Gemini returned invalid JSON format")
        return None
        
    except Exception as e:
        print(f"❌ Gemini error: {str(e)}")
        return None


def try_ollama_generation(prompt):
    """Try to generate using Ollama (local LLM)"""
    try:
        import requests
        
        # Check if Ollama is running locally
        ollama_url = "http://localhost:11434"
        ollama_model = "mistral"  # Default model
        
        # Test connection
        try:
            print(f"📡 Testing Ollama connection at {ollama_url}...")
            response = requests.get(f"{ollama_url}/api/tags", timeout=3)
            if response.status_code != 200:
                print(f"⚠️ Ollama server returned status {response.status_code}")
                return None
            
            # Check available models
            available_models = response.json().get('models', [])
            if not available_models:
                print("⚠️ Ollama has no models installed. Run: ollama pull mistral")
                return None
            
            # Use first available model if mistral not available
            ollama_model = next((m['name'].split(':')[0] for m in available_models), "mistral")
            print(f"✓ Using Ollama model: {ollama_model}")
            
        except requests.exceptions.ConnectionError:
            print("⚠️ Cannot connect to Ollama (http://localhost:11434)")
            print("   Install from: https://ollama.ai")
            print("   Then start: ollama serve")
            return None
        except requests.exceptions.Timeout:
            print("⚠️ Ollama connection timeout")
            return None
        
        # Generate with Ollama
        print(f"📡 Querying Ollama ({ollama_model})...")
        response = requests.post(
            f"{ollama_url}/api/generate",
            json={
                "model": ollama_model,
                "prompt": prompt,
                "stream": False,
                "temperature": 0.7,
            },
            timeout=120
        )
        
        if response.status_code != 200:
            print(f"⚠️ Ollama error: {response.status_code}")
            return None
        
        response_text = response.json().get("response", "").strip()
        
        # Clean JSON
        if '```json' in response_text:
            response_text = response_text.split('```json')[1].split('```')[0].strip()
        elif '```' in response_text:
            response_text = response_text.split('```')[1].split('```')[0].strip()
        
        # Parse
        trimmed = response_text.strip()
        if trimmed.startswith('{') or trimmed.startswith('['):
            try:
                return json.loads(trimmed)
            except Exception:
                pass
        
        json_match = re.search(r'(\{[\s\S]*\}|\[[\s\S]*\])', response_text)
        if json_match:
            json_str = json_match.group().strip()
            return json.loads(json_str)
        
        print("⚠️ Ollama response format invalid")
        return None
        
    except ImportError:
        print("⚠️ requests package not installed")
        return None
    except Exception as e:
        print(f"❌ Ollama error: {str(e)}")
        return None


def try_claude_generation(prompt):
    """Try to generate using Claude (OpenAI compatible API)"""
    try:
        import anthropic
        
        api_key = getattr(settings, 'CLAUDE_API_KEY', None)
        if not api_key:
            print("⚠️ Claude API key not configured")
            return None
        
        client = anthropic.Anthropic(api_key=api_key)
        
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=2048,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        response_text = message.content[0].text.strip()
        
        # Clean JSON
        if '```json' in response_text:
            response_text = response_text.split('```json')[1].split('```')[0].strip()
        elif '```' in response_text:
            response_text = response_text.split('```')[1].split('```')[0].strip()
        
        # Parse
        trimmed = response_text.strip()
        if trimmed.startswith('{') or trimmed.startswith('['):
            try:
                return json.loads(trimmed)
            except Exception:
                pass
        
        json_match = re.search(r'(\{[\s\S]*\}|\[[\s\S]*\])', response_text)
        if json_match:
            json_str = json_match.group().strip()
            return json.loads(json_str)
        
        return None
        
    except ImportError:
        print("⚠️ anthropic package not installed")
        return None
    except Exception as e:
        print(f"❌ Claude error: {str(e)}")
        return None


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
    try:
        if not request.user.is_teacher():
            return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
        
        problem = CodingProblem.objects.get(id=problem_id, teacher=request.user)
        problem.is_active = False
        problem.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Problem deleted successfully'
        })
    except CodingProblem.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Problem not found or you do not have permission to delete it'
        }, status=404)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


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


# ============================================
# LOCAL TEMPLATE FALLBACK (NO API NEEDED)
# ============================================

def generate_template_problem(topic, difficulty, language):
    """Generate a basic problem using local templates (no API needed)"""
    
    # Template problems by topic
    templates = {
        'array': {
            'title': f'Array Operation: {topic.title()}',
            'description': f'Write a function that performs an operation on an array related to {topic}.',
            'constraints': 'Array length: 1 to 1000\nArray values: -10^9 to 10^9',
            'sample_input': '[1, 2, 3, 4, 5]',
            'sample_output': '[5, 4, 3, 2, 1]' if 'reverse' in topic.lower() else '[15]',
            'explanation': f'Perform {topic} on the given array.',
        },
        'string': {
            'title': f'String Manipulation: {topic.title()}',
            'description': f'Write a function that performs string {topic}.',
            'constraints': 'String length: 1 to 1000\nCharacters: alphanumeric',
            'sample_input': 'hello world',
            'sample_output': 'olleh dlrow' if 'reverse' in topic.lower() else 'HELLO WORLD',
            'explanation': f'Apply {topic} to the input string.',
        },
        'linked list': {
            'title': f'Linked List: {topic.title()}',
            'description': f'Given a linked list, {topic}.',
            'constraints': 'List length: 1 to 1000\nNode values: -10^9 to 10^9',
            'sample_input': '[1, 2, 3]',
            'sample_output': '[3, 2, 1]' if 'reverse' in topic.lower() else '[1, 2, 3]',
            'explanation': f'Perform {topic} on the linked list.',
        },
        'tree': {
            'title': f'Binary Tree: {topic.title()}',
            'description': f'Given a binary tree, {topic}.',
            'constraints': 'Tree nodes: 1 to 1000\nNode values: -10^9 to 10^9',
            'sample_input': '[1, 2, 3, 4, 5]',
            'sample_output': '15' if 'sum' in topic.lower() else '[1, 2, 3, 4, 5]',
            'explanation': f'Perform {topic} on the binary tree.',
        },
        'math': {
            'title': f'Math Problem: {topic.title()}',
            'description': f'Solve a math problem related to {topic}.',
            'constraints': 'Number range: 1 to 10^6',
            'sample_input': '5',
            'sample_output': '120' if 'factorial' in topic.lower() else '5',
            'explanation': f'Calculate {topic}.',
        },
    }
    
    # Find best matching template
    selected = None
    for key, template in templates.items():
        if key in topic.lower():
            selected = template
            break
    
    # Use default array template if no match
    if not selected:
        selected = templates['array']
    
    # Adjust difficulty
    if difficulty == 'easy':
        selected['constraints'] += '\nTime Complexity: O(n)\nSpace Complexity: O(1)'
    elif difficulty == 'medium':
        selected['constraints'] += '\nTime Complexity: O(n log n)\nSpace Complexity: O(n)'
    else:
        selected['constraints'] += '\nTime Complexity: O(n^2)\nSpace Complexity: O(n)'
    
    # Generate starter code based on language
    starter_codes = {
        'python': f'def solve({topic.split()[0].lower()}):\n    """{selected["explanation"]}""""""\n    pass',
        'java': f'public class Solution {{\n    public int solve(int[] arr) {{\n        // {selected["explanation"]}\n        return 0;\n    }}\n}}',
        'cpp': f'#include <vector>\nusing namespace std;\n\nint solve(vector<int>& arr) {{\n    // {selected["explanation"]}\n    return 0;\n}}',
        'javascript': f'function solve(arr) {{\n    // {selected["explanation"]}\n    return 0;\n}}',
        'c': f'int solve(int arr[], int n) {{\n    // {selected["explanation"]}\n    return 0;\n}}',
    }
    
    return {
        'title': selected['title'],
        'description': selected['description'],
        'constraints': selected['constraints'],
        'sample_input': selected['sample_input'],
        'sample_output': selected['sample_output'],
        'explanation': selected['explanation'],
        'test_cases': [
            {
                'input': selected['sample_input'],
                'output': selected['sample_output'],
                'is_hidden': False
            },
            {
                'input': '[1, 1, 1]' if 'array' in topic.lower() else 'test',
                'output': '[1, 1, 1]' if 'array' in topic.lower() else 'tset',
                'is_hidden': False
            },
            {
                'input': '[10, 20, 30]' if 'array' in topic.lower() else 'hidden',
                'output': '[30, 20, 10]' if 'array' in topic.lower() else 'neddih',
                'is_hidden': True
            },
            {
                'input': '[100]' if 'array' in topic.lower() else 'single',
                'output': '[100]' if 'array' in topic.lower() else 'elgnis',
                'is_hidden': True
            },
        ],
        'starter_code_python': starter_codes.get('python', ''),
        'starter_code_java': starter_codes.get('java', ''),
        'starter_code_cpp': starter_codes.get('cpp', ''),
        'starter_code_javascript': starter_codes.get('javascript', ''),
        'starter_code_c': starter_codes.get('c', ''),
    }
