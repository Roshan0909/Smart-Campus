# 🎯 Code Arena - Complete Teacher & Student Flow

## 📍 TEACHER WORKFLOW

### Step 1: Access Code Arena
**Location:** Teacher Sidebar → **"Code Arena"** (new menu item)
**URL:** `/teacher/coding/assignments/`

You'll see:
- 🤖 **Generate New Problem** button
- 📚 **My Problems Library** button  
- List of active assignments

---

### Step 2: Generate Problem with AI
**Click:** "Generate New Problem" or "My Problems Library" → "Create New Problem"
**URL:** `/teacher/coding/problems/create/`

**Form Fields:**
- **Subject:** Select your class/subject
- **Topic:** e.g., "Arrays", "Recursion", "Binary Search"
- **Difficulty:** Easy 🟢 / Medium 🟡 / Hard 🔴
- **Language:** Python, Java, C++, JavaScript, C

**Actions:**
- 👁️ **Preview AI Generation** - See what AI creates before saving
- ✅ **Generate & Save Problem** - Save to your library

**AI Generates:**
- Complete problem description
- Input constraints
- Sample input/output
- Explanation
- 5+ test cases (2 visible, 3 hidden)
- Starter code for ALL 5 languages

---

### Step 3: View Your Problems
**URL:** `/teacher/coding/problems/`

**Table Shows:**
| Title | Topic | Difficulty | Subject | Created | Status | Actions |
|-------|-------|------------|---------|---------|--------|---------|
| Find Max | Arrays | 🟢 Easy | CS101 | Dec 11 | Active | 📤 **Assign** 📝 Edit 📊 View 🗑️ Delete |

**Key Action:** Click **"Assign"** button to assign problem to students

---

### Step 4: Assign Problem to Students
**Click:** "Assign" button on any problem
**URL:** `/teacher/coding/problems/<id>/assign/`

**Form Fields:**
- **Assignment Title:** e.g., "Week 1 - Array Practice"
- **Subject/Class:** Select which class gets this assignment
- **Deadline:** Number of days from now (default: 7 days)
- **Instructions:** Optional additional notes for students

**Result:** Students in that subject can now see and solve this problem!

---

### Step 5: Monitor Submissions
**From Assignments List:** Click "View Submissions"
**URL:** `/teacher/coding/problems/<id>/submissions/`

**See:**
- Student names
- Submission status (✅ Accepted, ❌ Wrong Answer, ⚠️ Runtime Error)
- Score (0-100)
- Execution time & memory
- Code submitted
- AI-generated hints given

---

## 🎓 STUDENT WORKFLOW

### Step 1: Access Code Arena
**Location:** Student Sidebar → **"Code Arena"** (appears between Leaderboard and Knowledge Bot)
**URL:** `/student/coding/`

**Dashboard Shows:**
- 📊 Statistics: Total Assignments / Completed / Pending
- 🔍 Filters: All / Pending / Completed / Overdue
- 📝 List of assigned problems with:
  - Assignment title & description
  - Topic & difficulty badges
  - Deadline (with overdue warning)
  - Status: ✅ Completed / ⚠️ In Progress / ⭐ Not Started
  - **"Start"** or **"Continue"** button

---

### Step 2: Start Solving
**Click:** "Start" button on any assignment
**URL:** `/student/coding/assignment/<id>/`

**Split-Screen Layout:**

```
┌────────────────────────────┬─────────────────────────────┐
│  📄 PROBLEM PANEL (45%)    │  💻 EDITOR PANEL (55%)      │
├────────────────────────────┼─────────────────────────────┤
│ ▸ Problem Description      │ Language: [Python ▼]        │
│ ▸ Constraints              │ Time: 2s | Memory: 128MB    │
│ ▸ Sample Input/Output      │ ┌─────────────────────────┐ │
│ ▸ Test Cases (visible)     │ │ def solution():         │ │
│ ▸ Additional Instructions  │ │     # Write code here   │ │
│                            │ │     pass                │ │
│                            │ └─────────────────────────┘ │
│                            │ [▶️ Run Code] [✅ Submit]   │
│                            │ ─────────────────────────── │
│                            │ 📤 OUTPUT PANEL             │
│                            │ 💡 AI HINTS (if errors)     │
└────────────────────────────┴─────────────────────────────┘
```

