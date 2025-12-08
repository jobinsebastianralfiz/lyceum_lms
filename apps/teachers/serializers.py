from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import TeacherProfile, TeacherSchedule, TeacherAnnouncement

User = get_user_model()


# ============== Authentication Serializers ==============

class TeacherLoginSerializer(serializers.Serializer):
    """Serializer for teacher login"""
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class TeacherChangePasswordSerializer(serializers.Serializer):
    """Serializer for changing password"""
    old_password = serializers.CharField(write_only=True, required=False)
    new_password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True, min_length=8)

    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({
                'confirm_password': 'Passwords do not match.'
            })
        return data


class TeacherForgotPasswordSerializer(serializers.Serializer):
    """Serializer for forgot password request"""
    email = serializers.EmailField()


class TeacherResetPasswordSerializer(serializers.Serializer):
    """Serializer for password reset with code"""
    email = serializers.EmailField()
    code = serializers.CharField(max_length=6)
    new_password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True, min_length=8)

    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({
                'confirm_password': 'Passwords do not match.'
            })
        return data


# ============== Profile Serializers ==============

class TeacherUserSerializer(serializers.ModelSerializer):
    """Serializer for User model (teacher-related fields)"""
    class Meta:
        model = User
        fields = ['id', 'email', 'name', 'phone_number', 'address', 'role', 'is_active', 'date_joined']
        read_only_fields = ['id', 'email', 'role', 'date_joined']


class TeacherProfileSerializer(serializers.ModelSerializer):
    """Full teacher profile serializer"""
    user = TeacherUserSerializer(read_only=True)
    full_name = serializers.CharField(read_only=True)
    email = serializers.EmailField(read_only=True)
    phone = serializers.CharField(read_only=True)
    total_students = serializers.IntegerField(read_only=True)
    total_courses = serializers.IntegerField(read_only=True)

    class Meta:
        model = TeacherProfile
        fields = [
            'id', 'user', 'employee_id', 'designation', 'department',
            'qualification', 'specialization', 'experience_years',
            'bio', 'profile_photo', 'date_of_joining', 'is_active',
            'must_change_password', 'full_name', 'email', 'phone',
            'total_students', 'total_courses', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'employee_id', 'must_change_password', 'created_at', 'updated_at']


class TeacherProfileUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating teacher profile"""
    name = serializers.CharField(write_only=True, required=False)
    phone_number = serializers.CharField(write_only=True, required=False, allow_blank=True)
    address = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = TeacherProfile
        fields = [
            'designation', 'department', 'qualification', 'specialization',
            'experience_years', 'bio', 'profile_photo',
            'name', 'phone_number', 'address'
        ]

    def update(self, instance, validated_data):
        # Update user fields
        user = instance.user
        if 'name' in validated_data:
            user.name = validated_data.pop('name')
        if 'phone_number' in validated_data:
            user.phone_number = validated_data.pop('phone_number')
        if 'address' in validated_data:
            user.address = validated_data.pop('address')
        user.save()

        # Update profile fields
        return super().update(instance, validated_data)


# ============== Course & Student Serializers ==============

class TeacherCourseListSerializer(serializers.Serializer):
    """Serializer for courses assigned to teacher"""
    id = serializers.IntegerField()
    title = serializers.CharField()
    description = serializers.CharField()
    category_name = serializers.SerializerMethodField()
    thumbnail = serializers.ImageField()
    is_published = serializers.BooleanField()
    total_students = serializers.SerializerMethodField()
    total_modules = serializers.SerializerMethodField()

    def get_category_name(self, obj):
        return obj.category.name if obj.category else None

    def get_total_students(self, obj):
        from apps.payments.models import Enrollment
        return Enrollment.objects.filter(course=obj, active=True).count()

    def get_total_modules(self, obj):
        return obj.module_links.count()


class TeacherStudentSerializer(serializers.Serializer):
    """Serializer for students in teacher's courses"""
    id = serializers.IntegerField()
    name = serializers.CharField()
    email = serializers.EmailField()
    phone_number = serializers.CharField()
    enrolled_at = serializers.DateTimeField()
    course_title = serializers.CharField()
    course_id = serializers.IntegerField()
    progress_percentage = serializers.FloatField()


