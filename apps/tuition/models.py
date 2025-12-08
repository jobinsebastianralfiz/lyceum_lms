from django.db import models
from django.conf import settings


class Standard(models.Model):
    """Class/Grade level - Class 1 to 12, or custom"""
    name = models.CharField(max_length=50)  # "Class 1", "Plus One", "Custom"
    code = models.CharField(max_length=10, unique=True)  # "1", "11", "C1"
    order = models.PositiveIntegerField(default=0)  # For sorting
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tuition_standards'
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class Subject(models.Model):
    """Subjects offered for tuition"""
    name = models.CharField(max_length=100)  # "Mathematics", "Physics"
    code = models.CharField(max_length=20, unique=True)  # "MATH", "PHY"
    standards = models.ManyToManyField(Standard, related_name='subjects', blank=True)
    description = models.TextField(blank=True, null=True)
    icon = models.CharField(max_length=50, default='ti ti-book')
    color = models.CharField(max_length=7, default='#5d87ff')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tuition_subjects'
        ordering = ['name']

    def __str__(self):
        return self.name


class TuitionBatch(models.Model):
    """Batch for group classes at center"""
    name = models.CharField(max_length=100)  # "Morning Batch - Class 10 Maths"
    code = models.CharField(max_length=20, unique=True)
    standard = models.ForeignKey(Standard, on_delete=models.CASCADE, related_name='batches')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='batches')

    # Schedule (e.g., {"mon": "10:00-11:00", "wed": "10:00-11:00", "fri": "10:00-11:00"})
    schedule = models.JSONField(default=dict, blank=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)

    # Capacity
    max_students = models.PositiveIntegerField(default=30)

    # Location (classroom/hall at center)
    location = models.CharField(max_length=100, blank=True, null=True)  # "Room 101", "Hall A"

    # Fee
    monthly_fee = models.DecimalField(max_digits=10, decimal_places=2)

    # Teacher (unified - same profile for online and offline)
    teacher = models.ForeignKey(
        'teachers.TeacherProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='teaching_batches'
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tuition_batches'
        ordering = ['-created_at']
        verbose_name_plural = 'Tuition Batches'

    def __str__(self):
        return f"{self.name} ({self.standard.name} - {self.subject.name})"

    @property
    def current_strength(self):
        return self.enrollments.filter(is_active=True).count()

    @property
    def is_full(self):
        return self.current_strength >= self.max_students

    @property
    def available_spots(self):
        return max(0, self.max_students - self.current_strength)


class TuitionStudent(models.Model):
    """Offline/Tuition student profile"""
    # Can link to existing user or be standalone
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tuition_profile'
    )

    # Basic Info
    name = models.CharField(max_length=200)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=20)

    # Parent/Guardian
    parent_name = models.CharField(max_length=200)
    parent_phone = models.CharField(max_length=20)
    parent_email = models.EmailField(blank=True, null=True)

    # Address
    address = models.TextField(blank=True, null=True)

    # Academic
    standard = models.ForeignKey(
        Standard,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='students'
    )
    school_name = models.CharField(max_length=200, blank=True, null=True)

    # Photo
    photo = models.ImageField(upload_to='tuition_students/', blank=True, null=True)

    # Status
    is_active = models.BooleanField(default=True)
    joined_date = models.DateField(auto_now_add=True)

    # Notes
    notes = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tuition_students'
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def active_enrollments(self):
        return self.enrollments.filter(is_active=True)

    @property
    def pending_fees(self):
        from django.db.models import Sum
        return self.enrollments.filter(
            is_active=True,
            fee_records__status__in=['pending', 'partial', 'overdue']
        ).aggregate(
            total=Sum('fee_records__outstanding')
        )['total'] or 0


