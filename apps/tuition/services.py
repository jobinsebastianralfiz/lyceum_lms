"""
Tuition Management Services
"""
from datetime import date, timedelta
from decimal import Decimal
from django.db import transaction
from django.db.models import Sum, Count, Q, Avg
import calendar


def seed_default_standards():
    """Create default standards (Class 1-12)"""
    from .models import Standard

    standards_data = [
        {'name': 'Class 1', 'code': '1', 'order': 1},
        {'name': 'Class 2', 'code': '2', 'order': 2},
        {'name': 'Class 3', 'code': '3', 'order': 3},
        {'name': 'Class 4', 'code': '4', 'order': 4},
        {'name': 'Class 5', 'code': '5', 'order': 5},
        {'name': 'Class 6', 'code': '6', 'order': 6},
        {'name': 'Class 7', 'code': '7', 'order': 7},
        {'name': 'Class 8', 'code': '8', 'order': 8},
        {'name': 'Class 9', 'code': '9', 'order': 9},
        {'name': 'Class 10', 'code': '10', 'order': 10},
        {'name': 'Plus One (Class 11)', 'code': '11', 'order': 11},
        {'name': 'Plus Two (Class 12)', 'code': '12', 'order': 12},
    ]

    created_count = 0
    for data in standards_data:
        standard, created = Standard.objects.get_or_create(
            code=data['code'],
            defaults={'name': data['name'], 'order': data['order']}
        )
        if created:
            created_count += 1

    return created_count


def seed_default_subjects():
    """Create default subjects"""
    from .models import Subject

    subjects_data = [
        {'name': 'Mathematics', 'code': 'MATH', 'icon': 'ti ti-math', 'color': '#3b82f6'},
        {'name': 'Physics', 'code': 'PHY', 'icon': 'ti ti-atom', 'color': '#8b5cf6'},
        {'name': 'Chemistry', 'code': 'CHEM', 'icon': 'ti ti-flask', 'color': '#10b981'},
        {'name': 'Biology', 'code': 'BIO', 'icon': 'ti ti-plant', 'color': '#22c55e'},
        {'name': 'English', 'code': 'ENG', 'icon': 'ti ti-language', 'color': '#f59e0b'},
        {'name': 'Hindi', 'code': 'HIN', 'icon': 'ti ti-book', 'color': '#ef4444'},
        {'name': 'Malayalam', 'code': 'MAL', 'icon': 'ti ti-book-2', 'color': '#06b6d4'},
        {'name': 'Social Science', 'code': 'SST', 'icon': 'ti ti-world', 'color': '#f97316'},
        {'name': 'Computer Science', 'code': 'CS', 'icon': 'ti ti-code', 'color': '#6366f1'},
        {'name': 'Accountancy', 'code': 'ACC', 'icon': 'ti ti-calculator', 'color': '#14b8a6'},
        {'name': 'Economics', 'code': 'ECO', 'icon': 'ti ti-chart-line', 'color': '#84cc16'},
        {'name': 'Business Studies', 'code': 'BUS', 'icon': 'ti ti-briefcase', 'color': '#a855f7'},
    ]

    created_count = 0
    for data in subjects_data:
        subject, created = Subject.objects.get_or_create(
            code=data['code'],
            defaults={
                'name': data['name'],
                'icon': data['icon'],
                'color': data['color']
            }
        )
        if created:
            created_count += 1

    return created_count


def seed_all_default_data():
    """Seed all default data"""
    standards_count = seed_default_standards()
    subjects_count = seed_default_subjects()
    return {
        'standards': standards_count,
        'subjects': subjects_count
    }


def generate_monthly_fees_for_enrollment(enrollment, month, year, created_by=None):
    """Generate a monthly fee record for an enrollment"""
    from .models import TuitionFee

    # Check if fee already exists
    existing = TuitionFee.objects.filter(
        enrollment=enrollment,
        month=month,
        year=year
    ).first()

    if existing:
        return existing, False

    # Calculate due date (10th of the month)
    due_date = date(year, month, 10)

    fee = TuitionFee.objects.create(
        enrollment=enrollment,
        month=month,
        year=year,
        fee_amount=enrollment.effective_fee,
        discount=Decimal('0'),
        total_amount=enrollment.effective_fee,
        due_date=due_date,
        created_by=created_by
    )

    return fee, True


def generate_monthly_fees_for_all(month, year, created_by=None):
    """Generate monthly fees for all active enrollments"""
    from .models import TuitionEnrollment

    active_enrollments = TuitionEnrollment.objects.filter(
        is_active=True,
        start_date__lte=date(year, month, 1)
    ).select_related('student', 'batch', 'subject')

    created_count = 0
    for enrollment in active_enrollments:
        # Skip if enrollment ended before this month
        if enrollment.end_date and enrollment.end_date < date(year, month, 1):
            continue

        fee, created = generate_monthly_fees_for_enrollment(
            enrollment, month, year, created_by
        )
        if created:
            created_count += 1

    return created_count


