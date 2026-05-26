export default function LiveDot({ className = "" }: { className?: string }) {
  return (
    <span
      className={`live-dot flex-shrink-0 ${className}`}
      aria-label="Đang hoạt động"
    />
  );
}
