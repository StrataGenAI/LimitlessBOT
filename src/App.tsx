import React, { useState, useEffect } from "react";
import { 
  Activity, 
  Shield, 
  Zap, 
  TrendingUp, 
  Terminal, 
  Settings, 
  Play, 
  Square, 
  AlertCircle,
  Clock,
  CheckCircle2,
  XCircle,
  ExternalLink
} from "lucide-react";
import { motion, AnimatePresence } from "motion/react";
import { 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  AreaChart,
  Area
} from "recharts";
import { cn } from "./lib/utils";

interface BotEvent {
  id: number;
  timestamp: string;
  source: string;
  source_type: string;
  headline: string;
  classification: string;
  materiality: number;
  reasoning: string;
  latency_ms: number;
  trade_executed: boolean;
  trade_details: string | null;
}

interface BotStats {
  total: number;
  trades: number;
  avg_latency: number;
}

export default function App() {
  const [events, setEvents] = useState<BotEvent[]>([]);
  const [stats, setStats] = useState<BotStats | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [isLiveMode, setIsLiveMode] = useState(false);
  const [activeTab, setActiveTab] = useState<"dashboard" | "logs" | "settings" | "backtest">("dashboard");
  const [isBacktesting, setIsBacktesting] = useState(false);

  const fetchStatus = async () => {
    try {
      const res = await fetch("/api/bot/status");
      const data = await res.json();
      setIsRunning(data.running);
    } catch (e) {
      console.error("Failed to fetch status", e);
    }
  };

  const fetchEvents = async () => {
    try {
      const res = await fetch("/api/events");
      const data = await res.json();
      setEvents(data);
    } catch (e) {
      console.error("Failed to fetch events", e);
    }
  };

  const fetchStats = async () => {
    try {
      const res = await fetch("/api/stats");
      const data = await res.json();
      setStats(data);
    } catch (e) {
      console.error("Failed to fetch stats", e);
    }
  };

  useEffect(() => {
    fetchStatus();
    fetchEvents();
    fetchStats();
    const interval = setInterval(() => {
      fetchEvents();
      fetchStats();
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  const toggleBot = async () => {
    const endpoint = isRunning ? "/api/bot/stop" : "/api/bot/start";
    try {
      await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ live: isLiveMode })
      });
      fetchStatus();
    } catch (e) {
      console.error("Failed to toggle bot", e);
    }
  };

  const runBacktest = async () => {
    setIsBacktesting(true);
    try {
      await fetch("/api/bot/backtest", { method: "POST" });
      fetchEvents();
      fetchStats();
    } catch (e) {
      console.error("Backtest failed", e);
    } finally {
      setIsBacktesting(false);
    }
  };

  const chartData = [...events].reverse().map(e => ({
    time: new Date(e.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    latency: e.latency_ms,
    materiality: e.materiality * 100
  }));

  return (
    <div className="min-h-screen bg-[#0a0a0b] text-zinc-100 font-sans selection:bg-blue-500/30">
      {/* Sidebar */}
      <div className="fixed left-0 top-0 bottom-0 w-64 border-r border-zinc-800 bg-[#0d0d0e] flex flex-col z-20">
        <div className="p-6 flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-blue-600 flex items-center justify-center shadow-lg shadow-blue-900/20">
            <Zap className="w-6 h-6 text-white fill-current" />
          </div>
          <div>
            <h1 className="font-bold text-lg tracking-tight">Limitless</h1>
            <p className="text-xs text-zinc-500 font-mono">v2.0.4-alpha</p>
          </div>
        </div>

        <nav className="flex-1 px-4 py-4 space-y-1">
          <NavItem 
            active={activeTab === "dashboard"} 
            onClick={() => setActiveTab("dashboard")}
            icon={<Activity className="w-5 h-5" />}
            label="Dashboard"
          />
          <NavItem 
            active={activeTab === "logs"} 
            onClick={() => setActiveTab("logs")}
            icon={<Terminal className="w-5 h-5" />}
            label="Live Logs"
          />
          <NavItem 
            active={activeTab === "backtest"} 
            onClick={() => setActiveTab("backtest")}
            icon={<TrendingUp className="w-5 h-5" />}
            label="Backtesting"
          />
          <NavItem 
            active={activeTab === "settings"} 
            onClick={() => setActiveTab("settings")}
            icon={<Settings className="w-5 h-5" />}
            label="Configuration"
          />
        </nav>

        <div className="p-4 border-t border-zinc-800">
          <div className="bg-zinc-900/50 rounded-xl p-4 border border-zinc-800">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium text-zinc-400">Bot Status</span>
              <div className={cn(
                "w-2 h-2 rounded-full animate-pulse",
                isRunning ? "bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)]" : "bg-red-500"
              )} />
            </div>
            <button 
              onClick={toggleBot}
              className={cn(
                "w-full py-2 rounded-lg text-sm font-semibold transition-all flex items-center justify-center gap-2",
                isRunning 
                  ? "bg-red-500/10 text-red-500 hover:bg-red-500/20 border border-red-500/20" 
                  : "bg-blue-600 text-white hover:bg-blue-500 shadow-lg shadow-blue-900/20"
              )}
            >
              {isRunning ? <Square className="w-4 h-4 fill-current" /> : <Play className="w-4 h-4 fill-current" />}
              {isRunning ? "Stop Bot" : "Start Bot"}
            </button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <main className="pl-64 min-h-screen">
        <header className="h-16 border-b border-zinc-800 bg-[#0a0a0b]/80 backdrop-blur-md sticky top-0 z-10 flex items-center justify-between px-8">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-zinc-900 border border-zinc-800">
              <div className="w-2 h-2 rounded-full bg-blue-500" />
              <span className="text-xs font-mono text-zinc-400">Base Mainnet</span>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 text-xs font-mono text-zinc-500">
              <Clock className="w-3.5 h-3.5" />
              {new Date().toLocaleTimeString()}
            </div>
          </div>
        </header>

        <div className="p-8 max-w-7xl mx-auto">
          <AnimatePresence mode="wait">
            {activeTab === "dashboard" && (
              <motion.div 
                key="dashboard"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="space-y-8"
              >
                {/* Stats Grid */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  <StatCard 
                    title="Total Events" 
                    value={stats?.total || 0} 
                    icon={<Activity className="w-5 h-5 text-blue-500" />}
                    trend="+12% vs last hour"
                  />
                  <StatCard 
                    title="Trades Executed" 
                    value={stats?.trades || 0} 
                    icon={<TrendingUp className="w-5 h-5 text-green-500" />}
                    trend="4.2% hit rate"
                  />
                  <StatCard 
                    title="Avg Latency" 
                    value={`${Math.round(stats?.avg_latency || 0)}ms`} 
                    icon={<Zap className="w-5 h-5 text-yellow-500" />}
                    trend="Sub-second edge"
                  />
                </div>

                {/* Charts Section */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <div className="bg-[#0d0d0e] border border-zinc-800 rounded-2xl p-6">
                    <h3 className="text-sm font-semibold mb-6 flex items-center gap-2">
                      <Zap className="w-4 h-4 text-yellow-500" />
                      LLM Classification Latency
                    </h3>
                    <div className="h-64">
                      <ResponsiveContainer width="100%" height="100%">
                        <AreaChart data={chartData}>
                          <defs>
                            <linearGradient id="colorLatency" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                              <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                            </linearGradient>
                          </defs>
                          <CartesianGrid strokeDasharray="3 3" stroke="#27272a" vertical={false} />
                          <XAxis dataKey="time" stroke="#71717a" fontSize={10} tickLine={false} axisLine={false} />
                          <YAxis stroke="#71717a" fontSize={10} tickLine={false} axisLine={false} unit="ms" />
                          <Tooltip 
                            contentStyle={{ backgroundColor: '#18181b', border: '1px solid #27272a', borderRadius: '8px' }}
                            itemStyle={{ color: '#3b82f6' }}
                          />
                          <Area type="monotone" dataKey="latency" stroke="#3b82f6" fillOpacity={1} fill="url(#colorLatency)" />
                        </AreaChart>
                      </ResponsiveContainer>
                    </div>
                  </div>

                  <div className="bg-[#0d0d0e] border border-zinc-800 rounded-2xl p-6">
                    <h3 className="text-sm font-semibold mb-6 flex items-center gap-2">
                      <TrendingUp className="w-4 h-4 text-green-500" />
                      Materiality Scores
                    </h3>
                    <div className="h-64">
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={chartData}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#27272a" vertical={false} />
                          <XAxis dataKey="time" stroke="#71717a" fontSize={10} tickLine={false} axisLine={false} />
                          <YAxis stroke="#71717a" fontSize={10} tickLine={false} axisLine={false} unit="%" />
                          <Tooltip 
                            contentStyle={{ backgroundColor: '#18181b', border: '1px solid #27272a', borderRadius: '8px' }}
                            itemStyle={{ color: '#10b981' }}
                          />
                          <Line type="monotone" dataKey="materiality" stroke="#10b981" strokeWidth={2} dot={false} />
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                </div>

                {/* Recent Events Table */}
                <div className="bg-[#0d0d0e] border border-zinc-800 rounded-2xl overflow-hidden">
                  <div className="p-6 border-b border-zinc-800 flex items-center justify-between">
                    <h3 className="text-sm font-semibold">Recent Pipeline Events</h3>
                    <button onClick={fetchEvents} className="text-xs text-blue-500 hover:text-blue-400 font-medium">Refresh</button>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm">
                      <thead>
                        <tr className="bg-zinc-900/50 text-zinc-500 border-b border-zinc-800">
                          <th className="px-6 py-4 font-medium">Timestamp</th>
                          <th className="px-6 py-4 font-medium">Source</th>
                          <th className="px-6 py-4 font-medium">Headline</th>
                          <th className="px-6 py-4 font-medium">Classification</th>
                          <th className="px-6 py-4 font-medium">Materiality</th>
                          <th className="px-6 py-4 font-medium">Status</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-zinc-800">
                        {events.slice(0, 10).map((event) => (
                          <tr key={event.id} className="hover:bg-zinc-900/30 transition-colors group">
                            <td className="px-6 py-4 text-zinc-500 font-mono text-xs">
                              {new Date(event.timestamp).toLocaleTimeString()}
                            </td>
                            <td className="px-6 py-4">
                              <span className={cn(
                                "px-2 py-1 rounded-md text-[10px] font-bold uppercase",
                                event.source_type === "TWITTER" 
                                  ? "bg-sky-500/10 text-sky-500" 
                                  : "bg-violet-500/10 text-violet-500"
                              )}>
                                {event.source_type}
                              </span>
                            </td>
                            <td className="px-6 py-4 max-w-md">
                              <p className="truncate text-zinc-300 group-hover:text-white transition-colors">{event.headline}</p>
                              <p className="text-[10px] text-zinc-600 mt-1">{event.source}</p>
                            </td>
                            <td className="px-6 py-4">
                              <span className={cn(
                                "px-2 py-1 rounded-md text-[10px] font-bold uppercase tracking-wider",
                                event.classification === "YES" ? "bg-green-500/10 text-green-500" :
                                event.classification === "NO" ? "bg-red-500/10 text-red-500" :
                                "bg-zinc-800 text-zinc-400"
                              )}>
                                {event.classification}
                              </span>
                            </td>
                            <td className="px-6 py-4 font-mono text-xs">
                              {(event.materiality * 100).toFixed(1)}%
                            </td>
                            <td className="px-6 py-4">
                              {event.trade_executed ? (
                                <div className="flex items-center gap-1.5 text-green-500 text-xs font-medium">
                                  <CheckCircle2 className="w-3.5 h-3.5" />
                                  Executed
                                </div>
                              ) : (
                                <div className="flex items-center gap-1.5 text-zinc-600 text-xs">
                                  <XCircle className="w-3.5 h-3.5" />
                                  Skipped
                                </div>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </motion.div>
            )}

            {activeTab === "logs" && (
              <motion.div 
                key="logs"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="bg-[#0d0d0e] border border-zinc-800 rounded-2xl p-6 h-[calc(100vh-12rem)] flex flex-col"
              >
                <div className="flex items-center justify-between mb-6">
                  <h3 className="text-sm font-semibold flex items-center gap-2">
                    <Terminal className="w-4 h-4 text-blue-500" />
                    System Execution Logs
                  </h3>
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-mono text-zinc-500">Auto-scrolling enabled</span>
                  </div>
                </div>
                <div className="flex-1 bg-black rounded-xl p-4 font-mono text-xs overflow-y-auto space-y-2 border border-zinc-800 shadow-inner">
                  {events.map((e) => (
                    <div key={e.id} className="border-l-2 border-zinc-800 pl-3 py-1 hover:border-blue-500 transition-colors">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-zinc-600">[{new Date(e.timestamp).toLocaleTimeString()}]</span>
                        <span className="text-blue-400 font-bold uppercase">{e.source}</span>
                        <span className="text-zinc-500">→</span>
                        <span className="text-zinc-300 truncate">{e.headline}</span>
                      </div>
                      <div className="grid grid-cols-2 gap-4 text-[10px]">
                        <div className="text-zinc-500 italic">
                          Reasoning: {e.reasoning}
                        </div>
                        <div className="text-right space-x-3">
                          <span className={e.classification === 'YES' ? 'text-green-500' : e.classification === 'NO' ? 'text-red-500' : 'text-zinc-500'}>
                            DIR: {e.classification}
                          </span>
                          <span className="text-zinc-400">MAT: {(e.materiality * 100).toFixed(1)}%</span>
                          <span className="text-zinc-400">LAT: {e.latency_ms}ms</span>
                        </div>
                      </div>
                    </div>
                  ))}
                  {events.length === 0 && (
                    <div className="h-full flex items-center justify-center text-zinc-600">
                      Waiting for incoming events...
                    </div>
                  )}
                </div>
              </motion.div>
            )}

            {activeTab === "backtest" && (
              <motion.div 
                key="backtest"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="space-y-8"
              >
                <div className="bg-[#0d0d0e] border border-zinc-800 rounded-2xl p-8">
                  <div className="flex items-center justify-between mb-8">
                    <div>
                      <h3 className="text-lg font-bold mb-1">Historical Backtesting</h3>
                      <p className="text-sm text-zinc-500">Simulate bot performance against historical news events and market outcomes.</p>
                    </div>
                    <button 
                      onClick={runBacktest}
                      disabled={isBacktesting || isRunning}
                      className={cn(
                        "px-6 py-2 rounded-xl text-sm font-bold transition-all flex items-center gap-2",
                        isBacktesting || isRunning
                          ? "bg-zinc-800 text-zinc-500 cursor-not-allowed"
                          : "bg-blue-600 text-white hover:bg-blue-500 shadow-lg shadow-blue-900/20"
                      )}
                    >
                      {isBacktesting ? <Activity className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4 fill-current" />}
                      {isBacktesting ? "Running Simulation..." : "Run Backtest"}
                    </button>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                    <div className="space-y-4">
                      <h4 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">Simulation Parameters</h4>
                      <div className="space-y-4">
                        <div className="p-4 rounded-xl bg-zinc-900 border border-zinc-800">
                          <label className="text-xs text-zinc-500 block mb-2">Dataset</label>
                          <div className="text-sm font-mono text-zinc-300">bot/historical_data.json</div>
                        </div>
                        <div className="p-4 rounded-xl bg-zinc-900 border border-zinc-800">
                          <label className="text-xs text-zinc-500 block mb-2">Initial Balance</label>
                          <div className="text-sm font-mono text-zinc-300">$1,000.00 USDC</div>
                        </div>
                      </div>
                    </div>
                    <div className="space-y-4">
                      <h4 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">Backtest Logic</h4>
                      <ul className="space-y-2 text-xs text-zinc-400">
                        <li className="flex items-center gap-2">
                          <CheckCircle2 className="w-3 h-3 text-blue-500" />
                          Uses live Gemini 1.5 Flash classification
                        </li>
                        <li className="flex items-center gap-2">
                          <CheckCircle2 className="w-3 h-3 text-blue-500" />
                          Applies current materiality thresholds
                        </li>
                        <li className="flex items-center gap-2">
                          <CheckCircle2 className="w-3 h-3 text-blue-500" />
                          Calculates PnL based on binary market outcomes
                        </li>
                      </ul>
                    </div>
                  </div>
                </div>

                {/* Results will appear in the dashboard stats and logs once completed */}
                <div className="p-4 rounded-xl bg-blue-500/5 border border-blue-500/20 flex gap-4">
                  <AlertCircle className="w-5 h-5 text-blue-500 shrink-0" />
                  <div className="text-xs text-zinc-400 leading-relaxed">
                    Backtest results are logged to the system database. You can view the simulated trades in the <span className="text-blue-400 font-semibold">Dashboard</span> and <span className="text-blue-400 font-semibold">Live Logs</span> tabs after completion.
                  </div>
                </div>
              </motion.div>
            )}

            {activeTab === "settings" && (
              <motion.div 
                key="settings"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                className="max-w-2xl"
              >
                <div className="bg-[#0d0d0e] border border-zinc-800 rounded-2xl p-8 space-y-8">
                  <div>
                    <h3 className="text-lg font-bold mb-1">Bot Configuration</h3>
                    <p className="text-sm text-zinc-500">Adjust thresholds and network parameters for the execution pipeline.</p>
                  </div>

                  <div className="space-y-6">
                    <div className="space-y-3">
                      <label className="text-sm font-medium text-zinc-300">Execution Mode</label>
                      <div className="grid grid-cols-2 gap-4">
                        <button 
                          onClick={() => setIsLiveMode(false)}
                          className={cn(
                            "p-4 rounded-xl border text-left transition-all",
                            !isLiveMode ? "border-blue-500 bg-blue-500/5 ring-1 ring-blue-500/20" : "border-zinc-800 bg-zinc-900/50 hover:border-zinc-700"
                          )}
                        >
                          <Shield className={cn("w-5 h-5 mb-2", !isLiveMode ? "text-blue-500" : "text-zinc-500")} />
                          <div className="font-bold text-sm">Dry Run</div>
                          <div className="text-[10px] text-zinc-500 mt-1">Simulate trades without using real funds.</div>
                        </button>
                        <button 
                          onClick={() => setIsLiveMode(true)}
                          className={cn(
                            "p-4 rounded-xl border text-left transition-all",
                            isLiveMode ? "border-red-500 bg-red-500/5 ring-1 ring-red-500/20" : "border-zinc-800 bg-zinc-900/50 hover:border-zinc-700"
                          )}
                        >
                          <Zap className={cn("w-5 h-5 mb-2", isLiveMode ? "text-red-500" : "text-zinc-500")} />
                          <div className="font-bold text-sm">Live Trading</div>
                          <div className="text-[10px] text-zinc-500 mt-1">Execute real orders on Base network.</div>
                        </button>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-6">
                      <div className="space-y-2">
                        <label className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">Min Materiality</label>
                        <input 
                          type="number" 
                          defaultValue="0.6" 
                          step="0.1"
                          className="w-full bg-zinc-900 border border-zinc-800 rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all"
                        />
                      </div>
                      <div className="space-y-2">
                        <label className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">Max Bet Size (USDC)</label>
                        <input 
                          type="number" 
                          defaultValue="50" 
                          className="w-full bg-zinc-900 border border-zinc-800 rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all"
                        />
                      </div>
                    </div>

                    <div className="p-4 rounded-xl bg-blue-500/5 border border-blue-500/20 flex gap-4">
                      <AlertCircle className="w-5 h-5 text-blue-500 shrink-0" />
                      <div className="text-xs text-zinc-400 leading-relaxed">
                        The bot uses <span className="text-blue-400 font-semibold">Gemini 1.5 Flash</span> for sub-second classification. Ensure your <span className="text-zinc-200 font-mono">GEMINI_API_KEY</span> is set in the environment variables.
                      </div>
                    </div>

                    <button className="w-full py-3 bg-zinc-100 text-black font-bold rounded-xl hover:bg-white transition-colors">
                      Save Configuration
                    </button>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </main>
    </div>
  );
}

function NavItem({ active, onClick, icon, label }: { active: boolean, onClick: () => void, icon: React.ReactNode, label: string }) {
  return (
    <button 
      onClick={onClick}
      className={cn(
        "w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all group",
        active 
          ? "bg-blue-600/10 text-blue-500 border border-blue-500/20" 
          : "text-zinc-500 hover:text-zinc-300 hover:bg-zinc-900"
      )}
    >
      <span className={cn("transition-colors", active ? "text-blue-500" : "text-zinc-500 group-hover:text-zinc-400")}>
        {icon}
      </span>
      {label}
    </button>
  );
}

function StatCard({ title, value, icon, trend }: { title: string, value: string | number, icon: React.ReactNode, trend: string }) {
  return (
    <div className="bg-[#0d0d0e] border border-zinc-800 rounded-2xl p-6 hover:border-zinc-700 transition-all group">
      <div className="flex items-center justify-between mb-4">
        <div className="w-10 h-10 rounded-xl bg-zinc-900 flex items-center justify-center border border-zinc-800 group-hover:border-zinc-700 transition-all">
          {icon}
        </div>
        <span className="text-[10px] font-mono text-zinc-600">{trend}</span>
      </div>
      <div className="space-y-1">
        <p className="text-xs font-medium text-zinc-500 uppercase tracking-wider">{title}</p>
        <p className="text-2xl font-bold text-white tracking-tight">{value}</p>
      </div>
    </div>
  );
}
