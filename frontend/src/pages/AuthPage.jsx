import { useState } from "react";
import Api from "../api/client";

/* Блок показа/скрытия пароля */
function PasswordField({ id, label, value, onChange, autoComplete, placeholder, maxLength, minLength, required }) {
    const [visible, setVisible] = useState(false);
    return (
        <div>
            <label htmlFor={id} className="form-label">{label}</label>
            <div className="input-group">
                <input
                    type={visible ? "text" : "password"}
                    className="form-control"
                    id={id}
                    value={value}
                    onChange={(e) => onChange(e.target.value)}
                    placeholder={placeholder || "Введите пароль"}
                    autoComplete={autoComplete}
                    maxLength={maxLength}
                    minLength={minLength}
                    required={required}
                />
                <button
                    className="btn btn-outline-secondary"
                    type="button"
                    aria-label={visible ? "Скрыть пароль" : "Показать пароль"}
                    onClick={() => setVisible((v) => !v)}
                >
                    {visible ? "🙈" : "👁"}
                </button>
            </div>
        </div>
    );
}

const emptyUser = {
    name: "",
    surname: "",
    patronymic: "",
    email: "",
    password: "",
    role: "user",
};

export default function AuthPage() {
    /* mode: login | register */
    const [mode, setMode] = useState("login");
    const [alert, setAlert] = useState(null); // {type: 'danger'|'success', text}

    /* login state */
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [busy, setBusy] = useState(false);

    /* register state (admin-only flow) */
    const [adminEmail, setAdminEmail] = useState("");
    const [adminPassword, setAdminPassword] = useState("");
    const [user, setUser] = useState(emptyUser);
    const [createdUserId, setCreatedUserId] = useState(null);

    // Если уже авторизован — редирект на главную
    if (Api.getAccessToken()) {
        window.location.href = Api.MAIN_PAGE;
        return null;
    }

    const showAlert = (text, type = "danger") => setAlert({ text, type });
    const hideAlert = () => setAlert(null);

    const switchToRegister = () => {
        setMode("register");
        setCreatedUserId(null);
        hideAlert();
    };
    const switchToLogin = () => {
        setMode("login");
        hideAlert();
    };

    /* ---------- LOGIN ---------- */
    const handleLogin = async (event) => {
        event.preventDefault();
        hideAlert();

        const trimmedEmail = email.trim();
        if (!trimmedEmail || !password) {
            showAlert("Заполните email и пароль");
            return;
        }

        setBusy(true);
        try {
            await Api.login(trimmedEmail, password);
            window.location.href = Api.MAIN_PAGE;
        } catch (error) {
            console.error("Login error:", error);
            showAlert(error.status === 401 ? "Неверный email или пароль" : (error.message || "Не удалось выполнить вход"));
            setBusy(false);
        }
    };

    /* ---------- REGISTER (admin-only flow) ---------- */
    const handleRegister = async (event) => {
        event.preventDefault();
        hideAlert();
        setCreatedUserId(null);

        const trimmedAdminEmail = adminEmail.trim();
        const data = {
            role: user.role,
            name: user.name.trim(),
            surname: user.surname.trim(),
            patronymic: user.patronymic.trim() || null,
            email: user.email.trim(),
            password: user.password,
        };

        // Клиентская валидация по ограничениям схемы бэкенда
        const lenErr = (v, min, max, label) =>
            v.length < min || v.length > max
                ? `${label}: от ${min} до ${max} символов` : null;

        const errors = [];
        if (!trimmedAdminEmail || !adminPassword) errors.push("Укажите учётные данные администратора");
        errors.push(lenErr(data.name || "", 2, 16, "Имя"));
        errors.push(lenErr(data.surname, 2, 16, "Фамилия"));
        if (data.patronymic) errors.push(lenErr(data.patronymic, 2, 16, "Отчество"));
        if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(data.email)) errors.push("Некорректный email");
        errors.push(lenErr(data.password, 4, 16, "Пароль"));

        const filtered = errors.filter(Boolean);
        if (filtered.length) {
            showAlert(filtered[0]);
            return;
        }

        setBusy(true);
        try {
            // 1. Авторизуемся под админом (нужен Bearer токен админа)
            await Api.login(trimmedAdminEmail, adminPassword);

            if (!Api.isAdmin()) {
                Api.clearTokens();
                throw Object.assign(new Error("Регистрировать пользователей может только администратор"), { status: 403 });
            }

            // 2. Создаём пользователя
            const result = await Api.register(data);

            setCreatedUserId(result.user_id || "—");
            showAlert(`Пользователь «${data.name} ${data.surname}» создан`, "success");
            setUser(emptyUser);
        } catch (error) {
            console.error("Register error:", error);
            if (error.status === 409) showAlert("Пользователь с таким email уже существует");
            else if (error.status === 401) showAlert("Неверные учётные данные администратора");
            else if (error.status === 403) showAlert(error.message);
            else showAlert(error.message || "Не удалось создать пользователя");
            Api.clearTokens();
        } finally {
            setBusy(false);
        }
    };

    const isRegister = mode === "register";

    return (
        <div className="auth-shell">
            <div className="auth-brand d-none d-lg-flex">
                <div className="auth-brand-inner">
                    <div className="auth-logo">M</div>
                    <h1>Мессенджер</h1>
                    <ul className="auth-features">
                        <li><span>👥</span> Мессенджер (от англ. messenger — «посыльный», «курьер») — это программа или
                            приложение для мгновенного обмена сообщениями через интернет. С его помощью можно не только писать
                            текст, но и отправлять фото, видео, голосовые записи, документы,
                            стикеры и другие файлы (В этом нельзя).
                            Часто мессенджеры поддерживают аудио- и видеозвонки (Этот не поддерживает),
                            создание групповых чатов и каналов для публичных рассылок. </li>
                    </ul>
                </div>
            </div>

            <div className="auth-panel">
                <div className="auth-card">
                    <div className="auth-card-header">
                        <div className="auth-logo auth-logo--sm d-lg-none">M</div>
                        <h2>{isRegister ? "Регистрация" : "С возвращением"}</h2>
                        <p className="text-muted">
                            {isRegister
                                ? "Форма доступна только администраторам системы"
                                : "Введите данные учётной записи, чтобы продолжить"}
                        </p>
                    </div>

                    {alert && (
                        <div className={`auth-alert alert-${alert.type}`} role="alert">
                            {alert.text}
                        </div>
                    )}

                    {/* ===== LOGIN ===== */}
                    {!isRegister && (
                        <form className="auth-form" noValidate onSubmit={handleLogin}>
                            <div className="mb-3">
                                <label htmlFor="username" className="form-label">Email</label>
                                <input
                                    type="email"
                                    className="form-control"
                                    id="username"
                                    name="username"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    placeholder="example@mail.com"
                                    autoComplete="username"
                                    required
                                    autoFocus
                                />
                            </div>
                            <div className="mb-4">
                                <PasswordField
                                    id="password"
                                    label="Пароль"
                                    value={password}
                                    onChange={setPassword}
                                    autoComplete="current-password"
                                    required
                                />
                            </div>
                            <button type="submit" className="btn btn-primary w-100 btn-lg" disabled={busy}>
                                {busy ? "Вход..." : "Войти"}
                            </button>
                        </form>
                    )}

                    {/* ===== REGISTER (только администратор) ===== */}
                    {isRegister && (
                        <form className="auth-form" noValidate onSubmit={handleRegister}>
                            <div className="reg-admin-hint">
                                Регистрация доступна только администраторам. Авторизуйтесь, затем создайте нового пользователя.
                            </div>

                            <div className="row g-2">
                                <div className="col-12 mb-3">
                                    <label htmlFor="reg-admin-email" className="form-label">Email администратора</label>
                                    <input
                                        type="email"
                                        className="form-control"
                                        id="reg-admin-email"
                                        value={adminEmail}
                                        onChange={(e) => setAdminEmail(e.target.value)}
                                        placeholder="admin@mail.com"
                                        autoComplete="username"
                                    />
                                </div>
                                <div className="col-12 mb-3">
                                    <PasswordField
                                        id="reg-admin-password"
                                        label="Пароль администратора"
                                        value={adminPassword}
                                        onChange={setAdminPassword}
                                        autoComplete="current-password"
                                        placeholder="Пароль"
                                    />
                                </div>
                            </div>

                            <div className="reg-divider"><span>Новый пользователь</span></div>

                            <div className="row g-2">
                                <div className="col-4">
                                    <label htmlFor="reg-name" className="form-label">Имя *</label>
                                    <input type="text" className="form-control" id="reg-name" maxLength={16} required
                                           value={user.name} onChange={(e) => setUser({ ...user, name: e.target.value })} />
                                </div>
                                <div className="col-4">
                                    <label htmlFor="reg-surname" className="form-label">Фамилия *</label>
                                    <input type="text" className="form-control" id="reg-surname" maxLength={16} required
                                           value={user.surname} onChange={(e) => setUser({ ...user, surname: e.target.value })} />
                                </div>
                                <div className="col-4">
                                    <label htmlFor="reg-patronymic" className="form-label">Отчество</label>
                                    <input type="text" className="form-control" id="reg-patronymic" maxLength={16}
                                           value={user.patronymic} onChange={(e) => setUser({ ...user, patronymic: e.target.value })} />
                                </div>
                            </div>

                            <div className="row g-2 mt-1">
                                <div className="col-7">
                                    <label htmlFor="reg-email" className="form-label">Email *</label>
                                    <input type="email" className="form-control" id="reg-email" maxLength={32} required
                                           value={user.email} onChange={(e) => setUser({ ...user, email: e.target.value })} />
                                </div>
                                <div className="col-5">
                                    <label htmlFor="reg-role" className="form-label">Роль *</label>
                                    <select className="form-select" id="reg-role"
                                            value={user.role} onChange={(e) => setUser({ ...user, role: e.target.value })}>
                                        <option value="user">Пользователь</option>
                                        <option value="moderator">Модератор</option>
                                        <option value="admin">Администратор</option>
                                    </select>
                                </div>
                            </div>

                            <div className="mt-3">
                                <PasswordField
                                    id="reg-password"
                                    label="Пароль *"
                                    value={user.password}
                                    onChange={(v) => setUser({ ...user, password: v })}
                                    minLength={4}
                                    maxLength={16}
                                    required
                                />
                                <div className="form-text">От 4 до 16 символов</div>
                            </div>

                            {createdUserId && (
                                <div className="reg-success">
                                    Пользователь создан. ID: <code>{createdUserId}</code>
                                </div>
                            )}

                            <button type="submit" className="btn btn-primary w-100 btn-lg mt-4" disabled={busy}>
                                {busy ? "Создание..." : "Зарегистрировать"}
                            </button>
                        </form>
                    )}

                    <div className="auth-switch">
                        {!isRegister ? (
                            <>
                                <span>Ещё нет аккаунта?</span>
                                <a href="#" className="fw-semibold" onClick={(e) => { e.preventDefault(); switchToRegister(); }}>
                                    Регистрация (админ)
                                </a>
                            </>
                        ) : (
                            <a href="#" className="fw-semibold" onClick={(e) => { e.preventDefault(); switchToLogin(); }}>
                                ← Вернуться ко входу
                            </a>
                        )}
                    </div>

                    <div className="auth-footer">
                        Регистрация новых пользователей осуществляется администратором системы.
                    </div>
                </div>
            </div>
        </div>
    );
}
