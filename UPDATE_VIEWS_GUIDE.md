# Custom Admin Views Update Guide

## Views Already Updated

### Module Views ✅
- `modules_list_view` - Updated to use `prefetch_related('courses')`
- `module_detail_view` - Updated to use video_links, assignment_links, quiz_links, course_links
- `module_create_view` - Updated to handle multiple courses via CourseModule
- `module_edit_view` - Updated to handle multiple courses via CourseModule

### Video Lesson Views ✅
- `video_lessons_list_view` - Updated to use `prefetch_related('modules')`
- `video_lesson_create_view` - Updated to handle multiple modules via ModuleVideo
- `video_lesson_edit_view` - Updated to handle multiple modules via ModuleVideo

### Assignment Views ✅
- `assignments_list_view` - Updated to use `prefetch_related('modules')`

## Views That Still Need Updates

### Assignment Views
**File**: `apps/custom_admin/views.py`

#### assignment_detail_view (line ~1976)
```python
# OLD
def assignment_detail_view(request, assignment_id):
    assignment = get_object_or_404(Assignment, id=assignment_id)
    # Uses assignment.module

# NEW
def assignment_detail_view(request, assignment_id):
    assignment = get_object_or_404(Assignment, id=assignment_id)
    module_links = assignment.module_links.select_related('module').order_by('order')
    # Now uses module_links to show all modules this assignment belongs to
```

#### assignment_create_view (line ~1988)
```python
# Add after form saves:
from apps.courses.models import ModuleAssignment

# Get selected modules from POST
module_ids = request.POST.getlist('modules')

# Create links
if module_ids:
    for module_id in module_ids:
        module = get_object_or_404(Module, id=module_id)
        max_order = ModuleAssignment.objects.filter(module=module).aggregate(
            models.Max('order')
        )['order__max'] or 0
        ModuleAssignment.objects.create(
            module=module,
            assignment=assignment,
            order=max_order + 1
        )
```

#### assignment_edit_view (line ~2008)
```python
# Similar to video_lesson_edit_view
# Delete old links, create new ones based on selected modules
current_modules = assignment.modules.all()

# After form saves:
assignment.module_links.all().delete()
# Then create new links as shown above
```

### Quiz Views
**File**: `apps/custom_admin/views.py`

#### quizzes_list_view (line ~2047)
```python
# OLD
quizzes = Quiz.objects.select_related('module', 'module__course')

# NEW
quizzes = Quiz.objects.prefetch_related('modules')

# Update search filter
Q(modules__title__icontains=search_query) |
Q(modules__courses__title__icontains=search_query)
```

#### quiz_detail_view (line ~2074)
```python
# OLD
quiz = get_object_or_404(Quiz, id=quiz_id)
# Uses quiz.module

# NEW
quiz = get_object_or_404(Quiz, id=quiz_id)
module_links = quiz.module_links.select_related('module').order_by('order')
```

#### quiz_create_view (line ~2089)
```python
# Add ModuleQuiz handling similar to ModuleAssignment
from apps.courses.models import ModuleQuiz

module_ids = request.POST.getlist('modules')

if module_ids:
    for module_id in module_ids:
        module = get_object_or_404(Module, id=module_id)
        max_order = ModuleQuiz.objects.filter(module=module).aggregate(
            models.Max('order')
        )['order__max'] or 0
        ModuleQuiz.objects.create(
            module=module,
            quiz=quiz,
            order=max_order + 1
        )
```

#### quiz_edit_view (line ~2146)
```python
current_modules = quiz.modules.all()

# After form saves:
quiz.module_links.all().delete()
# Then create new links
```

## Template Updates Needed

### Module Templates
**File**: `templates/custom_admin/modules/list.html`
```html
<!-- OLD -->
{{ module.course.title }}

<!-- NEW -->
{% for link in module.course_links.all %}
    {{ link.course.title }}{% if not forloop.last %}, {% endif %}
{% endfor %}
```

**File**: `templates/custom_admin/modules/detail.html`
```html
<!-- OLD -->
<h4>{{ module.course.title }}</h4>

<!-- NEW -->
<h4>Courses:</h4>
<ul>
{% for link in course_links %}
    <li>{{ link.course.title }} (Order: {{ link.order }})</li>
{% endfor %}
</ul>

<!-- OLD videos/assignments/quizzes -->
{% for video in video_lessons %}
{% for assignment in assignments %}
{% for quiz in quizzes %}

<!-- NEW -->
{% for link in video_links %}
    {{ link.video_lesson.title }} (Order: {{ link.order }})
{% endfor %}

{% for link in assignment_links %}
    {{ link.assignment.title }} (Order: {{ link.order }})
{% endfor %}

{% for link in quiz_links %}
    {{ link.quiz.title }} (Order: {{ link.order }})
{% endfor %}
```

