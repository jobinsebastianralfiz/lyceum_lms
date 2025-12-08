"""
Teacher Management Views for Custom Admin
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Q
import secrets
import string

from apps.teachers.models import TeacherProfile, TeacherSchedule, TeacherAnnouncement
from apps.users.models import User
from apps.courses.models import Course
from .forms import TeacherCreationForm, TeacherProfileEditForm, TeacherCourseAssignmentForm


def admin_required(view_func):
    """Decorator to ensure user is admin, superuser, or teacher"""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('custom_admin:login')
        user_role = getattr(request.user, 'role', None)
        if not (request.user.is_staff or request.user.is_superuser or user_role in ['admin', 'teacher']):
            messages.error(request, 'Access denied. Admin or Teacher privileges required.')
            return redirect('landing:login')
        return view_func(request, *args, **kwargs)
    return wrapper


@login_required
@admin_required
def teachers_list_view(request):
    """List all teachers"""
    teachers = TeacherProfile.objects.select_related('user').prefetch_related(
        'assigned_courses'
    ).order_by('-created_at')

    # Search
    search_query = request.GET.get('search', '')
    if search_query:
        teachers = teachers.filter(
            Q(user__name__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(employee_id__icontains=search_query) |
            Q(designation__icontains=search_query) |
            Q(department__icontains=search_query)
        )

    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter == 'active':
        teachers = teachers.filter(is_active=True, user__is_active=True)
    elif status_filter == 'inactive':
        teachers = teachers.filter(Q(is_active=False) | Q(user__is_active=False))

    # Annotate with student and course counts
    teachers = teachers.annotate(
        courses_count=Count('assigned_courses', distinct=True)
    )

    # Pagination
    paginator = Paginator(teachers, 15)
    page_number = request.GET.get('page')
    teachers_page = paginator.get_page(page_number)

    # Stats
    total_teachers = TeacherProfile.objects.count()
    active_teachers = TeacherProfile.objects.filter(is_active=True, user__is_active=True).count()

    context = {
        'teachers': teachers_page,
        'search_query': search_query,
        'status_filter': status_filter,
        'total_teachers': total_teachers,
        'active_teachers': active_teachers,
    }
    return render(request, 'custom_admin/teachers/list.html', context)


@login_required
@admin_required
def teacher_create_view(request):
    """Create a new teacher"""
    if request.method == 'POST':
        form = TeacherCreationForm(request.POST)
        if form.is_valid():
            try:
                profile = form.save()
                messages.success(
                    request,
                    f'Teacher "{profile.user.name}" created successfully. '
                    f'They will be required to change their password on first login.'
                )
                return redirect('custom_admin:teachers_list')
            except Exception as e:
                messages.error(request, f'Error creating teacher: {str(e)}')
    else:
        form = TeacherCreationForm()

    context = {
        'form': form,
        'title': 'Add New Teacher',
        'is_edit': False,
    }
    return render(request, 'custom_admin/teachers/form.html', context)


@login_required
@admin_required
def teacher_detail_view(request, teacher_id):
    """View teacher details"""
    teacher = get_object_or_404(
        TeacherProfile.objects.select_related('user').prefetch_related(
            'assigned_courses',
            'schedules',
            'announcements'
        ),
        pk=teacher_id
    )

    # Get assigned courses with student counts
    assigned_courses = teacher.assigned_courses.annotate(
        enrolled_students=Count('enrollments', filter=Q(enrollments__active=True))
    )

    # Get recent announcements
    recent_announcements = teacher.announcements.order_by('-created_at')[:5]

    # Get schedules
    schedules = teacher.schedules.filter(is_active=True).order_by('day_of_week', 'start_time')

    context = {
        'teacher': teacher,
        'assigned_courses': assigned_courses,
        'recent_announcements': recent_announcements,
        'schedules': schedules,
    }
    return render(request, 'custom_admin/teachers/detail.html', context)


@login_required
@admin_required
def teacher_edit_view(request, teacher_id):
    """Edit a teacher"""
    teacher = get_object_or_404(TeacherProfile.objects.select_related('user'), pk=teacher_id)

    if request.method == 'POST':
        form = TeacherProfileEditForm(request.POST, instance=teacher)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, f'Teacher "{teacher.user.name}" updated successfully.')
                return redirect('custom_admin:teacher_detail', teacher_id=teacher.id)
            except Exception as e:
                messages.error(request, f'Error updating teacher: {str(e)}')
    else:
        form = TeacherProfileEditForm(instance=teacher)

    context = {
        'form': form,
        'teacher': teacher,
        'title': f'Edit Teacher: {teacher.user.name}',
        'is_edit': True,
    }
    return render(request, 'custom_admin/teachers/form.html', context)


@login_required
@admin_required
def teacher_delete_view(request, teacher_id):
    """Delete/deactivate a teacher"""
    teacher = get_object_or_404(TeacherProfile.objects.select_related('user'), pk=teacher_id)

    if request.method == 'POST':
        action = request.POST.get('action', 'deactivate')

        if action == 'delete':
            # Hard delete
            user = teacher.user
            teacher_name = user.name
            teacher.delete()
            user.delete()
            messages.success(request, f'Teacher "{teacher_name}" has been permanently deleted.')
        else:
            # Soft delete (deactivate)
            teacher.is_active = False
            teacher.save()
            teacher.user.is_active = False
            teacher.user.save()
            messages.success(request, f'Teacher "{teacher.user.name}" has been deactivated.')

        return redirect('custom_admin:teachers_list')

    context = {
        'teacher': teacher,
    }
    return render(request, 'custom_admin/teachers/delete_confirm.html', context)


@login_required
@admin_required
def teacher_assign_courses_view(request, teacher_id):
    """Assign courses to a teacher"""
    teacher = get_object_or_404(TeacherProfile.objects.select_related('user'), pk=teacher_id)

    if request.method == 'POST':
        form = TeacherCourseAssignmentForm(request.POST, teacher_profile=teacher)
        if form.is_valid():
            form.save()
            messages.success(request, f'Courses updated for teacher "{teacher.user.name}".')
            return redirect('custom_admin:teacher_detail', teacher_id=teacher.id)
    else:
        form = TeacherCourseAssignmentForm(teacher_profile=teacher)

    # Get all published courses
    courses = Course.objects.filter(is_published=True).order_by('title')

    context = {
        'form': form,
        'teacher': teacher,
        'courses': courses,
    }
    return render(request, 'custom_admin/teachers/assign_courses.html', context)


@login_required
@admin_required
def teacher_reset_password_view(request, teacher_id):
    """Reset a teacher's password"""
    teacher = get_object_or_404(TeacherProfile.objects.select_related('user'), pk=teacher_id)

    if request.method == 'POST':
        # Generate temporary password
        temp_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))

        user = teacher.user
        user.set_password(temp_password)
        user.save()

        teacher.must_change_password = True
        teacher.save()

        messages.success(
            request,
            f'Password reset for "{user.name}". Temporary password: {temp_password}. '
            f'Please share this password securely with the teacher.'
        )
        return redirect('custom_admin:teacher_detail', teacher_id=teacher.id)

    context = {
        'teacher': teacher,
    }
    return render(request, 'custom_admin/teachers/reset_password_confirm.html', context)


@login_required
@admin_required
def teacher_toggle_status_view(request, teacher_id):
    """Toggle teacher active/inactive status"""
    teacher = get_object_or_404(TeacherProfile.objects.select_related('user'), pk=teacher_id)

    if request.method == 'POST':
        new_status = not teacher.is_active

        teacher.is_active = new_status
        teacher.save()

        teacher.user.is_active = new_status
        teacher.user.save()

        status_text = 'activated' if new_status else 'deactivated'
        messages.success(request, f'Teacher "{teacher.user.name}" has been {status_text}.')

    return redirect('custom_admin:teacher_detail', teacher_id=teacher.id)
