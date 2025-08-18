from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from apps.courses.models import Quiz, QuizAttempt
from apps.users.models import User


def is_staff_user(user):
    return user.is_authenticated and user.is_staff


@user_passes_test(is_staff_user)
def quiz_attempt_reset_view(request, quiz_id):
    """Reset quiz attempts for a specific quiz"""
    quiz = get_object_or_404(Quiz, id=quiz_id)
    
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        reset_type = request.POST.get('reset_type', 'all')
        
        if user_id and user_id != 'all':
            # Reset attempts for specific user
            user = get_object_or_404(User, id=user_id)
            
            if reset_type == 'incomplete_only':
                # Delete only incomplete attempts
                deleted_count = QuizAttempt.objects.filter(
                    quiz=quiz,
                    student=user,
                    completed=False
                ).delete()[0]
                action = f"incomplete attempts for {user.name or user.username}"
            else:
                # Delete all attempts for user
                deleted_count = QuizAttempt.objects.filter(
                    quiz=quiz,
                    student=user
                ).delete()[0]
                action = f"all attempts for {user.name or user.username}"
        else:
            # Reset attempts for all users
            if reset_type == 'incomplete_only':
                deleted_count = QuizAttempt.objects.filter(
                    quiz=quiz,
                    completed=False
                ).delete()[0]
                action = "all incomplete attempts"
            else:
                deleted_count = QuizAttempt.objects.filter(quiz=quiz).delete()[0]
                action = "all attempts"
        
        messages.success(request, f'Successfully reset {action} for quiz "{quiz.title}". {deleted_count} attempts removed.')
        return redirect('custom_admin:quiz_detail', quiz_id=quiz.id)
    
    # Get users who have attempted this quiz
    attempted_users = User.objects.filter(
        quiz_attempts__quiz=quiz
    ).distinct().order_by('name', 'username')
    
    # Get attempt counts
    attempt_counts = {}
    for user in attempted_users:
        total = QuizAttempt.objects.filter(quiz=quiz, student=user).count()
        incomplete = QuizAttempt.objects.filter(quiz=quiz, student=user, completed=False).count()
        completed = total - incomplete
        attempt_counts[user.id] = {
            'total': total,
            'completed': completed,
            'incomplete': incomplete
        }
    
    context = {
        'quiz': quiz,
        'attempted_users': attempted_users,
        'attempt_counts': attempt_counts,
    }
    
    return render(request, 'custom_admin/quizzes/reset_attempts.html', context)


@user_passes_test(is_staff_user)
def quiz_attempt_delete_view(request, attempt_id):
    """Delete a specific quiz attempt"""
    attempt = get_object_or_404(QuizAttempt, id=attempt_id)
    quiz_id = attempt.quiz.id
    
    if request.method == 'POST':
        student_name = attempt.student.name or attempt.student.username
        quiz_title = attempt.quiz.title
        attempt.delete()
        messages.success(request, f'Successfully deleted attempt by {student_name} for quiz "{quiz_title}".')
        return redirect('custom_admin:quiz_detail', quiz_id=quiz_id)
    
    return render(request, 'custom_admin/quiz_attempts/delete.html', {'attempt': attempt})