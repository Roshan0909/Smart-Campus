# Quiz Risk Assessment Feature

## Overview
Added comprehensive risk assessment system to evaluate quiz attempts based on proctoring violations, tab switches, and performance metrics.

## Risk Scoring Algorithm (0-100 scale)

### Components:
1. **Proctoring Violations** (max 40 points)
   - 8 points per violation
   - Detects: multiple persons, no person, phone detected

2. **Tab Switches** (max 30 points)
   - 5 points per tab switch
   - Indicates potential cheating via external resources

3. **Fullscreen Exits** (max 20 points)
   - 4 points per exit
   - Shows attempts to access other applications

4. **Performance Anomaly** (max 10 points)
   - Triggered when: score ≥90% AND (violations >2 OR tab_switches >3)
   - Flags suspiciously high scores with integrity issues

## Risk Levels

| Score Range | Level | Color | Status | Interpretation |
|------------|-------|-------|---------|----------------|
| 0-9 | MINIMAL RISK | Green | FAIR | Clean test, no issues |
| 10-24 | LOW RISK | Yellow | FAIR (Minor Issues) | Some minor flags |
| 25-49 | MODERATE RISK | Orange | SUSPICIOUS | Significant concerns |
| 50-100 | HIGH RISK | Red | UNFAIR | Strong evidence of cheating |

## Implementation

### Backend (`teachers/models.py`)
- Added `calculate_risk_score()` method to `QuizAttempt` model
- Returns: risk_score, risk_level, risk_color, risk_status, details

### Teacher Reports (`teachers/reports_views.py`)
- Updated `filter_quiz_reports()` to include risk data in JSON response
- Risk metrics now visible in quiz reports table

### Student Report (`students/views.py`)
- Updated `quiz_report()` view to include risk assessment
- Students can see their integrity score

### Templates
1. **Teacher Reports** (`quiz_reports.html`)
   - Added 3 columns: Risk Assessment, Violations, Tab Switches
   - Color-coded badges for instant visual feedback
   - Risk score displayed as "LEVEL (score/100)"

2. **Student Report** (`quiz_report.html`)
   - New "Test Integrity Assessment" card
   - Circular progress indicator for risk score
   - Breakdown of violations, tab switches, fullscreen exits
   - Detailed risk factors list
   - Color-coded throughout based on risk level

## Usage Examples

### For Teachers:
- View all student attempts with risk scores in reports
- Filter/sort by risk level (future enhancement)
- Identify potential cheating cases instantly
- Export reports with risk data (PDF/Excel)

### For Students:
- See their integrity assessment after quiz completion
- Understand what factors contributed to risk score
- Self-assess test-taking behavior

## Benefits
✅ Automated cheating detection
✅ Objective scoring system
✅ Visual feedback for quick assessment
✅ Detailed breakdown for investigation
✅ Fair evaluation based on multiple factors
✅ Prevents false accusations with data-driven approach

## Future Enhancements
- Email alerts for HIGH RISK attempts
- Risk trends over time per student
- Customizable risk thresholds
- Integration with AI behavior analysis
- Automatic flagging for teacher review