**File**: `templates/custom_admin/modules/form.html`
```html
<!-- OLD -->
<select name="course" required>
    <option value="">Select Course</option>
    {% for course in courses %}
        <option value="{{ course.id }}">{{ course.title }}</option>
    {% endfor %}
</select>

<!-- NEW (Multiple select) -->
<select name="courses" multiple required>
    {% for course in courses %}
        <option value="{{ course.id }}"
                {% if course in current_courses %}selected{% endif %}>
            {{ course.title }}
        </option>
    {% endfor %}
</select>
```

### Video Lesson Templates
**File**: `templates/custom_admin/video_lessons/list.html`
```html
<!-- OLD -->
{{ lesson.module.title }} - {{ lesson.module.course.title }}

<!-- NEW -->
{% for link in lesson.module_links.all %}
    {{ link.module.title }}{% if not forloop.last %}, {% endif %}
{% endfor %}
```

**File**: `templates/custom_admin/video_lessons/form.html`
```html
<!-- OLD -->
Select Module from Course dropdown

<!-- NEW -->
<label>Modules (Select multiple)</label>
<select name="modules" multiple>
    {% for module in modules %}
        <option value="{{ module.id }}"
                {% if module in current_modules %}selected{% endif %}>
            {{ module.title }}
        </option>
    {% endfor %}
</select>
```

### Assignment Templates
**File**: `templates/custom_admin/assignments/list.html`
```html
<!-- OLD -->
{{ assignment.module.title }}

<!-- NEW -->
{% for link in assignment.module_links.all %}
    {{ link.module.title }}{% if not forloop.last %}, {% endif %}
{% endfor %}
```

**File**: `templates/custom_admin/assignments/form.html`
```html
<!-- Similar to video lessons - add multiple select for modules -->
```

### Quiz Templates
**File**: `templates/custom_admin/quizzes/list.html`
```html
<!-- Similar updates as assignments -->
```

## Serializer Updates Needed

**File**: `apps/courses/serializers.py`

### ModuleSerializer
```python
class ModuleSerializer(serializers.ModelSerializer):
    # OLD
    course = CourseSerializer(read_only=True)

    # NEW
    courses = serializers.SerializerMethodField()
    video_lessons = serializers.SerializerMethodField()
    assignments = serializers.SerializerMethodField()
    quizzes = serializers.SerializerMethodField()

    def get_courses(self, obj):
        course_links = obj.course_links.select_related('course').order_by('order')
        return [{'id': link.course.id, 'title': link.course.title, 'order': link.order}
                for link in course_links]

    def get_video_lessons(self, obj):
        video_links = obj.video_links.select_related('video_lesson').order_by('order')
        return VideoLessonSerializer([link.video_lesson for link in video_links], many=True).data

    # Similar for assignments and quizzes
```

### VideoLessonSerializer
```python
class VideoLessonSerializer(serializers.ModelSerializer):
    # OLD
    module = ModuleSerializer(read_only=True)

    # NEW
    modules = serializers.SerializerMethodField()

    def get_modules(self, obj):
        module_links = obj.module_links.select_related('module').order_by('order')
        return [{'id': link.module.id, 'title': link.module.title, 'order': link.order}
                for link in module_links]
```

### Similar updates for AssignmentSerializer and QuizSerializer

## Summary

**Completed:**
- ✅ Module views (list, detail, create, edit)
- ✅ Video lesson views (list, create, edit)
- ✅ Assignment list view

**Remaining:**
- ❌ Assignment detail, create, edit views
- ❌ Quiz list, detail, create, edit views
- ❌ All templates (modules, videos, assignments, quizzes)
- ❌ All serializers

**Key Pattern:**
1. List views: Use `prefetch_related()` instead of `select_related()`
2. Detail views: Access through `*_links` with `.select_related().order_by('order')`
3. Create/Edit views: Delete old links, create new via through models
4. Templates: Loop through `*_links` instead of direct relations
5. Forms: Use multiple select for modules/courses
