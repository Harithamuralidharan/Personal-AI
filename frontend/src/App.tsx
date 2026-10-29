
import { useState, type ChangeEvent, type FormEvent } from "react";
import "./App.css";

type UploadResult = {
  status: string;
  document_name?: string;
  filename: string;
  page_count: number;
  chunk_count: number;
  embedding_dimension: number;
  note: string;
};

type Source = {
  filename: string;
  page_number: number;
};

type AskResult = {
  question: string;
  document_name: string;
  answer: string;
  sources: Source[];
  retrieved_chunks: number;
};

type ChatMessage = {
  question: string;
  answer: string;
  sources: Source[];
};

const API_BASE = "http://127.0.0.1:8000";

function App() {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<UploadResult | null>(null);

  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);
  const [askError, setAskError] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    setFile(event.target.files?.[0] ?? null);
    setError("");
    setAskError("");
    setResult(null);
    setMessages([]);
  }

  async function uploadPdf() {
    if (!file) {
      setError("First select a PDF file.");
      return;
    }

    setLoading(true);
    setError("");
    setAskError("");
    setResult(null);
    setMessages([]);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch(`${API_BASE}/upload`, {
        method: "POST",
        body: formData,
      });

      const payload = await response.json();

      if (!response.ok) {
        throw new Error(
          payload.detail ?? `Upload failed (${response.status}).`,
        );
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

  async function askQuestion(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const cleanQuestion = question.trim();

    if (!result) {
      setAskError("Please upload and process a PDF first.");
      return;
    }

    if (!cleanQuestion) {
      setAskError("Please enter a question.");
      return;
    }

    const documentName = result.document_name ?? result.filename;

    setAsking(true);
    setAskError("");

    try {
      const response = await fetch(`${API_BASE}/ask`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          question: cleanQuestion,
          top_k: 5,
          document_name: documentName,
        }),
      });

      const payload = await response.json();

      if (!response.ok) {
        throw new Error(
          payload.detail ?? `Question failed (${response.status}).`,
        );
      }

      const data = payload as AskResult;

      setMessages((previous) => [
        ...previous,
        {
          question: data.question,
          answer: data.answer,
          sources: data.sources,
        },
      ]);

      setQuestion("");
    } catch (caught) {
      setAskError(
        caught instanceof Error
          ? caught.message
          : "Could not get an answer. Check that the backend and Ollama are running.",
      );
    } finally {
      setAsking(false);
    }
  }

  return (
    <main className="page-shell">
      <header className="topbar">
        <div className="brand-mark">W</div>
        <div>
          <h1>Personal AI Workbench</h1>
          <p>Local-first document intelligence</p>
        </div>
        <span className="local-badge">LOCAL DEVELOPMENT</span>
      </header>

      <section className="intro">
        <p className="eyebrow">DOCUMENT KNOWLEDGE BASE</p>
        <h2>Upload a PDF. Ask questions. Get answers.</h2>
        <p>
          Your documents are processed locally using Ollama embeddings,
          PostgreSQL, pgvector, and a local language model.
        </p>
      </section>

      <section className="upload-card">
        <h3>1. Upload a PDF document</h3>
        <p className="muted">
          Selectable-text PDFs up to 15 MB. Scanned PDFs need OCR, which is
          not included yet.
        </p>

        <label className="file-label" htmlFor="pdf-file">
          Choose PDF
        </label>

        <input
          id="pdf-file"
          type="file"
          accept="application/pdf,.pdf"
          onChange={handleFileChange}
          disabled={loading || asking}
        />

        {file && (
          <p className="selected-file">
            Selected: {file.name} · {(file.size / 1024).toFixed(1)} KB
          </p>
        )}

        <button
          type="button"
          onClick={() => void uploadPdf()}
          disabled={!file || loading || asking}
        >
          {loading ? "Extracting and embedding…" : "Upload and process"}
        </button>

        {error && (
          <div className="message error" role="alert">
            {error}
          </div>
        )}

        {result && (
          <div className="message success" role="status">
            <h4>Document saved successfully</h4>
            <dl>
              <dt>Selected document</dt>
              <dd>{result.filename}</dd>
              <dt>Pages</dt>
              <dd>{result.page_count}</dd>
              <dt>Chunks saved</dt>
              <dd>{result.chunk_count}</dd>
              <dt>Embedding dimensions</dt>
              <dd>{result.embedding_dimension}</dd>
            </dl>
            <p>{result.note}</p>
          </div>
        )}
      </section>

      <section className="upload-card chat-card">
        <h3>2. Ask your document</h3>
        <p className="muted">
          {result
            ? `Questions will be searched in: ${result.filename}`
            : "Upload and process a PDF before asking questions."}
        </p>

        <form onSubmit={askQuestion} className="chat-form">
          <label htmlFor="question">Your question</label>
          <textarea
            id="question"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="Example: What is the main topic of this document?"
            rows={3}
            maxLength={2000}
            disabled={!result || asking}
          />

          <button
            type="submit"
            disabled={!result || asking || !question.trim()}
          >
            {asking ? "Thinking…" : "Ask AI"}
          </button>
        </form>

        {asking && (
          <p className="muted" role="status">
            Searching the selected PDF and generating an answer locally…
          </p>
        )}

        {askError && (
          <div className="message error" role="alert">
            {askError}
          </div>
        )}

        <div className="chat-history" aria-live="polite">
          {messages.map((message, index) => (
            <article
              className="answer-card"
              key={`${index}-${message.question}`}
            >
              <h4>Your question</h4>
              <p>{message.question}</p>

              <h4>AI answer</h4>
              <p className="answer-text">{message.answer}</p>

              {message.sources.length > 0 && (
                <div className="source-list">
                  <h4>Sources</h4>
                  <ul>
                    {message.sources.map((source, sourceIndex) => (
                      <li
                        key={`${source.filename}-${source.page_number}-${sourceIndex}`}
                      >
                        {source.filename} — Page {source.page_number}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </article>
          ))}
        </div>

        {messages.length === 0 && (
          <p className="muted empty-chat">
            Your questions and answers will appear here.
          </p>
        )}
      </section>

      <section className="steps">
        <h3>How it works</h3>
        <ol>
          <li>Extract text from each PDF page.</li>
          <li>Split text into chunks and generate local embeddings.</li>
          <li>Store document chunks and vectors in PostgreSQL + pgvector.</li>
          <li>Retrieve relevant chunks from the selected PDF.</li>
          <li>Generate an answer using the local LLM and show source pages.</li>
        </ol>
      </section>

      <footer>Local-first AI · No paid LLM or embedding API is used.</footer>
    </main>
  );
}

export default App;
