import re
import requests
from urllib.parse import urlparse, parse_qs
from django.conf import settings
from typing import Dict, Optional, Tuple


class VideoIntegrationService:
    """
    Service to handle video metadata fetching from YouTube and Vimeo APIs
    """
    
    @staticmethod
    def extract_video_info(url: str) -> Tuple[str, str, Optional[str]]:
        """
        Extract platform, video_id, and normalized URL from video URL
        Returns: (platform, video_id, normalized_url)
        """
        if not url:
            return None, None, None
            
        url = url.strip()
        
        # YouTube patterns
        youtube_patterns = [
            r'(?:youtube\.com/watch\?v=)([^&\n?#]+)',
            r'(?:youtu\.be/)([^&\n?#]+)',
            r'(?:youtube\.com/embed/)([^&\n?#]+)',
            r'(?:youtube\.com/v/)([^&\n?#]+)',
            r'(?:youtube\.com/shorts/)([^&\n?#]+)',
        ]
        
        for pattern in youtube_patterns:
            match = re.search(pattern, url)
            if match:
                video_id = match.group(1).split('&')[0]  # Remove any extra params
                normalized_url = f"https://www.youtube.com/watch?v={video_id}"
                return 'youtube', video_id, normalized_url
        
        # Vimeo patterns
        vimeo_patterns = [
            r'vimeo\.com/(\d+)',
            r'player\.vimeo\.com/video/(\d+)',
        ]
        
        for pattern in vimeo_patterns:
            match = re.search(pattern, url)
            if match:
                video_id = match.group(1)
                normalized_url = f"https://vimeo.com/{video_id}"
                return 'vimeo', video_id, normalized_url
        
        # If no pattern matches, treat as direct URL
        return 'direct', None, url
    
    @staticmethod
    def fetch_youtube_metadata(video_id: str) -> Dict:
        """
        Fetch video metadata from YouTube Data API v3
        """
        if not settings.YOUTUBE_API_KEY:
            return {'error': 'YouTube API key not configured'}
        
        api_url = "https://www.googleapis.com/youtube/v3/videos"
        params = {
            'id': video_id,
            'part': 'snippet,contentDetails,status',
            'key': settings.YOUTUBE_API_KEY
        }
        
        try:
            response = requests.get(api_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if not data.get('items'):
                return {'error': 'Video not found or not accessible'}
            
            item = data['items'][0]
            snippet = item.get('snippet', {})
            content_details = item.get('contentDetails', {})
            status = item.get('status', {})
            
            # Parse duration (PT4M13S -> 253 seconds)
            duration_str = content_details.get('duration', 'PT0S')
            duration_seconds = VideoIntegrationService._parse_youtube_duration(duration_str)
            
            # Get best quality thumbnail
            thumbnails = snippet.get('thumbnails', {})
            thumbnail_url = (
                thumbnails.get('maxres', {}).get('url') or
                thumbnails.get('standard', {}).get('url') or
                thumbnails.get('high', {}).get('url') or
                thumbnails.get('medium', {}).get('url') or
                thumbnails.get('default', {}).get('url', '')
            )
            
            return {
                'title': snippet.get('title', ''),
                'description': snippet.get('description', ''),
                'thumbnail_url': thumbnail_url,
                'duration': duration_seconds,
                'platform': 'youtube',
                'video_id': video_id,
                'privacy_status': status.get('privacyStatus', 'unknown'),
                'embeddable': status.get('embeddable', True),
                'published_at': snippet.get('publishedAt', ''),
            }
            
        except requests.RequestException as e:
            return {'error': f'YouTube API request failed: {str(e)}'}
        except Exception as e:
            return {'error': f'Failed to process YouTube response: {str(e)}'}
    
    @staticmethod
    def fetch_vimeo_metadata(video_id: str) -> Dict:
        """
        Fetch video metadata from Vimeo API
        """
        if not settings.VIMEO_ACCESS_TOKEN:
            return {'error': 'Vimeo access token not configured'}
        
        api_url = f"https://api.vimeo.com/videos/{video_id}"
        headers = {
            'Authorization': f'Bearer {settings.VIMEO_ACCESS_TOKEN}',
            'Accept': 'application/vnd.vimeo.*+json;version=3.4'
        }
        
        try:
            response = requests.get(api_url, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Get best quality thumbnail
            pictures = data.get('pictures', {}).get('sizes', [])
            thumbnail_url = ''
            if pictures:
                # Get largest thumbnail
                largest_pic = max(pictures, key=lambda x: x.get('width', 0))
                thumbnail_url = largest_pic.get('link', '')
            
            return {
                'title': data.get('name', ''),
                'description': data.get('description', ''),
                'thumbnail_url': thumbnail_url,
                'duration': data.get('duration', 0),
                'platform': 'vimeo',
                'video_id': video_id,
                'privacy_status': data.get('privacy', {}).get('view', 'unknown'),
                'embeddable': data.get('embed', {}).get('html') is not None,
                'published_at': data.get('created_time', ''),
            }
            
        except requests.RequestException as e:
            return {'error': f'Vimeo API request failed: {str(e)}'}
        except Exception as e:
            return {'error': f'Failed to process Vimeo response: {str(e)}'}
    
    @staticmethod
    def fetch_video_metadata(url: str) -> Dict:
        """
        Main method to fetch video metadata from any supported platform
        """
        platform, video_id, normalized_url = VideoIntegrationService.extract_video_info(url)
        
        if not platform or not video_id:
            return {
                'error': 'Unsupported video URL format',
                'platform': 'direct',
                'video_url': url
            }
        
        if platform == 'youtube':
            metadata = VideoIntegrationService.fetch_youtube_metadata(video_id)
        elif platform == 'vimeo':
            metadata = VideoIntegrationService.fetch_vimeo_metadata(video_id)
        else:
            return {
                'error': 'Unsupported platform',
                'platform': platform,
                'video_url': url
            }
        
        # Add normalized URL to response
        if 'error' not in metadata:
            metadata['normalized_url'] = normalized_url
            metadata['original_url'] = url
        
        return metadata
    
    @staticmethod
    def _parse_youtube_duration(duration_str: str) -> int:
        """
        Parse YouTube duration format (PT4M13S) to seconds
        """
        if not duration_str.startswith('PT'):
            return 0
        
        # Remove PT prefix
        duration_str = duration_str[2:]
        
        # Extract hours, minutes, seconds
        hours = minutes = seconds = 0
        
        # Hours
        h_match = re.search(r'(\d+)H', duration_str)
        if h_match:
            hours = int(h_match.group(1))
        
        # Minutes  
        m_match = re.search(r'(\d+)M', duration_str)
        if m_match:
            minutes = int(m_match.group(1))
        
        # Seconds
        s_match = re.search(r'(\d+)S', duration_str)
        if s_match:
            seconds = int(s_match.group(1))
        
        return hours * 3600 + minutes * 60 + seconds