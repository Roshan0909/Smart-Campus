"""
Student Code Arena Views
Handles: Viewing assignments, solving problems, running/submitting code
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.utils import timezone
import json
import subprocess
import tempfile
import os
import google.generativeai as genai
from django.conf import settings

from teachers.models import CodingProblem, CodingAssignment, TestCase, CodingSubmission


def parse_input_with_ai(test_input, problem_description, code):
    """
    Use AI to intelligently parse test input based on problem description
    Returns: list of parsed arguments to pass to the function
    """
    import json
    import re
    
    try:
        if not settings.GEMINI_API_KEY:
            print("⚠️ GEMINI_API_KEY not configured. Using basic parsing.")
            return parse_input_basic(test_input)
        
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Extract function signature and node class (if exists)
        func_signature = extract_function_signature(code)
        node_class = extract_node_class(code)
        
        # Detect if this is a linked list problem
        is_linked_list = 'ListNode' in code or 'Node' in code or 'linked' in problem_description.lower()
        is_tree = 'TreeNode' in code or 'tree' in problem_description.lower()
        
        prompt = f"""Analyze this problem and input, then parse the input into the correct argument types.

PROBLEM DESCRIPTION:
{problem_description}

FUNCTION SIGNATURE:
{func_signature}

NODE CLASS (if applicable):
{node_class if node_class else 'Not a linked structure problem'}

CODE PREVIEW:
{code[:500]}

TEST INPUT (raw string):
{test_input}

Your task:
1. Identify the function parameter names and types
2. Parse input into correct types: int, float, str, list, array, etc.
3. For linked lists: Convert arrays to linked list structure
4. Return ONLY a valid Python list of parsed arguments

IMPORTANT INSTRUCTIONS:
- For arrays/lists: parse as Python lists [1, 2, 3]
- For linked lists: Keep as Python list [1, 2, 3] - code will convert to ListNode
- For multiple inputs: split by newlines
- Convert to int/float when appropriate
- If input is JSON format, parse it
- Return format: ["arg1", 42, [1, 2, 3]] (valid Python syntax)
- Do NOT include any explanation, ONLY the Python list

Example inputs and outputs:
- Input "5" for n:int → [5]
- Input "1 2 3" for head:ListNode → [[1, 2, 3]]
- Input "[1,2,3]\\n[4,5,6]" for l1, l2 linked lists → [[1, 2, 3], [4, 5, 6]]
- Input "hello\\nworld" for s1:str, s2:str → ["hello", "world"]