class TuitionEnrollment(models.Model):
    """Student enrollment in batch or individual tuition"""
    TUITION_MODE_CHOICES = [
        ('batch', 'Batch Class'),           # Student joins a batch at center
        ('individual', 'Individual Class'),  # One-on-one at center
        ('home', 'Home Tuition'),            # Faculty goes to student's home
    ]

    student = models.ForeignKey(
        TuitionStudent,
        on_delete=models.CASCADE,
        related_name='enrollments'
    )
    mode = models.CharField(max_length=20, choices=TUITION_MODE_CHOICES)

    # For BATCH mode
    batch = models.ForeignKey(
        TuitionBatch,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='enrollments'
    )

    # For INDIVIDUAL/HOME modes
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='individual_enrollments'
    )
    monthly_fee = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    schedule = models.JSONField(default=dict, blank=True)  # {"tue": "16:00-17:00", "thu": "16:00-17:00"}
    teacher = models.ForeignKey(
        'teachers.TeacherProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='individual_tuitions'
    )

    # For HOME mode - student's address for tuition
    tuition_address = models.TextField(blank=True, null=True)

    # Dates
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tuition_enrollments'
        ordering = ['-created_at']

    def __str__(self):
        if self.mode == 'batch' and self.batch:
            return f"{self.student.name} - {self.batch.name}"
        return f"{self.student.name} - {self.effective_subject.name if self.effective_subject else 'N/A'} ({self.get_mode_display()})"

    @property
    def effective_fee(self):
        """Get monthly fee - from batch or individual setting"""
        if self.mode == 'batch' and self.batch:
            return self.batch.monthly_fee
        return self.monthly_fee

    @property
    def effective_subject(self):
        """Get subject - from batch or individual setting"""
        if self.mode == 'batch' and self.batch:
            return self.batch.subject
        return self.subject

    @property
    def effective_teacher(self):
        """Get teacher - from batch or individual setting"""
        if self.mode == 'batch' and self.batch:
            return self.batch.teacher
        return self.teacher

    @property
    def effective_schedule(self):
        """Get schedule - from batch or individual setting"""
        if self.mode == 'batch' and self.batch:
            return self.batch.schedule
        return self.schedule


class TuitionAttendance(models.Model):
    """Daily attendance for tuition classes"""
    STATUS_CHOICES = [
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
        ('excused', 'Excused'),
    ]

    enrollment = models.ForeignKey(
        TuitionEnrollment,
        on_delete=models.CASCADE,
        related_name='attendance_records'
    )
    date = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='present')

    # For batch classes - reference to batch for easier querying
    batch = models.ForeignKey(
        TuitionBatch,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='attendance_records'
    )

    # Timing
    check_in_time = models.TimeField(null=True, blank=True)
    check_out_time = models.TimeField(null=True, blank=True)

    # Notes
    notes = models.TextField(blank=True, null=True)

    marked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='marked_tuition_attendance'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'tuition_attendance'
        unique_together = ['enrollment', 'date']
        ordering = ['-date']
        verbose_name_plural = 'Tuition Attendance'

    def __str__(self):
        return f"{self.enrollment.student.name} - {self.date} - {self.get_status_display()}"


class TuitionFee(models.Model):
    """Monthly fee records for tuition students"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('partial', 'Partial'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
        ('waived', 'Waived'),
    ]
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('upi', 'UPI'),
        ('bank_transfer', 'Bank Transfer'),
        ('cheque', 'Cheque'),
        ('online', 'Online Payment'),
    ]

    enrollment = models.ForeignKey(
        TuitionEnrollment,
        on_delete=models.CASCADE,
        related_name='fee_records'
    )

    # Billing period
    month = models.PositiveIntegerField()  # 1-12
    year = models.PositiveIntegerField()

    # Amounts
    fee_amount = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Payment
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, blank=True, null=True)
    payment_date = models.DateField(null=True, blank=True)
    transaction_id = models.CharField(max_length=100, blank=True, null=True)

    # Due date
    due_date = models.DateField()

    # Receipt
    receipt_number = models.CharField(max_length=50, blank=True, null=True)

    # Notes
    notes = models.TextField(blank=True, null=True)

    # Finance integration - link to Income record when payment is made
    income_record = models.ForeignKey(
        'finance.Income',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tuition_fees'
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_tuition_fees'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tuition_fees'
        unique_together = ['enrollment', 'month', 'year']
        ordering = ['-year', '-month']

    def __str__(self):
        return f"{self.enrollment.student.name} - {self.month}/{self.year} - {self.get_status_display()}"

    @property
    def outstanding(self):
        return self.total_amount - self.paid_amount

    @property
    def month_name(self):
        import calendar
        return calendar.month_name[self.month]

    def save(self, *args, **kwargs):
        # Auto-calculate total amount
        self.total_amount = self.fee_amount - self.discount
        super().save(*args, **kwargs)
