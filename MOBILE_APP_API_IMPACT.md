# Mobile App API Impact Analysis

**Date**: 2025-10-16
**Feature**: Many-to-Many Module Reuse

---

## ⚠️ CRITICAL ISSUES FOUND

### **3 Serializers Have Breaking Changes**

The following serializers reference `module.course` which **NO LONGER EXISTS** after the refactoring:

1. **AssignmentSerializer** (line 492)
   - `course_title = serializers.CharField(source='module.course.title', read_only=True)`
   - **ERROR**: Assignments now can belong to multiple modules, modules can belong to multiple courses

2. **QuizSerializer** (line 608)
   - `course_title = serializers.CharField(source='module.course.title', read_only=True)`
   - **ERROR**: Quizzes now can belong to multiple modules, modules can belong to multiple courses

3. **ModuleProgressSerializer** (line 713)
   - `course_title = serializers.CharField(source='module.course.title', read_only=True)`
   - **ERROR**: Modules now can belong to multiple courses

---

## Impact Assessment

### ❌ **WILL BREAK IF DEPLOYED AS-IS**

These API endpoints will **throw errors**:

1. **GET `/api/assignments/`** - Returns assignment list with course_title
2. **GET `/api/assignments/{id}/`** - Returns assignment detail with course_title
3. **GET `/api/quizzes/`** - Returns quiz list with course_title
4. **GET `/api/quizzes/{id}/`** - Returns quiz detail with course_title
5. **GET `/api/progress/modules/`** - Returns module progress with course_title

**Error**: `AttributeError: 'Module' object has no attribute 'course'`

---

## Student-Facing APIs Status

### ✅ **Working APIs (No Issues)**

These APIs are **correctly updated** and will work:

1. **GET `/api/courses/`** - Course list ✅
   - Uses `CourseListSerializer` - Updated correctly

2. **GET `/api/courses/{id}/`** - Course detail with modules ✅
   - Uses `CourseDetailSerializer` - Updated correctly
   - Modules ordered via `CourseModule.order` ✅
   - Videos ordered via `ModuleVideo.order` ✅

3. **GET `/api/categories/`** - Category list ✅
   - No changes needed

4. **Video Progress APIs** ✅
   - `VideoLessonSerializer` updated correctly
   - Gets order from context (ModuleVideo)

---

## Required Fixes

### Fix 1: AssignmentSerializer

**Current (BROKEN)**:
```python
class AssignmentSerializer(serializers.ModelSerializer):
    module_title = serializers.CharField(source='module.title', read_only=True)
    course_title = serializers.CharField(source='module.course.title', read_only=True)  # ❌ BREAKS
```

**Fixed**:
```python
class AssignmentSerializer(serializers.ModelSerializer):
    # Show first module (or all modules if needed)
    modules = serializers.SerializerMethodField()  # ✅ Shows all modules
    order = serializers.SerializerMethodField()  # ✅ Gets order from context

    @extend_schema_field(serializers.ListField)
    def get_modules(self, obj):
        """Get all modules this assignment belongs to"""
        module_links = obj.module_links.select_related('module').order_by('order')
        return [{
            'id': link.module.id,
            'title': link.module.title,
            'order': link.order
        } for link in module_links]

    @extend_schema_field(serializers.IntegerField)
    def get_order(self, obj):
        """Get order from context (ModuleAssignment) if available"""
        module_assignment = self.context.get('module_assignment')
        if module_assignment:
            return module_assignment.order
        return obj.module_links.first().order if obj.module_links.exists() else 1
```

### Fix 2: QuizSerializer

**Current (BROKEN)**:
```python
class QuizSerializer(serializers.ModelSerializer):
    module_title = serializers.CharField(source='module.title', read_only=True)
    course_title = serializers.CharField(source='module.course.title', read_only=True)  # ❌ BREAKS
```

**Fixed**:
```python
class QuizSerializer(serializers.ModelSerializer):
    modules = serializers.SerializerMethodField()  # ✅ Shows all modules
    order = serializers.SerializerMethodField()  # ✅ Gets order from context

    @extend_schema_field(serializers.ListField)
    def get_modules(self, obj):
        """Get all modules this quiz belongs to"""
        module_links = obj.module_links.select_related('module').order_by('order')
        return [{
            'id': link.module.id,
            'title': link.module.title,
            'order': link.order
        } for link in module_links]

    @extend_schema_field(serializers.IntegerField)
    def get_order(self, obj):
        """Get order from context (ModuleQuiz) if available"""
        module_quiz = self.context.get('module_quiz')
        if module_quiz:
            return module_quiz.order
        return obj.module_links.first().order if obj.module_links.exists() else 1
```

### Fix 3: ModuleProgressSerializer

**Current (BROKEN)**:
```python
class ModuleProgressSerializer(serializers.ModelSerializer):
    module_title = serializers.CharField(source='module.title', read_only=True)
    course_title = serializers.CharField(source='module.course.title', read_only=True)  # ❌ BREAKS
```

