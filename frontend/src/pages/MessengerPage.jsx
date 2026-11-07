import { useCallback, useEffect, useRef, useState } from "react";
import Api from "../api/client";
import ChatItem from "../components/ChatItem";
import UserResultItem from "../components/UserResultItem";
import ModalShell from "../components/ModalShell";
import MessageList from "../components/MessageList";
import Avatar from "../components/Avatar";
import { toast, ToastContainer } from "../hooks/useToast.jsx";
import { useChatSocket, useDebouncedValue } from "../hooks/useMessengerHooks";
import { getChatTypeText, normalizeChats, normalizeUsers } from "../lib/helpers";

const LIST_WS_MAX = 3;

const roleTitle = (role) =>
    role === "admin" ? "Администратор" : role === "moderator" ? "Модератор" : "Пользователь";

export default function MessengerPage() {
    const currentUserIdRef = useRef(null);

    /* ===================== STATE ===================== */
    const [chats, setChats] = useState([]);
    const chatsRef = useRef([]);
    const [selectedChatId, setSelectedChatId] = useState(null);
    const selectedChatIdRef = useRef(null);
    const [listFilter, setListFilter] = useState("all"); // all | private | group
    const [roleLabel, setRoleLabel] = useState("");

    const [loadState, setLoadState] = useState("loading"); // loading | ready | error
    const reloadChatsFlag = useRef(0);
    const [reloadTick, setReloadTick] = useState(0);

    const [messages, setMessages] = useState([]);
    const [historyState, setHistoryState] = useState("idle"); // idle | loading | error
    const cursorRef = useRef(null);
    const hasMoreRef = useRef(false);
    const loadingHistoryRef = useRef(false);
    const [loadingMore, setLoadingMore] = useState(false);

    const [wsState, setWsState] = useState("connecting"); // connecting | online | offline

    const [searchQuery, setSearchQuery] = useState("");
    const debouncedSearch = useDebouncedValue(searchQuery.trim(), 400);
    const [searchResults, setSearchResults] = useState(null); // null — скрыть, [].. — список
    const searchStateRef = useRef({ query: "", offset: 0, limit: 10, hasMore: false });

    const [inviteOpen, setInviteOpen] = useState(false);
    const [inviteQuery, setInviteQuery] = useState("");
    const debouncedInvite = useDebouncedValue(inviteQuery.trim(), 400);
    const [inviteResults, setInviteResults] = useState([]);
    const [inviteMsg, setInviteMsg] = useState(null); // {kind, text}

    const [groupOpen, setGroupOpen] = useState(false);
    const [groupName, setGroupName] = useState("");
    const [groupDescription, setGroupDescription] = useState("");
    const [groupError, setGroupError] = useState("");
    const [groupBusy, setGroupBusy] = useState(false);

    const [composerValue, setComposerValue] = useState("");

    /* DOM refs */
    const messagesRef = useRef(null);
    const composerRef = useRef(null);
    const messengerRef = useRef(null);
    const listSocketsRef = useRef(new Map());

    /* всегда свежие значения для колбэков сокетов */
    const wsStateRef = useRef(wsState);
    wsStateRef.current = wsState;

    const updateChats = useCallback((updater) => {
        setChats((prev) => {
            const next = typeof updater === "function" ? updater(prev) : updater;
            chatsRef.current = next;
            return next;
        });
    }, []);

    const selectChat = useCallback((id) => {
        selectedChatIdRef.current = id;
        setSelectedChatId(id);
    }, []);

    const sortChats = (list) => [...list].sort((a, b) => {
        const at = a.lastMessage?.created_at ? new Date(a.lastMessage.created_at).getTime() : 0;
        const bt = b.lastMessage?.created_at ? new Date(b.lastMessage.created_at).getTime() : 0;
        if (at !== bt) return bt - at;
        return (a.name || "").localeCompare(b.name || "");
    });

    /* ===================== Фоновые сокписки на чаты списка ===================== */

    const closeListSocket = useCallback((chatId) => {
        const socket = listSocketsRef.current.get(chatId);
        if (socket) {
            socket.close();
            listSocketsRef.current.delete(chatId);
        }
    }, []);

    const applyChatUpdate = useCallback((chatId, lastMessage, markUnread) => {
        const id = String(chatId);
        const exists = chatsRef.current.some((c) => c.id === id);
        if (!exists) {
            // Собеседник создал новый чат — перезагружаем список
            reloadChatsFlag.current += 1;
            setReloadTick((t) => t + 1);
            return;
        }
        if (!lastMessage) return;
        updateChats((prev) => sortChats(prev.map((c) => {
            if (c.id !== id) return c;
            const copy = { ...c, lastMessage };
            if (markUnread && id !== String(selectedChatIdRef.current) &&
                String(lastMessage.user_id) !== String(currentUserIdRef.current)) {
                copy.unread = (c.unread || 0) + 1;
            }
            return copy;
        })));
    }, [updateChats]);

    const handleListEvent = useCallback((data) => {
        if (data.event === "chat_updated") {
            applyChatUpdate(data.chat_id, data.last_message, true);
        } else if (data.event === "new_message") {
            const msg = data.message;
            if (msg) applyChatUpdate(msg.chat_id || selectedChatIdRef.current, msg, false);
        }
    }, [applyChatUpdate]);

    const connectListSocket = useCallback((chatId) => {
        const conn = Api.connectChatWs(chatId, {
            onMessage: handleListEvent,
            shouldReconnect: () =>
                chatsRef.current.some((c) => c.id === chatId) &&
                String(selectedChatIdRef.current) !== chatId,
        });
        listSocketsRef.current.set(chatId, conn);
    }, [handleListEvent]);

    const ensureListSockets = useCallback(() => {
        if (!currentUserIdRef.current || chatsRef.current.length === 0) return;
        const candidates = chatsRef.current
            .map((c) => c.id)
            .filter((id) => id !== String(selectedChatIdRef.current))
            .slice(0, LIST_WS_MAX);

        for (const id of Array.from(listSocketsRef.current.keys())) {
            if (!candidates.includes(id)) closeListSocket(id);
        }
        for (const id of candidates) {
            if (!listSocketsRef.current.has(id)) connectListSocket(id);
        }
    }, [closeListSocket, connectListSocket]);

    /* ===================== Загрузка чатов ===================== */

    const refreshChatPreviewFromHistory = useCallback((chat) => {
        Api.getChatHistory(chat.id, 1)
            .then((data) => {
                const list = data.messages || [];
                const last = list[list.length - 1];
                if (last) {
                    updateChats((prev) => prev.map((c) => (c.id === chat.id ? { ...c, lastMessage: last } : c)));
                }
            })
            .catch(() => { /* не критично */ });
    }, [updateChats]);

    const loadChats = useCallback(async () => {
        const silent = reloadChatsFlag.current > 0;
        try {
            const data = await Api.getUserChats();
            const oldIds = new Set(chatsRef.current.map((c) => c.id));
            const normalized = normalizeChats(data.chats !== undefined ? data.chats : data);
            // сохраняем unread для уже известных чатов
            const merged = normalized.map((c) => {
                const old = chatsRef.current.find((x) => x.id === c.id);
                return old ? { ...c, unread: old.unread, lastMessage: c.lastMessage || old.lastMessage } : c;
            });
            updateChats(sortChats(merged));
            setLoadState("ready");

            // Новый чат появился (собеседник создал личный чат) — подтягиваем превью
            for (const chat of merged) {
                if (!oldIds.has(chat.id)) refreshChatPreviewFromHistory(chat);
            }
        } catch (error) {
            console.error(error);
            setLoadState("error");
        }
    }, [refreshChatPreviewFromHistory, updateChats]);

    /* init + перезагрузка по флагу */
    useEffect(() => {
        if (!Api.getAccessToken()) {
            Api.redirectToLogin();
            return;
        }
        currentUserIdRef.current = Api.getCurrentUserId();
        setRoleLabel(roleTitle(Api.getCurrentUserRole()));

        if (loadState === "error" && reloadChatsFlag.current === 0) {
            loadChats().then(ensureListSockets);
            return;
        }
        loadChats().then(ensureListSockets);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [reloadTick]);

    /* переподписка фоновых сокетов при смене списка/выбора */
    useEffect(() => {
        ensureListSockets();
    }, [chats, selectedChatId, ensureListSockets]);

    /* видимость вкладки — обновить список */
    useEffect(() => {
        const onVisibility = () => {
            if (document.visibilityState === "visible" && currentUserIdRef.current) {
                reloadChatsFlag.current += 1;
                loadChats().then(ensureListSockets);
            }
        };
        document.addEventListener("visibilitychange", onVisibility);
        return () => document.removeEventListener("visibilitychange", onVisibility);
    }, [loadChats, ensureListSockets]);

    /* закрытие сокетов при уходе со страницы */
    useEffect(() => {
        return () => {
            for (const id of Array.from(listSocketsRef.current.keys())) closeListSocket(id);
        };
    }, [closeListSocket]);

    /* клик вне поиска — скрыть результаты */
    useEffect(() => {
        const onDocClick = (event) => {
            if (!event.target.closest(".search-wrapper")) setSearchResults(null);
        };
        document.addEventListener("click", onDocClick);
        return () => document.removeEventListener("click", onDocClick);
    }, []);

    /* ===================== Открытие чата / история ===================== */

    const openChat = useCallback(async (chat) => {
        const previousChatId = selectedChatIdRef.current;
        selectChat(chat.id);
        updateChats((prev) => prev.map((c) => (c.id === chat.id ? { ...c, unread: 0 } : c)));

        cursorRef.current = null;
        hasMoreRef.current = true;
        loadingHistoryRef.current = false;

        if (previousChatId && previousChatId !== chat.id) closeListSocket(previousChatId);

        messengerRef.current?.classList.add("show-chat"); // мобильная версия

        setHistoryState("loading");
        setMessages([]);

        // 1. История через REST
        try {
            const data = await Api.getChatHistory(chat.id, 100, cursorRef.current);
            if (String(selectedChatIdRef.current) === String(chat.id)) {
                setMessages(data.messages || []);
                hasMoreRef.current = !!data.has_more;
                cursorRef.current = data.next_cursor;
                setHistoryState("idle");
                requestAnimationFrame(() => {
                    const el = messagesRef.current;
                    if (el) el.scrollTop = el.scrollHeight;
                });
            }
        } catch (error) {
            console.error(error);
            if (String(selectedChatIdRef.current) === String(chat.id)) setHistoryState("error");
        }
    }, [closeListSocket, selectChat, updateChats]);

    /* 2. WebSocket активного чата */
    const activeSocket = useChatSocket(selectedChatId, {
        onOpen: () => setWsState("online"),
        onClose: () => setWsState("offline"),
        onMessage: (data) => {
            if (data.event === "new_message") {
                const msg = data.message;
                if (String(selectedChatIdRef.current) === String(msg.chat_id ?? selectedChatIdRef.current)) {
                    setMessages((prev) => {
                        const el = messagesRef.current;
                        const stickToBottom = !el ||
                            el.scrollHeight - el.scrollTop - el.clientHeight < 120;
                        const next = [...prev, msg];
                        if (stickToBottom) {
                            requestAnimationFrame(() => {
                                if (messagesRef.current) messagesRef.current.scrollTop = messagesRef.current.scrollHeight;
                            });
                        }
                        return next;
                    });
                }
                applyChatUpdate(msg.chat_id || selectedChatIdRef.current, msg, false);
            } else if (data.event === "chat_updated") {
                applyChatUpdate(data.chat_id, data.last_message, true);
            } else if (data.event === "error") {
                toast(data.detail || "Ошибка доставки сообщения", "error");
            }
        },
        shouldReconnect: () => true,
    });

    /* Подгрузка истории при скролле вверх */
    useEffect(() => {
        const el = messagesRef.current;
        if (!el) return undefined;
        let timer = null;
        const onScroll = () => {
            clearTimeout(timer);
            timer = setTimeout(async () => {
                if (el.scrollTop >= 50 || loadingHistoryRef.current || !hasMoreRef.current) return;
                loadingHistoryRef.current = true;
                setLoadingMore(true);

                const oldScrollHeight = el.scrollHeight;
                const oldScrollTop = el.scrollTop;

                try {
                    const data = await Api.getChatHistory(selectedChatIdRef.current, 50, cursorRef.current);
                    const list = data.messages || [];
                    if (list.length > 0) {
                        setMessages((prev) => [...list, ...prev]);
                        hasMoreRef.current = !!data.has_more;
                        cursorRef.current = data.next_cursor;
                        // Компенсируем сдвиг: пользователь остаётся на том же месте
                        requestAnimationFrame(() => {
                            const box = messagesRef.current;
                            if (box) box.scrollTop = oldScrollTop + (box.scrollHeight - oldScrollHeight);
                        });
                    } else {
                        hasMoreRef.current = false;
                    }
                } catch (error) {
                    console.error("Ошибка загрузки истории:", error);
                } finally {
                    loadingHistoryRef.current = false;
                    setLoadingMore(false);
                }
            }, 100);
        };
        el.addEventListener("scroll", onScroll, { passive: true });
        return () => {
            clearTimeout(timer);
            el.removeEventListener("scroll", onScroll);
        };
    }, [selectedChatId]);

    const goBackToList = () => messengerRef.current?.classList.remove("show-chat");

    /* ===================== Composer ===================== */

    const composerEnabled = wsState === "online" && !!selectedChatId;

    useEffect(() => {
        if (composerEnabled) composerRef.current?.focus();
    }, [composerEnabled, selectedChatId]);

    const autoResize = () => {
        const el = composerRef.current;
        if (!el) return;
        el.style.height = "auto";
        el.style.height = Math.min(el.scrollHeight, 160) + "px";
    };

    const sendMessage = (event) => {
        event.preventDefault();
        const content = composerValue.trim();
        if (!content) return;
        const ok = activeSocket.send({
            chat_id: selectedChatId,
            user_id: currentUserIdRef.current,
            content,
        });
        if (ok) {
            setComposerValue("");
            requestAnimationFrame(autoResize);
        } else {
            toast("Нет соединения с чатом. Сообщение не отправлено.", "error");
        }
    };

    const onComposerKeyDown = (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            e.currentTarget.form?.requestSubmit();
        }
    };

    /* ===================== Поиск пользователей ===================== */

    useEffect(() => {
        const query = debouncedSearch;
        if (!query) {
            setSearchResults(null);
            return;
        }
        searchStateRef.current = { query, offset: 0, limit: 10, hasMore: false };
        runSearch(query, 0, false);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [debouncedSearch]);

    const runSearch = async (query, offset, append) => {
        try {
            const data = await Api.findUsers(query, offset, 10);
            searchStateRef.current.hasMore = !!data.has_more;
            const users = normalizeUsers(data.users);
            setSearchResults((prev) => {
                if (append) return [...(prev || []), ...users];
                return users;
            });
        } catch (error) {
            console.error("Search error:", error);
            setSearchResults([]);
            toast(error.message || "Ошибка поиска пользователей", "error");
        }
    };

    const loadMoreSearch = () => {
        searchStateRef.current.offset += searchStateRef.current.limit;
        runSearch(searchStateRef.current.query, searchStateRef.current.offset, true);
    };

    /* ===================== Создание личного чата ===================== */

    const handleCreatePrivateChat = async (userId) => {
        setSearchResults(null);
        setSearchQuery("");
        try {
            const data = await Api.createPrivateChat(userId);
            await loadChats();
            ensureListSockets();
            const chat = chatsRef.current.find((c) => c.id === String(data.chat_id));
            if (chat) openChat(chat);
        } catch (error) {
            console.error(error);
            toast(error.message || "Не удалось создать личный чат", "error");
        }
    };

    /* ===================== Создание группы ===================== */

    const openGroupModal = () => {
        setGroupError("");
        setGroupName("");
        setGroupDescription("");
        setGroupOpen(true);
    };

    const handleCreateGroup = async (event) => {
        event.preventDefault();
        setGroupError("");

        const chatName = groupName.trim();
        const chatDescription = groupDescription.trim();

        if (chatName.length < 2 || chatName.length > 16) {
            setGroupError("Название: от 2 до 16 символов");
            return;
        }

        setGroupBusy(true);
        try {
            const data = await Api.createGroupChat(chatName, chatDescription);
            await loadChats();
            ensureListSockets();
            const chat = chatsRef.current.find((c) => c.id === String(data.chat_id));
            setGroupOpen(false);
            toast("Групповой чат создан", "success");
            if (chat) openChat(chat);
        } catch (error) {
            console.error(error);
            setGroupError(error.message || "Не удалось создать групповой чат");
        } finally {
            setGroupBusy(false);
        }
    };

    /* ===================== Приглашение в группу ===================== */

    const selectedChat = chats.find((c) => c.id === String(selectedChatId)) || null;

    const openInviteModal = () => {
        if (!selectedChatId) return;
        setInviteMsg(null);
        setInviteQuery("");
        setInviteResults([]);
        setInviteOpen(true);
    };

    useEffect(() => {
        const query = debouncedInvite;
        if (!query) {
            setInviteResults([]);
            return;
        }
        Api.findUsers(query, 0, 10)
            .then((data) => setInviteResults(normalizeUsers(data.users)))
            .catch((error) => {
                setInviteResults([]);
                setInviteMsg({ kind: "danger", text: error.message || "Ошибка поиска" });
            });
    }, [debouncedInvite]);

    const inviteUser = async (userId, fullName) => {
        setInviteMsg({ kind: "info", text: "Приглашаем..." });
        try {
            // Эндпоинт возвращает текстовый ответ ("User add successfully" / "User add failed")
            const result = await Api.addUserToChat(userId, selectedChatId);
            const text = typeof result === "string" ? result : JSON.stringify(result || "");
            if (/fail/i.test(text)) {
                setInviteMsg({ kind: "danger", text: `Не удалось пригласить ${fullName}. Возможно, пользователь уже в чате.` });
            } else {
                setInviteMsg({ kind: "success", text: `${fullName} добавлен(а) в чат` });
                loadChats(true);
            }
        } catch (error) {
            setInviteMsg({ kind: "danger", text: error.message || "Ошибка приглашения" });
        }
    };

    /* ===================== Logout ===================== */

    const handleLogout = () => {
        for (const id of Array.from(listSocketsRef.current.keys())) closeListSocket(id);
        Api.redirectToLogin();
    };

    /* ===================== RENDER ===================== */

    const visibleChats = chats.filter((c) => listFilter === "all" || c.type === listFilter);
    const wsLabel = wsState === "online" ? "Онлайн" : wsState === "offline" ? "Офлайн" : "Соединение…";

    return (
        <div className="messenger" ref={messengerRef}>
            <ToastContainer />

            {/* ===================== LEFT SIDEBAR ===================== */}
            <aside className="sidebar">
                <div className="sidebar-header">
                    <div className="brand-row">
                        <div className="brand">
                            <div className="brand-logo">M</div>
                            <span>Мессенджер</span>
                        </div>
                        <div className="user-chip" title={roleLabel}>
                            <div className="avatar avatar--sm">{getInitialsForRole()}</div>
                            <button type="button" className="icon-btn" title="Выйти" onClick={handleLogout}>
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" /><polyline points="16 17 21 12 16 7" /><line x1="21" y1="12" x2="9" y2="12" /></svg>
                            </button>
                        </div>
                    </div>

                    {/* SEARCH USERS */}
                    <div className="search-wrapper">
                        <label htmlFor="user-search" className="visually-hidden">Поиск пользователей</label>
                        <svg className="search-icon" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" /></svg>
                        <input
                            type="text"
                            className="form-control"
                            id="user-search"
                            placeholder="Поиск по ФИО..."
                            autoComplete="off"
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                        />
                        {searchResults !== null && (
                            <div className="search-results card-pop">
                                {searchResults.length === 0 ? (
                                    <div className="search-msg">{debouncedSearch ? "Пользователи не найдены" : ""}</div>
                                ) : (
                                    <>
                                        {searchResults.map((user) => (
                                            <UserResultItem
                                                key={user.id}
                                                user={user}
                                                action="Написать →"
                                                onClick={() => handleCreatePrivateChat(user.id)}
                                            />
                                        ))}
                                        {searchStateRef.current.hasMore && (
                                            <button type="button" className="search-load-more" onClick={loadMoreSearch}>
                                                Показать ещё
                                            </button>
                                        )}
                                    </>
                                )}
                            </div>
                        )}
                    </div>

                    {/* TABS */}
                    <div className="chat-tabs" role="tablist">
                        {[["all", "Все"], ["private", "Личные"], ["group", "Группы"]].map(([filter, label]) => (
                            <button
                                key={filter}
                                className={"chat-tab" + (listFilter === filter ? " active" : "")}
                                type="button"
                                onClick={() => setListFilter(filter)}
                            >
                                {label}
                            </button>
                        ))}
                    </div>
                </div>

                {/* CHAT LIST */}
                <div className="chat-list">
                    {loadState === "loading" && (
                        <div className="chat-empty"><span className="spinner"></span> Загрузка чатов...</div>
                    )}
                    {loadState === "error" && (
                        <div className="chat-empty">
                            Не удалось загрузить чаты.<br />
                            <button
                                className="btn btn-sm btn-outline-primary mt-2"
                                onClick={() => { reloadChatsFlag.current += 1; setReloadTick((t) => t + 1); }}
                            >
                                Повторить
                            </button>
                        </div>
                    )}
                    {loadState === "ready" && visibleChats.length === 0 && (
                        <div className="chat-empty">
                            {chats.length
                                ? "В этой категории пока пусто."
                                : <>У вас пока нет чатов.<br />Найдите собеседника через поиск или создайте группу.</>}
                        </div>
                    )}
                    {loadState === "ready" && visibleChats.map((chat) => (
                        <ChatItem
                            key={chat.id}
                            chat={chat}
                            currentUserId={currentUserIdRef.current}
                            active={chat.id === String(selectedChatId)}
                            onClick={() => openChat(chat)}
                        />
                    ))}
                </div>

                {/* ACTIONS */}
                <div className="sidebar-footer">
                    <button type="button" className="btn btn-primary w-100" onClick={openGroupModal}>
                        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" /></svg>
                        {" "}Создать групповой чат
                    </button>
                </div>
            </aside>

            {/* ===================== MAIN CONTENT ===================== */}
            <main className="content">
                {!selectedChatId && (
                    <section className="welcome">
                        <div className="welcome-content">
                            <div className="welcome-icon">💬</div>
                            <h1>Добро пожаловать</h1>
                            <p>Выберите чат слева или найдите собеседника,<br />чтобы начать общение в реальном времени.</p>
                        </div>
                    </section>
                )}

                {selectedChat && (
                    <section className="chat-window open">
                        <header className="chat-header">
                            <button type="button" className="icon-btn back-btn" title="Назад к чатам" onClick={goBackToList}>
                                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="15 18 9 12 15 6" /></svg>
                            </button>
                            <Avatar name={selectedChat.name} />
                            <div className="chat-header-info">
                                <div className="chat-header-name">{selectedChat.name}</div>
                                <div className="chat-header-type">{getChatTypeText(selectedChat.type)}</div>
                            </div>
                            <div className={`ws-status ws-status--${wsState}`} title="Статус соединения">
                                <span className="ws-dot"></span><span className="ws-label">{wsLabel}</span>
                            </div>
                            {selectedChat.type === "group" && (
                                <button type="button" className="btn btn-outline-secondary btn-sm add-member-btn"
                                        title="Пригласить пользователя в чат" onClick={openInviteModal}>
                                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" /></svg>
                                    {" "}Пригласить
                                </button>
                            )}
                        </header>

                        <div className="messages" ref={messagesRef}>
                            {loadingMore && <div className="loading-spinner-top">Загрузка...</div>}
                            {historyState === "loading" && (
                                <div className="messages-empty"><span className="spinner"></span> Загрузка сообщений...</div>
                            )}
                            {historyState === "error" && (
                                <div className="messages-empty">Не удалось загрузить сообщения.</div>
                            )}
                            {historyState === "idle" && (
                                <MessageList messages={messages} currentUserId={currentUserIdRef.current} />
                            )}
                        </div>

                        <div className="message-input">
                            <form onSubmit={sendMessage}>
                                <div className="composer">
                                    <label htmlFor="message-input" className="visually-hidden">Сообщение</label>
                                    <textarea
                                        className="composer-field"
                                        id="message-input"
                                        rows={1}
                                        placeholder="Введите сообщение..."
                                        maxLength={1000}
                                        disabled={!composerEnabled}
                                        value={composerValue}
                                        ref={composerRef}
                                        onChange={(e) => { setComposerValue(e.target.value); autoResize(); }}
                                        onKeyDown={onComposerKeyDown}
                                    ></textarea>
                                    <button type="submit" className="send-btn" title="Отправить" disabled={!composerEnabled}>
                                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="22" y1="2" x2="11" y2="13" /><polygon points="22 2 15 22 11 13 2 9 22 2" /></svg>
                                    </button>
                                </div>
                                <div className="composer-hint">{composerEnabled ? "" : "Ожидание соединения..."}</div>
                            </form>
                        </div>
                    </section>
                )}
            </main>

            {/* Mobile sidebar backdrop */}
            <div className="sidebar-backdrop" onClick={goBackToList}></div>

            {/* ===================== CREATE GROUP MODAL ===================== */}
            <ModalShell open={groupOpen} onClose={() => setGroupOpen(false)}>
                <form onSubmit={handleCreateGroup}>
                    <div className="modal-header">
                        <h5 className="modal-title">Новый групповой чат</h5>
                        <button type="button" className="btn-close" data-bs-dismiss="modal" aria-label="Закрыть"></button>
                    </div>
                    <div className="modal-body">
                        {groupError && <div className="alert alert-danger">{groupError}</div>}
                        <div className="mb-3">
                            <label htmlFor="group-name" className="form-label">Название</label>
                            <input
                                type="text" className="form-control" id="group-name"
                                minLength={2} maxLength={16} required
                                value={groupName} onChange={(e) => setGroupName(e.target.value)}
                            />
                            <div className="form-text">От 2 до 16 символов</div>
                        </div>
                        <div className="mb-3">
                            <label htmlFor="group-description" className="form-label">Описание</label>
                            <textarea
                                className="form-control" id="group-description" rows={3} maxLength={250}
                                placeholder="Групповой чат"
                                value={groupDescription} onChange={(e) => setGroupDescription(e.target.value)}
                            ></textarea>
                        </div>
                    </div>
                    <div className="modal-footer">
                        <button type="button" className="btn btn-light" data-bs-dismiss="modal">Отмена</button>
                        <button type="submit" className="btn btn-primary" disabled={groupBusy}>
                            {groupBusy ? "Создание..." : "Создать"}
                        </button>
                    </div>
                </form>
            </ModalShell>

            {/* ===================== INVITE MODAL ===================== */}
            <ModalShell open={inviteOpen} onClose={() => setInviteOpen(false)}>
                <div className="modal-header">
                    <h5 className="modal-title">Пригласить в чат «{selectedChat ? selectedChat.name : ""}»</h5>
                    <button type="button" className="btn-close" data-bs-dismiss="modal" aria-label="Закрыть"></button>
                </div>
                <div className="modal-body">
                    {inviteMsg && <div className={`alert alert-${inviteMsg.kind}`}>{inviteMsg.text}</div>}
                    <div className="mb-3">
                        <label htmlFor="invite-search" className="form-label">Найти пользователя по ФИО</label>
                        <input
                            type="text" className="form-control" id="invite-search"
                            placeholder="Иванов Иван..." autoComplete="off"
                            value={inviteQuery} onChange={(e) => setInviteQuery(e.target.value)}
                        />
                    </div>
                    <div className="invite-results">
                        {!debouncedInvite ? (
                            <div className="text-muted small">Начните вводить имя для поиска.</div>
                        ) : inviteResults.length === 0 ? (
                            <div className="text-muted small">Пользователи не найдены.</div>
                        ) : (
                            inviteResults.map((user) => {
                                const fullName = [user.surname, user.name, user.patronymic].filter(Boolean).join(" ");
                                return (
                                    <UserResultItem
                                        key={user.id}
                                        user={user}
                                        action="Пригласить →"
                                        onClick={() => inviteUser(user.id, fullName)}
                                    />
                                );
                            })
                        )}
                    </div>
                </div>
            </ModalShell>
        </div>
    );
}

function getInitialsForRole() {
    return "?";
}
