from rest_framework import generics, permissions, status, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count
from django.utils import timezone
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiExample
from drf_spectacular.openapi import OpenApiResponse
from datetime import timedelta

from .models import Lead, News, Placement, Testimonial, LeadFollowUp
from .serializers import (
    LeadCreateSerializer, LeadListSerializer, LeadDetailSerializer,
    NewsListSerializer, NewsDetailSerializer, NewsSimpleSerializer,
    PlacementListSerializer, PlacementDetailSerializer, PlacementSimpleSerializer,
    TestimonialListSerializer, TestimonialDetailSerializer, TestimonialSimpleSerializer,
    ContentStatsSerializer, LeadFollowUpSerializer, StudentLeadStatusSerializer, StudentLeadListSerializer
)


# LEAD MANAGEMENT VIEWS (Mobile App)

@extend_schema_view(
    post=extend_schema(
        summary="Submit Lead for One-on-One Session",
        description="Students can submit their interest for one-on-one sessions",
        request=LeadCreateSerializer,
        responses={
            201: OpenApiResponse(
                description="Lead submitted successfully",
                examples=[
                    OpenApiExample(
                        'Success Response',
                        value={
                            "message": "Thank you for your interest! Our team will contact you within 24 hours.",
                            "lead_id": 123
                        }
                    )
                ]
            ),
            400: OpenApiResponse(description="Validation errors")
        },
        tags=['Mobile App - Leads']
    )
)
class LeadCreateView(generics.CreateAPIView):
    """Create new lead for one-on-one sessions"""
    serializer_class = LeadCreateSerializer
    permission_classes = [permissions.AllowAny]  # Allow anonymous submissions
    
    def create(self, request, *args, **kwargs):
        # Get client IP and user agent for tracking
        ip_address = self.get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Save with user if authenticated, otherwise anonymous
        submitted_by = request.user if request.user.is_authenticated else None
        
        lead = serializer.save(
            ip_address=ip_address,
            user_agent=user_agent,
            source='mobile_app',
            submitted_by=submitted_by
        )
        
        response_message = 'Thank you for your interest! Our team will contact you within 24 hours.'
        if submitted_by:
            response_message += ' You can track your lead status in the app.'
        
        return Response({
            'message': response_message,
            'lead_id': lead.id,
            'can_track': submitted_by is not None
        }, status=status.HTTP_201_CREATED)
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


# NEWS MANAGEMENT VIEWS (Mobile App)

@extend_schema_view(
    get=extend_schema(
        summary="List Latest News",
        description="Get latest news and updates for mobile app",
        responses={200: NewsListSerializer(many=True)},
        tags=['Mobile App - News']
    )
)
class NewsListView(generics.ListAPIView):
    """List published news for mobile app"""
    serializer_class = NewsListSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'is_featured']
    search_fields = ['title', 'excerpt', 'content']
    ordering = ['-published_at']
    
    def get_queryset(self):
        return News.objects.filter(
            is_published=True,
            published_at__lte=timezone.now()
        ).select_related('created_by')


@extend_schema_view(
    get=extend_schema(
        summary="Get News Details",
        description="Get detailed news article with full content",
        responses={
            200: NewsDetailSerializer,
            404: OpenApiResponse(description="News not found")
        },
        tags=['Mobile App - News']
    )
)
class NewsDetailView(generics.RetrieveAPIView):
    """Get detailed news article"""
    serializer_class = NewsDetailSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'slug'
    
    def get_queryset(self):
        return News.objects.filter(
            is_published=True,
            published_at__lte=timezone.now()
        ).select_related('created_by')
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        # Increment view count
        News.objects.filter(id=instance.id).update(view_count=instance.view_count + 1)
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


# PLACEMENT MANAGEMENT VIEWS (Mobile App)

@extend_schema_view(
    get=extend_schema(
        summary="List Student Placements",
        description="Get successful student placement stories",
        responses={200: PlacementListSerializer(many=True)},
        tags=['Mobile App - Placements']
    )
)
class PlacementListView(generics.ListAPIView):
    """List published placements"""
    serializer_class = PlacementListSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['placement_type', 'is_featured']
    search_fields = ['student_name', 'company_name', 'job_title', 'course_completed']
    ordering = ['-published_at']
    
    def get_queryset(self):
        return Placement.objects.filter(
            is_published=True,
            consent_given=True,
            published_at__lte=timezone.now()
        ).select_related('created_by')


@extend_schema_view(
    get=extend_schema(
        summary="Get Placement Details",
        description="Get detailed placement success story",
        responses={
            200: PlacementDetailSerializer,
            404: OpenApiResponse(description="Placement not found")
        },
        tags=['Mobile App - Placements']
    )
)
class PlacementDetailView(generics.RetrieveAPIView):
    """Get detailed placement story"""
    serializer_class = PlacementDetailSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        return Placement.objects.filter(
            is_published=True,
            consent_given=True,
            published_at__lte=timezone.now()
        ).select_related('created_by')


