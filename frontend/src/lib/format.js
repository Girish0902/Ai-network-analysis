export function formatDate(value) {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return String(value);
  return d.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatBytes(bytes) {
  if (bytes === undefined || bytes === null) return "—";
  if (bytes < 1024) return `${bytes} B`;
  const units = ["KB", "MB", "GB"];
  let value = bytes / 1024;
  let unit = units[0];
  for (let i = 0; i < units.length && value >= 1024; i += 1) {
    value /= 1024;
    unit = units[i + 1] || units[i];
  }
  return `${value.toFixed(1)} ${unit}`;
}

export function accessLabel(status) {
  if (!status) return "Admin access";
  switch (status) {
    case "APPROVED":
      return "Approved";
    case "PENDING":
      return "Pending";
    case "REJECTED":
      return "Rejected";
    default:
      return status;
  }
}