from django import forms
from .models import CourseRating, CourseReview


class CourseRatingForm(forms.ModelForm):
    class Meta:
        model = CourseRating
        fields = ['rating', 'review_text']
        widgets = {
            'rating': forms.Select(
                attrs={
                    'class': 'form-select',
                    'required': True
                }
            ),
            'review_text': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Share your thoughts about this course (optional)...'
                }
            )
        }
        labels = {
            'rating': 'Your Rating',
            'review_text': 'Your Review'
        }
        help_texts = {
            'rating': 'Rate this course from 1 to 5 stars',
            'review_text': 'Optional: Write a detailed review to help other students'
        }


class CourseReviewForm(forms.ModelForm):
    class Meta:
        model = CourseReview
        fields = ['title', 'content']
        widgets = {
            'title': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Review title (e.g., "Great course for beginners")',
                    'maxlength': 200
                }
            ),
            'content': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 6,
                    'placeholder': 'Write a detailed review about your experience with this course...'
                }
            )
        }
        labels = {
            'title': 'Review Title',
            'content': 'Detailed Review'
        }
        help_texts = {
            'title': 'A short, descriptive title for your review',
            'content': 'Share your detailed experience with this course'
        }


class RatingFilterForm(forms.Form):
    RATING_FILTER_CHOICES = [
        ('all', 'All Ratings'),
        ('5', '5 Stars'),
        ('4', '4 Stars'),
        ('3', '3 Stars'),
        ('2', '2 Stars'),
        ('1', '1 Star'),
    ]
    
    SORT_CHOICES = [
        ('newest', 'Newest First'),
        ('oldest', 'Oldest First'),
        ('highest_rating', 'Highest Rating'),
        ('lowest_rating', 'Lowest Rating'),
        ('most_helpful', 'Most Helpful'),
    ]
    
    rating_filter = forms.ChoiceField(
        choices=RATING_FILTER_CHOICES,
        required=False,
        initial='all',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    sort_by = forms.ChoiceField(
        choices=SORT_CHOICES,
        required=False,
        initial='newest',
        widget=forms.Select(attrs={'class': 'form-select'})
    )