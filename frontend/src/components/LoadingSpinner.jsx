export default function LoadingSpinner({ message }) {
  return (
    <div className="loading">
      <div className="spinner" />
      {message && <span>{message}</span>}
    </div>
  );
}
