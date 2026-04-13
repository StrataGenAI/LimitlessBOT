import express from "express";
import { createServer as createViteServer } from "vite";
import path from "path";
import { fileURLToPath } from "url";
import sqlite3 from "sqlite3";
import cors from "cors";
import { spawn, ChildProcess } from "child_process";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

async function startServer() {
  const app = express();
  const PORT = 3000;

  app.use(cors());
  app.use(express.json());

  const dbPath = path.join(__dirname, "bot_data.db");
  const db = new sqlite3.Database(dbPath);

  let botProcess: ChildProcess | null = null;

  // API Routes
  app.get("/api/events", (req, res) => {
    const query = `
      SELECT 
        e.id, 
        e.timestamp, 
        e.source_channel_id as source, 
        e.text as headline, 
        c.direction as classification, 
        c.materiality, 
        c.reasoning, 
        c.latency_ms,
        CASE WHEN t.id IS NOT NULL THEN 1 ELSE 0 END as trade_executed
      FROM events e
      LEFT JOIN classifications c ON e.id = c.event_id
      LEFT JOIN trades t ON c.id = t.classification_id
      ORDER BY e.timestamp DESC 
      LIMIT 50
    `;
    db.all(query, (err, rows) => {
      if (err) {
        res.status(500).json({ error: err.message });
        return;
      }
      res.json(rows);
    });
  });

  app.get("/api/stats", (req, res) => {
    const query = `
      SELECT 
        (SELECT COUNT(*) FROM events) as total,
        (SELECT COUNT(*) FROM trades) as trades,
        (SELECT AVG(latency_ms) FROM classifications) as avg_latency
    `;
    db.get(query, (err, row) => {
      if (err) {
        res.status(500).json({ error: err.message });
        return;
      }
      res.json(row);
    });
  });

  app.post("/api/bot/start", (req, res) => {
    if (botProcess) {
      res.json({ status: "already_running" });
      return;
    }

    const isLive = req.body.live === true;
    const args = ["bot/cli.py", "watch"];
    if (isLive) args.push("--live");

    botProcess = spawn("python3", args, {
      env: { ...process.env, PYTHONPATH: __dirname }
    });

    botProcess.stdout?.on("data", (data) => {
      console.log(`Bot STDOUT: ${data}`);
    });

    botProcess.stderr?.on("data", (data) => {
      console.error(`Bot STDERR: ${data}`);
    });

    botProcess.on("close", (code) => {
      console.log(`Bot process exited with code ${code}`);
      botProcess = null;
    });

    res.json({ status: "started" });
  });

  app.post("/api/bot/stop", (req, res) => {
    if (botProcess) {
      botProcess.kill();
      botProcess = null;
      res.json({ status: "stopped" });
    } else {
      res.json({ status: "not_running" });
    }
  });

  app.post("/api/bot/backtest", (req, res) => {
    if (botProcess) {
      res.status(400).json({ error: "Bot is already running" });
      return;
    }

    const args = ["bot/cli.py", "backtest"];
    const backtestProcess = spawn("python3", args, {
      env: { ...process.env, PYTHONPATH: __dirname }
    });

    backtestProcess.stdout?.on("data", (data) => {
      console.log(`Backtest STDOUT: ${data}`);
    });

    backtestProcess.on("close", (code) => {
      res.json({ status: "completed", code });
    });
  });

  app.get("/api/bot/status", (req, res) => {
    res.json({ running: botProcess !== null });
  });

  // Vite middleware for development
  if (process.env.NODE_ENV !== "production") {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa",
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), "dist");
    app.use(express.static(distPath));
    app.get("*", (req, res) => {
      res.sendFile(path.join(distPath, "index.html"));
    });
  }

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`Server running on http://localhost:${PORT}`);
  });
}

startServer();