class StudentDetailSerializer(serializers.ModelSerializer):
    """Detailed student information"""
    enrollments = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'name', 'email', 'phone_number', 'address', 'date_joined', 'enrollments']

    def get_enrollments(self, obj):
        from apps.payments.models import Enrollment
        teacher = self.context.get('teacher')
        if teacher:
            enrollments = Enrollment.objects.filter(
                user=obj,
                course__in=teacher.assigned_courses.all(),
                active=True
            ).select_related('course')
            return [{
                'course_id': e.course.id,
                'course_title': e.course.title,
                'enrolled_at': e.created_at,
                'payment_status': e.payment_status
            } for e in enrollments]
        return []


# ============== Assignment & Quiz Serializers ==============

class AssignmentSubmissionListSerializer(serializers.Serializer):
    """Serializer for assignment submissions list"""
    id = serializers.IntegerField()
    student_id = serializers.IntegerField()
    student_name = serializers.CharField()
    student_email = serializers.EmailField()
    assignment_id = serializers.IntegerField()
    assignment_title = serializers.CharField()
    course_title = serializers.CharField()
    github_url = serializers.URLField()
    submission_notes = serializers.CharField()
    status = serializers.CharField()
    score = serializers.IntegerField()
    max_points = serializers.IntegerField()
    submitted_at = serializers.DateTimeField()
    graded_at = serializers.DateTimeField()


class GradeSubmissionSerializer(serializers.Serializer):
    """Serializer for grading a submission"""
    score = serializers.IntegerField(min_value=0)
    grade_comments = serializers.CharField(required=False, allow_blank=True)

    def validate_score(self, value):
        submission = self.context.get('submission')
        if submission and value > submission.assignment.max_points:
            raise serializers.ValidationError(
                f"Score cannot exceed maximum points ({submission.assignment.max_points})"
            )
        return value


class QuizAttemptListSerializer(serializers.Serializer):
    """Serializer for quiz attempts list"""
    id = serializers.IntegerField()
    student_id = serializers.IntegerField()
    student_name = serializers.CharField()
    student_email = serializers.EmailField()
    quiz_id = serializers.IntegerField()
    quiz_title = serializers.CharField()
    course_title = serializers.CharField()
    attempt_number = serializers.IntegerField()
    score = serializers.IntegerField()
    total_points = serializers.IntegerField()
    score_percentage = serializers.FloatField()
    is_passed = serializers.BooleanField()
    time_taken = serializers.IntegerField()
    completed = serializers.BooleanField()
    started_at = serializers.DateTimeField()
    completed_at = serializers.DateTimeField()


# ============== Schedule Serializers ==============

class TeacherScheduleSerializer(serializers.ModelSerializer):
    """Serializer for teacher schedule"""
    course_title = serializers.SerializerMethodField()
    batch_name = serializers.SerializerMethodField()

    class Meta:
        model = TeacherSchedule
        fields = [
            'id', 'day_of_week', 'start_time', 'end_time',
            'course', 'course_title', 'batch', 'batch_name',
            'is_active', 'notes'
        ]

    def get_course_title(self, obj):
        return obj.course.title if obj.course else None

    def get_batch_name(self, obj):
        return obj.batch.name if obj.batch else None


# ============== Announcement Serializers ==============

