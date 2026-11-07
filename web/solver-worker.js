/* Local cube.js worker. It proposes solutions; Python verifies and proves QTM. */
"use strict";
const version = new URL(self.location.href).searchParams.get("v") || "1";
importScripts(`cube-core.js?v=${version}`, `cube-solve.js?v=${version}`);
let ready = false;
self.onmessage = (event) => {
  const { id, frames } = event.data;
  try {
    if (!ready) {
      self.postMessage({ id, type: "preparing" });
      Cube.initSolver();
      ready = true;
    }
    for (const frame of frames) {
      const cube = Cube.fromString(frame.facelets);
      const algorithm = cube.solve(22);
      if (!cube.clone().move(algorithm).isSolved()) throw new Error("Invalid solution");
      const moves = algorithm.trim() ? algorithm.trim().split(/\s+/).map(move => frame.back[move[0]] + move.slice(1)) : [];
      self.postMessage({ id, type: "candidate", moves });
    }
    self.postMessage({ id, type: "done" });
  } catch (error) {
    self.postMessage({ id, type: "error", detail: String(error) });
  }
};
