import { useEffect, useMemo, useState } from "react";
import { getRoi, getStatus, uploadVideo } from "./api";

function App() {
  const [file, setFile] = useState(null);
  const [videoId, setVideoId] = useState("");
  const [jobId, setJobId] = useState("");
  const [status, setStatus] = useState("IDLE");
  const [roi, setRoi] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const videoUrl = useMemo(() => (videoId ? `/api/video/${videoId}` : ""), [videoId]);

  useEffect(() => {
    if (!videoId || status === "COMPLETED" || status === "FAILED") return;
    const timer = setInterval(async () => {
      try {
        const s = await getStatus(videoId);
        setStatus(s.status);
        if (s.status === "COMPLETED") {
          const roiData = await getRoi(videoId);
          setRoi(roiData.roi_data || []);
        }
      } catch (_) {}
    }, 2500);
    return () => clearInterval(timer);
  }, [videoId, status]);

  const onSubmit = async (e) => {
    e.preventDefault();
    if (!file) return;
    setLoading(true);
    setError("");
    setRoi([]);
    try {
      const data = await uploadVideo(file);
      setVideoId(data.video_id);
      setJobId(data.job_id);
      setStatus(data.status);
    } catch (err) {
      setError(err?.response?.data?.detail || "Upload failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <div className="mx-auto max-w-6xl px-4 py-8">
        <h1 className="text-3xl font-semibold tracking-tight">SentraVision</h1>
        <p className="mt-2 text-slate-300">Distributed video face ROI pipeline powered by FastAPI + Celery + MediaPipe.</p>

        <form className="mt-6 rounded-xl border border-slate-800 bg-slate-900 p-4" onSubmit={onSubmit}>
          <input type="file" accept="video/*" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
          <button className="ml-4 rounded bg-brand-500 px-4 py-2 font-medium text-slate-950 disabled:opacity-40" disabled={!file || loading}>
            {loading ? "Uploading..." : "Upload Video"}
          </button>
          {error && <p className="mt-3 text-red-400">{error}</p>}
        </form>

        <section className="mt-6 grid gap-6 md:grid-cols-3">
          <article className="md:col-span-2 rounded-xl border border-slate-800 bg-slate-900 p-4">
            <h2 className="mb-3 text-xl font-medium">Processed Video</h2>
            {status === "COMPLETED" ? (
              <video className="w-full rounded-lg" controls src={videoUrl} />
            ) : (
              <div className="rounded-lg border border-dashed border-slate-700 p-10 text-center text-slate-400">
                {videoId ? `Current status: ${status}` : "Upload a video to start processing"}
              </div>
            )}
            {videoId && (
              <div className="mt-3 text-sm text-slate-300">
                <p>Video ID: {videoId}</p>
                <p>Job ID: {jobId}</p>
                <p>Status: {status}</p>
              </div>
            )}
          </article>

          <article className="rounded-xl border border-slate-800 bg-slate-900 p-4">
            <h2 className="mb-3 text-xl font-medium">ROI Metadata</h2>
            <div className="max-h-[420px] overflow-auto text-sm">
              {roi.length === 0 ? (
                <p className="text-slate-400">ROI will appear once processing completes.</p>
              ) : (
                roi.slice(0, 120).map((row) => (
                  <div key={row.id} className="mb-2 rounded border border-slate-800 p-2">
                    <p>frame: {row.frame_number}</p>
                    <p>t: {row.timestamp}s</p>
                    <p>box: ({row.x}, {row.y}, {row.width}, {row.height})</p>
                    <p>conf: {row.confidence}</p>
                  </div>
                ))
              )}
            </div>
          </article>
        </section>
      </div>
    </main>
  );
}

export default App;
