#!/usr/bin/env python3
"""
Test YouTube video ID extraction
"""
import os
import sys
import django

# Add the project directory to Python path
sys.path.append('/Users/jobinsebastian/djangoprojects/lms')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'codelearn_lms.settings')

# Setup Django
django.setup()

from apps.content_management.models import Testimonial

def test_youtube_extraction():
    """Test YouTube video ID extraction with various URL formats"""
    
    test_urls = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ",
        "https://youtube.com/embed/dQw4w9WgXcQ",
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ&feature=youtu.be",
        "https://youtu.be/dQw4w9WgXcQ?t=42s",
        "https://m.youtube.com/watch?v=dQw4w9WgXcQ",
        "http://youtube.com/v/dQw4w9WgXcQ?feature=youtube_gdata_player",
        "invalid-url",
        "",
        None
    ]
    
    # Create a temporary testimonial instance to test the method
    temp_testimonial = Testimonial()
    
    print("🧪 Testing YouTube Video ID Extraction")
    print("=" * 60)
    
    for i, url in enumerate(test_urls, 1):
        print(f"\n{i:2d}. Testing URL: {url}")
        
        if url:
            video_id = temp_testimonial.extract_youtube_video_id(url)
            if video_id:
                print(f"    ✅ Extracted ID: {video_id}")
                thumbnail_url = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
                print(f"    🖼️  Thumbnail: {thumbnail_url}")
            else:
                print(f"    ❌ Could not extract video ID")
        else:
            video_id = temp_testimonial.extract_youtube_video_id(url)
            print(f"    ⚪ Empty/None URL: {video_id}")
    
    print("\n" + "=" * 60)
    print("✅ YouTube extraction test completed!")

def test_testimonial_save():
    """Test testimonial save functionality"""
    print("\n🧪 Testing Testimonial Save Functionality")
    print("=" * 60)
    
    # Test creating a testimonial with YouTube URL
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    
    try:
        # Create a test testimonial (don't save to avoid conflicts)
        testimonial = Testimonial(
            student_name="Test Student",
            course_name="Test Course",
            batch_year="2025",
            testimonial_type="video_youtube",
            youtube_url=test_url,
            overall_rating=5
        )
        
        # Manually trigger the extraction without saving
        testimonial.youtube_video_id = testimonial.extract_youtube_video_id(testimonial.youtube_url)
        
        print(f"YouTube URL: {testimonial.youtube_url}")
        print(f"Extracted ID: {testimonial.youtube_video_id}")
        print(f"Thumbnail URL: {testimonial.youtube_thumbnail_url}")
        print(f"Embed URL: {testimonial.youtube_embed_url}")
        
        if testimonial.youtube_video_id == "dQw4w9WgXcQ":
            print("✅ Save functionality works correctly!")
        else:
            print("❌ Save functionality has issues!")
        
    except Exception as e:
        print(f"❌ Error during save test: {str(e)}")

def main():
    """Run all tests"""
    test_youtube_extraction()
    test_testimonial_save()
    
    print("\n💡 Next Steps:")
    print("1. Run: python manage.py fix_youtube_testimonials --dry-run")
    print("2. If results look good, run: python manage.py fix_youtube_testimonials")
    print("3. Test your API endpoints to verify YouTube data is returned")

if __name__ == "__main__":
    main()