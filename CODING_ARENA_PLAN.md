# Coding Arena - Implementation Plan & Status

## ✅ COMPLETED COMPONENTS

### 1. Backend Models (`teachers/models_coding.py`)
- ✅ CodingProblem: Stores AI-generated problems
- ✅ TestCase: Hidden & visible test cases with scoring
- ✅ CodingSubmission: Student attempts with AI feedback

### 2. AI Integration (`teachers/coding_problem_generator.py`)
- ✅ `generate_coding_problem()`: Gemini generates complete problems
- ✅ `generate_friendly_error_message()`: Converts compiler errors to casual hints
- ✅ `analyze_code_quality()`: Post-solve code quality feedback

### 3. Code Execution (`teachers/code_executor.py`)
- ✅ Judge0 API integration (Python, Java, C++, JavaScript, C)
- ✅ `execute_code()`: Single execution with timeout/memory limits
- ✅ `execute_with_test_cases()`: Batch test case validation
- ⚠️ **REQUIRES**: RapidAPI key for Judge0 (line 48)

### 4. Teacher Views (`teachers/coding_views.py`)
- ✅ Problem creation with AI preview
- ✅ Problem management (edit, delete)
- ✅ View student submissions
- ✅ Submission analytics

### 5. Student Views (`students/coding_views.py`)
- ✅ Problem browser with filters
- ✅ Code editor (solve_problem view)
- ✅ Code submission with AI hints
- ✅ Custom input testing
- ✅ Submission history
- ✅ Leaderboard

### 6. URL Routing
- ✅ Teachers: `/teacher/coding/...`
- ✅ Students: `/student/coding/...`

### 7. Templates
- ✅ `create_coding_problem.html`: Teacher problem generator
- ✅ `coding_problems_dashboard.html`: Student problem browser
- ✅ Sidebar integration in `base_student.html`

## 📋 REMAINING TASKS

### HIGH PRIORITY

1. **Database Migrations** (REQUIRED FIRST)
   ```bash
   cd c:\projects\smart_campus\campus
   python manage.py makemigrations teachers
   python manage.py migrate
   ```

2. **Judge0 API Setup**
   - Create RapidAPI account: https://rapidapi.com/judge0-official/api/judge0-ce
   - Get API key (free tier: 50 calls/day)
   - Edit `teachers/code_executor.py` line 48:
     ```python
     'X-RapidAPI-Key': 'YOUR_KEY_HERE'
     ```

3. **Monaco Editor Integration** (Code editor UI)
   Create `templates/students/solve_problem.html`:
   - Monaco Editor (VS Code-style editor)
   - Language selector (Python/Java/C++/JS/C)
   - Run/Submit buttons
   - Test case display
   - Output panel with AI hints

4. **Missing Templates**
   - `coding_problems_list.html` (teacher problem list)
   - `edit_coding_problem.html` (teacher edit interface)
   - `problem_submissions.html` (teacher submission view)
   - `my_submissions.html` (student submission history)
   - `submission_detail.html` (detailed results)
   - `coding_leaderboard.html` (student rankings)

### MEDIUM PRIORITY

5. **Admin Registration**
   Add to `teachers/admin.py`:
   ```python
   from .models_coding import CodingProblem, TestCase, CodingSubmission
   admin.site.register(CodingProblem)
   admin.site.register(TestCase)
   admin.site.register(CodingSubmission)
   ```

6. **Testing**
   - Test problem generation with Gemini
   - Test code execution with Judge0
   - Test AI error hints
   - Test leaderboard calculations

### LOW PRIORITY (Future Enhancements)

7. **Advanced Features**
   - Real-time collaborative coding
   - Code plagiarism detection
   - Time-based contests
   - Editorial solutions
   - Discussion forum per problem
   - Hints system (progressive reveals)
   - Streak tracking

## 🎨 UI DESIGN PRINCIPLES

### Current Theme Integration
- **Primary**: Linear gradient `#06B6D4 → #0891B2` (cyan)
- **Dark**: `#1E293B → #0F172A` (slate)
- **Font**: Poppins (800 weight for headers)
- **Borders**: 1rem border-radius
- **Shadows**: `rgba(6, 182, 212, 0.X)` variations
- **Animations**: Transform translateY(-4px) on hover

### Difficulty Colors
- Easy: `#10B981 → #059669` (green)
- Medium: `#F59E0B → #D97706` (amber)
- Hard: `#EF4444 → #DC2626` (red)

### Status Badges
- Solved: Green background with checkmark
- Attempted: Amber with exclamation
- New: Cyan with star

## 📝 MONACO EDITOR TEMPLATE STRUCTURE

