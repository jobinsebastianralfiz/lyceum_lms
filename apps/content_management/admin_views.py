from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count, Avg
from django.utils import timezone
from django.utils.text import slugify
from django.http import JsonResponse
from datetime import timedelta

from .models import Lead, News, Placement, Testimonial, LeadFollowUp, Banner, Event
from .serializers import LeadDetailSerializer
from apps.users.models import User


def is_staff_user(user):
    return user.is_authenticated and user.is_staff


# LEAD MANAGEMENT VIEWS

@user_passes_test(is_staff_user, login_url='/admin/login/')
def leads_list_view(request):
    """List all leads with filtering and search"""
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    interest_filter = request.GET.get('interest', '')
    assigned_filter = request.GET.get('assigned_to', '')
    
    leads = Lead.objects.select_related('assigned_to').order_by('-created_at')
    
    # Apply filters
    if search_query:
        leads = leads.filter(
            Q(name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(phone__icontains=search_query) |
            Q(career_goals__icontains=search_query)
        )
    
    if status_filter:
        leads = leads.filter(status=status_filter)
    
    if interest_filter:
        leads = leads.filter(area_of_interest=interest_filter)
        
    if assigned_filter:
        if assigned_filter == 'unassigned':
            leads = leads.filter(assigned_to__isnull=True)
        else:
            leads = leads.filter(assigned_to_id=assigned_filter)
    
    # Pagination
    paginator = Paginator(leads, 25)
    page_number = request.GET.get('page')
    leads_page = paginator.get_page(page_number)
    
    # Get filter options
    staff_users = User.objects.filter(is_staff=True)
    
    # Statistics
    now = timezone.now()
    stats = {
        'total_leads': Lead.objects.count(),
        'new_leads': Lead.objects.filter(status='new').count(),
        'leads_this_month': Lead.objects.filter(
            created_at__gte=now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        ).count(),
        'conversion_rate': '15%',  # You can calculate this based on your data
    }
    
    context = {
        'leads': leads_page,
        'search_query': search_query,
        'status_filter': status_filter,
        'interest_filter': interest_filter,
        'assigned_filter': assigned_filter,
        'staff_users': staff_users,
        'stats': stats,
        'lead_statuses': Lead.STATUS_CHOICES,
        'interest_areas': Lead.INTEREST_CHOICES,
    }
    
    return render(request, 'custom_admin/content/leads_list.html', context)


@user_passes_test(is_staff_user, login_url='/admin/login/')
def lead_detail_view(request, lead_id):
    """View and update lead details"""
    lead = get_object_or_404(Lead, id=lead_id)
    
    if request.method == 'POST':
        # Update lead
        lead.status = request.POST.get('status', lead.status)
        lead.notes = request.POST.get('notes', lead.notes)
        assigned_to_id = request.POST.get('assigned_to')
        if assigned_to_id:
            lead.assigned_to_id = assigned_to_id
        lead.save()
        
        messages.success(request, 'Lead updated successfully.')
        return redirect('custom_admin:lead_detail', lead_id=lead.id)
    
    # Get follow-ups
    follow_ups = lead.follow_ups.all().order_by('-scheduled_at')
    staff_users = User.objects.filter(is_staff=True)
    
    context = {
        'lead': lead,
        'follow_ups': follow_ups,
        'staff_users': staff_users,
        'lead_statuses': Lead.STATUS_CHOICES,
    }
    
    return render(request, 'custom_admin/content/lead_detail.html', context)


@user_passes_test(is_staff_user, login_url='/admin/login/')
def lead_delete_view(request, lead_id):
    """Delete a lead and all associated follow-ups"""
    lead = get_object_or_404(Lead, id=lead_id)
    
    if request.method == 'POST':
        lead_name = lead.name
        
        # Delete associated follow-ups first
        lead.follow_ups.all().delete()
        
        # Delete the lead
        lead.delete()
        
        messages.success(request, f'Lead "{lead_name}" and all associated data deleted successfully.')
        return redirect('custom_admin:leads_list')
    
    # If not POST, redirect back to lead detail
    return redirect('custom_admin:lead_detail', lead_id=lead_id)


# NEWS MANAGEMENT VIEWS

@user_passes_test(is_staff_user, login_url='/admin/login/')
def news_list_view(request):
    """List all news articles"""
    search_query = request.GET.get('search', '')
    category_filter = request.GET.get('category', '')
    status_filter = request.GET.get('status', '')
    
    news = News.objects.select_related('created_by').order_by('-created_at')
    
    # Apply filters
    if search_query:
        news = news.filter(
            Q(title__icontains=search_query) |
            Q(content__icontains=search_query) |
            Q(excerpt__icontains=search_query)
        )
    
    if category_filter:
        news = news.filter(category=category_filter)
    
    if status_filter:
        if status_filter == 'published':
            news = news.filter(is_published=True)
        elif status_filter == 'draft':
            news = news.filter(is_published=False)
        elif status_filter == 'featured':
            news = news.filter(is_featured=True)
    
    # Pagination
    paginator = Paginator(news, 20)
    page_number = request.GET.get('page')
    news_page = paginator.get_page(page_number)
    
    # Statistics
    stats = {
        'total_news': News.objects.count(),
        'published_news': News.objects.filter(is_published=True).count(),
        'draft_news': News.objects.filter(is_published=False).count(),
        'featured_news': News.objects.filter(is_featured=True).count(),
    }
    
    context = {
        'news': news_page,
        'search_query': search_query,
        'category_filter': category_filter,
        'status_filter': status_filter,
        'stats': stats,
        'news_categories': News.CATEGORY_CHOICES,
    }
    
    return render(request, 'custom_admin/content/news_list.html', context)


@user_passes_test(is_staff_user, login_url='/admin/login/')
def news_detail_view(request, news_id):
    """View and edit news article details"""
    news = get_object_or_404(News, id=news_id)
    
    if request.method == 'POST':
        # Update news article
        news.title = request.POST.get('title', news.title)
        news.content = request.POST.get('content', news.content)
        news.excerpt = request.POST.get('excerpt', news.excerpt)
        news.category = request.POST.get('category', news.category)
        news.tags = request.POST.get('tags', news.tags)
        news.is_published = request.POST.get('is_published') == 'on'
        news.is_featured = request.POST.get('is_featured') == 'on'
        
        # Update slug if title changed
        original_title = News.objects.get(id=news_id).title
        if news.title != original_title:
            slug = slugify(news.title)
            original_slug = slug
            counter = 1
            while News.objects.filter(slug=slug).exclude(id=news_id).exists():
                slug = f"{original_slug}-{counter}"
                counter += 1
            news.slug = slug
        
        # Handle file uploads
        if request.FILES.get('featured_image'):
            news.featured_image = request.FILES['featured_image']
        if request.FILES.get('thumbnail'):
            news.thumbnail = request.FILES['thumbnail']
        
        # Set published_at if publishing for first time
        if news.is_published and not news.published_at:
            news.published_at = timezone.now()
        elif not news.is_published:
            news.published_at = None
            
        news.save()
        
        messages.success(request, 'News article updated successfully.')
        return redirect('custom_admin:news_detail', news_id=news.id)
    
    context = {
        'news': news,
        'news_categories': News.CATEGORY_CHOICES,
    }
    
    return render(request, 'custom_admin/content/news_detail.html', context)


@user_passes_test(is_staff_user, login_url='/admin/login/')
def news_create_view(request):
    """Create new news article"""
    if request.method == 'POST':
        title = request.POST.get('title')
        content = request.POST.get('content')
        excerpt = request.POST.get('excerpt')
        category = request.POST.get('category')
        tags = request.POST.get('tags')
        is_published = request.POST.get('is_published') == 'on'
        is_featured = request.POST.get('is_featured') == 'on'
        
        # Create slug
        slug = slugify(title)
        original_slug = slug
        counter = 1
        while News.objects.filter(slug=slug).exists():
            slug = f"{original_slug}-{counter}"
            counter += 1
        
        news = News.objects.create(
            title=title,
            slug=slug,
            content=content,
            excerpt=excerpt,
            category=category,
            tags=tags,
            is_published=is_published,
            is_featured=is_featured,
            created_by=request.user,
            published_at=timezone.now() if is_published else None
        )
        
        # Handle file uploads
        if request.FILES.get('featured_image'):
            news.featured_image = request.FILES['featured_image']
        if request.FILES.get('thumbnail'):
            news.thumbnail = request.FILES['thumbnail']
        news.save()
        
        messages.success(request, 'News article created successfully.')
        return redirect('custom_admin:news_list')
    
    context = {
        'news_categories': News.CATEGORY_CHOICES,
    }
    
    return render(request, 'custom_admin/content/news_form.html', context)


# PLACEMENT MANAGEMENT VIEWS

@user_passes_test(is_staff_user, login_url='/admin/login/')
def placements_list_view(request):
    """List all placement records"""
    search_query = request.GET.get('search', '')
    placement_type_filter = request.GET.get('placement_type', '')
    status_filter = request.GET.get('status', '')
    
    placements = Placement.objects.select_related('created_by').order_by('-created_at')
    
    # Apply filters
    if search_query:
        placements = placements.filter(
            Q(student_name__icontains=search_query) |
            Q(company_name__icontains=search_query) |
            Q(job_title__icontains=search_query) |
            Q(course_completed__icontains=search_query)
        )
    
    if placement_type_filter:
        placements = placements.filter(placement_type=placement_type_filter)
    
    if status_filter:
        if status_filter == 'published':
            placements = placements.filter(is_published=True)
        elif status_filter == 'draft':
            placements = placements.filter(is_published=False)
        elif status_filter == 'featured':
            placements = placements.filter(is_featured=True)
    
    # Pagination
    paginator = Paginator(placements, 20)
    page_number = request.GET.get('page')
    placements_page = paginator.get_page(page_number)
    
    # Statistics
    stats = {
        'total_placements': Placement.objects.count(),
        'published_placements': Placement.objects.filter(is_published=True).count(),
        'average_package': Placement.objects.filter(
            is_published=True, can_show_package=True
        ).aggregate(avg=Avg('package_amount'))['avg'] or 0,
    }
    
    context = {
        'placements': placements_page,
        'search_query': search_query,
        'placement_type_filter': placement_type_filter,
        'status_filter': status_filter,
        'stats': stats,
        'placement_types': Placement.PLACEMENT_TYPE_CHOICES,
    }
    
    return render(request, 'custom_admin/content/placements_list.html', context)


@user_passes_test(is_staff_user, login_url='/admin/login/')
def placement_create_view(request):
    """Create new placement record"""
    if request.method == 'POST':
        placement = Placement.objects.create(
            student_name=request.POST.get('student_name'),
            company_name=request.POST.get('company_name'),
            job_title=request.POST.get('job_title'),
            location=request.POST.get('location', ''),
            course_completed=request.POST.get('course_completed'),
            batch_year=request.POST.get('batch_year'),
            placement_type=request.POST.get('placement_type'),
            package_amount=float(request.POST.get('package_amount', 0)),
            package_currency=request.POST.get('package_currency', 'INR'),
            can_show_package=request.POST.get('can_show_package') == 'on',
            placement_date=request.POST.get('placement_date') or None,
            success_story=request.POST.get('success_story', ''),
            key_skills_gained=request.POST.get('key_skills_gained', ''),
            career_progression=request.POST.get('career_progression', ''),
            is_published=request.POST.get('is_published') == 'on',
            is_featured=request.POST.get('is_featured') == 'on',
            consent_given=request.POST.get('consent_given') == 'on',
            can_show_details=request.POST.get('can_show_details') == 'on',
            created_by=request.user,
            published_at=timezone.now() if request.POST.get('is_published') == 'on' else None
        )
        
        # Handle file uploads
        if request.FILES.get('student_photo'):
            placement.student_photo = request.FILES['student_photo']
        if request.FILES.get('company_logo'):
            placement.company_logo = request.FILES['company_logo']
        if request.FILES.get('certificate_image'):
            placement.certificate_image = request.FILES['certificate_image']
        
        placement.save()
        
        messages.success(request, 'Placement record created successfully.')
        return redirect('custom_admin:placements_list')
    
    context = {
        'placement_types': Placement.PLACEMENT_TYPE_CHOICES,
    }
    
    return render(request, 'custom_admin/content/placement_form.html', context)


# TESTIMONIAL MANAGEMENT VIEWS

@user_passes_test(is_staff_user, login_url='/admin/login/')
def testimonials_list_view(request):
    """List all testimonials"""
    search_query = request.GET.get('search', '')
    testimonial_type_filter = request.GET.get('testimonial_type', '')
    status_filter = request.GET.get('status', '')
    
    testimonials = Testimonial.objects.select_related('created_by').order_by('-created_at')
    
    # Apply filters
    if search_query:
        testimonials = testimonials.filter(
            Q(student_name__icontains=search_query) |
            Q(course_name__icontains=search_query) |
            Q(testimonial_text__icontains=search_query) |
            Q(current_company__icontains=search_query)
        )
    
    if testimonial_type_filter:
        testimonials = testimonials.filter(testimonial_type=testimonial_type_filter)
    
    if status_filter:
        if status_filter == 'published':
            testimonials = testimonials.filter(is_published=True)
        elif status_filter == 'draft':
            testimonials = testimonials.filter(is_published=False)
        elif status_filter == 'featured':
            testimonials = testimonials.filter(is_featured=True)
    
    # Pagination
    paginator = Paginator(testimonials, 20)
    page_number = request.GET.get('page')
    testimonials_page = paginator.get_page(page_number)
    
    # Statistics
    stats = {
        'total_testimonials': Testimonial.objects.count(),
        'published_testimonials': Testimonial.objects.filter(is_published=True).count(),
        'video_testimonials': Testimonial.objects.filter(
            testimonial_type__in=['video_youtube', 'video_upload']
        ).count(),
        'average_rating': Testimonial.objects.filter(
            is_published=True
        ).aggregate(avg=Avg('overall_rating'))['avg'] or 0,
    }
    
    context = {
        'testimonials': testimonials_page,
        'search_query': search_query,
        'testimonial_type_filter': testimonial_type_filter,
        'status_filter': status_filter,
        'stats': stats,
        'testimonial_types': Testimonial.TESTIMONIAL_TYPE_CHOICES,
    }
    
    return render(request, 'custom_admin/content/testimonials_list.html', context)


@user_passes_test(is_staff_user, login_url='/admin/login/')
def testimonial_create_view(request):
    """Create new testimonial"""
    if request.method == 'POST':
        testimonial_type = request.POST.get('testimonial_type')
        
        testimonial = Testimonial.objects.create(
            student_name=request.POST.get('student_name'),
            course_name=request.POST.get('course_name'),
            batch_year=request.POST.get('batch_year'),
            testimonial_type=testimonial_type,
            testimonial_text=request.POST.get('testimonial_text', ''),
            youtube_url=request.POST.get('youtube_url', ''),
            overall_rating=int(request.POST.get('overall_rating', 5)),
            course_rating=int(request.POST.get('course_rating', 5)),
            instructor_rating=int(request.POST.get('instructor_rating', 5)),
            key_learnings=request.POST.get('key_learnings', ''),
            career_impact=request.POST.get('career_impact', ''),
            recommendation=request.POST.get('recommendation', ''),
            current_position=request.POST.get('current_position', ''),
            current_company=request.POST.get('current_company', ''),
            is_published=request.POST.get('is_published') == 'on',
            is_featured=request.POST.get('is_featured') == 'on',
            consent_given=request.POST.get('consent_given') == 'on',
            can_show_details=request.POST.get('can_show_details') == 'on',
            created_by=request.user,
            published_at=timezone.now() if request.POST.get('is_published') == 'on' else None
        )
        
        # Handle file uploads
        if request.FILES.get('student_photo'):
            testimonial.student_photo = request.FILES['student_photo']
        if request.FILES.get('uploaded_video'):
            testimonial.uploaded_video = request.FILES['uploaded_video']
        if request.FILES.get('video_thumbnail'):
            testimonial.video_thumbnail = request.FILES['video_thumbnail']
        if request.FILES.get('audio_file'):
            testimonial.audio_file = request.FILES['audio_file']
        
        testimonial.save()
        
        messages.success(request, 'Testimonial created successfully.')
        return redirect('custom_admin:testimonials_list')
    
    context = {
        'testimonial_types': Testimonial.TESTIMONIAL_TYPE_CHOICES,
        'rating_choices': Testimonial.RATING_CHOICES,
    }
    
    return render(request, 'custom_admin/content/testimonial_form.html', context)


@user_passes_test(is_staff_user, login_url='/admin/login/')
def testimonial_detail_view(request, testimonial_id):
    """View testimonial details"""
    testimonial = get_object_or_404(Testimonial, id=testimonial_id)
    
    context = {
        'testimonial': testimonial,
        'testimonial_types': Testimonial.TESTIMONIAL_TYPE_CHOICES,
        'rating_choices': Testimonial.RATING_CHOICES,
    }
    
    return render(request, 'custom_admin/content/testimonial_detail.html', context)


@user_passes_test(is_staff_user, login_url='/admin/login/')
def testimonial_edit_view(request, testimonial_id):
    """Edit testimonial"""
    testimonial = get_object_or_404(Testimonial, id=testimonial_id)
    
    if request.method == 'POST':
        try:
            # Update testimonial fields
            testimonial.student_name = request.POST.get('student_name', testimonial.student_name)
            testimonial.course_name = request.POST.get('course_name', testimonial.course_name)
            testimonial.batch_year = request.POST.get('batch_year', testimonial.batch_year)
            testimonial.testimonial_type = request.POST.get('testimonial_type', testimonial.testimonial_type)
            testimonial.testimonial_text = request.POST.get('testimonial_text', testimonial.testimonial_text)
            testimonial.youtube_url = request.POST.get('youtube_url', testimonial.youtube_url)
            testimonial.overall_rating = int(request.POST.get('overall_rating', testimonial.overall_rating))
            testimonial.course_rating = int(request.POST.get('course_rating', testimonial.course_rating))
            testimonial.instructor_rating = int(request.POST.get('instructor_rating', testimonial.instructor_rating))
            testimonial.key_learnings = request.POST.get('key_learnings', testimonial.key_learnings)
            testimonial.career_impact = request.POST.get('career_impact', testimonial.career_impact)
            testimonial.recommendation = request.POST.get('recommendation', testimonial.recommendation)
            testimonial.current_position = request.POST.get('current_position', testimonial.current_position)
            testimonial.current_company = request.POST.get('current_company', testimonial.current_company)
            testimonial.is_published = request.POST.get('is_published') == 'on'
            testimonial.is_featured = request.POST.get('is_featured') == 'on'
            testimonial.consent_given = request.POST.get('consent_given') == 'on'
            testimonial.can_show_details = request.POST.get('can_show_details') == 'on'
            
            # Handle file uploads
            if request.FILES.get('student_photo'):
                testimonial.student_photo = request.FILES['student_photo']
            if request.FILES.get('uploaded_video'):
                testimonial.uploaded_video = request.FILES['uploaded_video']
            if request.FILES.get('video_thumbnail'):
                testimonial.video_thumbnail = request.FILES['video_thumbnail']
            if request.FILES.get('audio_file'):
                testimonial.audio_file = request.FILES['audio_file']
            
            # Set published_at timestamp
            if testimonial.is_published and not testimonial.published_at:
                testimonial.published_at = timezone.now()
            elif not testimonial.is_published:
                testimonial.published_at = None
            
            testimonial.save()
            
            messages.success(request, f'Testimonial updated successfully!')
            return redirect('custom_admin:testimonial_detail', testimonial_id=testimonial.id)
            
        except Exception as e:
            messages.error(request, f'Error updating testimonial: {str(e)}')
    
    context = {
        'testimonial': testimonial,
        'testimonial_types': Testimonial.TESTIMONIAL_TYPE_CHOICES,
        'rating_choices': Testimonial.RATING_CHOICES,
        'is_edit': True,
    }
    
    return render(request, 'custom_admin/content/testimonial_form.html', context)


@user_passes_test(is_staff_user, login_url='/admin/login/')
def testimonial_delete_view(request, testimonial_id):
    """Delete testimonial"""
    testimonial = get_object_or_404(Testimonial, id=testimonial_id)
    
    if request.method == 'POST':
        testimonial_name = testimonial.student_name
        testimonial.delete()
        messages.success(request, f'Testimonial by {testimonial_name} deleted successfully!')
        return redirect('custom_admin:testimonials_list')
    
    context = {
        'testimonial': testimonial,
    }
    
    return render(request, 'custom_admin/content/testimonial_delete.html', context)


# DASHBOARD VIEW

@user_passes_test(is_staff_user, login_url='/admin/login/')
def content_dashboard_view(request):
    """Content management dashboard"""
    now = timezone.now()
    this_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Lead statistics
    lead_stats = {
        'total_leads': Lead.objects.count(),
        'new_leads': Lead.objects.filter(status='new').count(),
        'leads_this_month': Lead.objects.filter(created_at__gte=this_month_start).count(),
        'converted_leads': Lead.objects.filter(status='converted').count(),
    }
    
    # Content statistics
    content_stats = {
        'published_news': News.objects.filter(is_published=True).count(),
        'draft_news': News.objects.filter(is_published=False).count(),
        'published_placements': Placement.objects.filter(is_published=True).count(),
        'published_testimonials': Testimonial.objects.filter(is_published=True).count(),
    }
    
    # Enhanced testimonial statistics
    testimonial_stats = {
        'total_testimonials': Testimonial.objects.count(),
        'published_testimonials': Testimonial.objects.filter(is_published=True).count(),
        'draft_testimonials': Testimonial.objects.filter(is_published=False).count(),
        'featured_testimonials': Testimonial.objects.filter(is_featured=True).count(),
        'video_testimonials': Testimonial.objects.filter(testimonial_type__in=['video_youtube', 'video_upload']).count(),
        'audio_testimonials': Testimonial.objects.filter(testimonial_type='audio').count(),
        'text_testimonials': Testimonial.objects.filter(testimonial_type='text_image').count(),
        'average_rating': Testimonial.objects.aggregate(Avg('overall_rating'))['overall_rating__avg'] or 0,
        'testimonials_this_month': Testimonial.objects.filter(created_at__gte=this_month_start).count(),
    }
    
    # Recent activities
    recent_leads = Lead.objects.order_by('-created_at')[:5]
    recent_news = News.objects.order_by('-created_at')[:5]
    recent_testimonials = Testimonial.objects.order_by('-created_at')[:5]
    
    context = {
        'lead_stats': lead_stats,
        'content_stats': content_stats,
        'testimonial_stats': testimonial_stats,
        'recent_leads': recent_leads,
        'recent_news': recent_news,
        'recent_testimonials': recent_testimonials,
    }
    
    return render(request, 'custom_admin/content/dashboard.html', context)


# BANNER MANAGEMENT VIEWS

@user_passes_test(is_staff_user, login_url='/admin/login/')
def banners_list_view(request):
    """List all banners"""
    search_query = request.GET.get('search', '')
    banner_type_filter = request.GET.get('banner_type', '')
    status_filter = request.GET.get('status', '')

    banners = Banner.objects.select_related('created_by').order_by('-priority', '-created_at')

    # Apply filters
    if search_query:
        banners = banners.filter(
            Q(title__icontains=search_query) |
            Q(subtitle__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    if banner_type_filter:
        banners = banners.filter(banner_type=banner_type_filter)

    if status_filter:
        if status_filter == 'active':
            banners = banners.filter(is_active=True)
        elif status_filter == 'inactive':
            banners = banners.filter(is_active=False)

    # Pagination
    paginator = Paginator(banners, 20)
    page_number = request.GET.get('page')
    banners_page = paginator.get_page(page_number)

    # Statistics
    stats = {
        'total_banners': Banner.objects.count(),
        'active_banners': Banner.objects.filter(is_active=True).count(),
        'hero_banners': Banner.objects.filter(banner_type='hero', is_active=True).count(),
    }

    context = {
        'banners': banners_page,
        'search_query': search_query,
        'banner_type_filter': banner_type_filter,
        'status_filter': status_filter,
        'stats': stats,
        'banner_types': Banner.BANNER_TYPE_CHOICES,
    }

    return render(request, 'custom_admin/content/banners_list.html', context)


@user_passes_test(is_staff_user, login_url='/admin/login/')
def banner_create_view(request):
    """Create new banner"""
    if request.method == 'POST':
        banner = Banner.objects.create(
            title=request.POST.get('title'),
            subtitle=request.POST.get('subtitle', ''),
            description=request.POST.get('description', ''),
            cta_text=request.POST.get('cta_text', ''),
            cta_link=request.POST.get('cta_link', ''),
            secondary_cta_text=request.POST.get('secondary_cta_text', ''),
            secondary_cta_link=request.POST.get('secondary_cta_link', ''),
            banner_type=request.POST.get('banner_type', 'hero'),
            text_color=request.POST.get('text_color', 'white'),
            overlay_opacity=float(request.POST.get('overlay_opacity', 0.5)),
            stat_1_value=request.POST.get('stat_1_value', ''),
            stat_1_label=request.POST.get('stat_1_label', ''),
            stat_2_value=request.POST.get('stat_2_value', ''),
            stat_2_label=request.POST.get('stat_2_label', ''),
            stat_3_value=request.POST.get('stat_3_value', ''),
            stat_3_label=request.POST.get('stat_3_label', ''),
            is_active=request.POST.get('is_active') == 'on',
            priority=int(request.POST.get('priority', 0)),
            created_by=request.user,
        )

        # Handle file uploads
        if request.FILES.get('background_image'):
            banner.background_image = request.FILES['background_image']
        if request.FILES.get('featured_image'):
            banner.featured_image = request.FILES['featured_image']
        banner.save()

        messages.success(request, 'Banner created successfully.')
        return redirect('custom_admin:banners_list')

    context = {
        'banner_types': Banner.BANNER_TYPE_CHOICES,
    }

    return render(request, 'custom_admin/content/banner_form.html', context)


@user_passes_test(is_staff_user, login_url='/admin/login/')
def banner_edit_view(request, banner_id):
    """Edit banner"""
    banner = get_object_or_404(Banner, id=banner_id)

    if request.method == 'POST':
        banner.title = request.POST.get('title', banner.title)
        banner.subtitle = request.POST.get('subtitle', banner.subtitle)
        banner.description = request.POST.get('description', banner.description)
        banner.cta_text = request.POST.get('cta_text', banner.cta_text)
        banner.cta_link = request.POST.get('cta_link', banner.cta_link)
        banner.secondary_cta_text = request.POST.get('secondary_cta_text', banner.secondary_cta_text)
        banner.secondary_cta_link = request.POST.get('secondary_cta_link', banner.secondary_cta_link)
        banner.banner_type = request.POST.get('banner_type', banner.banner_type)
        banner.text_color = request.POST.get('text_color', banner.text_color)
        banner.overlay_opacity = float(request.POST.get('overlay_opacity', banner.overlay_opacity))
        banner.stat_1_value = request.POST.get('stat_1_value', banner.stat_1_value)
        banner.stat_1_label = request.POST.get('stat_1_label', banner.stat_1_label)
        banner.stat_2_value = request.POST.get('stat_2_value', banner.stat_2_value)
        banner.stat_2_label = request.POST.get('stat_2_label', banner.stat_2_label)
        banner.stat_3_value = request.POST.get('stat_3_value', banner.stat_3_value)
        banner.stat_3_label = request.POST.get('stat_3_label', banner.stat_3_label)
        banner.is_active = request.POST.get('is_active') == 'on'
        banner.priority = int(request.POST.get('priority', banner.priority))

        # Handle image removal
        if request.POST.get('remove_background_image'):
            if banner.background_image:
                banner.background_image.delete(save=False)
                banner.background_image = None
        elif request.FILES.get('background_image'):
            banner.background_image = request.FILES['background_image']

        if request.POST.get('remove_featured_image'):
            if banner.featured_image:
                banner.featured_image.delete(save=False)
                banner.featured_image = None
        elif request.FILES.get('featured_image'):
            banner.featured_image = request.FILES['featured_image']

        banner.save()

        messages.success(request, 'Banner updated successfully.')
        return redirect('custom_admin:banners_list')

    context = {
        'banner': banner,
        'banner_types': Banner.BANNER_TYPE_CHOICES,
        'is_edit': True,
    }

    return render(request, 'custom_admin/content/banner_form.html', context)


@user_passes_test(is_staff_user, login_url='/admin/login/')
def banner_delete_view(request, banner_id):
    """Delete banner"""
    banner = get_object_or_404(Banner, id=banner_id)

    if request.method == 'POST':
        banner_title = banner.title
        banner.delete()
        messages.success(request, f'Banner "{banner_title}" deleted successfully!')
        return redirect('custom_admin:banners_list')

    return redirect('custom_admin:banners_list')


# EVENT MANAGEMENT VIEWS

@user_passes_test(is_staff_user, login_url='/admin/login/')
def events_list_view(request):
    """List all events"""
    search_query = request.GET.get('search', '')
    event_type_filter = request.GET.get('event_type', '')
    status_filter = request.GET.get('status', '')

    events = Event.objects.select_related('created_by').order_by('-event_date')

    # Apply filters
    if search_query:
        events = events.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(venue_name__icontains=search_query)
        )

    if event_type_filter:
        events = events.filter(event_type=event_type_filter)

    if status_filter:
        if status_filter == 'published':
            events = events.filter(is_published=True)
        elif status_filter == 'draft':
            events = events.filter(is_published=False)
        elif status_filter == 'upcoming':
            events = events.filter(status='upcoming')

    # Pagination
    paginator = Paginator(events, 20)
    page_number = request.GET.get('page')
    events_page = paginator.get_page(page_number)

    # Statistics
    stats = {
        'total_events': Event.objects.count(),
        'published_events': Event.objects.filter(is_published=True).count(),
        'upcoming_events': Event.objects.filter(status='upcoming').count(),
        'featured_events': Event.objects.filter(is_featured=True).count(),
    }

    context = {
        'events': events_page,
        'search_query': search_query,
        'event_type_filter': event_type_filter,
        'status_filter': status_filter,
        'stats': stats,
        'event_types': Event.EVENT_TYPE_CHOICES,
        'event_statuses': Event.STATUS_CHOICES,
    }

    return render(request, 'custom_admin/content/events_list.html', context)


@user_passes_test(is_staff_user, login_url='/admin/login/')
def event_create_view(request):
    """Create new event"""
    if request.method == 'POST':
        title = request.POST.get('title')

        # Create slug
        slug = slugify(title)
        original_slug = slug
        counter = 1
        while Event.objects.filter(slug=slug).exists():
            slug = f"{original_slug}-{counter}"
            counter += 1

        event = Event.objects.create(
            title=title,
            slug=slug,
            description=request.POST.get('description', ''),
            short_description=request.POST.get('short_description', ''),
            event_type=request.POST.get('event_type'),
            status=request.POST.get('status', 'upcoming'),
            event_date=request.POST.get('event_date'),
            start_time=request.POST.get('start_time'),
            end_time=request.POST.get('end_time') or None,
            timezone=request.POST.get('timezone', 'Asia/Kolkata'),
            is_online=request.POST.get('is_online') == 'on',
            venue_name=request.POST.get('venue_name', ''),
            venue_address=request.POST.get('venue_address', ''),
            meeting_link=request.POST.get('meeting_link', ''),
            registration_required=request.POST.get('registration_required') == 'on',
            registration_link=request.POST.get('registration_link', ''),
            speakers=request.POST.get('speakers', ''),
            is_published=request.POST.get('is_published') == 'on',
            is_featured=request.POST.get('is_featured') == 'on',
            created_by=request.user,
            published_at=timezone.now() if request.POST.get('is_published') == 'on' else None
        )

        # Handle file uploads
        if request.FILES.get('featured_image'):
            event.featured_image = request.FILES['featured_image']
        if request.FILES.get('thumbnail'):
            event.thumbnail = request.FILES['thumbnail']
        event.save()

        messages.success(request, 'Event created successfully.')
        return redirect('custom_admin:events_list')

    context = {
        'event_types': Event.EVENT_TYPE_CHOICES,
        'event_statuses': Event.STATUS_CHOICES,
    }

    return render(request, 'custom_admin/content/event_form.html', context)


@user_passes_test(is_staff_user, login_url='/admin/login/')
def event_edit_view(request, event_id):
    """Edit event"""
    event = get_object_or_404(Event, id=event_id)

    if request.method == 'POST':
        event.title = request.POST.get('title', event.title)
        event.description = request.POST.get('description', event.description)
        event.short_description = request.POST.get('short_description', event.short_description)
        event.event_type = request.POST.get('event_type', event.event_type)
        event.status = request.POST.get('status', event.status)
        event.event_date = request.POST.get('event_date', event.event_date)
        event.start_time = request.POST.get('start_time', event.start_time)
        event.end_time = request.POST.get('end_time') or None
        event.timezone = request.POST.get('timezone', event.timezone)
        event.is_online = request.POST.get('is_online') == 'on'
        event.venue_name = request.POST.get('venue_name', event.venue_name)
        event.venue_address = request.POST.get('venue_address', event.venue_address)
        event.meeting_link = request.POST.get('meeting_link', event.meeting_link)
        event.registration_required = request.POST.get('registration_required') == 'on'
        event.registration_link = request.POST.get('registration_link', event.registration_link)
        event.speakers = request.POST.get('speakers', event.speakers)
        event.is_published = request.POST.get('is_published') == 'on'
        event.is_featured = request.POST.get('is_featured') == 'on'

        # Update slug if title changed
        original_title = Event.objects.get(id=event_id).title
        if event.title != original_title:
            slug = slugify(event.title)
            original_slug = slug
            counter = 1
            while Event.objects.filter(slug=slug).exclude(id=event_id).exists():
                slug = f"{original_slug}-{counter}"
                counter += 1
            event.slug = slug

        # Handle image removal
        if request.POST.get('remove_featured_image'):
            if event.featured_image:
                event.featured_image.delete(save=False)
                event.featured_image = None
        elif request.FILES.get('featured_image'):
            event.featured_image = request.FILES['featured_image']

        if request.POST.get('remove_thumbnail'):
            if event.thumbnail:
                event.thumbnail.delete(save=False)
                event.thumbnail = None
        elif request.FILES.get('thumbnail'):
            event.thumbnail = request.FILES['thumbnail']

        # Set published_at if publishing for first time
        if event.is_published and not event.published_at:
            event.published_at = timezone.now()
        elif not event.is_published:
            event.published_at = None

        event.save()

        messages.success(request, 'Event updated successfully.')
        return redirect('custom_admin:events_list')

    context = {
        'event': event,
        'event_types': Event.EVENT_TYPE_CHOICES,
        'event_statuses': Event.STATUS_CHOICES,
        'is_edit': True,
    }

    return render(request, 'custom_admin/content/event_form.html', context)


@user_passes_test(is_staff_user, login_url='/admin/login/')
def event_delete_view(request, event_id):
    """Delete event"""
    event = get_object_or_404(Event, id=event_id)

    if request.method == 'POST':
        event_title = event.title
        event.delete()
        messages.success(request, f'Event "{event_title}" deleted successfully!')
        return redirect('custom_admin:events_list')

    return redirect('custom_admin:events_list')