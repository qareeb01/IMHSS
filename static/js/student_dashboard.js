// student_dashboard.js 

// ========== GLOBAL STATE ==========
let currentSessionId = generateSessionId();
let chatHistoryLoaded = false;

// ========== NAVIGATION ==========
document.addEventListener('DOMContentLoaded', function() {
    initializeMobileMenu(); // Add mobile menu functionality
    setupNavigation();
    setupChatFunctionality();
    setupBreathingExercises();
    setupStretchingExercises();
    setupMoodTracker();
    loadChatHistory(); // Load previous chat messages
    autoHideAlerts(); // Auto-hide flash messages
});

// ========== AUTO-HIDE ALERTS ==========
function autoHideAlerts() {
    setTimeout(() => {
        const alerts = document.querySelectorAll('.alert');
        alerts.forEach(alert => {
            alert.style.animation = 'slideOutRight 0.5s forwards';
            setTimeout(() => {
                alert.remove();
            }, 500);
        });
    }, 4000); // Hide after 4 seconds
}

// ========== MOBILE MENU FUNCTIONALITY ==========
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
    const sidebar = document.querySelector('.student-sidebar');
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
    const sidebar = document.querySelector('.student-sidebar');
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
    const sidebar = document.querySelector('.student-sidebar');
    const overlay = document.querySelector('.sidebar-overlay');
    
    if (sidebar && overlay) {
        sidebar.classList.add('active');
        overlay.classList.add('active');
        document.body.style.overflow = 'hidden';
    }
}

function closeMobileMenu() {
    const sidebar = document.querySelector('.student-sidebar');
    const overlay = document.querySelector('.sidebar-overlay');
    
    if (sidebar && overlay) {
        sidebar.classList.remove('active');
        overlay.classList.remove('active');
        document.body.style.overflow = '';
    }
}

function setupNavigation() {
    const navLinks = document.querySelectorAll('.sidebar-link');
    const sections = document.querySelectorAll('.content-section');

    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Remove active class from all links and sections
            navLinks.forEach(l => l.classList.remove('active'));
            sections.forEach(s => s.classList.remove('active'));
            
            // Add active class to clicked link
            this.classList.add('active');
            
            // Show corresponding section
            const sectionId = this.getAttribute('data-section') + '-section';
            const targetSection = document.getElementById(sectionId);
            if (targetSection) {
                targetSection.classList.add('active');
                
                // If switching to chat section and history not loaded, load it
                if (sectionId === 'chat-section' && !chatHistoryLoaded) {
                    loadChatHistory();
                }
            }
            
            // Close mobile menu after navigation
            closeMobileMenu();
        });
    });
}

// ========== CHAT HISTORY LOADING ==========
async function loadChatHistory() {
    try {
        const response = await fetch('/student/chat/history', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            console.error('Failed to load chat history');
            return;
        }

        const data = await response.json();
        
        if (data.success && data.messages && data.messages.length > 0) {
            const chatMessages = document.getElementById('chat-messages');
            // Clear the initial welcome message
            chatMessages.innerHTML = '';
            
            // Display all previous messages
            data.messages.forEach(msg => {
                displayUserMessage(msg.content, new Date(msg.timestamp));
                displayAIMessage(msg.ai_response, new Date(msg.timestamp));
            });
            
            // Scroll to bottom
            chatMessages.scrollTop = chatMessages.scrollHeight;
            chatHistoryLoaded = true;
        }
    } catch (error) {
        console.error('Error loading chat history:', error);
    }
}

// ========== CHAT FUNCTIONALITY ==========
function setupChatFunctionality() {
    const chatInput = document.getElementById('chat-input');
    const sendBtn = document.getElementById('send-btn');
    const chatMessages = document.getElementById('chat-messages');

    // Auto-resize textarea
    chatInput.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = Math.min(this.scrollHeight, 120) + 'px';
    });

    // Send on Enter (Shift+Enter for new line)
    chatInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // Send on button click
    sendBtn.addEventListener('click', sendMessage);
}

async function sendMessage() {
    const chatInput = document.getElementById('chat-input');
    const message = chatInput.value.trim();

    if (!message) return;

    // Display user message immediately
    displayUserMessage(message);

    // Clear input and reset height
    chatInput.value = '';
    chatInput.style.height = 'auto';

    // Show typing indicator
    showTypingIndicator();

    try {
        const response = await fetch('/student/chat/send', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message: message,
                session_id: currentSessionId
            })
        });

        const data = await response.json();

        // Hide typing indicator
        hideTypingIndicator();

        if (data.success && data.ai_response) {
            displayAIMessage(data.ai_response);
        } else {
            displayAIMessage("I'm sorry, I'm having trouble responding right now. Please try again.");
        }

    } catch (error) {
        hideTypingIndicator();
        displayAIMessage("I'm sorry, I'm having trouble connecting right now. Please try again.");
        console.error('Chat error:', error);
    }
}

