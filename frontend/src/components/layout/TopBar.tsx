import React, { useState, useEffect } from 'react';
import { MapPin, Clock, Bell, ChevronDown, Menu, LogOut } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { useReadinessQuery } from '@/queries/useHealthQuery';
import { fetchAlerts } from '@/api/alerts';
import { useAppStore } from '@/store/useAppStore';
import { useLocationStore } from '@/store/useLocationStore';

interface TopBarProps {
  onOpenMobileMenu?: () => void;
}

/** Aquora wave logo mark — three stacked teal & blue curves */
const WaveMark: React.FC = () => (
  <svg width="32" height="22" viewBox="0 0 32 22" fill="none" aria-hidden="true">
    <path d="M2 6 C6 2, 10 2, 14 6 C18 10, 22 10, 26 6" stroke="#008080" strokeWidth="2.5" strokeLinecap="round" fill="none"/>
    <path d="M2 11 C6 7, 10 7, 14 11 C18 15, 22 15, 26 11" stroke="#006666" strokeWidth="2.5" strokeLinecap="round" fill="none"/>
    <path d="M2 16 C6 12, 10 12, 14 16 C18 20, 22 20, 26 16" stroke="#1a56db" strokeWidth="2" strokeLinecap="round" fill="none" opacity="0.6"/>
  </svg>
);

