import { useCallback, useEffect, useRef, useState } from "react";
import Api from "../api/client";
import Sidebar from "../components/messenger/Sidebar";
import ChatWindow from "../components/messenger/ChatWindow";
import CreateGroupModal from "../components/messenger/CreateGroupModal";
import InviteModal from "../components/messenger/InviteModal";
import { toast, ToastContainer } from "../hooks/useToast.jsx";
import { useChatSocket, useDebouncedValue } from "../hooks/useMessengerHooks";
import { normalizeChats, normalizeUsers } from "../lib/helpers";

const LIST_WS_MAX = 3;

const ROLE_TITLES = {
    admin: "Администратор",
    moderator: "Модератор",
    user: "Пользователь",
};

const roleTitle = (role) => ROLE_TITLES[role] || ROLE_TITLES.user;

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

    const visibleChats = chats.filter((chat) => listFilter === "all" || chat.type === listFilter);

    return (
        <div className="messenger" ref={messengerRef}>
            <ToastContainer />
            <Sidebar
                roleLabel={roleLabel}
                searchQuery={searchQuery}
                onSearchQueryChange={setSearchQuery}
                searchResults={searchResults}
                debouncedSearch={debouncedSearch}
                searchHasMore={searchStateRef.current.hasMore}
                onLoadMoreSearch={loadMoreSearch}
                onCreatePrivateChat={handleCreatePrivateChat}
                listFilter={listFilter}
                onListFilterChange={setListFilter}
                loadState={loadState}
                visibleChats={visibleChats}
                totalChats={chats.length}
                currentUserId={currentUserIdRef.current}
                selectedChatId={selectedChatId}
                onOpenChat={openChat}
                onRetry={() => { reloadChatsFlag.current += 1; setReloadTick((tick) => tick + 1); }}
                onLogout={handleLogout}
                onOpenGroupModal={openGroupModal}
            />

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
                    <ChatWindow
                        chat={selectedChat}
                        wsState={wsState}
                        historyState={historyState}
                        messages={messages}
                        currentUserId={currentUserIdRef.current}
                        loadingMore={loadingMore}
                        messagesRef={messagesRef}
                        composerRef={composerRef}
                        composerValue={composerValue}
                        onComposerChange={(value) => { setComposerValue(value); requestAnimationFrame(autoResize); }}
                        onComposerKeyDown={onComposerKeyDown}
                        onSendMessage={sendMessage}
                        onBack={goBackToList}
                        onOpenInvite={openInviteModal}
                    />
                )}
            </main>

            <div className="sidebar-backdrop" onClick={goBackToList}></div>

            <CreateGroupModal
                open={groupOpen}
                name={groupName}
                description={groupDescription}
                error={groupError}
                busy={groupBusy}
                onClose={() => setGroupOpen(false)}
                onNameChange={setGroupName}
                onDescriptionChange={setGroupDescription}
                onSubmit={handleCreateGroup}
            />
            <InviteModal
                open={inviteOpen}
                chatName={selectedChat ? selectedChat.name : ""}
                query={inviteQuery}
                debouncedQuery={debouncedInvite}
                results={inviteResults}
                message={inviteMsg}
                onClose={() => setInviteOpen(false)}
                onQueryChange={setInviteQuery}
                onInvite={inviteUser}
            />
        </div>
    );
}