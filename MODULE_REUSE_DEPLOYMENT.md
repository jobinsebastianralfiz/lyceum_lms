# Module Reuse Feature - Production Deployment Checklist

## 🚀 Critical Files for Module Reuse Feature

### **Phase 1: Database Migration (MUST RUN FIRST)**
**Run this migration on production BEFORE deploying any code:**

```bash
python manage.py migrate courses 0013_refactor_to_many_to_many
```

**Migration File:**
- `apps/courses/migrations/0013_refactor_to_many_to_many.py`

**What it does:**
- Creates many-to-many through tables (CourseModule, ModuleVideo, ModuleAssignment, ModuleQuiz)
- Migrates existing data from old structure to new structure
- Allows modules to be reused across multiple courses

---

## 📦 Python Files to Deploy

### **1. Core Models (CRITICAL)**
**File:** `apps/courses/models.py`
- Changed ForeignKey relationships to ManyToMany with through tables
- Added CourseModule, ModuleVideo, ModuleAssignment, ModuleQuiz through models
- Updated Module, VideoLesson, Assignment, Quiz models
- **IMPORTANT:** Added backward compatibility properties:
  - `VideoLesson.module` property (returns first module)
  - `Assignment.module` property (returns first module)
  - `Quiz.module` property (returns first module)
  - `Module.course` property (returns first course)
  - These enable `lesson.module.course` syntax to work in views

### **2. Serializers (CRITICAL for Mobile App)**
**File:** `apps/courses/serializers.py`
- Fixed AssignmentSerializer - now uses SerializerMethodField for module/course info
- Fixed QuizSerializer - backward compatible with mobile app
- Fixed ModuleProgressSerializer - handles many-to-many relationships
- All changes are backward compatible (no mobile app changes needed)

### **3. Admin Interface**
**File:** `apps/courses/admin.py`
- Updated admin for CourseModule, ModuleVideo, ModuleAssignment, ModuleQuiz
- Added inline management for modules within courses
- Better organization in admin panel

### **4. Custom Admin Views**
**File:** `apps/custom_admin/views.py`
- Added bulk user delete functionality (users_bulk_delete_view)
- Updated course/module views to handle many-to-many relationships

### **5. Custom Admin Forms**
**File:** `apps/custom_admin/forms.py`
- Updated forms to handle many-to-many relationships

### **6. URL Configuration**
**File:** `apps/custom_admin/urls.py`
- Added bulk delete route: `users/bulk-delete/`

---

## 🎨 Template Files to Deploy

### **Custom Admin Templates:**

1. **Modules Management:**
   - `templates/custom_admin/modules/list.html`
   - `templates/custom_admin/modules/form.html`
   - `templates/custom_admin/modules/detail.html`
   - `templates/custom_admin/modules/delete.html` (NEW)

2. **Assignments Management:**
   - `templates/custom_admin/assignments/list.html`
   - `templates/custom_admin/assignments/form.html`
   - `templates/custom_admin/assignments/detail.html`

3. **Quizzes Management:**
   - `templates/custom_admin/quizzes/list.html`
   - `templates/custom_admin/quizzes/form.html`
   - `templates/custom_admin/quizzes/detail.html`

4. **Video Lessons Management:**
   - `templates/custom_admin/video_lessons/form.html`

5. **Users Management:**
   - `templates/custom_admin/users/list.html` (Bulk delete feature added)

6. **Base Template:**
   - `templates/custom_admin/base.html`

### **Student Portal Templates:**

1. **Course Detail (Redesigned):**
   - `student_portal/templates/student_portal/courses/course_detail.html`
   - Modern design with organized content sections
   - Separated videos/assignments/quizzes

### **Landing Page Templates:**

1. **Login Page:**
   - `landing/templates/landing/login.html` (Registration disabled)

2. **Home Page:**
   - `landing/templates/landing/home.html` (CTAs updated)

3. **Base Template:**
   - `landing/templates/landing/base.html` (Navigation updated)

---

## 📋 Other Files Modified

### **Landing App:**
- `landing/urls.py` - Registration route commented out
- `landing/views.py` - Registration view disabled

### **Settings & URLs:**
- `codelearn_lms/settings.py` - No critical changes for module reuse
- `codelearn_lms/urls.py` - No critical changes for module reuse

