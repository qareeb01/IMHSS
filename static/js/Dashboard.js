// dashboard.js - Modern Dashboard Navigation

document.addEventListener('DOMContentLoaded', function() {
    
    // ========== MOBILE MENU SETUP (EXACTLY LIKE STUDENT DASHBOARD) ==========
    initializeMobileMenu();
    
    // ========== SIDEBAR NAVIGATION ==========
    const sidebarLinks = document.querySelectorAll('.sidebar-link');
    const tabContents = document.querySelectorAll('.tab-content');
    
    sidebarLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Remove active class from all links
            sidebarLinks.forEach(l => l.classList.remove('active'));
            
            // Add active class to clicked link
            this.classList.add('active');
            
            // Get target tab
            const targetTab = this.getAttribute('data-tab');
            
            // Hide all tabs
            tabContents.forEach(tab => tab.classList.remove('active'));
            
            // Show target tab
            const targetElement = document.getElementById(`${targetTab}-tab`);
            if (targetElement) {
                targetElement.classList.add('active');
            }
            
            // Close mobile menu after navigation
            closeMobileMenu();
        });
    });
    
    // ========== QUICK ACTION BUTTONS WITH TAB SWITCHING ==========
    const actionButtons = document.querySelectorAll('.action-btn[data-tab]');
    
    actionButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            // Only handle if it has data-tab (tab switching, not external links)
            const targetTab = this.getAttribute('data-tab');
            
            if (targetTab) {
                e.preventDefault();
                
                // Remove active class from all sidebar links
                sidebarLinks.forEach(l => l.classList.remove('active'));
                
                // Add active class to corresponding sidebar link
                const correspondingSidebarLink = document.querySelector(`.sidebar-link[data-tab="${targetTab}"]`);
                if (correspondingSidebarLink) {
                    correspondingSidebarLink.classList.add('active');
                }
                
                // Hide all tabs
                tabContents.forEach(tab => tab.classList.remove('active'));
                
                // Show target tab
                const targetElement = document.getElementById(`${targetTab}-tab`);
                if (targetElement) {
                    targetElement.classList.add('active');
                }
                
                // Close mobile menu after navigation
                closeMobileMenu();
                
                // Scroll to top
                window.scrollTo({ top: 0, behavior: 'smooth' });
            }
            // If no data-tab, let the link navigate normally (like "Register Student")
        });
    });
    
    // ========== SECTION TABS NAVIGATION ==========
    const sectionTabs = document.querySelectorAll('.section-tab');
    const contentSections = document.querySelectorAll('.content-section-area');
    
    sectionTabs.forEach(tab => {
        tab.addEventListener('click', function() {
            // Remove active class from all tabs
            sectionTabs.forEach(t => t.classList.remove('active'));
            
            // Add active class to clicked tab
            this.classList.add('active');
            
            // Get target section
            const targetSection = this.getAttribute('data-section');
            
            // Hide all sections
            contentSections.forEach(section => section.classList.remove('active'));
            
            // Show target section
            const targetElement = document.getElementById(targetSection);
            if (targetElement) {
                targetElement.classList.add('active');
            }
        });
    });
    
    // ========== AUTO-HIDE ALERTS ==========
    setTimeout(() => {
        const alerts = document.querySelectorAll('.alert');
        alerts.forEach(alert => {
            alert.style.display = 'none';
        });
    }, 4000);
    
});

