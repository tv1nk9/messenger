import Avatar from "../Avatar";
import MessageList from "../MessageList";
import { getChatTypeText } from "../../lib/helpers";
export default function ChatWindow({
    chat,
    wsState,
    historyState,
    messages,
    currentUserId,
    loadingMore,
    messagesRef,
    composerRef,
    composerValue,
    onComposerChange,
    onComposerKeyDown,
    onSendMessage,
    onBack,
    onOpenInvite,
}) {
    const wsLabel = wsState === "online" ? "Онлайн" : wsState === "offline" ? "Офлайн" : "Соединение…";
    const composerEnabled = wsState === "online";
    return (
        <section className="chat-window open">
            <header className="chat-header">
                <button type="button" className="icon-btn back-btn" title="Назад к чатам" onClick={onBack}>
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <polyline points="15 18 9 12 15 6" />
                    </svg>
                </button>
                <Avatar name={chat.name} />
                <div className="chat-header-info">
                    <div className="chat-header-name">{chat.name}</div>
                    <div className="chat-header-type">{getChatTypeText(chat.type)}</div>
                </div>
                <div className={`ws-status ws-status--${wsState}`} title="Статус соединения">
                    <span className="ws-dot"></span><span className="ws-label">{wsLabel}</span>
                </div>
                {chat.type === "group" && (
                    <button type="button" className="btn btn-outline-secondary btn-sm add-member-btn" title="Пригласить пользователя в чат" onClick={onOpenInvite}>
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                            <line x1="12" y1="5" x2="12" y2="19" />
                            <line x1="5" y1="12" x2="19" y2="12" />
                        </svg>
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
                {historyState === "idle" && <MessageList messages={messages} currentUserId={currentUserId} />}
            </div>
            <div className="message-input">
                <form onSubmit={onSendMessage}>
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
                            onChange={(event) => onComposerChange(event.target.value)}
                            onKeyDown={onComposerKeyDown}
                        />
                        <button type="submit" className="send-btn" title="Отправить" disabled={!composerEnabled}>
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <line x1="22" y1="2" x2="11" y2="13" />
                                <polygon points="22 2 15 22 11 13 2 9 22 2" />
                            </svg>
                        </button>
                    </div>
                    <div className="composer-hint">{composerEnabled ? "" : "Ожидание соединения..."}</div>
                </form>
            </div>
        </section>
    );
}