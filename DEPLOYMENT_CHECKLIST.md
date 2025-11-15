# Production Deployment Checklist - Many-to-Many Refactoring

## Files to Deploy to Production

### 1. Model Files ✅ CRITICAL
```
apps/courses/models.py
```
**Why**: Contains all the new many-to-many relationships and through models

### 2. Migration Files ✅ CRITICAL
```
apps/courses/migrations/0013_refactor_to_many_to_many.py
```
**Why**: Migrates existing data to new structure without data loss

### 3. Admin Files ✅ UPDATED
```
apps/courses/admin.py
```
**Why**: Django admin updated for new relationships

### 4. Forms Files ✅ UPDATED
```
apps/custom_admin/forms.py
```
**Why**: Removed old `module` and `order` fields from VideoLesson and Assignment forms

### 5. Custom Admin Views ⚠️ PARTIALLY UPDATED
```
apps/custom_admin/views.py
```
**Why**: Updated module and video lesson views; Assignment/Quiz views still need updates

**Updated Functions:**
- `modules_list_view` ✅
- `module_detail_view` ✅
- `module_create_view` ✅
- `module_edit_view` ✅
- `video_lessons_list_view` ✅
- `video_lesson_create_view` ✅
- `video_lesson_edit_view` ✅
- `assignments_list_view` ✅

**Need Updates Before Production:**
- `assignment_detail_view` ❌
- `assignment_create_view` ❌
- `assignment_edit_view` ❌
- `quizzes_list_view` ❌
- `quiz_detail_view` ❌
- `quiz_create_view` ❌
- `quiz_edit_view` ❌

### 6. Templates ❌ NOT YET UPDATED
All template files that reference old relationships need updates:

```
templates/custom_admin/modules/list.html
templates/custom_admin/modules/detail.html
templates/custom_admin/modules/form.html
templates/custom_admin/modules/delete.html

templates/custom_admin/video_lessons/list.html
templates/custom_admin/video_lessons/form.html

templates/custom_admin/assignments/list.html
templates/custom_admin/assignments/detail.html
templates/custom_admin/assignments/form.html

templates/custom_admin/quizzes/list.html
templates/custom_admin/quizzes/detail.html
templates/custom_admin/quizzes/form.html
```

**What needs changing:**
- References to `module.course` → `module.courses.all()` or `module.course_links.all()`
- References to `lesson.module` → `lesson.modules.all()` or `lesson.module_links.all()`
- Single select dropdowns for course/module → Multiple select
- Display of order field → Now in through models

### 7. Serializers ❌ NOT YET UPDATED (if using API)
```
apps/courses/serializers.py
```
**Why**: API responses need to reflect new many-to-many structure

### 8. Documentation Files 📄 REFERENCE ONLY
```
REFACTORING_SUMMARY.md
UPDATE_VIEWS_GUIDE.md
DEPLOYMENT_CHECKLIST.md (this file)
```
**Why**: For your reference during updates

---

## Deployment Steps for Production

### ⚠️ IMPORTANT: Do NOT deploy to production yet!
The refactoring is only 60% complete. Deploying now will break your custom admin interface.

### Option 1: Complete Updates Locally First (RECOMMENDED)

#### Step 1: Complete Remaining Views
```bash
# Update these views in apps/custom_admin/views.py
- assignment_detail_view
- assignment_create_view
- assignment_edit_view
- quiz_detail_view
- quiz_create_view
- quiz_edit_view
```
See `UPDATE_VIEWS_GUIDE.md` for exact code patterns.

#### Step 2: Update All Templates
```bash
# Update all templates that reference:
- module.course
- lesson.module
- assignment.module
- quiz.module
```
See `UPDATE_VIEWS_GUIDE.md` for template examples.

#### Step 3: Update Serializers (if using API)
```bash
# Update apps/courses/serializers.py
```

#### Step 4: Test Locally
```bash
# Test all functionality:
python3 manage.py runserver

# Test these actions:
1. Create a new module
2. Add module to multiple courses
3. Create a video lesson
4. Add video to multiple modules
5. Create assignment and quiz
6. Add them to multiple modules
7. Edit existing modules/videos/assignments/quizzes
8. View course details
9. View module details
```

