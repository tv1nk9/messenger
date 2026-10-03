const LOGIN_URL = "/api/v1/auth/login";
const MAIN_PAGE_URL = "/api/v1/info";

// DOM
const form = document.getElementById("login-form");
const usernameInput = document.getElementById("username");
const passwordInput = document.getElementById("password");
const errorBox = document.getElementById("error-box");
const submitButton = document.getElementById("submit-btn");

// ERROR Handling
function showError(message) {
    errorBox.textContent = message;
    errorBox.classList.remove("d-none");
}

function hideError() {
    errorBox.textContent = "";
    errorBox.classList.add("d-none");
}

// INIT
// Если токен уже есть, нет смысла показывать страницу авторизации
if (localStorage.getItem("access_token")) {
    window.location.href = MAIN_PAGE_URL;
}

// LOGIN Logic
if (form) {
    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        hideError();

        // Блокируем кнопку на время запроса
        submitButton.disabled = true;
        const originalBtnText = submitButton.textContent;
        submitButton.textContent = "Вход...";

        const username = usernameInput.value.trim();
        const password = passwordInput.value;

        try {
            const formData = new URLSearchParams();
            formData.append("username", username);
            formData.append("password", password);

            const response = await fetch(LOGIN_URL, {
                method: "POST",
                headers: {
                    "Content-Type": "application/x-www-form-urlencoded"
                },
                body: formData
            });

            // Если сервер вернул ошибку
            if (!response.ok) {
                let errorMessage = "Неверный email или пароль";
                try {
                    const data = await response.json();
                    errorMessage = errorMessage;
                } catch (e) {
                }
                throw new Error(errorMessage);
            }

            const data = await response.json();

            if (!data.access_token) {
                throw new Error("Сервер не вернул токен авторизации");
            }

            // Сохраняем JWT
            localStorage.setItem("access_token", data.access_token);

            // Открываем главную страницу
            window.location.href = MAIN_PAGE_URL;

        } catch (error) {
            console.error("Login error:", error);
            showError(error.message || "Не удалось выполнить вход");
        } finally {
            // Возвращаем кнопку в исходное состояние
            submitButton.disabled = false;
            submitButton.textContent = originalBtnText;
        }
    });
} else {
    console.warn("Элемент формы #login-form не найден на странице.");
}