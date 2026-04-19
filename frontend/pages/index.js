import { useState, useEffect, useRef, useCallback } from "react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";

export default function Home({ apiBaseUrl }) {
  const API_BASE = apiBaseUrl || process.env.NEXT_PUBLIC_API_URL || "";

  const [text, setText] = useState("");
  const [running, setRunning] = useState(false);

  const [pollTaskId, setPollTaskId] = useState(null);
  const [pollStatus, setPollStatus] = useState(null);
  const [pollProgress, setPollProgress] = useState(null);
  const [pollResult, setPollResult] = useState(null);

  const [hookTaskId, setHookTaskId] = useState(null);
  const [hookInboxToken, setHookInboxToken] = useState(null);
  const [hookWebhookUrl, setHookWebhookUrl] = useState(null);
  const [hookStatus, setHookStatus] = useState(null);
  const [hookProgress, setHookProgress] = useState(null);
  const [hookResult, setHookResult] = useState(null);
  const [hookInboxPayload, setHookInboxPayload] = useState(null);

  const pollTimerRef = useRef(null);
  const hookStatusTimerRef = useRef(null);
  const pollDoneRef = useRef(false);
  const hookDoneRef = useRef(false);
  const hookTerminalAtRef = useRef(null);
  const eventSourceRef = useRef(null);

  const finishIfAll = useCallback(() => {
    if (pollDoneRef.current && hookDoneRef.current) setRunning(false);
  }, []);

  useEffect(() => {
    return () => {
      if (pollTimerRef.current) clearInterval(pollTimerRef.current);
      if (hookStatusTimerRef.current) clearInterval(hookStatusTimerRef.current);
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    if (!API_BASE || !hookInboxToken || !running) return;

    const url = `${API_BASE}/webhook/stream/${hookInboxToken}`;
    const es = new EventSource(url);
    eventSourceRef.current = es;

    es.onmessage = (ev) => {
      try {
        const p = JSON.parse(ev.data);
        setHookInboxPayload(p);
        if (p.state) setHookStatus(p.state);
        if (p.state === "SUCCESS") {
          setHookProgress(100);
          setHookResult(p.result);
        } else if (p.state === "FAILURE") {
          setHookResult({ error: p.error });
        }
        es.close();
        eventSourceRef.current = null;
        if (hookStatusTimerRef.current) {
          clearInterval(hookStatusTimerRef.current);
          hookStatusTimerRef.current = null;
        }
        hookDoneRef.current = true;
        finishIfAll();
      } catch (e) {
        console.error(e);
        setHookStatus("FAILURE");
        setHookResult({ error: e.message || "Invalid SSE payload" });
        es.close();
        eventSourceRef.current = null;
        hookDoneRef.current = true;
        finishIfAll();
      }
    };

    es.onerror = () => {
      es.close();
      eventSourceRef.current = null;
    };

    return () => {
      es.close();
      if (eventSourceRef.current === es) eventSourceRef.current = null;
    };
  }, [API_BASE, hookInboxToken, running, finishIfAll]);

  async function runComparison(e) {
    e.preventDefault();
    if (!API_BASE) {
      setPollResult({ error: "Configure NEXT_PUBLIC_API_URL" });
      return;
    }
    if (!text.trim()) return;

    if (pollTimerRef.current) clearInterval(pollTimerRef.current);
    if (hookStatusTimerRef.current) clearInterval(hookStatusTimerRef.current);
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }

    pollDoneRef.current = false;
    hookDoneRef.current = false;
    hookTerminalAtRef.current = null;

    setRunning(true);
    setPollTaskId(null);
    setPollStatus("PENDING");
    setPollProgress(0);
    setPollResult(null);
    setHookTaskId(null);
    setHookInboxToken(null);
    setHookWebhookUrl(null);
    setHookStatus("PENDING");
    setHookProgress(0);
    setHookResult(null);
    setHookInboxPayload(null);

    try {
      const [pollRes, hookRes] = await Promise.all([
        fetch(`${API_BASE}/submit`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text }),
        }),
        fetch(`${API_BASE}/webhook/submit`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text }),
        }),
      ]);

      if (!pollRes.ok) throw new Error(`Polling submit failed: ${pollRes.status}`);
      if (!hookRes.ok) throw new Error(`Webhook submit failed: ${hookRes.status}`);

      const pollBody = await pollRes.json();
      const hookBody = await hookRes.json();

      setPollTaskId(pollBody.task_id);
      setHookTaskId(hookBody.task_id);
      setHookInboxToken(hookBody.inbox_token);
      setHookWebhookUrl(hookBody.webhook_url || null);

      pollTimerRef.current = setInterval(() => {
        pollLoopPoll(pollBody.task_id);
      }, 1000);
      hookStatusTimerRef.current = setInterval(() => {
        hookStatusOnlyPoll(hookBody.task_id);
      }, 1000);

      pollLoopPoll(pollBody.task_id);
      hookStatusOnlyPoll(hookBody.task_id);
    } catch (err) {
      console.error(err);
      setPollStatus("FAILURE");
      setPollResult({ error: err.message });
      setHookStatus("FAILURE");
      setHookResult({ error: err.message });
      pollDoneRef.current = true;
      hookDoneRef.current = true;
      setRunning(false);
    }
  }

  async function pollLoopPoll(id) {
    if (!API_BASE || !id) return;
    try {
      const r = await fetch(`${API_BASE}/status/${id}`);
      if (!r.ok) throw new Error(r.status);
      const j = await r.json();
      setPollStatus(j.state);

      if (j.meta) {
        if (typeof j.meta.percent === "number") setPollProgress(j.meta.percent);
        else if (j.meta.current && j.meta.total)
          setPollProgress(Math.round((j.meta.current / j.meta.total) * 100));
      } else if (j.state === "PENDING") setPollProgress(0);

      if (j.state === "SUCCESS") {
        setPollProgress(100);
        setPollResult(j.result);
        if (pollTimerRef.current) clearInterval(pollTimerRef.current);
        pollDoneRef.current = true;
        finishIfAll();
      } else if (j.state === "FAILURE") {
        setPollResult({ error: j.error });
        if (pollTimerRef.current) clearInterval(pollTimerRef.current);
        pollDoneRef.current = true;
        finishIfAll();
      }
    } catch (e) {
      console.error(e);
      setPollResult({ error: e.message });
      if (pollTimerRef.current) clearInterval(pollTimerRef.current);
      pollDoneRef.current = true;
      finishIfAll();
    }
  }

  async function hookStatusOnlyPoll(taskId) {
    if (!API_BASE || !taskId || hookDoneRef.current) return;
    try {
      const stRes = await fetch(`${API_BASE}/status/${taskId}`);
      if (!stRes.ok) return;
      const j = await stRes.json();
      setHookStatus(j.state);

      if (j.meta) {
        if (typeof j.meta.percent === "number") setHookProgress(j.meta.percent);
        else if (j.meta.current && j.meta.total)
          setHookProgress(Math.round((j.meta.current / j.meta.total) * 100));
      } else if (j.state === "PENDING") setHookProgress(0);

      const terminal = j.state === "SUCCESS" || j.state === "FAILURE";
      if (terminal) {
        if (!hookTerminalAtRef.current) hookTerminalAtRef.current = Date.now();
        else if (Date.now() - hookTerminalAtRef.current > 8000) {
          setHookResult({
            error: `Task finished but SSE did not deliver the webhook payload in time. Worker callback: ${hookWebhookUrl || "unknown"}. Check WEBHOOK_CALLBACK_BASE.`,
          });
          if (hookStatusTimerRef.current) clearInterval(hookStatusTimerRef.current);
          if (eventSourceRef.current) {
            eventSourceRef.current.close();
            eventSourceRef.current = null;
          }
          hookDoneRef.current = true;
          finishIfAll();
        }
      } else {
        hookTerminalAtRef.current = null;
      }
    } catch (e) {
      console.error(e);
    }
  }

  const badgeVariant = (s) => {
    switch (s) {
      case "SUCCESS":
        return "success";
      case "FAILURE":
        return "destructive";
      case "PROGRESS":
        return "default";
      case "PENDING":
        return "warning";
      default:
        return "secondary";
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 py-12 px-4">
      <div className="max-w-6xl mx-auto space-y-6">
        <div className="text-center space-y-2">
          <h1 className="text-4xl font-bold text-slate-900">
            Polling vs webhook + SSE
          </h1>
          <p className="text-slate-600">
            Left: <code className="text-sm">GET /status</code> — Right: Celery → webhook POST →
            backend → <code className="text-sm">EventSource /webhook/stream</code>
          </p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Shared input</CardTitle>
            <CardDescription>
              One run starts both flows with the same text (two tasks).
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={runComparison} className="space-y-4">
              <Textarea
                value={text}
                onChange={(e) => setText(e.target.value)}
                rows={5}
                placeholder="Enter text…"
                className="resize-none"
              />
              <Button type="submit" className="w-full" disabled={!text.trim() || running}>
                {running ? "Running…" : "Run side-by-side comparison"}
              </Button>
            </form>
          </CardContent>
        </Card>

        <div className="grid md:grid-cols-2 gap-6">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between gap-2">
                <CardTitle className="text-lg">Polling</CardTitle>
                {pollStatus && (
                  <Badge variant={badgeVariant(pollStatus)}>{pollStatus}</Badge>
                )}
              </div>
              <CardDescription>
                Progress and result from repeated <code className="text-xs">GET /status</code>
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {pollTaskId && (
                <p className="text-xs text-muted-foreground break-all">
                  task_id: {pollTaskId}
                </p>
              )}
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span>Progress</span>
                  <span>{pollProgress ?? 0}%</span>
                </div>
                <Progress value={pollProgress ?? 0} className="h-3" />
              </div>
              {pollResult && (
                <pre className="text-xs bg-slate-50 border rounded-lg p-3 overflow-auto max-h-64">
                  {JSON.stringify(pollResult, null, 2)}
                </pre>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <div className="flex items-center justify-between gap-2">
                <CardTitle className="text-lg">Webhook + SSE</CardTitle>
                {hookStatus && (
                  <Badge variant={badgeVariant(hookStatus)}>{hookStatus}</Badge>
                )}
              </div>
              <CardDescription>
                Progress from <code className="text-xs">GET /status</code>; completion from the
                worker via <code className="text-xs">POST /webhook/inbox</code> and pushed on{" "}
                <code className="text-xs">GET /webhook/stream</code> (SSE)
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {hookTaskId && (
                <p className="text-xs text-muted-foreground break-all">
                  task_id: {hookTaskId}
                </p>
              )}
              {hookInboxToken && (
                <p className="text-xs text-muted-foreground break-all">
                  inbox_token: {hookInboxToken}
                </p>
              )}
              {hookWebhookUrl && (
                <p className="text-xs text-muted-foreground break-all">
                  callback_url: {hookWebhookUrl}
                </p>
              )}
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span>Progress (Celery state)</span>
                  <span>{hookProgress ?? 0}%</span>
                </div>
                <Progress value={hookProgress ?? 0} className="h-3" />
              </div>
              {hookInboxPayload && (
                <div className="space-y-1">
                  <p className="text-sm font-medium">Webhook payload (via SSE)</p>
                  <pre className="text-xs bg-emerald-50 border border-emerald-100 rounded-lg p-3 overflow-auto max-h-40">
                    {JSON.stringify(hookInboxPayload, null, 2)}
                  </pre>
                </div>
              )}
              {hookResult && (
                <div className="space-y-1">
                  <p className="text-sm font-medium">Result (parsed from webhook)</p>
                  <pre className="text-xs bg-slate-50 border rounded-lg p-3 overflow-auto max-h-64">
                    {JSON.stringify(hookResult, null, 2)}
                  </pre>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

export async function getServerSideProps() {
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || "";
  return { props: { apiBaseUrl } };
}
