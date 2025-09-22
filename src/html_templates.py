css = '''
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

    :root {
        --cor-fundo: #0E1117;
        --cor-fundo-msg-bot: #262730;
        --cor-fundo-msg-user: #1E293B;
        --cor-texto: #FAFAFA;
        --cor-destaque: #3B82F6;
        --fonte-principal: 'Inter', sans-serif;
    }

    body {
        font-family: var(--fonte-principal);
    }

    .chat-message {
        padding: 1.5rem;
        border-radius: 0.75rem;
        margin-bottom: 1rem;
        display: flex;
        align-items: flex-start;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        transition: all 0.2s ease;
    }

    .chat-message:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
    }

    .chat-message.user {
        background-color: var(--cor-fundo-msg-user);
    }

    .chat-message.bot {
        background-color: var(--cor-fundo-msg-bot);
    }

    .chat-message .avatar {
      width: 60px;
      flex-shrink: 0;
      margin-right: 1rem;
    }

    .chat-message .avatar img {
      width: 60px;
      height: 60px;
      border-radius: 50%;
      object-fit: cover;
      border: 2px solid var(--cor-destaque);
    }

    .chat-message .message-container {
      width: 100%;
      display: flex;
      flex-direction: column;
    }
    
    .chat-message .message {
      width: 100%;
      padding: 0;
      color: var(--cor-texto);
      font-size: 1rem;
      line-height: 1.6;
    }
    
    .chat-message .message-footer {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-top: 1rem;
        font-size: 0.75rem;
        color: #9CA3AF;
    }

    .copy-button {
        background: none;
        border: none;
        color: #9CA3AF;
        cursor: pointer;
        font-size: 0.9rem;
        transition: color 0.2s ease;
    }

    .copy-button:hover {
        color: var(--cor-texto);
    }
</style>
'''

bot_template = '''
<div class="chat-message bot">
    <div class="avatar">
        <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/e/ef/ChatGPT-Logo.svg/1200px-ChatGPT-Logo.svg.png">
    </div>
    <div class="message-container">
        <div class="message" id="bot-msg-{{MSG_ID}}">{{MSG}}</div>
        <div class="message-footer">
            <span>{{TIMESTAMP}}</span>
            <button class="copy-button" onclick="navigator.clipboard.writeText(document.getElementById('bot-msg-{{MSG_ID}}').innerText)">
                &#x2398; </button>
        </div>
    </div>
</div>
'''

user_template = '''
<div class="chat-message user">
    <div class="avatar">
        <img src="https://www.transparentpng.com/download/user/gray-user-profile-icon-png-fP8Q1P.png">
    </div>    
    <div class="message-container">
        <div class="message" id="user-msg-{{MSG_ID}}">{{MSG}}</div>
        <div class="message-footer">
            <span>{{TIMESTAMP}}</span>
            <button class="copy-button" onclick="navigator.clipboard.writeText(document.getElementById('user-msg-{{MSG_ID}}').innerText)">
                &#x2398; </button>
        </div>
    </div>    
</div>
'''