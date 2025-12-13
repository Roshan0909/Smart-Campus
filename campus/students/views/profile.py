"""
Student Profile Views
Handles: Student profile management and personal information
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
from django.views.decorators.http import require_POST


@login_required
def student_profile(request):
    """View and edit student profile"""
    if not request.user.is_student():
        return HttpResponseForbidden("You don't have permission to access this page.")
    
    # Get or create student profile
    from students.models import StudentProfile
    profile, created = StudentProfile.objects.get_or_create(student=request.user)
    
    if request.method == 'POST':
        # Update profile
        profile.full_name = request.POST.get('full_name', '')
        profile.class_name = request.POST.get('class_name', '')
        profile.roll_number = request.POST.get('roll_number', '')
        profile.registration_number = request.POST.get('registration_number', '')
        profile.department = request.POST.get('department', '')
        profile.phone_number = request.POST.get('phone_number', '')
        profile.email_id = request.POST.get('email_id', '')
        profile.address = request.POST.get('address', '')
        
        profile.save()
        
        # Update user email if provided
        if request.POST.get('email_id'):
            request.user.email = request.POST.get('email_id')
            request.user.save()
        
        return JsonResponse({'success': True, 'message': 'Profile updated successfully'})
    
    return render(request, 'students/profile.html', {'profile': profile})
