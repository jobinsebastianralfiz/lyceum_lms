"""
Tuition Management Views for Custom Admin
Offline student management, attendance, and fee collection
"""
import logging
import json
from datetime import date, timedelta
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count
from django.http import JsonResponse
from django.utils import timezone

from apps.tuition.models import (
    Standard, Subject, TuitionBatch, TuitionStudent,
    TuitionEnrollment, TuitionAttendance, TuitionFee
)
from apps.tuition.services import (
    seed_all_default_data,
    generate_monthly_fees_for_all,
    collect_tuition_fee,
    get_tuition_dashboard_stats,
    mark_overdue_fees
)
from apps.users.models import User
from apps.teachers.models import TeacherProfile

logger = logging.getLogger(__name__)


def is_staff_user(user):
    """Check if user is staff/admin"""
    return user.is_authenticated and (user.is_staff or user.role == 'admin')


# =============================================================================
# TUITION DASHBOARD
# =============================================================================

@user_passes_test(is_staff_user)
def tuition_dashboard_view(request):
    """Main tuition dashboard with KPIs"""
    stats = get_tuition_dashboard_stats()

    today = date.today()

    # Get recent fee collections
    recent_collections = TuitionFee.objects.filter(
        status='paid'
    ).select_related(
        'enrollment__student', 'enrollment__batch'
    ).order_by('-payment_date', '-updated_at')[:5]

    # Get pending fees
    pending_fees = TuitionFee.objects.filter(
        status__in=['pending', 'partial', 'overdue']
    ).select_related(
        'enrollment__student', 'enrollment__batch'
    ).order_by('due_date')[:10]

    # Get today's batches
    day_name = today.strftime('%a').lower()[:3]
    todays_batches = TuitionBatch.objects.filter(is_active=True)

    # Get low attendance students (below 75%)
    low_attendance_students = []

    context = {
        'page_title': 'Tuition Dashboard',
        'stats': stats,
        'recent_collections': recent_collections,
        'pending_fees': pending_fees,
        'todays_batches': todays_batches,
        'today': today,
    }

    return render(request, 'custom_admin/tuition/dashboard.html', context)


# =============================================================================
# STANDARDS
# =============================================================================

@user_passes_test(is_staff_user)
def standards_list_view(request):
    """List all standards"""
    standards = Standard.objects.annotate(
        student_count=Count('students', filter=Q(students__is_active=True)),
        batch_count=Count('batches', filter=Q(batches__is_active=True))
    ).order_by('order', 'name')

    context = {
        'page_title': 'Standards (Classes)',
        'standards': standards,
    }
    return render(request, 'custom_admin/tuition/standards_list.html', context)


@user_passes_test(is_staff_user)
def standard_create_view(request):
    """Create a new standard"""
    if request.method == 'POST':
        try:
            name = request.POST.get('name', '').strip()
            code = request.POST.get('code', '').strip()
            order = request.POST.get('order', 0)
            description = request.POST.get('description', '').strip()

            if not name or not code:
                messages.error(request, 'Name and code are required.')
                return redirect('custom_admin:standard_create')

            if Standard.objects.filter(code=code).exists():
                messages.error(request, f'Standard with code "{code}" already exists.')
                return redirect('custom_admin:standard_create')

            Standard.objects.create(
                name=name,
                code=code,
                order=int(order) if order else 0,
                description=description or None
            )
            messages.success(request, f'Standard "{name}" created successfully.')
            return redirect('custom_admin:standards_list')

        except Exception as e:
            logger.error(f"Error creating standard: {str(e)}")
            messages.error(request, f'Error creating standard: {str(e)}')

    context = {
        'page_title': 'Add Standard',
    }
    return render(request, 'custom_admin/tuition/standard_form.html', context)


@user_passes_test(is_staff_user)
def standard_edit_view(request, standard_id):
    """Edit a standard"""
    standard = get_object_or_404(Standard, id=standard_id)

    if request.method == 'POST':
        try:
            standard.name = request.POST.get('name', '').strip()
            code = request.POST.get('code', '').strip()

            # Check for duplicate code
            if Standard.objects.filter(code=code).exclude(id=standard_id).exists():
                messages.error(request, f'Standard with code "{code}" already exists.')
                return redirect('custom_admin:standard_edit', standard_id=standard_id)

            standard.code = code
            standard.order = int(request.POST.get('order', 0))
            standard.description = request.POST.get('description', '').strip() or None
            standard.is_active = request.POST.get('is_active') == 'on'
            standard.save()

            messages.success(request, f'Standard "{standard.name}" updated successfully.')
            return redirect('custom_admin:standards_list')

        except Exception as e:
            logger.error(f"Error updating standard: {str(e)}")
            messages.error(request, f'Error updating standard: {str(e)}')

    context = {
        'page_title': 'Edit Standard',
        'standard': standard,
    }
    return render(request, 'custom_admin/tuition/standard_form.html', context)


@user_passes_test(is_staff_user)
def standard_delete_view(request, standard_id):
    """Delete a standard"""
    standard = get_object_or_404(Standard, id=standard_id)

    if request.method == 'POST':
        try:
            if standard.students.exists() or standard.batches.exists():
                messages.error(request, f'Cannot delete "{standard.name}" - it has associated students or batches.')
                return redirect('custom_admin:standards_list')

            name = standard.name
            standard.delete()
            messages.success(request, f'Standard "{name}" deleted successfully.')
        except Exception as e:
            logger.error(f"Error deleting standard: {str(e)}")
            messages.error(request, f'Error deleting standard: {str(e)}')

    return redirect('custom_admin:standards_list')


# =============================================================================
# SUBJECTS
# =============================================================================

@user_passes_test(is_staff_user)
def subjects_list_view(request):
    """List all subjects"""
    subjects = Subject.objects.annotate(
        batch_count=Count('batches', filter=Q(batches__is_active=True)),
        enrollment_count=Count('individual_enrollments', filter=Q(individual_enrollments__is_active=True))
    ).order_by('name')

    context = {
        'page_title': 'Subjects',
        'subjects': subjects,
    }
    return render(request, 'custom_admin/tuition/subjects_list.html', context)


