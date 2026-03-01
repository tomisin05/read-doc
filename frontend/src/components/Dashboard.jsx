// src/components/Dashboard.jsx
import { useState, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { logOut, uploadFile } from "../lib/firebase";

const API_BASE = import.meta.env.VITE_API_URL || "/api";

export default function Dashboard({ user }) {
  const [file, setFile] = useState(null);
  const [mode, setMode] = useState(null); // null | 'highlighted' | 'underlined'
  const [stage, setStage] = useState("idle"); // idle | uploading | processing | done | error
  const [downloadUrl, setDownloadUrl] = useState(null);
  const [outputName, setOutputName] = useState("");
  const [errorMsg, setErrorMsg] = useState("");
  const [progress, setProgress] = useState(0);

  const onDrop = useCallback((accepted) => {
    if (accepted.length > 0) {
      setFile(accepted[0]);
      setStage("idle");
      setDownloadUrl(null);
      setErrorMsg("");
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        [".docx"],
    },
    maxFiles: 1,
    maxSize: 20 * 1024 * 1024, // 20MB
  });

  const handleProcess = async () => {
    if (!file) return;
    setStage("uploading");
    setProgress(10);
    setErrorMsg("");
    setDownloadUrl(null);

    try {
      // 1. Upload to Firebase Storage
      const token = await user.getIdToken();
      const { path, name } = await uploadFile(file, user.uid);
      setProgress(40);
      setStage("processing");

      // 2. Call backend to process
      const response = await fetch(`${API_BASE}/api/process`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          storage_path: path,
          filename: name,
          mode: mode,
          user_id: user.uid,
        }),
      });

      setProgress(80);

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || "Processing failed");
      }

      const result = await response.json();
      setProgress(100);
      setDownloadUrl(result.download_url);
      setOutputName(result.output_filename);
      setStage("done");

      // Auto-download
      const link = document.createElement("a");
      link.href = result.download_url;
      link.download = result.output_filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (err) {
      setErrorMsg(err.message || "Something went wrong");
      setStage("error");
    }
  };

  const reset = () => {
    setFile(null);
    setStage("idle");
    setDownloadUrl(null);
    setErrorMsg("");
    setProgress(0);
  };

  const modeOptions = [
    // {
    //   id: 'both',
    //   label: 'Highlighted OR Underlined',
    //   description: 'Keep any run that is highlighted or underlined (most inclusive)',
    //   icon: '◈',
    // },
    {
      id: "highlighted",
      label: "Highlighted",
      description: "Keeps text with a highlight color applied",
      icon: "◉",
    },
    {
      id: "underlined",
      label: "Underlined",
      description: "Keeps underlined text",
      icon: "◈",
    },
  ];

  const isProcessing = stage === "uploading" || stage === "processing";

  return (
    <div className="dashboard">
      {/* Header */}
      <header className="dash-header">
        <div className="dash-brand">
          <img
            src="/logo-horizontal.svg"
            alt="read-doc"
            className="dash-logo-horizontal"
          />
        </div>
        <div className="dash-user">
          <span className="user-email">{user.displayName || user.email}</span>
          <button className="btn-logout" onClick={logOut}>
            Sign out
          </button>
        </div>
      </header>

      <main className="dash-main">
        <div className="dash-intro">
          <h2 className="dash-title">Create your read doc in seconds</h2>
          <p className="dash-desc">
            Upload a Verbatim-formatted .docx file. Choose which formatting to
            preserve, then download your clean, marked-only document.
          </p>
        </div>

        <div className="dash-grid">
          {/* Left: Upload */}
          <div className="panel">
            <div className="panel-label">01 — Upload Document</div>

            {!file ? (
              <div
                {...getRootProps()}
                className={`dropzone ${isDragActive ? "dragover" : ""}`}
              >
                <input {...getInputProps()} />
                <div className="dropzone-icon">
                  <svg
                    width="40"
                    height="40"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.5"
                  >
                    <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
                    <polyline points="17 8 12 3 7 8" />
                    <line x1="12" y1="3" x2="12" y2="15" />
                  </svg>
                </div>
                <p className="dropzone-text">
                  {isDragActive
                    ? "Drop it here"
                    : "Drag & drop your .docx file"}
                </p>
                <p className="dropzone-sub">or click to browse — max 20MB</p>
              </div>
            ) : (
              <div className="file-selected">
                <div className="file-icon">
                  <svg
                    width="28"
                    height="28"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.5"
                  >
                    <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
                    <polyline points="14 2 14 8 20 8" />
                  </svg>
                </div>
                <div className="file-info">
                  <div className="file-name">{file.name}</div>
                  <div className="file-size">
                    {(file.size / 1024).toFixed(1)} KB
                  </div>
                </div>
                {stage !== "processing" && stage !== "uploading" && (
                  <button
                    className="file-remove"
                    onClick={reset}
                    title="Remove"
                  >
                    ✕
                  </button>
                )}
              </div>
            )}
          </div>

          {/* Middle: Mode Selection */}
          <div className="panel">
            <div className="panel-label">02 — Extraction Mode</div>
            <div className="mode-options">
              {modeOptions.map((opt) => (
                <button
                  key={opt.id}
                  className={`mode-option ${mode === opt.id ? "selected" : ""}`}
                  onClick={() => setMode(opt.id)}
                  disabled={isProcessing}
                >
                  <span className="mode-icon">{opt.icon}</span>
                  <div className="mode-text">
                    <div className="mode-label">{opt.label}</div>
                    <div className="mode-desc">{opt.description}</div>
                  </div>
                  <div className="mode-check">{mode === opt.id ? "✓" : ""}</div>
                </button>
              ))}
            </div>
          </div>

          {/* Right: Process & Download */}
          <div className="panel">
            <div className="panel-label">03 — Process & Download</div>

            <div className="action-area">
              {stage === "idle" && (
                <button
                  className="btn-process"
                  onClick={handleProcess}
                  disabled={!file || !mode}
                >
                  <svg
                    width="20"
                    height="20"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                  >
                    <polygon points="5 3 19 12 5 21 5 3" />
                  </svg>
                  Run Extractor
                </button>
              )}

              {!mode && file && stage === "idle" && (
                <p className="mode-required">
                  Please select an extraction mode
                </p>
              )}

              {isProcessing && (
                <div className="processing-state">
                  <div className="progress-ring">
                    <svg viewBox="0 0 60 60" width="80" height="80">
                      <circle
                        cx="30"
                        cy="30"
                        r="24"
                        fill="none"
                        stroke="#1a1a2e"
                        strokeWidth="4"
                      />
                      <circle
                        cx="30"
                        cy="30"
                        r="24"
                        fill="none"
                        stroke="#c8ff00"
                        strokeWidth="4"
                        strokeLinecap="round"
                        strokeDasharray={`${2 * Math.PI * 24}`}
                        strokeDashoffset={`${
                          2 * Math.PI * 24 * (1 - progress / 100)
                        }`}
                        style={{
                          transition: "stroke-dashoffset 0.4s ease",
                          transform: "rotate(-90deg)",
                          transformOrigin: "50% 50%",
                        }}
                      />
                    </svg>
                    <span className="progress-pct">{progress}%</span>
                  </div>
                  <p className="processing-label">
                    {stage === "uploading"
                      ? "Uploading document..."
                      : "Extracting marked text..."}
                  </p>
                </div>
              )}

              {stage === "done" && (
                <div className="done-state">
                  <div className="done-check">✓</div>
                  <p className="done-label">Extraction complete!</p>
                  <a
                    href={downloadUrl}
                    download={outputName}
                    className="btn-download"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    <svg
                      width="18"
                      height="18"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                    >
                      <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
                      <polyline points="7 10 12 15 17 10" />
                      <line x1="12" y1="15" x2="12" y2="3" />
                    </svg>
                    Download {outputName}
                  </a>
                  <button className="btn-again" onClick={reset}>
                    Process another file
                  </button>
                </div>
              )}

              {stage === "error" && (
                <div className="error-state">
                  <div className="error-icon">✕</div>
                  <p className="error-label">Error</p>
                  <p className="error-msg">{errorMsg}</p>
                  <button
                    className="btn-again"
                    onClick={() => setStage("idle")}
                  >
                    Try again
                  </button>
                </div>
              )}

              <div className="action-note">
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <circle cx="12" cy="12" r="10" />
                  <line x1="12" y1="8" x2="12" y2="12" />
                  <line x1="12" y1="16" x2="12.01" y2="16" />
                </svg>
                Tags &amp; cites are always preserved. All uploaded files are
                automatically deleted daily at midnight.
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
