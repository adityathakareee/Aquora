import { create } from 'zustand';

export type IntelligenceTier = 'NATIONAL' | 'REGIONAL' | 'DEEP';

export interface LocationState {
  // Geographic Hierarchy
  selectedCountry: string; // 'IN'
  selectedState: string | null; // 'IN-MH'
  selectedDistrict: string | null;
  selectedBasin: string | null; // 'BASIN-MITHI'
  selectedCity: string | null; // 'IN-MH-MUMBAI'
  selectedCatchment: string | null; // 'CATCH-MITHI-01'

  // Intelligence Tier & Operational Status
  activeIntelligenceLevel: IntelligenceTier;
  activeZoneId: string | null;
  displayName: string;
  mapCenter: [number, number];
  mapZoom: number;

  // Actions
  setLocation: (update: Partial<LocationState>) => void;
  resetToMumbai: () => void;
}

export const useLocationStore = create<LocationState>((set) => ({
  // Defaults to the foundational Mumbai Deep Intelligence Zone
  selectedCountry: 'IN',
  selectedState: 'IN-MH',
  selectedDistrict: null,
  selectedBasin: 'BASIN-MITHI',
  selectedCity: 'IN-MH-MUMBAI',
  selectedCatchment: 'CATCH-MITHI-01',
  activeIntelligenceLevel: 'DEEP',
  activeZoneId: 'deep_mumbai_mithi',
  displayName: 'Mumbai · Mithi Catchment',
  mapCenter: [19.076, 72.8777],
  mapZoom: 13,

  setLocation: (update) => set((state) => ({ ...state, ...update })),

  resetToMumbai: () =>
    set({
      selectedCountry: 'IN',
      selectedState: 'IN-MH',
      selectedDistrict: null,
      selectedBasin: 'BASIN-MITHI',
      selectedCity: 'IN-MH-MUMBAI',
      selectedCatchment: 'CATCH-MITHI-01',
      activeIntelligenceLevel: 'DEEP',
      activeZoneId: 'deep_mumbai_mithi',
      displayName: 'Mumbai · Mithi Catchment',
      mapCenter: [19.076, 72.8777],
      mapZoom: 13,
    }),
}));
