"""
Reports module for teachers - Generate and filter quiz reports with PDF export
"""
from django.db.models import Q, Count, Avg, Max, Min
from teachers.models import Quiz, QuizAttempt, Question
from django.utils import timezone
from datetime import timedelta
from io import BytesIO
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import json


class QuizReportFilter:
    """Handle filtering of quiz reports based on various criteria"""
    
    def __init__(self, teacher):
        self.teacher = teacher
        self.filters = {}
    
    def set_search_filter(self, search_text):
        """Search in quiz title or student name"""
        self.filters['search'] = search_text
        return self

    def set_quiz_filter(self, quiz_id):
        self.filters['quiz_id'] = quiz_id
        return self

    def set_subject_filter(self, subject_id):
        self.filters['subject_id'] = subject_id
        return self

    def set_student_filter(self, student_id):
        self.filters['student_id'] = student_id
        return self

    def set_difficulty_filter(self, difficulty):
        self.filters['difficulty'] = difficulty
        return self

    def set_date_range_filter(self, start_date, end_date):
        if start_date:
            self.filters['start_date'] = start_date
        if end_date:
            self.filters['end_date'] = end_date
        return self

    def set_score_range_filter(self, min_score, max_score):
        self.filters['min_score'] = min_score
        self.filters['max_score'] = max_score
        return self
    
    def get_attempts(self):
        """Get filtered quiz attempts"""
        query = QuizAttempt.objects.filter(quiz__created_by=self.teacher).select_related(
            'quiz', 'student'
        ).prefetch_related('quiz__questions')
        
        # Apply filters
        if 'quiz_id' in self.filters:
            query = query.filter(quiz_id=self.filters['quiz_id'])
        
        if 'subject_id' in self.filters:
            query = query.filter(quiz__subject_id=self.filters['subject_id'])
        
        if 'student_id' in self.filters:
            query = query.filter(student_id=self.filters['student_id'])
        
        if 'completed_only' in self.filters and self.filters['completed_only']:
            query = query.filter(completed_at__isnull=False)
        
        if 'difficulty' in self.filters:
            query = query.filter(quiz__difficulty=self.filters['difficulty'])
        
        if 'start_date' in self.filters and self.filters['start_date']:
            query = query.filter(completed_at__gte=self.filters['start_date'])
        
        if 'end_date' in self.filters and self.filters['end_date']:
            end_date = self.filters['end_date']
            # Include entire day
            end_date_end = end_date.replace(hour=23, minute=59, second=59)
            query = query.filter(completed_at__lte=end_date_end)
        
        if 'min_score' in self.filters and self.filters['min_score'] is not None:
            query = query.filter(score__gte=self.filters['min_score'])
        
        if 'max_score' in self.filters and self.filters['max_score'] is not None:
            query = query.filter(score__lte=self.filters['max_score'])
        
        if 'search' in self.filters and self.filters['search']:
            search_text = self.filters['search']
            query = query.filter(
                Q(quiz__title__icontains=search_text) |
                Q(student__username__icontains=search_text) |
                Q(student__first_name__icontains=search_text) |
                Q(student__last_name__icontains=search_text)
            )
        
        return query.order_by('-completed_at')
    
    def get_statistics(self):
        """Get aggregate statistics for filtered data"""
        attempts = self.get_attempts()
        completed_attempts = attempts.filter(completed_at__isnull=False)
        
        stats = {
            'total_attempts': attempts.count(),
            'completed_attempts': completed_attempts.count(),
            'avg_score': None,
            'max_score': None,
            'min_score': None,
            'avg_percentage': None,
            'unique_students': attempts.values('student').distinct().count(),
            'total_quizzes': attempts.values('quiz').distinct().count(),
        }
        
        if completed_attempts.exists():
            agg = completed_attempts.aggregate(
                avg_score=Avg('score'),
                max_score=Max('score'),
                min_score=Min('score'),
                avg_total=Avg('total_points')
            )
            stats['avg_score'] = round(agg['avg_score'], 2) if agg['avg_score'] else 0
            stats['max_score'] = agg['max_score']
            stats['min_score'] = agg['min_score']
            
            # Only calculate percentage if both values are available
            if agg['avg_score'] and agg['avg_total'] and agg['avg_total'] > 0:
                stats['avg_percentage'] = round((agg['avg_score'] / agg['avg_total']) * 100, 2)
            else:
                stats['avg_percentage'] = 0
        
        return stats


