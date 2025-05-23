function toggleSection(header) {
            const section = header.parentNode;
            const content = section.querySelector('.section-content');
            const arrow = header.querySelector('.arrow');

            content.style.display = content.style.display === 'block' ? 'none' : 'block';
            arrow.classList.toggle('fa-chevron-down');
            arrow.classList.toggle('fa-chevron-up');
        }

        const textarea = document.getElementById("userInput");

        textarea.addEventListener("input", () => {
            textarea.style.height = "auto";
            textarea.style.height = (textarea.scrollHeight) + "px";
        });

        // Mobile navigation toggle
        const mobileMenuBtn = document.querySelector('.mobile-menu-btn');
        const navLinks = document.querySelector('.nav-links');

        if (mobileMenuBtn && navLinks) {
            // Function to toggle menu state
            function toggleMenu() {
                navLinks.classList.toggle('active');
                mobileMenuBtn.textContent = navLinks.classList.contains('active') ? '✕' : '☰';
            }

            // Toggle menu when menu button is clicked
            mobileMenuBtn.addEventListener('click', function(event) {
                event.stopPropagation(); // Prevent event from bubbling up
                toggleMenu();
            });

            // Close menu when clicking anywhere on the document
            document.addEventListener('click', function(event) {
                // Check if menu is open and the click is not on the menu or menu button
                if (navLinks.classList.contains('active') && 
                    !navLinks.contains(event.target) && 
                    event.target !== mobileMenuBtn) {
                    toggleMenu();
                }
            });

            // Handle touch events for mobile devices
            document.addEventListener('touchstart', function(event) {
                // Check if menu is open and the touch is not on the menu or menu button
                if (navLinks.classList.contains('active') && 
                    !navLinks.contains(event.target) && 
                    event.target !== mobileMenuBtn) {
                    toggleMenu();
                }
            });

            // Prevent clicks on nav links from closing the menu
            navLinks.addEventListener('click', function(event) {
                event.stopPropagation();
            });

            // Also handle touch events on nav links
            navLinks.addEventListener('touchstart', function(event) {
                event.stopPropagation();
            });
        }


        // Toggle dark/light mode
        document.querySelectorAll('.mode-toggle').forEach(button => {
        button.addEventListener('click', function() {
            const icon = this.querySelector('i');
            const body = document.body;
            
            // Toggle between dark and light mode
            if (icon.classList.contains('fa-moon')) {
            // Switch to dark mode
            icon.classList.remove('fa-moon');
            icon.classList.add('fa-sun');
            body.style.backgroundColor = '#121212';
            body.style.color = '#000000';
            document.querySelectorAll('.content-section').forEach(section => {
                section.style.backgroundColor = '#16213e';
                section.style.boxShadow = '0 1px 3px rgba(255,255,255,0.1)';
            });
            } else {
            // Switch to light mode
            icon.classList.remove('fa-sun');
            icon.classList.add('fa-moon');
            body.style.backgroundColor = '#f5f5f5';
            body.style.color = '#333';
            document.querySelectorAll('.content-section').forEach(section => {
                section.style.backgroundColor = 'white';
                section.style.boxShadow = '0 1px 3px rgba(0,0,0,0.1)';
            });
            }
        });
        });
        
        function copyResponse(btn) {
            const responseText = btn.closest('.assistant-message').textContent;
            navigator.clipboard.writeText(responseText).then(() => {
                btn.innerHTML = "copied!";
                setTimeout(() => {
                btn.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16"
                    fill="currentColor" class="icon-copy" viewBox="0 0 16 16">
                    <path d="M10 1H2a1 1 0 0 0-1 1v10h1V2a.5.5 0 0 1 .5-.5H10V1z"/>
                    <path d="M14 4a1 1 0 0 0-1-1H5a1 1 0 0 0-1 1v10a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1V4zm-1 0v10H5V4h8z"/>
                </svg>`;
                }, 1500);
            });
        }

        // AfroZoomer AI Assistant Script       
        document.addEventListener('DOMContentLoaded', function() {
            const chatForm = document.getElementById('chatForm');
            const userInput = document.getElementById('userInput');
            const chatMessages = document.getElementById('chatMessages');
            const chatMessage = document.querySelector('.chat-messages');
            const observer = new MutationObserver(() => {
                if (chatMessage.children.length > 0) {
                    chatMessage.style.overflowY = 'auto';
                } else {
                    chatMessage.style.overflowY = 'hidden';
                }
            });
            observer.observe(chatMessage, { childList: true });
            
            chatForm.addEventListener('submit', function(e) {
                e.preventDefault();
                
                const userMessage = userInput.value.trim();
                if (userMessage === '') return;
                
                // Add user message to the chat
                addMessage('user', userMessage);
                
                // Show thinking indicator
                const thinkingId = addThinking();
                
                // Clear input
                userInput.value = '';
                
                // Send message to the server
                fetch('/ask', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded',
                    },
                    body: 'user_input=' + encodeURIComponent(userMessage)
                })
                .then(response => response.json())
                .then(data => {
                    // const now = new Date();
                    // document.getElementById("assistant-message").textContent = data.response;
                    // document.getElementById("response-timestamp").textContent = 
                    //     `Answered on ${now.toLocaleDateString()} at ${now.toLocaleTimeString()}`;
                    // Remove thinking indicator
                    removeThinking(thinkingId);
                    
                    // Process the response to convert markdown-like syntax
                    const formattedResponse = formatResponse(data.response);
                    
                    // Add assistant response
                    addMessage('assistant', formattedResponse);
                    
                    // Scroll to bottom
                    scrollToBottom();
                })
                .catch(error => {
                    console.error('Error:', error);
                    removeThinking(thinkingId);
                    addMessage('assistant', 'Sorry, I encountered an error. Please try again.');
                });
            });

            if ('serviceWorker' in navigator) {
                navigator.serviceWorker.register('/static/service-worker.js')
                    .then(reg => console.log('✅ Service Worker registered'))
                    .catch(err => console.error('❌ Service Worker failed:', err));
            }
            
            window.dataLayer = window.dataLayer || [];
            function gtag(){ dataLayer.push(arguments); }
            gtag('js', new Date());
            gtag('config', 'G-VP6344NLKP');

            document.getElementById("sendBtn").addEventListener("click", function() {
                gtag('event', 'click', {
                    'event_category': 'Button',
                    'event_label': 'Send Message',
                    'value': 1
                });
            });


            function addMessage(sender, content) {
                const messageDiv = document.createElement('div');
                messageDiv.className = `message ${sender}-message`;

                const avatar = document.createElement('div');
                avatar.className = `avatar ${sender}-avatar`;
                avatar.innerHTML = `<span>${sender === 'user' ? 'U' : 'A'}</span>`;

                const messageContent = document.createElement('div');
                messageContent.className = `message-content ${sender === 'assistant' ? 'assistant-content' : ''}`;

                if (sender === 'assistant') {
                    messageContent.innerHTML = content;
                    messageDiv.appendChild(avatar);          // Avatar on left
                    messageDiv.appendChild(messageContent);
                } else {
                    messageContent.textContent = content;
                    messageDiv.appendChild(messageContent);  // Message first
                    messageDiv.appendChild(avatar);          // Avatar on right
                }

                chatMessages.appendChild(messageDiv);
                scrollToBottom();
            }

            
            function addThinking() {
                const thinkingId = 'thinking-' + Date.now();
                const thinkingDiv = document.createElement('div');
                thinkingDiv.className = 'message assistant-message';
                thinkingDiv.id = thinkingId;
                
                const avatar = document.createElement('div');
                avatar.className = 'avatar assistant-avatar';
                avatar.innerHTML = '<span>A</span>';
                
                const messageContent = document.createElement('div');
                messageContent.className = 'message-content';
                messageContent.innerHTML = '<div class="thinking"><div class="dot-typing"></div></div>';
                
                thinkingDiv.appendChild(avatar);
                thinkingDiv.appendChild(messageContent);
                
                chatMessages.appendChild(thinkingDiv);
                scrollToBottom();
                
                return thinkingId;
            }
            
            function removeThinking(thinkingId) {
                const thinkingDiv = document.getElementById(thinkingId);
                if (thinkingDiv) {
                    thinkingDiv.remove();
                }
            }
            
            function scrollToBottom() {
                chatMessages.scrollTop = chatMessages.scrollHeight;
            }
            
            function formatResponse(text) {
                if (!text) return '';
                
                // Process markdown-like formatting
                let formatted = text
                    // Handle paragraphs - ensure double newlines become proper paragraphs
                    .replace(/\n\s*\n/g, '</p><p>')
                    
                    // Handle bold text with ** or __
                    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                    .replace(/__(.*?)__/g, '<strong>$1</strong>')
                    
                    // Handle italic text with * or _
                    .replace(/\*(.*?)\*/g, '<em>$1</em>')
                    .replace(/_(.*?)_/g, '<em>$1</em>')
                    
                    // Handle headings (# Heading)
                    .replace(/^# (.*?)$/gm, '<h1>$1</h1>')
                    .replace(/^## (.*?)$/gm, '<h2>$1</h2>')
                    .replace(/^### (.*?)$/gm, '<h3>$1</h3>')
                    
                    // Handle lists
                    .replace(/^\s*\* (.*?)$/gm, '<li>$1</li>')
                    .replace(/^\s*- (.*?)$/gm, '<li>$1</li>')
                    .replace(/^\s*\d+\. (.*?)$/gm, '<li>$1</li>')
                    
                    // Handle code blocks
                    .replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>')
                    
                    // Handle inline code
                    .replace(/`(.*?)`/g, '<code>$1</code>')
                    
                    // Handle blockquotes
                    .replace(/^\> (.*?)$/gm, '<blockquote>$1</blockquote>')
                    
                    // Handle "thinking" blocks
                    .replace(/\[thinking\]([\s\S]*?)\[\/thinking\]/g, '<div class="thinking">$1</div>');
                
                // Wrap in paragraph tags if not already wrapped
                if (!formatted.startsWith('<')) {
                    formatted = '<p>' + formatted;
                }
                if (!formatted.endsWith('>')) {
                    formatted = formatted + '</p>';
                }
                
                return formatted;
            }
            
            // Initial focus on input
            userInput.focus();
        });