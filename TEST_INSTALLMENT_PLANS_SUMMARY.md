# 🎯 Test Installment Plans & Enrollment Workflow

## 📊 Created Test Data

### 💰 Course Pricing (5 Courses)
```
₹22,000 - Django REST API Development
₹25,000 - Advanced JavaScript & TypeScript  
₹28,000 - React Native Mobile App Development
₹35,000 - Full Stack Web Development Bootcamp
₹42,000 - Python for Data Science & Machine Learning
```

### 📅 Installment Plan Options (6 Plans)
```
1.  2-Month Plan: ₹12,500/month ×  2 = ₹25,000 total
2.  3-Month Plan: ₹ 8,333/month ×  3 = ₹25,000 total  
3.  4-Month Plan: ₹ 6,250/month ×  4 = ₹25,000 total
4.  6-Month Plan: ₹ 4,167/month ×  6 = ₹25,000 total
5.  8-Month Plan: ₹ 3,125/month ×  8 = ₹25,000 total
6. 12-Month Plan: ₹ 2,083/month × 12 = ₹25,000 total
```

## 🔄 Testing Workflow

### Step 1: Create Enrollment with Installment Plan
1. Go to **Custom Admin → Enrollments → Add New Enrollment**
2. Fill out enrollment form:
   - **Student**: Select any student
   - **Course**: Choose from the 5 test courses above
   - **Total Amount**: Will auto-populate from course price
   - **Payment Status**: Select "Partial" 
   - **Has Installment Plan**: ✅ Check this box

3. **Submit** → System redirects to installment plan selection

### Step 2: Assign Installment Plan  
1. **Enrollment**: Pre-selected from previous step
2. **Select Plan**: Choose from 6 available plans
3. **Installment Amount**: Will be calculated based on plan
4. **Start Date**: Set first payment due date
5. **Submit** → Plan assigned to enrollment

### Step 3: Generate Payment Schedule
The system should create individual Payment records for each installment:

**Example: ₹35,000 course with 3-Month Plan**
```
Payment 1: ₹11,667 due Date 1 (Status: Pending)
Payment 2: ₹11,667 due Date 2 (Status: Pending) 
Payment 3: ₹11,666 due Date 3 (Status: Pending)
```

### Step 4: Process Payments
1. Go to **Custom Admin → Payments**
2. Find payment record for enrollment
3. Update payment status to "Completed" when payment received
4. Enrollment status automatically updates:
   - 1 payment completed → "Partial"
   - All payments completed → "Completed"

## 🧪 Test Scenarios

### Scenario A: Quick 2-Month Plan
- **Course**: Django REST API (₹22,000)
- **Plan**: 2-Month Plan  
- **Payments**: ₹11,000 × 2 months
- **Timeline**: Complete in 2 months

### Scenario B: Budget 6-Month Plan  
- **Course**: Full Stack Bootcamp (₹35,000)
- **Plan**: 6-Month Plan
- **Payments**: ₹5,833 × 6 months  
- **Timeline**: Affordable monthly payments

### Scenario C: Extended 12-Month Plan
- **Course**: Data Science & ML (₹42,000)
- **Plan**: 12-Month Plan
- **Payments**: ₹3,500 × 12 months
- **Timeline**: Maximum affordability

## 📋 Testing Checklist

### ✅ Basic Functionality
- [ ] Create enrollment with installment plan
- [ ] Assign installment plan to enrollment  
- [ ] Generate payment schedule
- [ ] Process individual payments
- [ ] Update enrollment status

### ✅ Business Logic
- [ ] Verify installment amounts are correct
- [ ] Check payment due dates are properly spaced
- [ ] Confirm enrollment status updates correctly
- [ ] Test outstanding amount calculations
- [ ] Validate tax calculations

### ✅ Edge Cases
- [ ] What happens with course price changes?
- [ ] How to handle partial payments?
- [ ] Can installment plans be modified?
- [ ] What if payment is late/overdue?
- [ ] How to handle refunds/cancellations?

## 🚀 Ready for Production Testing

The test data is now ready! You can:

1. **Test the full enrollment workflow**
2. **Verify installment calculations** 
3. **Check payment processing**
4. **Validate business rules**
5. **Test different course price points**

All test plans use realistic pricing and common installment structures that students would actually choose.

---

**Next Steps:**
- Test the enrollment creation flow
- Verify installment plan assignment works
- Check payment processing functionality  
- Validate all calculations are correct
- Test with different course prices