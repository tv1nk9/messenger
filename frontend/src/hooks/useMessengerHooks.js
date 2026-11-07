import { useCallback, useEffect, useRef, useState } from "react";
import Api from "../api/client";

/**
 * Дебаунс значения (используется для поиска по ФИО — задержка 400 мс, как в оригинале).
 */
export function useDebouncedValue(value, delay = 400) {
    const [debounced, setDebounced] = useState(value);
    useEffect(() => {
        const timer = setTimeout(() => setDebounced(value), delay);
        return () => clearTimeout(timer);
    }, [value, delay]);
    return debounced;
}

/**
 * Хранение состояния во время скролла (для подгрузки истории сообщений).
 */
export function useScrollInfo(ref) {
    const info = useRef({ scrollTop: 0, scrollHeight: 0, clientHeight: 0 });

    useEffect(() => {
        const el = ref.current;
        if (!el) return undefined;
        const onScroll = () => {
            info.current = {
                scrollTop: el.scrollTop,
                scrollHeight: el.scrollHeight,
                clientHeight: el.clientHeight,
            };
        };
        el.addEventListener("scroll", onScroll, { passive: true });
        return () => el.removeEventListener("scroll", onScroll);
    }, [ref]);

    return info;
}

/**
 * Подписка на WebSocket активного чата с автопереподключением (через Api.connectChatWs).
 * handlers оборачиваются в ref — сокет не пересоздаётся при каждом рендере.
 */
export function useChatSocket(chatId, handlers) {
    const socketRef = useRef(null);
    const handlersRef = useRef(handlers);
    handlersRef.current = handlers;

    useEffect(() => {
        if (!chatId) return undefined;

        const conn = Api.connectChatWs(chatId, {
            onOpen: () => handlersRef.current.onOpen && handlersRef.current.onOpen(),
            onClose: () => handlersRef.current.onClose && handlersRef.current.onClose(),
            onMessage: (data) => handlersRef.current.onMessage && handlersRef.current.onMessage(data),
            shouldReconnect: () => handlersRef.current.shouldReconnect
                ? handlersRef.current.shouldReconnect() : true,
        });
        socketRef.current = conn;

        return () => {
            conn.close();
            socketRef.current = null;
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [chatId]);

    const send = useCallback((payload) => {
        if (socketRef.current && socketRef.current.isOpen()) {
            return socketRef.current.send(payload);
        }
        return false;
    }, []);

    const isOpen = useCallback(() => !!(socketRef.current && socketRef.current.isOpen()), []);

    return { send, isOpen };
}
