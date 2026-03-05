'use client';

import { useEffect, useState } from 'react';
import { AlertTriangle, Info, AlertCircle, TrendingUp, Activity, Shield } from 'lucide-react';

interface Alert {
  id: string;
  timestamp: string;
  pattern: string;
  severity: 'info' | 'warning' | 'critical';
  confidence: number;
  exchange: string;
  symbol: string;
  context: Record<string, any>;
  explanation: string;
  ai_generated: boolean;
}

interface AlertFeedProps {
  maxAlerts?: number;
}

export default function AlertFeed({ maxAlerts = 50 }: AlertFeedProps) {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    // Fetch initial alerts
    fetchAlerts();

    // Set up WebSocket connection for real-time alerts
    const ws = new WebSocket(`${process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000'}/ws`);

    ws.onopen = () => {
      console.log('Connected to alert stream');
      setConnected(true);
    };

    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      if (message.type === 'alert') {
        const newAlert = message.data as Alert;
        setAlerts((prev) => [newAlert, ...prev].slice(0, maxAlerts));
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      setConnected(false);
    };

    ws.onclose = () => {
      console.log('Disconnected from alert stream');
      setConnected(false);
    };

    return () => {
      ws.close();
    };
  }, [maxAlerts]);

  const fetchAlerts = async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/alerts?limit=${maxAlerts}`);
      const data = await response.json();
      setAlerts(data.alerts || []);
    } catch (error) {
      console.error('Failed to fetch alerts:', error);
    }
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'critical':
        return <AlertTriangle className="w-5 h-5" />;
      case 'warning':
        return <AlertCircle className="w-5 h-5" />;
      default:
        return <Info className="w-5 h-5" />;
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'bg-red-900/20 border-red-500 text-red-400';
      case 'warning':
        return 'bg-yellow-900/20 border-yellow-500 text-yellow-400';
      default:
        return 'bg-blue-900/20 border-blue-500 text-blue-400';
    }
  };

  const getPatternIcon = (pattern: string) => {
    if (pattern.includes('spoofing') || pattern.includes('layering')) {
      return <Shield className="w-4 h-4" />;
    } else if (pattern.includes('momentum') || pattern.includes('ignition')) {
      return <TrendingUp className="w-4 h-4" />;
    } else {
      return <Activity className="w-4 h-4" />;
    }
  };

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      fractionalSecondDigits: 3,
    });
  };

  return (
    <div className="bg-gray-900 rounded-lg p-4 h-full">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold text-white">Pattern Detection Alerts</h3>
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${connected ? 'bg-green-500' : 'bg-red-500'}`} />
          <span className="text-xs text-gray-400">{connected ? 'Live' : 'Disconnected'}</span>
        </div>
      </div>

      <div className="space-y-2 overflow-y-auto max-h-[600px] custom-scrollbar">
        {alerts.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            No alerts detected yet. Monitoring for patterns...
          </div>
        ) : (
          alerts.map((alert) => (
            <div
              key={alert.id}
              className={`p-3 rounded-lg border ${getSeverityColor(alert.severity)} transition-all hover:opacity-80`}
            >
              <div className="flex items-start gap-3">
                <div className="flex-shrink-0 mt-0.5">
                  {getSeverityIcon(alert.severity)}
                </div>

                <div className="flex-grow min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <div className="flex items-center gap-1">
                      {getPatternIcon(alert.pattern)}
                      <span className="font-semibold capitalize">
                        {alert.pattern.replace(/_/g, ' ')}
                      </span>
                    </div>
                    {alert.ai_generated && (
                      <span className="px-2 py-0.5 bg-purple-900/30 border border-purple-500 text-purple-400 text-xs rounded">
                        AI
                      </span>
                    )}
                    <span className="text-xs opacity-75">
                      {alert.exchange}:{alert.symbol}
                    </span>
                  </div>

                  <p className="text-sm opacity-90 mb-2">
                    {alert.explanation}
                  </p>

                  <div className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-3">
                      <span className="opacity-60">
                        {formatTimestamp(alert.timestamp)}
                      </span>
                      <span className="opacity-60">
                        Confidence: {(alert.confidence * 100).toFixed(0)}%
                      </span>
                    </div>

                    {alert.context && Object.keys(alert.context).length > 0 && (
                      <button
                        onClick={() => console.log('Alert context:', alert.context)}
                        className="text-xs text-blue-400 hover:text-blue-300"
                      >
                        View Details
                      </button>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Alert Statistics */}
      <div className="mt-4 pt-4 border-t border-gray-800">
        <div className="grid grid-cols-3 gap-4 text-xs">
          <div className="text-center">
            <div className="text-red-400 font-semibold">
              {alerts.filter(a => a.severity === 'critical').length}
            </div>
            <div className="text-gray-500">Critical</div>
          </div>
          <div className="text-center">
            <div className="text-yellow-400 font-semibold">
              {alerts.filter(a => a.severity === 'warning').length}
            </div>
            <div className="text-gray-500">Warning</div>
          </div>
          <div className="text-center">
            <div className="text-blue-400 font-semibold">
              {alerts.filter(a => a.severity === 'info').length}
            </div>
            <div className="text-gray-500">Info</div>
          </div>
        </div>
      </div>
    </div>
  );
}