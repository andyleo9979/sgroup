document.addEventListener('DOMContentLoaded', function() {
    // Initialize form validation for all forms with the 'needs-validation' class
    const forms = document.querySelectorAll('.needs-validation');
    
    // Loop over them and prevent submission if validation fails
    Array.from(forms).forEach(form => {
        form.addEventListener('submit', event => {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            
            form.classList.add('was-validated');
        }, false);
    });
    
    // Add custom validation for common fields
    setupEmailValidation();
    setupPasswordValidation();
    setupDateValidation();
    setupNumberValidation();
    setupPhoneValidation();
});

/**
 * Setup email validation
 */
function setupEmailValidation() {
    const emailInputs = document.querySelectorAll('input[type="email"]');
    
    emailInputs.forEach(input => {
        input.addEventListener('input', function() {
            const email = this.value;
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            
            if (email && !emailRegex.test(email)) {
                this.setCustomValidity('Please enter a valid email address');
            } else {
                this.setCustomValidity('');
            }
        });
    });
}

/**
 * Setup password validation for password fields
 */
function setupPasswordValidation() {
    const passwordInputs = document.querySelectorAll('input[type="password"][data-password-validate="true"]');
    
    passwordInputs.forEach(input => {
        input.addEventListener('input', function() {
            const password = this.value;
            
            // Check if password is at least 8 characters
            if (password && password.length < 8) {
                this.setCustomValidity('Password must be at least 8 characters long');
            } else {
                this.setCustomValidity('');
            }
        });
    });
    
    // Setup password confirmation validation
    const passwordConfirmInputs = document.querySelectorAll('input[data-password-confirm-for]');
    
    passwordConfirmInputs.forEach(input => {
        input.addEventListener('input', function() {
            const mainPasswordId = this.getAttribute('data-password-confirm-for');
            const mainPassword = document.getElementById(mainPasswordId);
            
            if (mainPassword && this.value !== mainPassword.value) {
                this.setCustomValidity('Passwords do not match');
            } else {
                this.setCustomValidity('');
            }
        });
    });
}

/**
 * Setup date validation
 */
function setupDateValidation() {
    const dateInputs = document.querySelectorAll('input[type="date"]');
    
    dateInputs.forEach(input => {
        // Check if the input has min or max attributes
        const minDate = input.getAttribute('min');
        const maxDate = input.getAttribute('max');
        
        input.addEventListener('input', function() {
            const date = this.value ? new Date(this.value) : null;
            
            if (date) {
                if (minDate && new Date(minDate) > date) {
                    this.setCustomValidity(`Date cannot be before ${minDate}`);
                } else if (maxDate && new Date(maxDate) < date) {
                    this.setCustomValidity(`Date cannot be after ${maxDate}`);
                } else {
                    this.setCustomValidity('');
                }
            }
        });
    });
}

/**
 * Setup number validation for numeric inputs
 */
function setupNumberValidation() {
    const numberInputs = document.querySelectorAll('input[type="number"]');
    
    numberInputs.forEach(input => {
        const min = input.getAttribute('min');
        const max = input.getAttribute('max');
        
        input.addEventListener('input', function() {
            const value = parseFloat(this.value);
            
            if (!isNaN(value)) {
                if (min !== null && value < parseFloat(min)) {
                    this.setCustomValidity(`Value cannot be less than ${min}`);
                } else if (max !== null && value > parseFloat(max)) {
                    this.setCustomValidity(`Value cannot be greater than ${max}`);
                } else {
                    this.setCustomValidity('');
                }
            }
        });
    });
}

/**
 * Setup phone number validation
 */
function setupPhoneValidation() {
    const phoneInputs = document.querySelectorAll('input[type="tel"]');
    
    phoneInputs.forEach(input => {
        input.addEventListener('input', function() {
            const phone = this.value;
            // Basic phone validation - can be improved for specific country formats
            const phoneRegex = /^\+?[0-9]{10,15}$/;
            
            if (phone && !phoneRegex.test(phone.replace(/[\s-]/g, ''))) {
                this.setCustomValidity('Please enter a valid phone number (10-15 digits)');
            } else {
                this.setCustomValidity('');
            }
        });
    });
}

/**
 * Dynamically update available courses based on selected student
 * @param {string} studentId - ID of the selected student
 * @param {string} courseSelectId - ID of the course select element
 */
function updateCoursesByStudent(studentId, courseSelectId) {
    const courseSelect = document.getElementById(courseSelectId);
    
    if (!courseSelect || !studentId) {
        return;
    }
    
    // Clear current options
    courseSelect.innerHTML = '<option value="">Select a course</option>';
    courseSelect.disabled = true;
    
    fetch(`/api/students/${studentId}/available-courses`)
        .then(response => response.json())
        .then(data => {
            // Add options for each available course
            data.courses.forEach(course => {
                const option = document.createElement('option');
                option.value = course.id;
                option.textContent = course.name;
                courseSelect.appendChild(option);
            });
            
            courseSelect.disabled = false;
        })
        .catch(error => {
            console.error('Error fetching available courses:', error);
            // Add a disabled option indicating error
            const option = document.createElement('option');
            option.textContent = 'Error loading courses';
            option.disabled = true;
            courseSelect.appendChild(option);
        });
}

/**
 * Show confirmation dialog before delete
 * @param {string} itemType - Type of item being deleted (e.g., 'student', 'course')
 * @returns {boolean} True if confirmed, false otherwise
 */
function confirmDelete(itemType) {
    return confirm(`Are you sure you want to delete this ${itemType}? This action cannot be undone.`);
}
