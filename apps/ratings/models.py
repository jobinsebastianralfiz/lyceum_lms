from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.courses.models import Course

User = get_user_model()


class CourseRating(models.Model):
    RATING_CHOICES = [
        (1, '1 Star'),
        (2, '2 Stars'),
        (3, '3 Stars'),
        (4, '4 Stars'),
        (5, '5 Stars'),
    ]
    
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='ratings')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='course_ratings')
    rating = models.IntegerField(
        choices=RATING_CHOICES,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    review_text = models.TextField(blank=True, null=True, help_text="Optional review text")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_approved = models.BooleanField(default=True, help_text="Admin can moderate reviews")
    
    class Meta:
        unique_together = ('course', 'user')
        ordering = ['-created_at']
        verbose_name = 'Course Rating'
        verbose_name_plural = 'Course Ratings'
    
    def __str__(self):
        return f"{self.user.username} - {self.course.title} ({self.rating} stars)"
    
    @property
    def star_display(self):
        return "★" * self.rating + "☆" * (5 - self.rating)


class CourseReview(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='course_reviews')
    title = models.CharField(max_length=200, help_text="Review title/summary")
    content = models.TextField(help_text="Detailed review content")
    rating = models.ForeignKey(CourseRating, on_delete=models.CASCADE, related_name='detailed_review')
    is_helpful_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_approved = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Course Review'
        verbose_name_plural = 'Course Reviews'
    
    def __str__(self):
        return f"{self.title} - {self.user.username}"


class ReviewHelpful(models.Model):
    review = models.ForeignKey(CourseReview, on_delete=models.CASCADE, related_name='helpful_votes')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    is_helpful = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('review', 'user')
        verbose_name = 'Review Helpfulness Vote'
        verbose_name_plural = 'Review Helpfulness Votes'
    
    def __str__(self):
        return f"{self.user.username} - {'Helpful' if self.is_helpful else 'Not Helpful'}"