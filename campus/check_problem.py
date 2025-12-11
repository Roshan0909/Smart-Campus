import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'student_campus.settings')
django.setup()

from teachers.models_coding import CodingProblem

p = CodingProblem.objects.first()
if p:
    print('='*60)
    print('STARTER CODE:')
    print('='*60)
    print(p.starter_code_python)
    print('\n' + '='*60)
    print('FIRST TEST CASE:')
    print('='*60)
    tc = p.test_cases.first()
    print(f'Input: {tc.input_data}')
    print(f'Expected Output: {tc.expected_output}')
else:
    print('No problems found')
