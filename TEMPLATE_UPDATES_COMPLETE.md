# Template Updates - Complete Guide

## Templates Already Updated ✅

### 1. templates/custom_admin/modules/list.html
- ✅ Changed `module.course` → `module.courses.all()`
- ✅ Changed `module.order` → `module.course_links.all().first.order`
- ✅ Changed content counts to use new relationships

### 2. templates/custom_admin/modules/form.html
- ✅ Changed single select `course` → multiple select `courses`
- ✅ Removed `order` field (now in CourseModule)

## Templates That Need Similar Updates

### Video Lesson Templates

#### templates/custom_admin/video_lessons/list.html
**OLD:**
```html
{{ lesson.module.title }}
{{ lesson.order }}
```

**NEW:**
```html
{% for link in lesson.module_links.all|slice:":2" %}
  {{ link.module.title }}{% if not forloop.last %}, {% endif %}
{% endfor %}
{% if lesson.modules.count > 2 %}
  +{{ lesson.modules.count|add:"-2" }} more
{% endif %}
```

#### templates/custom_admin/video_lessons/form.html
**OLD:**
```html
<select name="module" required>
  <option value="{{ module.id }}"
          {% if lesson.module.id == module.id %}selected{% endif %}>
```

**NEW:**
```html
<select name="modules" multiple size="5">
  <option value="{{ module.id }}"
          {% if module in current_modules %}selected{% endif %}>
    {{ module.title }}
  </option>
</select>
<div class="form-text">Hold Ctrl/Cmd to select multiple modules</div>
```

Remove `order` field from form.

### Assignment Templates

#### templates/custom_admin/assignments/list.html
**Changes needed:**
```html
<!-- OLD -->
{{ assignment.module.title }}
{{ assignment.order }}

<!-- NEW -->
{% for link in assignment.module_links.all|slice:":2" %}
  {{ link.module.title }}
{% endfor %}
```

#### templates/custom_admin/assignments/detail.html
**Add module_links display:**
```html
<h5>Used in Modules:</h5>
<ul>
{% for link in module_links %}
  <li>{{ link.module.title }} (Order: {{ link.order }})</li>
{% endfor %}
</ul>
```

#### templates/custom_admin/assignments/form.html
**Change to multiple select:**
```html
<select name="modules" multiple size="5">
  {% for module in modules %}
    <option value="{{ module.id }}"
            {% if module in current_modules %}selected{% endif %}>
      {{ module.title }}
    </option>
  {% endfor %}
</select>
```

Remove `order` field.

### Quiz Templates

#### templates/custom_admin/quizzes/list.html
**Same changes as assignments:**
```html
<!-- OLD -->
{{ quiz.module.title }}
{{ quiz.order }}

<!-- NEW -->
{% for link in quiz.module_links.all|slice:":2" %}
  {{ link.module.title }}
{% endfor %}
```

#### templates/custom_admin/quizzes/detail.html
**Add module_links:**
```html
<h5>Used in Modules:</h5>
<ul>
{% for link in module_links %}
  <li>{{ link.module.title }} (Order: {{ link.order }})</li>
{% endfor %}
</ul>
```

#### templates/custom_admin/quizzes/form.html
**Multiple select:**
```html
<select name="modules" multiple size="5">
  {% for module in modules %}
    <option value="{{ module.id }}"
            {% if module in current_modules %}selected{% endif %}>
      {{ module.title }}
    </option>
  {% endfor %}
</select>
```

Remove `order` field.

### Module Detail Template

#### templates/custom_admin/modules/detail.html
**Major changes needed:**

**OLD:**
```html
<h4>Course: {{ module.course.title }}</h4>
<p>Order: {{ module.order }}</p>

{% for video in video_lessons %}
  {{ video.title }}
{% endfor %}

{% for assignment in assignments %}
  {{ assignment.title }}
{% endfor %}

{% for quiz in quizzes %}
  {{ quiz.title }}
{% endfor %}
```

