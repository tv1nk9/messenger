import Avatar from "./Avatar";
import { formatTime, getChatTypeText } from "../lib/helpers";

export default function ChatItem({ chat, currentUserId, active, onClick }) {
    let previewText = getChatTypeText(chat.type);
    let previewTime = "";

    if (chat.lastMessage) {
        const mine = String(chat.lastMessage.user_id) === String(currentUserId);
        previewText = (mine ? "Вы: " : "") + chat.lastMessage.content;
        previewTime = formatTime(chat.lastMessage.created_at);
    }

    return (
        <button
            type="button"
            className={"chat-item" + (active ? " active" : "")}
            onClick={onClick}
        >
            <Avatar name={chat.name} />
            <div className="chat-info">
                <div className="chat-top-row">
                    <div className="chat-name">{chat.name}</div>
                    <div className="chat-time">{previewTime}</div>
                </div>
                <div className="chat-bottom-row">
                    <div className="chat-last-message">{previewText}</div>
                    {chat.unread ? <span className="unread-badge">{chat.unread}</span> : null}
                </div>
            </div>
        </button>
    );
}
