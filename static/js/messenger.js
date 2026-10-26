/*
 * ==========================================================
 * MESSENGER PAGE — список чатов, поиск, история, realtime WS
 * Покрывает все API-сценарии:
 *   GET  /info/user_chats            — список чатов
 *   POST /info/find_user             — пагинация (offset/limit, has_more)
 *   GET  /info/chat_history/{id}     — история сообщений
 *   POST /chat/create_private_chat   — создание личного чата из поиска
 *   POST /chat/create_group_chat     — создание группы (модалка)
 *   POST /chat/add_user_to_chat      — приглашение в группу (модалка "Пригласить")
 *   POST /auth/refresh               — автоматическое обновление токена (api.js)
 *   WS   /ws/chat/{id}               — new_message / chat_updated / error
 * ==========================================================
 */
(function () {
    "use strict";

    const $ = (id) => document.getElementById(id);

    /* ===================== STATE ===================== */
    let chats = [];
    let selectedChatId = null;
    let searchTimeout = null;
    let inviteTimeout = null;
    let currentUserId = null;
    let listFilter = "all";                 // all | private | group
    let activeSocket = null;                // WebSocket активного чата
    const listSockets = new Map();          // фоновые подписки chat_id -> connection
    const LIST_WS_MAX = 3;

    /* ===================== DOM ===================== */
    const messenger = $("messenger");
    const sidebar = $("sidebar");
    const backdrop = $("sidebar-backdrop");
    const chatList = $("chat-list");
    const welcome = $("welcome");
    const chatWindow = $("chat-window");
    const chatAvatar = $("chat-avatar");
    const chatHeaderName = $("chat-header-name");
    const chatHeaderType = $("chat-header-type");
    const wsStatus = $("ws-status");
    const addMemberBtn = $("add-member-btn");
    const messages = $("messages");
    const userSearch = $("user-search");
    const searchResults = $("search-results");
    const createGroupForm = $("create-group-form");
    const createGroupSubmit = $("create-group-submit");
    const groupError = $("group-error");
    const logoutButton = $("logout-btn");
    const messageForm = $("message-form");
    const messageInput = $("message-input");
    const messageSendBtn = $("message-send-btn");
    const composerHint = $("composer-hint");

    /* ===================== HELPERS ===================== */

    async function sleep(ms) {
      return new Promise(resolve => setTimeout(resolve, ms));
    }


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

    function avatarColor(seed) {
        const palette = ["#6366f1", "#8b5cf6", "#ec4899", "#f97316", "#10b981", "#06b6d4", "#3b82f6", "#eab308"];
        let hash = 0;
        const s = String(seed || "?");
        for (let i = 0; i < s.length; i++) hash = (hash * 31 + s.charCodeAt(i)) >>> 0;
        return palette[hash % palette.length];
    }

    function formatTime(rawTime) {
        if (!rawTime) return "";
        const date = new Date(rawTime);
        if (isNaN(date)) return "";
        const now = new Date();
        const sameDay = date.toDateString() === now.toDateString();
        if (sameDay) {
            return date.toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" });
        }
        return date.toLocaleDateString("ru-RU", { day: "2-digit", month: "short" });
    }

    function normalizeChats(data) {
        if (!data) return [];
        const list = Array.isArray(data) ? data : Object.entries(data).map(([id, name]) => ({
            chat_id: id, chat_name: name, chat_type: "unknown", last_message: null
        }));
        return list.map(chat => ({
            id: String(chat.chat_id),
            type: chat.chat_type,
            name: chat.chat_name,
            lastMessage: chat.last_message || null
        }));
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
            return data.map(u => ({ id: u.user_id, name: u.name, surname: u.surname, patronymic: u.patronymic, email: u.email }));
        }
        return [];
    }

    function toast(message, type) {
        let container = document.querySelector(".toast-container");
        if (!container) {
            container = document.createElement("div");
            container.className = "toast-container";
            document.body.appendChild(container);
        }
        const el = document.createElement("div");
        el.className = `app-toast app-toast--${type || "info"}`;
        el.textContent = message;
        container.appendChild(el);
        requestAnimationFrame(() => el.classList.add("show"));
        setTimeout(() => {
            el.classList.remove("show");
            setTimeout(() => el.remove(), 300);
        }, 3500);
    }

    /* ===================== CHAT LIST ===================== */

    async function loadChats(silent) {
        if (!silent && chats.length === 0 && !chatList.querySelector(".chat-item")) {
            chatList.innerHTML = `<div class="chat-empty"><span class="spinner"></span> Загрузка чатов...</div>`;
        }

        try {
            const data = await Api.getUserChats();
            const oldIds = new Set(chats.map(c => c.id));
            chats = normalizeChats(data.chats !== undefined ? data.chats : data);
            renderChats();

            // Новый чат появился (собеседник создал личный чат) — подтягиваем превью
            for (const chat of chats) {
                if (!oldIds.has(chat.id)) refreshChatPreviewFromHistory(chat);
            }
        } catch (error) {
            console.error(error);
            chatList.innerHTML = `
                <div class="chat-empty">
                    Не удалось загрузить чаты.<br>
                    <button class="btn btn-sm btn-outline-primary mt-2" id="retry-chats-btn">Повторить</button>
                </div>`;
            const retry = $("retry-chats-btn");
            if (retry) retry.addEventListener("click", () => loadChats().then(ensureListSockets));
        }
    }

    async function refreshChatPreviewFromHistory(chat) {
        try {
            const data = await Api.getChatHistory(chat.id, 1);
            const list = data.messages || [];
            const last = list[list.length - 1];
            if (last) {
                chat.lastMessage = last;
                renderChats();
            }
        } catch (e) { /* не критично */ }
    }

    function sortChats() {
        chats.sort((a, b) => {
            const at = a.lastMessage?.created_at ? new Date(a.lastMessage.created_at).getTime() : 0;
            const bt = b.lastMessage?.created_at ? new Date(b.lastMessage.created_at).getTime() : 0;
            if (at !== bt) return bt - at;
            return (a.name || "").localeCompare(b.name || "");
        });
    }

    function renderChats() {
        sortChats();
        chatList.innerHTML = "";

        const visible = chats.filter(c => listFilter === "all" || c.type === listFilter);

        if (visible.length === 0) {
            chatList.innerHTML = `<div class="chat-empty">${chats.length ? "В этой категории пока пусто." : "У вас пока нет чатов.<br>Найдите собеседника через поиск или создайте группу."}</div>`;
            return;
        }

        visible.forEach(chat => {
            const item = document.createElement("button");
            item.type = "button";
            item.className = "chat-item" + (chat.id === String(selectedChatId) ? " active" : "");

            let previewText = getChatTypeText(chat.type);
            let previewTime = "";
            let unreadBadge = "";

            if (chat.lastMessage) {
                const mine = String(chat.lastMessage.user_id) === String(currentUserId);
                previewText = (mine ? "Вы: " : "") + chat.lastMessage.content;
                previewTime = formatTime(chat.lastMessage.created_at);
            }
            if (chat.unread) {
                unreadBadge = `<span class="unread-badge">${chat.unread}</span>`;
            }

            item.innerHTML = `
                <div class="avatar" style="background:${avatarColor(chat.name)}">${escapeHtml(getInitials(chat.name))}</div>
                <div class="chat-info">
                    <div class="chat-top-row">
                        <div class="chat-name">${escapeHtml(chat.name)}</div>
                        <div class="chat-time">${escapeHtml(previewTime)}</div>
                    </div>
                    <div class="chat-bottom-row">
                        <div class="chat-last-message">${escapeHtml(previewText)}</div>
                        ${unreadBadge}
                    </div>
                </div>`;

            item.addEventListener("click", () => openChat(chat));
            chatList.appendChild(item);
        });
    }

    /* ===================== OPEN CHAT ===================== */

    let currentCursor = null;
    let isLoadingHistory = false;
    let hasMoreHistory = false;

    async function openChat(chat) {
        const previousChatId = selectedChatId;
        selectedChatId = chat.id;
        chat.unread = 0;

        currentCursor = null;
        isLoadingHistory = false;
        hasMoreHistory = true;

        closeActiveSocket();
        if (previousChatId && previousChatId !== chat.id) closeListSocket(previousChatId);
        ensureListSockets();

        welcome.style.display = "none";
        chatWindow.classList.add("open");
        messenger.classList.add("show-chat"); // мобильная версия

        chatAvatar.textContent = getInitials(chat.name);
        chatAvatar.style.background = avatarColor(chat.name);
        chatHeaderName.textContent = chat.name;
        chatHeaderType.textContent = getChatTypeText(chat.type);
        addMemberBtn.style.display = chat.type === "group" ? "" : "none";

        setComposerEnabled(false);
        messages.innerHTML = `<div class="messages-empty"><span class="spinner"></span> Загрузка сообщений...</div>`;

        // 1. История через REST
        try {
            const data = await Api.getChatHistory(chat.id, 100, currentCursor);
            if (String(selectedChatId) === String(chat.id)) {
                messages.innerHTML = ``
                renderMessages(data.messages || []);

                hasMoreHistory = data.has_more;
                currentCursor = data.next_cursor;

                messages.scrollTop = messages.scrollHeight;

            }
        } catch (error) {
            console.error(error);
            messages.innerHTML = `<div class="messages-empty">Не удалось загрузить сообщения.</div>`;
        }

        // 2. WebSocket для realtime
        connectActiveSocket(chat.id);

        renderChats();
    }

    messages.addEventListener("scroll", async () => {
        await sleep(1000);
        if (messages.scrollTop < 50 && !isLoadingHistory && hasMoreHistory) {
            await loadMoreHistory();
        }
    });

    async function loadMoreHistory() {
        if (isLoadingHistory || !hasMoreHistory) return;
        isLoadingHistory = true;

        const topSpinner = document.createElement("div");
        topSpinner.className = "loading-spinner-top";
        topSpinner.textContent = "Загрузка...";
        messages.prepend(topSpinner);

        try {
            const data = await Api.getChatHistory(selectedChatId, 50, currentCursor);

            if (data.messages && data.messages.length > 0) {
                // Запоминаем позицию ДО вставки
                const oldScrollHeight = messages.scrollHeight;
                const oldScrollTop = messages.scrollTop;

                // ✅ Вставляем наверх, а НЕ перерисовываем
                prependMessages(data.messages);

                hasMoreHistory = data.has_more;
                currentCursor = data.next_cursor;

                // Компенсируем сдвиг: пользователь остаётся на том же месте
                const newScrollHeight = messages.scrollHeight;
                messages.scrollTop = oldScrollTop + (newScrollHeight - oldScrollHeight);
            } else {
                hasMoreHistory = false;
            }
        } catch (error) {
            console.error("Ошибка загрузки истории:", error);
        } finally {
            isLoadingHistory = false;
            topSpinner.remove();
        }
    }

    function goBackToList() {
        messenger.classList.remove("show-chat");
    }

    /* ===================== WEBSOCKET ===================== */

    function setWsState(state) {
        wsStatus.className = `ws-status ws-status--${state}`;
        const label = wsStatus.querySelector(".ws-label");
        if (state === "online") label.textContent = "Онлайн";
        else if (state === "offline") label.textContent = "Офлайн";
        else label.textContent = "Соединение…";
    }

    function connectActiveSocket(chatId) {
        activeSocket = Api.connectChatWs(chatId, {
            onOpen: () => {
                setWsState("online");
                setComposerEnabled(true);
            },
            onClose: () => {
                setWsState("offline");
                setComposerEnabled(false);
            },
            onMessage: (data) => {
                if (data.event === "new_message") {
                    appendMessage(data.message);
                    updateChatPreview(data.message);
                } else if (data.event === "chat_updated") {
                    applyChatUpdate(data.chat_id, data.last_message, true);
                } else if (data.event === "error") {
                    toast(data.detail || "Ошибка доставки сообщения", "error");
                }
            },
            shouldReconnect: () => String(selectedChatId) === String(chatId)
        });
    }

    function closeActiveSocket() {
        if (activeSocket) {
            activeSocket.close();
            activeSocket = null;
            setWsState("offline");
        }
    }

    // Фоновые подписки на несколько чатов: мгновенные обновления списка
    function ensureListSockets() {
        if (!currentUserId || chats.length === 0) return;

        const candidates = chats
            .map(c => c.id)
            .filter(id => id !== String(selectedChatId))
            .slice(0, LIST_WS_MAX);

        for (const id of Array.from(listSockets.keys())) {
            if (!candidates.includes(id)) closeListSocket(id);
        }

        for (const id of candidates) {
            if (!listSockets.has(id)) connectListSocket(id);
        }
    }

    function connectListSocket(chatId) {
        const conn = Api.connectChatWs(chatId, {
            onMessage: (data) => {
                if (data.event === "chat_updated") {
                    applyChatUpdate(data.chat_id, data.last_message, true);
                } else if (data.event === "new_message") {
                    updateChatPreview(data.message);
                }
            },
            shouldReconnect: () =>
                chats.some(c => c.id === chatId) && String(selectedChatId) !== chatId
        });
        listSockets.set(chatId, conn);
    }

    function closeListSocket(chatId) {
        const socket = listSockets.get(chatId);
        if (socket) {
            socket.close();
            listSockets.delete(chatId);
        }
    }

    function applyChatUpdate(chatId, lastMessage, markUnread) {
        const chat = chats.find(c => c.id === String(chatId));
        if (chat) {
            if (lastMessage) {
                chat.lastMessage = lastMessage;
                if (markUnread && String(chatId) !== String(selectedChatId) &&
                    String(lastMessage.user_id) !== String(currentUserId)) {
                    chat.unread = (chat.unread || 0) + 1;
                }
                renderChats();
            }
            return;
        }
        // Собеседник создал новый чат — перезагружаем список
        loadChats(true).then(ensureListSockets);
    }

    function updateChatPreview(msg) {
        if (!msg) return;
        applyChatUpdate(msg.chat_id || selectedChatId, msg, false);
    }

    /* ===================== COMPOSER ===================== */

    function setComposerEnabled(enabled) {
        messageInput.disabled = !enabled;
        messageSendBtn.disabled = !enabled;
        composerHint.textContent = enabled ? "" : "Ожидание соединения...";
        if (enabled) messageInput.focus();
    }

    function sendMessage(content) {
        if (!activeSocket || !activeSocket.isOpen()) return false;
        return activeSocket.send({
            chat_id: selectedChatId,
            user_id: currentUserId,
            content: content
        });
    }

    function autoResize() {
        messageInput.style.height = "auto";
        messageInput.style.height = Math.min(messageInput.scrollHeight, 160) + "px";
    }

    messageInput.addEventListener("input", autoResize);

    messageInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            messageForm.requestSubmit();
        }
    });

    messageForm.addEventListener("submit", (event) => {
        event.preventDefault();
        const content = messageInput.value.trim();
        if (!content) return;
        if (sendMessage(content)) {
            messageInput.value = "";
            autoResize();
        } else {
            toast("Нет соединения с чатом. Сообщение не отправлено.", "error");
        }
    });

    /* ===================== MESSAGES RENDER ===================== */


    function prependMessages(list) {
        const empty = messages.querySelector(".messages-empty");
        if (empty) empty.remove();

        const fragment = document.createDocumentFragment();
        let lastDate = null;

        list.forEach(msg => {
            const d = new Date(msg.created_at);
            if (!isNaN(d)) {
                const key = d.toDateString();
                if (key !== lastDate) {
                    fragment.appendChild(makeDateDivider(d));
                    lastDate = key;
                }
            }

            const mine = String(msg.user_id) === String(currentUserId);
            const element = document.createElement("div");
            element.className = `message ${mine ? "outgoing" : "incoming"}`;
            const time = formatTime(msg.created_at);
            element.innerHTML = `
                ${mine ? "" : `<div class="message-avatar" style="background:${avatarColor(msg.username)}">${escapeHtml(getInitials(msg.username))}</div>`}
                <div class="message-bubble">
                    ${mine ? "" : `<div class="message-author">${escapeHtml(msg.username || "")}</div>`}
                    <div class="message-text">${escapeHtml(msg.content)}</div>
                    <div class="message-time">${time}</div>
                </div>`;
            fragment.appendChild(element);
        });

        // Вставляем после спиннера (если он есть) или в самое начало
        const spinner = messages.querySelector(".loading-spinner-top");
        const anchor = spinner ? spinner.nextSibling : messages.firstChild;
        messages.insertBefore(fragment, anchor);
    }


    function renderMessages(list) {
        messages.innerHTML = "";
        if (!list.length) {
            messages.innerHTML = `<div class="messages-empty">Сообщений пока нет.<br>Напишите первым!</div>`;
            return;
        }

        let lastDate = null;
        list.forEach(msg => {
            const d = new Date(msg.created_at);
            if (!isNaN(d)) {
                const key = d.toDateString();
                if (key !== lastDate) {
                    messages.appendChild(makeDateDivider(d));
                    lastDate = key;
                }
            }
            appendMessage(msg, true);
        });
        messages.scrollTop = messages.scrollHeight;
    }

    function makeDateDivider(date) {
        const el = document.createElement("div");
        el.className = "date-divider";
        const today = new Date();
        const yesterday = new Date(today);
        yesterday.setDate(today.getDate() - 1);
        let label;
        if (date.toDateString() === today.toDateString()) label = "Сегодня";
        else if (date.toDateString() === yesterday.toDateString()) label = "Вчера";
        else label = date.toLocaleDateString("ru-RU", { day: "numeric", month: "long" });
        el.innerHTML = `<span>${label}</span>`;
        return el;
    }

    function appendMessage(msg, skipScrollCheck) {
        const empty = messages.querySelector(".messages-empty");
        if (empty) empty.remove();

        const stickToBottom = skipScrollCheck ||
            messages.scrollHeight - messages.scrollTop - messages.clientHeight < 120;

        const element = document.createElement("div");
        const mine = String(msg.user_id) === String(currentUserId);
        element.className = `message ${mine ? "outgoing" : "incoming"}`;

        const time = formatTime(msg.created_at);
        element.innerHTML = `
            ${mine ? "" : `<div class="message-avatar" style="background:${avatarColor(msg.username)}">${escapeHtml(getInitials(msg.username))}</div>`}
            <div class="message-bubble">
                ${mine ? "" : `<div class="message-author">${escapeHtml(msg.username || "")}</div>`}
                <div class="message-text">${escapeHtml(msg.content)}</div>
                <div class="message-time">${time}</div>
            </div>`;
        messages.appendChild(element);

        if (stickToBottom) messages.scrollTop = messages.scrollHeight;
    }

    /* ===================== USER SEARCH (find_user + pagination) ===================== */

    let searchState = { query: "", offset: 0, limit: 10, hasMore: false };

    userSearch.addEventListener("input", () => {
        clearTimeout(searchTimeout);
        const query = userSearch.value.trim();
        if (!query) {
            hideSearchResults();
            return;
        }
        searchState = { query, offset: 0, limit: 10, hasMore: false };
        searchTimeout = setTimeout(() => runSearch(false), 400);
    });

    async function runSearch(append) {
        try {
            const data = await Api.findUsers(searchState.query, searchState.offset, searchState.limit);
            searchState.hasMore = !!data.has_more;
            const users = normalizeUsers(data.users);
            renderSearchResults(users, append);
        } catch (error) {
            console.error("Search error:", error);
            renderSearchMessage(error.message || "Ошибка поиска пользователей");
        }
    }

    function renderSearchResults(users, append) {
        if (!append) searchResults.innerHTML = "";
        searchResults.style.display = "block";

        if (!append && users.length === 0) {
            renderSearchMessage("Пользователи не найдены");
            return;
        }

        users.forEach(user => {
            const fullName = [user.surname, user.name, user.patronymic].filter(Boolean).join(" ");
            const element = document.createElement("div");
            element.className = "search-result";
            element.innerHTML = `
                <div class="avatar avatar--sm" style="background:${avatarColor(fullName)}">${escapeHtml(getInitials(fullName))}</div>
                <div class="search-result-info">
                    <div class="search-result-name">${escapeHtml(fullName)}</div>
                    ${user.email ? `<div class="search-result-email">${escapeHtml(user.email)}</div>` : ""}
                </div>
                <span class="search-result-action">Написать →</span>`;
            element.addEventListener("click", () => createPrivateChat(user.id));
            searchResults.appendChild(element);
        });

        if (searchState.hasMore) {
            const more = document.createElement("button");
            more.type = "button";
            more.className = "search-load-more";
            more.textContent = "Показать ещё";
            more.addEventListener("click", () => {
                searchState.offset += searchState.limit;
                runSearch(true);
            });
            searchResults.appendChild(more);
        }
    }

    function renderSearchMessage(message) {
        searchResults.innerHTML = `<div class="search-msg">${escapeHtml(message)}</div>`;
        searchResults.style.display = "block";
    }

    function hideSearchResults() {
        searchResults.style.display = "none";
        searchResults.innerHTML = "";
    }

    /* ===================== CREATE PRIVATE CHAT ===================== */

    async function createPrivateChat(userId) {
        hideSearchResults();
        userSearch.value = "";

        try {
            const data = await Api.createPrivateChat(userId);
            await loadChats(true);
            const chat = chats.find(c => c.id === String(data.chat_id));
            if (chat) openChat(chat);
        } catch (error) {
            console.error(error);
            toast(error.message || "Не удалось создать личный чат", "error");
        }
    }

    /* ===================== CREATE GROUP CHAT ===================== */

    const createGroupModal = new bootstrap.Modal($("createGroupModal"));

    $("new-group-btn").addEventListener("click", () => {
        groupError.classList.add("d-none");
        createGroupModal.show();
    });

    createGroupForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        groupError.classList.add("d-none");

        const chatName = $("group-name").value.trim();
        const chatDescription = $("group-description").value.trim();

        if (chatName.length < 2 || chatName.length > 16) {
            groupError.textContent = "Название: от 2 до 16 символов";
            groupError.classList.remove("d-none");
            return;
        }

        createGroupSubmit.disabled = true;
        createGroupSubmit.textContent = "Создание...";

        try {
            const data = await Api.createGroupChat(chatName, chatDescription);
            await loadChats(true);
            const chat = chats.find(c => c.id === String(data.chat_id));
            if (chat) openChat(chat);
            createGroupForm.reset();
            createGroupModal.hide();
            toast("Групповой чат создан", "success");
        } catch (error) {
            console.error(error);
            groupError.textContent = error.message || "Не удалось создать групповой чат";
            groupError.classList.remove("d-none");
        } finally {
            createGroupSubmit.disabled = false;
            createGroupSubmit.textContent = "Создать";
        }
    });

    /* ===================== INVITE TO GROUP (add_user_to_chat) ===================== */

    const inviteModal = new bootstrap.Modal($("inviteModal"));
    const inviteResultMsg = $("invite-result-msg");

    addMemberBtn.addEventListener("click", () => {
        if (!selectedChatId) return;
        const chat = chats.find(c => c.id === selectedChatId);
        $("invite-chat-name").textContent = chat ? chat.name : "";
        inviteResultMsg.classList.add("d-none");
        $("invite-search").value = "";
        $("invite-results").innerHTML = `<div class="text-muted small">Начните вводить имя для поиска.</div>`;
        inviteModal.show();
    });

    $("invite-search").addEventListener("input", () => {
        clearTimeout(inviteTimeout);
        const query = $("invite-search").value.trim();
        if (!query) {
            $("invite-results").innerHTML = `<div class="text-muted small">Начните вводить имя для поиска.</div>`;
            return;
        }
        inviteTimeout = setTimeout(() => runInviteSearch(query), 400);
    });

    async function runInviteSearch(query) {
        try {
            const data = await Api.findUsers(query, 0, 10);
            const users = normalizeUsers(data.users);
            const box = $("invite-results");
            box.innerHTML = "";
            if (users.length === 0) {
                box.innerHTML = `<div class="text-muted small">Пользователи не найдены.</div>`;
                return;
            }
            users.forEach(user => {
                const fullName = [user.surname, user.name, user.patronymic].filter(Boolean).join(" ");
                const el = document.createElement("div");
                el.className = "search-result";
                el.innerHTML = `
                    <div class="avatar avatar--sm" style="background:${avatarColor(fullName)}">${escapeHtml(getInitials(fullName))}</div>
                    <div class="search-result-info">
                        <div class="search-result-name">${escapeHtml(fullName)}</div>
                        ${user.email ? `<div class="search-result-email">${escapeHtml(user.email)}</div>` : ""}
                    </div>
                    <span class="search-result-action">Пригласить →</span>`;
                el.addEventListener("click", () => inviteUser(user.id, fullName));
                box.appendChild(el);
            });
        } catch (error) {
            $("invite-results").innerHTML = `<div class="text-muted small">${escapeHtml(error.message || "Ошибка поиска")}</div>`;
        }
    }

    async function inviteUser(userId, fullName) {
        showInviteResult("Приглашаем...", "info");
        try {
            // Эндпоинт возвращает текстовый ответ ("User add successfully" / "User add failed")
            const result = await Api.addUserToChat(userId, selectedChatId);
            const text = typeof result === "string" ? result : JSON.stringify(result || "");
            if (/fail/i.test(text)) {
                showInviteResult(`Не удалось пригласить ${fullName}. Возможно, пользователь уже в чате.`, "danger");
            } else {
                showInviteResult(`${fullName} добавлен(а) в чат`, "success");
                loadChats(true);
            }
        } catch (error) {
            showInviteResult(error.message || "Ошибка приглашения", "danger");
        }
    }

    function showInviteResult(message, kind) {
        inviteResultMsg.textContent = message;
        inviteResultMsg.className = `alert alert-${kind}`;
    }

    /* ===================== TABS / LOGOUT / INIT ===================== */

    document.querySelectorAll(".chat-tab").forEach(tab => {
        tab.addEventListener("click", () => {
            document.querySelectorAll(".chat-tab").forEach(t => t.classList.remove("active"));
            tab.classList.add("active");
            listFilter = tab.dataset.filter;
            renderChats();
        });
    });

    logoutButton.addEventListener("click", () => {
        closeActiveSocket();
        for (const id of Array.from(listSockets.keys())) closeListSocket(id);
        Api.redirectToLogin();
    });

    $("back-btn").addEventListener("click", goBackToList);
    backdrop.addEventListener("click", goBackToList);

    document.addEventListener("click", (event) => {
        if (!event.target.closest(".search-wrapper")) hideSearchResults();
    });

    async function init() {
        if (!Api.getAccessToken()) {
            Api.redirectToLogin();
            return;
        }
        currentUserId = Api.getCurrentUserId();

        // Чип текущего пользователя: роль из JWT
        const role = Api.getCurrentUserRole();
        $("user-chip").title = role === "admin" ? "Администратор" : (role === "moderator" ? "Модератор" : "Пользователь");

        await loadChats();
        ensureListSockets();
    }

    document.addEventListener("visibilitychange", () => {
        if (document.visibilityState === "visible" && currentUserId) {
            loadChats(true).then(ensureListSockets);
        }
    });

    window.addEventListener("beforeunload", () => {
        closeActiveSocket();
        for (const id of Array.from(listSockets.keys())) closeListSocket(id);
    });

    document.addEventListener("DOMContentLoaded", init);
})();
