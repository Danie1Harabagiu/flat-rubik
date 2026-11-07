/* Same-origin assets only. No cube state is sent to a server. */
(() => {
  "use strict";
  const script = new URL(document.currentScript.src);
  const version = script.searchParams.get("v") || "1";
  const workerURL = new URL(`solver-worker.js?v=${version}`, script);
  const jobs = new Map();
  let worker = null;
  let active = null;

  function stopActive() {
    if (active !== null && worker) {
      worker.terminate();
      worker = null;
    }
    active = null;
  }

  function ensureWorker() {
    if (worker) return;
    worker = new Worker(workerURL);
    worker.onmessage = ({ data }) => {
      const job = jobs.get(data.id);
      if (!job) return;
      if (data.type === "candidate") job.candidates.push(data.moves);
      job.status = data.type;
      if (data.detail) job.detail = data.detail;
      if (data.type === "done" || data.type === "error") active = null;
    };
    worker.onerror = (error) => {
      const job = jobs.get(active);
      if (job) {
        job.status = "error";
        job.detail = error.message;
      }
      if (worker) worker.terminate();
      worker = null;
      active = null;
    };
  }

  window.flatRubikSolver = {
    startJson(id, payload) {
      stopActive();
      ensureWorker();
      jobs.set(id, { candidates: [], status: "preparing" });
      active = id;
      worker.postMessage({ id, frames: JSON.parse(payload) });
      return true;
    },
    pollJson(id) {
      const job = jobs.get(id);
      if (!job) return "null";
      const snapshot = JSON.stringify(job);
      job.candidates = [];
      return snapshot;
    },
    cancel(id) {
      if (active === id) stopActive();
      jobs.delete(id);
    }
  };
})();
