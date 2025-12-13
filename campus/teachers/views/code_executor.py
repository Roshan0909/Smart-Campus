"""
Judge0 API integration for secure code execution
Documentation: https://ce.judge0.com/
"""
import requests
import time
import base64


# Judge0 CE (Community Edition) - Free API
JUDGE0_URL = "https://judge0-ce.p.rapidapi.com"

# Language IDs for Judge0
LANGUAGE_IDS = {
    'python': 71,      # Python 3.8.1
    'java': 62,        # Java (OpenJDK 13.0.1)
    'cpp': 54,         # C++ (GCC 9.2.0)
    'c': 50,           # C (GCC 9.2.0)
    'javascript': 63,  # JavaScript (Node.js 12.14.0)
}


def execute_code(source_code, language, stdin='', timeout=2):
    """
    Execute code using Judge0 API
    
    Args:
        source_code: Code to execute
        language: Programming language
        stdin: Input for the program
        timeout: Maximum execution time in seconds
    
    Returns:
        dict: Execution results
    """
    
    # TEMPORARY: Use local execution for Python if Judge0 API key not set
    # Remove this in production!
    if language.lower() == 'python':
        print("⚠️ Using local Python execution (DEVELOPMENT ONLY)")
        return execute_python_local(source_code, stdin)
    
    language_id = LANGUAGE_IDS.get(language.lower())
    if not language_id:
        return {
            'success': False,
            'error': f'Unsupported language: {language}'
        }
    
    # Encode source code and stdin to base64
    source_b64 = base64.b64encode(source_code.encode()).decode()
    stdin_b64 = base64.b64encode(stdin.encode()).decode() if stdin else ''
    
    # Submission payload
    payload = {
        'source_code': source_b64,
        'language_id': language_id,
        'stdin': stdin_b64,
        'cpu_time_limit': timeout,
        'memory_limit': 128000,  # 128 MB in KB
    }
    
    headers = {
        'content-type': 'application/json',
        'X-RapidAPI-Key': 'YOUR_RAPIDAPI_KEY',  # Replace with actual key
        'X-RapidAPI-Host': 'judge0-ce.p.rapidapi.com'
    }
    
    try:
        # Submit code
        submit_url = f"{JUDGE0_URL}/submissions?base64_encoded=true&wait=true"
        response = requests.post(submit_url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        
        result = response.json()
        
        # Decode output
        stdout = base64.b64decode(result.get('stdout', '')).decode() if result.get('stdout') else ''
        stderr = base64.b64decode(result.get('stderr', '')).decode() if result.get('stderr') else ''
        compile_output = base64.b64decode(result.get('compile_output', '')).decode() if result.get('compile_output') else ''
        
        # Map Judge0 status
        status_id = result.get('status', {}).get('id')
        status_map = {
            3: 'accepted',
            4: 'wrong_answer',
            5: 'time_limit',
            6: 'compilation_error',
            7: 'runtime_error',
            8: 'runtime_error',
            9: 'runtime_error',
            10: 'runtime_error',
            11: 'runtime_error',
            12: 'runtime_error',
            13: 'runtime_error',
        }
        
        status = status_map.get(status_id, 'pending')
        
        return {
            'success': True,
            'status': status,
            'stdout': stdout.strip(),
            'stderr': stderr.strip(),
            'compile_output': compile_output.strip(),
            'time': result.get('time'),  # Execution time in seconds
            'memory': result.get('memory'),  # Memory in KB
            'status_description': result.get('status', {}).get('description', ''),
        }
        
    except requests.exceptions.Timeout:
        return {
            'success': False,
            'status': 'time_limit',
            'error': 'Execution timeout'
        }
    except Exception as e:
        return {
            'success': False,
            'status': 'error',
            'error': str(e)
        }


def execute_with_test_cases(source_code, language, test_cases, timeout=2):
    """
    Execute code against multiple test cases
    
    Args:
        source_code: Code to execute
        language: Programming language
        test_cases: List of dicts with 'input' and 'expected_output'
        timeout: Maximum execution time per test
    
    Returns:
        dict: Results for all test cases
    """
    
    results = []
    passed_count = 0
    
    for i, test_case in enumerate(test_cases):
        result = execute_code(
            source_code=source_code,
            language=language,
            stdin=test_case['input'],
            timeout=timeout
        )
        
        if not result['success']:
            results.append({
                'test_case': i + 1,
                'passed': False,
                'status': result.get('status', 'error'),
                'error': result.get('error', ''),
                'expected': test_case['expected_output'],
                'actual': ''
            })
            continue
        
        # Check if output matches expected
        actual_output = result['stdout'].strip()
        expected_output = test_case['expected_output'].strip()
        passed = actual_output == expected_output
        
        if passed:
            passed_count += 1
        
        results.append({
            'test_case': i + 1,
            'passed': passed,
            'status': result['status'],
            'expected': expected_output,
            'actual': actual_output,
            'time': result.get('time'),
            'memory': result.get('memory'),
            'error': result.get('stderr') or result.get('compile_output') or ''
        })
    
    return {
        'total': len(test_cases),
        'passed': passed_count,
        'results': results,
        'all_passed': passed_count == len(test_cases)
    }


# Fallback: Simple Python execution (development only - NOT SECURE)
def execute_python_local(source_code, stdin=''):
    """
    LOCAL Python execution - use only for development/testing
    Should NOT be used in production!
    """
    import sys
    from io import StringIO
    import time
    
    old_stdin = sys.stdin
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    
    sys.stdin = StringIO(stdin)
    sys.stdout = StringIO()
    sys.stderr = StringIO()
    
    start_time = time.time()
    
    try:
        exec(source_code, {})
        execution_time = time.time() - start_time
        
        output = sys.stdout.getvalue()
        errors = sys.stderr.getvalue()
        
        return {
            'success': True,
            'status': 'accepted',
            'stdout': output,
            'stderr': errors,
            'compile_output': '',
            'time': execution_time,
            'memory': 0,
            'status_description': 'Accepted'
        }
    except SyntaxError as e:
        return {
            'success': False,
            'status': 'compilation_error',
            'stdout': '',
            'stderr': '',
            'compile_output': f"SyntaxError: {e.msg} at line {e.lineno}",
            'error': f"SyntaxError: {e.msg} at line {e.lineno}",
            'time': 0,
            'memory': 0
        }
    except Exception as e:
        execution_time = time.time() - start_time
        return {
            'success': False,
            'status': 'runtime_error',
            'stdout': sys.stdout.getvalue(),
            'stderr': f"{type(e).__name__}: {str(e)}",
            'compile_output': '',
            'error': f"{type(e).__name__}: {str(e)}",
            'time': execution_time,
            'memory': 0
        }
    finally:
        sys.stdin = old_stdin
        sys.stdout = old_stdout
        sys.stderr = old_stderr


def execute_python_unsafe(source_code, stdin=''):
    """Deprecated - use execute_python_local instead"""
    return execute_python_local(source_code, stdin)
