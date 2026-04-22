<div class="chat-container">
        <!-- Header -->
        <div class="chat-header">
            <div class="header-info">
                <div class="ai-avatar">
                    <i class="fas fa-robot"></i>
                </div>
                <div class="header-text">
                    <h1>Retail Assistant</h1>
                    <p>Multi-Agent System powered by LangGraph</p>
                </div>
            </div>

            <button id="btn-close-chatbot">
                <i class="fa-solid fa-xmark"></i>
            </button>
        </div>

        <!-- Messages Container -->
        <div class="messages-container" id="messagesContainer">
            <div class="welcome-message">
                <h2>Welcome to Retail Assistant</h2>
                <p>I'm powered by a sophisticated multi-agent system that can help you with various tasks. How can I assist you today?</p>

                <div class="suggestions">
                    <div class="suggestion-chip" onclick="sendSuggestion('What can you do')">
                        What can you do?
                    </div>
                    <div class="suggestion-chip" onclick="sendSuggestion('How does your multi-agent system work?')">
                        How do you work?
                    </div>
                    <div class="suggestion-chip" onclick="sendSuggestion('Can you give me a summary of the sales performance for current month')">
                        Analyze sales data
                    </div>
                    <div class="suggestion-chip" onclick="sendSuggestion('What should we restock for current month')">
                        Generate restock plan
                    </div>
                </div>
            </div>

            <!-- Messages will be inserted here dynamically -->
            <div id="messagesArea"></div>

            <!-- Typing Indicator -->
            <div class="typing-indicator" id="typingIndicator" style="display: none;">
                <div class="typing-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
                <span>AI is thinking...</span>
            </div>
        </div>

        <!-- Input Container -->
        <div class="input-container">
            <div class="input-wrapper">
                <textarea
                    class="message-input"
                    id="messageInput"
                    placeholder="Type your message here..."
                    rows="1"
                    onkeydown="handleKeyDown(event)"
                    oninput="autoResize(this)"
                    onblur="autoResize(this)"
                ></textarea>
                <div class="message-buttons">
                    <button class="send-button" id="sendButton" onclick="sendMessage()" >
                        <i class="fas fa-paper-plane"></i>
                    </button>
                    <button class="cancel-button" id="cancelButton" onclick="cancelStream()" disabled>
                        <i class="fas fa-stop"></i>
                    </button>

                </div>

            </div>
        </div>
</div>
