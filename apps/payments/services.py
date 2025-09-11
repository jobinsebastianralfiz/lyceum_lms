"""
Centralized service for enrollment checks across all services
This ensures consistent enrollment logic across Rating, Course, and other services
"""

from .models import Enrollment


class EnrollmentService:
    """
    Centralized service for enrollment-related operations
    Use this to ensure consistent enrollment checks across all services
    """
    
    @staticmethod
    def is_user_enrolled(user, course):
        """
        Check if user is enrolled in a course with access rights
        
        Args:
            user: User instance
            course: Course instance
            
        Returns:
            bool: True if user has enrollment access, False otherwise
        """
        if not user or not course:
            return False
            
        return Enrollment.objects.filter(
            user=user,
            course=course,
            active=True,
            payment_status__in=['completed', 'free']
        ).exists()
    
    @staticmethod
    def get_user_enrollment(user, course):
        """
        Get user's enrollment for a course if they have access
        
        Args:
            user: User instance
            course: Course instance
            
        Returns:
            Enrollment instance or None
        """
        if not user or not course:
            return None
            
        return Enrollment.objects.filter(
            user=user,
            course=course,
            active=True,
            payment_status__in=['completed', 'free']
        ).first()
    
    @staticmethod
    def get_user_enrollments(user):
        """
        Get all active enrollments for a user
        
        Args:
            user: User instance
            
        Returns:
            QuerySet of Enrollment instances
        """
        if not user:
            return Enrollment.objects.none()
            
        return Enrollment.objects.filter(
            user=user,
            active=True,
            payment_status__in=['completed', 'free']
        ).select_related('course')
    
    @staticmethod
    def can_access_premium_content(user, course):
        """
        Check if user can access premium content (paid courses)
        
        Args:
            user: User instance
            course: Course instance
            
        Returns:
            bool: True if user has premium access, False otherwise
        """
        if not user or not course:
            return False
            
        enrollment = Enrollment.objects.filter(
            user=user,
            course=course,
            active=True
        ).first()
        
        if not enrollment:
            return False
            
        # Free courses - everyone with enrollment has access
        if course.is_free or enrollment.payment_status == 'free':
            return True
            
        # Paid courses - must have completed payment
        return enrollment.payment_status == 'completed'
    
    @staticmethod
    def has_partial_payment(user, course):
        """
        Check if user has made partial payment for a course
        
        Args:
            user: User instance
            course: Course instance
            
        Returns:
            bool: True if user has partial payment, False otherwise
        """
        if not user or not course:
            return False
            
        return Enrollment.objects.filter(
            user=user,
            course=course,
            active=True,
            payment_status='partial'
        ).exists()
    
    @staticmethod
    def can_rate_course(user, course):
        """
        Check if user can rate a course (more flexible than enrollment check)
        Allows rating for:
        - Completed payments
        - Free courses
        - Partial payments (if they have some course access)
        
        Args:
            user: User instance
            course: Course instance
            
        Returns:
            bool: True if user can rate the course, False otherwise
        """
        if not user or not course:
            return False
            
        return Enrollment.objects.filter(
            user=user,
            course=course,
            active=True,
            payment_status__in=['completed', 'free', 'partial']  # Allow partial payments to rate
        ).exists()