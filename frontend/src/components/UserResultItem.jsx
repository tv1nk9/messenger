import Avatar from "./Avatar";

/**
 * Результат поиска пользователя (используется в сайдбаре и в модалке приглашения).
 */
export default function UserResultItem({ user, action, onClick }) {
    const fullName = [user.surname, user.name, user.patronymic].filter(Boolean).join(" ");
    return (
        <div className="search-result" onClick={onClick}>
            <Avatar name={fullName} small />
            <div className="search-result-info">
                <div className="search-result-name">{fullName}</div>
                {user.email ? <div className="search-result-email">{user.email}</div> : null}
            </div>
            <span className="search-result-action">{action}</span>
        </div>
    );
}
