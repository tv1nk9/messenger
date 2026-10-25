/*
 * ==========================================================
 * AUTH PAGE — вход + регистрация (только для администратора)
 * Использует window.Api из api.js
 * ==========================================================
 */
(function () {
    "use strict";

    const $ = (id) => document.getElementById(id);

    const alertBox = $("alert-box");
    const loginForm = $("login-form");
    const registerForm = $("register-form");
    const switchLink = $("switch-link");
    const backToLogin = $("back-to-login");
    const switchHint = $("switch-hint");
    const authTitle = $("auth-title");
    const authSubtitle = $("auth-subtitle");

    /* ---------- Alerts ---------- */

    function showAlert(message, type) {
        alertBox.textContent = message;
        alertBox.className = `auth-alert alert-${type || "danger"}`;
        alertBox.classList.remove("d-none");
    }

    function hideAlert() {
        alertBox.classList.add("d-none");
        alertBox.textContent = "";
    }

    /* ---------- Если уже авторизован ---------- */

    if (Api.getAccessToken()) {
        window.location.href = Api.MAIN_PAGE;
        return;
    }

    /* ---------- Переключение форм ---------- */

    function showRegister() {
        loginForm.classList.add("d-none");
        registerForm.classList.remove("d-none");
        switchLink.classList.add("d-none");
        backToLogin.classList.remove("d-none");
        switchHint.textContent = "Регистрация новой учётной записи";
        authTitle.textContent = "Регистрация";
        authSubtitle.textContent = "Форма доступна только администраторам системы";
        hideAlert();
    }

    function showLogin() {
        registerForm.classList.add("d-none");
        loginForm.classList.remove("d-none");
        backToLogin.classList.add("d-none");
        switchLink.classList.remove("d-none");
        switchHint.textContent = "Ещё нет аккаунта?";
        authTitle.textContent = "С возвращением";
        authSubtitle.textContent = "Введите данные учётной записи, чтобы продолжить";
        hideAlert();
    }

    switchLink.addEventListener("click", (e) => { e.preventDefault(); showRegister(); });
    backToLogin.addEventListener("click", (e) => { e.preventDefault(); showLogin(); });

    /* ---------- Показ/скрытие пароля ---------- */

    document.querySelectorAll(".pwd-toggle").forEach((btn) => {
        btn.addEventListener("click", () => {
            const input = $(btn.dataset.target);
            if (!input) return;
            const isPwd = input.type === "password";
            input.type = isPwd ? "text" : "password";
            btn.textContent = isPwd ? "🙈" : "👁";
        });
    });

    /* ---------- LOGIN ---------- */

    if (loginForm) {
        loginForm.addEventListener("submit", async (event) => {
            event.preventDefault();
            hideAlert();

            const email = $("username").value.trim();
            const password = $("password").value;

            if (!email || !password) {
                showAlert("Заполните email и пароль");
                return;
            }

            const btn = $("submit-btn");
            btn.disabled = true;
            const original = btn.textContent;
            btn.textContent = "Вход...";

            try {
                await Api.login(email, password);
                window.location.href = Api.MAIN_PAGE;
            } catch (error) {
                console.error("Login error:", error);
                showAlert(error.status === 401 ? "Неверный email или пароль" : (error.message || "Не удалось выполнить вход"));
            } finally {
                btn.disabled = false;
                btn.textContent = original;
            }
        });
    }

    /* ---------- REGISTER (admin-only flow) ---------- */

    if (registerForm) {
        registerForm.addEventListener("submit", async (event) => {
            event.preventDefault();
            hideAlert();
            $("reg-success").classList.add("d-none");

            const adminEmail = $("reg-admin-email").value.trim();
            const adminPassword = $("reg-admin-password").value;

            const user = {
                role: $("reg-role").value,
                name: $("reg-name").value.trim(),
                surname: $("reg-surname").value.trim(),
                patronymic: $("reg-patronymic").value.trim() || null,
                email: $("reg-email").value.trim(),
                password: $("reg-password").value
            };

            // Клиентская валидация по ограничениям схемы бэкенда
            const lenErr = (v, min, max, label) =>
                v.length < min || v.length > max
                    ? `${label}: от ${min} до ${max} символов` : null;

            const errors = [];
            if (!adminEmail || !adminPassword) errors.push("Укажите учётные данные администратора");
            if (!user.name) errors.push(lenErr(user.name || "", 2, 16, "Имя"));
            else errors.push(lenErr(user.name, 2, 16, "Имя"));
            errors.push(lenErr(user.surname, 2, 16, "Фамилия"));
            if (user.patronymic) errors.push(lenErr(user.patronymic, 2, 16, "Отчество"));
            if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(user.email)) errors.push("Некорректный email");
            errors.push(lenErr(user.password, 4, 16, "Пароль"));

            const filtered = errors.filter(Boolean);
            if (filtered.length) {
                showAlert(filtered[0]);
                return;
            }

            const btn = $("register-btn");
            btn.disabled = true;
            const original = btn.textContent;
            btn.textContent = "Создание...";

            try {
                // 1. Авторизуемся под админом (нужен Bearer токен админа)
                await Api.login(adminEmail, adminPassword);

                if (!Api.isAdmin()) {
                    Api.clearTokens();
                    throw Object.assign(new Error("Регистрировать пользователей может только администратор"), { status: 403 });
                }

                // 2. Создаём пользователя
                const result = await Api.register(user);

                // 3. Возвращаем сессию админа (login выше перезаписал токены тем же админом — ок)
                $("reg-success").classList.remove("d-none");
                $("reg-user-id").textContent = result.user_id || "—";
                showAlert(`Пользователь «${user.name} ${user.surname}» создан`, "success");
                registerForm.reset();
            } catch (error) {
                console.error("Register error:", error);
                if (error.status === 409) showAlert("Пользователь с таким email уже существует");
                else if (error.status === 401) showAlert("Неверные учётные данные администратора");
                else if (error.status === 403) showAlert(error.message);
                else showAlert(error.message || "Не удалось создать пользователя");
                Api.clearTokens();
            } finally {
                btn.disabled = false;
                btn.textContent = original;
            }
        });
    }
})();