@user_passes_test(is_staff_user)
def subject_create_view(request):
    """Create a new subject"""
    standards = Standard.objects.filter(is_active=True).order_by('order')

    if request.method == 'POST':
        try:
            name = request.POST.get('name', '').strip()
            code = request.POST.get('code', '').strip().upper()
            description = request.POST.get('description', '').strip()
            icon = request.POST.get('icon', 'ti ti-book')
            color = request.POST.get('color', '#5d87ff')
            selected_standards = request.POST.getlist('standards')

            if not name or not code:
                messages.error(request, 'Name and code are required.')
                return redirect('custom_admin:subject_create')

            if Subject.objects.filter(code=code).exists():
                messages.error(request, f'Subject with code "{code}" already exists.')
                return redirect('custom_admin:subject_create')

            subject = Subject.objects.create(
                name=name,
                code=code,
                description=description or None,
                icon=icon,
                color=color
            )

            if selected_standards:
                subject.standards.set(selected_standards)

            messages.success(request, f'Subject "{name}" created successfully.')
            return redirect('custom_admin:subjects_list')

        except Exception as e:
            logger.error(f"Error creating subject: {str(e)}")
            messages.error(request, f'Error creating subject: {str(e)}')

    context = {
        'page_title': 'Add Subject',
        'standards': standards,
    }
    return render(request, 'custom_admin/tuition/subject_form.html', context)


@user_passes_test(is_staff_user)
def subject_edit_view(request, subject_id):
    """Edit a subject"""
    subject = get_object_or_404(Subject, id=subject_id)
    standards = Standard.objects.filter(is_active=True).order_by('order')

    if request.method == 'POST':
        try:
            subject.name = request.POST.get('name', '').strip()
            code = request.POST.get('code', '').strip().upper()

            if Subject.objects.filter(code=code).exclude(id=subject_id).exists():
                messages.error(request, f'Subject with code "{code}" already exists.')
                return redirect('custom_admin:subject_edit', subject_id=subject_id)

            subject.code = code
            subject.description = request.POST.get('description', '').strip() or None
            subject.icon = request.POST.get('icon', 'ti ti-book')
            subject.color = request.POST.get('color', '#5d87ff')
            subject.is_active = request.POST.get('is_active') == 'on'
            subject.save()

            selected_standards = request.POST.getlist('standards')
            subject.standards.set(selected_standards)

            messages.success(request, f'Subject "{subject.name}" updated successfully.')
            return redirect('custom_admin:subjects_list')

        except Exception as e:
            logger.error(f"Error updating subject: {str(e)}")
            messages.error(request, f'Error updating subject: {str(e)}')

    context = {
        'page_title': 'Edit Subject',
        'subject': subject,
        'standards': standards,
    }
    return render(request, 'custom_admin/tuition/subject_form.html', context)


@user_passes_test(is_staff_user)
def subject_delete_view(request, subject_id):
    """Delete a subject"""
    subject = get_object_or_404(Subject, id=subject_id)

    if request.method == 'POST':
        try:
            if subject.batches.exists() or subject.individual_enrollments.exists():
                messages.error(request, f'Cannot delete "{subject.name}" - it has associated batches or enrollments.')
                return redirect('custom_admin:subjects_list')

            name = subject.name
            subject.delete()
            messages.success(request, f'Subject "{name}" deleted successfully.')
        except Exception as e:
            logger.error(f"Error deleting subject: {str(e)}")
            messages.error(request, f'Error deleting subject: {str(e)}')

    return redirect('custom_admin:subjects_list')


# =============================================================================
# BATCHES
# =============================================================================

@user_passes_test(is_staff_user)
def batches_list_view(request):
    """List all batches"""
    batches = TuitionBatch.objects.select_related(
        'standard', 'subject', 'teacher'
    ).annotate(
        enrollment_count=Count('enrollments', filter=Q(enrollments__is_active=True))
    ).order_by('-created_at')

    # Filters
    standard_id = request.GET.get('standard')
    subject_id = request.GET.get('subject')
    status = request.GET.get('status')

    if standard_id:
        batches = batches.filter(standard_id=standard_id)
    if subject_id:
        batches = batches.filter(subject_id=subject_id)
    if status == 'active':
        batches = batches.filter(is_active=True)
    elif status == 'inactive':
        batches = batches.filter(is_active=False)

    paginator = Paginator(batches, 20)
    page = request.GET.get('page', 1)
    batches = paginator.get_page(page)

    standards = Standard.objects.filter(is_active=True).order_by('order')
    subjects = Subject.objects.filter(is_active=True).order_by('name')

    context = {
        'page_title': 'Tuition Batches',
        'batches': batches,
        'standards': standards,
        'subjects': subjects,
        'selected_standard': standard_id,
        'selected_subject': subject_id,
        'selected_status': status,
    }
    return render(request, 'custom_admin/tuition/batches_list.html', context)


