from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Count, Avg, Sum, Q
from datetime import timedelta
from apps.users.models import User
from apps.courses.models import (
    StudentAnalytics, ProgressAlert, StudentProgress, 
    QuizAttempt, AssignmentSubmission, Course
)


class Command(BaseCommand):
    help = 'Update student analytics and generate alerts for mentoring'

    def add_arguments(self, parser):
        parser.add_argument(
            '--create-alerts', 
            action='store_true',
            help='Generate new alerts for at-risk students'
        )

    def handle(self, *args, **options):
        self.stdout.write('Starting analytics update...')
        
        students = User.objects.filter(role='student', is_active=True)
        alerts_created = 0
        
        for student in students:
            # Get or create analytics record
            analytics, created = StudentAnalytics.objects.get_or_create(
                student=student
            )
            
            if created:
                self.stdout.write(f'Created analytics for {student.name}')
            
            # Update engagement metrics
            self._update_engagement_metrics(student, analytics)
            
            # Update performance metrics
            self._update_performance_metrics(student, analytics)
            
            # Calculate risk score
            risk_score = analytics.calculate_risk_score()
            
            # Create alerts if requested and student needs mentoring
            if options['create_alerts'] and analytics.needs_mentoring:
                alert_created = self._create_alerts(student, analytics)
                if alert_created:
                    alerts_created += 1
            
            self.stdout.write(
                f'Updated {student.name}: Risk Level {analytics.risk_level} '
                f'(Score: {risk_score:.1f})'
            )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Analytics updated for {students.count()} students. '
                f'Created {alerts_created} new alerts.'
            )
        )

    def _update_engagement_metrics(self, student, analytics):
        """Update engagement-related metrics"""
        # Update last login
        analytics.last_login = student.last_login
        
        # Count total videos watched
        analytics.total_videos_watched = StudentProgress.objects.filter(
            user=student, completed=True
        ).count()
        
        # Count assignments submitted
        analytics.total_assignments_submitted = AssignmentSubmission.objects.filter(
            student=student
        ).exclude(status='draft').count()
        
        # Count quizzes attempted
        analytics.total_quizzes_attempted = QuizAttempt.objects.filter(
            student=student, completed=True
        ).count()
        
        analytics.save()

    def _update_performance_metrics(self, student, analytics):
        """Update performance-related metrics"""
        # Calculate average quiz score
        quiz_avg = QuizAttempt.objects.filter(
            student=student, completed=True
        ).aggregate(avg_score=Avg('score'))['avg_score']
        
        analytics.avg_quiz_score = quiz_avg or 0
        
        # Calculate average assignment score (assuming scores are stored)
        # This would need to be adjusted based on your assignment scoring system
        assignment_avg = AssignmentSubmission.objects.filter(
            student=student, status='graded'
        ).aggregate(avg_score=Avg('score'))['avg_score']
        
        analytics.avg_assignment_score = assignment_avg or 0
        
        # Count completed modules
        analytics.modules_completed = student.module_progress.filter(
            is_completed=True
        ).count()
        
        analytics.save()

    def _create_alerts(self, student, analytics):
        """Create alerts for at-risk students"""
        alert_created = False
        
        # Check for inactivity alert
        if analytics.last_login:
            days_inactive = (timezone.now() - analytics.last_login).days
            if days_inactive > 7:
                # Check if alert already exists
                if not ProgressAlert.objects.filter(
                    student=student,
                    alert_type='inactive',
                    is_resolved=False
                ).exists():
                    
                    first_enrollment = student.enrollments.filter(active=True).first()
                    course = first_enrollment.course if first_enrollment else None
                    
                    if course:
                        ProgressAlert.objects.create(
                            student=student,
                            course=course,
                            alert_type='inactive',
                            priority='high' if days_inactive > 14 else 'medium',
                            title=f'Student inactive for {days_inactive} days',
                            description=f'{student.name} has not logged in for {days_inactive} days. '
                                      f'Last login: {analytics.last_login.strftime("%Y-%m-%d")}'
                        )
                    alert_created = True
        
        # Check for poor performance alert
        if analytics.avg_quiz_score < 50:
            if not ProgressAlert.objects.filter(
                student=student,
                alert_type='poor_performance',
                is_resolved=False
            ).exists():
                
                first_enrollment = student.enrollments.filter(active=True).first()
                course = first_enrollment.course if first_enrollment else None
                
                if course:
                    ProgressAlert.objects.create(
                        student=student,
                        course=course,
                        alert_type='poor_performance',
                        priority='high',
                        title='Poor quiz performance',
                        description=f'{student.name} has an average quiz score of {analytics.avg_quiz_score:.1f}%. '
                                  'Immediate intervention recommended.'
                    )
                alert_created = True
        
        return alert_created