Return ONLY the Python list representation (no markdown, no explanation):"""
        
        response = model.generate_content(prompt, safety_settings=[
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_CIVIC_INTEGRITY", "threshold": "BLOCK_NONE"},
        ])
        
        result_text = response.text.strip()
        print(f"🤖 AI parsed input: {result_text}")
        
        # Clean up the response
        result_text = result_text.replace('```python', '').replace('```', '').strip()
        
        # Safely evaluate the list
        try:
            parsed_args = eval(result_text)
            if isinstance(parsed_args, list):
                # Convert array arguments to ListNode if needed
                if is_linked_list:
                    parsed_args = convert_arrays_to_linked_list(parsed_args, code)
                return parsed_args
        except:
            pass
        
        # Fallback to basic parsing if AI parsing fails
        print("⚠️ AI parsing failed, using basic parsing")
        result = parse_input_basic(test_input)
        if is_linked_list:
            result = convert_arrays_to_linked_list(result, code)
        return result
        
    except Exception as e:
        print(f"❌ AI parsing error: {str(e)}")
        result = parse_input_basic(test_input)
        return result


def extract_function_signature(code):
    """Extract function signature from code"""
    import re
    match = re.search(r'def\s+(\w+)\s*\((.*?)\):', code)
    if match:
        return f"def {match.group(1)}({match.group(2)}):"
    return "Unknown function"


def extract_node_class(code):
    """Extract ListNode or Node class definition from code"""
    import re
    # Look for class definition (ListNode, Node, TreeNode, etc.)
    class_pattern = r'class\s+(\w*Node)\s*(?:\(|:)(.*?)(?=class|\Z)'
    match = re.search(class_pattern, code, re.DOTALL)
    if match:
        return match.group(0)
    return None


def parse_input_basic(test_input):
    """Basic fallback input parsing"""
    import json
    
    # Try JSON parsing first
    try:
        parsed = json.loads(test_input)
        if isinstance(parsed, list):
            return parsed
        return [parsed]
    except:
        pass
    
    # Split by newlines
    lines = test_input.strip().split('\n')
    
    # Try to convert each line
    result = []
    for line in lines:
        line = line.strip()
        
        # Try JSON (for arrays)
        try:
            parsed = json.loads(line)
            result.append(parsed)
            continue
        except:
            pass
        
        # Try int
        try:
            result.append(int(line))
            continue
        except:
            pass
        
        # Try float
        try:
            result.append(float(line))
            continue
        except:
            pass
        
        # Keep as string
        result.append(line)
    
    return result if result else [test_input]


def convert_arrays_to_linked_list(args, code):
    """
    Convert array arguments to ListNode structures for linked list problems
    Returns: list of converted arguments
    """
    # Just return args - conversion happens in execute_python_code with helper function
    return args


# ============================================
# STUDENT DASHBOARD & ASSIGNMENTS
# ============================================

@login_required
def assignments_dashboard(request):
    """Student dashboard showing all active assignments"""
    if not request.user.is_student():
        return HttpResponseForbidden("Only students can access this page.")
    
    # Get all active assignments
    assignments = CodingAssignment.objects.filter(
        is_active=True
    ).select_related('problem', 'teacher').order_by('-assigned_date')
    
    # Get student's submissions
    submissions = CodingSubmission.objects.filter(student=request.user)
    solved_ids = submissions.filter(status='accepted').values_list('problem_id', flat=True)
    attempted_ids = submissions.values_list('problem_id', flat=True).distinct()
    
    # Annotate assignments with status
    assignments_data = []
    for assignment in assignments:
        is_solved = assignment.problem.id in solved_ids
        is_attempted = assignment.problem.id in attempted_ids
        is_overdue = timezone.now() > assignment.deadline
        
        # Get best submission
        best_submission = submissions.filter(
            assignment=assignment
        ).order_by('-score', 'submitted_at').first()
        
        # Check if completed (any submission locks the assignment)
        is_completed = best_submission is not None
        
        # Always show score if there's a submission
        best_score = best_submission.score if best_submission else None
        
        assignments_data.append({
            'assignment': assignment,
            'solved': is_solved,
            'attempted': is_attempted,
            'overdue': is_overdue,
            'completed': is_completed,  # ✅ NEW: Perfect score flag
            'best_score': best_score,  # Changed to show None instead of 0
            'best_status': best_submission.status if best_submission else None,
        })
    
    context = {
        'assignments_data': assignments_data,
        'total': len(assignments_data),
        'solved': len([a for a in assignments_data if a['solved']]),
        'attempted': len([a for a in assignments_data if a['attempted']]),
    }
    return render(request, 'students/coding/assignments_dashboard.html', context)


# ============================================
# SOLVE PROBLEM (MAIN EDITOR)
# ============================================

@login_required
def solve_problem(request, assignment_id):
    """Main problem-solving interface with split-screen editor"""
    if not request.user.is_student():
        return HttpResponseForbidden("Only students can access this page.")
    
    assignment = get_object_or_404(CodingAssignment, id=assignment_id, is_active=True)
    
    # ✅ CHECK: Prevent access if already completed with perfect score
    best_submission = CodingSubmission.objects.filter(
        student=request.user,
        assignment=assignment
    ).order_by('-score').first()
    
    if best_submission:
        messages.warning(request, f'🔒 You have already submitted "{assignment.problem.title}". This problem is locked and cannot be reattempted.')
        return redirect('student_coding_dashboard')
    
    problem = assignment.problem
    
    # Get visible test cases
    visible_tests = problem.test_cases.filter(is_hidden=False)
    
    # Get previous submissions
    previous_submissions = CodingSubmission.objects.filter(
        student=request.user,
        assignment=assignment
    ).order_by('-submitted_at')[:5]
    
    # Check if overdue
    is_overdue = timezone.now() > assignment.deadline
    
    context = {
        'assignment': assignment,
        'problem': problem,
        'visible_tests': visible_tests,
        'previous_submissions': previous_submissions,
        'is_overdue': is_overdue,
        'best_submission': best_submission,  # ✅ Pass best submission for completion check
    }
    return render(request, 'students/coding/solve_problem.html', context)


# ============================================
# CODE EXECUTION
# ============================================

def execute_python_code(code, test_input, time_limit=2, problem_description=''):
    """
    Execute Python code with test input - dynamically handles different input formats
    Supports: arrays, primitives, linked lists, trees, etc.
    Returns: (output, error, execution_time, status)
    """
    import time
    import json
    
    try:
        # Use AI to intelligently parse input based on problem description
        parsed_input_args = parse_input_with_ai(test_input, problem_description, code)
        
        # Check if this is a linked list problem
        is_linked_list = 'ListNode' in code or 'Node' in code or 'linked' in problem_description.lower()
        
        # Build the test runner with parsed arguments
        args_str = ', '.join([repr(arg) for arg in parsed_input_args])
        
        # Add ListNode conversion helper if needed
        helper_section = ""
        if is_linked_list:
            helper_section = """