@user_passes_test(is_staff_user)
def batch_create_view(request):
    """Create a new batch"""
    standards = Standard.objects.filter(is_active=True).order_by('order')
    subjects = Subject.objects.filter(is_active=True).order_by('name')
    teachers = TeacherProfile.objects.filter(is_active=True, can_teach_offline=True).select_related('user').order_by('user__name')

    if request.method == 'POST':
        try:
            name = request.POST.get('name', '').strip()
            code = request.POST.get('code', '').strip().upper()
            standard_id = request.POST.get('standard')
            subject_id = request.POST.get('subject')
            teacher_id = request.POST.get('teacher')
            monthly_fee = request.POST.get('monthly_fee', '0')
            max_students = request.POST.get('max_students', 30)
            location = request.POST.get('location', '').strip()
            start_date = request.POST.get('start_date')
            end_date = request.POST.get('end_date')

            # Parse schedule
            schedule = {}
            for day in ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']:
                time_slot = request.POST.get(f'schedule_{day}', '').strip()
                if time_slot:
                    schedule[day] = time_slot

            if not name or not code or not standard_id or not subject_id or not start_date:
                messages.error(request, 'Name, code, standard, subject, and start date are required.')
                return redirect('custom_admin:batch_create')

            if TuitionBatch.objects.filter(code=code).exists():
                messages.error(request, f'Batch with code "{code}" already exists.')
                return redirect('custom_admin:batch_create')

            batch = TuitionBatch.objects.create(
                name=name,
                code=code,
                standard_id=standard_id,
                subject_id=subject_id,
                teacher_id=teacher_id if teacher_id else None,
                monthly_fee=Decimal(monthly_fee),
                max_students=int(max_students),
                location=location or None,
                schedule=schedule,
                start_date=start_date,
                end_date=end_date if end_date else None
            )

            messages.success(request, f'Batch "{name}" created successfully.')
            return redirect('custom_admin:batches_list')

        except Exception as e:
            logger.error(f"Error creating batch: {str(e)}")
            messages.error(request, f'Error creating batch: {str(e)}')

    context = {
        'page_title': 'Add Batch',
        'standards': standards,
        'subjects': subjects,
        'teachers': teachers,
    }
    return render(request, 'custom_admin/tuition/batch_form.html', context)


@user_passes_test(is_staff_user)
def batch_detail_view(request, batch_id):
    """View batch details with enrolled students"""
    batch = get_object_or_404(TuitionBatch, id=batch_id)

    enrollments = TuitionEnrollment.objects.filter(
        batch=batch
    ).select_related('student').order_by('-is_active', 'student__name')

    # Recent attendance
    recent_attendance = TuitionAttendance.objects.filter(
        batch=batch
    ).select_related('enrollment__student').order_by('-date')[:20]

    context = {
        'page_title': f'Batch: {batch.name}',
        'batch': batch,
        'enrollments': enrollments,
        'recent_attendance': recent_attendance,
    }
    return render(request, 'custom_admin/tuition/batch_detail.html', context)


@user_passes_test(is_staff_user)
def batch_edit_view(request, batch_id):
    """Edit a batch"""
    batch = get_object_or_404(TuitionBatch, id=batch_id)
    standards = Standard.objects.filter(is_active=True).order_by('order')
    subjects = Subject.objects.filter(is_active=True).order_by('name')
    teachers = TeacherProfile.objects.filter(is_active=True, can_teach_offline=True).select_related('user').order_by('user__name')

    if request.method == 'POST':
        try:
            batch.name = request.POST.get('name', '').strip()
            code = request.POST.get('code', '').strip().upper()

            if TuitionBatch.objects.filter(code=code).exclude(id=batch_id).exists():
                messages.error(request, f'Batch with code "{code}" already exists.')
                return redirect('custom_admin:batch_edit', batch_id=batch_id)

            batch.code = code
            batch.standard_id = request.POST.get('standard')
            batch.subject_id = request.POST.get('subject')
            teacher_id = request.POST.get('teacher')
            batch.teacher_id = teacher_id if teacher_id else None
            batch.monthly_fee = Decimal(request.POST.get('monthly_fee', '0'))
            batch.max_students = int(request.POST.get('max_students', 30))
            batch.location = request.POST.get('location', '').strip() or None
            batch.start_date = request.POST.get('start_date')
            end_date = request.POST.get('end_date')
            batch.end_date = end_date if end_date else None
            batch.is_active = request.POST.get('is_active') == 'on'

            # Parse schedule
            schedule = {}
            for day in ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']:
                time_slot = request.POST.get(f'schedule_{day}', '').strip()
                if time_slot:
                    schedule[day] = time_slot
            batch.schedule = schedule

            batch.save()
            messages.success(request, f'Batch "{batch.name}" updated successfully.')
            return redirect('custom_admin:batch_detail', batch_id=batch_id)

        except Exception as e:
            logger.error(f"Error updating batch: {str(e)}")
            messages.error(request, f'Error updating batch: {str(e)}')

    context = {
        'page_title': 'Edit Batch',
        'batch': batch,
        'standards': standards,
        'subjects': subjects,
        'teachers': teachers,
    }
    return render(request, 'custom_admin/tuition/batch_form.html', context)


@user_passes_test(is_staff_user)
def batch_delete_view(request, batch_id):
    """Delete a batch"""
    batch = get_object_or_404(TuitionBatch, id=batch_id)

    if request.method == 'POST':
        try:
            if batch.enrollments.filter(is_active=True).exists():
                messages.error(request, f'Cannot delete "{batch.name}" - it has active enrollments.')
                return redirect('custom_admin:batches_list')

            name = batch.name
            batch.delete()
            messages.success(request, f'Batch "{name}" deleted successfully.')
        except Exception as e:
            logger.error(f"Error deleting batch: {str(e)}")
            messages.error(request, f'Error deleting batch: {str(e)}')

    return redirect('custom_admin:batches_list')


# =============================================================================
# TUITION STUDENTS
# =============================================================================

@user_passes_test(is_staff_user)
def tuition_students_list_view(request):
    """List all tuition students"""
    students = TuitionStudent.objects.select_related('standard').order_by('name')

    # Filters
    search = request.GET.get('search', '').strip()
    standard_id = request.GET.get('standard')
    status = request.GET.get('status')

    if search:
        students = students.filter(
            Q(name__icontains=search) |
            Q(phone__icontains=search) |
            Q(parent_name__icontains=search) |
            Q(parent_phone__icontains=search)
        )
    if standard_id:
        students = students.filter(standard_id=standard_id)
    if status == 'active':
        students = students.filter(is_active=True)
    elif status == 'inactive':
        students = students.filter(is_active=False)

    paginator = Paginator(students, 20)
    page = request.GET.get('page', 1)
    students = paginator.get_page(page)

    standards = Standard.objects.filter(is_active=True).order_by('order')

    context = {
        'page_title': 'Tuition Students',
        'students': students,
        'standards': standards,
        'search': search,
        'selected_standard': standard_id,
        'selected_status': status,
    }
    return render(request, 'custom_admin/tuition/students_list.html', context)


