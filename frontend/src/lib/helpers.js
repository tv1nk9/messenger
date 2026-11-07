/* ===================== Хелперы отображения и нормализации данных ===================== */

export function getInitials(name) {
    if (!name) return "?";
    const parts = name.trim().split(/\s+/).filter(Boolean);
    if (parts.length === 1) return parts[0].substring(0, 2).toUpperCase();
    return (parts[0][0] + parts[1][0]).toUpperCase();
}

export function getChatTypeText(type) {
    if (type === "group") return "Групповой чат";
    if (type === "private") return "Личный чат";
    return "Чат";
}

export function avatarColor(seed) {
    const palette = ["#6366f1", "#8b5cf6", "#ec4899", "#f97316", "#10b981", "#06b6d4", "#3b82f6", "#eab308"];
    let hash = 0;
    const s = String(seed || "?");
    for (let i = 0; i < s.length; i++) hash = (hash * 31 + s.charCodeAt(i)) >>> 0;
    return palette[hash % palette.length];
}

export function formatTime(rawTime) {
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

export function normalizeChats(data) {
    if (!data) return [];
    const list = Array.isArray(data) ? data : Object.entries(data).map(([id, name]) => ({
        chat_id: id, chat_name: name, chat_type: "unknown", last_message: null
    }));
    return list.map(chat => ({
        id: String(chat.chat_id),
        type: chat.chat_type,
        name: chat.chat_name,
        lastMessage: chat.last_message || null,
        unread: 0
    }));
}

export function normalizeUsers(data) {
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

export function fullNameOf(user) {
    return [user.surname, user.name, user.patronymic].filter(Boolean).join(" ");
}

export function dateLabel(date) {
    const today = new Date();
    const yesterday = new Date(today);
    yesterday.setDate(today.getDate() - 1);
    if (date.toDateString() === today.toDateString()) return "Сегодня";
    if (date.toDateString() === yesterday.toDateString()) return "Вчера";
    return date.toLocaleDateString("ru-RU", { day: "numeric", month: "long" });
}

export function groupMessagesByDay(list) {
    const groups = [];
    let current = null;
    list.forEach(msg => {
        const d = new Date(msg.created_at);
        const key = isNaN(d) ? null : d.toDateString();
        if (key !== (current && current.key)) {
            current = { key, date: isNaN(d) ? null : d, items: [] };
            groups.push(current);
        }
        current.items.push(msg);
    });
    return groups;
}
