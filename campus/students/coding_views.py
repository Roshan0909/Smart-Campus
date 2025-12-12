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

from teachers.models_coding import CodingProblem, CodingAssignment, TestCase, CodingSubmission


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
        
        # Check if completed with perfect score
        is_completed = best_submission and best_submission.score == 100
        
        assignments_data.append({
            'assignment': assignment,
            'solved': is_solved,
            'attempted': is_attempted,
            'overdue': is_overdue,
            'completed': is_completed,  # ✅ NEW: Perfect score flag
            'best_score': best_submission.score if best_submission else 0,
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
    
    if best_submission and best_submission.score == 100:
        messages.warning(request, f'✅ You have already completed "{assignment.problem.title}" with a perfect score (100/100). This problem is locked and cannot be reattempted.')
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

def execute_python_code(code, test_input, time_limit=2):
    """
    Execute Python code with test input
    Returns: (output, error, execution_time, status)
    """
    import time
    import ast
    
    try:
        # Wrap the code to call the function with test input
        # This handles both function-based and stdin-based code
        wrapped_code = code + f"""

# Auto-generated test runner
if __name__ == '__main__':
    import sys
    try:
        # Try to find and call the first defined function
        import inspect
        test_input = {test_input}
        
        # Get all functions defined in this module
        current_module = sys.modules[__name__]
        functions = [obj for name, obj in inspect.getmembers(current_module) 
                    if inspect.isfunction(obj) and obj.__module__ == __name__]
        
        if functions:
            # Call the first function with test input
            result = functions[0](test_input)
            print(result)
        else:
            # If no function, the code should handle stdin
            pass
    except Exception as e:
        print(f"Error calling function: {{e}}", file=sys.stderr)
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
                problem.time_limit
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
                problem.time_limit
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
