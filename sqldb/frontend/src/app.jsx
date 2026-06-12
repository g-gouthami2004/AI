import React, { useState, useRef, useEffect } from "react";

const API_BASE = "http://localhost:8000";

function genId(prefix) {
  return `${prefix}_${Math.random().toString(36).slice(2, 9)}`;
}

export default function App() {
  const [userId] = useState(() => genId("user"));
  const [sessionId] = useState(() => genId("session"));
  const [docReady, setDocReady] = useState(false);
  const [docName, setDocName] = useState("");
  const [uploadStatus, setUploadStatus] = useState(null); // {type, msg}
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  
  const [status, setStatus] = useState({ state: "idle", text: "Ready" });

  const fileInputRef = useRef(null);
  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);
  
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = Math.min(ta.scrollHeight, 120) + "px";
  }, [input]);

  async function handleUpload(file) {
    if (!file?.name.endsWith(".pdf")) {
      setUploadStatus({ type: "error", msg: "Only PDF files are supported." });
      return;
    }
    setUploadStatus({ type: "loading", msg: "⬆ Uploading & indexing…" });
    setStatus({ state: "busy", text: "Indexing document…" });
    setDocReady(false);

    const fd = new FormData();
    fd.append("file", file);
    fd.append("session_id", sessionId);

    try {
      const res = await fetch(`${API_BASE}/upload`, { method: "POST", body: fd });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Upload failed");

      setUploadStatus({ type: "success", msg: `✓ ${data.message}` });
      setDocName(file.name);
      setDocReady(true);
      setStatus({ state: "ready", text: "Ready to chat" });
    } catch (err) {
      setUploadStatus({ type: "error", msg: `✗ ${err.message}` });
      setStatus({ state: "error", text: "Upload failed" });
      setDocReady(false);
    }
  }

  async function sendMessage() {
    const text = input.trim();
    if (!text || !docReady || isSending) return;

    setInput("");
    setMessages(prev => [...prev, { role: "user", text }]);
    setIsSending(true);
    setStatus({ state: "busy", text: "Thinking…" });

    const fd = new FormData();
    fd.append("message", text);
    fd.append("user_id", userId);
    fd.append("session_id", sessionId);

    try {
      const res = await fetch(`${API_BASE}/chat`, { method: "POST", body: fd });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Chat failed");

      setMessages(prev => [...prev, { role: "ai", text: data.response }]);
      setStatus({ state: "ready", text: "Ready to chat" });
    } catch (err) {
      setMessages(prev => [...prev, { role: "ai", text: `⚠ Error: ${err.message}` }]);
      setStatus({ state: "error", text: "Request failed" });
    } finally {
      setIsSending(false);
    }
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }

  const canSend = docReady && !isSending && input.trim() !== "";

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <div>
            <span className="brand-name">Doc</span>
          </div>
        </div>

        <p className="section-label">Document</p>

        <div
          className={`upload-zone ${isDragging ? "drag-over" : ""}`}
          onClick={() => fileInputRef.current.click()}
          onDragOver={e => { e.preventDefault(); setIsDragging(true); }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={e => {
            e.preventDefault();
            setIsDragging(false);
            handleUpload(e.dataTransfer.files[0]);
          }}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf"
            hidden
            onChange={e => handleUpload(e.target.files[0])}
          />
          <div className="upload-icon">
            <svg viewBox="0 0 24 24" fill="none">
              <path d="M12 16V8M12 8l-3 3M12 8l3 3" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/>
              <path d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/>
            </svg>
          </div>
          <p className="upload-primary">Drop PDF here</p>
        </div>
        
        {uploadStatus && (
          <div className={`upload-status ${uploadStatus.type}`}>{uploadStatus.msg}</div>
        )}

        {docReady && (
          <div className="doc-card">
            <div className="doc-icon">
              <svg viewBox="0 0 20 20" fill="none">
                <rect x="3" y="1" width="11" height="15" rx="1.5" stroke="currentColor" strokeWidth="1.4"/>
                <path d="M14 1l3 3v12a1 1 0 01-1 1H7" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/>
                <path d="M6 8h5M6 11h3" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" opacity="0.6"/>
              </svg>
            </div>
            <div className="doc-info">
              <span className="doc-name">{docName}</span>
              <span className="doc-badge">Indexed</span>
            </div>
          </div>
        )}
      </aside>

      {/* ── Chat ── */}
      <main className="chat-area">
        

        <div className="messages">
          {messages.length === 0 && (
            <div className="empty-state">
            </div>
          )}

          {messages.map((msg, i) => (
            <div key={i} className={`message ${msg.role}`}>
              <div className="message-meta">{msg.role === "user" ? "You" : "Doc"}</div>
              <div className="bubble">{msg.text}</div>
            </div>
          ))}

          {isSending && (
            <div className="message ai">
              <div className="message-meta">Doc</div>
              <div className="bubble typing-bubble">
                <div className="typing-dot" />
                <div className="typing-dot" />
                <div className="typing-dot" />
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        <div className="input-row">
          <div className="input-wrap">
            <textarea
              ref={textareaRef}
              className="message-input"
              placeholder="Type here…"
              rows={1}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
            />
            <button className="send-btn" disabled={!canSend} onClick={sendMessage}>
              <svg viewBox="0 0 20 20" fill="none">
                <path d="M3 10l14-7-7 14V10H3z" fill="currentColor"/>
              </svg>
            </button>
          
          </div>
          <button className="clear-btn" onClick={() => setMessages([])}>
            <svg viewBox="0 0 20 20" fill="none">
              <path d="M4 5h12M8 5V4a1 1 0 011-1h2a1 1 0 011 1v1m2 0v10a2 2 0 01-2 2H8a2 2 0 01-2-2V5h10z"
                stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/>
            </svg>
            Clear
          </button>
        </div>
      </main>
    </div>
  );
}