#### Step 5: Deploy to Production
```bash
# 1. Backup production database FIRST!
pg_dump your_database > backup_before_refactoring.sql

# 2. Upload files to production server
scp apps/courses/models.py production:/path/to/project/
scp apps/courses/migrations/0013_refactor_to_many_to_many.py production:/path/to/project/
scp apps/courses/admin.py production:/path/to/project/
scp apps/custom_admin/forms.py production:/path/to/project/
scp apps/custom_admin/views.py production:/path/to/project/
# ... upload all updated templates ...
# ... upload serializers if updated ...

# 3. On production server, run migration
python manage.py migrate courses

# 4. Restart application
systemctl restart gunicorn  # or your app server
systemctl restart nginx

# 5. Test production immediately after deployment
```

---

### Option 2: Gradual Deployment (Advanced)

If you want to deploy in stages:

#### Stage 1: Deploy Models & Migration Only
**Risk**: Django admin will have errors, custom admin may partially work

**Files to deploy:**
```
apps/courses/models.py
apps/courses/migrations/0013_refactor_to_many_to_many.py
```

**Run:**
```bash
python manage.py migrate courses --skip-checks
```

#### Stage 2: Deploy Admin & Forms
**Files:**
```
apps/courses/admin.py
apps/custom_admin/forms.py
```

#### Stage 3: Deploy Updated Views
**Files:**
```
apps/custom_admin/views.py (after completing remaining updates)
```

#### Stage 4: Deploy Templates
**Files:**
```
All template files (after updating)
```

#### Stage 5: Deploy Serializers
**Files:**
```
apps/courses/serializers.py (after updating)
```

---

## Production Migration Commands

### On Production Server:

```bash
# 1. Activate virtual environment
source /path/to/venv/bin/activate

# 2. Navigate to project directory
cd /path/to/project

# 3. Backup database FIRST!
python manage.py dumpdata courses > backup_courses_$(date +%Y%m%d_%H%M%S).json

# 4. Run migration
python manage.py migrate courses

# 5. Check for any errors
python manage.py check

# 6. Collect static files (if templates changed)
python manage.py collectstatic --noinput

# 7. Restart application server
sudo systemctl restart gunicorn
sudo systemctl restart nginx
```

---

## Rollback Plan (In Case of Issues)

If something goes wrong in production:

```bash
# 1. Restore database from backup
psql your_database < backup_before_refactoring.sql

# 2. Revert code changes
git checkout main  # or your previous stable branch
git pull origin main

# 3. Restart services
sudo systemctl restart gunicorn
sudo systemctl restart nginx
```

---

## Testing Checklist Before Production

### Test These Scenarios Locally:

- [ ] Create a new course
- [ ] Create a new module
- [ ] Add the same module to 2 different courses
- [ ] Create a video lesson
- [ ] Add the same video to 2 different modules
- [ ] Create an assignment
- [ ] Add the same assignment to 2 different modules
- [ ] Create a quiz
- [ ] Add the same quiz to 2 different modules
- [ ] Edit an existing module
- [ ] Change which courses a module belongs to
- [ ] Edit an existing video
- [ ] Change which modules a video belongs to
- [ ] Delete a module (should only remove from course, not delete content)
- [ ] Delete a video (should only remove from module if used elsewhere)
- [ ] View course detail page
- [ ] View module detail page
- [ ] Student can enroll in course
- [ ] Student can view course content
- [ ] Student can complete video lessons
- [ ] Student can submit assignments
- [ ] Student can take quizzes
- [ ] API endpoints work (if using API)
- [ ] Mobile app can fetch courses (if you have a mobile app)

---

## Current Status

### ✅ Safe to Deploy
```
apps/courses/models.py
apps/courses/migrations/0013_refactor_to_many_to_many.py
apps/courses/admin.py
apps/custom_admin/forms.py
```

### ⚠️ Partially Complete - Test Before Deploy
```
apps/custom_admin/views.py
```

### ❌ NOT Safe to Deploy Yet
```
templates/custom_admin/** (all templates)
apps/courses/serializers.py
```

---

## Estimated Time to Complete

- Remaining views: 2-3 hours
- Templates: 3-4 hours
- Serializers: 1-2 hours
- Testing: 2-3 hours

**Total**: ~8-12 hours of development work

---

## Summary

**DO NOT DEPLOY TO PRODUCTION UNTIL:**
1. ✅ All views are updated (60% done)
2. ✅ All templates are updated (0% done)
3. ✅ Serializers are updated if using API (0% done)
4. ✅ Full local testing completed
5. ✅ Production database backup created

**When ready to deploy, deploy ALL files at once to avoid partial functionality.**
