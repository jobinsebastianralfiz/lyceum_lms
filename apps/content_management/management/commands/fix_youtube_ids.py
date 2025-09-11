from django.core.management.base import BaseCommand
from apps.content_management.models import Testimonial


class Command(BaseCommand):
    help = 'Fix YouTube video IDs for testimonials with YouTube URLs'

    def handle(self, *args, **options):
        # Find testimonials with YouTube URLs but no video ID
        testimonials_to_fix = Testimonial.objects.filter(
            testimonial_type='video_youtube',
            youtube_url__isnull=False
        ).exclude(youtube_url='')
        
        self.stdout.write(f"Found {testimonials_to_fix.count()} YouTube testimonials to check")
        
        fixed_count = 0
        for testimonial in testimonials_to_fix:
            old_video_id = testimonial.youtube_video_id
            # Extract video ID using the method
            new_video_id = testimonial.extract_youtube_video_id(testimonial.youtube_url)
            
            if new_video_id and new_video_id != old_video_id:
                testimonial.youtube_video_id = new_video_id
                testimonial.save(update_fields=['youtube_video_id'])
                fixed_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Fixed testimonial {testimonial.id}: '{testimonial.student_name}' - "
                        f"extracted '{new_video_id}' from '{testimonial.youtube_url}'"
                    )
                )
            elif not new_video_id:
                self.stdout.write(
                    self.style.WARNING(
                        f"Could not extract video ID from testimonial {testimonial.id}: "
                        f"'{testimonial.youtube_url}'"
                    )
                )
            else:
                self.stdout.write(f"Testimonial {testimonial.id} already has correct video ID: {old_video_id}")
        
        self.stdout.write(
            self.style.SUCCESS(f"Fixed {fixed_count} testimonials")
        )