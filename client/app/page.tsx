"use client";

import React from "react";
import Link from "next/link";
import { useAuth } from "./contexts/AuthContext";
import { 
  Activity, 
  Brain, 
  Bell, 
  BarChart3, 
  ArrowRight, 
  ShieldCheck, 
  Zap,
  Globe,
  Settings
} from "lucide-react";

export default function LandingPage() {
  const { isAuthenticated } = useAuth();

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col">
      {/* Navigation */}
      <header className="border-b border-card-border bg-white/80 backdrop-blur-md sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-primary/10 text-primary">
              <Activity className="w-6 h-6 animate-pulse-slow" />
            </div>
            <span className="text-xl font-bold tracking-tight text-slate-900">
              PulseGuard
            </span>
          </div>

          <nav className="flex items-center gap-4">
            {isAuthenticated ? (
              <Link 
                href="/dashboard" 
                className="flex items-center gap-1.5 bg-primary hover:bg-primary-hover text-white text-sm font-semibold px-4 py-2 rounded-xl transition-all shadow-sm"
              >
                Go to Dashboard
                <ArrowRight className="w-4 h-4" />
              </Link>
            ) : (
              <>
                <Link 
                  href="/auth/login" 
                  className="text-slate-600 hover:text-slate-900 text-sm font-medium transition-colors px-3 py-2"
                >
                  Sign In
                </Link>
                <Link 
                  href="/auth/signup" 
                  className="bg-primary hover:bg-primary-hover text-white text-sm font-semibold px-4 py-2 rounded-xl transition-all shadow-sm"
                >
                  Get Started
                </Link>
              </>
            )}
          </nav>
        </div>
      </header>

      {/* Hero Section */}
      <section className="relative overflow-hidden py-20 lg:py-32 border-b border-card-border bg-gradient-to-b from-white to-slate-50">
        {/* Background Gradients */}
        <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-primary/5 rounded-full blur-3xl -z-10" />
        <div className="absolute top-1/2 right-10 w-96 h-96 bg-info/5 rounded-full blur-3xl -z-10" />

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-primary/10 border border-primary/20 text-primary text-xs font-semibold uppercase tracking-wider mb-6">
            <Zap className="w-3.5 h-3.5" />
            AI-Driven API Monitoring
          </div>

          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold text-slate-950 tracking-tight max-w-4xl mx-auto leading-none mb-6">
            Keep Your APIs Running. <br/>
            Let AI Diagnose the Failures.
          </h1>

          <p className="text-lg text-slate-600 max-w-2xl mx-auto mb-10">
            PulseGuard checks your endpoints every 10 seconds, alerts you immediately on failures, and uses advanced LLMs to write root-cause incident reports instantly.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            {isAuthenticated ? (
              <Link 
                href="/dashboard" 
                className="w-full sm:w-auto flex items-center justify-center gap-2 bg-primary hover:bg-primary-hover text-white font-semibold px-6 py-3.5 rounded-xl transition-all shadow-md hover:shadow-lg text-base"
              >
                Open Dashboard
                <ArrowRight className="w-5 h-5" />
              </Link>
            ) : (
              <>
                <Link 
                  href="/auth/signup" 
                  className="w-full sm:w-auto flex items-center justify-center gap-2 bg-primary hover:bg-primary-hover text-white font-semibold px-6 py-3.5 rounded-xl transition-all shadow-md hover:shadow-lg text-base"
                >
                  Start Monitoring Free
                  <ArrowRight className="w-5 h-5" />
                </Link>
                <Link 
                  href="/auth/login" 
                  className="w-full sm:w-auto flex items-center justify-center gap-2 bg-white hover:bg-slate-50 text-slate-800 border border-slate-200 font-semibold px-6 py-3.5 rounded-xl transition-all shadow-sm text-base"
                >
                  Live Demo Preview
                </Link>
              </>
            )}
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section className="py-20 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-16">
            <h2 className="text-3xl font-bold text-slate-950 sm:text-4xl">
              All-In-One API Reliability Stack
            </h2>
            <p className="mt-4 text-slate-600">
              PulseGuard brings together high-speed monitoring, instant alerts, and machine diagnostics in a single, lightweight developer platform.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
            {/* Feature 1 */}
            <div className="glass-panel p-6 rounded-2xl border border-card-border bg-slate-50/50 hover:bg-slate-50 transition-all">
              <div className="w-12 h-12 rounded-xl bg-primary/10 text-primary flex items-center justify-center mb-5">
                <Globe className="w-6 h-6" />
              </div>
              <h3 className="text-lg font-bold text-slate-950 mb-2">10-Second Checking</h3>
              <p className="text-sm text-slate-600">
                Ultra-frequent status checks with microsecond latency metrics to spot anomalies before users do.
              </p>
            </div>

            {/* Feature 2 */}
            <div className="glass-panel p-6 rounded-2xl border border-card-border bg-slate-50/50 hover:bg-slate-50 transition-all">
              <div className="w-12 h-12 rounded-xl bg-success/10 text-success flex items-center justify-center mb-5">
                <Brain className="w-6 h-6" />
              </div>
              <h3 className="text-lg font-bold text-slate-950 mb-2">AI Root-Cause Diagnosis</h3>
              <p className="text-sm text-slate-600">
                Integrates Llama 3 models to write incident analysis reports explaining why servers fail.
              </p>
            </div>

            {/* Feature 3 */}
            <div className="glass-panel p-6 rounded-2xl border border-card-border bg-slate-50/50 hover:bg-slate-50 transition-all">
              <div className="w-12 h-12 rounded-xl bg-danger/10 text-danger flex items-center justify-center mb-5">
                <Bell className="w-6 h-6" />
              </div>
              <h3 className="text-lg font-bold text-slate-950 mb-2">Webhook & SMTP Alerts</h3>
              <p className="text-sm text-slate-600">
                Send structured alerts immediately to webhooks or emails the second state transitions happen.
              </p>
            </div>

            {/* Feature 4 */}
            <div className="glass-panel p-6 rounded-2xl border border-card-border bg-slate-50/50 hover:bg-slate-50 transition-all">
              <div className="w-12 h-12 rounded-xl bg-info/10 text-info flex items-center justify-center mb-5">
                <BarChart3 className="w-6 h-6" />
              </div>
              <h3 className="text-lg font-bold text-slate-950 mb-2">Prometheus/Grafana</h3>
              <p className="text-sm text-slate-600">
                Built-in exporters for Prometheus server scraping to generate dashboard metrics seamlessly.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Mock Dashboard Preview */}
      <section className="py-16 bg-slate-50 border-t border-card-border overflow-hidden">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="glass-panel border border-card-border rounded-3xl overflow-hidden shadow-2xl bg-white max-w-5xl mx-auto">
            {/* Header bar */}
            <div className="border-b border-card-border px-6 py-4 bg-slate-50 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="w-3.5 h-3.5 rounded-full bg-red-500" />
                <span className="w-3.5 h-3.5 rounded-full bg-yellow-500" />
                <span className="w-3.5 h-3.5 rounded-full bg-green-500" />
              </div>
              <div className="text-xs font-mono text-slate-400 bg-white px-3 py-1 rounded-md border border-slate-200">
                dashboard.pulseguard.io
              </div>
              <div className="w-14" />
            </div>

            {/* Dashboard Mock Content */}
            <div className="p-6 sm:p-8 bg-slate-50/30">
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-8">
                <div>
                  <h4 className="text-lg font-bold text-slate-900">Endpoints Monitoring</h4>
                  <p className="text-xs text-slate-500">Live API health statuses and performance reports.</p>
                </div>
                <div className="flex gap-2">
                  <span className="text-xs px-2.5 py-1 rounded-full bg-success/15 text-success border border-success/20 font-semibold flex items-center gap-1">
                    <ShieldCheck className="w-3 h-3" /> System Healthy
                  </span>
                </div>
              </div>

              {/* Status List Mock */}
              <div className="space-y-4">
                <div className="p-4 rounded-xl border border-card-border bg-white shadow-sm flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className="w-2.5 h-2.5 rounded-full bg-success animate-pulse-glow-green" />
                    <div>
                      <div className="font-semibold text-sm text-slate-900">User Auth API</div>
                      <div className="text-xs text-slate-400">https://api.myapp.com/v1/auth/status</div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-xs font-semibold text-success">Healthy (200 OK)</div>
                    <div className="text-xs text-slate-400">12ms response</div>
                  </div>
                </div>

                <div className="p-4 rounded-xl border border-card-border bg-white shadow-sm flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className="w-2.5 h-2.5 rounded-full bg-danger animate-pulse-glow-red" />
                    <div>
                      <div className="font-semibold text-sm text-slate-900">Product Catalog Feed</div>
                      <div className="text-xs text-slate-400">https://api.myapp.com/v1/products</div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-xs font-semibold text-danger">Failing (503 Service Unavailable)</div>
                    <div className="text-xs text-slate-400">1500ms latency</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="mt-auto border-t border-card-border bg-white py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <p className="text-sm text-slate-500">
            &copy; {new Date().getFullYear()} PulseGuard Platform. All rights reserved.
          </p>
        </div>
      </footer>
    </div>
  );
}
