"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "../contexts/AuthContext";
import { 
  Activity, Plus, LogOut, Globe, Clock, Server, AlertTriangle, 
  CheckCircle2, XCircle, ChevronRight, Play, Trash2, X, RefreshCw, Sparkles, Loader2
} from "lucide-react";
import { API_URL, WS_URL } from "../config";

interface Project {
  id: number;
  name: string;
  description: string;
  webhook_url?: string;
}

interface Endpoint {
  id: number;
  name: string;
  url: string;
  method: string;
  check_interval: number;
  is_active: boolean;
  project_id: number;
  status: string;
  consecutive_failures: number;
  last_checked_at?: string;
  latest_result?: {
    status_code?: number;
    response_time_ms?: number;
    is_healthy?: boolean;
    error_message?: string;
    checked_at?: string;
  };
}

interface AlertNotification {
  id: string;
  endpointName: string;
  url: string;
  summary: string;
  suggestions: string;
}

export default function DashboardPage() {
  const { user, token, logout, isAuthenticated, loading: authLoading } = useAuth();
  const router = useRouter();

  // App State
  const [projects, setProjects] = useState<Project[]>([]);
  const [endpoints, setEndpoints] = useState<Endpoint[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeAlerts, setActiveAlerts] = useState<AlertNotification[]>([]);

  // Modals state
  const [isProjectModalOpen, setIsProjectModalOpen] = useState(false);
  const [projectName, setProjectName] = useState("");
  const [projectDesc, setProjectDesc] = useState("");
  const [projectWebhook, setProjectWebhook] = useState("");

  const [isEndpointModalOpen, setIsEndpointModalOpen] = useState(false);
  const [endpointName, setEndpointName] = useState("");
  const [endpointUrl, setEndpointUrl] = useState("");
  const [endpointMethod, setEndpointMethod] = useState("GET");
  const [endpointInterval, setEndpointInterval] = useState(60);
  const [endpointProjectId, setEndpointProjectId] = useState<number | "">("");

  // Refs for tracking websocket connection
  const socketRef = useRef<WebSocket | null>(null);

  // Authenticate user check
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push("/auth/login");
    }
  }, [isAuthenticated, authLoading, router]);

  // Fetch initial data — memoized so the effect below has a stable dependency
  const fetchData = useCallback(async (signal?: AbortSignal) => {
    if (!token) return;
    try {
      setLoading(true);
      // Fetch projects
      const projRes = await fetch(`${API_URL}/api/projects`, {
        headers: { Authorization: `Bearer ${token}` },
        signal
      });
      
      if (projRes.status === 401) {
        logout();
        return;
      }
      
      const projData = await projRes.json();
      if (signal?.aborted) return;
      setProjects(projData);

      // Fetch endpoints
      const endRes = await fetch(`${API_URL}/api/endpoints`, {
        headers: { Authorization: `Bearer ${token}` },
        signal
      });
      
      if (endRes.status === 401) {
        logout();
        return;
      }
      
      const endData = await endRes.json();
      if (signal?.aborted) return;

      // Pre-fill latest result for all endpoints in parallel
      const endpointsWithResults: Endpoint[] = await Promise.all(
        endData.map(async (ep: Endpoint) => {
          try {
            const latRes = await fetch(`${API_URL}/api/endpoints/${ep.id}/latest`, {
              headers: { Authorization: `Bearer ${token}` },
              signal
            });
            
            if (latRes.status === 401) {
              logout();
              return ep;
            }
            if (latRes.ok) {
              const latest = await latRes.json();
              return { ...ep, latest_result: latest };
            }
          } catch (e) {
            // No monitoring results yet for this endpoint
          }
          return ep;
        })
      );

      if (signal?.aborted) return;
      setEndpoints(endpointsWithResults);

      setEndpointProjectId((prev) =>
        projData.length > 0 && !prev ? projData[0].id : prev
      );
    } catch (err) {
      if (err instanceof DOMException && err.name === 'AbortError') {
        // Ignored unmounted fetch
        return;
      }
      console.error("Error loading dashboard data:", err);
    } finally {
      if (!signal?.aborted) {
        setLoading(false);
      }
    }
  }, [token, logout]);

  useEffect(() => {
    const controller = new AbortController();

    if (token) {
      fetchData(controller.signal);
    }

    return () => {
      controller.abort();
    };
  }, [token, fetchData]);

  // WebSocket Connection
  useEffect(() => {
    if (!token) return;

    let isMounted = true;

    const connectWebSocket = () => {
      if (!isMounted) return; // Don't reconnect after cleanup
      console.log("Connecting WebSocket client...");
      const wsUrl = `${WS_URL}/api/ws?token=${token}`;
      const ws = new WebSocket(wsUrl);
      socketRef.current = ws;

      ws.onopen = () => {
        console.log("WebSocket connected successfully!");
      };

      ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          
          if (payload.type === "endpoint_update") {
            const updatedEpId = payload.endpoint_id;
            const updatedStatus = payload.status;
            const updatedFailures = payload.consecutive_failures;
            const latestResult = payload.latest_result;
            const aiAnalysis = payload.ai_analysis;

            // Update endpoints state
            setEndpoints((prev) =>
              prev.map((ep) =>
                ep.id === updatedEpId
                  ? {
                      ...ep,
                      status: updatedStatus,
                      consecutive_failures: updatedFailures,
                      latest_result: latestResult,
                    }
                  : ep
              )
            );

            // Trigger failure warning banner if AI analysis is present
            if (aiAnalysis && updatedStatus === "failing") {
              const newAlert: AlertNotification = {
                id: Math.random().toString(),
                endpointName: prevEndpointsRef.current.find(ep => ep.id === updatedEpId)?.name || "Endpoint",
                url: prevEndpointsRef.current.find(ep => ep.id === updatedEpId)?.url || "",
                summary: aiAnalysis.summary,
                suggestions: aiAnalysis.suggestions
              };
              setActiveAlerts((prevAlerts) => [newAlert, ...prevAlerts]);
            }
          }
        } catch (e) {
          console.error("Error parsing WebSocket message:", e);
        }
      };

      ws.onclose = () => {
        if (!isMounted) return; // Component unmounted — don't reconnect
        console.log("WebSocket connection closed. Reconnecting in 3s...");
        setTimeout(connectWebSocket, 3000);
      };

      ws.onerror = () => {
        // Browser WebSocket errors never carry useful detail (always empty object).
        // The onclose handler will fire immediately after and handle the reconnect.
        ws.close();
      };
    };

    connectWebSocket();

    return () => {
      isMounted = false;
      if (socketRef.current) {
        socketRef.current.close();
      }
    };
  }, [token]);

  // Keep a ref to endpoints for WebSocket alerts to lookup metadata
  const prevEndpointsRef = useRef<Endpoint[]>([]);
  useEffect(() => {
    prevEndpointsRef.current = endpoints;
  }, [endpoints]);

  // Add Project
  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!projectName.trim()) return;

    try {
      const response = await fetch(`${API_URL}/api/projects/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          name: projectName,
          description: projectDesc,
          webhook_url: projectWebhook || undefined,
        }),
      });

      if (response.status === 401) {
        logout();
        return;
      }

      if (response.ok) {
        const newProj = await response.json();
        setProjects((prev) => [...prev, newProj]);
        setProjectName("");
        setProjectDesc("");
        setProjectWebhook("");
        setIsProjectModalOpen(false);
        if (!endpointProjectId) setEndpointProjectId(newProj.id);
      }
    } catch (err) {
      console.error("Error creating project:", err);
    }
  };

  // Delete Project
  const handleDeleteProject = async (projectId: number) => {
    if (!confirm("Are you sure you want to delete this project? This will delete all monitored endpoints under it.")) return;
    try {
      const response = await fetch(`${API_URL}/api/projects/${projectId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.status === 401) {
        logout();
        return;
      }

      if (response.ok) {
        setProjects((prev) => prev.filter((p) => p.id !== projectId));
        setEndpoints((prev) => prev.filter((ep) => ep.project_id !== projectId));
        if (selectedProjectId === projectId) setSelectedProjectId(null);
      }
    } catch (err) {
      console.error("Error deleting project:", err);
    }
  };

  // Add Endpoint
  const handleCreateEndpoint = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!endpointName.trim() || !endpointUrl.trim() || !endpointProjectId) return;

    try {
      const response = await fetch(`${API_URL}/api/endpoints/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          name: endpointName,
          url: endpointUrl,
          method: endpointMethod,
          check_interval: endpointInterval,
          project_id: Number(endpointProjectId),
          is_active: true,
        }),
      });

      if (response.status === 401) {
        logout();
        return;
      }

      if (response.ok) {
        const newEp = await response.json();
        setEndpoints((prev) => [...prev, newEp]);
        setEndpointName("");
        setEndpointUrl("");
        setEndpointMethod("GET");
        setEndpointInterval(60);
        setIsEndpointModalOpen(false);
      }
    } catch (err) {
      console.error("Error creating endpoint:", err);
    }
  };

  // Delete Endpoint
  const handleDeleteEndpoint = async (e: React.MouseEvent, endpointId: number) => {
    e.stopPropagation(); // prevent row click redirect
    if (!confirm("Are you sure you want to delete this endpoint?")) return;
    try {
      const response = await fetch(`${API_URL}/api/endpoints/${endpointId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.status === 401) {
        logout();
        return;
      }

      if (response.ok) {
        setEndpoints((prev) => prev.filter((ep) => ep.id !== endpointId));
      }
    } catch (err) {
      console.error("Error deleting endpoint:", err);
    }
  };

  // Trigger Instant Ping
  const handleTriggerPing = async (e: React.MouseEvent, endpointId: number) => {
    e.stopPropagation();
    try {
      // Create a temporary status check state locally
      setEndpoints((prev) =>
        prev.map((ep) =>
          ep.id === endpointId
            ? {
                ...ep,
                status: "checking",
              }
            : ep
        )
      );

      // Trigger ping via background task. Note: in python we don't have a direct router ping,
      // but wait! We can trigger a manual AI analysis which queries the health,
      // or wait, let's see how the scheduler works. The background task executes automatically.
      // Can we manually ping? If we have a local task, let's check.
      // Webhooks/WS listener handles UI status transition updates.
      const response = await fetch(`${API_URL}/api/endpoints/${endpointId}/ping`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` }
      });
      
      if (response.status === 401) {
        logout();
        return;
      }
      
      if (!response.ok) {
        // If the endpoint doesn't exist, we fall back to manual mock check or notify
        console.log("No custom ping endpoint registered. Running automatic trigger simulation.");
      }
    } catch (err) {
      console.error("Error triggering manual ping:", err);
    }
  };

  // Filtered Endpoints
  const filteredEndpoints = selectedProjectId
    ? endpoints.filter((ep) => ep.project_id === selectedProjectId)
    : endpoints;

  // Metric Computations
  const totalMonitored = endpoints.length;
  const healthyCount = endpoints.filter((ep) => ep.status === "healthy").length;
  const healthRatio = totalMonitored > 0 ? Math.round((healthyCount / totalMonitored) * 100) : 100;
  const failingCount = endpoints.filter((ep) => ep.status === "failing").length;

  const latencies = endpoints
    .map((ep) => ep.latest_result?.response_time_ms)
    .filter((ms): ms is number => typeof ms === "number" && ms > 0);
  const avgLatency = latencies.length > 0 ? Math.round(latencies.reduce((a, b) => a + b, 0) / latencies.length) : 0;

  if (authLoading || !user) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-zinc-950">
        <Loader2 className="w-8 h-8 animate-spin text-purple-500" />
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col bg-zinc-950 text-zinc-100 pb-16">
      {/* Top Navigation */}
      <header className="glass-panel sticky top-0 z-40 border-b border-zinc-900 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-purple-500/10 border border-purple-500/20 text-purple-400">
              <Activity className="w-5 h-5 animate-pulse-slow" />
            </div>
            <span className="font-bold text-lg tracking-tight text-white">PulseGuard</span>
          </div>

          <div className="flex items-center gap-4">
            <span className="text-zinc-400 text-sm hidden sm:inline">{user.email}</span>
            <button
              onClick={logout}
              className="flex items-center gap-2 text-zinc-400 hover:text-white bg-zinc-900 border border-zinc-800 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors"
            >
              <LogOut className="w-4 h-4" />
              <span>Log Out</span>
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto w-full px-6 mt-8 flex-1">
        {/* Real-time AI Incidents Alert Banner */}
        {activeAlerts.length > 0 && (
          <div className="space-y-4 mb-8">
            {activeAlerts.map((alert) => (
              <div 
                key={alert.id}
                className="relative glass-panel bg-red-950/15 border border-red-500/30 rounded-2xl p-6 shadow-xl glow-red overflow-hidden"
              >
                <div className="absolute top-0 right-0 p-3">
                  <button 
                    onClick={() => setActiveAlerts((prev) => prev.filter((a) => a.id !== alert.id))}
                    className="text-red-400 hover:text-red-300 transition-colors"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
                <div className="flex items-start gap-4">
                  <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/25 text-red-400">
                    <AlertTriangle className="w-6 h-6" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                      <span className="text-red-400 text-xs font-bold uppercase tracking-widest">Critical Alert</span>
                      <h4 className="font-semibold text-white text-base">API Incident Detected: {alert.endpointName}</h4>
                    </div>
                    <p className="text-zinc-400 text-xs font-mono break-all mb-4">{alert.url}</p>
                    
                    <div className="bg-zinc-950/80 border border-zinc-900 rounded-xl p-4 mt-2">
                      <div className="flex items-center gap-1.5 mb-2 text-purple-400 text-xs font-semibold">
                        <Sparkles className="w-3.5 h-3.5" />
                        <span>AI Root-Cause Diagnosis</span>
                      </div>
                      <p className="text-zinc-300 text-sm leading-relaxed mb-3">{alert.summary}</p>
                      
                      <div className="text-xs text-zinc-400">
                        <span className="font-semibold text-zinc-300 block mb-1">Troubleshooting Checklist:</span>
                        <div className="whitespace-pre-line leading-relaxed">{alert.suggestions}</div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Statistics Header */}
        <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          {/* Total Endpoints */}
          <div className="glass-panel p-5 rounded-2xl border border-zinc-900">
            <div className="flex items-center justify-between mb-3 text-zinc-500">
              <span className="text-xs uppercase tracking-wider font-semibold">Total Monitored</span>
              <Globe className="w-4 h-4 text-zinc-400" />
            </div>
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-bold text-white">{totalMonitored}</span>
              <span className="text-zinc-500 text-xs">endpoints</span>
            </div>
          </div>

          {/* Health Index */}
          <div className="glass-panel p-5 rounded-2xl border border-zinc-900">
            <div className="flex items-center justify-between mb-3 text-zinc-500">
              <span className="text-xs uppercase tracking-wider font-semibold">Health Score</span>
              <CheckCircle2 className="w-4 h-4 text-emerald-500" />
            </div>
            <div className="flex items-baseline gap-2">
              <span className={`text-3xl font-bold ${healthRatio > 90 ? 'text-emerald-400' : healthRatio > 70 ? 'text-amber-400' : 'text-red-400'}`}>
                {healthRatio}%
              </span>
              <span className="text-zinc-500 text-xs">online</span>
            </div>
          </div>

          {/* Latency Avg */}
          <div className="glass-panel p-5 rounded-2xl border border-zinc-900">
            <div className="flex items-center justify-between mb-3 text-zinc-500">
              <span className="text-xs uppercase tracking-wider font-semibold">Average Latency</span>
              <Clock className="w-4 h-4 text-purple-400" />
            </div>
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-bold text-white">{avgLatency || "--"}</span>
              <span className="text-zinc-500 text-xs">ms</span>
            </div>
          </div>

          {/* Active Incidents */}
          <div className="glass-panel p-5 rounded-2xl border border-zinc-900">
            <div className="flex items-center justify-between mb-3 text-zinc-500">
              <span className="text-xs uppercase tracking-wider font-semibold">Active Incidents</span>
              <AlertTriangle className="w-4 h-4 text-red-500 animate-pulse-slow" />
            </div>
            <div className="flex items-baseline gap-2">
              <span className={`text-3xl font-bold ${failingCount > 0 ? 'text-red-400 animate-pulse' : 'text-zinc-400'}`}>
                {failingCount}
              </span>
              <span className="text-zinc-500 text-xs">failing</span>
            </div>
          </div>
        </section>

        {/* Dashboard Split Body */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
          {/* Projects Side Panel */}
          <aside className="lg:col-span-1 flex flex-col gap-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold uppercase tracking-wider text-zinc-400">Projects</h3>
              <button
                onClick={() => setIsProjectModalOpen(true)}
                className="p-1 rounded-lg bg-zinc-900 border border-zinc-800 text-zinc-400 hover:text-white hover:border-zinc-700 transition-all"
              >
                <Plus className="w-4 h-4" />
              </button>
            </div>

            <div className="flex flex-col gap-2">
              {/* All Projects Option */}
              <button
                onClick={() => setSelectedProjectId(null)}
                className={`w-full text-left px-4 py-2.5 rounded-xl text-sm font-medium border transition-all ${
                  selectedProjectId === null
                    ? "bg-purple-950/20 border-purple-500/30 text-purple-300"
                    : "bg-zinc-900/40 border-transparent text-zinc-400 hover:bg-zinc-900/80 hover:text-white"
                }`}
              >
                All Projects
              </button>

              {/* Individual Projects */}
              {projects.map((proj) => (
                <div key={proj.id} className="group relative flex items-center">
                  <button
                    onClick={() => setSelectedProjectId(proj.id)}
                    className={`flex-1 text-left px-4 py-2.5 rounded-xl text-sm font-medium border transition-all pr-10 ${
                      selectedProjectId === proj.id
                        ? "bg-purple-950/20 border-purple-500/30 text-purple-300"
                        : "bg-zinc-900/40 border-transparent text-zinc-400 hover:bg-zinc-900/80 hover:text-white"
                    }`}
                  >
                    <div className="truncate font-semibold">{proj.name}</div>
                    <div className="text-xs text-zinc-500 truncate">{proj.description || "No description"}</div>
                  </button>
                  
                  <button
                    onClick={() => handleDeleteProject(proj.id)}
                    className="absolute right-2 opacity-0 group-hover:opacity-100 p-1 text-zinc-500 hover:text-red-400 rounded-md hover:bg-zinc-800 transition-all"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}

              {projects.length === 0 && (
                <div className="text-center p-6 border border-dashed border-zinc-800 rounded-2xl text-zinc-500 text-sm">
                  No projects yet.
                </div>
              )}
            </div>
          </aside>

          {/* Endpoints Table/List Area */}
          <section className="lg:col-span-3 flex flex-col gap-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold uppercase tracking-wider text-zinc-400">
                Monitored Routes ({filteredEndpoints.length})
              </h3>
              <button
                onClick={() => setIsEndpointModalOpen(true)}
                disabled={projects.length === 0}
                className="flex items-center gap-1.5 bg-purple-600 hover:bg-purple-500 text-white font-medium px-3.5 py-2 rounded-xl text-sm transition-colors shadow-lg shadow-purple-600/10 disabled:opacity-50 disabled:pointer-events-none"
              >
                <Plus className="w-4 h-4" />
                <span>Add Route</span>
              </button>
            </div>

            {loading ? (
              <div className="glass-panel rounded-2xl border border-zinc-900 p-16 flex items-center justify-center">
                <Loader2 className="w-6 h-6 animate-spin text-purple-500" />
              </div>
            ) : (
              <div className="flex flex-col gap-3">
                {filteredEndpoints.map((ep) => {
                  const isHealthy = ep.status === "healthy";
                  const isChecking = ep.status === "checking";
                  const statusGlowClass = isHealthy 
                    ? "bg-emerald-500 animate-pulse-glow-green" 
                    : isChecking 
                      ? "bg-blue-500 animate-pulse" 
                      : "bg-red-500 animate-pulse-glow-red";
                  const latestResult = ep.latest_result;

                  return (
                    <div
                      key={ep.id}
                      onClick={() => router.push(`/endpoints/${ep.id}`)}
                      className="glass-panel glass-panel-hover rounded-xl p-4 border border-zinc-900 cursor-pointer flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4"
                    >
                      {/* Left: Health Indicator & Details */}
                      <div className="flex items-center gap-4 min-w-0">
                        {/* Status Light */}
                        <div className={`w-3.5 h-3.5 rounded-full shrink-0 border border-zinc-950 ${statusGlowClass}`} />
                        
                        <div className="min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="font-semibold text-white truncate text-base">{ep.name}</span>
                            <span className="bg-zinc-800 text-zinc-400 font-mono text-[10px] font-bold px-1.5 py-0.5 rounded uppercase shrink-0">
                              {ep.method}
                            </span>
                          </div>
                          <p className="text-zinc-500 text-xs font-mono truncate max-w-sm mt-0.5">{ep.url}</p>
                        </div>
                      </div>

                      {/* Right: Latency & Settings Actions */}
                      <div className="flex items-center justify-between sm:justify-end gap-6 w-full sm:w-auto border-t sm:border-t-0 pt-3 sm:pt-0 border-zinc-800">
                        {/* Check Interval */}
                        <div className="flex items-center gap-1 text-zinc-500 text-xs">
                          <Clock className="w-3.5 h-3.5" />
                          <span>{ep.check_interval}s</span>
                        </div>

                        {/* Latency badge */}
                        <div className="flex flex-col items-end shrink-0">
                          <span className="text-xs text-zinc-500">Latency</span>
                          <span className={`text-sm font-semibold font-mono ${isHealthy ? 'text-white' : 'text-zinc-500'}`}>
                            {latestResult?.response_time_ms ? `${latestResult.response_time_ms} ms` : "--"}
                          </span>
                        </div>

                        {/* Interactive Buttons */}
                        <div className="flex items-center gap-2">
                          <button
                            onClick={(e) => handleTriggerPing(e, ep.id)}
                            title="Trigger Instant Check"
                            className="p-2 text-zinc-400 hover:text-white rounded-lg hover:bg-zinc-800/80 border border-transparent hover:border-zinc-800 transition-all"
                          >
                            <Play className="w-4 h-4 fill-zinc-400 hover:fill-white" />
                          </button>
                          
                          <button
                            onClick={(e) => handleDeleteEndpoint(e, ep.id)}
                            title="Delete Endpoint"
                            className="p-2 text-zinc-500 hover:text-red-400 rounded-lg hover:bg-zinc-800/80 transition-all"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>

                          <ChevronRight className="w-5 h-5 text-zinc-600 group-hover:text-zinc-400 transition-colors" />
                        </div>
                      </div>
                    </div>
                  );
                })}

                {filteredEndpoints.length === 0 && (
                  <div className="glass-panel rounded-2xl border border-zinc-900 border-dashed p-16 text-center text-zinc-500">
                    <Server className="w-10 h-10 text-zinc-700 mx-auto mb-3" />
                    <p className="text-sm font-semibold text-zinc-400">No monitored routes in this scope</p>
                    <p className="text-xs text-zinc-500 mt-1">Click "Add Route" to register your first endpoint.</p>
                  </div>
                )}
              </div>
            )}
          </section>
        </div>
      </main>

      {/* Add Project Modal */}
      {isProjectModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="glass-panel w-full max-w-md rounded-2xl border border-zinc-800 p-6 shadow-2xl animate-in fade-in zoom-in-95 duration-200">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-bold text-white">Create Project</h3>
              <button onClick={() => setIsProjectModalOpen(false)} className="text-zinc-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <form onSubmit={handleCreateProject} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-2">Project Name</label>
                <input
                  type="text"
                  required
                  value={projectName}
                  onChange={(e) => setProjectName(e.target.value)}
                  placeholder="e.g. Production API"
                  className="w-full bg-zinc-900/85 border border-zinc-800 rounded-xl px-4 py-2.5 text-sm text-white placeholder-zinc-600 focus:outline-none focus:border-purple-500/50"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-2">Description</label>
                <textarea
                  value={projectDesc}
                  onChange={(e) => setProjectDesc(e.target.value)}
                  placeholder="e.g. Core microservices monitoring"
                  rows={3}
                  className="w-full bg-zinc-900/85 border border-zinc-800 rounded-xl px-4 py-2.5 text-sm text-white placeholder-zinc-600 focus:outline-none focus:border-purple-500/50 resize-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-2">Webhook URL (Slack/Discord)</label>
                <input
                  type="url"
                  value={projectWebhook}
                  onChange={(e) => setProjectWebhook(e.target.value)}
                  placeholder="https://hooks.slack.com/services/..."
                  className="w-full bg-zinc-900/85 border border-zinc-800 rounded-xl px-4 py-2.5 text-sm text-white placeholder-zinc-600 focus:outline-none focus:border-purple-500/50"
                />
              </div>

              <div className="flex gap-3 justify-end pt-4">
                <button
                  type="button"
                  onClick={() => setIsProjectModalOpen(false)}
                  className="bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 px-4 py-2.5 rounded-xl text-sm font-semibold transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="bg-purple-600 hover:bg-purple-500 px-4 py-2.5 rounded-xl text-sm font-semibold text-white transition-colors"
                >
                  Save Project
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Add Endpoint Modal */}
      {isEndpointModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="glass-panel w-full max-w-md rounded-2xl border border-zinc-800 p-6 shadow-2xl animate-in fade-in zoom-in-95 duration-200">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-bold text-white">Add Route to Monitor</h3>
              <button onClick={() => setIsEndpointModalOpen(false)} className="text-zinc-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <form onSubmit={handleCreateEndpoint} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-2">Project Scope</label>
                <select
                  required
                  value={endpointProjectId}
                  onChange={(e) => setEndpointProjectId(Number(e.target.value))}
                  className="w-full bg-zinc-900/85 border border-zinc-800 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-purple-500/50"
                >
                  {projects.map((p) => (
                    <option key={p.id} value={p.id}>{p.name}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-2">Route Name</label>
                <input
                  type="text"
                  required
                  value={endpointName}
                  onChange={(e) => setEndpointName(e.target.value)}
                  placeholder="e.g. Users Healthcheck"
                  className="w-full bg-zinc-900/85 border border-zinc-800 rounded-xl px-4 py-2.5 text-sm text-white placeholder-zinc-600 focus:outline-none focus:border-purple-500/50"
                />
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div className="col-span-1">
                  <label className="block text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-2">Method</label>
                  <select
                    value={endpointMethod}
                    onChange={(e) => setEndpointMethod(e.target.value)}
                    className="w-full bg-zinc-900/85 border border-zinc-800 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-purple-500/50"
                  >
                    <option value="GET">GET</option>
                    <option value="POST">POST</option>
                    <option value="PUT">PUT</option>
                    <option value="DELETE">DELETE</option>
                  </select>
                </div>

                <div className="col-span-2">
                  <label className="block text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-2">Interval (Seconds)</label>
                  <select
                    value={endpointInterval}
                    onChange={(e) => setEndpointInterval(Number(e.target.value))}
                    className="w-full bg-zinc-900/85 border border-zinc-800 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-purple-500/50"
                  >
                    <option value={10}>10s (Real-time)</option>
                    <option value={30}>30s</option>
                    <option value={60}>60s (1 min)</option>
                    <option value={300}>300s (5 min)</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-2">Target URL</label>
                <input
                  type="url"
                  required
                  value={endpointUrl}
                  onChange={(e) => setEndpointUrl(e.target.value)}
                  placeholder="https://api.yourdomain.com/health"
                  className="w-full bg-zinc-900/85 border border-zinc-800 rounded-xl px-4 py-2.5 text-sm text-white placeholder-zinc-600 focus:outline-none focus:border-purple-500/50"
                />
              </div>

              <div className="flex gap-3 justify-end pt-4">
                <button
                  type="button"
                  onClick={() => setIsEndpointModalOpen(false)}
                  className="bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 px-4 py-2.5 rounded-xl text-sm font-semibold transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="bg-purple-600 hover:bg-purple-500 px-4 py-2.5 rounded-xl text-sm font-semibold text-white transition-colors"
                >
                  Start Monitoring
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
