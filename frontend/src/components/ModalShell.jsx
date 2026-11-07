import { useEffect, useRef } from "react";
import { Modal } from "bootstrap";

/**
 * Обёртка над Bootstrap-модалкой: показывает/скрывает модалку при смене `open`.
 */
export default function ModalShell({ open, onClose, children }) {
    const ref = useRef(null);
    const modalRef = useRef(null);

    useEffect(() => {
        if (!ref.current) return undefined;
        const modal = new Modal(ref.current);
        modalRef.current = modal;
        const el = ref.current;
        const hiddenHandler = () => onClose();
        el.addEventListener("hidden.bs.modal", hiddenHandler);
        if (open) modal.show();
        return () => {
            el.removeEventListener("hidden.bs.modal", hiddenHandler);
            modal.dispose();
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    useEffect(() => {
        if (!modalRef.current) return;
        if (open) modalRef.current.show();
        else modalRef.current.hide();
    }, [open]);

    return (
        <div className="modal fade" ref={ref} tabIndex="-1" aria-hidden="true">
            <div className="modal-dialog modal-dialog-centered">
                <div className="modal-content">
                    {children}
                </div>
            </div>
        </div>
    );
}