# Helper to convert array to linked list
def _array_to_linked_list(arr):
    if not arr:
        return None
    import inspect
    node_class = None
    for name, obj in inspect.getmembers(globals()):
        if inspect.isclass(obj) and 'Node' in name:
            node_class = obj
            break
    if node_class is None:
        return arr  # Fallback if no Node class found
    head = node_class(arr[0])
    current = head
    for val in arr[1:]:
        current.next = node_class(val)
        current = current.next
    return head

# Helper to convert linked list back to array
def _linked_list_to_array(head):
    if head is None:
        return []
    result = []
    current = head
    while current:
        if hasattr(current, 'val'):
            result.append(current.val)
        else:
            result.append(current)
        current = current.next if hasattr(current, 'next') else None
    return result

# Helper to convert tree to array (level-order)
def _tree_to_array(root):
    if root is None:
        return []
    from collections import deque
    result = []
    queue = deque([root])
    while queue:
        node = queue.popleft()
        if node is None:
            result.append(None)
        else:
            if hasattr(node, 'val'):
                result.append(node.val)
            else:
                result.append(node)
            if hasattr(node, 'left'):
                queue.append(node.left)
            if hasattr(node, 'right'):
                queue.append(node.right)
    # Trim trailing Nones
    while result and result[-1] is None:
        result.pop()
    return result
"""
        
        wrapped_code = code + helper_section + f"""

