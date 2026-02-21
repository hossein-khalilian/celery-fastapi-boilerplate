import { useState, useEffect } from "react";
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

const API_BASE = process.env.NEXT_PUBLIC_API_URL;

export default function Home() {
  // Debug: log API URL on mount
  useEffect(() => {
    console.log("API Base URL:", API_BASE);
  }, []);
  const [text, setText] = useState("");
  const [taskId, setTaskId] = useState(null);
  const [status, setStatus] = useState(null);
  const [progress, setProgress] = useState(null);
  const [result, setResult] = useState(null);

  async function submit(e) {
    e.preventDefault();
    setStatus("PENDING");
    setResult(null);
    setProgress(0); // Initialize to 0 so progress bar shows immediately

    try {
      const res = await fetch(`${API_BASE}/submit`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });

      if (!res.ok) {
        throw new Error(`HTTP error! status: ${res.status}`);
      }

      const body = await res.json();
      setTaskId(body.task_id);
      pollStatus(body.task_id);
    } catch (error) {
      console.error("Error submitting task:", error);
      setStatus("FAILURE");
      setResult({
        error: `Failed to submit task: ${error.message}. Make sure the backend is running at ${API_BASE}`,
      });
    }
  }

  async function pollStatus(id) {
    const url = `${API_BASE}/status/${id}`;
    const iv = setInterval(async () => {
      try {
        const r = await fetch(url);
        if (!r.ok) {
          throw new Error(`HTTP error! status: ${r.status}`);
        }
        const j = await r.json();
        // backend returns `state` and optional `meta` with progress
        setStatus(j.state);

        // Handle progress updates
        if (j.meta) {
          if (typeof j.meta.percent === "number") {
            setProgress(j.meta.percent);
          } else if (j.meta.current && j.meta.total) {
            setProgress(Math.round((j.meta.current / j.meta.total) * 100));
          }
        } else if (j.state === "PENDING") {
          // Keep progress at 0 while pending
          setProgress(0);
        }

        // Handle final states - ensure progress reaches 100% on success
        if (j.state === "SUCCESS") {
          // Set progress to 100% before showing result
          setProgress(100);
          // Small delay to show 100% progress bar before showing result
          setTimeout(() => {
            setResult(j.result);
            clearInterval(iv);
          }, 300);
        } else if (j.state === "FAILURE") {
          setResult({ error: j.error });
          clearInterval(iv);
        }
      } catch (error) {
        console.error("Error polling status:", error);
        setStatus("FAILURE");
        setResult({ error: `Failed to poll status: ${error.message}` });
        clearInterval(iv);
      }
    }, 1000);
  }

  const getStatusVariant = () => {
    switch (status) {
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
      <div className="max-w-4xl mx-auto space-y-6">
        <div className="text-center space-y-2">
          <h1 className="text-4xl font-bold text-slate-900">
            Text Processing Demo
          </h1>
          <p className="text-slate-600">Powered by Celery & FastAPI</p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Submit Text for Processing</CardTitle>
            <CardDescription>
              Enter your text below and it will be processed asynchronously
              using Celery workers
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={submit} className="space-y-4">
              <Textarea
                value={text}
                onChange={(e) => setText(e.target.value)}
                rows={6}
                placeholder="Enter your text here..."
                className="resize-none"
              />
              <Button type="submit" className="w-full" disabled={!text.trim()}>
                Submit for Processing
              </Button>
            </form>
          </CardContent>
        </Card>

        {taskId && (
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Task Status</CardTitle>
                {status && <Badge variant={getStatusVariant()}>{status}</Badge>}
              </div>
              <CardDescription>
                Task ID:{" "}
                <code className="text-xs bg-slate-100 px-2 py-1 rounded">
                  {taskId}
                </code>
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="font-medium">Progress</span>
                  <span className="font-semibold text-primary">
                    {progress !== null ? progress : 0}%
                  </span>
                </div>
                <Progress
                  value={progress !== null ? progress : 0}
                  className="h-3"
                />
                {status === "PENDING" && progress === 0 && (
                  <p className="text-sm text-muted-foreground italic">
                    Waiting for task to start...
                  </p>
                )}
              </div>
            </CardContent>
          </Card>
        )}

        {result && (
          <Card>
            <CardHeader>
              <CardTitle>Processing Result</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {result.elapsed_time !== undefined && (
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-semibold text-blue-900">
                        Total Processing Time
                      </p>
                      <p className="text-sm text-blue-700 mt-1">
                        {result.elapsed_time} seconds
                      </p>
                      <p className="text-xs text-blue-600 mt-1">
                        Includes queue wait time and processing time
                      </p>
                    </div>
                  </div>
                </div>
              )}
              {result.error ? (
                <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                  <p className="text-red-900 font-semibold">Error</p>
                  <p className="text-sm text-red-700 mt-1">{result.error}</p>
                </div>
              ) : (
                <div className="bg-slate-50 rounded-lg p-4 border">
                  <pre className="text-xs overflow-auto">
                    {JSON.stringify(result, null, 2)}
                  </pre>
                </div>
              )}
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
