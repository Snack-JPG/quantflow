'use client'

import { useCallback, useEffect, useState, useRef } from 'react'
import { AlertTriangle, Info, AlertCircle, TrendingUp, Shield, Eye, type LucideIcon } from 'lucide-react'

interface Alert {
  id: string
  timestamp: string
  pattern: string
  severity: 'info' | 'warning' | 'critical'
  confidence: number
  exchange: string
  symbol: string
  context: Record<string, unknown>
  explanation: string
  ai_generated: boolean
}

interface AlertSocketMessage {
  type: string
  data?: Alert
}

// Map pattern names to icons
const patternIcons: Record<string, LucideIcon> = {
  spoofing: Shield,
  layering: TrendingUp,
  walls: Eye,
  iceberg: Eye,
  momentum_ignition: TrendingUp,
  wash_trading: AlertTriangle,
  tape_painting: TrendingUp,
  front_running: AlertTriangle,
  complex_manipulation: AlertCircle
}

// Map severity to colors and icons
const severityConfig = {
  info: {
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-200',
    textColor: 'text-blue-800',
    badgeBg: 'bg-blue-100',
    badgeText: 'text-blue-700',
    icon: Info
  },
  warning: {
    bgColor: 'bg-yellow-50',
    borderColor: 'border-yellow-200',
    textColor: 'text-yellow-800',
    badgeBg: 'bg-yellow-100',
    badgeText: 'text-yellow-700',
    icon: AlertTriangle
  },
  critical: {
    bgColor: 'bg-red-50',
    borderColor: 'border-red-200',
    textColor: 'text-red-800',
    badgeBg: 'bg-red-100',
    badgeText: 'text-red-700',
    icon: AlertCircle
  }
}

export default function AlertFeed({ maxAlerts = 20 }: { maxAlerts?: number }) {
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [isConnected, setIsConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  const fetchAlerts = useCallback(async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/alerts?limit=${maxAlerts}`)
      if (response.ok) {
        const data = await response.json()
        setAlerts(data.alerts || [])
      }
    } catch (error) {
      console.error('Error fetching alerts:', error)
    }
  }, [maxAlerts])

  const connectWebSocket = useCallback(() => {
    const wsUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws'

    try {
      const ws = new WebSocket(wsUrl)
      wsRef.current = ws

      ws.onopen = () => {
        console.log('AlertFeed WebSocket connected')
        setIsConnected(true)
        // Clear any reconnect timeout
        if (reconnectTimeoutRef.current) {
          clearTimeout(reconnectTimeoutRef.current)
        }
      }

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data) as AlertSocketMessage
          if (message.type === 'alert' && message.data) {
            const newAlert = message.data
            setAlerts(prev => {
              // Add new alert at the beginning, limit to maxAlerts
              const updated = [newAlert, ...prev].slice(0, maxAlerts)
              return updated
            })
          }
        } catch (error) {
          console.error('Error parsing WebSocket message:', error)
        }
      }

      ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        setIsConnected(false)
      }

      ws.onclose = () => {
        console.log('WebSocket disconnected')
        setIsConnected(false)
        wsRef.current = null

        // Attempt to reconnect after 3 seconds
        reconnectTimeoutRef.current = setTimeout(() => {
          console.log('Attempting to reconnect WebSocket...')
          connectWebSocket()
        }, 3000)
      }
    } catch (error) {
      console.error('Error creating WebSocket connection:', error)
      setIsConnected(false)
    }
  }, [maxAlerts])

  useEffect(() => {
    fetchAlerts()
    connectWebSocket()

    return () => {
      if (wsRef.current) {
        wsRef.current.close()
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
    }
  }, [connectWebSocket, fetchAlerts])

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp)
    const now = new Date()
    const diff = now.getTime() - date.getTime()

    if (diff < 60000) {
      return 'Just now'
    } else if (diff < 3600000) {
      const minutes = Math.floor(diff / 60000)
      return `${minutes}m ago`
    } else if (diff < 86400000) {
      const hours = Math.floor(diff / 3600000)
      return `${hours}h ago`
    } else {
      return date.toLocaleDateString() + ' ' + date.toLocaleTimeString()
    }
  }

  const formatPatternName = (pattern: string) => {
    return pattern.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
  }

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold text-gray-800">Pattern Detection Alerts</h2>
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
          <span className="text-xs text-gray-500">
            {isConnected ? 'Live' : 'Disconnected'}
          </span>
        </div>
      </div>

      {alerts.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          <AlertCircle className="mx-auto h-12 w-12 text-gray-400 mb-3" />
          <p>No alerts detected yet</p>
          <p className="text-sm mt-1">Monitoring for market manipulation patterns...</p>
        </div>
      ) : (
        <div className="space-y-3 max-h-[600px] overflow-y-auto">
          {alerts.map((alert) => {
            const config = severityConfig[alert.severity]
            const PatternIcon = patternIcons[alert.pattern] || AlertCircle
            const SeverityIcon = config.icon

            return (
              <div
                key={alert.id}
                className={`${config.bgColor} ${config.borderColor} border rounded-lg p-4 transition-all hover:shadow-md`}
              >
                <div className="flex items-start gap-3">
                  <div className={`${config.badgeBg} rounded-lg p-2`}>
                    <PatternIcon className={`h-5 w-5 ${config.badgeText}`} />
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`font-semibold ${config.textColor}`}>
                        {formatPatternName(alert.pattern)}
                      </span>

                      {/* Severity badge */}
                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${config.badgeBg} ${config.badgeText}`}>
                        <SeverityIcon className="h-3 w-3" />
                        {alert.severity.toUpperCase()}
                      </span>

                      {/* Confidence badge */}
                      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-700">
                        {Math.round(alert.confidence * 100)}% conf
                      </span>

                      {/* AI badge if applicable */}
                      {alert.ai_generated && (
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-700">
                          AI
                        </span>
                      )}
                    </div>

                    <p className="text-sm text-gray-700 mb-2">
                      {alert.explanation}
                    </p>

                    <div className="flex items-center gap-4 text-xs text-gray-500">
                      <span>{alert.exchange.toUpperCase()}</span>
                      <span>{alert.symbol}</span>
                      <span>{formatTimestamp(alert.timestamp)}</span>
                    </div>

                    {/* Show context details for critical alerts */}
                    {alert.severity === 'critical' && alert.context && Object.keys(alert.context).length > 0 && (
                      <div className="mt-2 pt-2 border-t border-gray-200">
                        <details className="text-xs">
                          <summary className="cursor-pointer text-gray-600 hover:text-gray-800">
                            View details
                          </summary>
                          <div className="mt-2 p-2 bg-gray-50 rounded">
                            <pre className="text-gray-700 overflow-x-auto">
                              {JSON.stringify(alert.context, null, 2)}
                            </pre>
                          </div>
                        </details>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
