// registration-form.js - Client-side validation for registration forms
// Purpose: Validate user input before submitting to server
// NO BUSINESS LOGIC - Only UI validation

// Wait for entire HTML page to load before running code
document.addEventListener('DOMContentLoaded', function() {
    
    // Find the registration form on the page
    const form = document.querySelector('.registration-form');
    
    // If no form exists on this page, stop execution (exit early)
    if (!form) return;
    
    // Find all input fields marked as required
    const requiredFields = form.querySelectorAll('[required]');
    
    // Find password fields (only exist on counselor registration page)
    const passwordField = document.getElementById('counselor_password');
    const confirmPasswordField = document.getElementById('counselor_password_confirm');
    
    // Find email input fields (can be multiple on one form)
    const emailFields = form.querySelectorAll('input[type="email"]');
    
    // Find phone number input fields (can be multiple on one form)
    const phoneFields = form.querySelectorAll('input[type="tel"]');
    
    // Find all text and email inputs for space trimming
    const textInputs = form.querySelectorAll('input[type="text"], input[type="email"]');
    
    // Find gender dropdown field (only on student registration)
    const genderField = document.getElementById('gender');
    

    // Find Hall dropdown field (only on student registration)
    const hallField = document.getElementById('hall');
    
    // ========== PASSWORD CONFIRMATION VALIDATION ==========
    // Only runs if both password fields exist (counselor form only)
    if (passwordField && confirmPasswordField) {
        
        // Listen for typing in the password confirmation field
        confirmPasswordField.addEventListener('input', function() {
            // Check if both passwords match
            if (this.value !== passwordField.value) {
                // Passwords don't match - show error
                this.setCustomValidity('Passwords do not match'); // Built-in browser validation message
                this.classList.add('invalid'); // Add red border (CSS class)
                this.classList.remove('valid'); // Remove green border
            } else {
                // Passwords match - clear error
                this.setCustomValidity(''); // Clear validation message
                this.classList.remove('invalid'); // Remove red border
                this.classList.add('valid'); // Add green border
            }
        });
        
        // Listen for typing in the main password field
        passwordField.addEventListener('input', function() {
            // If user already typed in confirmation field, recheck it
            if (confirmPasswordField.value) {
                // Trigger validation on confirmation field
                confirmPasswordField.dispatchEvent(new Event('input'));
            }
        });
    }
    
    // ========== EMAIL VALIDATION ==========
    // Loop through each email field found
    emailFields.forEach(field => {
        // Listen for when user leaves the email field (blur = lose focus)
        field.addEventListener('blur', function() {
            // Regular expression pattern for valid email format
            // Example: name@domain.com
            const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            
            // Test if email matches pattern AND field is not empty
            if (!emailPattern.test(this.value) && this.value !== '') {
                // Invalid email - show error
                this.classList.add('invalid'); // Add red border
                this.classList.remove('valid'); // Remove green border
            } else if (this.value !== '') {
                // Valid email - show success
                this.classList.remove('invalid'); // Remove red border
                this.classList.add('valid'); // Add green border
            }
            // If field is empty, do nothing (will be caught by required validation)
        });
    });
    
    // ========== GENDER DROPDOWN VALIDATION ==========
    // Only runs if gender field exists (student form only)
    if (genderField) {
        // Listen for when user selects an option
        genderField.addEventListener('change', function() {
            // Check if user selected the placeholder "Select Gender" option
            
            if (this.value === "") {
                // Invalid selection - show error
                this.classList.add('invalid'); // Add red border
                this.classList.remove('valid'); // Remove green border
            } else {
                // Valid selection - show success
                this.classList.remove('invalid'); // Remove red border
                this.classList.add('valid'); // Add green border
            }

            // Update hall dropdown based on gender selection
            if (hallField) {
                if (this.value === "male") {
                    hallField.innerHTML = `
                        <option value="">Select Hall</option>
                        <option value="Bethel Splendor">Bethel Splendor</option>
                        <option value="Emarald">Emarald</option>
                        <option value="Neal Wilson">Neal Wilson</option>
                        <option value="Nelson Meandela">Nelson Meandela</option>
                        <option value="Samual Akande">Samual Akande</option>
                        <option value="Topaz">Topaz</option>
                        <option value="Welch">Welch</option>
                        <option value="Winslow">Winslow</option>
                        <option value="Gamaliel">Gamaliel</option>
                        <option value="off campus">off campus</option>
                    `;
                } else if (this.value === "female") {
                    hallField.innerHTML = `
                        <option value="">Select Hall</option>
                        <option value="Diamond">Diamond</option>
                        <option value="Crystal">Crystal</option>
                        <option value="FAD">FAD</option>
                        <option value="Nyberg">Nyberg</option>
                        <option value="Queen Esther">Queen Esther</option>
                        <option value="Ogden">Ogden</option>
                        <option value="Havilah">Havilah</option>
                        <option value="Platinum">Platinum</option>
                        <option value="Sapphire">Sapphire</option>
                        <option value="white">white</option>
                        <option value="ameyo">ameyo</option>
                        <option value="off campus">off campus</option>
                    `;
                }
            }
        });
    }

    if (hallField) {
        // Listen for when user selects an option
        hallField.addEventListener('change', function() {
            // Check if user selected the placeholder "Select Hall" option
            if (this.value === "Select Hall" || this.value === "") {
                // Invalid selection - show error
                this.classList.add('invalid'); // Add red border
                this.classList.remove('valid'); // Remove green border
            } else {
                // Valid selection - show success
                this.classList.remove('invalid'); // Remove red border
                this.classList.add('valid'); // Add green border
            }
            console.log(this.value )
        });
    }

    // ========== PHONE NUMBER VALIDATION & FORMATTING ==========
    // Loop through each phone field found
    // Phone validation
    
    phoneFields.forEach(field => {
        // Format on blur
        field.addEventListener('blur', function() {
            let raw = this.value.replace(/\D/g, ''); // Remove non-digits
    
            // Auto-add +234 if number starts with 0
            if (raw.startsWith('0') && raw.length === 11) {
                raw = '234' + raw.slice(1);
            }
    
            // Format Nigerian number: +234 801 234 5678
            if (raw.startsWith('234') && raw.length === 13) {
                this.value = `+${raw.slice(0, 3)} ${raw.slice(3, 6)} ${raw.slice(6, 9)} ${raw.slice(9)}`;
            }
    
            // Nigerian phone validation pattern
            const phonePattern = /^(?:\+234|0)[789][01]\d{8}$/;
    
            if (!phonePattern.test(this.value.replace(/\s/g, '')) && this.value !== '') {
                this.classList.add('invalid');
                this.classList.remove('valid');
            } else if (this.value !== '') {
                this.classList.remove('invalid');
                this.classList.add('valid');
            }
        });
    });
    // Real-time validation for all required fields
    requiredFields.forEach(field => {
        field.addEventListener('input', function() {
            if (this.value.trim() === '') {
                this.classList.remove('valid');
            } else {
                this.classList.add('valid');
            }
        });
    })
    
    // ========== REAL-TIME VALIDATION FOR REQUIRED FIELDS ==========
    // Loop through each required field
    requiredFields.forEach(field => {
        // Listen for typing in the field
        field.addEventListener('input', function() {
            // Check if field is empty (after trimming whitespace)
            if (this.value.trim() === '') {
                // Field is empty - remove valid styling (but don't show error yet)
                this.classList.remove('valid');
            } else {
                // Field has content - show success
                this.classList.add('valid'); // Add green border
            }
        });
    });
    
    // ========== TRIM EXTRA SPACES IN TEXT INPUTS ==========
    // Loop through text and email inputs
    textInputs.forEach(input => {
        // Listen for typing
        input.addEventListener('input', function() {
            // Replace multiple spaces with single space
            // Example: "John    Doe" → "John Doe"
            this.value = this.value.replace(/\s+/g, ' ');
        });
    });
    
    // ========== FORM SUBMISSION VALIDATION ==========
    // Listen for form submission (when user clicks submit button)
    form.addEventListener('submit', function(e) {
        // Variable to track if form is valid
        let isValid = true;
        // Variable to store first field with error (for focusing)
        let firstInvalidField = null;
        
        // --- Check all required fields ---
        requiredFields.forEach(field => {
            // Check if field is empty (after trimming whitespace)
            if (field.value.trim() === '') {
                // Field is empty - mark as invalid
                isValid = false; // Form is not valid
                field.classList.add('invalid'); // Add red border
                
                // Store first invalid field (for focusing later)
                if (!firstInvalidField) {
                    firstInvalidField = field;
                }
            } else {
                // Field has content - remove error styling
                field.classList.remove('invalid');
            }
        });
        
        // --- Check password match (counselor form only) ---
        if (passwordField && confirmPasswordField) {
            // Check if passwords match
            if (passwordField.value !== confirmPasswordField.value) {
                // Passwords don't match - mark as invalid
                isValid = false; // Form is not valid
                confirmPasswordField.classList.add('invalid'); // Add red border
                
                // Store field for focusing if it's the first error
                if (!firstInvalidField) {
                    firstInvalidField = confirmPasswordField;
                }
                
                // Show alert to user
                alert('Passwords do not match. Please check and try again.');
            }
        }
    

        // --- Check password length (counselor form only) ---
        if (passwordField && passwordField.value.length < 8) {
            // Password is too short - mark as invalid
            isValid = false; // Form is not valid
            passwordField.classList.add('invalid'); // Add red border
            
            // Store field for focusing if it's the first error
            if (!firstInvalidField) {
                firstInvalidField = passwordField;
            }
            
            // Show alert to user
            alert('Password must be at least 8 characters long.');
        }
        
        // --- If form is invalid, prevent submission ---
        if (!isValid) {
            // Stop form from submitting to server
            e.preventDefault();
            
            // Focus on first field with error
            if (firstInvalidField) {
                // Move cursor to the field
                firstInvalidField.focus();
                // Scroll page to show the field in center of screen
                firstInvalidField.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
            
            // Show general error if not password-related
            if (!passwordField || (passwordField.value.length >= 8 && passwordField.value === confirmPasswordField.value)) {
                alert('Please fill in all required fields correctly.');
            }
        } else {
            // Form is valid - show loading state on submit button
            const submitButton = form.querySelector('.btn-primary');
            if (submitButton) {
                // Disable button to prevent double-submission
                submitButton.disabled = true;
                // Change button text to show processing
                submitButton.innerHTML = '<span class="btn-icon">⏳</span> Processing...';
            }
        }
    });
    
    // Auto-format phone number (optional)
    phoneFields.forEach(field => {
        field.addEventListener('input', function(e) {
            let value = this.value.replace(/\D/g, '');
            
            // Format as: +234-XXX-XXX-XXXX
            if (value.length > 0) {
                if (value.startsWith('234')) {
                    value = '+234 ' + value.slice(3);
                } else if (value.startsWith('0')) {
                    value = '+234 ' + value.slice(1);
                }
                
                // Add dashes
                if (value.length > 8) {
                    value = value.slice(0, 8) + ' ' + value.slice(8);
                }
                if (value.length > 12) {
                    value = value.slice(0, 12) + ' ' + value.slice(12);
                }
                
                this.value = value.slice(0, 18); // Limit length
            }
        });
    });

    // ========== PREVENT FORM RE-SUBMISSION ON PAGE RELOAD ==========
    // Check if browser supports history API
    if (window.history.replaceState) {
        // Replace current history entry (prevents re-submit on back button)
        window.history.replaceState(null, null, window.location.href);
    }
    
    // ========== AUTO-HIDE ALERT MESSAGES ==========
    // Wait 4 seconds (4000 milliseconds), then run this code
    setTimeout(() => {
        // Find all alert messages on page
        const alerts = document.querySelectorAll('.alert');
        // Loop through each alert
        alerts.forEach(alert => {
            // Hide the alert by setting display to none
            alert.style.display = 'none';
        });
    }, 4000); // 4000 = 4 seconds
    
}); // End of DOMContentLoaded event listener

// ============================================
// NOTES FOR BACKEND INTEGRATION
// ============================================

/*
⚠️ SECURITY WARNING: Client-side validation is NOT secure!
Users can bypass JavaScript validation using browser developer tools.

Backend MUST implement:
1. Server-side validation of ALL fields (never trust client data)
2. Email uniqueness check (prevent duplicate accounts)
3. Password hashing with bcrypt/pbkdf2 (NEVER store plain text passwords)
4. CSRF protection (prevent cross-site request forgery)
5. Rate limiting (prevent spam/brute force attacks)
6. Input sanitization (prevent SQL injection, XSS attacks)
7. Role verification (counselor can create students, admin can create counselors)
8. Student capacity check (max 5 per counselor)

Client-side validation = Good user experience (instant feedback)
Server-side validation = Security (protect your data)

Always use BOTH!
*/