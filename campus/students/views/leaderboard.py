"""
Student Leaderboard Views
Handles: Displaying competitive leaderboard and student rankings
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden


@login_required
def leaderboard(request):
    """Display creative leaderboard with student rankings"""
    if not request.user.is_student():
        return HttpResponseForbidden("You don't have permission to access this page.")
    
    from .leaderboard_utils import get_leaderboard_data
    
    # Get leaderboard data
    leaderboard_data = get_leaderboard_data()
    
    # Find current student's data
    current_student_data = None
    for entry in leaderboard_data:
        if entry['student'].id == request.user.id:
            current_student_data = entry
            break
    
    return render(request, 'students/leaderboard.html', {
        'leaderboard': leaderboard_data,
        'current_student_data': current_student_data,
        'total_students': len(leaderboard_data)
    })
