import { useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useDropzone } from "react-dropzone";
import {
  Upload, FileText, X, CheckCircle2,
  AlertCircle, File, Loader2
} from "lucide-react";
import { PageHeader }       from "@/components/ui/PageHeader";
import { Button }           from "@/components/ui/Button";
import { Card, CardContent } from "@/components/ui/Card";
import { ProgressBar }      from "@/components/ui/ProgressBar";
import { toast }            from "@/components/ui/Toaster";
import { useUploadDataset } from "@/hooks/useDatasets";
import { formatBytes, cn }  from "@/lib/utils";

const ACCEPTED_TYPES = {
  "text/csv": [".csv"],
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [".xlsx"],
  "application/vnd.ms-excel": [".xls"],
  "application/json": [".json"],
  "application/octet-stream": [".parquet"],
  "application/pdf": [".pdf"],
};

const MAX_SIZE = 100 * 1024 * 1024; // 100 MB

const FORMAT_TIPS = [
  { ext: "CSV",     desc: "Comma-separated values — most common format" },
  { ext: "Excel",   desc: "XLSX or XLS spreadsheets" },
  { ext: "JSON",    desc: "Array of objects or flat records" },
  { ext: "Parquet", desc: "Columnar binary format — very fast" },
  { ext: "PDF",     desc: "Tables extracted via pdfplumber" },
];

export function UploadPage() {
  const navigate = useNavigate();
  const upload = useUploadDataset();

  const [file, setFile] = useState<File | null>(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [uploadProgress, setUploadProgress] = useState(0);

  const onDrop = useCallback((accepted: File[]) => {
    if (accepted.length > 0) {
      const f = accepted[0];
      setFile(f);
      // Derive a clean default name from filename
      setName(f.name.replace(/\.[^.]+$/, "").replace(/[-_]/g, " "));
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive, fileRejections } = useDropzone({
    onDrop,
    accept: ACCEPTED_TYPES,
    maxSize: MAX_SIZE,
    maxFiles: 1,
  });

  const handleUpload = async () => {
    if (!file) return;

    try {
      setUploadProgress(10);
      const dataset = await upload.mutateAsync({
        file,
        name: name || file.name,
        description: description || undefined,
      });
      setUploadProgress(100);
      toast.success("Dataset uploaded!", "Profiling in background — redirecting to workspace.");
      setTimeout(() => navigate(`/workspace/${dataset.id}`), 800);
    } catch (err) {
      setUploadProgress(0);
      const msg = err instanceof Error ? err.message : "Upload failed";
      toast.error("Upload failed", msg);
    }
  };

  const clearFile = () => {
    setFile(null);
    setName("");
    setDescription("");
    setUploadProgress(0);
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6 animate-fade-in">
      <PageHeader
        title="Upload Dataset"
        description="Upload a file to start a multi-agent analysis. Profiling begins automatically."
      />

      {/* Drop zone */}
      <Card>
        <CardContent className="pt-5">
          {!file ? (
            <div
              {...getRootProps()}
              className={cn(
                "border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-all duration-200",
                isDragActive
                  ? "border-brand-500 bg-brand-500/5"
                  : "border-surface-4 hover:border-brand-500/50 hover:bg-surface-3/30"
              )}
            >
              <input {...getInputProps()} />
              <div className={cn(
                "flex items-center justify-center w-12 h-12 rounded-xl border mx-auto mb-4 transition-colors",
                isDragActive
                  ? "bg-brand-500/15 border-brand-500/30"
                  : "bg-surface-3 border-surface-4"
              )}>
                <Upload className={cn("w-5 h-5", isDragActive ? "text-brand-400" : "text-zinc-500")} />
              </div>
              <p className="text-sm font-medium text-zinc-200 mb-1">
                {isDragActive ? "Drop your file here" : "Drag & drop your dataset here"}
              </p>
              <p className="text-xs text-zinc-500 mb-4">or click to browse</p>
              <div className="flex flex-wrap gap-2 justify-center">
                {["CSV", "Excel", "JSON", "Parquet", "PDF"].map((t) => (
                  <span key={t} className="px-2 py-0.5 text-2xs rounded-md bg-surface-3 border border-surface-4 text-zinc-500 font-mono">
                    .{t.toLowerCase()}
                  </span>
                ))}
              </div>
              <p className="text-2xs text-zinc-600 mt-3">Maximum file size: 100 MB</p>
            </div>
          ) : (
            /* File selected state */
            <div className="space-y-4">
              <div className="flex items-center gap-3 p-4 rounded-xl bg-surface-3/50 border border-surface-4">
                <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-brand-500/10 border border-brand-500/20 shrink-0">
                  <File className="w-5 h-5 text-brand-400" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-zinc-100 truncate">{file.name}</p>
                  <p className="text-xs text-zinc-500">{formatBytes(file.size)}</p>
                </div>
                {!upload.isPending && (
                  <button onClick={clearFile} className="text-zinc-500 hover:text-zinc-300 transition-colors">
                    <X className="w-4 h-4" />
                  </button>
                )}
              </div>

              {/* Name input */}
              <div>
                <label className="block text-xs font-medium text-zinc-400 mb-1.5">
                  Dataset name
                </label>
                <input
                  className="input-base"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Sales Q3 2024"
                  disabled={upload.isPending}
                />
              </div>

              {/* Description input */}
              <div>
                <label className="block text-xs font-medium text-zinc-400 mb-1.5">
                  Description <span className="text-zinc-600">(optional)</span>
                </label>
                <textarea
                  className="input-base resize-none"
                  rows={2}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="What does this dataset contain?"
                  disabled={upload.isPending}
                />
              </div>

              {/* Progress */}
              {upload.isPending && (
                <div className="space-y-1.5">
                  <ProgressBar value={uploadProgress} size="sm" />
                  <p className="text-xs text-zinc-500 flex items-center gap-1.5">
                    <Loader2 className="w-3 h-3 animate-spin" />
                    Uploading…
                  </p>
                </div>
              )}

              {/* Success */}
              {upload.isSuccess && (
                <div className="flex items-center gap-2 text-success text-xs">
                  <CheckCircle2 className="w-4 h-4" />
                  Upload complete! Redirecting…
                </div>
              )}

              {/* Error */}
              {upload.isError && (
                <div className="flex items-center gap-2 text-danger text-xs">
                  <AlertCircle className="w-4 h-4" />
                  {upload.error?.message ?? "Upload failed"}
                </div>
              )}

              <Button
                className="w-full"
                onClick={handleUpload}
                isLoading={upload.isPending}
                disabled={!name.trim() || upload.isPending || upload.isSuccess}
              >
                <Upload className="w-4 h-4" />
                Upload Dataset
              </Button>
            </div>
          )}

          {/* Rejection messages */}
          {fileRejections.length > 0 && (
            <div className="mt-3 flex items-center gap-2 text-danger text-xs">
              <AlertCircle className="w-3.5 h-3.5 shrink-0" />
              {fileRejections[0].errors[0].message}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Supported formats */}
      <Card>
        <CardContent className="pt-5">
          <p className="text-xs font-medium text-zinc-400 mb-3">Supported formats</p>
          <div className="space-y-2">
            {FORMAT_TIPS.map(({ ext, desc }) => (
              <div key={ext} className="flex items-center gap-3">
                <span className="inline-block w-14 text-center text-2xs font-mono px-1.5 py-0.5 rounded bg-surface-3 border border-surface-4 text-zinc-500 shrink-0">
                  {ext}
                </span>
                <span className="text-xs text-zinc-500">{desc}</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