def collect_tuition_fee(fee, amount, payment_method, transaction_id=None, notes=None, collected_by=None):
    """
    Collect payment for a tuition fee.
    Creates income record in finance module.
    """
    from apps.finance.models import Income, IncomeCategory

    fee.paid_amount += Decimal(str(amount))
    fee.payment_method = payment_method
    fee.payment_date = date.today()
    fee.transaction_id = transaction_id

    if notes:
        fee.notes = (fee.notes or '') + f"\n{notes}" if fee.notes else notes

    # Update status
    if fee.paid_amount >= fee.total_amount:
        fee.status = 'paid'
    elif fee.paid_amount > 0:
        fee.status = 'partial'

    # Generate receipt number if paid
    if fee.status == 'paid' and not fee.receipt_number:
        fee.receipt_number = f"TF-{fee.year}{fee.month:02d}-{fee.id:06d}"

    fee.save()

    # Create income record in finance module
    try:
        # Get or create Tuition Fees category
        category, _ = IncomeCategory.objects.get_or_create(
            slug='tuition-fees',
            defaults={
                'name': 'Tuition Fees',
                'source_type': 'other',
                'is_auto_imported': True,
                'icon': 'ti ti-school',
                'color': '#2ab673'
            }
        )

        income = Income.objects.create(
            title=f"Tuition Fee - {fee.enrollment.student.name} - {fee.month_name} {fee.year}",
            category=category,
            amount=Decimal(str(amount)),
            tax_amount=Decimal('0'),
            payment_method=payment_method,
            income_date=date.today(),
            payer_name=fee.enrollment.student.parent_name,
            payer_email=fee.enrollment.student.parent_email,
            payer_phone=fee.enrollment.student.parent_phone,
            status='received',
            is_auto_imported=True,
            created_by=collected_by,
            notes=f"Tuition fee for {fee.enrollment.student.name} - {fee.month_name} {fee.year}"
        )

        fee.income_record = income
        fee.save()

    except Exception as e:
        # Log error but don't fail the fee collection
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error creating income record for tuition fee: {str(e)}")

    return fee


def get_tuition_dashboard_stats():
    """Get statistics for tuition dashboard"""
    from .models import TuitionStudent, TuitionBatch, TuitionEnrollment, TuitionFee, TuitionAttendance

    today = date.today()
    current_month = today.month
    current_year = today.year

    # Active counts
    active_students = TuitionStudent.objects.filter(is_active=True).count()
    active_batches = TuitionBatch.objects.filter(is_active=True).count()
    active_enrollments = TuitionEnrollment.objects.filter(is_active=True).count()

    # This month's fee collection
    this_month_fees = TuitionFee.objects.filter(
        month=current_month,
        year=current_year
    )

    total_expected = this_month_fees.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
    total_collected = this_month_fees.aggregate(total=Sum('paid_amount'))['total'] or Decimal('0')
    pending_amount = total_expected - total_collected

    # Pending fees count
    pending_fees_count = TuitionFee.objects.filter(
        status__in=['pending', 'partial', 'overdue']
    ).count()

    # Today's classes (batches scheduled for today)
    day_name = today.strftime('%a').lower()[:3]
    # This is approximate - would need to parse schedule JSON
    todays_batches = TuitionBatch.objects.filter(is_active=True).count()

    # This month's attendance
    month_start = date(current_year, current_month, 1)
    attendance_stats = TuitionAttendance.objects.filter(
        date__gte=month_start,
        date__lte=today
    ).aggregate(
        total=Count('id'),
        present=Count('id', filter=Q(status='present')),
        absent=Count('id', filter=Q(status='absent')),
        late=Count('id', filter=Q(status='late'))
    )

    attendance_rate = 0
    if attendance_stats['total'] > 0:
        attendance_rate = round(
            (attendance_stats['present'] + attendance_stats['late']) /
            attendance_stats['total'] * 100, 1
        )

    return {
        'active_students': active_students,
        'active_batches': active_batches,
        'active_enrollments': active_enrollments,
        'total_expected': total_expected,
        'total_collected': total_collected,
        'pending_amount': pending_amount,
        'pending_fees_count': pending_fees_count,
        'todays_batches': todays_batches,
        'attendance_rate': attendance_rate,
        'attendance_stats': attendance_stats,
    }


def mark_overdue_fees():
    """Mark fees as overdue if past due date"""
    from .models import TuitionFee

    today = date.today()

    updated = TuitionFee.objects.filter(
        status__in=['pending', 'partial'],
        due_date__lt=today
    ).update(status='overdue')

    return updated
