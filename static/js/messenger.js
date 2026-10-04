/*
 * ==========================================================
 * CONFIG & API
 * ==========================================================
 */
const API = {
    userChats: "/api/v1/info/user_chats",
    createGroup: "/api/v1/chat/create_group_chat",
    findUsers: "/api/v1/info/find_user",
    createPrivate: "/api/v1/chat/create_private_chat",
    chatHistory: "/api/v1/info/chat_history"
};

/*
 * ==========================================================
 * STATE
 * ==========================================================
 */
let chats = [];
let selectedChatId = null;
let searchTimeout = null;
let currentUserId = null; // из JWT (sub) — для разделения "своих"/"чужих" сообщений

/*
 * ==========================================================
 * DOM ELEMENTS
 * ==========================================================
 */
const messenger = document.getElementById("messenger");
const chatList = document.getElementById("chat-list");
const welcome = document.getElementById("welcome");
const chatWindow = document.getElementById("chat-window");
const chatAvatar = document.getElementById("chat-avatar");
const chatHeaderName = document.getElementById("chat-header-name");
const chatHeaderType = document.getElementById("chat-header-type");
const messages = document.getElementById("messages");
const userSearch = document.getElementById("user-search");
const searchResults = document.getElementById("search-results");
const createGroupForm = document.getElementById("create-group-form");
const createGroupSubmit = document.getElementById("create-group-submit");
const groupError = document.getElementById("group-error");
const logoutButton = document.getElementById("logout-btn");
const messageForm = document.getElementById("message-form");
const messageInput = document.getElementById("message-input");
const messageSendBtn = document.getElementById("message-send-btn");

/*
 * ==========================================================
 * AUTH & FETCH HELPERS
 * ==========================================================
 */
function getToken() {
    return localStorage.getItem("access_token");
}

function authHeaders() {
    const token = getToken();
    return token ? { "Authorization": `Bearer ${token}` } : {};
}

function redirectToLogin() {
    localStorage.removeItem("access_token");
    window.location.href = "/api/v1/auth/"; // Или "/login", в зависимости от вашего роутинга
}

async function apiFetch(url, options = {}) {
    const headers = {
        ...authHeaders(),
        ...(options.headers || {})
    };

    const response = await fetch(url, { ...options, headers });

    if (response.status === 401) {
        redirectToLogin();
        throw new Error("Авторизация истекла");
    }

    return response;
}

/*
 * ==========================================================
 * CHAT MANAGEMENT
 * ==========================================================
 */
async function loadChats() {
    chatList.innerHTML = `<div class="chat-empty">Загрузка чатов...</div>`;

    try {
        const response = await apiFetch(API.userChats, { method: "GET" });
        if (!response.ok) throw new Error("Не удалось получить список чатов");

        const data = await response.json();
        chats = normalizeChats(data.chats);
        renderChats();
    } catch (error) {
        console.error(error);
        chatList.innerHTML = `
            <div class="chat-empty">
                Не удалось загрузить чаты.<br>
                <button class="btn btn-sm btn-outline-primary mt-2" onclick="loadChats()">Повторить</button>
            </div>`;
    }
}

function normalizeChats(data) {
    if (!data) return [];

    if (Array.isArray(data)) {
        return data.map(chat => ({
            id: String(chat.chat_id),
            type: chat.chat_type,
            name: chat.chat_name
        }));
    }

    if (typeof data === "object" && !Array.isArray(data)) {
        return Object.entries(data).map(([chatId, chatName]) => ({
            id: chatId,
            type: "unknown",
            name: chatName
        }));
    }

    return [];
}

function renderChats() {
    chatList.innerHTML = "";

    if (chats.length === 0) {
        chatList.innerHTML = `<div class="chat-empty">У вас пока нет чатов.</div>`;
        return;
    }

    chats.forEach(chat => {
        const element = document.createElement("div");
        element.className = "chat-item";
        if (String(chat.id) === String(selectedChatId)) {
            element.classList.add("active");
        }

        element.innerHTML = `
            <div class="avatar">${escapeHtml(getInitials(chat.name))}</div>
            <div class="chat-info">
                <div class="chat-name">${escapeHtml(chat.name)}</div>
                <div class="chat-type">${escapeHtml(getChatTypeText(chat.type))}</div>
            </div>`;

        element.addEventListener("click", () => openChat(chat));
        chatList.appendChild(element);
    });
}

