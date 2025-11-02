#!/usr/bin/env node
/**
 * Minimal static file server for Playwright tests.
 */

const { createServer } = require("node:http");
const { stat, readFile } = require("node:fs/promises");
const path = require("node:path");

const rootDir = path.resolve(__dirname, "..");
const port = Number(process.env.PORT || 4173);
const host = process.env.HOST || "127.0.0.1";

const mimeTypes = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "application/javascript; charset=utf-8",
  ".mjs": "application/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".db": "application/octet-stream",
  ".wasm": "application/wasm",
  ".ico": "image/x-icon",
  ".png": "image/png",
  ".svg": "image/svg+xml",
  ".txt": "text/plain; charset=utf-8",
};

function resolvePath(urlPath) {
  const decoded = decodeURIComponent(urlPath.split("?")[0]);
  const relativePath = decoded === "/" ? "/index.html" : decoded;
  const fullPath = path.resolve(rootDir, `.${relativePath}`);

  if (!fullPath.startsWith(rootDir)) {
    return null;
  }

  return fullPath;
}

const server = createServer(async (req, res) => {
  if (!req.url) {
    res.statusCode = 400;
    res.end("Bad Request");
    return;
  }

  const filePath = resolvePath(req.url);
  if (!filePath) {
    res.statusCode = 403;
    res.end("Forbidden");
    return;
  }

  try {
    const fileStat = await stat(filePath);
    if (fileStat.isDirectory()) {
      res.statusCode = 403;
      res.end("Forbidden");
      return;
    }

    const ext = path.extname(filePath).toLowerCase();
    const mimeType = mimeTypes[ext] || "application/octet-stream";

    const buffer = await readFile(filePath);
    res.statusCode = 200;
    res.setHeader("Content-Type", mimeType);
    res.setHeader("Content-Length", buffer.byteLength);
    res.end(buffer);
  } catch {
    res.statusCode = 404;
    res.end("Not Found");
  }
});

server.listen(port, host, () => {
  process.stdout.write(`Static server listening on http://${host}:${port}\n`);
});

process.on("SIGTERM", () => {
  server.close(() => process.exit(0));
});
