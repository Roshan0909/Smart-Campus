"""
Test script to verify code execution and test cases work properly
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'student_campus.settings')
django.setup()

from teachers.models_coding import CodingProblem, TestCase, CodingAssignment
from authentication.models import User

def test_code_execution():
    print("\n" + "="*60)
    print("TESTING CODE ARENA - Test Cases & Execution")
    print("="*60)
    
    # Check if any problems exist
    problems = CodingProblem.objects.all()
    print(f"\n✓ Total problems in database: {problems.count()}")
    
    if problems.exists():
        for problem in problems:
            print(f"\n📝 Problem: {problem.title}")
            print(f"   Difficulty: {problem.difficulty}")
            print(f"   Topic: {problem.topic}")
            
            # Check test cases
            test_cases = problem.test_cases.all()
            visible = test_cases.filter(is_hidden=False)
            hidden = test_cases.filter(is_hidden=True)
            
            print(f"   Test Cases: {test_cases.count()} total")
            print(f"   - Visible: {visible.count()}")
            print(f"   - Hidden: {hidden.count()}")
            
            if test_cases.exists():
                print("\n   Test Case Details:")
                for idx, tc in enumerate(test_cases, 1):
                    visibility = "🔒 Hidden" if tc.is_hidden else "👁️ Visible"
                    print(f"   Test {idx} {visibility}:")
                    print(f"      Input: {tc.input_data[:50]}...")
                    print(f"      Output: {tc.expected_output[:50]}...")
                    print(f"      Points: {tc.points}")
            else:
                print("   ⚠️ WARNING: No test cases found!")
            
            # Check assignments
            assignments = CodingAssignment.objects.filter(problem=problem)
            print(f"\n   Assignments: {assignments.count()}")
            for assign in assignments:
                print(f"   - {assign.title} (Active: {assign.is_active})")
    
    else:
        print("\n⚠️ No problems found in database!")
        print("   Please create a problem using the teacher interface first.")
    
    print("\n" + "="*60)
    print("Test Complete!")
    print("="*60 + "\n")

if __name__ == '__main__':
    test_code_execution()