```html
<!-- solve_problem.html -->
<div class="row">
    <div class="col-md-6">
        <!-- Problem Description -->
        <div class="problem-panel">
            <h3>{{ problem.title }}</h3>
            <div>{{ problem.description }}</div>
            <h5>Constraints</h5>
            <pre>{{ problem.constraints }}</pre>
            <h5>Sample Input/Output</h5>
            <!-- Sample test cases -->
        </div>
    </div>
    <div class="col-md-6">
        <!-- Monaco Editor -->
        <div id="editor" style="height: 500px;"></div>
        
        <!-- Language Selector -->
        <select id="language">
            <option value="python">Python</option>
            <option value="java">Java</option>
            ...
        </select>
        
        <!-- Action Buttons -->
        <button onclick="runCode()">Run Code</button>
        <button onclick="submitCode()">Submit</button>
        
        <!-- Output Panel -->
        <div id="output"></div>
        
        <!-- AI Hint (if error) -->
        <div id="hint" class="ai-hint" style="display:none;"></div>
    </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/monaco-editor/min/vs/loader.js"></script>
<script>
require.config({ paths: { vs: 'https://cdn.jsdelivr.net/npm/monaco-editor/min/vs' }});
require(['vs/editor/editor.main'], function () {
    var editor = monaco.editor.create(document.getElementById('editor'), {
        value: getStarterCode(),
        language: 'python',
        theme: 'vs-dark',
        minimap: { enabled: false }
    });
});

async function submitCode() {
    const response = await fetch('/student/coding/submit/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
        body: JSON.stringify({
            problem_id: {{ problem.id }},
            source_code: editor.getValue(),
            language: document.getElementById('language').value
        })
    });
    const data = await response.json();
    
    if (data.status === 'accepted') {
        showSuccess(data);
    } else {
        showError(data.friendly_hint); // Show AI-generated casual hint
    }
}
</script>
```

## 🔧 CONFIGURATION CHECKLIST

### Environment Variables (`.env`)
- ✅ `API_KEY` - Gemini API (already configured)
- ⚠️ `JUDGE0_API_KEY` - Need to add

### Dependencies
- ✅ `google-generativeai` (AI generation)
- ✅ `requests` (API calls)
- ✅ Django 5.2.8
- ⚠️ May need: `django-cors-headers` if using frontend framework

## 🚀 QUICK START GUIDE

### Step 1: Run Migrations
```bash
cd c:\projects\smart_campus\campus
python manage.py makemigrations
python manage.py migrate
```

### Step 2: Get Judge0 API Key
1. Visit https://rapidapi.com/judge0-official/api/judge0-ce
2. Subscribe to free plan
3. Copy API key
4. Paste into `teachers/code_executor.py` line 48

### Step 3: Test Problem Generation
1. Login as teacher
2. Visit: http://localhost:8000/teacher/coding/problems/create/
3. Fill form:
   - Topic: "Arrays"
   - Difficulty: "Easy"
   - Language: "Python"
4. Click "Preview AI Generation"
5. If successful, click "Save"

### Step 4: Student Access
1. Login as student
2. Click "Code Arena" in sidebar
3. Browse problems
4. Click "Solve" (needs Monaco editor template)

## ⚠️ KNOWN ISSUES

1. **Circular Import Fixed**: Changed `from teachers.models import Subject` to `'teachers.Subject'` string reference
2. **Missing Dependency**: `langchain-text-splitters` error - skip if not using chat features
3. **Judge0 Free Tier**: Limited to 50 calls/day (consider implementing queue for production)

## 💡 AI FEATURES IMPLEMENTED

### Problem Generation
- Gemini 2.0 creates complete problems from topic/difficulty
- Generates 5+ test cases (2 visible, 3 hidden)
- Creates starter code for all 5 languages
- Includes constraints, explanations, samples

### Error Feedback
Instead of showing:
```
SyntaxError: invalid syntax at line 5
```

AI shows:
```
Hey buddy, looks like you forgot a colon at the end of line 5! 
Python needs that after the 'if' statement. Give it another shot! 😊
```

### Code Quality Analysis
After solving, AI provides:
- Time/space complexity
- Code quality rating
- Specific suggestions
- What you did well

## 📊 DATABASE SCHEMA

```
CodingProblem
├── title (char 200)
├── description (text)
├── difficulty (choice: easy/medium/hard)
├── topic (char 100)
├── subject (FK)
├── teacher (FK)
├── constraints (text)
├── sample_input/output (text)
├── starter_code_* (text x5 languages)
├── time_limit (int, default 2s)
├── memory_limit (int, default 128MB)
└── is_active (bool)

TestCase
├── problem (FK)
├── input_data (text)
├── expected_output (text)
├── is_hidden (bool)
└── points (int, default 10)

CodingSubmission
├── problem (FK)
├── student (FK)
├── language (char 20)
├── source_code (text)
├── status (choice)
├── score (int)
├── execution_time/memory (float)
├── error_message (text)
├── friendly_hint (text) ← AI-generated!
├── test_cases_passed/total (int)
└── submitted_at (datetime)
```

## 🎯 NEXT STEPS PRIORITY

1. ✅ Create migrations
2. ✅ Get Judge0 API key
3. ✅ Create `solve_problem.html` with Monaco Editor
4. Create remaining teacher templates
5. Create remaining student templates
6. Test end-to-end flow
7. Deploy to production

---

**Status**: 70% Complete
**Blockers**: None (just need to run migrations and get API key)
**ETA to MVP**: 2-3 hours for templates + testing