@user_passes_test(is_staff_user)
def tuition_student_create_view(request):
    """Create a new tuition student with optional enrollment"""
    standards = Standard.objects.filter(is_active=True).order_by('order')
    batches = TuitionBatch.objects.filter(is_active=True).select_related('standard', 'subject')
    subjects = Subject.objects.filter(is_active=True).order_by('name')
    faculty_list = TeacherProfile.objects.filter(is_active=True).select_related('user').order_by('user__name')

    if request.method == 'POST':
        try:
            name = request.POST.get('name', '').strip()
            email = request.POST.get('email', '').strip()
            phone = request.POST.get('phone', '').strip()
            parent_name = request.POST.get('parent_name', '').strip()
            parent_phone = request.POST.get('parent_phone', '').strip()
            parent_email = request.POST.get('parent_email', '').strip()
            address = request.POST.get('address', '').strip()
            standard_id = request.POST.get('standard')
            school_name = request.POST.get('school_name', '').strip()
            notes = request.POST.get('notes', '').strip()
            date_of_birth = request.POST.get('date_of_birth', '').strip()

            if not name or not phone or not parent_name or not parent_phone:
                messages.error(request, 'Name, phone, parent name, and parent phone are required.')
                return redirect('custom_admin:tuition_student_create')

            # Email is required for app login
            if not email:
                messages.error(request, 'Email is required so the student can login to the app.')
                return redirect('custom_admin:tuition_student_create')

            # Check if email already exists
            if User.objects.filter(email=email).exists():
                messages.error(request, f'A user with email "{email}" already exists.')
                return redirect('custom_admin:tuition_student_create')

            # Generate a temporary password
            import secrets
            temp_password = secrets.token_urlsafe(8)

            # Create User account first (so student can login to app)
            user = User.objects.create_user(
                email=email,
                name=name,
                password=temp_password,
                role='student',
                student_type='offline',
                phone_number=phone,
                address=address or None,
                parent_name=parent_name,
                parent_phone=parent_phone,
                parent_email=parent_email or None,
                school_name=school_name or None,
                standard_id=standard_id if standard_id else None,
                date_of_birth=date_of_birth if date_of_birth else None,
            )

            # Handle photo upload to User model
            if 'photo' in request.FILES:
                user.photo = request.FILES['photo']
                user.save()

            # Create TuitionStudent linked to User
            student = TuitionStudent.objects.create(
                user=user,  # Link to User account
                name=name,
                email=email,
                phone=phone,
                parent_name=parent_name,
                parent_phone=parent_phone,
                parent_email=parent_email or None,
                address=address or None,
                standard_id=standard_id if standard_id else None,
                school_name=school_name or None,
                notes=notes or None
            )

            # Copy photo to TuitionStudent as well
            if 'photo' in request.FILES:
                student.photo = request.FILES['photo']
                student.save()

            # Log the temporary password for admin to share with student
            logger.info(f"Created tuition student {name} with email {email}. Temp password: {temp_password}")

            # Handle optional enrollment
            add_enrollment = request.POST.get('add_enrollment')
            if add_enrollment:
                enrollment_mode = request.POST.get('enrollment_mode', 'batch')
                enrollment_start_date = request.POST.get('enrollment_start_date')

                enrollment_data = {
                    'student': student,
                    'mode': enrollment_mode,
                    'start_date': enrollment_start_date,
                    'is_active': True,
                }

                if enrollment_mode == 'batch':
                    batch_id = request.POST.get('enrollment_batch')
                    if batch_id:
                        enrollment_data['batch_id'] = batch_id
                        TuitionEnrollment.objects.create(**enrollment_data)
                        messages.success(request, f'Student "{name}" created and enrolled in batch successfully.')
                    else:
                        messages.success(request, f'Student "{name}" created. No batch selected for enrollment.')
                else:
                    # Individual or Home tuition
                    subject_id = request.POST.get('enrollment_subject')
                    monthly_fee = request.POST.get('enrollment_monthly_fee')
                    teacher_id = request.POST.get('enrollment_teacher')
                    tuition_address = request.POST.get('enrollment_tuition_address', '').strip()

                    if subject_id and monthly_fee:
                        enrollment_data['subject_id'] = subject_id
                        enrollment_data['monthly_fee'] = Decimal(monthly_fee)
                        enrollment_data['teacher_id'] = teacher_id if teacher_id else None
                        if enrollment_mode == 'home' and tuition_address:
                            enrollment_data['tuition_address'] = tuition_address
                        TuitionEnrollment.objects.create(**enrollment_data)
                        messages.success(request, f'Student "{name}" created and enrolled successfully.')
                    else:
                        messages.success(request, f'Student "{name}" created. Missing subject/fee for enrollment.')
            else:
                messages.success(request, f'Student "{name}" created successfully.')

            # Show temporary password to admin
            messages.info(request, f'App Login: Email: {email}, Temporary Password: {temp_password}')

            return redirect('custom_admin:tuition_student_detail', student_id=student.id)

        except Exception as e:
            logger.error(f"Error creating student: {str(e)}")
            messages.error(request, f'Error creating student: {str(e)}')

    context = {
        'page_title': 'Add Student',
        'standards': standards,
        'batches': batches,
        'subjects': subjects,
        'faculty_list': faculty_list,
    }
    return render(request, 'custom_admin/tuition/student_form.html', context)


@user_passes_test(is_staff_user)
def tuition_student_detail_view(request, student_id):
    """View student details"""
    student = get_object_or_404(TuitionStudent, id=student_id)

    enrollments = TuitionEnrollment.objects.filter(
        student=student
    ).select_related('batch', 'subject', 'teacher').order_by('-is_active', '-created_at')

    # Get fee records
    fee_records = TuitionFee.objects.filter(
        enrollment__student=student
    ).select_related('enrollment__batch').order_by('-year', '-month')[:12]

    # Get attendance records
    attendance_records = TuitionAttendance.objects.filter(
        enrollment__student=student
    ).order_by('-date')[:20]

    context = {
        'page_title': f'Student: {student.name}',
        'student': student,
        'enrollments': enrollments,
        'fee_records': fee_records,
        'attendance_records': attendance_records,
    }
    return render(request, 'custom_admin/tuition/student_detail.html', context)