async function openChat(chat) {
    selectedChatId = chat.id;
    welcome.style.display = "none";
    chatWindow.style.display = "flex";

    chatAvatar.textContent = getInitials(chat.name);
    chatHeaderName.textContent = chat.name;
    chatHeaderType.textContent = getChatTypeText(chat.type);

    setComposerEnabled(false);
    messages.innerHTML = `<div class="messages-empty">Загрузка сообщений...</div>`;

    // 1. Подтягиваем историю через REST
    try {
        const response = await apiFetch(`${API.chatHistory}/${chat.id}?limit=50`);
        if (!response.ok) throw new Error("Не удалось загрузить историю");
        const data = await response.json();
        renderMessages(data.messages || []);
    } catch (error) {
        console.error(error);
        messages.innerHTML = `<div class="messages-empty">Не удалось загрузить сообщения.</div>`;
    }

    // 2. Открываем WebSocket для реалтайма
    connectWebSocket(chat.id);

    renderChats();
    messenger.classList.add("show-chat"); // Для мобильной версии
}

/*
 * ==========================================================
 * USER SEARCH
 * ==========================================================
 */
userSearch.addEventListener("input", () => {
    clearTimeout(searchTimeout);
    const query = userSearch.value.trim();

    if (!query) {
        hideSearchResults();
        return;
    }

    searchTimeout = setTimeout(() => searchUsers(query), 400);
});

async function searchUsers(query) {
    try {
        const response = await apiFetch(API.findUsers, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ query: query })
        });

        if (!response.ok) {
            throw new Error("Ошибка поиска пользователей");
        }

        const data = await response.json();

        renderSearchResults(normalizeUsers(data.users));

    } catch (error) {
        console.error("Search error:", error);
        renderSearchMessage("Ошибка поиска пользователей");
    }
}


function normalizeUsers(data) {
    if (data && typeof data === "object" && !Array.isArray(data)) {
        return Object.entries(data).map(([userId, values]) => ({
            id: userId,
            name: values[0],
            surname: values[1],
            patronymic: values[2],
            email: values[3]
        }));
    }

    if (Array.isArray(data)) {
        return data.map(user => ({
            id: user.user_id,
            name: user.name,
            surname: user.surname,
            patronymic: user.patronymic
        }));
    }

    return [];
}

function renderSearchResults(users) {
    searchResults.innerHTML = "";

    if (users.length === 0) {
        renderSearchMessage("Пользователи не найдены");
        return;
    }

    users.forEach(user => {
        const fullName = [user.name, user.surname, user.patronymic].filter(Boolean).join(" ");
        const element = document.createElement("div");
        element.className = "search-result";

        element.innerHTML = `
            <div class="avatar">${escapeHtml(getInitials(fullName))}</div>
            <div>
                <div class="fw-semibold">${escapeHtml(fullName)}</div>
                ${user.email ? `<small class="text-muted">${escapeHtml(user.email)}</small>` : ""}
            </div>`;

        element.addEventListener("click", () => createPrivateChat(user.id));
        searchResults.appendChild(element);
    });

    searchResults.style.display = "block";
}

function renderSearchMessage(message) {
    searchResults.innerHTML = `<div class="p-3 text-muted">${escapeHtml(message)}</div>`;
    searchResults.style.display = "block";
}

function hideSearchResults() {
    searchResults.style.display = "none";
    searchResults.innerHTML = "";
}

/*
 * ==========================================================
 * CHAT CREATION
 * ==========================================================
 */
async function createPrivateChat(userId) {
    hideSearchResults();
    userSearch.value = "";

    try {
        const response = await apiFetch(API.createPrivate, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ user_2_id: userId })
        });

        if (!response.ok) {
            const data = await response.json().catch(() => ({}));
            throw new Error(data.detail || "Не удалось создать личный чат");
        }

        const data = await response.json();
        await loadChats();

        const chat = chats.find(item => String(item.id) === String(data.chat_id));
        if (chat) openChat(chat);

    } catch (error) {
        console.error(error);
        alert(error.message);
    }
}

createGroupForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    groupError.classList.add("d-none");
    groupError.textContent = "";

    const chatName = document.getElementById("group-name").value.trim();
    const chatDescription = document.getElementById("group-description").value.trim();

    if (!chatName) return;

    createGroupSubmit.disabled = true;
    createGroupSubmit.textContent = "Создание...";

    try {
        const response = await apiFetch(API.createGroup, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                chat_name: chatName,
                chat_description: chatDescription || null
            })
        });

        if (!response.ok) {
            const data = await response.json().catch(() => ({}));
            throw new Error(data.detail || "Не удалось создать групповой чат");
        }

        const data = await response.json();
        await loadChats();

        if (data.chat_id) {
            const chat = chats.find(item => String(item.id) === String(data.chat_id));
            if (chat) openChat(chat);
        }

        createGroupForm.reset();
        const modal = bootstrap.Modal.getInstance(document.getElementById("createGroupModal"));
        if (modal) modal.hide();

    } catch (error) {
        console.error(error);
        groupError.textContent = error.message;
        groupError.classList.remove("d-none");
    } finally {
        createGroupSubmit.disabled = false;
        createGroupSubmit.textContent = "Создать";
    }
});

/*
 * ==========================================================
 * UTILITIES & INIT
 * ==========================================================
 */
