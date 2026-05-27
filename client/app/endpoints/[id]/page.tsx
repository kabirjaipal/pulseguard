"use client";

import React, { useState, useEffect, useRef } from "react";
import { useRouter, useParams } from "next/navigation";
import { useAuth } from "../../contexts/AuthContext";
import { 
  ArrowLeft, Activity, Play, AlertTriangle, CheckCircle2, 
  XCircle, Clock, Globe, ShieldAlert, Sparkles, RefreshCw, Server, Terminal, Loader2
} from "lucide-react";
import { API_URL, WS_URL } from "../../config";

interface Endpoint {
  id: number;
  name: string;
  url: string;
  method: string;
  check_interval: number;
  is_active: boolean;
  status: string;
  consecutive_failures: number;
  project_id: number;
}

interface LogResult {
  id: number;
  endpoint_id: number;
  status_code?: number;
  response_time_ms?: number;
  is_healthy: boolean;
  error_message?: string;
  checked_at: string;
}

interface AIAnalysis {
  id: number;
  endpoint_id: number;
  summary: string;
  suggestions: string;
  raw_logs?: string;
  created_at: string;
}

export default function EndpointDetailPage() {
  const { id } = useParams();
  const { token, logout, isAuthenticated, loading: authLoading } = useAuth();
  const router = useRouter();

  // Route States
  const [endpoint, setEndpoint] = useState<Endpoint | null>(null);
  const [history, setHistory] = useState<LogResult[]>([]);
  const [analyses, setAnalyses] = useState<AIAnalysis[]>([]);
  const [loading, setLoading] = useState(true);
  const [pinging, setPinging] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState("");

  const socketRef = useRef<WebSocket | null>(null);

  // Authenticate user check
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push("/auth/login");
    }
  }, [isAuthenticated, authLoading, router]);

  // Load details, history, and AI reports
  const loadData = async () => {
    if (!token || !id) return;
    try {
      setLoading(true);
      setError("");

      // 1. Fetch endpoint details
      const epRes = await fetch(`${API_URL}/api/endpoints/${id}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (epRes.status === 401) {
        logout();
        return;
      }
      if (!epRes.ok) throw new Error("Could not load endpoint metadata.");
      const epData = await epRes.json();
      setEndpoint(epData);

      // 2. Fetch history
      const histRes = await fetch(`${API_URL}/api/endpoints/${id}/history?limit=30`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (histRes.status === 401) {
        logout();
        return;
      }
      if (histRes.ok) {
        setHistory(await histRes.json());
      }

      // 3. Fetch AI reports
      const aiRes = await fetch(`${API_URL}/api/incidents/endpoint/${id}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (aiRes.status === 401) {
        logout();
        return;
      }
      if (aiRes.ok) {
        const aiData = await aiRes.json();
        // Sort descending by date
        setAnalyses(aiData.sort((a: AIAnalysis, b: AIAnalysis) => 
          new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
        ));
      }
    } catch (err: any) {
      setError(err.message || "An error occurred while loading data.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (token && id) {
      loadData();
    }
  }, [token, id]);

  // Connect WebSocket to receive real-time updates for this endpoint
  useEffect(() => {
    if (!token || !id) return;

    const connectWebSocket = () => {
      const wsUrl = `${WS_URL}/api/ws?token=${token}`;
      const ws = new WebSocket(wsUrl);
      socketRef.current = ws;

      ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          
          if (payload.type === "endpoint_update" && payload.endpoint_id === Number(id)) {
            const updatedStatus = payload.status;
            const updatedFailures = payload.consecutive_failures;
            const latestResult = payload.latest_result;
            const newAiAnalysis = payload.ai_analysis;

            // Update local endpoint status
            setEndpoint((prev) => 
              prev ? { ...prev, status: updatedStatus, consecutive_failures: updatedFailures } : null
            );

            // Add new log to history
            if (latestResult && latestResult.id) {
              setHistory((prev) => {
                // Prevent duplicate logs
                if (prev.some((log) => log.id === latestResult.id)) return prev;
                // Add new and slice to limit
                const newHist = [...prev, latestResult];
                if (newHist.length > 30) newHist.shift();
                return newHist;
              });
            }

            // If an AI analysis is broadcasted, prepend it
            if (newAiAnalysis) {
              const formattedAnalysis: AIAnalysis = {
                id: Math.random(),
                endpoint_id: Number(id),
                summary: newAiAnalysis.summary,
                suggestions: newAiAnalysis.suggestions,
                created_at: newAiAnalysis.created_at || new Date().toISOString()
              };
              setAnalyses((prev) => [formattedAnalysis, ...prev]);
            }
          }
        } catch (e) {
          console.error("Error parsing details WS message:", e);
        }
      };

      ws.onclose = () => {
        setTimeout(connectWebSocket, 3000);
      };
    };

    connectWebSocket();

    return () => {
      if (socketRef.current) {
        socketRef.current.close();
      }
    };
  }, [token, id]);

  // Trigger manual check ping
  const handleTriggerPing = async () => {
    if (!id || !token || pinging) return;
    try {
      setPinging(true);
      
      // Update local status to checking
      setEndpoint((prev) => prev ? { ...prev, status: "checking" } : null);

      const res = await fetch(`${API_URL}/api/endpoints/${id}/ping`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` }
      });

      if (res.status === 401) {
        logout();
        return;
      }

      if (!res.ok) throw new Error("Failed to trigger manual check.");
      
      // Give a small visual feedback. The WS will trigger the status update,
      // but in case it takes a moment, we keep the spinner active shortly.
      setTimeout(() => setPinging(false), 1500);
    } catch (err: any) {
      console.error(err);
      setPinging(false);
      loadData(); // reload to reset status
    }
  };

  // Trigger manual AI Incident analysis
  const handleTriggerAI = async () => {
    if (!id || !token || analyzing) return;
    try {
      setAnalyzing(true);
      setError("");

      const res = await fetch(`${API_URL}/api/incidents/endpoint/${id}/analyze`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` }
      });

      if (res.status === 401) {
        logout();
        return;
      }

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.detail || "AI analysis failed. Make sure the endpoint has failed checks in its logs.");
      }

      const newAnalysis = await res.json();
      setAnalyses((prev) => [newAnalysis, ...prev]);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setAnalyzing(false);
    }
  };

  // Render SVG Latency Chart
  const renderLatencyChart = () => {
    const validHistory = history.filter((h) => typeof h.response_time_ms === "number" && h.response_time_ms > 0);
    
    if (validHistory.length === 0) {
      return (
        <div className="h-48 flex flex-col items-center justify-center text-zinc-600 text-sm">
          <Clock className="w-8 h-8 mb-2" />
          <span>No response latency records available yet</span>
        </div>
      );
    }

    const maxLatency = Math.max(...validHistory.map((h) => h.response_time_ms || 0), 100);
    // Pad max latency by 20% for visual breathing room
    const chartMax = Math.ceil(maxLatency * 1.2);

    const width = 800;
    const height = 200;
    const padding = 30;

    const chartWidth = width - padding * 2;
    const chartHeight = height - padding * 2;

    // Map logs to coordinates
    const points = validHistory.map((h, i) => {
      const x = padding + (i / (validHistory.length - 1)) * chartWidth;
      const y = padding + chartHeight - ((h.response_time_ms || 0) / chartMax) * chartHeight;
      return { x, y, val: h.response_time_ms, date: new Date(h.checked_at).toLocaleTimeString() };
    });

    // Create polyline / path description
    const pathD = points.reduce((acc, p, i) => {
      return i === 0 ? `M ${p.x} ${p.y}` : `${acc} L ${p.x} ${p.y}`;
    }, "");

    // Create gradient fill area path description
    const areaD = points.length > 0 
      ? `${pathD} L ${points[points.length - 1].x} ${height - padding} L ${points[0].x} ${height - padding} Z`
      : "";

    return (
      <div className="relative">
        <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-full overflow-visible select-none">
          <defs>
            <linearGradient id="latencyGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#8b5cf6" stopOpacity="0.4" />
              <stop offset="100%" stopColor="#8b5cf6" stopOpacity="0.0" />
            </linearGradient>
          </defs>

          {/* Grid lines (horizontal) */}
          {[0, 0.25, 0.5, 0.75, 1].map((ratio, index) => {
            const y = padding + ratio * chartHeight;
            const gridVal = Math.round(chartMax - ratio * chartMax);
            return (
              <g key={index}>
                <line 
                  x1={padding} 
                  y1={y} 
                  x2={width - padding} 
                  y2={y} 
                  stroke="#1f1f23" 
                  strokeWidth="1" 
                  strokeDasharray="4 4"
                />
                <text 
                  x={padding - 8} 
                  y={y + 4} 
                  fill="#52525b" 
                  fontSize="10" 
                  textAnchor="end"
                  fontFamily="monospace"
                >
                  {gridVal}ms
                </text>
              </g>
            );
          })}

          {/* Area under the line */}
          {areaD && <path d={areaD} fill="url(#latencyGrad)" />}

          {/* Latency line */}
          {pathD && <path d={pathD} fill="none" stroke="#a78bfa" strokeWidth="2.5" strokeLinecap="round" />}

          {/* Data Points */}
          {points.map((p, index) => (
            <g key={index} className="group/point">
              <circle 
                cx={p.x} 
                cy={p.y} 
                r="4" 
                fill="#8b5cf6" 
                stroke="#18181b" 
                strokeWidth="1.5"
                className="hover:r-6 hover:fill-purple-400 cursor-pointer transition-all"
              />
              {/* Tooltip on hover */}
              <g className="opacity-0 group-hover/point:opacity-100 transition-opacity pointer-events-none">
                <rect 
                  x={p.x - 45} 
                  y={p.y - 35} 
                  width="90" 
                  height="24" 
                  rx="6" 
                  fill="#09090b" 
                  stroke="#3f3f46" 
                  strokeWidth="1"
                />
                <text 
                  x={p.x} 
                  y={p.y - 20} 
                  fill="#ffffff" 
                  fontSize="10" 
                  textAnchor="middle" 
                  fontWeight="bold"
                  fontFamily="monospace"
                >
                  {p.val} ms
                </text>
              </g>
            </g>
          ))}
        </svg>
      </div>
    );
  };

  if (authLoading || loading || !endpoint) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-zinc-950">
        {error ? (
          <div className="text-center">
            <ShieldAlert className="w-12 h-12 text-red-400 mx-auto mb-4" />
            <p className="text-white font-semibold">{error}</p>
            <button 
              onClick={() => router.push("/dashboard")}
              className="mt-4 inline-flex items-center gap-2 text-sm text-purple-400 hover:text-purple-300"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Back to Dashboard</span>
            </button>
          </div>
        ) : (
          <Loader2 className="w-8 h-8 animate-spin text-purple-500" />
        )}
      </div>
    );
  }

  const isHealthy = endpoint.status === "healthy";
  const isChecking = endpoint.status === "checking";
  const statusGlowClass = isHealthy 
    ? "bg-emerald-500 animate-pulse-glow-green" 
    : isChecking 
      ? "bg-blue-500 animate-pulse" 
      : "bg-red-500 animate-pulse-glow-red";

  return (
    <div className="min-h-screen flex flex-col bg-zinc-950 text-zinc-100 pb-16">
      {/* Top Navigation */}
      <header className="glass-panel sticky top-0 z-40 border-b border-zinc-900 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <button
            onClick={() => router.push("/dashboard")}
            className="flex items-center gap-2 text-zinc-400 hover:text-white transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
            <span className="font-semibold text-sm">Dashboard</span>
          </button>
          <div className="flex items-center gap-2">
            <span className="text-zinc-500 font-medium text-xs uppercase tracking-widest">Scope details</span>
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto w-full px-6 mt-8">
        {/* Endpoint Heading Metadata Card */}
        <section className="glass-panel rounded-2xl p-6 border border-zinc-900 mb-8 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="flex items-start gap-4">
            {/* Status Pulse */}
            <div className={`w-4 h-4 rounded-full mt-1.5 shrink-0 border border-zinc-950 ${statusGlowClass}`} />
            <div>
              <div className="flex items-center gap-2.5 flex-wrap">
                <h1 className="text-2xl font-bold text-white">{endpoint.name}</h1>
                <span className="bg-zinc-800 text-zinc-400 font-mono text-xs font-bold px-2 py-0.5 rounded uppercase">
                  {endpoint.method}
                </span>
                <span className={`text-xs font-semibold px-2 py-0.5 rounded-full capitalize ${
                  isHealthy ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-red-500/10 text-red-400 border border-red-500/20'
                }`}>
                  {endpoint.status}
                </span>
              </div>
              <p className="text-zinc-500 text-xs font-mono break-all mt-1.5 max-w-xl">{endpoint.url}</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={handleTriggerPing}
              disabled={pinging}
              className="flex items-center gap-2 bg-zinc-900 border border-zinc-800 hover:border-zinc-700 text-white font-medium px-4 py-2.5 rounded-xl text-sm transition-all disabled:opacity-50"
            >
              {pinging ? (
                <RefreshCw className="w-4 h-4 animate-spin text-purple-400" />
              ) : (
                <Play className="w-4 h-4 fill-white" />
              )}
              <span>Check Now</span>
            </button>

            {/* Manually trigger AI Diagnostic report */}
            <button
              onClick={handleTriggerAI}
              disabled={analyzing}
              className="flex items-center gap-2 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white font-medium px-4 py-2.5 rounded-xl text-sm transition-all disabled:opacity-50"
            >
              {analyzing ? (
                <RefreshCw className="w-4 h-4 animate-spin text-purple-200" />
              ) : (
                <Sparkles className="w-4 h-4" />
              )}
              <span>Analyze Incident</span>
            </button>
          </div>
        </section>

        {/* Display manual trigger errors */}
        {error && (
          <div className="flex items-start gap-3 p-4 mb-6 rounded-xl bg-red-950/20 border border-red-500/30 text-red-200 text-sm">
            <ShieldAlert className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Latency History Section */}
          <div className="lg:col-span-2 flex flex-col gap-6">
            {/* SVG Latency Chart Card */}
            <div className="glass-panel rounded-2xl border border-zinc-900 p-6">
              <h3 className="text-sm font-semibold uppercase tracking-wider text-zinc-400 mb-6 flex items-center gap-2">
                <Activity className="w-4 h-4 text-purple-400" />
                <span>Response Time Trend (Last 30 Checks)</span>
              </h3>
              {renderLatencyChart()}
            </div>

            {/* Logs List Table Card */}
            <div className="glass-panel rounded-2xl border border-zinc-900 p-6">
              <h3 className="text-sm font-semibold uppercase tracking-wider text-zinc-400 mb-4 flex items-center gap-2">
                <Terminal className="w-4 h-4 text-zinc-500" />
                <span>Execution Logs</span>
              </h3>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm text-zinc-400 border-collapse">
                  <thead>
                    <tr className="border-b border-zinc-900 text-xs font-semibold text-zinc-500 uppercase">
                      <th className="py-3 px-2">Status</th>
                      <th className="py-3 px-2">Code</th>
                      <th className="py-3 px-2">Latency</th>
                      <th className="py-3 px-2">Error Detail</th>
                      <th className="py-3 px-2 text-right">Checked At</th>
                    </tr>
                  </thead>
                  <tbody>
                    {history.slice().reverse().map((log) => (
                      <tr key={log.id} className="border-b border-zinc-900/60 hover:bg-zinc-900/20 transition-colors">
                        <td className="py-3 px-2">
                          {log.is_healthy ? (
                            <span className="flex items-center gap-1 text-emerald-400 font-semibold text-xs">
                              <CheckCircle2 className="w-3.5 h-3.5" />
                              <span>OK</span>
                            </span>
                          ) : (
                            <span className="flex items-center gap-1 text-red-400 font-semibold text-xs">
                              <XCircle className="w-3.5 h-3.5" />
                              <span>FAIL</span>
                            </span>
                          )}
                        </td>
                        <td className="py-3 px-2 font-mono text-zinc-300">
                          {log.status_code || "--"}
                        </td>
                        <td className="py-3 px-2 font-mono text-zinc-300">
                          {log.response_time_ms ? `${log.response_time_ms}ms` : "--"}
                        </td>
                        <td className="py-3 px-2 text-xs truncate max-w-xs text-zinc-500 font-mono">
                          {log.error_message || "None"}
                        </td>
                        <td className="py-3 px-2 text-right text-xs text-zinc-500 font-mono">
                          {new Date(log.checked_at).toLocaleString()}
                        </td>
                      </tr>
                    ))}

                    {history.length === 0 && (
                      <tr>
                        <td colSpan={5} className="py-8 text-center text-zinc-600 text-sm">
                          No check logs recorded yet.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          {/* AI Diagnoses Sidebar */}
          <div className="lg:col-span-1 flex flex-col gap-6">
            <h3 className="text-sm font-semibold uppercase tracking-wider text-zinc-400 flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-purple-400 animate-pulse-slow" />
              <span>AI Incident Diagnostic Reports</span>
            </h3>

            <div className="flex flex-col gap-4 overflow-y-auto max-h-[600px] pr-1">
              {analyses.map((report) => (
                <div 
                  key={report.id}
                  className="glass-panel bg-zinc-900/50 border border-zinc-900 rounded-xl p-5 shadow-lg relative overflow-hidden"
                >
                  <div className="flex items-center gap-1.5 mb-2.5 text-purple-400 text-xs font-semibold">
                    <Clock className="w-3.5 h-3.5" />
                    <span>{new Date(report.created_at).toLocaleString()}</span>
                  </div>
                  <h4 className="text-sm font-bold text-white mb-2">Root Cause Summary</h4>
                  <p className="text-zinc-300 text-xs leading-relaxed mb-4">{report.summary}</p>
                  
                  <div className="pt-3 border-t border-zinc-800/80 text-xs">
                    <span className="font-semibold text-zinc-400 block mb-1.5">Actionable Advice:</span>
                    <div className="whitespace-pre-line text-zinc-400 leading-relaxed font-sans">{report.suggestions}</div>
                  </div>
                </div>
              ))}

              {analyses.length === 0 && (
                <div className="glass-panel border-dashed border-zinc-900 rounded-2xl p-8 text-center text-zinc-500">
                  <Server className="w-8 h-8 text-zinc-700 mx-auto mb-2" />
                  <p className="text-xs font-semibold text-zinc-400">No incident reports generated</p>
                  <p className="text-[10px] text-zinc-600 mt-1 leading-relaxed">
                    AI diagnostics compile automatically upon 3 consecutive ping failures, or you can force one using the analyze button.
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
