# Many-to-Many Refactoring Summary

## What Was Changed

### Models Refactored (apps/courses/models.py)

**Before:** One-to-Many (ForeignKey) relationships
- Course → Module (ForeignKey)
- Module → VideoLesson (ForeignKey)
- Module → Assignment (ForeignKey)
- Module → Quiz (ForeignKey)

**After:** Many-to-Many relationships with through models
- Course ↔ Module (via `CourseModule`)
- Module ↔ VideoLesson (via `ModuleVideo`)
- Module ↔ Assignment (via `ModuleAssignment`)
- Module ↔ Quiz (via `ModuleQuiz`)

### New Through Models
1. **CourseModule** - Links courses to modules with ordering
2. **ModuleVideo** - Links modules to video lessons with ordering
3. **ModuleAssignment** - Links modules to assignments with ordering
4. **ModuleQuiz** - Links modules to quizzes with ordering

### Fields Removed
- `Module.course` → Now accessed via `Module.courses` (ManyToMany)
- `Module.order` → Now in `CourseModule.order`
- `VideoLesson.module` → Now accessed via `VideoLesson.modules` (ManyToMany)
- `VideoLesson.order` → Now in `ModuleVideo.order`
- `Assignment.module` → Now accessed via `Assignment.modules` (ManyToMany)
- `Assignment.order` → Now in `ModuleAssignment.order`
- `Quiz.module` → Now accessed via `Quiz.modules` (ManyToMany)
- `Quiz.order` → Now in `ModuleQuiz.order`

## Benefits

### Content Reuse
✅ Create a module once, add it to multiple courses
✅ Create a video/quiz/assignment once, use it in multiple modules
✅ Updates to content automatically reflect across all courses using it

### Example Usage
```python
# Create reusable module
python_basics = Module.objects.create(
    title="Python Basics",
    description="Introduction to Python"
)

# Add to multiple courses with different ordering
CourseModule.objects.create(course=web_dev_course, module=python_basics, order=1)
CourseModule.objects.create(course=data_science_course, module=python_basics, order=2)

# Create reusable video
video = VideoLesson.objects.create(
    title="Python Variables",
    platform="youtube",
    video_id="abc123"
)

# Add to multiple modules
ModuleVideo.objects.create(module=python_basics, video_lesson=video, order=1)
ModuleVideo.objects.create(module=advanced_python, video_lesson=video, order=5)
```

## Data Migration

✅ **Existing data preserved** - The migration automatically converted all existing relationships to the new structure maintaining the same order.

## What Needs Updating

### ❌ Custom Admin Views (apps/custom_admin/views.py)
Views that need updating:
- `modules_list_view` - Module queries
- `module_create_view` - Module/Course assignment
- `module_edit_view` - Module/Course management
- `video_lesson_create_view` - Module assignment
- `assignment_create_view` - Module assignment
- `quiz_create_view` - Module assignment

### ❌ Custom Admin Forms (apps/custom_admin/forms.py)
✅ Already updated:
- `CustomVideoLessonForm` - Removed `module` and `order` fields
- `CustomAssignmentForm` - Removed `module` and `order` fields

Still needs work for proper many-to-many handling in create/edit views.

### ❌ Custom Admin Templates
Templates that reference `module.course` or `*.module` need updating to use the new relationships.

### ❌ Serializers (if using DRF API)
API serializers need to be updated to handle the new many-to-many structure.

## Migration File
Location: `apps/courses/migrations/0013_refactor_to_many_to_many.py`

The migration:
1. Creates new through models
2. Migrates existing data
3. Removes old ForeignKey fields

## Next Steps

1. **Update Custom Admin Views** - Modify views to work with through models
2. **Update Custom Admin Templates** - Fix template references to old relationships
3. **Update Serializers** - If using APIs, update serializers
4. **Test Thoroughly** - Verify existing courses still display correctly
5. **Update Documentation** - Document the new workflow for content creation/reuse

## Accessing Related Data

### Old Way (One-to-Many)
```python
# Get modules for a course
course.modules.all()

# Get module's course
module.course

# Get videos for a module
module.video_lessons.all()
```

### New Way (Many-to-Many)
```python
# Get modules for a course (ordered)
course.module_links.select_related('module').order_by('order')
# Or just: course.modules.all()

# Get courses for a module
module.courses.all()

# Get videos for a module (ordered)
module.video_links.select_related('video_lesson').order_by('order')
# Or just: module.module_videos.all()

# To access the through model (for order, etc)
CourseModule.objects.filter(course=course).order_by('order')
```

## Status
- ✅ Models updated
- ✅ Migration created and run
- ✅ Django admin.py updated (basic)
- ✅ Forms updated (partial)
- ❌ Custom admin views - **NEEDS UPDATE**
- ❌ Custom admin templates - **NEEDS UPDATE**
- ❌ Serializers - **NEEDS UPDATE**