function displayUserMessage(content, timestamp = new Date()) {
    const chatMessages = document.getElementById('chat-messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message user-message';
    
    messageDiv.innerHTML = `
        <div class="message-content">
            <p>${escapeHtml(content)}</p>
        </div>
        <span class="message-time">${formatTime(timestamp)}</span>
    `;
    
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function displayAIMessage(content, timestamp = new Date()) {
    const chatMessages = document.getElementById('chat-messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message ai-message';
    
    messageDiv.innerHTML = `
        <div class="message-content">
            <p>${escapeHtml(content)}</p>
        </div>
        <span class="message-time">${formatTime(timestamp)}</span>
    `;
    
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function showTypingIndicator() {
    document.getElementById('typing-indicator').style.display = 'flex';
    const chatMessages = document.getElementById('chat-messages');
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function hideTypingIndicator() {
    document.getElementById('typing-indicator').style.display = 'none';
}

// ========== BREATHING EXERCISES ==========
function setupBreathingExercises() {
    const exerciseButtons = document.querySelectorAll('.start-exercise-btn[data-exercise]');
    const modal = document.getElementById('breathing-modal');
    const closeBtn = modal.querySelector('.close-modal-btn');
    const stopBtn = document.getElementById('stop-breathing-btn');

    exerciseButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            const exerciseType = this.getAttribute('data-exercise');
            startBreathingExercise(exerciseType);
        });
    });

    closeBtn.addEventListener('click', stopBreathingExercise);
    stopBtn.addEventListener('click', stopBreathingExercise);
}

let breathingInterval = null;

function startBreathingExercise(type) {
    const modal = document.getElementById('breathing-modal');
    const title = document.getElementById('exercise-title');
    const instruction = document.getElementById('breathing-instruction');
    const timer = document.getElementById('breathing-timer');
    const circle = document.getElementById('breathing-circle');

    modal.style.display = 'flex';

    let phases = [];
    if (type === 'box') {
        title.textContent = 'Box Breathing';
        phases = [
            { text: 'Breathe In', duration: 4, scale: 1.2 },
            { text: 'Hold', duration: 4, scale: 1.2 },
            { text: 'Breathe Out', duration: 4, scale: 1 },
            { text: 'Hold', duration: 4, scale: 1 }
        ];
    } else if (type === '478') {
        title.textContent = '4-7-8 Breathing';
        phases = [
            { text: 'Breathe In', duration: 4, scale: 1.2 },
            { text: 'Hold', duration: 7, scale: 1.2 },
            { text: 'Breathe Out', duration: 8, scale: 1 }
        ];
    } else {
        title.textContent = 'Deep Breathing';
        phases = [
            { text: 'Breathe In', duration: 5, scale: 1.2 },
            { text: 'Breathe Out', duration: 5, scale: 1 }
        ];
    }

    let phaseIndex = 0;
    let countdown = phases[0].duration;

    function updateBreathing() {
        const currentPhase = phases[phaseIndex];
        instruction.textContent = currentPhase.text;
        timer.textContent = countdown;

        circle.style.transform = `scale(${currentPhase.scale})`;
        circle.style.transition = `transform ${countdown}s ease-in-out`;

        countdown--;

        if (countdown < 0) {
            phaseIndex = (phaseIndex + 1) % phases.length;
            countdown = phases[phaseIndex].duration;
        }
    }

    updateBreathing();
    breathingInterval = setInterval(updateBreathing, 1000);
}

function stopBreathingExercise() {
    if (breathingInterval) {
        clearInterval(breathingInterval);
        breathingInterval = null;
    }
    document.getElementById('breathing-modal').style.display = 'none';
}

// ========== STRETCHING EXERCISES ==========
function setupStretchingExercises() {
    const stretchButtons = document.querySelectorAll('.start-exercise-btn[data-stretch]');
    const modal = document.getElementById('stretching-modal');
    const closeBtn = modal.querySelector('.close-modal-btn');
    const nextBtn = document.getElementById('next-stretch-btn');
    const stopBtn = document.getElementById('stop-stretch-btn');

    stretchButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            const stretchType = this.getAttribute('data-stretch');
            startStretchingExercise(stretchType);
        });
    });

    closeBtn.addEventListener('click', stopStretchingExercise);
    nextBtn.addEventListener('click', nextStretch);
    stopBtn.addEventListener('click', stopStretchingExercise);
}