# Auto-generated test runner
if __name__ == '__main__':
    import sys
    try:
        import inspect
        
        # Pre-parsed arguments from intelligent input parser
        test_args = [{args_str}]
        
        # Convert array arguments to linked list if needed
        is_linked_list = {is_linked_list}
        if is_linked_list:
            test_args = [_array_to_linked_list(arg) if isinstance(arg, list) else arg for arg in test_args]
        
        # Get all functions defined in this module
        current_module = sys.modules[__name__]
        functions = [obj for name, obj in inspect.getmembers(current_module) 
                    if inspect.isfunction(obj) and obj.__module__ == __name__ and not name.startswith('_')]
        
        if functions:
            func = functions[0]
            # Call with unpacked arguments
            result = func(*test_args)
            
            # Convert result back to array if it's a linked list or tree
            if is_linked_list:
                # Check if result is a node (has 'next' or 'left'/'right')
                if hasattr(result, 'next'):
                    result = _linked_list_to_array(result)
                elif hasattr(result, 'left') or hasattr(result, 'right'):
                    result = _tree_to_array(result)
            
            print(result)
        else:
            # If no function found, try stdin approach
            pass
    except Exception as e:
        print(f"Error: {{e}}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
"""
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(wrapped_code)
            temp_file = f.name
        
        # Execute
        start_time = time.time()
        
        process = subprocess.run(
            ['python', temp_file],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=time_limit,
            text=True,
            encoding='utf-8'
        )
        
        execution_time = time.time() - start_time
        
        # Clean up
        os.unlink(temp_file)
        
        if process.returncode != 0:
            error_msg = process.stderr.strip()
            # Remove the auto-generated code from error messages
            error_lines = [line for line in error_msg.split('\n') 
                          if 'Auto-generated test runner' not in line]
            return None, '\n'.join(error_lines), execution_time, 'runtime_error'
        
        return process.stdout.strip(), None, execution_time, 'success'
        
    except subprocess.TimeoutExpired:
        try:
            os.unlink(temp_file)
        except:
            pass
        return None, 'Time Limit Exceeded', time_limit, 'time_limit'
    except Exception as e:
        return None, str(e), 0, 'runtime_error'


def get_friendly_error_message(error_text, code):
    """Convert technical error to friendly message using AI"""
    try:
        # Check if API key exists
        if not settings.GEMINI_API_KEY:
            print("⚠️ GEMINI_API_KEY not configured! Set API_KEY environment variable.")
            raise ValueError("API key not configured")
        
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        prompt = f"""You are a friendly coding buddy helping a friend fix their code. A student got this error:

ERROR:
{error_text}

THEIR CODE:
{code}

Talk to them like a casual friend! Start with something like "Hey buddy" or "Yo" or "Dude".
IMPORTANT: Always mention the SPECIFIC error type (like SyntaxError, NameError, TypeError, etc.) in your message.
Point out EXACTLY what went wrong - mention the specific line number, variable name, or mistake.
Be playful and encouraging, maybe call them "silly" or make a light joke.
Keep it to 2-3 short sentences max. Be super casual and friendly like texting a friend.

Example styles:
- "Hey buddy! You got a SyntaxError on line 5 - you forgot the colon after your if statement, silly! Python needs that colon."
- "Yo! NameError on line 3 - you're trying to use a variable 'count' that doesn't exist yet. Define it first, dude!"
- "Dude! TypeError happening - you're trying to add a string and a number on line 7. Convert one of them first!"

Now write your friendly message (make sure to include the error type):"""
        
        response = model.generate_content(prompt)
        hint = response.text.strip()
        print(f"✅ Generated AI hint: {hint[:100]}...")
        return hint
        
    except Exception as e:
        print(f"❌ AI hint generation failed: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return "Hey! Something's not quite right with your code. Take another look at the error above!"


@login_required
@require_POST
def run_code(request):
    """Run code against visible test cases only"""
    print("\n=== RUN CODE REQUEST ===")
    if not request.user.is_student():
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    
    try:
        data = json.loads(request.body)
        assignment_id = data.get('assignment_id')
        code = data.get('code')
        language = data.get('language', 'python')
        print(f"Assignment ID: {assignment_id}, Language: {language}")
        print(f"Code length: {len(code)} characters")
        
        if language != 'python':
            return JsonResponse({
                'success': False,
                'error': f'{language} execution coming soon! Use Python for now.'
            })
        
        assignment = get_object_or_404(CodingAssignment, id=assignment_id)
        problem = assignment.problem
        
        # Get visible test cases only
        test_cases = problem.test_cases.filter(is_hidden=False)
        
        if not test_cases.exists():
            return JsonResponse({
                'success': False,
                'error': 'No test cases found for this problem. Please contact your teacher.'
            })
        
        results = []
        passed_count = 0
        first_error = None
        
        for idx, test in enumerate(test_cases, 1):
            output, error, exec_time, status = execute_python_code(
                code, 
                test.input_data, 
                problem.time_limit,
                problem.description  # ✅ Pass problem description for AI parsing
            )
            
            # Check if output matches
            if status == 'success':
                actual_output = output.strip() if output else ''
                expected_output = test.expected_output.strip()
                
                if actual_output == expected_output:
                    passed = True
                    passed_count += 1
                    final_status = 'accepted'
                else:
                    passed = False
                    final_status = 'wrong_answer'
            else:
                passed = False
                actual_output = ''
                final_status = status
                if not first_error and error:
                    first_error = error
            
            results.append({
                'test_number': idx,
                'passed': passed,
                'status': final_status,
                'input': test.input_data[:100],  # Limit display
                'expected_output': test.expected_output[:100],
                'actual_output': actual_output[:100] if actual_output else '(no output)',
                'error': error if error else None,
                'time': round(exec_time, 3)
            })
        
        # Generate friendly hint if there were errors
        friendly_hint = None
        if first_error:
            print(f"🔍 First error detected: {first_error[:100]}")
            friendly_hint = get_friendly_error_message(first_error, code)
            print(f"💬 Friendly hint result: {friendly_hint[:100] if friendly_hint else 'None'}")
        else:
            print("✅ No errors - all tests passed!")
        
        print(f"Run Code - Test cases: {len(test_cases)}, Passed: {passed_count}")
        print(f"Results count: {len(results)}")
        if friendly_hint:
            print(f"Friendly hint: {friendly_hint[:100]}")
        
        return JsonResponse({
            'success': True,
            'results': results,
            'passed': passed_count,
            'total': len(test_cases),
            'all_passed': passed_count == len(test_cases),
            'friendly_hint': friendly_hint,
        })
        
    except Exception as e:
        import traceback
        print(f"Error in run_code: {str(e)}")
        print(traceback.format_exc())
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
@require_POST
def submit_code(request):
    """Submit code for grading (runs all test cases including hidden)"""
    if not request.user.is_student():
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    
    try:
        data = json.loads(request.body)
        assignment_id = data.get('assignment_id')
        code = data.get('code')
        language = data.get('language', 'python')
        
        if language != 'python':
            return JsonResponse({
                'success': False,
                'error': f'{language} submission coming soon! Use Python for now.'
            })
        
        assignment = get_object_or_404(CodingAssignment, id=assignment_id)
        problem = assignment.problem
        
        # Get ALL test cases (visible + hidden)
        test_cases = problem.test_cases.all()
        
        if not test_cases.exists():
            return JsonResponse({
                'success': False,
                'error': 'No test cases found for this problem. Please contact your teacher.'
            })
        
        results = []
        passed_count = 0
        total_points = 0
        earned_points = 0
        first_error = None
        submission_status = 'accepted'
        
        for test in test_cases:
            total_points += test.points
            
            output, error, exec_time, status = execute_python_code(
                code,
                test.input_data,
                problem.time_limit,
                problem.description  # ✅ Pass problem description for AI parsing
            )
            
            if status == 'success':
                actual_output = output.strip() if output else ''
                expected_output = test.expected_output.strip()
                
                if actual_output == expected_output:
                    passed = True
                    passed_count += 1
                    earned_points += test.points
                else:
                    passed = False
                    submission_status = 'wrong_answer'
            else:
                passed = False
                submission_status = status
                if not first_error and error:
                    first_error = error
            
            # Only show hidden test results as pass/fail (no details)
            if test.is_hidden:
                results.append({
                    'test_number': len(results) + 1,
                    'passed': passed,
                    'hidden': True,
                })
            else:
                results.append({
                    'test_number': len(results) + 1,
                    'passed': passed,
                    'status': status if not passed else 'accepted',
                    'input': test.input_data[:100],
                    'expected_output': test.expected_output[:100],
                    'actual_output': output[:100] if output else '(no output)',
                    'error': error if error else None,
                    'hidden': False,
                })
        
        # Calculate score (0-100)
        score = int((earned_points / total_points) * 100) if total_points > 0 else 0
        
        # Generate friendly feedback
        friendly_hint = None
        if first_error:
            friendly_hint = get_friendly_error_message(first_error, code)
        
        # Save submission
        submission = CodingSubmission.objects.create(
            assignment=assignment,
            problem=problem,
            student=request.user,
            language=language,
            source_code=code,
            status=submission_status,
            score=score,
            test_cases_passed=passed_count,
            test_cases_total=len(test_cases),
            friendly_hint=friendly_hint or '',
            error_message=first_error or ''
        )
        
        return JsonResponse({
            'success': True,
            'submission_id': submission.id,
            'score': score,
            'status': submission_status,
            'results': results,
            'passed': passed_count,
            'total': len(test_cases),
            'all_passed': passed_count == len(test_cases),
            'friendly_hint': friendly_hint,
            'message': 'Submission saved successfully!'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


# ============================================
# SUBMISSION HISTORY
# ============================================

@login_required
def my_submissions(request):
    """View student's submission history"""
    if not request.user.is_student():
        return HttpResponseForbidden("Only students can access this page.")
    
    submissions = CodingSubmission.objects.filter(
        student=request.user
    ).select_related('problem', 'assignment').order_by('-submitted_at')
    
    context = {
        'submissions': submissions,
    }
    return render(request, 'students/coding/my_submissions.html', context)


@login_required
def submission_detail(request, submission_id):
    """View details of a specific submission"""
    if not request.user.is_student():
        return HttpResponseForbidden("Only students can access this page.")
    
    submission = get_object_or_404(
        CodingSubmission, 
        id=submission_id, 
        student=request.user
    )
    
    context = {
        'submission': submission,
    }
    return render(request, 'students/coding/submission_detail.html', context)