// ========================================
// MOBILE MENU FUNCTIONALITY (SAME AS STUDENT DASHBOARD)
// ========================================
function initializeMobileMenu() {
    // Create mobile menu toggle button if it doesn't exist
    if (!document.querySelector('.mobile-menu-toggle')) {
        const toggleBtn = document.createElement('button');
        toggleBtn.className = 'mobile-menu-toggle';
        toggleBtn.setAttribute('aria-label', 'Toggle menu');
        toggleBtn.innerHTML = `
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="3" y1="12" x2="21" y2="12"></line>
                <line x1="3" y1="6" x2="21" y2="6"></line>
                <line x1="3" y1="18" x2="21" y2="18"></line>
            </svg>
        `;
        document.body.appendChild(toggleBtn);
        
        toggleBtn.addEventListener('click', toggleMobileMenu);
    }
    
    // Create overlay if it doesn't exist
    if (!document.querySelector('.sidebar-overlay')) {
        const overlay = document.createElement('div');
        overlay.className = 'sidebar-overlay';
        document.body.appendChild(overlay);
        
        overlay.addEventListener('click', closeMobileMenu);
    }
    
    // Add close button to sidebar
    const sidebar = document.querySelector('.sidebar-left');
    if (sidebar && !sidebar.querySelector('.mobile-close-btn')) {
        const closeBtn = document.createElement('button');
        closeBtn.className = 'mobile-close-btn';
        closeBtn.setAttribute('aria-label', 'Close menu');
        closeBtn.innerHTML = `
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
        `;
        sidebar.appendChild(closeBtn);
        
        closeBtn.addEventListener('click', closeMobileMenu);
    }
}

function toggleMobileMenu() {
    const sidebar = document.querySelector('.sidebar-left');
    const overlay = document.querySelector('.sidebar-overlay');
    
    if (sidebar && overlay) {
        const isActive = sidebar.classList.contains('active');
        
        if (isActive) {
            closeMobileMenu();
        } else {
            openMobileMenu();
        }
    }
}

function openMobileMenu() {
    const sidebar = document.querySelector('.sidebar-left');
    const overlay = document.querySelector('.sidebar-overlay');
    
    if (sidebar && overlay) {
        sidebar.classList.add('active');
        overlay.classList.add('active');
        document.body.style.overflow = 'hidden';
    }
}

function closeMobileMenu() {
    const sidebar = document.querySelector('.sidebar-left');
    const overlay = document.querySelector('.sidebar-overlay');
    
    if (sidebar && overlay) {
        sidebar.classList.remove('active');
        overlay.classList.remove('active');
        document.body.style.overflow = '';
    }
}

// ========================================
// MODERN REAL-TIME NOTIFICATION SYSTEM
// ========================================