@user_passes_test(is_staff_user)
def tuition_student_edit_view(request, student_id):
    """Edit a tuition student"""
    student = get_object_or_404(TuitionStudent, id=student_id)
    standards = Standard.objects.filter(is_active=True).order_by('order')

    if request.method == 'POST':
        try:
            name = request.POST.get('name', '').strip()
            email = request.POST.get('email', '').strip()
            phone = request.POST.get('phone', '').strip()
            parent_name = request.POST.get('parent_name', '').strip()
            parent_phone = request.POST.get('parent_phone', '').strip()
            parent_email = request.POST.get('parent_email', '').strip()
            address = request.POST.get('address', '').strip()
            standard_id = request.POST.get('standard')
            school_name = request.POST.get('school_name', '').strip()
            notes = request.POST.get('notes', '').strip()
            date_of_birth = request.POST.get('date_of_birth', '').strip()
            is_active = request.POST.get('is_active') == 'on'

            # Update TuitionStudent
            student.name = name
            student.email = email or None
            student.phone = phone
            student.parent_name = parent_name
            student.parent_phone = parent_phone
            student.parent_email = parent_email or None
            student.address = address or None
            student.standard_id = standard_id if standard_id else None
            student.school_name = school_name or None
            student.notes = notes or None
            student.is_active = is_active

            # Handle photo upload
            if 'photo' in request.FILES:
                student.photo = request.FILES['photo']

            student.save()

            # Sync data to linked User account (if exists)
            if student.user:
                user = student.user
                user.name = name
                user.phone_number = phone
                user.address = address or None
                user.parent_name = parent_name
                user.parent_phone = parent_phone
                user.parent_email = parent_email or None
                user.school_name = school_name or None
                user.standard_id = standard_id if standard_id else None
                user.date_of_birth = date_of_birth if date_of_birth else None
                user.is_active = is_active

                # Update email only if changed and not already taken
                if email and email != user.email:
                    if not User.objects.filter(email=email).exclude(id=user.id).exists():
                        user.email = email
                    else:
                        messages.warning(request, f'Email "{email}" is already in use by another user. User email not updated.')

                if 'photo' in request.FILES:
                    user.photo = request.FILES['photo']

                user.save()

            messages.success(request, f'Student "{student.name}" updated successfully.')
            return redirect('custom_admin:tuition_student_detail', student_id=student_id)

        except Exception as e:
            logger.error(f"Error updating student: {str(e)}")
            messages.error(request, f'Error updating student: {str(e)}')

    context = {
        'page_title': 'Edit Student',
        'student': student,
        'standards': standards,
    }
    return render(request, 'custom_admin/tuition/student_form.html', context)


@user_passes_test(is_staff_user)
def tuition_student_delete_view(request, student_id):
    """Delete a tuition student"""
    student = get_object_or_404(TuitionStudent, id=student_id)

    if request.method == 'POST':
        try:
            if student.enrollments.filter(is_active=True).exists():
                messages.error(request, f'Cannot delete "{student.name}" - has active enrollments. Deactivate enrollments first.')
                return redirect('custom_admin:tuition_students_list')

            name = student.name
            student.delete()
            messages.success(request, f'Student "{name}" deleted successfully.')
        except Exception as e:
            logger.error(f"Error deleting student: {str(e)}")
            messages.error(request, f'Error deleting student: {str(e)}')

    return redirect('custom_admin:tuition_students_list')


# =============================================================================
# ENROLLMENTS
# =============================================================================

@user_passes_test(is_staff_user)
def tuition_enrollments_list_view(request):
    """List all enrollments"""
    enrollments = TuitionEnrollment.objects.select_related(
        'student', 'batch', 'subject', 'teacher'
    ).order_by('-created_at')

    # Filters
    mode = request.GET.get('mode')
    status = request.GET.get('status')
    batch_id = request.GET.get('batch')

    if mode:
        enrollments = enrollments.filter(mode=mode)
    if status == 'active':
        enrollments = enrollments.filter(is_active=True)
    elif status == 'inactive':
        enrollments = enrollments.filter(is_active=False)
    if batch_id:
        enrollments = enrollments.filter(batch_id=batch_id)

    paginator = Paginator(enrollments, 20)
    page = request.GET.get('page', 1)
    enrollments = paginator.get_page(page)

    batches = TuitionBatch.objects.filter(is_active=True).order_by('name')

    context = {
        'page_title': 'Tuition Enrollments',
        'enrollments': enrollments,
        'batches': batches,
        'selected_mode': mode,
        'selected_status': status,
        'selected_batch': batch_id,
        'mode_choices': TuitionEnrollment.TUITION_MODE_CHOICES,
    }
    return render(request, 'custom_admin/tuition/enrollments_list.html', context)


