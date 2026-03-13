interface Props {
    error: string | null;
}

export function ErrorPanel({ error }: Props) {
    if (!error) return null;

    return (
        <div className="panel error-panel">
            <h2>⚠ Error</h2>
            <pre className="error-body">{error}</pre>
        </div>
    );
}
