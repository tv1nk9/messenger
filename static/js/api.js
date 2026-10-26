/*
 * ==========================================================
 * API CLIENT — единый слой работы с REST/WebSocket и JWT
 * Покрывает все эндпоинты бэкенда:
 *   POST /api/v1/auth/register        (админ)
 *   POST /api/v1/auth/login           (OAuth2 form)
 *   POST /api/v1/auth/refresh
 *   POST /api/v1/chat/create_group_chat
 *   POST /api/v1/chat/create_private_chat
 *   POST /api/v1/chat/add_user_to_chat
 *   POST /api/v1/info/find_user
 *   GET  /api/v1/info/user_chats
 *   GET  /api/v1/info/chat_history/{chat_id}
 *   WS   /api/v1/ws/chat/{chat_id}?token=...
 * ==========================================================
 */
(function (global) {
    "use strict";

    const API_BASE = "/api/v1";
    const LOGIN_PAGE = "/login_page";
    const MAIN_PAGE = "/";

    const STORAGE_ACCESS = "access_token";
    const STORAGE_REFRESH = "refresh_token";

    /* ---------------- Token storage ---------------- */

    function getAccessToken() {
        return localStorage.getItem(STORAGE_ACCESS);
    }

    function getRefreshToken() {
        return localStorage.getItem(STORAGE_REFRESH);
    }

    function saveTokens(data) {
        if (data && data.access_token) {
            localStorage.setItem(STORAGE_ACCESS, data.access_token);
        }
        if (data && data.refresh_token) {
            localStorage.setItem(STORAGE_REFRESH, data.refresh_token);
        }
    }

    function clearTokens() {
        localStorage.removeItem(STORAGE_ACCESS);
        localStorage.removeItem(STORAGE_REFRESH);
    }

    function parseJwtPayload(token) {
        try {
            const base64 = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
            return JSON.parse(atob(base64));
        } catch (e) {
            return null;
        }
    }

    function getCurrentUserId() {
        const token = getAccessToken();
        if (!token) return null;
        const payload = parseJwtPayload(token);
        return payload ? payload.sub : null;
    }

    function getCurrentUserRole() {
        const token = getAccessToken();
        if (!token) return null;
        const payload = parseJwtPayload(token);
        return payload ? payload.role : null;
    }

    function isAdmin() {
        return getCurrentUserRole() === "admin";
    }

    function redirectToLogin() {
        clearTokens();
        window.location.href = LOGIN_PAGE;
    }

    /* ---------------- Fetch core ---------------- */

    let refreshInFlight = null;

    async function refreshTokens() {
        const refresh = getRefreshToken();
        if (!refresh) return false;
        if (!refreshInFlight) {
            refreshInFlight = fetch(`${API_BASE}/auth/refresh`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ refresh_token: refresh })
            })
                .then((resp) => {
                    if (!resp.ok) return false;
                    return resp.json().then((data) => {
                        saveTokens(data);
                        return true;
                    });
                })
                .catch(() => false)
                .finally(() => { refreshInFlight = null; });
        }
        return refreshInFlight;
    }

    async function request(path, options = {}, retry = true) {
        const headers = Object.assign({}, options.headers || {});
        const token = getAccessToken();
        if (token) headers["Authorization"] = `Bearer ${token}`;

        const response = await fetch(`${API_BASE}${path}`, Object.assign({}, options, { headers }));

        // Токен истёк — пробуем обновить один раз и повторить запрос
        if (response.status === 401 && retry) {
            const refreshed = await refreshTokens();
            if (refreshed) {
                return request(path, options, false);
            }
            redirectToLogin();
            throw new ApiError("Сессия истекла. Войдите заново.", 401);
        }

        if (response.status === 204) return null;

        let data = null;
        const text = await response.text();
        try { data = text ? JSON.parse(text) : null; } catch (e) { data = text; }

        if (!response.ok) {
            let detail = data && data.detail ? data.detail : `Ошибка ${response.status}`;
            if (Array.isArray(detail)) {
                detail = detail.map((d) => d.msg || JSON.stringify(d)).join("; ");
            }
            throw new ApiError(String(detail), response.status, data);
        }

        return data;
    }

    class ApiError extends Error {
        constructor(message, status, data) {
            super(message);
            this.name = "ApiError";
            this.status = status;
            this.data = data;
        }
    }

    function jsonBody(payload) {
        return {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        };
    }

    /* ---------------- Auth ---------------- */

    async function login(email, password) {
        const form = new URLSearchParams();
        form.append("username", email);
        form.append("password", password);
        const data = await request("/auth/login", {
            method: "POST",
            headers: { "Content-Type": "application/x-www-form-urlencoded" },
            body: form.toString()
        }, false);
        saveTokens(data);
        return data;
    }

    async function register(user) {
        return request("/auth/register", jsonBody(user));
    }

    /* ---------------- Chats ---------------- */

    async function createGroupChat(chatName, chatDescription) {
        return request("/chat/create_group_chat", jsonBody({
            chat_name: chatName,
            chat_description: chatDescription || null
        }));
    }

    async function createPrivateChat(userId2) {
        return request("/chat/create_private_chat", jsonBody({ user_2_id: userId2 }));
    }

    async function addUserToChat(userId, chatId) {
        return request("/chat/add_user_to_chat", jsonBody({ user_id: userId, chat_id: chatId }));
    }

    /* ---------------- Info ---------------- */

    async function findUsers(name, offset = 0, limit = 10) {
        return request("/info/find_user", jsonBody({ name, offset, limit }));
    }

    async function getUserChats() {
        return request("/info/user_chats");
    }

    async function getChatHistory(chatId, limit = 50) {
        return request(`/info/chat_history/${encodeURIComponent(chatId)}?limit=${limit}`);
    }

    /* ---------------- WebSocket ---------------- */

    function wsUrl(chatId, token) {
        const proto = window.location.protocol === "https:" ? "wss" : "ws";
        const t = token || getAccessToken();
        return `${proto}://${window.location.host}${API_BASE}/ws/chat/${encodeURIComponent(chatId)}?token=${encodeURIComponent(t)}`;
    }

    /**
     * Создаёт WebSocket с автоматическим переподключением.
     * handlers: { onOpen, onMessage(eventData), onClose(event), onError, shouldReconnect() }
     */
    function connectChatWs(chatId, handlers = {}) {
        let socket = null;
        let delay = 1000;
        let closedByUs = false;
        let reconnectTimer = null;

        function open() {
            socket = new WebSocket(wsUrl(chatId));
            socket.closedByUs = false;

            socket.onopen = () => {
                delay = 1000;
                handlers.onOpen && handlers.onOpen();
            };

            socket.onmessage = (event) => {
                let data;
                try { data = JSON.parse(event.data); } catch (e) { return; }
                handlers.onMessage && handlers.onMessage(data);
            };

            socket.onerror = () => { /* за ним всегда идёт onclose */ };

            socket.onclose = (event) => {
                handlers.onClose && handlers.onClose(event);
                if (closedByUs) return;
                if (event.code === 1008) return; // политика: невалидный токен / не участник
                if (handlers.shouldReconnect && !handlers.shouldReconnect()) return;
                clearTimeout(reconnectTimer);
                reconnectTimer = setTimeout(open, Math.min(delay, 30000));
                delay = Math.min(delay * 2, 30000);
            };
        }

        open();

        return {
            send(payload) {
                if (socket && socket.readyState === WebSocket.OPEN) {
                    socket.send(JSON.stringify(payload));
                    return true;
                }
                return false;
            },
            isOpen() {
                return socket && socket.readyState === WebSocket.OPEN;
            },
            close() {
                closedByUs = true;
                clearTimeout(reconnectTimer);
                if (socket) {
                    socket.onclose = null;
                    socket.close();
                    socket = null;
                }
            }
        };
    }

    /* ---------------- Public API ---------------- */

    global.Api = {
        API_BASE,
        LOGIN_PAGE,
        MAIN_PAGE,
        ApiError,
        getAccessToken,
        getRefreshToken,
        saveTokens,
        clearTokens,
        getCurrentUserId,
        getCurrentUserRole,
        isAdmin,
        redirectToLogin,
        refreshTokens,
        request,
        login,
        register,
        createGroupChat,
        createPrivateChat,
        addUserToChat,
        findUsers,
        getUserChats,
        getChatHistory,
        wsUrl,
        connectChatWs
    };
})(window);
