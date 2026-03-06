'use client';

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Terminal, Search, Send, Download, Copy, Sparkles, Database, TrendingUp, AlertCircle } from 'lucide-react';

interface QueryEvent {
  time: string;
  exchange: string;
  type: string;
  size: string;
  confidence: number;
}

interface QueryResultPayload {
  analysis?: string;
  metrics?: Record<string, string | number>;
  events?: QueryEvent[];
  summary?: string;
  statistics?: Record<string, string | number>;
  interpretation?: string;
  message?: string;
  dataPoints?: number;
  timeRange?: string;
  confidence?: number;
  [key: string]: unknown;
}

interface QueryResult {
  id: string;
  query: string;
  timestamp: number;
  type: 'data' | 'analysis' | 'commentary' | 'error';
  result: QueryResultPayload;
}

const sampleQueries = [
  "Show me all spoofing events in the last 24 hours",
  "What happened at 14:32 when BTC dropped 2%?",
  "Calculate average VPIN during volatile periods",
  "Find correlations between order flow imbalance and price movements",
  "Identify all large trades (>$100k) today",
  "Show regime changes in the past week",
  "Compare bid-ask spreads across exchanges",
  "Analyze Kyle's Lambda trends",
];

export default function ResearchConsolePage() {
  const [query, setQuery] = useState('');
  const [queryHistory, setQueryHistory] = useState<QueryResult[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [selectedExport, setSelectedExport] = useState<'csv' | 'json'>('csv');

  const processQuery = async (queryText: string) => {
    setIsProcessing(true);

    // Simulate processing delay
    await new Promise(resolve => setTimeout(resolve, 1500));

    // Generate mock response based on query type
    let result: QueryResult;

    if (queryText.toLowerCase().includes('spoofing')) {
      result = {
        id: Date.now().toString(),
        query: queryText,
        timestamp: Date.now(),
        type: 'data',
        result: {
          events: [
            { time: '14:32:15', exchange: 'Binance', type: 'Layering', size: '$45,000', confidence: 0.92 },
            { time: '15:18:22', exchange: 'Coinbase', type: 'Spoofing', size: '$78,000', confidence: 0.87 },
            { time: '16:45:10', exchange: 'Kraken', type: 'Momentum Ignition', size: '$120,000', confidence: 0.95 },
          ],
          summary: 'Found 3 potential manipulation events in the last 24 hours',
        }
      };
    } else if (queryText.toLowerCase().includes('what happened')) {
      result = {
        id: Date.now().toString(),
        query: queryText,
        timestamp: Date.now(),
        type: 'commentary',
        result: {
          analysis: `At 14:32, a significant market event occurred:

1. **Large Sell Order**: A $2.5M market sell order hit Binance, causing immediate price impact
2. **Cascade Effect**: Stop losses triggered between $44,800-$44,500
3. **Order Book Imbalance**: Bid depth dropped 65% within 30 seconds
4. **Cross-Exchange Arbitrage**: Price divergence reached 0.8% triggering arbitrage bots
5. **Recovery**: Market makers stepped in at $44,200 support level

The event appears to be a liquidation cascade rather than coordinated manipulation.`,
          metrics: {
            priceChange: -2.1,
            volumeSpike: 450,
            vpinPeak: 0.78,
            recoveryTime: '3 minutes',
          }
        }
      };
    } else if (queryText.toLowerCase().includes('vpin')) {
      result = {
        id: Date.now().toString(),
        query: queryText,
        timestamp: Date.now(),
        type: 'analysis',
        result: {
          statistics: {
            avgVPIN: 0.52,
            stdDev: 0.15,
            maxVPIN: 0.84,
            volatilePeriods: 8,
            correlation: 0.73,
          },
          chart: 'vpin_volatile_periods.png',
          interpretation: 'VPIN averaged 0.52 during volatile periods (σ > 0.03), indicating moderate toxicity. Peak values > 0.7 preceded 75% of major price moves.',
        }
      };
    } else {
      result = {
        id: Date.now().toString(),
        query: queryText,
        timestamp: Date.now(),
        type: 'data',
        result: {
          message: 'Query processed successfully',
          dataPoints: Math.floor(Math.random() * 1000),
          timeRange: '24 hours',
          confidence: 0.85 + Math.random() * 0.15,
        }
      };
    }

    setQueryHistory(prev => [result, ...prev]);
    setIsProcessing(false);
    setQuery('');
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      processQuery(query);
    }
  };

  const exportData = (result: QueryResult) => {
    const dataStr = selectedExport === 'json'
      ? JSON.stringify(result.result, null, 2)
      : Object.entries(result.result).map(([k, v]) => `${k},${v}`).join('\n');

    const blob = new Blob([dataStr], { type: selectedExport === 'json' ? 'application/json' : 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `research_${result.id}.${selectedExport}`;
    a.click();
  };

  const formatTime = (timestamp: number) => {
    return new Date(timestamp).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  return (
    <div className="min-h-screen bg-zinc-950 p-4">
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="max-w-[1400px] mx-auto"
      >
        {/* Header */}
        <div className="mb-6 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Terminal className="w-6 h-6 text-cyan-500" />
            <h1 className="text-2xl font-bold text-white">Research Console</h1>
          </div>
          <div className="flex items-center gap-3">
            <select
              value={selectedExport}
              onChange={(e) => setSelectedExport(e.target.value as 'csv' | 'json')}
              className="bg-zinc-900 border border-zinc-800 rounded-lg px-3 py-2 text-sm text-white"
            >
              <option value="csv">Export as CSV</option>
              <option value="json">Export as JSON</option>
            </select>
          </div>
        </div>

        {/* Query Input */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-zinc-900 rounded-lg border border-zinc-800 p-4 mb-4"
        >
          <form onSubmit={handleSubmit} className="flex gap-3">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Ask anything about your market data..."
                className="w-full bg-zinc-950 border border-zinc-800 rounded-lg pl-10 pr-4 py-3 text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-cyan-600"
                disabled={isProcessing}
              />
            </div>
            <button
              type="submit"
              disabled={!query.trim() || isProcessing}
              className="px-6 py-3 bg-cyan-600 text-white rounded-lg hover:bg-cyan-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {isProcessing ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  Processing...
                </>
              ) : (
                <>
                  <Send className="w-4 h-4" />
                  Send Query
                </>
              )}
            </button>
          </form>

          {/* Sample Queries */}
          <div className="mt-3 flex items-center gap-2 flex-wrap">
            <span className="text-xs text-zinc-500">Try:</span>
            {sampleQueries.slice(0, 3).map(sample => (
              <button
                key={sample}
                onClick={() => setQuery(sample)}
                className="text-xs px-2 py-1 bg-zinc-950 text-cyan-400 rounded hover:bg-zinc-800 transition-colors"
              >
                {sample}
              </button>
            ))}
          </div>
        </motion.div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-12 gap-4">
          {/* Query Results */}
          <div className="col-span-12 lg:col-span-8 space-y-4">
            <AnimatePresence mode="popLayout">
              {queryHistory.map((result, index) => (
                <motion.div
                  key={result.id}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 20 }}
                  transition={{ delay: index * 0.05 }}
                  className="bg-zinc-900 rounded-lg border border-zinc-800"
                >
                  <div className="p-4 border-b border-zinc-800">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          {result.type === 'commentary' && <Sparkles className="w-4 h-4 text-purple-500" />}
                          {result.type === 'data' && <Database className="w-4 h-4 text-blue-500" />}
                          {result.type === 'analysis' && <TrendingUp className="w-4 h-4 text-green-500" />}
                          {result.type === 'error' && <AlertCircle className="w-4 h-4 text-red-500" />}
                          <span className="text-xs text-zinc-500">{formatTime(result.timestamp)}</span>
                        </div>
                        <div className="text-sm text-white font-medium">{result.query}</div>
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => navigator.clipboard.writeText(JSON.stringify(result.result))}
                          className="p-1 text-zinc-500 hover:text-white transition-colors"
                        >
                          <Copy className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => exportData(result)}
                          className="p-1 text-zinc-500 hover:text-white transition-colors"
                        >
                          <Download className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  </div>

                  <div className="p-4">
                    {result.type === 'commentary' && result.result.analysis && (
                      <div className="space-y-3">
                        <div className="prose prose-sm prose-invert max-w-none">
                          <div className="text-sm text-zinc-300 whitespace-pre-line">
                            {result.result.analysis}
                          </div>
                        </div>
                        {result.result.metrics && (
                          <div className="grid grid-cols-4 gap-3 mt-4">
                            {Object.entries(
                              result.result.metrics as Record<string, string | number>
                            ).map(([key, value]) => (
                              <div key={key} className="bg-zinc-950 rounded-lg p-2">
                                <div className="text-[10px] text-zinc-500 capitalize">
                                  {key.replace(/([A-Z])/g, ' $1').trim()}
                                </div>
                                <div className="text-sm font-mono text-white">
                                  {typeof value === 'number' ? value.toFixed(2) : value}
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}

                    {result.type === 'data' && result.result.events && (
                      <div className="overflow-x-auto">
                        <table className="w-full text-xs">
                          <thead>
                            <tr className="border-b border-zinc-800">
                              <th className="text-left p-2 text-zinc-500">Time</th>
                              <th className="text-left p-2 text-zinc-500">Exchange</th>
                              <th className="text-left p-2 text-zinc-500">Type</th>
                              <th className="text-right p-2 text-zinc-500">Size</th>
                              <th className="text-right p-2 text-zinc-500">Confidence</th>
                            </tr>
                          </thead>
                          <tbody>
                            {result.result.events.map((event, i) => (
                              <tr key={i} className="border-b border-zinc-800/50">
                                <td className="p-2 text-zinc-400">{event.time}</td>
                                <td className="p-2 text-zinc-400">{event.exchange}</td>
                                <td className="p-2">
                                  <span className="px-2 py-0.5 bg-yellow-500/20 text-yellow-400 rounded text-[10px]">
                                    {event.type}
                                  </span>
                                </td>
                                <td className="p-2 text-right font-mono text-zinc-300">{event.size}</td>
                                <td className="p-2 text-right">
                                  <span className={`font-mono ${
                                    event.confidence > 0.9 ? 'text-green-400' : 'text-yellow-400'
                                  }`}>
                                    {(event.confidence * 100).toFixed(0)}%
                                  </span>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                        {result.result.summary && (
                          <div className="mt-3 p-2 bg-zinc-950 rounded text-xs text-zinc-400">
                            {result.result.summary}
                          </div>
                        )}
                      </div>
                    )}

                    {result.type === 'analysis' && result.result.statistics && (
                      <div className="space-y-3">
                        <div className="grid grid-cols-3 gap-3">
                          {Object.entries(
                            result.result.statistics as Record<string, string | number>
                          ).map(([key, value]) => (
                            <div key={key} className="bg-zinc-950 rounded-lg p-3">
                              <div className="text-xs text-zinc-500 capitalize mb-1">
                                {key.replace(/([A-Z])/g, ' $1').trim()}
                              </div>
                              <div className="text-lg font-mono text-white">
                                {typeof value === 'number' ? value.toFixed(3) : value}
                              </div>
                            </div>
                          ))}
                        </div>
                        {result.result.interpretation && (
                          <div className="p-3 bg-blue-500/10 border border-blue-500/30 rounded-lg">
                            <p className="text-xs text-blue-300">
                              {result.result.interpretation}
                            </p>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Default display for other result types */}
                    {!result.result.analysis && !result.result.events && !result.result.statistics && (
                      <pre className="text-xs text-zinc-300 font-mono whitespace-pre-wrap">
                        {JSON.stringify(result.result, null, 2)}
                      </pre>
                    )}
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>

            {queryHistory.length === 0 && !isProcessing && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="bg-zinc-900 rounded-lg border border-zinc-800 p-12 text-center"
              >
                <Terminal className="w-16 h-16 text-zinc-700 mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-white mb-2">
                  Natural Language Query Interface
                </h3>
                <p className="text-sm text-zinc-500 mb-6 max-w-md mx-auto">
                  Ask questions about your market data in plain English.
                  Get instant analysis, AI-powered insights, and exportable results.
                </p>
                <div className="space-y-2">
                  {sampleQueries.slice(3, 6).map(sample => (
                    <button
                      key={sample}
                      onClick={() => setQuery(sample)}
                      className="block w-full text-left px-4 py-2 bg-zinc-950 text-cyan-400 rounded-lg hover:bg-zinc-800 transition-colors text-sm"
                    >
                      → {sample}
                    </button>
                  ))}
                </div>
              </motion.div>
            )}
          </div>

          {/* Right Sidebar */}
          <div className="col-span-12 lg:col-span-4 space-y-4">
            {/* AI Market Commentary */}
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              className="bg-zinc-900 rounded-lg border border-zinc-800 p-4"
            >
              <div className="flex items-center gap-2 mb-3">
                <Sparkles className="w-4 h-4 text-purple-500" />
                <h3 className="text-sm font-semibold text-white">AI Market Commentary</h3>
              </div>
              <div className="space-y-3">
                <div className="p-3 bg-zinc-950 rounded-lg">
                  <div className="text-xs text-purple-400 mb-1">Current Market State</div>
                  <p className="text-xs text-zinc-300">
                    Market showing signs of accumulation phase. Order flow imbalance
                    favoring buyers (62/38 ratio) with decreasing VPIN suggesting
                    lower toxicity. Expect range-bound action until $46,500 resistance.
                  </p>
                </div>
                <div className="p-3 bg-zinc-950 rounded-lg">
                  <div className="text-xs text-yellow-400 mb-1">Anomaly Alert</div>
                  <p className="text-xs text-zinc-300">
                    Detected unusual order clustering at $45,200 across 3 exchanges.
                    Pattern consistent with institutional accumulation. Monitor for
                    potential breakout.
                  </p>
                </div>
                <div className="p-3 bg-zinc-950 rounded-lg">
                  <div className="text-xs text-cyan-400 mb-1">Regime Forecast</div>
                  <p className="text-xs text-zinc-300">
                    Hurst exponent trending toward 0.6+ indicating shift from
                    mean-reverting to trending regime. Consider trend-following
                    strategies in next 4-6 hours.
                  </p>
                </div>
              </div>
            </motion.div>

            {/* Quick Stats */}
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.1 }}
              className="bg-zinc-900 rounded-lg border border-zinc-800 p-4"
            >
              <h3 className="text-sm font-semibold text-white mb-3">Research Statistics</h3>
              <div className="space-y-2">
                <div className="flex justify-between text-xs">
                  <span className="text-zinc-500">Queries Today</span>
                  <span className="text-white font-mono">{queryHistory.length}</span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-zinc-500">Data Points Analyzed</span>
                  <span className="text-white font-mono">1.2M</span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-zinc-500">Patterns Identified</span>
                  <span className="text-white font-mono">47</span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-zinc-500">Anomalies Detected</span>
                  <span className="text-yellow-400 font-mono">3</span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-zinc-500">API Response Time</span>
                  <span className="text-green-400 font-mono">142ms</span>
                </div>
              </div>
            </motion.div>

            {/* Sample Queries */}
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.2 }}
              className="bg-zinc-900 rounded-lg border border-zinc-800 p-4"
            >
              <h3 className="text-sm font-semibold text-white mb-3">Example Queries</h3>
              <div className="space-y-2">
                {sampleQueries.map(sample => (
                  <button
                    key={sample}
                    onClick={() => setQuery(sample)}
                    className="w-full text-left px-3 py-2 bg-zinc-950 text-xs text-zinc-400 rounded hover:bg-zinc-800 hover:text-cyan-400 transition-colors"
                  >
                    {sample}
                  </button>
                ))}
              </div>
            </motion.div>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
