import { FolderOpen } from "lucide-react";
import { pickDirectory } from "../lib/tauri";

interface DirectoryPickerProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  optional?: boolean;
}

export function DirectoryPicker({
  label,
  value,
  onChange,
  placeholder = "Select a directory...",
  optional,
}: DirectoryPickerProps) {
  async function handlePick() {
    const dir = await pickDirectory();
    if (dir) onChange(dir);
  }

  return (
    <div>
      <label className="label">
        {label}
        {optional && <span className="text-gray-400 font-normal ml-1">(optional)</span>}
      </label>
      <div className="flex gap-2">
        <input
          type="text"
          className="input flex-1 font-mono text-xs"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
        />
        <button
          type="button"
          onClick={handlePick}
          className="btn-secondary px-3"
          title="Browse..."
        >
          <FolderOpen className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
