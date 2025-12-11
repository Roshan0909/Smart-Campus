"""
AI-powered coding problem generator using Gemini
"""
import json
import re
from ai_fallback import generate_content


def generate_coding_problem(topic, difficulty='medium', language='python', subject_context=''):
    """
    Generate a complete coding problem with test cases using AI
    
    Args:
        topic: Programming topic (e.g., "arrays", "recursion", "dynamic programming")
        difficulty: Problem difficulty level
        language: Primary programming language
        subject_context: Additional context from subject/course
    
    Returns:
        dict: Complete problem with test cases and starter code
    """
    
    prompt = f"""Generate a {difficulty} difficulty coding problem about {topic}.

Output ONLY valid JSON in this exact format (no markdown, no explanation):

{{
  "title": "Problem title",
  "description": "Clear problem statement with examples",
  "constraints": "Input constraints (e.g., 1 <= n <= 1000)",
  "sample_input": "5",
  "sample_output": "120",
  "explanation": "Brief explanation of sample",
  "test_cases": [
    {{"input": "5", "output": "120", "is_hidden": false}},
    {{"input": "3", "output": "6", "is_hidden": false}},
    {{"input": "1", "output": "1", "is_hidden": true}},
    {{"input": "10", "output": "3628800", "is_hidden": true}},
    {{"input": "0", "output": "1", "is_hidden": true}}
  ],
  "starter_code": {{
    "python": "n = int(input())\\n# Your code here\\nprint(result)",
    "java": "import java.util.Scanner;\\nclass Solution {{\\n  public static void main(String[] args) {{\\n    Scanner sc = new Scanner(System.in);\\n    int n = sc.nextInt();\\n    // Your code here\\n    System.out.println(result);\\n  }}\\n}}",
    "cpp": "#include <iostream>\\nusing namespace std;\\nint main() {{\\n  int n;\\n  cin >> n;\\n  // Your code here\\n  cout << result;\\n  return 0;\\n}}",
    "javascript": "const readline = require('readline');\\nconst rl = readline.createInterface({{input: process.stdin}});\\nrl.on('line', (n) => {{\\n  // Your code here\\n  console.log(result);\\n}})",
    "c": "#include <stdio.h>\\nint main() {{\\n  int n;\\n  scanf(\\\"%d\\\", &n);\\n  // Your code here\\n  printf(\\\"%d\\\", result);\\n  return 0;\\n}}"
  }},
  "time_limit": 2,
  "memory_limit": 128
}}

Make the problem about: {topic}
Difficulty: {difficulty}
Include 5 test cases (2 visible, 3 hidden). Return ONLY the JSON."""
    
    try:
        print(f"Generating problem: topic={topic}, difficulty={difficulty}")
        response = generate_content(prompt, model='gemini')
        
        if not response:
            return {
                'success': False,
                'error': 'AI service did not return a response. Please try again.'
            }
        
        print(f"AI Response (first 300 chars): {response[:300]}")
        
        # Clean response - remove markdown code blocks if present
        cleaned_response = response.strip()
        if cleaned_response.startswith('```'):
            # Remove code block markers
            cleaned_response = re.sub(r'^```(?:json)?\s*', '', cleaned_response)
            cleaned_response = re.sub(r'\s*```$', '', cleaned_response)
        
        # Extract JSON from response
        json_match = re.search(r'\{[\s\S]*\}', cleaned_response)
        if json_match:
            json_str = json_match.group()
            print(f"Extracted JSON (first 200 chars): {json_str[:200]}")
            problem_data = json.loads(json_str)
            
            # Validate required fields
            required_fields = ['title', 'description', 'test_cases', 'starter_code']
            missing = [f for f in required_fields if f not in problem_data]
            if missing:
                return {
                    'success': False,
                    'error': f'AI response missing required fields: {", ".join(missing)}'
                }
            
            return {
                'success': True,
                'problem': problem_data
            }
        else:
            return {
                'success': False,
                'error': f'Could not find JSON in AI response. Response: {response[:300]}'
            }
            
    except json.JSONDecodeError as e:
        return {
            'success': False,
            'error': f'JSON parsing error: {e.msg} at line {e.lineno} column {e.colno}. Check if AI returned valid JSON.'
        }
    except Exception as e:
        import traceback
        print(f"Error generating problem: {traceback.format_exc()}")
        return {
            'success': False,
            'error': f'Generation failed: {str(e)}'
        }


def generate_friendly_error_message(error_message, source_code, language):
    """
    Convert compiler errors to friendly, casual hints using AI
    
    Args:
        error_message: Raw compiler error
        source_code: Student's code
        language: Programming language
    
    Returns:
        str: Friendly hint message
    """
    
    prompt = f"""
You are a friendly coding mentor helping a student debug their code. 

The student wrote this {language} code:
```{language}
{source_code}
```

They got this error:
```
{error_message}
```

Generate a CASUAL, FRIENDLY hint to help them fix it. Rules:
1. Be conversational and encouraging (like "Hey, check line 5 man" or "Looks like you forgot something on line 3 buddy")
2. Point to the specific line number if possible
3. Don't just repeat the error - explain what's wrong in simple terms
4. Give a hint about how to fix it, not the complete solution
5. Keep it under 100 words
6. Use emojis sparingly (1-2 max)
7. Be supportive - mistakes are part of learning!

Return ONLY the friendly message, nothing else.
"""
    
    try:
        hint = generate_content(prompt, model='gemini')
        return hint.strip()
    except:
        # Fallback if AI fails
        return "Hmm, something's not quite right with your code. Take a closer look at the error message and try debugging step by step! 🔍"


def analyze_code_quality(source_code, language, problem_description):
    """
    Provide AI feedback on code quality even if tests pass
    
    Args:
        source_code: Student's working code
        language: Programming language
        problem_description: Original problem
    
    Returns:
        dict: Code quality feedback
    """
    
    prompt = f"""
Analyze this {language} code for a student:

Problem: {problem_description}

Code:
```{language}
{source_code}
```

Provide brief feedback in JSON format:
{{
    "time_complexity": "O(n)",
    "space_complexity": "O(1)", 
    "code_quality": "good/average/needs_improvement",
    "suggestions": [
        "Brief suggestion 1",
        "Brief suggestion 2"
    ],
    "positive_points": [
        "What they did well"
    ]
}}

Keep it concise and encouraging. Return ONLY the JSON.
"""
    
    try:
        response = generate_content(prompt, model='gemini')
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            return json.loads(json_match.group())
        return None
    except:
        return None