@user_passes_test(is_staff_user)
def tuition_enrollment_create_view(request):
    """Create a new enrollment"""
    students = TuitionStudent.objects.filter(is_active=True).order_by('name')
    batches = TuitionBatch.objects.filter(is_active=True).select_related('standard', 'subject')
    subjects = Subject.objects.filter(is_active=True).order_by('name')
    teachers = TeacherProfile.objects.filter(is_active=True, can_teach_offline=True).select_related('user').order_by('user__name')

    if request.method == 'POST':
        try:
            student_id = request.POST.get('student')
            mode = request.POST.get('mode')
            batch_id = request.POST.get('batch')
            subject_id = request.POST.get('subject')
            teacher_id = request.POST.get('teacher')
            monthly_fee = request.POST.get('monthly_fee')
            start_date = request.POST.get('start_date')
            end_date = request.POST.get('end_date')
            tuition_address = request.POST.get('tuition_address', '').strip()

            # Parse schedule for individual/home modes
            schedule = {}
            for day in ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']:
                time_slot = request.POST.get(f'schedule_{day}', '').strip()
                if time_slot:
                    schedule[day] = time_slot

            if not student_id or not mode or not start_date:
                messages.error(request, 'Student, mode, and start date are required.')
                return redirect('custom_admin:tuition_enrollment_create')

            if mode == 'batch' and not batch_id:
                messages.error(request, 'Batch is required for batch mode.')
                return redirect('custom_admin:tuition_enrollment_create')

            if mode in ['individual', 'home'] and not subject_id:
                messages.error(request, 'Subject is required for individual/home mode.')
                return redirect('custom_admin:tuition_enrollment_create')

            enrollment = TuitionEnrollment.objects.create(
                student_id=student_id,
                mode=mode,
                batch_id=batch_id if mode == 'batch' else None,
                subject_id=subject_id if mode != 'batch' else None,
                teacher_id=teacher_id if teacher_id and mode != 'batch' else None,
                monthly_fee=Decimal(monthly_fee) if monthly_fee and mode != 'batch' else None,
                schedule=schedule if mode != 'batch' else {},
                start_date=start_date,
                end_date=end_date if end_date else None,
                tuition_address=tuition_address if mode == 'home' else None
            )

            messages.success(request, f'Enrollment created successfully.')
            return redirect('custom_admin:tuition_enrollment_detail', enrollment_id=enrollment.id)

        except Exception as e:
            logger.error(f"Error creating enrollment: {str(e)}")
            messages.error(request, f'Error creating enrollment: {str(e)}')

    context = {
        'page_title': 'New Enrollment',
        'students': students,
        'batches': batches,
        'subjects': subjects,
        'teachers': teachers,
        'mode_choices': TuitionEnrollment.TUITION_MODE_CHOICES,
    }
    return render(request, 'custom_admin/tuition/enrollment_form.html', context)


@user_passes_test(is_staff_user)
def tuition_enrollment_detail_view(request, enrollment_id):
    """View enrollment details"""
    enrollment = get_object_or_404(
        TuitionEnrollment.objects.select_related(
            'student', 'batch', 'subject', 'teacher'
        ),
        id=enrollment_id
    )

    # Get fee records
    fee_records = TuitionFee.objects.filter(
        enrollment=enrollment
    ).order_by('-year', '-month')

    # Get attendance records
    attendance_records = TuitionAttendance.objects.filter(
        enrollment=enrollment
    ).order_by('-date')[:30]

    context = {
        'page_title': f'Enrollment: {enrollment}',
        'enrollment': enrollment,
        'fee_records': fee_records,
        'attendance_records': attendance_records,
    }
    return render(request, 'custom_admin/tuition/enrollment_detail.html', context)


@user_passes_test(is_staff_user)
def tuition_enrollment_edit_view(request, enrollment_id):
    """Edit an enrollment"""
    enrollment = get_object_or_404(TuitionEnrollment, id=enrollment_id)
    students = TuitionStudent.objects.filter(is_active=True).order_by('name')
    batches = TuitionBatch.objects.filter(is_active=True).select_related('standard', 'subject')
    subjects = Subject.objects.filter(is_active=True).order_by('name')
    teachers = TeacherProfile.objects.filter(is_active=True, can_teach_offline=True).select_related('user').order_by('user__name')

    if request.method == 'POST':
        try:
            enrollment.student_id = request.POST.get('student')
            mode = request.POST.get('mode')
            enrollment.mode = mode

            if mode == 'batch':
                enrollment.batch_id = request.POST.get('batch')
                enrollment.subject = None
                enrollment.teacher = None
                enrollment.monthly_fee = None
                enrollment.schedule = {}
                enrollment.tuition_address = None
            else:
                enrollment.batch = None
                enrollment.subject_id = request.POST.get('subject')
                teacher_id = request.POST.get('teacher')
                enrollment.teacher_id = teacher_id if teacher_id else None
                monthly_fee = request.POST.get('monthly_fee')
                enrollment.monthly_fee = Decimal(monthly_fee) if monthly_fee else None

                schedule = {}
                for day in ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']:
                    time_slot = request.POST.get(f'schedule_{day}', '').strip()
                    if time_slot:
                        schedule[day] = time_slot
                enrollment.schedule = schedule

                if mode == 'home':
                    enrollment.tuition_address = request.POST.get('tuition_address', '').strip() or None
                else:
                    enrollment.tuition_address = None

            enrollment.start_date = request.POST.get('start_date')
            end_date = request.POST.get('end_date')
            enrollment.end_date = end_date if end_date else None
            enrollment.is_active = request.POST.get('is_active') == 'on'

            enrollment.save()
            messages.success(request, 'Enrollment updated successfully.')
            return redirect('custom_admin:tuition_enrollment_detail', enrollment_id=enrollment_id)

        except Exception as e:
            logger.error(f"Error updating enrollment: {str(e)}")
            messages.error(request, f'Error updating enrollment: {str(e)}')

    context = {
        'page_title': 'Edit Enrollment',
        'enrollment': enrollment,
        'students': students,
        'batches': batches,
        'subjects': subjects,
        'teachers': teachers,
        'mode_choices': TuitionEnrollment.TUITION_MODE_CHOICES,
    }
    return render(request, 'custom_admin/tuition/enrollment_form.html', context)


# =============================================================================
# ATTENDANCE
# =============================================================================

@user_passes_test(is_staff_user)
def tuition_attendance_list_view(request):
    """List attendance records"""
    attendance = TuitionAttendance.objects.select_related(
        'enrollment__student', 'batch', 'marked_by'
    ).order_by('-date', '-created_at')

    # Filters
    attendance_date = request.GET.get('date')
    batch_id = request.GET.get('batch')
    status = request.GET.get('status')

    if attendance_date:
        attendance = attendance.filter(date=attendance_date)
    if batch_id:
        attendance = attendance.filter(batch_id=batch_id)
    if status:
        attendance = attendance.filter(status=status)

    paginator = Paginator(attendance, 50)
    page = request.GET.get('page', 1)
    attendance = paginator.get_page(page)

    batches = TuitionBatch.objects.filter(is_active=True).order_by('name')

    context = {
        'page_title': 'Tuition Attendance',
        'attendance': attendance,
        'batches': batches,
        'selected_date': attendance_date or date.today().isoformat(),
        'selected_batch': batch_id,
        'selected_status': status,
        'status_choices': TuitionAttendance.STATUS_CHOICES,
    }
    return render(request, 'custom_admin/tuition/attendance_list.html', context)