**Fixed**:
```python
class ModuleProgressSerializer(serializers.ModelSerializer):
    module_title = serializers.CharField(source='module.title', read_only=True)
    courses = serializers.SerializerMethodField()  # ✅ Shows all courses

    @extend_schema_field(serializers.ListField)
    def get_courses(self, obj):
        """Get all courses this module belongs to"""
        course_links = obj.module.course_links.select_related('course').order_by('order')
        return [{
            'id': link.course.id,
            'title': link.course.title,
            'order': link.order
        } for link in course_links]
```

---

## Alternative: Backward Compatible Fix

If you want **minimal changes** to mobile app:

### Option: Return First Module/Course Only

```python
# AssignmentSerializer
module_title = serializers.SerializerMethodField()
course_title = serializers.SerializerMethodField()

@extend_schema_field(serializers.CharField)
def get_module_title(self, obj):
    """Get first module title for backward compatibility"""
    first_link = obj.module_links.select_related('module').first()
    return first_link.module.title if first_link else None

@extend_schema_field(serializers.CharField)
def get_course_title(self, obj):
    """Get first course title for backward compatibility"""
    first_link = obj.module_links.select_related('module__course_links__course').first()
    if first_link and first_link.module.course_links.exists():
        first_course_link = first_link.module.course_links.first()
        return first_course_link.course.title
    return None
```

**Pros**:
- Mobile app doesn't need changes
- Same API response structure

**Cons**:
- Only shows first module/course (not all)
- Doesn't take advantage of new many-to-many feature

---

## Recommended Approach

### **Option 1: Full Update (Recommended)**

Update serializers to return **all modules/courses** (shows full capability):

**Mobile App Changes Required**:
```dart
// OLD (Flutter)
String moduleTitle = assignment['module_title'];
String courseTitle = assignment['course_title'];

// NEW (Flutter)
List<dynamic> modules = assignment['modules'];
String firstModule = modules.isNotEmpty ? modules[0]['title'] : '';

// Display all modules
for (var module in modules) {
  print("Module: ${module['title']} (Order: ${module['order']})");
}
```

**Pros**:
- Shows full relationship data
- Future-proof
- Takes advantage of many-to-many

**Cons**:
- Requires mobile app update

---

### **Option 2: Backward Compatible (Quick Fix)**

Keep same API structure, return first module/course only:

**Mobile App Changes Required**: None ✅

**Pros**:
- No mobile app changes needed
- Quick deployment

**Cons**:
- Doesn't show all modules/courses
- Limited functionality

---

## Deployment Decision Required

### ⚠️ **CANNOT DEPLOY WITHOUT FIXING SERIALIZERS**

**Choose One**:

1. **Fix serializers + Update mobile app** (1-2 weeks)
   - Full many-to-many support
   - Better long-term

2. **Fix serializers with backward compatibility** (1 day)
   - Quick deployment
   - Mobile app works as-is
   - Limited functionality

---

## Files That Need Fixes

**File**: `apps/courses/serializers.py`

**Lines to fix**:
- Line 491-492: AssignmentSerializer.course_title
- Line 607-608: QuizSerializer.course_title
- Line 712-713: ModuleProgressSerializer.course_title

---

## Updated Status

### Before Fixes:
- ❌ **NOT READY FOR PRODUCTION**
- Will break mobile app APIs

### After Fixes:
- ✅ **READY FOR PRODUCTION** (with Option 1 or 2 applied)

---

## Testing Required After Fix

1. Test assignment API:
   ```bash
   curl http://localhost:8000/api/assignments/
   curl http://localhost:8000/api/assignments/1/
   ```

2. Test quiz API:
   ```bash
   curl http://localhost:8000/api/quizzes/
   curl http://localhost:8000/api/quizzes/1/
   ```

3. Test module progress API:
   ```bash
   curl http://localhost:8000/api/progress/modules/
   ```

4. Verify mobile app still works (if using backward compatible fix)

---

## Conclusion

**Current Status**: ❌ **NOT PRODUCTION READY**

**Reason**: 3 serializers have breaking references to `module.course`

**Solution**: Apply fixes to `apps/courses/serializers.py`

**Estimated Fix Time**:
- Option 1 (Full): 30 minutes coding + mobile app update
- Option 2 (Backward Compatible): 15 minutes coding

**Recommendation**: Apply **Option 2 (Backward Compatible)** first for quick deployment, then plan **Option 1** for next release to take full advantage of many-to-many.

---

## Next Steps

1. ❌ **DO NOT DEPLOY YET** - Serializers must be fixed first
2. Choose Option 1 or Option 2
3. Update `apps/courses/serializers.py`
4. Test all affected API endpoints
5. Then proceed with deployment

---

*Document generated: 2025-10-16*
*Status: CRITICAL ISSUES FOUND*
*Action Required: Fix serializers before deployment*