---

### Step 3: Write Code
**Monaco Editor Features:**
- VS Code-style syntax highlighting
- Auto-completion
- Error detection
- Choose language: Python / Java / C++ / JavaScript / C
- Starter code provided for each language

---

### Step 4: Test Code
**Click:** ▶️ **Run Code** button

**What Happens:**
1. Prompts for custom input (optional)
2. Executes your code with that input
3. Shows output in Output Panel
4. If errors → AI generates **friendly hint**:

**Example:**
```
❌ Instead of: "SyntaxError: invalid syntax at line 5"
✅ You get: "Hey buddy, looks like you forgot a colon at the end 
   of line 5! Python needs that after the 'if' statement. 
   Give it another shot! 😊"
```

---

### Step 5: Submit Solution
**Click:** ✅ **Submit Solution** button

**What Happens:**
1. Confirms submission
2. Runs ALL test cases (visible + hidden)
3. Shows results:
   - ✅ **Test 1: Passed** (shows input/output for visible tests)
   - ✅ **Test 2: Passed**
   - ❌ **Test 3: Failed (Hidden)** (only shows pass/fail)
   - Score: 80/100
   - Status: Wrong Answer

4. If errors → AI gives specific hints:
   ```
   💡 AI Hint: "Check your loop on line 8, man. It looks like 
   you're going one index too far. Try using 'range(len(arr)-1)' 
   instead of 'range(len(arr))' to avoid that IndexError! 🔍"
   ```

5. If all passed → Congratulations message! 🎉

---

### Step 6: Iterate & Improve
- Fix code based on AI hints
- Re-run tests
- Submit again (unlimited attempts before deadline)
- Best score is saved

---

## 🎨 UI HIGHLIGHTS

### Teacher Side:
- **Code Arena Menu Item** - Quick access in sidebar
- **Assignments Dashboard** - See all assignments at a glance
- **AI Problem Generator** - One-click problem creation
- **Submission Analytics** - Track student progress

### Student Side:
- **Assignment Cards** - Clear deadlines & status
- **Split-Screen Editor** - Problem on left, code on right
- **Monaco Editor** - Professional code editing experience
- **AI Hints** - Friendly, casual error explanations
- **Real-time Testing** - Instant feedback

---

## 📋 QUICK REFERENCE

### Teacher URLs:
```
/teacher/coding/assignments/          → Main dashboard
/teacher/coding/problems/create/      → Generate problem
/teacher/coding/problems/             → Problems library
/teacher/coding/problems/<id>/assign/ → Assign problem
/teacher/coding/problems/<id>/submissions/ → View submissions
```

### Student URLs:
```
/student/coding/                      → Assignments dashboard
/student/coding/assignment/<id>/      → Solve problem
/student/coding/submissions/          → Submission history
/student/coding/leaderboard/          → Rankings
```

---

## 🚀 TO START USING:

1. **Run Migrations:**
   ```bash
   cd c:\projects\smart_campus\campus
   python manage.py makemigrations
   python manage.py migrate
   ```

2. **Get Judge0 API Key** (Free):
   - Visit: https://rapidapi.com/judge0-official/api/judge0-ce
   - Sign up for free tier (50 executions/day)
   - Copy API key
   - Paste in: `teachers/code_executor.py` line 48

3. **Login as Teacher:**
   - Go to "Code Arena" in sidebar
   - Click "Generate New Problem"
   - Fill form → Preview → Save
   - Click "Assign" → Select class → Set deadline
   - Done! Students can now access it

4. **Login as Student:**
   - Go to "Code Arena" in sidebar
   - See assigned problem
   - Click "Start"
   - Write code → Run/Submit
   - Get AI hints if errors

---

**Everything is ready! Just run migrations and add the Judge0 API key!** 🎉
