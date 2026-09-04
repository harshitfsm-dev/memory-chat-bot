import {
  FileArchive,
  FileCode,
  FileImage,
  FileSpreadsheet,
  FileText,
  FileType,
  type LucideIcon,
} from "lucide-react";

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  const units = ["KB", "MB", "GB"];
  let value = bytes / 1024;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  return `${value < 10 ? value.toFixed(1) : Math.round(value)} ${units[unit]}`;
}

export function fileKindLabel(mime: string, name: string): string {
  const ext = name.split(".").pop()?.toUpperCase() ?? "FILE";
  if (mime.startsWith("image/")) return ext === "FILE" ? "Image" : ext;
  return ext;
}

export function fileIcon(mime: string, name: string): LucideIcon {
  const ext = name.split(".").pop()?.toLowerCase() ?? "";
  if (mime.startsWith("image/")) return FileImage;
  if (mime === "application/pdf" || ext === "pdf") return FileType;
  if (["xlsx", "xls", "csv"].includes(ext)) return FileSpreadsheet;
  if (["zip", "rar", "7z"].includes(ext)) return FileArchive;
  if (["ts", "tsx", "js", "json", "py", "sql", "md"].includes(ext)) return FileCode;
  return FileText;
}
