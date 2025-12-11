from django.db import models
from authentication.models import User
import json

class Subject(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subjects')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['name']

class PDFNote(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='notes')
    title = models.CharField(max_length=200)
    pdf_file = models.FileField(upload_to='notes/%Y/%m/%d/')  # Now supports PDF, DOC, DOCX, PPT, PPTX
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.title} - {self.subject.name}"
    
    def get_file_extension(self):
        return self.pdf_file.name.split('.')[-1].lower() if self.pdf_file else ''
    
    def get_file_icon(self):
        ext = self.get_file_extension()
        icons = {
            'pdf': 'bi-file-pdf',
            'doc': 'bi-file-word',
            'docx': 'bi-file-word',
            'ppt': 'bi-file-ppt',
            'pptx': 'bi-file-ppt',
        }
        return icons.get(ext, 'bi-file-earmark')
    
    class Meta:
        ordering = ['-created_at']

class Quiz(models.Model):
    title = models.CharField(max_length=200)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='quizzes')
    pdf_note = models.ForeignKey(PDFNote, on_delete=models.CASCADE, related_name='quizzes', null=True)
    description = models.TextField(blank=True)
    duration = models.IntegerField(help_text="Duration in minutes", default=30)
    num_questions = models.IntegerField(default=10)
    topics = models.TextField(blank=True, help_text="Comma-separated topics (optional)")
    difficulty = models.CharField(max_length=20, choices=[('easy', 'Easy'), ('medium', 'Medium'), ('hard', 'Hard')], default='medium')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_quizzes')
    created_at = models.DateTimeField(auto_now_add=True)
    deadline = models.DateTimeField(null=True, blank=True, help_text="Quiz deadline")
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.title} - {self.subject.name}"
    
    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Quizzes"

class Question(models.Model):
    QUESTION_TYPES = [
        ('multiple_choice', 'Multiple Choice'),
        ('true_false', 'True/False'),
        ('short_answer', 'Short Answer'),
    ]
    
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    text = models.TextField()
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES)
    options = models.JSONField(default=list, blank=True)  # For multiple choice/true-false
    correct_answer = models.TextField()  # Index for MC/TF, text for short answer
    points = models.IntegerField(default=1)
    order = models.IntegerField(default=0)
    
    def __str__(self):
        return f"{self.quiz.title} - Q{self.order}"
    
    class Meta:
        ordering = ['order']

class QuizAttempt(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='attempts')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='quiz_attempts')
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    score = models.IntegerField(null=True, blank=True)
    total_points = models.IntegerField(default=0)
    answers = models.JSONField(default=dict)  # Store student answers
    
    # Proctoring fields
    proctoring_violations = models.JSONField(default=list, blank=True)  # Store violation logs
    tab_switch_count = models.IntegerField(default=0)
    fullscreen_exit_count = models.IntegerField(default=0)
    
    def calculate_risk_score(self):
        """
        Calculate risk score based on violations, tab switches, and performance
        Returns: dict with risk_score (0-100), risk_level, risk_color, and details
        """
        risk_score = 0
        details = []
        
        # 1. Proctoring violations (max 40 points)
        violation_count = len(self.proctoring_violations) if self.proctoring_violations else 0
        if violation_count > 0:
            violation_risk = min(violation_count * 8, 40)  # 8 points per violation, max 40
            risk_score += violation_risk
            details.append(f"{violation_count} proctoring violation(s) (+{violation_risk} risk)")
        
        # 2. Tab switches (max 30 points)
        if self.tab_switch_count > 0:
            tab_risk = min(self.tab_switch_count * 5, 30)  # 5 points per switch, max 30
            risk_score += tab_risk
            details.append(f"{self.tab_switch_count} tab switch(es) (+{tab_risk} risk)")
        
        # 3. Fullscreen exits (max 20 points)
        if self.fullscreen_exit_count > 0:
            fullscreen_risk = min(self.fullscreen_exit_count * 4, 20)  # 4 points per exit, max 20
            risk_score += fullscreen_risk
            details.append(f"{self.fullscreen_exit_count} fullscreen exit(s) (+{fullscreen_risk} risk)")
        
        # 4. Performance anomaly (max 10 points)
        # Suspiciously high score with violations suggests cheating
        if self.score and self.total_points:
            percentage = (self.score / self.total_points) * 100
            if percentage >= 90 and (violation_count > 2 or self.tab_switch_count > 3):
                performance_risk = 10
                risk_score += performance_risk
                details.append(f"High score with violations (+{performance_risk} risk)")
        
        # Determine risk level and color
        if risk_score >= 50:
            risk_level = "HIGH RISK"
            risk_color = "#dc3545"  # Red
            risk_status = "UNFAIR"
        elif risk_score >= 25:
            risk_level = "MODERATE RISK"
            risk_color = "#fd7e14"  # Orange
            risk_status = "SUSPICIOUS"
        elif risk_score >= 10:
            risk_level = "LOW RISK"
            risk_color = "#ffc107"  # Yellow
            risk_status = "FAIR (Minor Issues)"
        else:
            risk_level = "MINIMAL RISK"
            risk_color = "#28a745"  # Green
            risk_status = "FAIR"
        
        return {
            'risk_score': min(risk_score, 100),  # Cap at 100
            'risk_level': risk_level,
            'risk_color': risk_color,
            'risk_status': risk_status,
            'details': details
        }
    
    def __str__(self):
        return f"{self.student.username} - {self.quiz.title}"
    
    class Meta:
        ordering = ['-started_at']


class ProctoringSnapshot(models.Model):
    """Store proctoring snapshots with violation details"""
    attempt = models.ForeignKey(QuizAttempt, on_delete=models.CASCADE, related_name='snapshots')
    image = models.ImageField(upload_to='proctoring/%Y/%m/%d/')
    violation_type = models.CharField(max_length=50)  # 'multiple_persons', 'no_person', 'phone_detected'
    person_count = models.IntegerField(default=0)
    phone_count = models.IntegerField(default=0)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.attempt.student.username} - {self.violation_type} at {self.timestamp}"
    
    class Meta:
        ordering = ['-timestamp']

class ChatMessage(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    message = models.TextField(blank=True)
    file = models.FileField(upload_to='chat_files/%Y/%m/%d/', null=True, blank=True)
    attached_note = models.ForeignKey(PDFNote, on_delete=models.SET_NULL, null=True, blank=True, related_name='chat_references')
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Message {self.id}"
    
    def is_image(self):
        if self.file:
            ext = self.file.name.split('.')[-1].lower()
            return ext in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp']
        return False
    
    def file_extension(self):
        if self.file:
            return self.file.name.split('.')[-1].lower()
        return None
    
    class Meta:
        ordering = ['created_at']
