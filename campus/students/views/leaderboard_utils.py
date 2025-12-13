"""
Leaderboard utilities for calculating student rankings and generating AI suggestions
"""
import os
from dotenv import load_dotenv
from teachers.models import QuizAttempt

# Load .env from the campus directory
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(env_path)

API_KEY = os.getenv("API_KEY")
if not API_KEY:
    raise ValueError("API_KEY not found in environment variables. Please check your .env file at: " + env_path)

def get_leaderboard_data():
    """
    Calculate comprehensive leaderboard rankings based on multiple metrics
    """
    from authentication.models import User
    
    students = User.objects.filter(role='student')
    leaderboard = []
    
    for student in students:
        # Get quiz statistics
        attempts = QuizAttempt.objects.filter(
            student=student,
            completed_at__isnull=False
        )
        
        total_quizzes = attempts.count()
        if total_quizzes == 0:
            continue  # Skip students with no quiz attempts
        
        # Calculate metrics
        total_score = sum([attempt.score for attempt in attempts])
        total_possible = sum([attempt.total_points for attempt in attempts])
        
        avg_percentage = (total_score / total_possible * 100) if total_possible > 0 else 0
        
        # Count perfect scores
        perfect_scores = attempts.filter(score=total_possible).count()
        
        # Get recent performance (last 5 quizzes)
        recent_attempts = attempts.order_by('-completed_at')[:5]
        recent_avg = 0
        if recent_attempts.exists():
            recent_score = sum([a.score for a in recent_attempts])
            recent_possible = sum([a.total_points for a in recent_attempts])
            recent_avg = (recent_score / recent_possible * 100) if recent_possible > 0 else 0
        
        # Calculate engagement score (weighted combination)
        engagement_score = (
            avg_percentage * 0.5 +  # 50% weight on average score
            (perfect_scores / total_quizzes * 100) * 0.2 +  # 20% weight on perfect scores
            recent_avg * 0.2 +  # 20% weight on recent performance
            min(total_quizzes * 2, 10)  # 10% weight on participation (capped at 10 points)
        )
        
        leaderboard.append({
            'student': student,
            'total_quizzes': total_quizzes,
            'avg_percentage': round(avg_percentage, 2),
            'total_score': total_score,
            'total_possible': total_possible,
            'perfect_scores': perfect_scores,
            'recent_avg': round(recent_avg, 2),
            'engagement_score': round(engagement_score, 2)
        })
    
    # Sort by engagement score (highest first)
    leaderboard.sort(key=lambda x: x['engagement_score'], reverse=True)
    
    # Add rankings and badges
    for idx, entry in enumerate(leaderboard, 1):
        entry['rank'] = idx
        entry['badge'] = get_rank_badge(idx)
        entry['tier'] = get_tier(entry['engagement_score'])
    
    return leaderboard


def get_rank_badge(rank):
    """Get badge icon and color based on rank"""
    badges = {
        1: {'icon': '👑', 'name': 'Champion', 'color': '#FFD700'},
        2: {'icon': '🥈', 'name': 'Runner-up', 'color': '#C0C0C0'},
        3: {'icon': '🥉', 'name': 'Bronze Star', 'color': '#CD7F32'},
        4: {'icon': '🌟', 'name': '4th Place', 'color': '#9B59B6'},
        5: {'icon': '⭐', 'name': '5th Place', 'color': '#667eea'},
        6: {'icon': '💫', 'name': '6th Place', 'color': '#3498db'},
        7: {'icon': '✨', 'name': '7th Place', 'color': '#1abc9c'},
        8: {'icon': '🔥', 'name': '8th Place', 'color': '#e74c3c'},
        9: {'icon': '💎', 'name': '9th Place', 'color': '#00D9FF'},
        10: {'icon': '🏅', 'name': '10th Place', 'color': '#f39c12'},
    }
    
    if rank <= 10:
        return badges.get(rank, {'icon': '⭐', 'name': 'Top 10', 'color': '#667eea'})
    elif rank <= 20:
        return {'icon': '🎖️', 'name': f'{rank}th Place', 'color': '#95a5a6'}
    else:
        return {'icon': '🎯', 'name': f'{rank}th Place', 'color': '#7f8c8d'}


def get_tier(engagement_score):
    """Determine tier based on engagement score"""
    if engagement_score >= 85:
        return {'name': 'Diamond', 'color': '#00D9FF', 'icon': '💎'}
    elif engagement_score >= 70:
        return {'name': 'Platinum', 'color': '#E5E4E2', 'icon': '🌟'}
    elif engagement_score >= 55:
        return {'name': 'Gold', 'color': '#FFD700', 'icon': '⚡'}
    elif engagement_score >= 40:
        return {'name': 'Silver', 'color': '#C0C0C0', 'icon': '🔥'}
    elif engagement_score >= 25:
        return {'name': 'Bronze', 'color': '#CD7F32', 'icon': '📚'}
    else:
        return {'name': 'Beginner', 'color': '#95a5a6', 'icon': '🎓'}
