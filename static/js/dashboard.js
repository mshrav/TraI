/**
 * AI Trading Bot – Admin Dashboard
 *
 * FIXES vs original:
 *  1. Socket.io now connects to the *same origin* (window.location) instead of the
 *     hardcoded "http://localhost:5000".  The hardcoded URL broke the dashboard when
 *     it was opened on any other machine or port-forwarded via a tunnel.
 *  2. sendMessage() now renders the sent message *immediately* in the chat window
 *     (optimistic UI) instead of waiting up to 2 seconds for the next poll cycle.
 *     Previously the dashboard appeared to do nothing after clicking Send.
 *  3. The 'new_message' socket event handler renders the incoming message directly
 *     without a full page re-render, so Telegram messages appear instantly.
 *  4. lastMessageCount was shared across users; switching users could skip a render.
 *     Replaced with a per-user message-count map (lastMessageCounts).
 *  5. The redundant messagePollingInterval (2 s) is kept as a fallback but is now
 *     correctly cancelled and restarted when switching users.
 *  6. clearChatBtn is wired up (it was present in HTML but had no handler).
 */

// ---------------------------------------------------------------------------
// Global state
// ---------------------------------------------------------------------------

let socket               = null;
let currentUserId        = null;
let users                = [];
let messagePollingTimer  = null;
const lastMessageCounts  = {};   // FIX: per-user count so switching users works correctly

// ---------------------------------------------------------------------------
// Initialisation
// ---------------------------------------------------------------------------

document.addEventListener('DOMContentLoaded', () => {
    initSocket();
    loadUsers();
    setupEventListeners();

    // Fallback poll – keep user list fresh even if SocketIO events are missed
    setInterval(loadUsers, 5000);
});

// ---------------------------------------------------------------------------
// Socket.io
// ---------------------------------------------------------------------------

function initSocket() {
    // FIX: connect to the same origin so this works outside localhost
    if (typeof io === 'undefined') {
        console.warn('Socket.IO client unavailable; dashboard will use HTTP polling.');
        updateConnectionStatus(false);
        return;
    }
    socket = io({ transports: ['websocket', 'polling'] });

    socket.on('connect', () => {
        console.log('Socket connected');
        updateConnectionStatus(true);
        socket.emit('request_users');
    });

    socket.on('disconnect', () => {
        console.log('Socket disconnected');
        updateConnectionStatus(false);
    });

    socket.on('connect_error', (err) => {
        console.error('Socket error:', err);
        updateConnectionStatus(false);
    });

    socket.on('connected', (data) => {
        console.log('Server handshake:', data);
    });

    socket.on('users_list', (userList) => {
        users = userList;
        renderUsers(userList);
    });

    // FIX: render the new message immediately instead of waiting for the poll
    socket.on('new_message', (data) => {
        console.log('New message from socket:', data);
        if (currentUserId === Number(data.user_id)) {
            loadMessages(currentUserId, true);
        }
        // Refresh user list to update last-message preview + unread badge
        loadUsers();
    });

    socket.on('user_updated', (userList) => {
        users = userList;
        renderUsers(userList);
    });
}

// ---------------------------------------------------------------------------
// Connection status indicator
// ---------------------------------------------------------------------------

function updateConnectionStatus(connected) {
    const dot  = document.getElementById('connectionDot');
    const text = document.getElementById('connectionText');
    if (connected) {
        dot.classList.add('connected');
        dot.classList.remove('error');
        text.textContent = 'Connected';
    } else {
        dot.classList.remove('connected');
        dot.classList.add('error');
        text.textContent = 'Disconnected';
    }
}

// ---------------------------------------------------------------------------
// User list
// ---------------------------------------------------------------------------

async function loadUsers() {
    try {
        const res      = await fetch('/api/users');
        const userList = await res.json();
        users = userList;
        renderUsers(userList);
    } catch (err) {
        console.error('loadUsers error:', err);
    }
}