class QuizReportGenerator:
    """Generate detailed PDF reports from filtered quiz data"""
    
    def __init__(self, filter_obj, risk_filter=None):
        self.filter_obj = filter_obj
        self.risk_filter = risk_filter
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Setup custom ReportLab styles"""
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor('#06B6D4'),
            spaceAfter=12,
            alignment=TA_CENTER
        ))
        
        self.styles.add(ParagraphStyle(
            name='CustomHeading',
            parent=self.styles['Heading2'],
            fontSize=12,
            textColor=colors.HexColor('#0891b2'),
            spaceAfter=8
        ))
        
        self.styles.add(ParagraphStyle(
            name='CustomNormal',
            parent=self.styles['Normal'],
            fontSize=9,
            alignment=TA_LEFT
        ))
        
        self.styles.add(ParagraphStyle(
            name='CenterAlign',
            parent=self.styles['Normal'],
            fontSize=7,
            alignment=TA_CENTER,
            leading=9
        ))
        
        self.styles.add(ParagraphStyle(
            name='SmallText',
            parent=self.styles['Normal'],
            fontSize=7,
            alignment=TA_LEFT,
            leading=9
        ))
    
    def generate_pdf(self, filename=None):
        """Generate PDF report"""
        if filename is None:
            filename = f"quiz_report_{timezone.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        pdf_buffer = BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.7*inch, leftMargin=0.5*inch, rightMargin=0.5*inch)
        elements = []
        
        # Title
        title = Paragraph("📊 Quiz Performance Report", self.styles['CustomTitle'])
        elements.append(title)
        elements.append(Spacer(1, 0.15*inch))
        
        # Generate timestamp
        timestamp = Paragraph(
            f"<b>Report Generated:</b> {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}",
            self.styles['Normal']
        )
        elements.append(timestamp)
        elements.append(Spacer(1, 0.25*inch))
        
        # Statistics Section
        stats = self.filter_obj.get_statistics()
        elements.extend(self._build_statistics_section(stats))
        elements.append(Spacer(1, 0.25*inch))
        
        # Detailed Attempts Table
        elements.extend(self._build_attempts_table())
        
        # Build PDF
        doc.build(elements)
        pdf_buffer.seek(0)
        return pdf_buffer, filename
    
    def _build_statistics_section(self, stats):
        """Build statistics summary section"""
        elements = []
        
        elements.append(Paragraph("📈 Summary Statistics", self.styles['CustomHeading']))
        elements.append(Spacer(1, 0.15*inch))
        
        # Calculate risk statistics on filtered attempts
        attempts = list(self.filter_obj.get_attempts())
        
        # Apply risk filter if specified
        if self.risk_filter:
            filtered_attempts = []
            for attempt in attempts:
                risk_score = attempt.calculate_risk_score()['risk_score']
                if self.risk_filter == 'accept' and risk_score < 25:
                    filtered_attempts.append(attempt)
                elif self.risk_filter == 'review' and 25 <= risk_score < 50:
                    filtered_attempts.append(attempt)
                elif self.risk_filter == 'reject' and risk_score >= 50:
                    filtered_attempts.append(attempt)
            attempts = filtered_attempts
        
        risk_scores = [a.calculate_risk_score()['risk_score'] for a in attempts if a.completed_at]
        high_risk_count = sum(1 for score in risk_scores if score >= 50)
        moderate_risk_count = sum(1 for score in risk_scores if 25 <= score < 50)
        low_risk_count = sum(1 for score in risk_scores if 10 <= score < 25)
        fair_count = sum(1 for score in risk_scores if score < 10)
        total_violations = sum(len(a.proctoring_violations) if a.proctoring_violations else 0 for a in attempts)
        total_tab_switches = sum(a.tab_switch_count for a in attempts)
        max_risk = max(risk_scores) if risk_scores else 0
        min_risk = min(risk_scores) if risk_scores else 0
        avg_risk = round(sum(risk_scores) / len(risk_scores), 2) if risk_scores else 0
        
        # Recalculate stats for filtered attempts
        completed_attempts = [a for a in attempts if a.completed_at]
        total_attempts_count = len(attempts)
        completed_count = len(completed_attempts)
        unique_students = len(set(a.student_id for a in attempts))
        unique_quizzes = len(set(a.quiz_id for a in attempts))
        
        if completed_attempts:
            avg_score = round(sum(a.score for a in completed_attempts if a.score) / len(completed_attempts), 2)
            scores = [a.score for a in completed_attempts if a.score and a.total_points]
            totals = [a.total_points for a in completed_attempts if a.score and a.total_points]
            avg_percentage = round(sum((s/t*100) for s, t in zip(scores, totals)) / len(scores), 2) if scores else 0
            max_score = max(a.score for a in completed_attempts if a.score)
            min_score = min(a.score for a in completed_attempts if a.score)
        else:
            avg_score = 0
            avg_percentage = 0
            max_score = 0
            min_score = 0
        
        # Build stats rows with optional colors for values (no HTML font tags)
        stats_rows = [
            ('<b>Metric</b>', '<b>Value</b>', None),
            ('Total Attempts', str(total_attempts_count), None),
            ('Completed Attempts', str(completed_count), None),
            ('Unique Students', str(unique_students), None),
            ('Total Quizzes', str(unique_quizzes), None),
            ('Average Score', f"{avg_score} pts", None),
            ('Average Percentage', f"{avg_percentage}%", None),
            ('Highest Score', str(max_score), None),
            ('Lowest Score', str(min_score), None),
            ('<b>--- Risk Assessment ---</b>', '', None),
            ('Fair Attempts', str(fair_count), colors.HexColor('#28a745')),
            ('Low Risk Attempts', str(low_risk_count), colors.HexColor('#ffc107')),
            ('Moderate Risk Attempts', str(moderate_risk_count), colors.HexColor('#fd7e14')),
            ('High Risk (Unfair) Attempts', str(high_risk_count), colors.HexColor('#dc3545')),
            ('Average Risk Score', str(avg_risk), None),
            ('Maximum Risk Score', str(max_risk), colors.HexColor('#dc3545')),
            ('Minimum Risk Score', str(min_risk), colors.HexColor('#28a745')),
            ('Total Violations', str(total_violations), colors.HexColor('#dc3545')),
            ('Total Tab Switches', str(total_tab_switches), colors.HexColor('#ffc107')),
        ]

        stats_data = [[label, value] for label, value, _ in stats_rows]

        stats_table = Table(stats_data, colWidths=[3.5*inch, 2*inch])
        table_style = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#06B6D4')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 14),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f0fbff')),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#cffafe')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0fbff')]),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('TOPPADDING', (0, 1), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 10),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]

        # Apply per-row value colors
        for idx, (_, _, color_val) in enumerate(stats_rows):
            if color_val:
                table_style.append(('TEXTCOLOR', (1, idx), (1, idx), color_val))

        stats_table.setStyle(TableStyle(table_style))
        
        elements.append(stats_table)
        return elements
    
    def _build_attempts_table(self):
        """Build detailed attempts table with proper formatting"""
        elements = []
        
        elements.append(Spacer(1, 0.2*inch))
        elements.append(Paragraph("📋 Detailed Attempt Records", self.styles['CustomHeading']))
        elements.append(Spacer(1, 0.15*inch))
        
        attempts = list(self.filter_obj.get_attempts())
        
        # Apply risk filter if specified
        if self.risk_filter:
            filtered_attempts = []
            for attempt in attempts:
                risk_score = attempt.calculate_risk_score()['risk_score']
                if self.risk_filter == 'accept' and risk_score < 25:
                    filtered_attempts.append(attempt)
                elif self.risk_filter == 'review' and 25 <= risk_score < 50:
                    filtered_attempts.append(attempt)
                elif self.risk_filter == 'reject' and risk_score >= 50:
                    filtered_attempts.append(attempt)
            attempts = filtered_attempts
        
        # Create table data using Paragraph objects for proper rendering
        header = [
            Paragraph('<b>Quiz Title</b>', self.styles['Normal']),
            Paragraph('<b>Student</b>', self.styles['Normal']),
            Paragraph('<b>Score</b>', self.styles['CenterAlign']),
            Paragraph('<b>%</b>', self.styles['CenterAlign']),
            Paragraph('<b>Risk</b>', self.styles['CenterAlign']),
            Paragraph('<b>Status</b>', self.styles['CenterAlign']),
            Paragraph('<b>Viol</b>', self.styles['CenterAlign']),
            Paragraph('<b>Tabs</b>', self.styles['CenterAlign']),
            Paragraph('<b>Date</b>', self.styles['CenterAlign']),
        ]
        
        table_data = [header]
        
        for attempt in attempts:
            score = attempt.score if attempt.score else 0
            total = attempt.total_points if attempt.total_points else 0
            percentage = round((score / total * 100), 2) if total and total > 0 else 0
            
            # Get student name - fallback to username if first/last names are empty
            student_name = attempt.student.get_full_name().strip() if attempt.student.get_full_name() else attempt.student.username
            if not student_name or student_name.isspace():
                student_name = attempt.student.username
            
            # Calculate risk assessment
            risk_data = attempt.calculate_risk_score()
            violation_count = len(attempt.proctoring_violations) if attempt.proctoring_violations else 0
            
            # Determine status recommendation
            if risk_data['risk_score'] >= 50:
                status = '<font color="#dc3545"><b>REJECT</b></font>'
            elif risk_data['risk_score'] >= 25:
                status = '<font color="#fd7e14"><b>REVIEW</b></font>'
            else:
                status = '<font color="#28a745"><b>ACCEPT</b></font>'
            
            row = [
                Paragraph(str(attempt.quiz.title)[:18], self.styles['SmallText']),
                Paragraph(str(student_name)[:20], self.styles['SmallText']),
                Paragraph(f"{score}/{total}", self.styles['CenterAlign']),
                Paragraph(f"{percentage}%", self.styles['CenterAlign']),
                Paragraph(f'<font color="{risk_data["risk_color"]}"><b>{risk_data["risk_score"]}</b></font>', self.styles['CenterAlign']),
                Paragraph(status.replace('<b>', '').replace('</b>', ''), self.styles['CenterAlign']),
                Paragraph(str(violation_count), self.styles['CenterAlign']),
                Paragraph(str(attempt.tab_switch_count), self.styles['CenterAlign']),
                Paragraph(attempt.completed_at.strftime('%d/%m') if attempt.completed_at else '-', self.styles['CenterAlign']),
            ]
            table_data.append(row)
        
        if len(table_data) > 1:
            # Widen percentage and risk columns for better readability in PDF
            attempts_table = Table(table_data, colWidths=[1.1*inch, 1.1*inch, 0.55*inch, 0.55*inch, 0.55*inch, 0.7*inch, 0.4*inch, 0.4*inch, 0.6*inch])
            attempts_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0891b2')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (1, -1), 'LEFT'),
                ('ALIGN', (2, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 8),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                ('TOPPADDING', (0, 0), (-1, 0), 6),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d1d5db')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')]),
                ('FONTSIZE', (0, 1), (-1, -1), 7),
                ('TOPPADDING', (0, 1), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
                ('LEFTPADDING', (0, 0), (-1, -1), 4),
                ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ]))
            elements.append(attempts_table)
            
            # Add summary at bottom
            elements.append(Spacer(1, 0.15*inch))
            summary_text = f"<i>Total Records: <b>{len(attempts)}</b></i>"
            elements.append(Paragraph(summary_text, self.styles['Normal']))
        else:
            elements.append(Paragraph("<i>No data available for the selected filters.</i>", self.styles['Normal']))
        
        return elements


class QuizAnalytics:
    """Analyze quiz performance and generate insights"""
    
    @staticmethod
    def get_performance_by_question(quiz_id):
        """Get performance metrics for each question in a quiz"""
        quiz = Quiz.objects.get(id=quiz_id)
        questions = quiz.questions.all()
        
        performance_data = []
        
        for question in questions:
            attempts = QuizAttempt.objects.filter(
                quiz=quiz,
                completed_at__isnull=False
            )
            
            correct_count = 0
            for attempt in attempts:
                student_answer = attempt.answers.get(str(question.id))
                if student_answer == question.correct_answer:
                    correct_count += 1
            
            total_attempts = attempts.count()
            success_rate = (correct_count / total_attempts * 100) if total_attempts > 0 else 0
            
            performance_data.append({
                'question_id': question.id,
                'question_text': question.text[:50],
                'correct_answers': correct_count,
                'total_attempts': total_attempts,
                'success_rate': round(success_rate, 2),
                'difficulty': 'Easy' if success_rate > 80 else 'Medium' if success_rate > 50 else 'Hard'
            })
        
        return performance_data
    
    @staticmethod
    def get_student_progress(student_id, quiz_ids=None):
        """Get student progress across quizzes"""
        query = QuizAttempt.objects.filter(
            student_id=student_id,
            completed_at__isnull=False
        ).select_related('quiz').order_by('completed_at')
        
        if quiz_ids:
            query = query.filter(quiz_id__in=quiz_ids)
        
        progress_data = []
        for attempt in query:
            score = attempt.score if attempt.score else 0
            total = attempt.total_points if attempt.total_points else 0
            percentage = (score / total * 100) if total and total > 0 else 0
            progress_data.append({
                'quiz_title': attempt.quiz.title,
                'score': score,
                'total': total,
                'percentage': round(percentage, 2),
                'completed_at': attempt.completed_at,
                'time_taken_minutes': int((attempt.completed_at - attempt.started_at).total_seconds() / 60) if (attempt.completed_at and attempt.started_at) else 0
            })
        
        return progress_data
