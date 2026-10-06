import React, { FormEvent, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const API = import.meta.env.VITE_API_URL || "/api";

type Project = {
  id: string;
  name: string;
  status: string;
  error?: string;
  goal: { text: string };
  team_plan?: { agents?: Array<{ key: string; role: string }> };
};

type Health = {
  status: string;
  database: boolean;
  ollama: boolean;
  sandbox: boolean;
};

type Detail = {
  project: Project;
  tasks: Array<{ id: string; task_key: string; name: string; status: string; error?: string }>;
  artifacts: Array<{ id: string; name: string; size: number; status: string }>;
  approvals: Array<{ id: string; action: string; risk: string; status: string }>;
};

async function call(path: string, init?: RequestInit) {
  const response = await fetch(`${API}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    ...init,
  });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

function App() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [detail, setDetail] = useState<Detail | null>(null);
  const [health, setHealth] = useState<Health | null>(null);
  const [error, setError] = useState("");

  const refresh = async () => {
    const [data, healthData] = await Promise.all([call("/projects"), call("/system/health")]);
    setProjects(data.items);
    setHealth(healthData);
    if (detail) setDetail(await call(`/projects/${detail.project.id}`));
  };

  useEffect(() => {
    refresh().catch((reason) => setError(String(reason)));
    const timer = window.setInterval(() => refresh().catch(() => undefined), 3000);
    return () => window.clearInterval(timer);
  }, [detail?.project.id]);

  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    try {
      const data = await call("/projects", {
        method: "POST",
        body: JSON.stringify({ name: form.get("name"), goal: form.get("goal") }),
      });
      formElement.reset();
      setDetail(await call(`/projects/${data.project.id}`));
      await refresh();
    } catch (reason) {
      setError(String(reason));
    }
  }

  async function decide(id: string, approved: boolean) {
    await call(`/approvals/${id}/${approved ? "approve" : "reject"}`, {
      method: "POST",
      body: JSON.stringify({ comment: approved ? "Approved in dashboard" : "Rejected in dashboard" }),
    });
    await refresh();
  }

  async function retry(projectId: string) {
    setError("");
    try {
      await call(`/projects/${projectId}/start`, { method: "POST" });
      await refresh();
    } catch (reason) {
      setError(String(reason));
    }
  }

  return (
    <main>
      <header>
        <p className="eyebrow">LOCAL AI DELIVERY CONTROL PLANE</p>
        <h1>Agent Orchestrator</h1>
        <p>Turn an objective into a governed plan, reviewed work, and inspectable artifacts.</p>
      </header>

      {error && <div className="error">{error}</div>}
      {health && !health.ollama && <div className="error">Ollama is unavailable. New and retried projects cannot run until the configured remote Ollama server is reachable.</div>}

      <section className="panel">
        <h2>Start a project</h2>
        <form onSubmit={create}>
          <input name="name" minLength={3} placeholder="Project name" required />
          <textarea name="goal" minLength={10} placeholder="Describe the outcome you want…" required />
          <button type="submit" disabled={health?.ollama === false}>Assemble team and execute</button>
        </form>
      </section>

      <div className="layout">
        <section className="panel projects">
          <h2>Projects</h2>
          {projects.map((project) => (
            <button className="project" key={project.id} onClick={async () => setDetail(await call(`/projects/${project.id}`))}>
              <span>{project.name}</span><strong data-status={project.status}>{project.status}</strong>
            </button>
          ))}
        </section>

        <section className="panel detail">
          {!detail ? <p>Select a project to inspect it.</p> : <>
            <div className="title-row"><h2>{detail.project.name}</h2><strong>{detail.project.status}</strong></div>
            <p>{detail.project.goal.text}</p>
            {detail.project.error && <div className="error">{detail.project.error}</div>}
            {detail.project.status === "failed" && <button onClick={() => retry(detail.project.id)} disabled={health?.ollama === false}>Retry project</button>}
            <h3>Team</h3>
            <div className="chips">{detail.project.team_plan?.agents?.map((agent) => <span key={agent.key}>{agent.role}</span>) || "Planning…"}</div>
            <h3>Tasks</h3>
            <ol>{detail.tasks.map((task) => <li key={task.id}><div><b>{task.name}</b><small>{task.task_key}</small></div><strong>{task.status}</strong>{task.error && <p className="error-text">{task.error}</p>}</li>)}</ol>
            {detail.approvals.filter((item) => item.status === "pending").map((approval) => <div className="approval" key={approval.id}><b>Approval required: {approval.action}</b><p>{approval.risk}</p><button onClick={() => decide(approval.id, true)}>Approve</button><button className="secondary" onClick={() => decide(approval.id, false)}>Reject</button></div>)}
            <h3>Artifacts</h3>
            <ul>{detail.artifacts.map((artifact) => <li key={artifact.id}><a href={`${API}/artifacts/${artifact.id}/download`}>{artifact.name}</a> · {artifact.size} bytes</li>)}</ul>
          </>}
        </section>
      </div>
    </main>
  );
}

createRoot(document.getElementById("root")!).render(<React.StrictMode><App /></React.StrictMode>);