// Only run on counselor dashboard
if (window.location.pathname.includes('counselor/dashboard')) {
    let lastNotificationCount = 0;
    let notificationQueue = [];
    
    // Check for new notifications every 30 seconds
    setInterval(async function() {
        await checkForNewNotifications();
    }, 10000);
    
    // Initial check on page load
    setTimeout(checkForNewNotifications, 2000);
    
    async function checkForNewNotifications() {
        try {
            const response = await fetch('/counselor/check-notifications');
            const data = await response.json();
            
            // If there are new notifications
            if (data.count > lastNotificationCount && lastNotificationCount > 0) {
                const newFlags = data.count - lastNotificationCount;
                
                // Show in-app notification for each new flag
                data.flags.slice(0, newFlags).forEach((flag, index) => {
                    setTimeout(() => {
                        showInAppNotification(flag);
                    }, index * 500); // Stagger notifications by 500ms
                });
                
                // Show browser notification (only one summary)
                showBrowserNotification(`${newFlags} New High-Risk Alert(s)`, data.flags[0]);
                
                // Play notification sound
                playNotificationSound();
            }
            
            // Update badge count
            updateNotificationBadge(data.count);
            
            // If user is on flagged tab and there are new notifications, refresh the page
            const flaggedTab = document.getElementById('flagged-tab');
            if (flaggedTab && flaggedTab.classList.contains('active') && 
                data.count > lastNotificationCount && lastNotificationCount > 0) {
                location.reload();
            }
            
            // Update last known count
            lastNotificationCount = data.count;
            
        } catch (error) {
            console.error('Notification check failed:', error);
        }
    }
    
    // ========================================
    // IN-APP NOTIFICATION (MODERN TOAST)
    // ========================================
    function showInAppNotification(flag) {
        // Create notification container if it doesn't exist
        let container = document.getElementById('notification-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'notification-container';
            document.body.appendChild(container);
        }
        
        // Create notification element
        const notification = document.createElement('div');
        notification.className = 'toast-notification';
        
        // Format time
        const timeAgo = getTimeAgo(new Date(flag.flagged_at));
        
        notification.innerHTML = `
            <div class="toast-icon">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
                    <line x1="12" y1="9" x2="12" y2="13"></line>
                    <line x1="12" y1="17" x2="12.01" y2="17"></line>
                </svg>
            </div>
            <div class="toast-content">
                <div class="toast-header">
                    <h4>High-Risk Alert</h4>
                    <span class="toast-time">${timeAgo}</span>
                </div>
                <p class="toast-student">${flag.student_name}</p>
                <p class="toast-keywords">
                    ${flag.keywords.map(k => `<span class="keyword-pill">${k}</span>`).join(' ')}
                </p>
                <div class="toast-actions">
                    <button class="toast-btn primary" onclick="viewFlaggedMessages()">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                            <circle cx="12" cy="12" r="3"></circle>
                        </svg>
                        Review Now
                    </button>
                    <button class="toast-btn dismiss" onclick="this.closest('.toast-notification').remove()">
                        Dismiss
                    </button>
                </div>
            </div>
            <button class="toast-close" onclick="this.parentElement.remove()">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <line x1="18" y1="6" x2="6" y2="18"></line>
                    <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
            </button>
        `;
        
        // Add to container
        container.appendChild(notification);
        
        // Animate in
        setTimeout(() => {
            notification.classList.add('show');
        }, 100);
        
        // Auto-remove after 10 seconds
        setTimeout(() => {
            notification.classList.add('hide');
            setTimeout(() => {
                notification.remove();
            }, 300);
        }, 10000);
    }
    
    // ========================================
    // BROWSER NOTIFICATION (DESKTOP)
    // ========================================
    function showBrowserNotification(title, flag) {
        if (!("Notification" in window)) return;
        
        if (Notification.permission === "granted") {
            createBrowserNotification(title, flag);
        } else if (Notification.permission !== "denied") {
            Notification.requestPermission().then(function(permission) {
                if (permission === "granted") {
                    createBrowserNotification(title, flag);
                }
            });
        }
    }
    
    function createBrowserNotification(title, flag) {
        const notification = new Notification(title, {
            body: `Student: ${flag.student_name}\nKeywords: ${flag.keywords.join(', ')}`,
            icon: '/static/images/alert-icon.png',
            badge: '/static/images/badge-icon.png',
            tag: 'high-risk-alert',
            requireInteraction: true,
            vibrate: [200, 100, 200]
        });
        
        notification.onclick = function() {
            window.focus();
            viewFlaggedMessages();
            notification.close();
        };
    }
    
    // ========================================
    // NOTIFICATION BADGE
    // ========================================
    function updateNotificationBadge(count) {
        const flaggedLink = document.querySelector('[data-tab="flagged"]');
        if (!flaggedLink) return;
        
        // Remove existing badge
        const existingBadge = flaggedLink.querySelector('.notification-badge');
        if (existingBadge) {
            existingBadge.remove();
        }
        
        // Add new badge if count > 0
        if (count > 0) {
            const badge = document.createElement('span');
            badge.className = 'notification-badge';
            badge.textContent = count > 99 ? '99+' : count;
            flaggedLink.appendChild(badge);
            
            // Animate badge
            setTimeout(() => {
                badge.classList.add('bounce');
            }, 100);
        }
    }
    
    // ========================================
    // NOTIFICATION SOUND
    // ========================================
    function playNotificationSound() {
        // Create a pleasant notification sound using Web Audio API
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        
        // Create oscillator for a pleasant "ding" sound
        const oscillator = audioContext.createOscillator();
        const gainNode = audioContext.createGain();
        
        oscillator.connect(gainNode);
        gainNode.connect(audioContext.destination);
        
        // Set frequency for a pleasant tone
        oscillator.frequency.setValueAtTime(800, audioContext.currentTime);
        oscillator.frequency.exponentialRampToValueAtTime(600, audioContext.currentTime + 0.1);
        
        // Set volume envelope
        gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.5);
        
        // Play sound
        oscillator.start(audioContext.currentTime);
        oscillator.stop(audioContext.currentTime + 0.5);
    }
    
    // ========================================
    // HELPER FUNCTIONS
    // ========================================
    function getTimeAgo(date) {
        const seconds = Math.floor((new Date() - date) / 1000);
        
        if (seconds < 60) return 'Just now';
        if (seconds < 3600) return `${Math.floor(seconds / 60)} min ago`;
        if (seconds < 86400) return `${Math.floor(seconds / 3600)} hours ago`;
        return `${Math.floor(seconds / 86400)} days ago`;
    }
    
    console.log('🔔 Modern notification system enabled');
}