---

## 🔧 Deployment Steps (In Order)

### **Step 1: Backup Database**
```bash
# On production server
python manage.py dumpdata > backup_before_module_reuse.json
```

### **Step 2: Pull Latest Code**
```bash
git pull origin main
```

### **Step 3: Install Dependencies** (if any new)
```bash
pip install -r requirements.txt
```

### **Step 4: Run Migration**
```bash
python manage.py migrate courses 0013_refactor_to_many_to_many
```

### **Step 5: Collect Static Files**
```bash
python manage.py collectstatic --noinput
```

### **Step 6: Restart Application**
```bash
# Apache/mod_wsgi
sudo systemctl restart apache2

# Or Gunicorn
sudo systemctl restart gunicorn

# Or uWSGI
sudo systemctl restart uwsgi
```

### **Step 7: Clear Cache** (if using Redis/Memcached)
```bash
python manage.py clear_cache
```

---

## ✅ Post-Deployment Verification

### **1. Test Module Reuse:**
- Go to Custom Admin → Modules
- Create a new module
- Add it to multiple courses
- Verify it appears in all courses

### **2. Test Mobile API:**
- Test `/api/courses/` endpoint
- Test `/api/assignments/` endpoint
- Test `/api/quizzes/` endpoint
- Verify backward compatibility

### **3. Test Student Portal:**
- Visit course detail page
- Verify modules display correctly
- Verify videos/assignments/quizzes are organized in sections
- Check progress tracking works

### **4. Test Bulk User Delete:**
- Go to Custom Admin → Users
- Select multiple users
- Click "Delete Selected"
- Verify deletion works

---

## 🔄 Rollback Plan (If Issues Occur)

### **Option 1: Restore Database Backup**
```bash
python manage.py flush --noinput
python manage.py loaddata backup_before_module_reuse.json
```

### **Option 2: Revert Migration**
```bash
python manage.py migrate courses 0012_add_video_platform_support
```

### **Option 3: Revert Code**
```bash
git revert HEAD
git push origin main
# Then restart application
```

---

## 📱 Mobile App Compatibility

**GOOD NEWS:** No mobile app changes required!

The serializers were updated with backward compatibility:
- AssignmentSerializer returns module/course info via SerializerMethodField
- QuizSerializer returns module/course info via SerializerMethodField
- ModuleProgressSerializer handles many-to-many relationships
- All API responses remain the same format

---

## 🎯 Summary of Changes

### **Module Reuse Feature (19 Files):**
1. ✅ Migration: 1 file
2. ✅ Python files: 5 files (models, serializers, admin, views, student_portal/views)
3. ✅ Templates: 13 files (admin + student portal)

### **Additional Features:**
4. ✅ Bulk user delete: 2 files (views, template)
5. ✅ Registration disabled: 3 files (views, urls, templates)
6. ✅ Course detail redesign: 1 file (modern UI)

### **Student Portal Views (CRITICAL)**
**File:** `student_portal/views.py`
- Fixed all queries using old `module__course` syntax
- Updated to use many-to-many relationships:
  - `module_links__module__course_links__course`
- Added backward compatibility with model properties (lesson.module.course still works)

### **Total Files to Deploy: 24 files**

---

## 🚨 IMPORTANT NOTES

1. **Migration MUST run before deploying code** - Otherwise app will crash
2. **Backup database first** - Migration changes data structure
3. **No mobile app update needed** - API is backward compatible
4. **Test on staging first** - If you have a staging environment
5. **Monitor logs after deployment** - Check for any errors

---

## 📞 Support

If issues occur after deployment:
1. Check Django logs: `tail -f logs/django.log`
2. Check Apache/Nginx error logs
3. Check database for migration status: `python manage.py showmigrations courses`
4. Rollback if critical issues found

---

## ✨ New Features Available After Deployment

1. **Module Reuse** - Create modules once, use in multiple courses
2. **Better Organization** - Cleaner course/module management
3. **Bulk User Delete** - Remove spam users efficiently
4. **Modern Course UI** - Better student experience
5. **Organized Content** - Videos/assignments/quizzes in sections

---

**Generated:** October 16, 2025
**Version:** 1.0
**Status:** Ready for Production Deployment
