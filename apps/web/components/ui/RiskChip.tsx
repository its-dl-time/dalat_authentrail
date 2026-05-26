import type { RiskLevel } from "@/lib/api";

const CONFIG: Record<RiskLevel, { label: string; cls: string }> = {
  low:    { label: "Tin cậy",    cls: "risk-low"  },
  medium: { label: "Cần lưu ý", cls: "risk-med"  },
  high:   { label: "Rủi ro cao",cls: "risk-high" },
};

export default function RiskChip({
  level,
  className = "",
}: {
  level: RiskLevel;
  className?: string;
}) {
  const { label, cls } = CONFIG[level];
  return (
    <span
      className={`${cls} inline-block px-2 py-0.5 rounded-full text-[9.5px] font-bold uppercase tracking-wide ${className}`}
    >
      {label}
    </span>
  );
}
