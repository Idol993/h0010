import { useRef, useState } from "react";
import axios from "axios";

interface Props {
  onUploaded: () => void;
}

interface UploadState {
  name: string;
  status: "uploading" | "success" | "error";
  progress: number;
  error?: string;
}

export default function UploadPanel({ onUploaded }: Props) {
  const [items, setItems] = useState<UploadState[]>([]);
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFiles = async (files: FileList | File[]) => {
    const arr = Array.from(files).filter((f) => {
      const ext = "." + (f.name.split(".").pop() || "").toLowerCase();
      const allowed = [".pdf", ".docx", ".txt", ".md", ".text"];
      if (ext === ".doc") {
        const newItem: UploadState = {
          name: f.name,
          status: "error",
          progress: 0,
          error: "老版 Word .doc 格式暂不支持，请另存为 .docx 后再上传",
        };
        setItems((prev) => [...prev, newItem]);
        return false;
      }
      return allowed.includes(ext);
    });
    if (arr.length === 0) return;
    const newItems: UploadState[] = arr.map((f) => ({
      name: f.name,
      status: "uploading",
      progress: 0,
    }));
    setItems((prev) => [...prev, ...newItems]);

    for (let i = 0; i < arr.length; i++) {
      const file = arr[i];
      const idx = items.length + i;
      try {
        const form = new FormData();
        form.append("file", file);
        const { data } = await axios.post("/api/upload", form, {
          headers: { "Content-Type": "multipart/form-data" },
          onUploadProgress: (e) => {
            if (e.total) {
              setItems((prev) => {
                const next = [...prev];
                if (next[idx]) next[idx].progress = Math.round((e.loaded / e.total) * 80);
                return next;
              });
            }
          },
        });
        setItems((prev) => {
          const next = [...prev];
          if (data && data.success) {
            next[idx] = { ...next[idx], status: "success", progress: 100 };
          } else {
            next[idx] = { ...next[idx], status: "error", progress: 0, error: data?.error || "解析失败" };
          }
          return next;
        });
      } catch (err: any) {
        setItems((prev) => {
          const next = [...prev];
          next[idx] = {
            ...next[idx],
            status: "error",
            progress: 0,
            error: err?.response?.data?.detail || err.message || "上传失败",
          };
          return next;
        });
      }
    }
    onUploaded();
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    if (e.dataTransfer.files?.length) handleFiles(e.dataTransfer.files);
  };

  return (
    <div className="panel">
      <h3 style={{ margin: 0, marginBottom: 16 }}>上传简历</h3>
      <div
        className={`drop-zone ${dragging ? "dragging" : ""}`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
      >
        <div style={{ fontSize: 16, marginBottom: 8 }}>拖拽文件到此处 或 点击选择文件</div>
        <div style={{ fontSize: 13 }}>支持 PDF / Word (.docx) / 纯文本，老版 .doc 格式请转成 .docx 后上传，单个文件不超过 10MB</div>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept=".pdf,.docx,.txt,.md,.text"
          style={{ display: "none" }}
          onChange={(e) => e.target.files && handleFiles(e.target.files)}
        />
      </div>
      {items.length > 0 && (
        <div className="upload-list">
          {items.map((it, i) => (
            <div key={i} className={`upload-item ${it.status}`}>
              <span className="status-dot" />
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 14, marginBottom: 4, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {it.name}
                </div>
                <div className="progress-bar">
                  <div style={{ width: `${it.progress}%` }} />
                </div>
                {it.status === "success" && <div style={{ fontSize: 12, color: "var(--success)", marginTop: 4 }}>解析完成</div>}
                {it.status === "error" && <div style={{ fontSize: 12, color: "var(--danger)", marginTop: 4 }}>{it.error}</div>}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
