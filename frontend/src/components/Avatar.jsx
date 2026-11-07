import { avatarColor, getInitials } from "../lib/helpers";

export default function Avatar({ name, small = false }) {
    const initials = getInitials(name);
    const style = { background: avatarColor(name) };
    if (small) {
        return <div className="avatar avatar--sm" style={style}>{initials}</div>;
    }
    return <div className="avatar" style={style}>{initials}</div>;
}
