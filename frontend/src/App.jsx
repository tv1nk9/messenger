import { Navigate, Route, Routes } from "react-router-dom";
import AuthPage from "./pages/AuthPage";
import MessengerPage from "./pages/MessengerPage";
import Api from "./api/client";

/* Приватный маршрут: без токена — редирект на страницу входа */
function RequireAuth({ children }) {
    if (!Api.getAccessToken()) {
        return <Navigate to="/login" replace />;
    }
    return children;
}

export default function App() {
    return (
        <Routes>
            <Route path="/login" element={<AuthPage />} />
            <Route
                path="/"
                element={
                    <RequireAuth>
                        <MessengerPage />
                    </RequireAuth>
                }
            />
            <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
    );
}
