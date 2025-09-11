from django.core.management.base import BaseCommand
from apps.content_management.models import Testimonial
import re


class Command(BaseCommand):
    help = 'Fix YouTube video IDs for existing testimonials'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be fixed without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        # Find YouTube testimonials without video IDs
        youtube_testimonials = Testimonial.objects.filter(
            testimonial_type='video_youtube'
        )
        
        fixed_count = 0
        error_count = 0
        
        self.stdout.write(f"Found {youtube_testimonials.count()} YouTube testimonials")
        
        for testimonial in youtube_testimonials:
            self.stdout.write(f"\nProcessing: {testimonial.student_name} (ID: {testimonial.id})")
            self.stdout.write(f"  Current video ID: {testimonial.youtube_video_id}")
            self.stdout.write(f"  YouTube URL: {testimonial.youtube_url}")
            
            if testimonial.youtube_url and not testimonial.youtube_video_id:
                # Extract YouTube video ID using the model method
                video_id = testimonial.extract_youtube_video_id(testimonial.youtube_url)
                
                if video_id:
                    self.stdout.write(f"  ✅ Extracted video ID: {video_id}")
                    
                    if not dry_run:
                        testimonial.youtube_video_id = video_id
                        testimonial.save()
                        self.stdout.write(f"  💾 Updated testimonial {testimonial.id}")
                    else:
                        self.stdout.write(f"  🔍 Would update testimonial {testimonial.id}")
                    
                    fixed_count += 1
                else:
                    self.stdout.write(f"  ❌ Could not extract video ID from URL")
                    error_count += 1
                    
            elif testimonial.youtube_video_id:
                self.stdout.write(f"  ✅ Already has video ID: {testimonial.youtube_video_id}")
            else:
                self.stdout.write(f"  ⚠️  No YouTube URL provided")
                error_count += 1
        
        self.stdout.write(f"\n" + "="*50)
        if dry_run:
            self.stdout.write(f"DRY RUN COMPLETE:")
        else:
            self.stdout.write(f"FIX COMPLETE:")
            
        self.stdout.write(f"  ✅ Fixed: {fixed_count}")
        self.stdout.write(f"  ❌ Errors: {error_count}")
        
        if dry_run:
            self.stdout.write(f"\nRun without --dry-run to apply changes")
        else:
            self.stdout.write(f"\n✅ All changes saved successfully!")

    def extract_youtube_id_advanced(self, url):
        """Advanced YouTube ID extraction with multiple pattern support"""
        patterns = [
            r'(?:youtube\.com\/watch\?v=)([^&\n?#]+)',
            r'(?:youtu\.be\/)([^&\n?#]+)',
            r'(?:youtube\.com\/embed\/)([^&\n?#]+)',
            r'(?:youtube\.com\/v\/)([^&\n?#]+)',
            r'(?:youtube\.com\/user\/\S+\#p\/\w\/\w\/)([^&\n?#]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None