class TeacherAnnouncementSerializer(serializers.ModelSerializer):
    """Serializer for teacher announcements"""
    course_title = serializers.SerializerMethodField()
    is_published = serializers.BooleanField(read_only=True)

    class Meta:
        model = TeacherAnnouncement
        fields = [
            'id', 'title', 'content', 'course', 'course_title',
            'is_global', 'publish_at', 'expires_at', 'is_active',
            'is_published', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

    def get_course_title(self, obj):
        return obj.course.title if obj.course else "All Courses"


class TeacherAnnouncementCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating announcements"""
    class Meta:
        model = TeacherAnnouncement
        fields = ['title', 'content', 'course', 'is_global', 'publish_at', 'expires_at']


# ============== Dashboard Serializers ==============

class TeacherDashboardSerializer(serializers.Serializer):
    """Serializer for teacher dashboard data"""
    total_courses = serializers.IntegerField()
    total_students = serializers.IntegerField()
    pending_assignments = serializers.IntegerField()
    pending_quizzes = serializers.IntegerField()
    upcoming_sessions = serializers.ListField()
    recent_submissions = serializers.ListField()
    announcements_count = serializers.IntegerField()


# ============== Admin Teacher Management Serializers ==============

class AdminTeacherCreateSerializer(serializers.Serializer):
    """Serializer for admin to create a teacher"""
    # User fields
    email = serializers.EmailField()
    name = serializers.CharField(max_length=150)
    phone_number = serializers.CharField(max_length=15, required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, min_length=8)

    # Profile fields
    designation = serializers.CharField(max_length=100, required=False, allow_blank=True)
    department = serializers.CharField(max_length=100, required=False, allow_blank=True)
    qualification = serializers.CharField(required=False, allow_blank=True)
    specialization = serializers.CharField(required=False, allow_blank=True)
    experience_years = serializers.IntegerField(default=0, min_value=0)
    bio = serializers.CharField(required=False, allow_blank=True)
    date_of_joining = serializers.DateField(required=False)

    # Course assignments
    assigned_course_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        default=[]
    )

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def create(self, validated_data):
        assigned_course_ids = validated_data.pop('assigned_course_ids', [])

        # Create user
        user = User.objects.create_user(
            email=validated_data['email'],
            name=validated_data['name'],
            password=validated_data['password'],
            role='teacher',
            phone_number=validated_data.get('phone_number', ''),
        )

        # Create teacher profile
        profile = TeacherProfile.objects.create(
            user=user,
            designation=validated_data.get('designation', ''),
            department=validated_data.get('department', ''),
            qualification=validated_data.get('qualification', ''),
            specialization=validated_data.get('specialization', ''),
            experience_years=validated_data.get('experience_years', 0),
            bio=validated_data.get('bio', ''),
            date_of_joining=validated_data.get('date_of_joining'),
            must_change_password=True
        )

        # Assign courses
        if assigned_course_ids:
            from apps.courses.models import Course
            courses = Course.objects.filter(id__in=assigned_course_ids)
            profile.assigned_courses.set(courses)

        return profile


class AdminTeacherUpdateSerializer(serializers.Serializer):
    """Serializer for admin to update a teacher"""
    # User fields
    name = serializers.CharField(max_length=150, required=False)
    phone_number = serializers.CharField(max_length=15, required=False, allow_blank=True)
    is_active = serializers.BooleanField(required=False)

    # Profile fields
    designation = serializers.CharField(max_length=100, required=False, allow_blank=True)
    department = serializers.CharField(max_length=100, required=False, allow_blank=True)
    qualification = serializers.CharField(required=False, allow_blank=True)
    specialization = serializers.CharField(required=False, allow_blank=True)
    experience_years = serializers.IntegerField(min_value=0, required=False)
    bio = serializers.CharField(required=False, allow_blank=True)
    date_of_joining = serializers.DateField(required=False)

    def update(self, instance, validated_data):
        user = instance.user

        # Update user fields
        if 'name' in validated_data:
            user.name = validated_data['name']
        if 'phone_number' in validated_data:
            user.phone_number = validated_data['phone_number']
        if 'is_active' in validated_data:
            user.is_active = validated_data['is_active']
        user.save()

        # Update profile fields
        for field in ['designation', 'department', 'qualification', 'specialization',
                      'experience_years', 'bio', 'date_of_joining']:
            if field in validated_data:
                setattr(instance, field, validated_data[field])
        instance.save()

        return instance


class AdminTeacherListSerializer(serializers.ModelSerializer):
    """Serializer for listing teachers (admin view)"""
    user = TeacherUserSerializer(read_only=True)
    total_students = serializers.IntegerField(read_only=True)
    total_courses = serializers.IntegerField(read_only=True)
    assigned_courses = serializers.SerializerMethodField()

    class Meta:
        model = TeacherProfile
        fields = [
            'id', 'user', 'employee_id', 'designation', 'department',
            'qualification', 'specialization', 'experience_years',
            'date_of_joining', 'is_active', 'total_students', 'total_courses',
            'assigned_courses', 'created_at'
        ]

    def get_assigned_courses(self, obj):
        return [{'id': c.id, 'title': c.title} for c in obj.assigned_courses.all()[:5]]


class AssignCoursesSerializer(serializers.Serializer):
    """Serializer for assigning courses to teacher"""
    course_ids = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=True
    )