@user_passes_test(is_staff_user)
def mark_attendance_view(request):
    """Mark attendance for a batch on a date"""
    batches = TuitionBatch.objects.filter(is_active=True).select_related('standard', 'subject')

    batch_id = request.GET.get('batch')
    attendance_date = request.GET.get('date', date.today().isoformat())

    batch = None
    enrollments = []
    existing_attendance = {}

    if batch_id:
        batch = get_object_or_404(TuitionBatch, id=batch_id)
        enrollments = TuitionEnrollment.objects.filter(
            batch=batch, is_active=True
        ).select_related('student')

        # Get existing attendance for this date
        existing = TuitionAttendance.objects.filter(
            batch=batch, date=attendance_date
        )
        for att in existing:
            existing_attendance[att.enrollment_id] = att

    if request.method == 'POST':
        try:
            attendance_date = request.POST.get('attendance_date')
            batch_id = request.POST.get('batch_id')
            batch = get_object_or_404(TuitionBatch, id=batch_id)

            enrollments = TuitionEnrollment.objects.filter(
                batch=batch, is_active=True
            )

            for enrollment in enrollments:
                status = request.POST.get(f'status_{enrollment.id}', 'present')
                check_in = request.POST.get(f'check_in_{enrollment.id}', '').strip()
                check_out = request.POST.get(f'check_out_{enrollment.id}', '').strip()
                notes = request.POST.get(f'notes_{enrollment.id}', '').strip()

                # Update or create attendance
                att, created = TuitionAttendance.objects.update_or_create(
                    enrollment=enrollment,
                    date=attendance_date,
                    defaults={
                        'batch': batch,
                        'status': status,
                        'check_in_time': check_in if check_in else None,
                        'check_out_time': check_out if check_out else None,
                        'notes': notes or None,
                        'marked_by': request.user
                    }
                )

            messages.success(request, f'Attendance marked for {batch.name} on {attendance_date}.')
            return redirect('custom_admin:tuition_attendance_list')

        except Exception as e:
            logger.error(f"Error marking attendance: {str(e)}")
            messages.error(request, f'Error marking attendance: {str(e)}')

    context = {
        'page_title': 'Mark Attendance',
        'batches': batches,
        'batch': batch,
        'enrollments': enrollments,
        'existing_attendance': existing_attendance,
        'attendance_date': attendance_date,
        'status_choices': TuitionAttendance.STATUS_CHOICES,
    }
    return render(request, 'custom_admin/tuition/attendance_mark.html', context)


@user_passes_test(is_staff_user)
def batch_attendance_view(request, batch_id):
    """View/mark attendance for a specific batch"""
    batch = get_object_or_404(TuitionBatch, id=batch_id)
    attendance_date = request.GET.get('date', date.today().isoformat())

    enrollments = TuitionEnrollment.objects.filter(
        batch=batch, is_active=True
    ).select_related('student')

    # Get existing attendance
    existing = TuitionAttendance.objects.filter(
        batch=batch, date=attendance_date
    )
    existing_attendance = {att.enrollment_id: att for att in existing}

    if request.method == 'POST':
        try:
            for enrollment in enrollments:
                status = request.POST.get(f'status_{enrollment.id}', 'present')
                check_in = request.POST.get(f'check_in_{enrollment.id}', '').strip()
                check_out = request.POST.get(f'check_out_{enrollment.id}', '').strip()
                notes = request.POST.get(f'notes_{enrollment.id}', '').strip()

                TuitionAttendance.objects.update_or_create(
                    enrollment=enrollment,
                    date=attendance_date,
                    defaults={
                        'batch': batch,
                        'status': status,
                        'check_in_time': check_in if check_in else None,
                        'check_out_time': check_out if check_out else None,
                        'notes': notes or None,
                        'marked_by': request.user
                    }
                )

            messages.success(request, f'Attendance saved for {attendance_date}.')
            return redirect('custom_admin:batch_attendance', batch_id=batch_id)

        except Exception as e:
            logger.error(f"Error saving attendance: {str(e)}")
            messages.error(request, f'Error saving attendance: {str(e)}')

    context = {
        'page_title': f'Attendance: {batch.name}',
        'batch': batch,
        'enrollments': enrollments,
        'existing_attendance': existing_attendance,
        'attendance_date': attendance_date,
        'status_choices': TuitionAttendance.STATUS_CHOICES,
    }
    return render(request, 'custom_admin/tuition/batch_attendance.html', context)


# =============================================================================
# FEE COLLECTION
# =============================================================================

@user_passes_test(is_staff_user)
def tuition_fees_list_view(request):
    """List all fee records"""
    fees = TuitionFee.objects.select_related(
        'enrollment__student', 'enrollment__batch', 'created_by'
    ).order_by('-year', '-month', '-created_at')

    # Filters
    status = request.GET.get('status')
    month = request.GET.get('month')
    year = request.GET.get('year')
    search = request.GET.get('search', '').strip()

    if status:
        fees = fees.filter(status=status)
    if month:
        fees = fees.filter(month=int(month))
    if year:
        fees = fees.filter(year=int(year))
    if search:
        fees = fees.filter(
            Q(enrollment__student__name__icontains=search) |
            Q(enrollment__student__phone__icontains=search)
        )

    # Get summary
    summary = fees.aggregate(
        total=Sum('total_amount'),
        collected=Sum('paid_amount'),
        pending=Sum('total_amount') - Sum('paid_amount')
    )

    paginator = Paginator(fees, 30)
    page = request.GET.get('page', 1)
    fees = paginator.get_page(page)

    # Years for filter
    years = TuitionFee.objects.values_list('year', flat=True).distinct().order_by('-year')

    context = {
        'page_title': 'Tuition Fees',
        'fees': fees,
        'summary': summary,
        'years': list(years) if years else [date.today().year],
        'months': list(range(1, 13)),
        'selected_status': status,
        'selected_month': month,
        'selected_year': year,
        'search': search,
        'status_choices': TuitionFee.STATUS_CHOICES,
    }
    return render(request, 'custom_admin/tuition/fees_list.html', context)