# TESTIMONIAL MANAGEMENT VIEWS (Mobile App)

@extend_schema_view(
    get=extend_schema(
        summary="List Student Testimonials",
        description="Get student testimonials - videos and text",
        responses={200: TestimonialListSerializer(many=True)},
        tags=['Mobile App - Testimonials']
    )
)
class TestimonialListView(generics.ListAPIView):
    """List published testimonials"""
    serializer_class = TestimonialListSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['testimonial_type', 'is_featured', 'overall_rating']
    search_fields = ['student_name', 'course_name', 'testimonial_text']
    ordering = ['-published_at']
    
    def get_queryset(self):
        return Testimonial.objects.filter(
            is_published=True,
            consent_given=True,
            published_at__lte=timezone.now()
        ).select_related('created_by')


@extend_schema_view(
    get=extend_schema(
        summary="Get Testimonial Details",
        description="Get detailed testimonial with full content",
        responses={
            200: TestimonialDetailSerializer,
            404: OpenApiResponse(description="Testimonial not found")
        },
        tags=['Mobile App - Testimonials']
    )
)
class TestimonialDetailView(generics.RetrieveAPIView):
    """Get detailed testimonial"""
    serializer_class = TestimonialDetailSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        return Testimonial.objects.filter(
            is_published=True,
            consent_given=True,
            published_at__lte=timezone.now()
        ).select_related('created_by')


@extend_schema_view(
    post=extend_schema(
        summary="Like Testimonial",
        description="Increment like count for testimonial",
        responses={
            200: OpenApiResponse(
                description="Testimonial liked successfully",
                examples=[
                    OpenApiExample(
                        'Success Response',
                        value={"message": "Testimonial liked", "likes_count": 15}
                    )
                ]
            )
        },
        tags=['Mobile App - Testimonials']
    )
)
class TestimonialLikeView(APIView):
    """Like a testimonial"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request, pk):
        try:
            testimonial = Testimonial.objects.get(id=pk, is_published=True)
            testimonial.likes_count += 1
            testimonial.save()
            return Response({
                'message': 'Testimonial liked',
                'likes_count': testimonial.likes_count
            })
        except Testimonial.DoesNotExist:
            return Response(
                {'error': 'Testimonial not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )


# DASHBOARD/HOME CONTENT API

@extend_schema_view(
    get=extend_schema(
        summary="Get Dashboard Content",
        description="Get featured content for mobile app home screen",
        responses={
            200: OpenApiResponse(
                description="Dashboard content",
                examples=[
                    OpenApiExample(
                        'Success Response',
                        value={
                            "featured_news": [],
                            "latest_placements": [],
                            "featured_testimonials": [],
                            "stats": {
                                "total_students": 1000,
                                "successful_placements": 850,
                                "average_package": "₹6.5 LPA"
                            }
                        }
                    )
                ]
            )
        },
        tags=['Mobile App - Dashboard']
    )
)
class DashboardContentView(APIView):
    """Get featured content for mobile app dashboard"""
    permission_classes = [permissions.AllowAny]
    
    def get(self, request):
        # Featured News (latest 3)
        featured_news = News.objects.filter(
            is_published=True,
            is_featured=True,
            published_at__lte=timezone.now()
        ).order_by('-published_at')[:3]
        
        # Latest Placements (latest 5)
        latest_placements = Placement.objects.filter(
            is_published=True,
            consent_given=True,
            published_at__lte=timezone.now()
        ).order_by('-published_at')[:5]
        
        # Featured Testimonials (latest 5)
        featured_testimonials = Testimonial.objects.filter(
            is_published=True,
            is_featured=True,
            consent_given=True,
            published_at__lte=timezone.now()
        ).order_by('-published_at')[:5]
        
        # Basic stats
        total_placements = Placement.objects.filter(is_published=True).count()
        avg_package = Placement.objects.filter(
            is_published=True, 
            can_show_package=True
        ).aggregate(avg=models.Avg('package_amount'))['avg'] or 0
        
        return Response({
            'featured_news': NewsSimpleSerializer(featured_news, many=True).data,
            'latest_placements': PlacementSimpleSerializer(latest_placements, many=True).data,
            'featured_testimonials': TestimonialSimpleSerializer(featured_testimonials, many=True).data,
            'stats': {
                'total_placements': total_placements,
                'average_package': f"₹{avg_package:,.0f}" if avg_package else "Not available",
                'success_rate': "95%"  # You can calculate this based on your data
            }
        })


# ADMIN VIEWS (For Custom Admin Panel)

class AdminLeadListView(generics.ListAPIView):
    """Admin view for listing all leads"""
    serializer_class = LeadListSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'area_of_interest', 'current_experience', 'assigned_to']
    search_fields = ['name', 'email', 'phone']
    ordering = ['-created_at']
    
    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Lead.objects.all().select_related('assigned_to')
        return Lead.objects.none()


@extend_schema_view(
    get=extend_schema(
        summary="Get Lead Details",
        description="Get detailed lead information for admin",
        responses={
            200: LeadDetailSerializer,
            404: OpenApiResponse(description="Lead not found"),
            403: OpenApiResponse(description="Permission denied")
        },
        tags=['Admin - Lead Management']
    ),
    put=extend_schema(
        summary="Update Lead",
        description="Update lead information and status",
        request=LeadDetailSerializer,
        responses={
            200: LeadDetailSerializer,
            400: OpenApiResponse(description="Validation errors"),
            403: OpenApiResponse(description="Permission denied"),
            404: OpenApiResponse(description="Lead not found")
        },
        tags=['Admin - Lead Management']
    ),
    patch=extend_schema(
        summary="Partially Update Lead",
        description="Partially update lead information",
        request=LeadDetailSerializer,
        responses={
            200: LeadDetailSerializer,
            400: OpenApiResponse(description="Validation errors"),
            403: OpenApiResponse(description="Permission denied"),
            404: OpenApiResponse(description="Lead not found")
        },
        tags=['Admin - Lead Management']
    ),
    delete=extend_schema(
        summary="Delete Lead",
        description="Permanently delete a lead record and all associated follow-ups",
        responses={
            204: OpenApiResponse(description="Lead deleted successfully"),
            403: OpenApiResponse(description="Permission denied"),
            404: OpenApiResponse(description="Lead not found")
        },
        tags=['Admin - Lead Management']
    )
)
class AdminLeadDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Admin view for lead details, updates, and deletion"""
    serializer_class = LeadDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Lead.objects.all().select_related('assigned_to').prefetch_related('follow_ups')
        return Lead.objects.none()
    
    def destroy(self, request, *args, **kwargs):
        """Delete lead and all associated follow-ups"""
        instance = self.get_object()
        
        # Delete associated follow-ups first
        instance.follow_ups.all().delete()
        
        # Delete the lead
        self.perform_destroy(instance)
        
        return Response(
            {'message': f'Lead "{instance.name}" and all associated data deleted successfully'}, 
            status=status.HTTP_200_OK
        )


