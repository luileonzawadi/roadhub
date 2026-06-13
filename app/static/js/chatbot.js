/* ============================================================
   ROADHUB AI ASSISTANT CHAT WIDGET
   ============================================================ */

(function() {
  // Prevent duplicate instantiation
  if (window.__RoadhubChatbotLoaded) return;
  window.__RoadhubChatbotLoaded = true;

  // Initialize chatbot HTML container
  document.addEventListener('DOMContentLoaded', () => {
    // 1. Inject Chatbot Container & Toggle Button
    const chatContainer = document.createElement('div');
    chatContainer.id = 'roadhub-chatbot-root';
    chatContainer.innerHTML = `
      <!-- Launcher Button -->
      <button class="roadhub-chat-launcher" id="roadhubChatLauncher" aria-label="Open support chat">
        <svg viewBox="0 0 24 24"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
      </button>

      <!-- Chat Window Card -->
      <div class="roadhub-chat-widget" id="roadhubChatWidget">
        <div class="roadhub-chat-header">
          <div class="roadhub-chat-header-info">
            <div class="roadhub-chat-avatar">RH</div>
            <div class="roadhub-chat-title">
              <h3>Roadhub Assistant</h3>
              <span><span class="online-indicator"></span>Active Advisor</span>
            </div>
          </div>
          <button class="roadhub-chat-close" id="roadhubChatClose" aria-label="Close chat">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>

        <div class="roadhub-chat-body" id="roadhubChatBody">
          <!-- Welcome Message -->
          <div class="chat-message bot">
            <div class="chat-bubble">
              Hello! 👋 Welcome to Roadhub. I'm your interactive engineering study assistant. Ask me anything about our HVAC, Electrical, Civil, or Architecture courses, certifications, pricing, or mentorship!
            </div>
            <span class="chat-time">Just now</span>
          </div>
        </div>

        <div class="roadhub-chat-footer">
          <!-- Suggestion Chips -->
          <div class="roadhub-chat-suggestions" id="roadhubChatSuggestions">
            <button class="suggestion-btn" data-query="HVAC & Mechanical">Mechanical Paths</button>
            <button class="suggestion-btn" data-query="Electrical Power">Electrical Paths</button>
            <button class="suggestion-btn" data-query="Autodesk certification">Autodesk Certs</button>
            <button class="suggestion-btn" data-query="Pricing details">Pricing & Fees</button>
          </div>

          <!-- Input Controls -->
          <div class="roadhub-chat-input-wrapper">
            <input type="text" class="roadhub-chat-input" id="roadhubChatInput" placeholder="Type your question..." aria-label="Chat input field" />
            <button class="roadhub-chat-send" id="roadhubChatSend" aria-label="Send message">
              <svg viewBox="0 0 24 24"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
            </button>
          </div>
        </div>
      </div>
    `;

    document.body.appendChild(chatContainer);

    // 2. Select Elements
    const launcher = document.getElementById('roadhubChatLauncher');
    const widget = document.getElementById('roadhubChatWidget');
    const closeBtn = document.getElementById('roadhubChatClose');
    const chatBody = document.getElementById('roadhubChatBody');
    const chatInput = document.getElementById('roadhubChatInput');
    const sendBtn = document.getElementById('roadhubChatSend');
    const suggestions = document.getElementById('roadhubChatSuggestions');

    // Load Chat History from sessionStorage if present
    const loadChatHistory = () => {
      const history = sessionStorage.getItem('roadhub_chat_history');
      if (history) {
        chatBody.innerHTML = history;
        scrollToBottom();
      }
    };

    const saveChatHistory = () => {
      sessionStorage.setItem('roadhub_chat_history', chatBody.innerHTML);
    };

    // Helper to scroll body
    const scrollToBottom = () => {
      chatBody.scrollTop = chatBody.scrollHeight;
    };

    // Open/Close toggle
    const toggleChat = () => {
      const isActive = widget.classList.toggle('active');
      launcher.classList.toggle('active', isActive);
      if (isActive) {
        setTimeout(() => chatInput.focus(), 150);
        scrollToBottom();
      }
    };

    launcher.addEventListener('click', toggleChat);
    closeBtn.addEventListener('click', toggleChat);

    // Add Message Bubble
    const appendMessage = (text, isUser = false) => {
      const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      const msgDiv = document.createElement('div');
      msgDiv.className = `chat-message ${isUser ? 'user' : 'bot'}`;
      msgDiv.innerHTML = `
        <div class="chat-bubble">${text}</div>
        <span class="chat-time">${timeStr}</span>
      `;
      chatBody.appendChild(msgDiv);
      scrollToBottom();
      saveChatHistory();
    };

    // Show/Hide Typing Indicator
    let typingIndicator = null;
    const showTypingIndicator = () => {
      if (typingIndicator) return;
      typingIndicator = document.createElement('div');
      typingIndicator.className = 'typing-indicator';
      typingIndicator.innerHTML = '<span></span><span></span><span></span>';
      chatBody.appendChild(typingIndicator);
      scrollToBottom();
    };

    const removeTypingIndicator = () => {
      if (typingIndicator) {
        typingIndicator.remove();
        typingIndicator = null;
      }
    };

    // Send Message Logic
    const handleSend = async (messageText) => {
      const query = messageText || chatInput.value.trim();
      if (!query) return;

      if (!messageText) chatInput.value = '';

      // Add user message
      appendMessage(query, true);

      // Show typing indicator
      showTypingIndicator();

      try {
        const response = await fetch('/api/chat', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ message: query })
        });

        const data = await response.json();
        removeTypingIndicator();

        if (response.ok && data.response) {
          appendMessage(data.response, false);
        } else {
          appendMessage("Sorry, I encountered an issue. Please try again in a moment.", false);
        }
      } catch (err) {
        removeTypingIndicator();
        appendMessage("Network error. Please check your internet connection.", false);
        console.error("Chatbot Error:", err);
      }
    };

    // Event Listeners for inputs
    sendBtn.addEventListener('click', () => handleSend());
    chatInput.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') handleSend();
    });

    // Suggestion chips handler
    suggestions.addEventListener('click', (e) => {
      const btn = e.target.closest('.suggestion-btn');
      if (btn) {
        const query = btn.getAttribute('data-query');
        handleSend(query);
      }
    });

    // Initial Load
    loadChatHistory();
  });
})();