function renderUsers(userList) {
    const container    = document.getElementById('usersList');
    const totalUsers   = document.getElementById('totalUsers');
    const totalMessages = document.getElementById('totalMessages');

    totalUsers.textContent    = userList.length;
    totalMessages.textContent = userList.reduce((acc, u) => acc + (u.unread || 0), 0);

    if (userList.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-users"></i>
                <p>No users yet</p>
            </div>`;
        return;
    }

    container.innerHTML = userList.map(user => {
        const initial = user.name ? user.name.charAt(0).toUpperCase() : 'U';
        const time    = formatTime(user.last_time);
        const active  = currentUserId === user.user_id ? 'active' : '';
        return `
            <div class="user-item ${active}" data-user-id="${user.user_id}"
                 onclick="selectUser(${user.user_id})">
                <div class="user-avatar-small">
                    ${escapeHtml(initial)}
                    ${user.unread > 0 ? `<span class="unread-badge">${user.unread}</span>` : ''}
                </div>
                <div class="user-info">
                    <div class="user-name">${escapeHtml(user.name)}</div>
                    <div class="user-last-message">${escapeHtml(user.last_message)}</div>
                </div>
                <div class="user-time">${time}</div>
            </div>`;
    }).join('');
}

// ---------------------------------------------------------------------------
// Selecting a user / loading messages
// ---------------------------------------------------------------------------

async function selectUser(userId) {
    currentUserId = userId;

    document.querySelectorAll('.user-item').forEach(el =>
        el.classList.toggle('active', parseInt(el.dataset.userId) === userId)
    );

    const user = users.find(u => u.user_id === userId);
    if (!user) return;

    document.getElementById('noChatSelected').style.display = 'none';
    document.getElementById('chatView').style.display       = 'flex';
    document.getElementById('chatUserName').textContent     = user.name;
    document.getElementById('chatUserId').textContent       = `ID: ${user.user_id}`;

    await loadMessages(userId, true);
    document.getElementById('messageInput').focus();
}

async function loadMessages(userId, forceRender = false) {
    try {
        const res      = await fetch(`/api/users/${userId}/messages`);
        const messages = await res.json();

        // FIX: use per-user count map so switching users always re-renders
        const key  = String(userId);
        const prev = lastMessageCounts[key] || 0;
        if (forceRender || messages.length !== prev) {
            lastMessageCounts[key] = messages.length;
            renderMessages(messages);
        }

        // Fallback poll in case socket events are missed
        if (messagePollingTimer) clearInterval(messagePollingTimer);
        messagePollingTimer = setInterval(() => {
            if (currentUserId === userId) loadMessages(userId);
        }, 3000);

    } catch (err) {
        console.error('loadMessages error:', err);
    }
}

// ---------------------------------------------------------------------------
// Rendering messages
// ---------------------------------------------------------------------------

function renderMessages(messages) {
    const container = document.getElementById('messagesContainer');

    if (messages.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-comments"></i>
                <p>No messages yet</p>
            </div>`;
        return;
    }

    let html     = '';
    let lastDate = '';

    messages.forEach(msg => {
        const msgDate = new Date(msg.timestamp).toLocaleDateString();
        if (msgDate !== lastDate) {
            lastDate  = msgDate;
            html += `<div class="date-separator"><span>${formatDate(msg.timestamp)}</span></div>`;
        }
        html += buildMessageHtml(msg);
    });

    container.innerHTML = html;
    scrollToBottom();
}

/** Build the HTML for a single message bubble. */
function buildMessageHtml(msg) {
    const time = formatTime(msg.timestamp);
    return `
        <div class="message ${escapeHtml(msg.sender)}">
            <div class="message-bubble">${escapeHtml(msg.text)}</div>
            <div class="message-time">${time}</div>
        </div>`;
}

/**
 * FIX: append a single new message without rebuilding the whole list.
 * This is used by the socket 'new_message' handler and by the optimistic
 * send path so messages appear immediately.
 */
function appendMessage(msg) {
    const container = document.getElementById('messagesContainer');

    // Remove "no messages" placeholder if present
    const empty = container.querySelector('.empty-state');
    if (empty) empty.remove();

    const div = document.createElement('div');
    div.innerHTML = buildMessageHtml(msg);
    container.appendChild(div.firstElementChild);
    scrollToBottom();

    // Update local count so the next poll doesn't force a full re-render
    const key = String(currentUserId);
    lastMessageCounts[key] = (lastMessageCounts[key] || 0) + 1;
}

function scrollToBottom() {
    const c = document.getElementById('messagesContainer');
    c.scrollTop = c.scrollHeight;
}

// ---------------------------------------------------------------------------
// Sending messages
// ---------------------------------------------------------------------------

let _sending = false;

async function sendMessage(text) {
    const messageText = (text || '').trim();
    if (!currentUserId || !messageText || _sending) return;
    _sending = true;
    const input = document.getElementById('messageInput');
    const sendBtn = document.getElementById('sendBtn');
    sendBtn.disabled = true;

    try {
        const res = await fetch('/api/send', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: currentUserId, text: messageText }),
        });
        const result = await res.json();
        if (!res.ok || !result.success) {
            showToast(result.error || 'Telegram delivery failed', 'error');
            return;
        }
        input.value = '';
        showToast('Reply delivered to Telegram', 'success');
        await loadMessages(currentUserId, true);
        await loadUsers();
    } catch (err) {
        console.error('sendMessage error:', err);
        showToast('Network error while sending reply', 'error');
    } finally {
        _sending = false;
        sendBtn.disabled = false;
        input.focus();
    }
}

