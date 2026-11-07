import Avatar from "./Avatar";
import { dateLabel, formatTime, groupMessagesByDay } from "../lib/helpers";

function Message({ msg, mine }) {
    return (
        <div className={`message ${mine ? "outgoing" : "incoming"}`}>
            {!mine && <Avatar name={msg.username} />}
            <div className="message-bubble">
                {!mine && <div className="message-author">{msg.username || ""}</div>}
                <div className="message-text">{msg.content}</div>
                <div className="message-time">{formatTime(msg.created_at)}</div>
            </div>
        </div>
    );
}

/**
 * Список сообщений с разделителями по дням.
 * key строится на id сообщения (или его позиции), поэтому при подгрузке истории
 * наверх React сохраняет уже отрендеренные DOM-узлы (важно для компенсации скролла).
 */
export default function MessageList({ messages, currentUserId }) {
    if (!messages.length) {
        return <div className="messages-empty">Сообщений пока нет.<br />Напишите первым!</div>;
    }

    const groups = groupMessagesByDay(messages);

    return (
        <>
            {groups.map((group, gi) => (
                <div key={`g-${group.key}-${gi}`}>
                    {group.date && <div className="date-divider"><span>{dateLabel(group.date)}</span></div>}
                    {group.items.map((msg, mi) => (
                        <Message
                            key={`${msg.message_id ?? msg.id ?? `${group.key}-${mi}`}`}
                            msg={msg}
                            mine={String(msg.user_id) === String(currentUserId)}
                        />
                    ))}
                </div>
            ))}
        </>
    );
}
