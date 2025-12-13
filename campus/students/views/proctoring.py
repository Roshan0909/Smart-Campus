"""
Student Proctoring Views
Handles: Proctoring snapshots during quiz taking
"""
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import json
import base64


@login_required
@require_POST
def save_proctoring_snapshot(request, attempt_id):
    """Save proctoring snapshot with violation details"""
    print(f"📸 Proctoring snapshot request received for attempt {attempt_id}")
    print(f"User: {request.user}, Method: {request.method}")
    
    if not request.user.is_student():
        print("❌ Permission denied - user is not a student")
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    try:
        from teachers.models import QuizAttempt, ProctoringSnapshot
        from django.core.files.base import ContentFile
        from django.shortcuts import get_object_or_404
        
        # Get the quiz attempt
        attempt = get_object_or_404(QuizAttempt, id=attempt_id, student=request.user)
        print(f"✓ Found attempt: {attempt.id} for quiz: {attempt.quiz.title}")
        
        # Parse the request data
        data = json.loads(request.body)
        image_data = data.get('image')  # Base64 image
        violation_type = data.get('violation_type')
        person_count = data.get('person_count', 0)
        phone_count = data.get('phone_count', 0)
        
        print(f"📊 Violation data: type={violation_type}, persons={person_count}, phones={phone_count}")
        
        if not image_data or not violation_type:
            print("❌ Missing required data")
            return JsonResponse({'error': 'Missing required data'}, status=400)
        
        # Decode base64 image
        format, imgstr = image_data.split(';base64,')
        ext = format.split('/')[-1]
        image_file = ContentFile(base64.b64decode(imgstr), name=f'snapshot_{attempt.id}_{violation_type}.{ext}')
        
        print(f"📷 Creating snapshot in database...")
        # Save snapshot
        snapshot = ProctoringSnapshot.objects.create(
            attempt=attempt,
            image=image_file,
            violation_type=violation_type,
            person_count=person_count,
            phone_count=phone_count
        )
        print(f"✓ Snapshot saved with ID: {snapshot.id}, image path: {snapshot.image.url}")
        
        # Update attempt violation log
        violation_log = {
            'type': violation_type,
            'timestamp': snapshot.timestamp.isoformat(),
            'person_count': person_count,
            'phone_count': phone_count
        }
        
        attempt.proctoring_violations.append(violation_log)
        attempt.save()
        
        print(f"✅ Successfully saved proctoring snapshot for attempt {attempt.id}")
        print(f"Total violations for this attempt: {len(attempt.proctoring_violations)}")
        
        return JsonResponse({
            'success': True,
            'snapshot_id': snapshot.id,
            'message': 'Snapshot saved successfully'
        })
        
    except Exception as e:
        print(f"❌ ERROR saving snapshot: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)