// ========================================
// GLOBAL HELPER FUNCTIONS
// ========================================
function viewFlaggedMessages() {
    // Reload page to fetch latest flags, then navigate to flagged tab
    window.location.href = window.location.pathname + '#flagged';
    window.location.reload();
}

// ========================================
// NOTIFICATION PERMISSION HANDLER
// ========================================
const enableNotificationsBtn = document.getElementById('enable-notifications-btn');

if (enableNotificationsBtn) {
    // Show button if notifications not granted
    if (Notification.permission !== "granted") {
        enableNotificationsBtn.style.display = 'flex';
    }
    
    enableNotificationsBtn.addEventListener('click', async function() {
        if (!("Notification" in window)) {
            showPermissionModal(
                'Not Supported',
                'Your browser doesn\'t support desktop notifications.',
                false
            );
            return;
        }
        
        const permission = await Notification.requestPermission();
        
        if (permission === "granted") {
            showPermissionModal(
                'Notifications Enabled!',
                'You\'ll now receive real-time alerts for high-risk messages.',
                true
            );
            this.style.display = 'none';
            
            // Show test notification
            setTimeout(() => {
                showInAppNotification({
                    student_name: 'Test Student',
                    flagged_at: new Date().toISOString(),
                    keywords: ['test notification']
                });
            }, 1000);
        } else {
            showPermissionModal(
                'Notifications Blocked',
                'Please enable notifications in your browser settings to receive alerts.',
                false
            );
        }
    });
}

