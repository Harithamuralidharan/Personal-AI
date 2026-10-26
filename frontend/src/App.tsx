import { useState, type ChangeEvent } from "react";
import "./App.css";

type UploadResult = {
  status: string;
  document_id: string;
  filename: string;
  page_count: number;
  chunk_count: number;
  embedding_dimension: number;
  note: string;
};

const API_BASE = "http://127.0.0.1:8000";

function App() {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<UploadResult | null>(null);

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    setFile(event.target.files?.[0] ?? null);
    setError("");
    setResult(null);
  }

  async function uploadPdf() {
    if (!file) {
      setError("First select a PDF file.");
      return;
    }

    setLoading(true);
    setError("");
    setResult(null);
    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch(`${API_BASE}/upload`, {
        method: "POST",
        body: formData,
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail ?? `Upload failed (${response.status}).`);
      }
      setResult(payload as UploadResult);
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Upload failed. Check that the backend and Ollama are running.",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="page-shell">
      <header className="topbar">
        <div className="brand-mark">W</div>
        <div>
          <h1>Personal AI Workbench</h1>
          <p>Day 1 · Local-first document ingestion</p>
        </div>
        <span className="local-badge">LOCAL DEVELOPMENT</span>
      </header>

      <section className="intro">
        <p className="eyebrow">DOCUMENT KNOWLEDGE BASE</p>
        <h2>Upload a PDF. Save its knowledge locally.</h2>
        <p>
          The backend extracts text page by page, creates 500-token chunks with 50-token overlap,
          generates local embeddings with Ollama, and stores the chunks in PostgreSQL + pgvector.
        </p>
      </section>

      <section className="upload-card">
        <h3>Upload a PDF document</h3>
        <p className="muted">Selectable-text PDFs up to 15 MB. Scanned PDFs need OCR, which is not included yet.</p>
        <label className="file-label" htmlFor="pdf-file">Choose PDF</label>
        <input id="pdf-file" type="file" accept="application/pdf,.pdf" onChange={handleFileChange} />
        {file && <p className="selected-file">Selected: {file.name} · {(file.size / 1024).toFixed(1)} KB</p>}
        <button type="button" onClick={() => void uploadPdf()} disabled={!file || loading}>
          {loading ? "Extracting and embedding…" : "Upload and process"}
        </button>

        {error && <div className="message error" role="alert">{error}</div>}

        {result && (
          <div className="message success" role="status">
            <h4>Document saved successfully</h4>
            <dl>
              <dt>File</dt><dd>{result.filename}</dd>
              <dt>Pages</dt><dd>{result.page_count}</dd>
              <dt>Chunks saved</dt><dd>{result.chunk_count}</dd>
              <dt>Embedding dimensions</dt><dd>{result.embedding_dimension}</dd>
              <dt>Document ID</dt><dd className="document-id">{result.document_id}</dd>
            </dl>
            <p>{result.note}</p>
          </div>
        )}
      </section>

      <section className="steps">
        <h3>What happens after upload?</h3>
        <ol>
          <li>Validate the PDF and extract text from each page.</li>
          <li>Split text into up-to-500-token chunks with a 50-token overlap.</li>
          <li>Generate 768-dimensional embeddings on your laptop through Ollama.</li>
          <li>Save document metadata, page numbers, chunks, and vectors in PostgreSQL.</li>
        </ol>
      </section>
      <footer>Day 1 foundation · No paid LLM or embedding API is used.</footer>
    </main>
  );
}

export default App;
