import { useEffect, useState } from "react";

/* Глобальные всплывающие уведомления (аналог toast() из оригинального JS) */

let counter = 0;
const listeners = new Set();

function pushToast(message, type = "info") {
    counter += 1;
    const item = { id: counter, message, type };
    listeners.forEach((fn) => fn((prev) => [...prev, item]));
    setTimeout(() => {
        listeners.forEach((fn) => fn((prev) => prev.filter((t) => t.id !== item.id)));
    }, 3500);
}

export function toast(message, type) {
    pushToast(message, type);
}

export function ToastContainer() {
    const [toasts, setToasts] = useState([]);

    useEffect(() => {
        listeners.add(setToasts);
        return () => { listeners.delete(setToasts); };
    }, []);

    if (toasts.length === 0) return null;
    return (
        <div className="toast-container">
            {toasts.map((t) => (
                <div key={t.id} className={`app-toast app-toast--${t.type} show`}>
                    {t.message}
                </div>
            ))}
        </div>
    );
}
