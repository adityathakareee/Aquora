import React, { useState } from 'react';
import { TopBar } from './TopBar';
import { Sidebar } from './Sidebar';
import { OverviewFeature } from '@/features/overview';
import { FloodMapFeature } from '@/features/flood-map';
import { TravelWindowFeature } from '@/features/travel-window';
import { CriticalAccessFeature } from '@/features/critical-access';
import { ProtectCityFeature } from '@/features/protect-city';
import { AlertCenterFeature } from '@/features/alerts';
import { GroundTruthFeature } from '@/features/ground-truth';
import { SimulatorFeature } from '@/features/simulator';
import { useAppStore } from '@/store/useAppStore';
import { useLocationStore } from '@/store/useLocationStore';
import { GeographicTierModal } from './GeographicTierModal';

export const AppShell: React.FC = () => {
  const { activeTab } = useAppStore();
  const { isTierModalOpen, setTierModalOpen } = useLocationStore();
  const [mobileMenuOpen, setMobileMenuOpen] = useState<boolean>(false);
  const mainRef = React.useRef<HTMLElement>(null);

  React.useEffect(() => {
    if (mainRef.current) {
      mainRef.current.scrollTop = 0;
    }
  }, [activeTab]);

  return (
    <div className="flex flex-col h-screen w-screen overflow-hidden font-sans" style={{ background: 'var(--aq-bg)' }}>
      {/* Persistent top header */}
      <TopBar onOpenMobileMenu={() => setMobileMenuOpen(true)} />

      {/* Sidebar + main content */}
      <div className="flex flex-1 overflow-visible relative min-h-0">
        <Sidebar mobileOpen={mobileMenuOpen} onCloseMobile={() => setMobileMenuOpen(false)} />

        {/* Main scrollable workspace */}
        <main
          ref={mainRef}
          className="flex-1 overflow-y-auto"
          style={{ background: 'var(--aq-bg)' }}
        >
          <div className="max-w-[1440px] mx-auto px-5 md:px-7 py-6">
            {activeTab === 'overview'       && <div key="overview"       className="aq-page-enter"><OverviewFeature /></div>}
            {activeTab === 'flood-map'      && <div key="flood-map"      className="aq-page-enter"><FloodMapFeature /></div>}
            {activeTab === 'travel-window'  && <div key="travel-window"  className="aq-page-enter"><TravelWindowFeature /></div>}
            {activeTab === 'critical-access'&& <div key="critical-access"className="aq-page-enter"><CriticalAccessFeature /></div>}
            {activeTab === 'protect-city'   && <div key="protect-city"   className="aq-page-enter"><ProtectCityFeature /></div>}
            {activeTab === 'alerts'         && <div key="alerts"         className="aq-page-enter"><AlertCenterFeature /></div>}
            {activeTab === 'ground-truth'   && <div key="ground-truth"   className="aq-page-enter"><GroundTruthFeature /></div>}
            {activeTab === 'simulator'      && <div key="simulator"      className="aq-page-enter"><SimulatorFeature /></div>}
          </div>
        </main>
      </div>

      {/* Global Geographic Hierarchy & Tier Selector Modal */}
      <GeographicTierModal
        isOpen={isTierModalOpen}
        onClose={() => setTierModalOpen(false)}
      />
    </div>
  );
};

export default AppShell;