export const TopBar: React.FC<TopBarProps> = ({ onOpenMobileMenu }) => {
  const { data: readiness } = useReadinessQuery();
  const { setActiveTab, navigateToLanding } = useAppStore();
  const { displayName, activeIntelligenceLevel } = useLocationStore();
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const isConnected = readiness?.status === 'ok' || readiness?.status === 'degraded';

  // Fetch real alerts count from backend
  const { data: alertsRes } = useQuery({
    queryKey: ['global-alerts-count'],
    queryFn: () => fetchAlerts(),
    refetchInterval: 20000,
    retry: false,
  });

  const activeAlertsCount = alertsRes?.alerts
    ? alertsRes.alerts.filter((a) => a.status === 'ACTIVE').length
    : 0;

  const [currentTime, setCurrentTime] = useState(() =>
    new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  );
  const currentDate = new Date().toLocaleDateString('en-GB', {
    weekday: 'short', day: 'numeric', month: 'short', year: 'numeric',
  });

  useEffect(() => {
    const id = setInterval(() => {
      setCurrentTime(new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }));
    }, 30_000);
    return () => clearInterval(id);
  }, []);

  return (
    <header
      className="h-[64px] shrink-0 z-30 flex items-center justify-between px-4 md:px-6 border-b select-none"
      style={{
        background: '#ffffff',
        borderColor: 'rgba(15,35,64,0.08)',
        boxShadow: '0 1px 2px rgba(15,35,64,0.03)',
      }}
    >
      {/* ── Left: brand identity ───────────────────────── */}
      <div className="flex items-center gap-3 min-w-0">
        {/* Mobile menu toggle */}
        {onOpenMobileMenu && (
          <button
            onClick={onOpenMobileMenu}
            className="md:hidden p-1.5 rounded-lg text-slate-500 hover:bg-slate-100 transition-colors"
            aria-label="Open navigation menu"
          >
            <Menu className="w-5 h-5" />
          </button>
        )}

        <div className="flex items-center gap-2.5 cursor-pointer" onClick={() => setActiveTab('overview')}>
          <WaveMark />

          <div className="flex flex-col leading-none">
            <span
              className="font-extrabold tracking-tight text-base"
              style={{ color: 'var(--aq-navy)', letterSpacing: '-0.02em' }}
            >
              AQUORA
            </span>
            <span className="hidden sm:block text-[11px] font-medium mt-0.5" style={{ color: 'var(--aq-text-muted)' }}>
              See the flood before it reaches the road.
            </span>
          </div>
        </div>
      </div>

      {/* ── Center: location + time ─────────────────────── */}
      <div className="hidden md:flex items-center gap-4 text-[12px]">
        <div className="flex items-center gap-2">
          <span className="flex items-center gap-1.5 font-semibold text-slate-700">
            <MapPin className="w-3.5 h-3.5 text-[#008080]" />
            {displayName}
          </span>
          <span
            className={`px-1.5 py-0.5 rounded text-[10px] font-bold tracking-wider uppercase ${
              activeIntelligenceLevel === 'DEEP'
                ? 'bg-teal-50 text-teal-700 border border-teal-200'
                : activeIntelligenceLevel === 'REGIONAL'
                ? 'bg-blue-50 text-blue-700 border border-blue-200'
                : 'bg-slate-100 text-slate-700 border border-slate-200'
            }`}
          >
            {activeIntelligenceLevel} ZONE
          </span>
        </div>
        <span className="w-px h-3.5 bg-slate-200" />
        <span className="flex items-center gap-1.5 font-medium text-slate-500">
          <Clock className="w-3.5 h-3.5 text-slate-400" />
          {currentDate} · {currentTime}
        </span>
      </div>

      {/* ── Right: env status + notification bell + user ── */}
      <div className="flex items-center gap-2.5">
        {/* Dynamic environment status badge */}
        {(() => {
          const env = readiness?.environment?.toLowerCase() || 'development';
          let label = 'Local environment';
          let isLive = false;

          if (isConnected) {
            if (env === 'production') {
              label = 'Live environment';
              isLive = true;
            } else if (env === 'staging') {
              label = 'Staging environment';
              isLive = true;
            } else {
              label = 'Local environment';
              isLive = true;
            }
          } else {
            label = 'Service unavailable';
            isLive = false;
          }

          return (
            <span
              className="hidden sm:flex items-center gap-1.5 text-[11px] font-semibold px-2.5 py-1 rounded-full border"
              style={{
                color: isLive ? '#008080' : '#d97706',
                background: isLive ? '#e6f2f2' : '#fffbeb',
                borderColor: isLive ? '#b2d8d8' : '#fde68a',
              }}
            >
              <span
                className="w-1.5 h-1.5 rounded-full aq-live-dot"
                style={{ background: isLive ? '#008080' : '#d97706' }}
              />
              {label}
            </span>
          );
        })()}

        {/* Global Functional Notification Bell Button */}
        <button
          onClick={() => setActiveTab('alerts')}
          className="relative p-2 rounded-xl text-slate-600 hover:bg-[#e6f2f2] hover:text-[#008080] transition-colors cursor-pointer group"
          title="Alerts - Open Alert Center"
          aria-label="Open alerts center"
        >
          <Bell className="w-5 h-5 transition-transform group-hover:scale-105" />

          {/* Real active alert count badge (NO fake numbers) */}
          {activeAlertsCount > 0 && (
            <span
              className="absolute -top-0.5 -right-0.5 flex h-4 min-w-[16px] items-center justify-center rounded-full bg-red-600 px-1 text-[10px] font-extrabold text-white shadow-xs border border-white"
              title={`${activeAlertsCount} active alerts`}
            >
              {activeAlertsCount}
            </span>
          )}
        </button>

        {/* User profile avatar control with dropdown */}
        <div className="relative">
          <button
            onClick={() => setUserMenuOpen(!userMenuOpen)}
            className={`flex items-center gap-1.5 pl-1.5 pr-2.5 py-1 rounded-full border transition-all cursor-pointer ${
              userMenuOpen ? 'bg-teal-50 border-teal-500/50 shadow-sm' : 'border-slate-200 hover:bg-slate-50'
            }`}
            aria-label="User profile menu"
            title="User Profile & Settings"
          >
            <span
              className="w-6 h-6 rounded-full flex items-center justify-center text-[11px] font-bold text-white shadow-xs"
              style={{ background: 'var(--aq-navy)' }}
            >
              U
            </span>
            <ChevronDown className={`w-3.5 h-3.5 text-slate-400 transition-transform duration-200 ${userMenuOpen ? 'rotate-180 text-teal-600' : ''}`} />
          </button>

          {/* Profile Dropdown Menu */}
          {userMenuOpen && (
            <>
              {/* Click outside backdrop */}
              <div
                className="fixed inset-0 z-40"
                onClick={() => setUserMenuOpen(false)}
              />

              <div className="absolute right-0 mt-2 w-72 rounded-2xl bg-white border border-slate-200 shadow-2xl z-50 p-4 space-y-3 animate-in fade-in slide-in-from-top-2">
                {/* User Info Header */}
                <div className="flex items-center gap-3 pb-3 border-b border-slate-100">
                  <div className="w-10 h-10 rounded-xl bg-[#008080] text-white font-extrabold text-sm flex items-center justify-center shadow-md">
                    U
                  </div>
                  <div className="flex flex-col min-w-0">
                    <span className="text-xs font-bold text-slate-900 truncate">
                      Mumbai Civic Ops Admin
                    </span>
                    <span className="text-[11px] text-slate-500 truncate">
                      ops.mumbai@aquora.gov.in
                    </span>
                    <span className="text-[10px] font-semibold text-[#008080] mt-0.5">
                      ● Active Live Session
                    </span>
                  </div>
                </div>

                {/* Account Details & Context */}
                <div className="space-y-1.5 text-[11px] text-slate-600 bg-slate-50 p-2.5 rounded-xl border border-slate-100">
                  <div className="flex justify-between">
                    <span className="text-slate-500 font-medium">Catchment Zone:</span>
                    <span className="font-bold text-slate-800">Mithi River (17.8 km)</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500 font-medium">Access Tier:</span>
                    <span className="font-bold text-teal-700">Civic Intelligence Level 3</span>
                  </div>
                </div>

                {/* Actions */}
                <div className="pt-1 space-y-1">
                  <button
                    onClick={() => {
                      setUserMenuOpen(false);
                      setActiveTab('alerts');
                    }}
                    className="w-full text-left px-3 py-2 rounded-xl text-xs font-semibold text-slate-700 hover:bg-slate-100 hover:text-teal-700 flex items-center justify-between transition-colors cursor-pointer"
                  >
                    <span>Alert Center Notifications</span>
                    <Bell className="w-3.5 h-3.5 text-slate-400" />
                  </button>

                  <button
                    onClick={() => {
                      setUserMenuOpen(false);
                      navigateToLanding();
                    }}
                    className="w-full text-left px-3 py-2 rounded-xl text-xs font-bold text-red-600 hover:bg-red-50 hover:text-red-700 flex items-center justify-between transition-colors cursor-pointer border border-red-100 mt-1"
                  >
                    <span>Sign Out & Exit to Landing Page</span>
                    <LogOut className="w-3.5 h-3.5 text-red-500" />
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </header>
  );
};

export default TopBar;