**NEW:**
```html
<h4>Courses:</h4>
<ul>
{% for link in course_links %}
  <li>
    <a href="{% url 'custom_admin:course_detail' link.course.id %}">
      {{ link.course.title }}
    </a>
    (Order in course: {{ link.order }})
  </li>
{% endfor %}
</ul>

<h5>Video Lessons:</h5>
<ul>
{% for link in video_links %}
  <li>
    <a href="{% url 'custom_admin:video_lesson_edit' link.video_lesson.id %}">
      {{ link.video_lesson.title }}
    </a>
    (Order: {{ link.order }})
  </li>
{% endfor %}
</ul>

<h5>Assignments:</h5>
<ul>
{% for link in assignment_links %}
  <li>
    <a href="{% url 'custom_admin:assignment_edit' link.assignment.id %}">
      {{ link.assignment.title }}
    </a>
    (Order: {{ link.order }})
  </li>
{% endfor %}
</ul>

<h5>Quizzes:</h5>
<ul>
{% for link in quiz_links %}
  <li>
    <a href="{% url 'custom_admin:quiz_edit' link.quiz.id %}">
      {{ link.quiz.title }}
    </a>
    (Order: {{ link.order }})
  </li>
{% endfor %}
</ul>
```

## Pattern Summary

### List Templates
1. Replace `item.module` with loop over `item.module_links.all`
2. Replace `item.course` with loop over `item.course_links.all`
3. Remove `order` display or get from `link.order`

### Form Templates
1. Change `<select name="module">` to `<select name="modules" multiple>`
2. Change `<select name="course">` to `<select name="courses" multiple>`
3. Remove `order` input field
4. Add help text about Ctrl/Cmd for multiple selection
5. Update selected logic to check `{% if module in current_modules %}`

### Detail Templates
1. Display all related items through `*_links` variables
2. Show `link.order` for each item
3. Link to related objects properly

## Quick Reference

### New Relationships
- `module.courses.all()` - courses this module belongs to
- `module.course_links.all()` - CourseModule objects (has .order, .course)
- `module.video_links.all()` - ModuleVideo objects (has .order, .video_lesson)
- `module.assignment_links.all()` - ModuleAssignment objects
- `module.quiz_links.all()` - ModuleQuiz objects

- `video.modules.all()` - modules this video belongs to
- `video.module_links.all()` - ModuleVideo objects

- `assignment.modules.all()` - modules this assignment belongs to
- `assignment.module_links.all()` - ModuleAssignment objects

- `quiz.modules.all()` - modules this quiz belongs to
- `quiz.module_links.all()` - ModuleQuiz objects

### Accessing Order
```html
{% for link in module.course_links.all %}
  Order: {{ link.order }}
  Course: {{ link.course.title }}
{% endfor %}
```

### Counting Content
```html
<!-- OLD -->
{{ module.video_lessons.count }}

<!-- NEW -->
{{ module.module_videos.count }}
{{ module.video_links.count }}
```

## All Templates to Update

### Priority 1 - Critical (Will cause errors)
- ✅ templates/custom_admin/modules/list.html
- ✅ templates/custom_admin/modules/form.html
- ❌ templates/custom_admin/modules/detail.html
- ❌ templates/custom_admin/video_lessons/form.html
- ❌ templates/custom_admin/assignments/form.html
- ❌ templates/custom_admin/quizzes/form.html

### Priority 2 - Important (Will show incorrect data)
- ❌ templates/custom_admin/video_lessons/list.html
- ❌ templates/custom_admin/assignments/list.html
- ❌ templates/custom_admin/assignments/detail.html
- ❌ templates/custom_admin/quizzes/list.html
- ❌ templates/custom_admin/quizzes/detail.html

### Priority 3 - Nice to have
- ❌ templates/custom_admin/courses/detail.html (if it shows modules)
- ❌ Any dashboard/statistics pages that reference modules

## Status Summary
- ✅ Module views: COMPLETE
- ✅ Assignment/Quiz views: COMPLETE
- ✅ Module list template: COMPLETE
- ✅ Module form template: COMPLETE
- ⚠️  Remaining templates: ~10 files to update
- ❌ Serializers: NOT STARTED