function showPermissionModal(title, message, success) {
    const modal = document.createElement('div');
    modal.className = 'notification-permission-modal';
    modal.innerHTML = `
        <div class="notification-permission-content">
            <div class="icon">
                <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    ${success 
                        ? '<polyline points="20 6 9 17 4 12"></polyline>'
                        : '<circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line>'
                    }
                </svg>
            </div>
            <h3>${title}</h3>
            <p>${message}</p>
            <div class="permission-actions">
                <button class="permission-btn allow" onclick="this.closest('.notification-permission-modal').remove()">
                    Got it
                </button>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    // Close on outside click
    modal.addEventListener('click', function(e) {
        if (e.target === modal) {
            modal.remove();
        }
    });
    
    // Auto-close after 3 seconds
    setTimeout(() => {
        modal.remove();
    }, 3000);
}

// ========================================
// PASSWORD CHANGE - STRENGTH & VALIDATION
// ========================================
(function initPasswordChangeValidation() {
    const newPasswordInput = document.getElementById('new_password');
    const confirmPasswordInput = document.getElementById('confirm_password');
    const strengthIndicator = document.getElementById('password-strength');
    const matchMessage = document.getElementById('password-match-message');
    const submitBtn = document.getElementById('change-password-btn');

    // Only run if password change elements exist
    if (!newPasswordInput || !confirmPasswordInput) return;

    // Password strength checker
    if (newPasswordInput && strengthIndicator) {
        newPasswordInput.addEventListener('input', function() {
            const password = this.value;
            const strength = checkPasswordStrength(password);
            
            strengthIndicator.innerHTML = `
                <div style="display: flex; gap: 4px; margin-bottom: 4px;">
                    <div style="flex: 1; height: 4px; background: ${strength.level >= 1 ? strength.color : '#e2e8f0'}; border-radius: 2px;"></div>
                    <div style="flex: 1; height: 4px; background: ${strength.level >= 2 ? strength.color : '#e2e8f0'}; border-radius: 2px;"></div>
                    <div style="flex: 1; height: 4px; background: ${strength.level >= 3 ? strength.color : '#e2e8f0'}; border-radius: 2px;"></div>
                    <div style="flex: 1; height: 4px; background: ${strength.level >= 4 ? strength.color : '#e2e8f0'}; border-radius: 2px;"></div>
                </div>
                <p style="margin: 0; font-size: 0.75rem; color: ${strength.color}; font-weight: 500;">
                    ${strength.text}
                </p>
            `;
            
            checkPasswordMatch();
        });
    }

    // Password match checker
    if (confirmPasswordInput && matchMessage) {
        confirmPasswordInput.addEventListener('input', checkPasswordMatch);
        newPasswordInput.addEventListener('input', checkPasswordMatch);
    }

    function checkPasswordMatch() {
        const newPassword = newPasswordInput.value;
        const confirmPassword = confirmPasswordInput.value;
        
        if (confirmPassword === '') {
            matchMessage.textContent = '';
            matchMessage.style.color = '';
            return;
        }
        
        if (newPassword === confirmPassword) {
            matchMessage.textContent = '✓ Passwords match';
            matchMessage.style.color = '#48bb78';
            if (submitBtn) submitBtn.disabled = false;
        } else {
            matchMessage.textContent = '✗ Passwords do not match';
            matchMessage.style.color = '#f56565';
            if (submitBtn) submitBtn.disabled = true;
        }
    }

    function checkPasswordStrength(password) {
        let strength = 0;
        let text = 'Too weak';
        let color = '#f56565';
        
        if (password.length >= 8) strength++;
        if (password.length >= 12) strength++;
        if (/[a-z]/.test(password) && /[A-Z]/.test(password)) strength++;
        if (/\d/.test(password)) strength++;
        if (/[^a-zA-Z\d]/.test(password)) strength++;
        
        if (strength <= 1) {
            text = 'Weak password';
            color = '#f56565';
        } else if (strength === 2) {
            text = 'Fair password';
            color = '#ed8936';
        } else if (strength === 3) {
            text = 'Good password';
            color = '#ecc94b';
        } else if (strength >= 4) {
            text = 'Strong password';
            color = '#48bb78';
        }
        
        return { level: strength, text: text, color: color };
    }

    // Form validation
    const passwordForm = document.getElementById('password-change-form');
    if (passwordForm) {
        passwordForm.addEventListener('submit', function(e) {
            const newPassword = newPasswordInput.value;
            const confirmPassword = confirmPasswordInput.value;
            
            if (newPassword !== confirmPassword) {
                e.preventDefault();
                alert('Passwords do not match. Please check and try again.');
                return false;
            }
            
            if (newPassword.length < 8) {
                e.preventDefault();
                alert('Password must be at least 8 characters long.');
                return false;
            }
        });
    }
})();

// ========================================
// CHARACTER COUNTER - MESSAGE BODY
// ========================================
(function initCharacterCounter() {
    const bodyEl = document.getElementById('body');
    const countEl = document.getElementById('bodyCount');
    
    if (!bodyEl || !countEl) return;
    
    function updateCounter() {
        const length = bodyEl.value.length;
        countEl.textContent = length;
        countEl.style.color = length > 3800 ? '#c53030' : '#718096';
    }
    
    bodyEl.addEventListener('input', updateCounter);
    updateCounter();
})();