@user_passes_test(is_staff_user)
def generate_monthly_fees_view(request):
    """Generate monthly fees for all active enrollments"""
    if request.method == 'POST':
        try:
            month = int(request.POST.get('month', date.today().month))
            year = int(request.POST.get('year', date.today().year))

            count = generate_monthly_fees_for_all(month, year, request.user)

            if count > 0:
                messages.success(request, f'Generated {count} fee records for {month}/{year}.')
            else:
                messages.info(request, f'No new fee records to generate for {month}/{year}.')

            return redirect('custom_admin:tuition_fees_list')

        except Exception as e:
            logger.error(f"Error generating fees: {str(e)}")
            messages.error(request, f'Error generating fees: {str(e)}')

    context = {
        'page_title': 'Generate Monthly Fees',
        'current_month': date.today().month,
        'current_year': date.today().year,
        'months': list(range(1, 13)),
        'years': list(range(date.today().year - 1, date.today().year + 2)),
    }
    return render(request, 'custom_admin/tuition/fee_generate.html', context)


@user_passes_test(is_staff_user)
def tuition_fee_detail_view(request, fee_id):
    """View fee details"""
    fee = get_object_or_404(
        TuitionFee.objects.select_related(
            'enrollment__student', 'enrollment__batch', 'created_by', 'income_record'
        ),
        id=fee_id
    )

    context = {
        'page_title': f'Fee: {fee.enrollment.student.name} - {fee.month_name} {fee.year}',
        'fee': fee,
    }
    return render(request, 'custom_admin/tuition/fee_detail.html', context)


@user_passes_test(is_staff_user)
def collect_fee_view(request, fee_id):
    """Collect payment for a fee"""
    fee = get_object_or_404(
        TuitionFee.objects.select_related('enrollment__student', 'enrollment__batch'),
        id=fee_id
    )

    if fee.status == 'paid':
        messages.warning(request, 'This fee is already fully paid.')
        return redirect('custom_admin:tuition_fee_detail', fee_id=fee_id)

    if request.method == 'POST':
        try:
            amount = Decimal(request.POST.get('amount', '0'))
            payment_method = request.POST.get('payment_method', 'cash')
            transaction_id = request.POST.get('transaction_id', '').strip()
            notes = request.POST.get('notes', '').strip()

            if amount <= 0:
                messages.error(request, 'Amount must be greater than 0.')
                return redirect('custom_admin:collect_fee', fee_id=fee_id)

            if amount > fee.outstanding:
                messages.error(request, f'Amount cannot exceed outstanding amount (₹{fee.outstanding}).')
                return redirect('custom_admin:collect_fee', fee_id=fee_id)

            collect_tuition_fee(
                fee=fee,
                amount=amount,
                payment_method=payment_method,
                transaction_id=transaction_id or None,
                notes=notes or None,
                collected_by=request.user
            )

            messages.success(request, f'Payment of ₹{amount} collected successfully.')
            return redirect('custom_admin:tuition_fee_detail', fee_id=fee_id)

        except Exception as e:
            logger.error(f"Error collecting fee: {str(e)}")
            messages.error(request, f'Error collecting fee: {str(e)}')

    context = {
        'page_title': 'Collect Payment',
        'fee': fee,
        'payment_methods': TuitionFee.PAYMENT_METHOD_CHOICES,
    }
    return render(request, 'custom_admin/tuition/fee_collect.html', context)


@user_passes_test(is_staff_user)
def fee_receipt_view(request, fee_id):
    """Generate printable receipt"""
    fee = get_object_or_404(
        TuitionFee.objects.select_related(
            'enrollment__student', 'enrollment__batch', 'enrollment__batch__standard',
            'enrollment__batch__subject', 'enrollment__subject'
        ),
        id=fee_id
    )

    context = {
        'page_title': f'Receipt: {fee.receipt_number or fee_id}',
        'fee': fee,
    }
    return render(request, 'custom_admin/tuition/fee_receipt.html', context)


# =============================================================================
# API ENDPOINTS
# =============================================================================

@user_passes_test(is_staff_user)
def api_batch_students(request, batch_id):
    """Get students in a batch (for AJAX)"""
    batch = get_object_or_404(TuitionBatch, id=batch_id)
    enrollments = TuitionEnrollment.objects.filter(
        batch=batch, is_active=True
    ).select_related('student')

    students = [
        {
            'id': e.student.id,
            'name': e.student.name,
            'enrollment_id': e.id
        }
        for e in enrollments
    ]

    return JsonResponse({'students': students})


@user_passes_test(is_staff_user)
def api_student_enrollments(request, student_id):
    """Get enrollments for a student (for AJAX)"""
    student = get_object_or_404(TuitionStudent, id=student_id)
    enrollments = TuitionEnrollment.objects.filter(
        student=student, is_active=True
    ).select_related('batch', 'subject')

    data = [
        {
            'id': e.id,
            'mode': e.get_mode_display(),
            'batch': e.batch.name if e.batch else None,
            'subject': e.effective_subject.name if e.effective_subject else None,
            'fee': str(e.effective_fee)
        }
        for e in enrollments
    ]

    return JsonResponse({'enrollments': data})


@user_passes_test(is_staff_user)
def api_mark_overdue(request):
    """Mark overdue fees (for scheduled task or manual trigger)"""
    if request.method == 'POST':
        count = mark_overdue_fees()
        return JsonResponse({'success': True, 'updated': count})
    return JsonResponse({'error': 'POST required'}, status=405)


@user_passes_test(is_staff_user)
def api_seed_data(request):
    """Seed default data (for initial setup)"""
    if request.method == 'POST':
        result = seed_all_default_data()
        return JsonResponse({'success': True, 'result': result})
    return JsonResponse({'error': 'POST required'}, status=405)
