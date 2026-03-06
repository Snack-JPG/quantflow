'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  Activity,
  BarChart3,
  Beaker,
  Terminal,
  Settings
} from 'lucide-react';

const navItems = [
  {
    name: 'Live Trading',
    path: '/',
    icon: Activity,
    description: 'Real-time order book & market data'
  },
  {
    name: 'Analysis Lab',
    path: '/analysis',
    icon: BarChart3,
    description: 'Market microstructure analytics'
  },
  {
    name: 'Strategy Builder',
    path: '/strategy',
    icon: Beaker,
    description: 'Backtest & optimize strategies'
  },
  {
    name: 'Research Console',
    path: '/research',
    icon: Terminal,
    description: 'Natural language queries & AI insights'
  },
];

export function Navigation() {
  const pathname = usePathname();

  return (
    <nav className="bg-zinc-950 border-b border-zinc-800">
      <div className="max-w-[1920px] mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <div className="flex items-center gap-8">
            <Link href="/" className="flex items-center gap-2">
              <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-sm">QF</span>
              </div>
              <span className="text-xl font-bold text-white">QuantFlow</span>
            </Link>

            {/* Main Navigation */}
            <div className="hidden md:flex items-center gap-1">
              {navItems.map((item) => {
                const Icon = item.icon;
                const isActive = pathname === item.path;

                return (
                  <Link
                    key={item.path}
                    href={item.path}
                    className={`
                      flex items-center gap-2 px-4 py-2 rounded-lg transition-all duration-200
                      ${isActive
                        ? 'bg-zinc-800 text-white'
                        : 'text-zinc-400 hover:text-white hover:bg-zinc-900'
                      }
                    `}
                  >
                    <Icon className="w-4 h-4" />
                    <span className="text-sm font-medium">{item.name}</span>
                  </Link>
                );
              })}
            </div>
          </div>

          {/* Right Section */}
          <div className="flex items-center gap-4">
            {/* Connection Status */}
            <div className="flex items-center gap-2 px-3 py-1.5 bg-zinc-900 rounded-lg">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
              <span className="text-xs text-zinc-400">Connected</span>
            </div>

            {/* Settings */}
            <button className="p-2 text-zinc-400 hover:text-white transition-colors">
              <Settings className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>
    </nav>
  );
}