logoutButton.addEventListener("click", () => {
    localStorage.removeItem("access_token");
    window.location.href = "/api/v1/auth/";
});

document.addEventListener("click", (event) => {
    if (!event.target.closest(".search-wrapper")) {
        hideSearchResults();
    }
});

function getInitials(name) {
    if (!name) return "?";
    const parts = name.trim().split(/\s+/).filter(Boolean);
    if (parts.length === 1) return parts[0].substring(0, 2).toUpperCase();
    return (parts[0][0] + parts[1][0]).toUpperCase();
}

function getChatTypeText(type) {
    if (type === "group") return "Групповой чат";
    if (type === "private") return "Личный чат";
    return "Чат";
}

function escapeHtml(value) {
    if (value === null || value === undefined) return "";
    const div = document.createElement("div");
    div.textContent = String(value);
    return div.innerHTML;
}


/*
 * ==========================================================
 * WEBSOCKET (REALTIME)
 * ==========================================================
 */
let ws = null;
let wsReconnectTimer = null;
let wsReconnectDelay = 1000;      // экспоненциальная задержка: 1s, 2s, 4s ... max 30s
let intentionalClose = false;

function parseJwtPayload(token) {
    try {
        const base64 = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
        return JSON.parse(atob(base64));
    } catch (e) {
        return null;
    }
}

function wsUrl(chatId) {
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    return `${proto}://${window.location.host}/api/v1/ws/chat/${chatId}?token=${encodeURIComponent(getToken())}`;
}

function connectWebSocket(chatId) {
    disconnectWebSocket();          // закрываем соединение предыдущего чата
    intentionalClose = false;
    wsReconnectDelay = 1000;

    ws = new WebSocket(wsUrl(chatId));

    ws.onopen = () => {
        wsReconnectDelay = 1000;
        setComposerEnabled(true);
    };

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.event === "new_message") {
            appendMessage(data.message);
        } else if (data.event === "error") {
            console.error("WS:", data.detail);
        }
    };

    ws.onclose = (event) => {
        setComposerEnabled(false);
        // 1008 — не авторизован / не участник чата: переподключаться бессмысленно
        if (intentionalClose || event.code === 1008) return;
        scheduleReconnect(chatId);
    };

    ws.onerror = () => { /* onclose отработает следом */ };
}

function scheduleReconnect(chatId) {
    clearTimeout(wsReconnectTimer);
    wsReconnectTimer = setTimeout(() => {
        // чат мог смениться, пока ждали таймер
        if (selectedChatId && String(selectedChatId) === String(chatId)) {
            connectWebSocket(chatId);
        }
    }, wsReconnectDelay);
    wsReconnectDelay = Math.min(wsReconnectDelay * 2, 30000);
}

function disconnectWebSocket() {
    if (ws) {
        intentionalClose = true;
        ws.close();
        ws = null;
    }
    clearTimeout(wsReconnectTimer);
}

function setComposerEnabled(enabled) {
    messageInput.disabled = !enabled;
    messageSendBtn.disabled = !enabled;
    if (enabled) messageInput.focus();
}

function sendMessage(content) {
    if (!ws || ws.readyState !== WebSocket.OPEN) return false;
    ws.send(JSON.stringify({
        chat_id: selectedChatId,
        user_id: currentUserId,
        content: content
    }));
    return true;
}

function renderMessages(list) {
    messages.innerHTML = "";
    if (!list.length) {
        messages.innerHTML = `<div class="messages-empty">Сообщений пока нет. Напишите первым!</div>`;
        return;
    }
    list.forEach(appendMessage);
}

function appendMessage(msg) {
    const empty = messages.querySelector(".messages-empty");
    if (empty) empty.remove();

    const element = document.createElement("div");
    const mine = String(msg.user_id) === String(currentUserId);
    element.className = `message ${mine ? "outgoing" : "incoming"}`;

    const time = new Date(msg.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    element.innerHTML = `
        <div class="message-bubble">
            ${mine ? "" : `<div class="message-author fw-semibold small">${escapeHtml(msg.username || "")}</div>`}
            <div>${escapeHtml(msg.content)}</div>
            <div class="message-time small text-muted text-end">${time}</div>
        </div>`;
    messages.appendChild(element);
    messages.scrollTop = messages.scrollHeight;
}

messageForm.addEventListener("submit", (event) => {
    event.preventDefault();
    const content = messageInput.value.trim();
    if (!content) return;
    if (sendMessage(content)) {
        messageInput.value = "";
    }
});

async function init() {
    const token = getToken();
    if (!token) {
        redirectToLogin();
        return;
    }
    const payload = parseJwtPayload(token);
    currentUserId = payload ? payload.sub : null
    await loadChats();
}

// Запуск при загрузке DOM
document.addEventListener("DOMContentLoaded", init);