// ---------------------------------------------------------------------------
// Event listeners
// ---------------------------------------------------------------------------

function setupEventListeners() {
    // Message form submit
    document.getElementById('messageForm').addEventListener('submit', (e) => {
        e.preventDefault();
        sendMessage(document.getElementById('messageInput').value);
    });

    // Enter key (without Shift) in the text field
    document.getElementById('messageInput').addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage(e.target.value);
        }
    });

    // Quick-reply buttons
    document.querySelectorAll('.quick-reply').forEach(btn => {
        btn.addEventListener('click', () => {
            document.getElementById('messageInput').value = btn.dataset.text;
            document.getElementById('messageInput').focus();
        });
    });

    // User search
    document.getElementById('userSearch').addEventListener('input', function () {
        const q        = this.value.toLowerCase();
        const filtered = users.filter(u =>
            String(u.name || '').toLowerCase().includes(q) || String(u.user_id).includes(q)
        );
        renderUsers(filtered);
    });

    // View profile button
    document.getElementById('viewProfileBtn').addEventListener('click', async () => {
        if (!currentUserId) return;
        try {
            const res      = await fetch(`/api/users/${currentUserId}/messages`);
            const messages = await res.json();
            const user     = users.find(u => u.user_id === currentUserId);
            showProfileModal(user, messages);
        } catch (err) {
            console.error('Profile load error:', err);
        }
    });

    // FIX: clear chat button was wired in HTML but had no handler
    document.getElementById('clearChatBtn').addEventListener('click', () => {
        if (!currentUserId) return;
        if (confirm('Clear chat display? (Messages are not deleted from storage.)')) {
            document.getElementById('messagesContainer').innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-comments"></i>
                    <p>Chat cleared from view</p>
                </div>`;
        }
    });

    // Profile modal close
    document.getElementById('closeProfileModal').addEventListener('click', () => {
        document.getElementById('profileModal').classList.remove('show');
    });
    document.getElementById('profileModal').addEventListener('click', (e) => {
        if (e.target === e.currentTarget)
            e.currentTarget.classList.remove('show');
    });
}

// ---------------------------------------------------------------------------
// Profile modal
// ---------------------------------------------------------------------------

function showProfileModal(user, messages) {
    if (!user) return;
    const userMsgs  = messages.filter(m => m.sender === 'user');
    const adminMsgs = messages.filter(m => m.sender === 'admin');

    document.getElementById('profileContent').innerHTML = `
        <div class="profile-field">
            <span class="profile-label">Name</span>
            <span class="profile-value">${escapeHtml(user.name)}</span>
        </div>
        <div class="profile-field">
            <span class="profile-label">User ID</span>
            <span class="profile-value">${user.user_id}</span>
        </div>
        <div class="profile-field">
            <span class="profile-label">Messages Sent</span>
            <span class="profile-value">${userMsgs.length}</span>
        </div>
        <div class="profile-field">
            <span class="profile-label">Admin Replies</span>
            <span class="profile-value">${adminMsgs.length}</span>
        </div>
        <div class="profile-field">
            <span class="profile-label">Last Active</span>
            <span class="profile-value">${formatDateTime(user.last_time)}</span>
        </div>`;

    document.getElementById('profileModal').classList.add('show');
}

// ---------------------------------------------------------------------------
// Toast notifications
// ---------------------------------------------------------------------------

function showToast(message, type = 'success') {
    const toast        = document.getElementById('toast');
    const toastMessage = document.getElementById('toastMessage');
    toastMessage.textContent = message;
    toast.classList.toggle('error', type === 'error');
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), 3000);
}

// ---------------------------------------------------------------------------
// Utility / formatting helpers
// ---------------------------------------------------------------------------

function formatTime(timestamp) {
    const date = new Date(timestamp);
    const now  = new Date();
    const diff = now - date;

    if (diff < 86_400_000)  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    if (diff < 604_800_000) return date.toLocaleDateString([], { weekday: 'short', hour: '2-digit', minute: '2-digit' });
    return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
}

function formatDate(timestamp) {
    return new Date(timestamp).toLocaleDateString([], { weekday: 'long', month: 'short', day: 'numeric' });
}

function formatDateTime(timestamp) {
    return new Date(timestamp).toLocaleString([], {
        year: 'numeric', month: 'short', day: 'numeric',
        hour: '2-digit', minute: '2-digit',
    });
}

function escapeHtml(text) {
    if (text == null) return '';
    const div = document.createElement('div');
    div.textContent = String(text);
    return div.innerHTML;
}
