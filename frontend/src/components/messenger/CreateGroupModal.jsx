import ModalShell from "../ModalShell";
export default function CreateGroupModal({
    open,
    name,
    description,
    error,
    busy,
    onClose,
    onNameChange,
    onDescriptionChange,
    onSubmit,
}) {
    return (
        <ModalShell open={open} onClose={onClose}>
            <form onSubmit={onSubmit}>
                <div className="modal-header">
                    <h5 className="modal-title">Новый групповой чат</h5>
                    <button type="button" className="btn-close" data-bs-dismiss="modal" aria-label="Закрыть"></button>
                </div>
                <div className="modal-body">
                    {error && <div className="alert alert-danger">{error}</div>}
                    <div className="mb-3">
                        <label htmlFor="group-name" className="form-label">Название</label>
                        <input
                            type="text"
                            className="form-control"
                            id="group-name"
                            minLength={2}
                            maxLength={16}
                            required
                            value={name}
                            onChange={(event) => onNameChange(event.target.value)}
                        />
                        <div className="form-text">От 2 до 16 символов</div>
                    </div>
                    <div className="mb-3">
                        <label htmlFor="group-description" className="form-label">Описание</label>
                        <textarea
                            className="form-control"
                            id="group-description"
                            rows={3}
                            maxLength={250}
                            placeholder="Групповой чат"
                            value={description}
                            onChange={(event) => onDescriptionChange(event.target.value)}
                        />
                    </div>
                </div>
                <div className="modal-footer">
                    <button type="button" className="btn btn-light" data-bs-dismiss="modal">Отмена</button>
                    <button type="submit" className="btn btn-primary" disabled={busy}>
                        {busy ? "Создание..." : "Создать"}
                    </button>
                </div>
            </form>
        </ModalShell>
    );
}