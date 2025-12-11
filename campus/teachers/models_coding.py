from django.db import models
from authentication.models import User

class CodingProblem(models.Model):
    """AI-generated coding problems"""
    DIFFICULTY_CHOICES = [
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard'),
    ]
    
    LANGUAGE_CHOICES = [
        ('python', 'Python'),
        ('java', 'Java'),
        ('cpp', 'C++'),
        ('javascript', 'JavaScript'),
        ('c', 'C'),
    ]
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES)
    topic = models.CharField(max_length=100)
    subject = models.ForeignKey('teachers.Subject', on_delete=models.CASCADE, related_name='coding_problems', null=True, blank=True)
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_problems')
    
    # AI-generated content
    constraints = models.TextField(blank=True)
    sample_input = models.TextField(blank=True)
    sample_output = models.TextField(blank=True)
    explanation = models.TextField(blank=True)
    
    # Boilerplate code for each language
    starter_code_python = models.TextField(blank=True)
    starter_code_java = models.TextField(blank=True)
    starter_code_cpp = models.TextField(blank=True)
    starter_code_javascript = models.TextField(blank=True)
    starter_code_c = models.TextField(blank=True)
    
    # Metadata
    time_limit = models.IntegerField(default=2)  # seconds
    memory_limit = models.IntegerField(default=128)  # MB
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.title} ({self.difficulty})"
    
    class Meta:
        ordering = ['-created_at']


class CodingAssignment(models.Model):
    """Teacher assigns problems to students"""
    problem = models.ForeignKey(CodingProblem, on_delete=models.CASCADE, related_name='assignments')
    subject = models.ForeignKey('teachers.Subject', on_delete=models.CASCADE, related_name='coding_assignments', null=True, blank=True)
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name='coding_assignments')
    
    # Assignment details
    title = models.CharField(max_length=200, help_text="Assignment name for students")
    instructions = models.TextField(blank=True, help_text="Additional instructions")
    
    # Timing
    assigned_date = models.DateTimeField(auto_now_add=True)
    deadline = models.DateTimeField()
    
    # Visibility
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        subject_name = self.subject.name if self.subject else "General"
        return f"{self.title} - {subject_name}"
    
    class Meta:
        ordering = ['-assigned_date']


class TestCase(models.Model):
    """Test cases for problems"""
    problem = models.ForeignKey(CodingProblem, on_delete=models.CASCADE, related_name='test_cases')
    input_data = models.TextField()
    expected_output = models.TextField()
    is_hidden = models.BooleanField(default=False)  # Hidden test cases for evaluation
    points = models.IntegerField(default=10)
    
    def __str__(self):
        return f"Test case for {self.problem.title}"


class CodingSubmission(models.Model):
    """Student code submissions"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('wrong_answer', 'Wrong Answer'),
        ('runtime_error', 'Runtime Error'),
        ('time_limit', 'Time Limit Exceeded'),
        ('compilation_error', 'Compilation Error'),
    ]
    
    assignment = models.ForeignKey(CodingAssignment, on_delete=models.CASCADE, related_name='submissions', null=True, blank=True)
    problem = models.ForeignKey(CodingProblem, on_delete=models.CASCADE, related_name='submissions')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='code_submissions')
    language = models.CharField(max_length=20)
    source_code = models.TextField()
    
    # Results
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pending')
    score = models.IntegerField(default=0)
    execution_time = models.FloatField(null=True, blank=True)
    memory_used = models.FloatField(null=True, blank=True)
    
    # AI-generated feedback
    error_message = models.TextField(blank=True)
    friendly_hint = models.TextField(blank=True)  # AI-converted error explanation
    
    # Test case results
    test_cases_passed = models.IntegerField(default=0)
    test_cases_total = models.IntegerField(default=0)
    
    submitted_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.student.username} - {self.problem.title} ({self.status})"
    
    class Meta:
        ordering = ['-submitted_at']
