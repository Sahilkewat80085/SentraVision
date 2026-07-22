import { useEffect, useMemo, useState } from "react";
import { getRoi, getStatus, uploadVideo } from "./api";

// ── Shared UI Icons ──────────────────────────────────────────────────
const UploadIcon = () => (
  <svg className="h-10 w-10 text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
  </svg>
);

const DetectionIcon = () => (
  <svg className="mx-auto h-8 w-8 text-slate-700" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
  </svg>
);

// ── Subcomponents ────────────────────────────────────────────────────
function VideoPreview({ status, videoUrl, backendError, videoId, jobId }) {
  return (
    <article className="md:col-span-2 rounded-2xl border border-slate-800/80 bg-slate-900/30 backdrop-blur-xl p-6 shadow-2xl flex flex-col justify-between">
      <div>
        <h2 className="text-lg font-bold tracking-tight text-slate-200 mb-4">Processed Video</h2>
        <div className="relative aspect-video w-full rounded-xl overflow-hidden bg-slate-950 border border-slate-800/60 flex items-center justify-center">
          {status === "COMPLETED" ? (
            <video className="w-full h-full object-contain" controls src={videoUrl} />
          ) : (
            <div className="p-8 text-center max-w-sm">
              {status === "PROCESSING" ? (
                <div className="flex flex-col items-center gap-4">
                  <span className="animate-spin h-10 w-10 border-4 border-brand-500 border-t-transparent rounded-full" />
                  <p className="text-sm font-semibold text-brand-500 tracking-wide">Processing video...</p>
                  <p className="text-xs text-slate-400">MediaPipe is mapping face frames</p>
                </div>
              ) : status === "PENDING" ? (
                <div className="flex flex-col items-center gap-3">
                  <div className="h-2 w-24 bg-slate-800 rounded-full overflow-hidden">
                    <div className="h-full bg-brand-500 animate-pulse w-2/3" />
                  </div>
                  <p className="text-xs text-slate-400">Waiting for worker pick-up...</p>
                </div>
              ) : (
                <div className="flex flex-col items-center gap-3">
                  <UploadIcon />
                  <p className="text-xs text-slate-500 leading-relaxed">
                    Your processed output video containing drawn bounding boxes will display here once uploaded.
                  </p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {videoId && (
        <div className="mt-6 border-t border-slate-900 pt-5 text-xs text-slate-400 font-mono grid grid-cols-2 gap-4">
          <div>
            <span className="text-slate-500">Video ID</span>
            <p className="text-slate-300 font-semibold truncate mt-0.5">{videoId}</p>
          </div>
          <div>
            <span className="text-slate-500">Celery Task ID</span>
            <p className="text-slate-300 font-semibold truncate mt-0.5">{jobId}</p>
          </div>
          <div>
            <span className="text-slate-500">Processing Status</span>
            <p className={`font-semibold mt-0.5 ${status === "COMPLETED" ? "text-brand-500" : status === "FAILED" ? "text-red-400" : "text-amber-400"}`}>
              {status}
            </p>
          </div>
          {backendError && (
            <div className="col-span-2 mt-2 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 break-words font-sans">
              <strong>Error:</strong> {backendError}
            </div>
          )}
        </div>
      )}
    </article>
  );
}

function App() {
  const [file, setFile] = useState(null);
  const [videoId, setVideoId] = useState("");
  const [jobId, setJobId] = useState("");
  const [status, setStatus] = useState("IDLE");
  const [roi, setRoi] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [backendError, setBackendError] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize] = useState(8); // Compact list height
  const [totalCount, setTotalCount] = useState(0);

  const videoUrl = useMemo(() => (videoId ? `/api/video/${videoId}` : ""), [videoId]);
  const totalPages = Math.ceil(totalCount / pageSize);

  // Status Polling Effect
  useEffect(() => {
    if (!videoId || status === "COMPLETED" || status === "FAILED") return;
    const timer = setInterval(async () => {
      try {
        const s = await getStatus(videoId);
        setStatus(s.status);
        if (s.status === "FAILED") {
          setBackendError(s.error_message || "Unknown processing error");
        }
      } catch (err) {
        console.error("Poller status update failure:", err);
      }
    }, 2500);
    return () => clearInterval(timer);
  }, [videoId, status]);

  // Paginated ROI Loading Effect
  useEffect(() => {
    if (status !== "COMPLETED" || !videoId) return;
    let active = true;
    const loadRoi = async () => {
      try {
        const data = await getRoi(videoId, page, pageSize);
        if (active) {
          setRoi(data.roi_data || []);
          setTotalCount(data.total_count || 0);
        }
      } catch (err) {
        console.error("Failed to fetch ROI details", err);
      }
    };
    loadRoi();
    return () => {
      active = false;
    };
  }, [videoId, status, page, pageSize]);

  const onSubmit = async (e) => {
    e.preventDefault();
    if (!file) return;
    setLoading(true);
    setError("");
    setRoi([]);
    setPage(1);
    setTotalCount(0);
    setBackendError("");
    try {
      const data = await uploadVideo(file);
      setVideoId(data.video_id);
      setJobId(data.job_id);
      setStatus(data.status);
    } catch (err) {
      setError(err?.message || "Upload failed");
    } finally {
      setLoading(false);
    }
  };

  const handlePrevPage = () => {
    setPage((prev) => Math.max(1, prev - 1));
  };

  const handleNextPage = () => {
    setPage((prev) => Math.min(totalPages, prev + 1));
  };

  return (
    <main className="min-h-screen bg-slate-950 bg-radial-gradient text-slate-100 font-sans selection:bg-brand-500 selection:text-slate-950">
      <div className="mx-auto max-w-6xl px-6 py-12">
        {/* Header */}
        <header className="flex flex-col md:flex-row md:items-center md:justify-between border-b border-slate-900 pb-8">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-4xl font-extrabold tracking-tight bg-gradient-to-r from-brand-500 to-emerald-300 bg-clip-text text-transparent">
                SentraVision
              </h1>
              {status === "PROCESSING" && (
                <span className="flex h-3 w-3 relative">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
                </span>
              )}
            </div>
            <p className="mt-2 text-slate-400 max-w-xl text-sm leading-relaxed">
              Distributed asynchronous video pipeline with real-time face ROI extraction, built on FastAPI, Celery, and MediaPipe.
            </p>
          </div>
          <div className="mt-4 md:mt-0 flex gap-2">
            <span className="rounded-full bg-slate-900 px-4 py-1.5 text-xs font-mono text-slate-400 border border-slate-800">
              v1.0.0
            </span>
          </div>
        </header>

        {/* Upload Form */}
        <form
          className="mt-8 rounded-2xl border border-slate-800/80 bg-slate-900/30 backdrop-blur-xl p-6 shadow-2xl transition-all hover:border-slate-700/50"
          onSubmit={onSubmit}
        >
          <div className="flex flex-col sm:flex-row items-center gap-4">
            <label className="flex-1 w-full flex items-center justify-between border border-dashed border-slate-700/60 rounded-xl px-4 py-3 cursor-pointer hover:border-brand-500/60 transition-colors">
              <span className="text-sm text-slate-400 truncate">
                {file ? file.name : "Select video file (.mp4, .mov, etc.)"}
              </span>
              <input
                type="file"
                accept="video/*"
                className="hidden"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              />
              <span className="text-xs bg-slate-800 text-slate-200 px-3 py-1 rounded-md font-semibold hover:bg-slate-700">
                Browse
              </span>
            </label>
            <button
              className="w-full sm:w-auto rounded-xl bg-brand-500 px-6 py-3 font-semibold text-slate-950 transition-all hover:bg-emerald-400 active:scale-95 disabled:opacity-40 disabled:pointer-events-none shadow-lg shadow-brand-500/10"
              disabled={!file || loading}
            >
              {loading ? (
                <span className="flex items-center gap-2">
                  <span className="animate-spin h-4 w-4 border-2 border-slate-950 border-t-transparent rounded-full" />
                  Uploading...
                </span>
              ) : (
                "Upload & Process"
              )}
            </button>
          </div>
          {error && (
            <div className="mt-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-xs text-red-400 font-medium">
              {error}
            </div>
          )}
        </form>

        {/* Main Workspace */}
        <section className="mt-8 grid gap-8 md:grid-cols-3">
          {/* Video Preview Card */}
          <VideoPreview
            status={status}
            videoUrl={videoUrl}
            backendError={backendError}
            videoId={videoId}
            jobId={jobId}
          />

          {/* ROI Metadata Card */}
          <article className="rounded-2xl border border-slate-800/80 bg-slate-900/30 backdrop-blur-xl p-6 shadow-2xl flex flex-col justify-between min-h-[460px]">
            <div>
              <h2 className="text-lg font-bold tracking-tight text-slate-200 mb-4">ROI Detections</h2>

              <div className="space-y-3">
                {roi.length === 0 ? (
                  <div className="text-center py-12">
                    <DetectionIcon />
                    <p className="mt-3 text-xs text-slate-500">
                      No coordinates extracted yet. Start a job to run face detection.
                    </p>
                  </div>
                ) : (
                  roi.map((row) => (
                    <div
                      key={row.id}
                      className="group rounded-xl border border-slate-800/60 bg-slate-950/40 p-3 shadow-inner hover:border-slate-700/40 transition-colors"
                    >
                      <div className="flex justify-between items-center text-xs border-b border-slate-900 pb-1.5 mb-1.5 font-mono text-slate-400">
                        <span>Frame #{row.frame_number}</span>
                        <span className="text-brand-500 font-semibold">{(row.confidence * 100).toFixed(1)}% conf</span>
                      </div>
                      <div className="grid grid-cols-2 text-xs font-mono text-slate-400 gap-y-0.5">
                        <div>
                          <span className="text-slate-600">Time:</span> {row.timestamp.toFixed(2)}s
                        </div>
                        <div>
                          <span className="text-slate-600">Pos:</span> ({row.x}, {row.y})
                        </div>
                        <div className="col-span-2">
                          <span className="text-slate-600">Size:</span> {row.width}px x {row.height}px
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Pagination Controls */}
            {totalPages > 1 && (
              <div className="mt-6 border-t border-slate-900 pt-5 flex items-center justify-between text-xs">
                <button
                  type="button"
                  onClick={handlePrevPage}
                  disabled={page === 1}
                  className="px-3 py-1.5 bg-slate-950 border border-slate-800 text-slate-300 rounded-lg hover:bg-slate-900 disabled:opacity-30 disabled:pointer-events-none select-none transition-colors"
                >
                  Prev
                </button>
                <span className="text-slate-400 font-mono">
                  Page {page} / {totalPages}
                </span>
                <button
                  type="button"
                  onClick={handleNextPage}
                  disabled={page === totalPages}
                  className="px-3 py-1.5 bg-slate-950 border border-slate-800 text-slate-300 rounded-lg hover:bg-slate-900 disabled:opacity-30 disabled:pointer-events-none select-none transition-colors"
                >
                  Next
                </button>
              </div>
            )}
          </article>
        </section>
      </div>
    </main>
  );
}

export default App;

