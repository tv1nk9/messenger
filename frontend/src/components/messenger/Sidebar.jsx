import ChatItem from "../ChatItem";
import UserResultItem from "../UserResultItem";
const CHAT_FILTERS = [
    ["all", "Все"],
    ["private", "Личные"],
    ["group", "Группы"],
];
export default function Sidebar({
    roleLabel,
    searchQuery,
    onSearchQueryChange,
    searchResults,
    debouncedSearch,
    searchHasMore,
    onLoadMoreSearch,
    onCreatePrivateChat,
    listFilter,
    onListFilterChange,
    loadState,
    visibleChats,
    totalChats,
    currentUserId,
    selectedChatId,
    onOpenChat,
    onRetry,
    onLogout,
    onOpenGroupModal,
}) {
    return (
        <aside className="sidebar">
            <div className="sidebar-header">
                <div className="brand-row">
                    <div className="brand">
                        <div className="brand-logo">M</div>
                        <span>Мессенджер</span>
                    </div>
                    <div className="user-chip" title={roleLabel}>
                        <div className="avatar avatar--sm">?</div>
                        <button type="button" className="icon-btn" title="Выйти" onClick={onLogout}>
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                                <polyline points="16 17 21 12 16 7" />
                                <line x1="21" y1="12" x2="9" y2="12" />
                            </svg>
                        </button>
                    </div>
                </div>
                <div className="search-wrapper">
                    <label htmlFor="user-search" className="visually-hidden">Поиск пользователей</label>
                    <svg className="search-icon" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                        <circle cx="11" cy="11" r="8" />
                        <line x1="21" y1="21" x2="16.65" y2="16.65" />
                    </svg>
                    <input
                        type="text"
                        className="form-control"
                        id="user-search"
                        placeholder="Поиск по ФИО..."
                        autoComplete="off"
                        value={searchQuery}
                        onChange={(event) => onSearchQueryChange(event.target.value)}
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
                                            onClick={() => onCreatePrivateChat(user.id)}
                                        />
                                    ))}
                                    {searchHasMore && (
                                        <button type="button" className="search-load-more" onClick={onLoadMoreSearch}>
                                            Показать ещё
                                        </button>
                                    )}
                                </>
                            )}
                        </div>
                    )}
                </div>
                <div className="chat-tabs" role="tablist">
                    {CHAT_FILTERS.map(([filter, label]) => (
                        <button
                            key={filter}
                            className={"chat-tab" + (listFilter === filter ? " active" : "")}
                            type="button"
                            onClick={() => onListFilterChange(filter)}
                        >
                            {label}
                        </button>
                    ))}
                </div>
            </div>
            <div className="chat-list">
                {loadState === "loading" && (
                    <div className="chat-empty"><span className="spinner"></span> Загрузка чатов...</div>
                )}
                {loadState === "error" && (
                    <div className="chat-empty">
                        Не удалось загрузить чаты.<br />
                        <button className="btn btn-sm btn-outline-primary mt-2" onClick={onRetry}>
                            Повторить
                        </button>
                    </div>
                )}
                {loadState === "ready" && visibleChats.length === 0 && (
                    <div className="chat-empty">
                        {totalChats
                            ? "В этой категории пока пусто."
                            : <>У вас пока нет чатов.<br />Найдите собеседника через поиск или создайте группу.</>}
                    </div>
                )}
                {loadState === "ready" && visibleChats.map((chat) => (
                    <ChatItem
                        key={chat.id}
                        chat={chat}
                        currentUserId={currentUserId}
                        active={chat.id === String(selectedChatId)}
                        onClick={() => onOpenChat(chat)}
                    />
                ))}
            </div>
            <div className="sidebar-footer">
                <button type="button" className="btn btn-primary w-100" onClick={onOpenGroupModal}>
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                        <line x1="12" y1="5" x2="12" y2="19" />
                        <line x1="5" y1="12" x2="19" y2="12" />
                    </svg>
                    {" "}Создать групповой чат
                </button>
            </div>
        </aside>
    );
}