@extend_schema_view(
    get=extend_schema(
        summary="Get Content Management Statistics",
        description="Get statistics for admin dashboard",
        responses={200: ContentStatsSerializer},
        tags=['Admin - Statistics']
    )
)
class ContentStatsView(APIView):
    """Get content management statistics for admin"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        if not request.user.is_staff:
            return Response(
                {'error': 'Permission denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        now = timezone.now()
        this_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        stats = {
            'total_leads': Lead.objects.count(),
            'new_leads': Lead.objects.filter(status='new').count(),
            'leads_this_month': Lead.objects.filter(created_at__gte=this_month_start).count(),
            'total_news': News.objects.count(),
            'published_news': News.objects.filter(is_published=True).count(),
            'total_placements': Placement.objects.count(),
            'total_testimonials': Testimonial.objects.count(),
            'featured_content': (
                News.objects.filter(is_featured=True).count() +
                Placement.objects.filter(is_featured=True).count() +
                Testimonial.objects.filter(is_featured=True).count()
            )
        }
        
        serializer = ContentStatsSerializer(stats)
        return Response(serializer.data)


# STUDENT LEAD STATUS VIEWS

@extend_schema_view(
    get=extend_schema(
        summary="Get My Lead Status",
        description="Get the status of leads submitted by the authenticated user",
        responses={
            200: StudentLeadListSerializer(many=True),
            401: OpenApiResponse(description="Authentication required")
        },
        tags=['Student - Lead Status']
    )
)
class MyLeadStatusListView(generics.ListAPIView):
    """List leads submitted by authenticated user"""
    serializer_class = StudentLeadListSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Lead.objects.filter(submitted_by=self.request.user).order_by('-created_at')


@extend_schema_view(
    get=extend_schema(
        summary="Get Lead Status Details",
        description="Get detailed status of a specific lead submitted by the authenticated user",
        responses={
            200: StudentLeadStatusSerializer,
            404: OpenApiResponse(description="Lead not found"),
            401: OpenApiResponse(description="Authentication required")
        },
        tags=['Student - Lead Status']
    )
)
class MyLeadStatusDetailView(generics.RetrieveAPIView):
    """Get detailed status of a specific lead"""
    serializer_class = StudentLeadStatusSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Lead.objects.filter(submitted_by=self.request.user)