let stretchingInterval = null;
let currentStretchIndex = 0;
let stretchSequence = [];
let stretchCountdown = 0;

function startStretchingExercise(type) {
    const modal = document.getElementById('stretching-modal');
    modal.style.display = 'flex';

    if (type === 'neck') {
        stretchSequence = [
            'Tilt your head to the right, hold for 30 seconds',
            'Tilt your head to the left, hold for 30 seconds',
            'Look down, bringing chin to chest, hold for 30 seconds',
            'Look up gently, hold for 30 seconds'
        ];
    } else if (type === 'shoulder') {
        stretchSequence = [
            'Roll shoulders backward 10 times',
            'Roll shoulders forward 10 times',
            'Raise shoulders to ears, hold 5 seconds, release',
            'Pull shoulders back, squeeze shoulder blades'
        ];
    } else {
        stretchSequence = [
            'Reach arms overhead, stretch tall',
            'Bend forward, touch toes (or as far as comfortable)',
            'Twist torso to the right, hold',
            'Twist torso to the left, hold',
            'Side bend to the right',
            'Side bend to the left'
        ];
    }

    currentStretchIndex = 0;
    displayStretch();
}

function displayStretch() {
    const instruction = document.getElementById('stretch-instruction');
    const timer = document.getElementById('stretch-timer');
    const progressBar = document.getElementById('stretch-progress-bar');

    instruction.textContent = stretchSequence[currentStretchIndex];
    stretchCountdown = 30;
    timer.textContent = stretchCountdown + 's';

    const progress = ((currentStretchIndex + 1) / stretchSequence.length) * 100;
    progressBar.style.width = progress + '%';

    if (stretchingInterval) clearInterval(stretchingInterval);

    stretchingInterval = setInterval(() => {
        stretchCountdown--;
        timer.textContent = stretchCountdown + 's';

        if (stretchCountdown <= 0) {
            clearInterval(stretchingInterval);
            nextStretch();
        }
    }, 1000);
}

function nextStretch() {
    currentStretchIndex++;
    if (currentStretchIndex < stretchSequence.length) {
        displayStretch();
    } else {
        stopStretchingExercise();
        alert('Great job! Stretching session complete! 🎉');
    }
}

function stopStretchingExercise() {
    if (stretchingInterval) {
        clearInterval(stretchingInterval);
        stretchingInterval = null;
    }
    document.getElementById('stretching-modal').style.display = 'none';
}

// ========== MOOD TRACKER ==========
function setupMoodTracker() {
    const moodButtons = document.querySelectorAll('.mood-btn');
    const moodMessage = document.getElementById('mood-message');

    moodButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            // Remove selected class from all buttons
            moodButtons.forEach(b => b.classList.remove('selected'));
            
            // Add selected class to clicked button
            this.classList.add('selected');
            
            const mood = this.getAttribute('data-mood');
            
            // Show encouraging message
            const messages = {
                great: "That's wonderful! Keep up the positive energy! ✨",
                good: "Great to hear! It's nice to have good days. 😊",
                okay: "That's okay. Some days are just okay, and that's perfectly fine. 💙",
                bad: "I'm sorry you're not feeling great. Remember, it's okay to have tough days. 💚",
                terrible: "I hear you. If you need to talk, I'm here to listen. Please consider reaching out for support. ❤️"
            };
            
            moodMessage.textContent = messages[mood];
            moodMessage.classList.add('show');
            
            // Store mood (you can add backend call here if needed)
            saveMood(mood);
        });
    });
}

function saveMood(mood) {
    // Store mood in localStorage for now
    const today = new Date().toISOString().split('T')[0];
    const moodData = JSON.parse(localStorage.getItem('moodHistory') || '{}');
    moodData[today] = mood;
    localStorage.setItem('moodHistory', JSON.stringify(moodData));
}

// ========== UTILITY FUNCTIONS ==========
function generateSessionId() {
    return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
}

function formatTime(date) {
    const now = new Date();
    const diff = Math.floor((now - date) / 1000); // difference in seconds

    if (diff < 60) return 'Just now';
    if (diff < 3600) return Math.floor(diff / 60) + ' min ago';
    if (diff < 86400) return Math.floor(diff / 3600) + ' hr ago';
    
    return date.toLocaleTimeString('en-US', { 
        hour: 'numeric', 
        minute: '2-digit',
        hour12: true 
    });
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}