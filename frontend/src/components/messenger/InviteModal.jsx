import ModalShell from "../ModalShell";
import UserResultItem from "../UserResultItem";
import { fullNameOf } from "../../lib/helpers";
export default function InviteModal({
    open,
    chatName,
    query,
    debouncedQuery,
    results,
    message,
    onClose,
    onQueryChange,
    onInvite,
}) {
    return (
        <ModalShell open={open} onClose={onClose}>
            <div className="modal-header">
                <h5 className="modal-title">Пригласить в чат «{chatName}»</h5>
                <button type="button" className="btn-close" data-bs-dismiss="modal" aria-label="Закрыть"></button>
            </div>
            <div className="modal-body">
                {message && <div className={`alert alert-${message.kind}`}>{message.text}</div>}
                <div className="mb-3">
                    <label htmlFor="invite-search" className="form-label">Найти пользователя по ФИО</label>
                    <input
                        type="text"
                        className="form-control"
                        id="invite-search"
                        placeholder="Иванов Иван..."
                        autoComplete="off"
                        value={query}
                        onChange={(event) => onQueryChange(event.target.value)}
                    />
                </div>
                <div className="invite-results">
                    {!debouncedQuery ? (
                        <div className="text-muted small">Начните вводить имя для поиска.</div>
                    ) : results.length === 0 ? (
                        <div className="text-muted small">Пользователи не найдены.</div>
                    ) : (
                        results.map((user) => (
                            <UserResultItem
                                key={user.id}
                                user={user}
                                action="Пригласить →"
                                onClick={() => onInvite(user.id, fullNameOf(user))}
                            />
                        ))
                    )}
                </div>
            </div>
        </ModalShell>
    );
}