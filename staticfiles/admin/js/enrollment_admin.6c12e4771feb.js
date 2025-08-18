(function($) {
    'use strict';
    
    function updateEnrollmentPricing() {
        var courseSelect = $('#id_course');
        var totalAmountField = $('#id_total_amount');
        var taxAmountField = $('#id_tax_amount');
        var paymentStatusField = $('#id_payment_status');
        
        if (courseSelect.length && totalAmountField.length) {
            courseSelect.change(function() {
                var courseId = $(this).val();
                if (courseId) {
                    // Fetch course pricing via AJAX
                    $.ajax({
                        url: '/admin/payments/enrollment/get-course-pricing/',
                        data: {
                            'course_id': courseId
                        },
                        success: function(data) {
                            if (data.is_free) {
                                totalAmountField.val('0.00');
                                taxAmountField.val('0.00');
                                paymentStatusField.val('free');
                                
                                // Hide payment fields for free courses and mark as not required
                                $('.field-total_amount, .field-tax_amount').hide();
                                $('.field-total_amount input, .field-tax_amount input').removeAttr('required');
                                $('.field-payment_status').find('select option[value="free"]').prop('selected', true);
                                
                                // Add note for free course
                                if (!$('.free-course-note').length) {
                                    $('.field-course').after('<div class="free-course-note" style="color: green; font-weight: bold; margin: 10px 0;">✅ This is a free course - payment fields are automatically set to 0</div>');
                                }
                            } else {
                                totalAmountField.val(data.total_price);
                                taxAmountField.val(data.tax_amount);
                                paymentStatusField.val('pending');
                                
                                // Show payment fields for paid courses and mark as required
                                $('.field-total_amount, .field-tax_amount').show();
                                $('.field-total_amount input, .field-tax_amount input').attr('required', 'required');
                                
                                // Remove free course note
                                $('.free-course-note').remove();
                            }
                        },
                        error: function() {
                            console.log('Error fetching course pricing');
                        }
                    });
                } else {
                    // Show all fields if no course selected
                    $('.field-total_amount, .field-tax_amount').show();
                    $('.free-course-note').remove();
                }
            });
            
            // Trigger change event on page load if course is already selected
            if (courseSelect.val()) {
                courseSelect.trigger('change');
            }
        }
    }
    
    $(document).ready(function() {
        updateEnrollmentPricing();
    });
    
})(django.jQuery);