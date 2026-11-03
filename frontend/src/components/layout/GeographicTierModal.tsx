import React, { useState } from 'react';
import {
  Globe,
  Compass,
  Waves,
  ShieldCheck,
  ChevronRight,
  X,
  Layers,
  Database,
  CheckCircle2,
  AlertTriangle,
  AlertCircle,
  Info,
  Clock,
  MapPin,
  Cpu,
  RefreshCw,
} from 'lucide-react';
import { useLocationStore } from '@/store/useLocationStore';
import {
  screenNationalPoint,
  getRegionalIntelligence,
  getBasinSummary,
  inspectDeepPoint,
  NationalScreeningResponse,
  RegionalIntelligenceResponse,
  BasinSummaryResponse,
  DeepIntelligenceResponse,
} from '@/api/intelligence';

interface GeographicTierModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const GeographicTierModal: React.FC<GeographicTierModalProps> = ({ isOpen, onClose }) => {
  const {
    activeIntelligenceLevel,
    displayName,
    setLocation,
    resetToMumbai,
  } = useLocationStore();

  const [activeTab, setActiveTab] = useState<'tiers' | 'national' | 'regional' | 'deep' | 'provenance'>('tiers');

  // National demo state
  const [nationalLat, setNationalLat] = useState<number>(25.5941);
  const [nationalLon, setNationalLon] = useState<number>(85.1376);
  const [nationalLoading, setNationalLoading] = useState<boolean>(false);
  const [nationalBenchmarkRainfall, setNationalBenchmarkRainfall] = useState<boolean>(false);
  const [nationalError, setNationalError] = useState<string | null>(null);
  const [nationalResult, setNationalResult] = useState<NationalScreeningResponse | null>(null);

  // Regional demo state
  const [selectedBasinId, setSelectedBasinId] = useState<string>('BASIN-GANGA');
  const [regionalLat, setRegionalLat] = useState<number>(25.60);
  const [regionalLon, setRegionalLon] = useState<number>(85.15);
  const [regionalLoading, setRegionalLoading] = useState<boolean>(false);
  const [regionalResult, setRegionalResult] = useState<RegionalIntelligenceResponse | null>(null);
  const [basinSummary, setBasinSummary] = useState<BasinSummaryResponse | null>(null);

  // Deep demo state
  const [deepLat, setDeepLat] = useState<number>(19.0728);
  const [deepLon, setDeepLon] = useState<number>(72.8826);
  const [deepLoading, setDeepLoading] = useState<boolean>(false);
  const [deepResult, setDeepResult] = useState<DeepIntelligenceResponse | null>(null);

  if (!isOpen) return null;

  // Actions
  const handleSelectNational = () => {
    setLocation({
      selectedCountry: 'IN',
      selectedState: null,
      selectedDistrict: null,
      selectedBasin: null,
      selectedCity: null,
      selectedCatchment: null,
      activeIntelligenceLevel: 'NATIONAL',
      activeZoneId: 'national_india',
      displayName: 'India (National Screening)',
      mapCenter: [20.5937, 78.9629],
      mapZoom: 5,
    });
  };

  const handleSelectBasin = (basinId: string, name: string, center: [number, number], zoom: number) => {
    setLocation({
      selectedCountry: 'IN',
      selectedState: null,
      selectedDistrict: null,
      selectedBasin: basinId,
      selectedCity: null,
      selectedCatchment: null,
      activeIntelligenceLevel: 'REGIONAL',
      activeZoneId: `regional_${basinId.toLowerCase().replace('-', '_')}`,
      displayName: `${name} (Regional)`,
      mapCenter: center,
      mapZoom: zoom,
    });
  };

  const handleSelectMumbaiDeep = () => {
    resetToMumbai();
  };

  // Run national screening
  const runNationalScreening = async (
    lat: number,
    lon: number,
    allowBenchmark: boolean = nationalBenchmarkRainfall
  ) => {
    setNationalLoading(true);
    setNationalError(null);
    try {
      const res = await screenNationalPoint({
        latitude: lat,
        longitude: lon,
        allow_benchmark_rainfall: allowBenchmark,
      });
      setNationalResult(res);
    } catch (e: any) {
      console.error('National screening error:', e);
      setNationalError(e?.message || 'National Screening API request failed.');
    } finally {
      setNationalLoading(false);
    }
  };

  // Run regional screening
  const runRegionalScreening = async (lat: number, lon: number, basinId: string) => {
    setRegionalLoading(true);
    try {
      const [res, summary] = await Promise.all([
        getRegionalIntelligence({
          latitude: lat,
          longitude: lon,
          allow_benchmark_rainfall: true,
        }),
        getBasinSummary(basinId).catch(() => null),
      ]);
      setRegionalResult(res);
      setBasinSummary(summary);
    } catch (e: any) {
      console.error(e);
    } finally {
      setRegionalLoading(false);
    }
  };

  // Run deep inspection
  const runDeepInspection = async (lat: number, lon: number) => {
    setDeepLoading(true);
    try {
      const res = await inspectDeepPoint({
        latitude: lat,
        longitude: lon,
        allow_benchmark_rainfall: true,
      });
      setDeepResult(res);
    } catch (e: any) {
      console.error(e);
    } finally {
      setDeepLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-200">
      <div className="relative w-full max-w-4xl max-h-[90vh] bg-white rounded-2xl shadow-2xl border border-slate-200 flex flex-col overflow-hidden text-slate-800">

        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 bg-slate-50/80">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-teal-50 text-[#008080] border border-teal-200 shadow-xs">
              <Globe className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-extrabold text-slate-900 tracking-tight flex items-center gap-2">
                Geographic Hierarchy & Intelligence Tiers
                <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-teal-100 text-teal-800">
                  AQUORA Platform
                </span>
              </h2>
              <p className="text-xs text-slate-500 font-medium mt-0.5">
                Current Scope: <strong className="text-slate-800">{displayName}</strong> · Active Level:{' '}
                <span className="font-bold text-[#008080]">{activeIntelligenceLevel}</span>
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-xl text-slate-400 hover:text-slate-700 hover:bg-slate-200/60 transition-colors cursor-pointer"
            aria-label="Close dialog"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tab Navigation */}
        <div className="flex border-b border-slate-200 bg-slate-100/70 px-6 gap-2 text-xs font-semibold overflow-x-auto">
          {[
            { id: 'tiers', label: '1. Tier Hierarchy & Switcher', icon: Layers },
            { id: 'national', label: '2. National Screening (Macro)', icon: Globe },
            { id: 'regional', label: '3. Regional Basins (Meso)', icon: Compass },
            { id: 'deep', label: '4. Deep Mithi & Restrictions', icon: Waves },
            { id: 'provenance', label: '5. Evidence & Provenance', icon: Database },
          ].map((t) => {
            const Icon = t.icon;
            const isActive = activeTab === t.id;
            return (
              <button
                key={t.id}
                id={`tab-${t.id}`}
                onClick={() => setActiveTab(t.id as any)}
                className={`flex items-center gap-2 py-3 px-3.5 border-b-2 font-bold transition-all cursor-pointer whitespace-nowrap ${isActive
                    ? 'border-[#008080] text-[#008080] bg-white shadow-2xs rounded-t-lg'
                    : 'border-transparent text-slate-600 hover:text-slate-900 hover:border-slate-300'
                  }`}
              >
                <Icon className="w-4 h-4" />
                {t.label}
              </button>
            );
          })}
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">

          {/* TAB 1: TIER HIERARCHY & SWITCHER */}
          {activeTab === 'tiers' && (
            <div className="space-y-6">
              <div className="bg-teal-50/60 border border-teal-200 rounded-xl p-4 text-xs text-slate-700 leading-relaxed">
                <span className="font-bold text-teal-900 block mb-1">
                  🏛️ Authoritative Geographic Hierarchy:
                </span>
                <p>
                  <strong>India</strong> (Country) → <strong>State</strong> → <strong>District</strong> →{' '}
                  <strong>River Basin</strong> → <strong>City</strong> → <strong>Catchment</strong> →{' '}
                  <strong>Deep Intelligence Zone</strong>.
                </p>
                <p className="mt-1 text-slate-600">
                  Select an operational tier below to navigate the camera and scope the analytics:
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {/* Level 1 National */}
                <div
                  onClick={handleSelectNational}
                  className={`p-4 rounded-xl border transition-all cursor-pointer flex flex-col justify-between ${activeIntelligenceLevel === 'NATIONAL'
                      ? 'border-[#008080] bg-teal-50/50 shadow-md ring-1 ring-[#008080]'
                      : 'border-slate-200 bg-white hover:border-teal-300 hover:shadow-xs'
                    }`}
                >
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-[10px] font-extrabold uppercase px-2 py-0.5 rounded bg-slate-100 text-slate-700">
                        Level 1: National
                      </span>
                      {activeIntelligenceLevel === 'NATIONAL' && (
                        <CheckCircle2 className="w-4 h-4 text-[#008080]" />
                      )}
                    </div>
                    <h3 className="text-sm font-bold text-slate-900">India Subcontinent</h3>
                    <p className="text-[11px] text-slate-500 mt-1">
                      Macro flood susceptibility screening across all 6,876 IFI records using 11 Core Predictors.
                    </p>
                  </div>
                  <div className="mt-4 pt-3 border-t border-slate-100 text-[11px] font-semibold text-teal-700 flex items-center justify-between">
                    <span>Switch to National</span>
                    <ChevronRight className="w-3.5 h-3.5" />
                  </div>
                </div>

                {/* Level 2 Regional */}
                <div
                  className={`p-4 rounded-xl border transition-all flex flex-col justify-between ${activeIntelligenceLevel === 'REGIONAL'
                      ? 'border-[#008080] bg-teal-50/50 shadow-md ring-1 ring-[#008080]'
                      : 'border-slate-200 bg-white hover:border-teal-300 hover:shadow-xs'
                    }`}
                >
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-[10px] font-extrabold uppercase px-2 py-0.5 rounded bg-blue-100 text-blue-800">
                        Level 2: Regional
                      </span>
                      {activeIntelligenceLevel === 'REGIONAL' && (
                        <CheckCircle2 className="w-4 h-4 text-[#008080]" />
                      )}
                    </div>
                    <h3 className="text-sm font-bold text-slate-900">Major River Basins</h3>
                    <p className="text-[11px] text-slate-500 mt-1">
                      HydroBASINS Level 5/6 watershed exposure index using 14 features across 4 active basins.
                    </p>
                    <div className="grid grid-cols-2 gap-1.5 mt-3 text-[10.5px]">
                      <button
                        onClick={() => handleSelectBasin('BASIN-GANGA', 'Ganga Basin', [25.5, 83.0], 6)}
                        className="p-1.5 rounded bg-slate-50 hover:bg-blue-100 text-slate-700 font-bold border border-slate-200 text-left transition-colors cursor-pointer"
                      >
                        Ganga Basin
                      </button>
                      <button
                        onClick={() => handleSelectBasin('BASIN-BRAHMAPUTRA', 'Brahmaputra Basin', [26.5, 92.5], 6)}
                        className="p-1.5 rounded bg-slate-50 hover:bg-blue-100 text-slate-700 font-bold border border-slate-200 text-left transition-colors cursor-pointer"
                      >
                        Brahmaputra
                      </button>
                      <button
                        onClick={() => handleSelectBasin('BASIN-GODAVARI', 'Godavari Basin', [19.0, 78.0], 6)}
                        className="p-1.5 rounded bg-slate-50 hover:bg-blue-100 text-slate-700 font-bold border border-slate-200 text-left transition-colors cursor-pointer"
                      >
                        Godavari
                      </button>
                      <button
                        onClick={() => handleSelectBasin('BASIN-KRISHNA', 'Krishna Basin', [16.5, 76.5], 6)}
                        className="p-1.5 rounded bg-slate-50 hover:bg-blue-100 text-slate-700 font-bold border border-slate-200 text-left transition-colors cursor-pointer"
                      >
                        Krishna
                      </button>
                      <button
                        onClick={() => handleSelectBasin('BASIN-SABARMATI', 'Sabarmati Basin', [23.0, 72.6], 7)}
                        className="p-1.5 rounded bg-slate-50 hover:bg-blue-100 text-slate-700 font-bold border border-slate-200 text-left transition-colors cursor-pointer"
                      >
                        Sabarmati
                      </button>
                      <button
                        onClick={() => handleSelectBasin('BASIN-NARMADA', 'Narmada Basin', [22.5, 77.0], 6)}
                        className="p-1.5 rounded bg-slate-50 hover:bg-blue-100 text-slate-700 font-bold border border-slate-200 text-left transition-colors cursor-pointer"
                      >
                        Narmada
                      </button>
                      <button
                        onClick={() => handleSelectBasin('BASIN-MAHANADI', 'Mahanadi Basin (DFO 3382 Study)', [20.45, 85.85], 8)}
                        className="col-span-2 p-1.5 rounded bg-amber-50 hover:bg-amber-100 text-amber-900 font-bold border border-amber-200 text-left transition-colors cursor-pointer flex items-center justify-between"
                      >
                        <span>Mahanadi Basin · Phase 7F Research</span>
                        <span className="text-[9px] bg-amber-200 text-amber-900 px-1 py-0.5 rounded font-mono">PROTOTYPE</span>
                      </button>
                    </div>
                  </div>
                </div>

                {/* Level 3 Deep Zone */}
                <div
                  onClick={handleSelectMumbaiDeep}
                  className={`p-4 rounded-xl border transition-all cursor-pointer flex flex-col justify-between ${activeIntelligenceLevel === 'DEEP'
                      ? 'border-[#008080] bg-teal-50/50 shadow-md ring-1 ring-[#008080]'
                      : 'border-slate-200 bg-white hover:border-teal-300 hover:shadow-xs'
                    }`}
                >
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-[10px] font-extrabold uppercase px-2 py-0.5 rounded bg-teal-100 text-teal-800">
                        Level 3: Deep Zone
                      </span>
                      {activeIntelligenceLevel === 'DEEP' && (
                        <CheckCircle2 className="w-4 h-4 text-[#008080]" />
                      )}
                    </div>
                    <h3 className="text-sm font-bold text-slate-900">Mumbai · Mithi Catchment</h3>
                    <p className="text-[11px] text-slate-500 mt-1">
                      Phase 6 deterministic 2D hydraulic solver + 30m Copernicus DEM + 366 critical facilities.
                    </p>
                  </div>
                  <div className="mt-4 pt-3 border-t border-slate-100 text-[11px] font-semibold text-teal-700 flex items-center justify-between">
                    <span>Active Foundational Zone</span>
                    <ChevronRight className="w-3.5 h-3.5" />
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: NATIONAL SCREENING DEMO */}
          {activeTab === 'national' && (
            <div className="space-y-5">
              {/* Controls Card */}
              <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-3.5 shadow-2xs">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-xs font-bold uppercase tracking-wider text-slate-800 flex items-center gap-2">
                      <Cpu className="w-4 h-4 text-[#008080]" />
                      Level 1: National Flood Risk Screening (Macro Susceptibility)
                    </h3>
                    <p className="text-xs text-slate-500 mt-0.5">
                      Executes live inference via the Kaggle-trained XGBoost Booster (<code>aquora_national_screening_xgboost_v1</code>) across 11 Core National Features.
                    </p>
                  </div>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-teal-100 text-teal-800 font-bold">
                    FastAPI ML Engine
                  </span>
                </div>

                {/* Presets */}
                <div>
                  <div className="flex items-center gap-1.5 mb-2">
                    <MapPin className="w-3.5 h-3.5 text-slate-400" />
                    <span className="text-xs font-semibold text-slate-700">Geographic Verification Presets:</span>
                  </div>
                  <div className="flex flex-wrap items-center gap-1.5">
                    {[
                      { label: 'Patna (Ganga)', lat: 25.5941, lon: 85.1376, desc: 'Ganga River Basin' },
                      { label: 'Guwahati (Brahmaputra)', lat: 26.1445, lon: 91.7362, desc: 'Brahmaputra River Basin' },
                      { label: 'Vijayawada (Krishna)', lat: 16.5062, lon: 80.6480, desc: 'Krishna River Basin / AP' },
                      { label: 'Nagpur (Godavari)', lat: 21.1458, lon: 79.0882, desc: 'Godavari River Basin / Vidarbha' },
                      { label: 'Ahmedabad (Sabarmati)', lat: 23.0225, lon: 72.5714, desc: 'Sabarmati River Basin / Gujarat' },
                      { label: 'Delhi (Yamuna)', lat: 28.6139, lon: 77.2090, desc: 'Yamuna Corridor' },
                      { label: 'Mumbai (Deep Boundary)', lat: 19.0728, lon: 72.8826, desc: 'Mumbai Mithi Hydraulic Boundary' },
                    ].map((p) => (
                      <button
                        key={p.label}
                        id={`btn-preset-${p.label.toLowerCase().replace(/[^a-z0-9]/g, '-')}`}
                        onClick={() => {
                          setNationalLat(p.lat);
                          setNationalLon(p.lon);
                          runNationalScreening(p.lat, p.lon, nationalBenchmarkRainfall);
                        }}
                        className={`px-2.5 py-1 text-[11px] font-bold rounded-lg border transition-all cursor-pointer ${nationalLat === p.lat && nationalLon === p.lon
                            ? 'bg-teal-700 text-white border-teal-800 shadow-xs'
                            : 'bg-white border-slate-200 text-slate-700 hover:bg-teal-50 hover:text-teal-700'
                          }`}
                        title={p.desc}
                      >
                        {p.label}
                      </button>
                    ))}
                    <button
                      id="btn-preset-out-of-bounds"
                      onClick={() => {
                        setNationalLat(51.5074);
                        setNationalLon(-0.1278);
                        runNationalScreening(51.5074, -0.1278, nationalBenchmarkRainfall);
                      }}
                      className="px-2.5 py-1 text-[11px] font-bold rounded-lg bg-red-50 border border-red-200 text-red-700 hover:bg-red-100 transition-colors cursor-pointer"
                      title="Verifies out-of-bounds rejection without spatial fallback"
                    >
                      Test Out of Bounds (London)
                    </button>
                  </div>
                </div>

                {/* Input Fields & Actions */}
                <div className="flex flex-wrap items-center justify-between gap-3 pt-2 border-t border-slate-200/80">
                  <div className="flex items-center gap-3">
                    <div className="flex items-center gap-1.5 text-xs">
                      <label className="text-slate-500 font-semibold">Lat:</label>
                      <input
                        id="input-national-lat"
                        type="number"
                        step="0.0001"
                        value={nationalLat}
                        onChange={(e) => setNationalLat(parseFloat(e.target.value))}
                        className="w-28 px-2.5 py-1 text-xs border border-slate-300 rounded font-mono bg-white text-slate-800 focus:outline-teal-600"
                      />
                    </div>
                    <div className="flex items-center gap-1.5 text-xs">
                      <label className="text-slate-500 font-semibold">Lon:</label>
                      <input
                        id="input-national-lon"
                        type="number"
                        step="0.0001"
                        value={nationalLon}
                        onChange={(e) => setNationalLon(parseFloat(e.target.value))}
                        className="w-28 px-2.5 py-1 text-xs border border-slate-300 rounded font-mono bg-white text-slate-800 focus:outline-teal-600"
                      />
                    </div>
                    <label className="flex items-center gap-1.5 text-xs text-slate-600 cursor-pointer select-none ml-2">
                      <input
                        id="check-benchmark-rainfall"
                        type="checkbox"
                        checked={nationalBenchmarkRainfall}
                        onChange={(e) => {
                          const nextVal = e.target.checked;
                          setNationalBenchmarkRainfall(nextVal);
                          if (nationalResult) {
                            runNationalScreening(nationalLat, nationalLon, nextVal);
                          }
                        }}
                        className="rounded text-teal-600 focus:ring-teal-500 h-3.5 w-3.5"
                      />
                      <span>Allow Benchmark / Historical Scenario Input (Scenario Testing Only; Not Live Operational Gauges)</span>
                    </label>
                  </div>

                  <button
                    id="btn-run-national-screening"
                    onClick={() => runNationalScreening(nationalLat, nationalLon, nationalBenchmarkRainfall)}
                    disabled={nationalLoading}
                    className="px-4 py-1.5 text-xs font-bold text-white bg-[#008080] hover:bg-teal-700 rounded-lg transition-colors cursor-pointer disabled:opacity-50 flex items-center gap-1.5 shadow-xs"
                  >
                    {nationalLoading ? (
                      <>
                        <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                        <span>Extracting & Screening...</span>
                      </>
                    ) : (
                      <>
                        <Cpu className="w-3.5 h-3.5" />
                        <span>Execute ML Screening</span>
                      </>
                    )}
                  </button>
                </div>
              </div>

              {/* Scientific Disclaimer & Governance Box */}
              <div className="bg-amber-50/90 border border-amber-300 rounded-xl p-4 text-xs text-amber-950 space-y-2.5 shadow-2xs">
                <div className="flex items-start gap-2.5">
                  <AlertTriangle className="w-4 h-4 text-amber-700 shrink-0 mt-0.5" />
                  <div className="space-y-1">
                    <span className="font-extrabold text-amber-900 block text-xs leading-snug">
                      Experimental National Flood Susceptibility Screening — Uncalibrated Model Output. This is a research screening score, not a validated flood probability or public warning.
                    </span>
                    <p className="text-[11px] text-amber-800 leading-relaxed">
                      This macro screening score is derived from the experimental Phase 7E machine learning pipeline. Please note the following governance invariants:
                    </p>
                    <ul className="list-disc list-inside space-y-0.5 text-[11px] text-amber-900/90 pt-0.5">
                      <li>
                        <strong>Historical Observation Training:</strong> The Phase 7E XGBoost model was trained on multi-event satellite flood extents (DFO 4499, DFO 2935, DFO 3372) across Indian river basins.
                      </li>
                      <li>
                        <strong>Experimental & Uncalibrated:</strong> The returned score is a relative macro-scale susceptibility ranking, not a calibrated statistical probability or operational civil defense evacuation alert.
                      </li>
                      <li>
                        <strong>Deterministic Physics Authority:</strong> The Phase 6 deterministic 2D hydrodynamic flow solver remains the primary authority for Deep Intelligence flood-depth simulation (Mumbai / Mithi). ML scores never override physical calculations.
                      </li>
                      <li>
                        <strong>Zero Data Fabrication:</strong> Missing operational rain gauge data is never simulated or fabricated; when unobserved, it strictly remains <code>null / Unavailable</code>.
                      </li>
                    </ul>
                  </div>
                </div>
              </div>

              {/* Error Alert */}
              {nationalError && (
                <div className="border border-red-200 bg-red-50 rounded-xl p-4 text-xs text-red-800 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <AlertCircle className="w-4 h-4 text-red-600 shrink-0" />
                    <span>{nationalError}</span>
                  </div>
                  <button
                    onClick={() => runNationalScreening(nationalLat, nationalLon, nationalBenchmarkRainfall)}
                    className="px-2.5 py-1 text-[11px] font-bold bg-white text-red-700 rounded border border-red-200 hover:bg-red-100 cursor-pointer"
                  >
                    Retry
                  </button>
                </div>
              )}

              {/* Loading Skeleton */}
              {nationalLoading && !nationalResult && (
                <div className="border border-slate-200 rounded-xl p-8 bg-white text-center space-y-3">
                  <RefreshCw className="w-6 h-6 text-[#008080] animate-spin mx-auto" />
                  <p className="text-xs font-semibold text-slate-700">
                    Extracting 11 Core National Features & Executing XGBoost Model...
                  </p>
                  <p className="text-[11px] text-slate-500 font-mono">
                    Querying Copernicus DEM, HydroSHEDS drainage, and IMD precipitation networks...
                  </p>
                </div>
              )}

              {/* National Result Presentation */}
              {nationalResult && (
                <div className="border border-slate-200 rounded-xl p-5 bg-white space-y-5 shadow-xs">
                  {/* Result Header & Badges */}
                  <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-slate-100">
                    <div className="flex items-center gap-2">
                      <span
                        className={`px-2.5 py-1 rounded-md text-[10px] font-extrabold uppercase tracking-wider ${nationalResult.status === 'READY'
                            ? 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                            : nationalResult.status === 'OUTSIDE_COVERAGE'
                              ? 'bg-rose-100 text-rose-800 border border-rose-200'
                              : 'bg-amber-100 text-amber-800 border border-amber-300'
                          }`}
                      >
                        Status: {nationalResult.status}
                      </span>
                      <span className="text-xs text-slate-600 font-medium flex items-center gap-1">
                        <MapPin className="w-3.5 h-3.5 text-slate-400" />
                        Zone: <strong className="text-slate-800">{nationalResult.resolved_zone}</strong>
                      </span>
                    </div>

                    <div className="flex items-center gap-2 text-[11px]">
                      {nationalResult.provenance?.feature_provenance?.rainfall_is_benchmark ? (
                        <span className="px-2 py-0.5 rounded bg-amber-100 text-amber-900 font-bold border border-amber-300">
                          BENCHMARK / HISTORICAL INPUT
                        </span>
                      ) : nationalResult.status === 'READY' ? (
                        <span className="px-2 py-0.5 rounded bg-emerald-50 text-emerald-800 font-bold border border-emerald-200">
                          OPERATIONAL OBSERVATION
                        </span>
                      ) : null}
                      <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-600 font-mono font-medium border border-slate-200">
                        Model: {nationalResult.model_id} (v{nationalResult.model_version})
                      </span>
                      <span className="px-2 py-0.5 rounded bg-teal-50 text-teal-700 font-bold border border-teal-200">
                        {nationalResult.calibration_status}
                      </span>
                    </div>
                  </div>

                  {/* Message Banner (for Out of Bounds or Informational Notes) */}
                  {nationalResult.message && nationalResult.status !== 'INSUFFICIENT_INPUT_DATA' && (
                    <div className={`p-3 rounded-lg text-xs border ${nationalResult.status === 'OUTSIDE_COVERAGE'
                        ? 'bg-rose-50 border-rose-200 text-rose-800'
                        : 'bg-slate-50 border-slate-200 text-slate-700'
                      }`}>
                      ℹ️ {nationalResult.message}
                    </div>
                  )}

                  {/* INSUFFICIENT DATA CARD — STRICT INPUT-VALIDITY ENFORCEMENT */}
                  {nationalResult.status === 'INSUFFICIENT_INPUT_DATA' ? (
                    <div className="p-4 rounded-xl bg-amber-50/90 border border-amber-300 space-y-3.5">
                      <div className="flex items-start gap-2.5">
                        <AlertTriangle className="w-5 h-5 text-amber-700 shrink-0 mt-0.5" />
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <span className="font-extrabold text-amber-950 text-sm">
                              INSUFFICIENT INPUT DATA · INFERENCE SUPPRESSED
                            </span>
                            <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-200 text-amber-900 border border-amber-300">
                              {nationalResult.provenance?.input_validity || 'NO_PREDICTORS_AVAILABLE'}
                            </span>
                          </div>
                          <p className="text-xs text-amber-800 leading-relaxed">
                            {nationalResult.message || (
                              'Zero trained model predictors are available for this location. Inference is strictly suppressed to prevent returning an uninformative XGBoost default base score (1.30%).'
                            )}
                          </p>
                        </div>
                      </div>

                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2.5 border-t border-amber-200 text-xs text-amber-950">
                        <div className="p-3 rounded-lg bg-white/80 border border-amber-200 space-y-1.5">
                          <span className="font-bold text-[11px] text-slate-700 uppercase tracking-wider block">
                            Geographic Coordinate Coverage Status
                          </span>
                          <div className="font-mono text-slate-800 text-[11px]">
                            Coordinates: {nationalResult.coordinates.latitude.toFixed(4)}°N, {nationalResult.coordinates.longitude.toFixed(4)}°E
                          </div>
                          <div className="text-[11px] text-slate-700">
                            Hydrologic Basin: <strong>{nationalResult.resolved_zone}</strong>
                          </div>
                          <div className="text-[10.5px] text-amber-800 font-semibold pt-1 border-t border-slate-100">
                            ⚠️ Copernicus 30m DEM & hydrographic network unindexed for this coordinate tile.
                          </div>
                        </div>

                        <div className="p-3 rounded-lg bg-white/80 border border-amber-200 space-y-1.5">
                          <span className="font-bold text-[11px] text-slate-700 uppercase tracking-wider block">
                            Predictor Availability Audit (7 Trained Features)
                          </span>
                          <div className="text-[11px] text-slate-700 flex justify-between">
                            <span>Available Predictors:</span>
                            <strong className="text-emerald-700 font-mono font-bold">
                              {nationalResult.provenance?.available_predictors?.length || 0} / 7
                            </strong>
                          </div>
                          <div className="text-[11px] text-slate-700 flex justify-between">
                            <span>Missing Predictors:</span>
                            <strong className="text-rose-700 font-mono font-bold">
                              {nationalResult.provenance?.missing_predictors?.length || 7} / 7
                            </strong>
                          </div>
                          <div className="text-[10px] text-slate-500 font-mono truncate" title={nationalResult.provenance?.missing_predictors?.join(', ')}>
                            Missing: {nationalResult.provenance?.missing_predictors?.join(', ') || 'All 7 features'}
                          </div>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <>
                      {/* Operational vs Benchmark Disclaimer Banner */}
                      {nationalResult.status === 'READY' && (
                        nationalResult.provenance?.feature_provenance?.rainfall_is_benchmark ? (
                          <div className="p-2.5 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-900 flex items-center justify-between">
                            <span className="font-bold flex items-center gap-1.5">
                              <AlertTriangle className="w-3.5 h-3.5 text-amber-700" />
                              BENCHMARK / HISTORICAL SCENARIO INPUT ACTIVE
                            </span>
                            <span className="text-[11px] text-amber-800">
                              Precipitation features are non-operational benchmark test fixtures, NOT real-time or calibrated gauges.
                            </span>
                          </div>
                        ) : (
                          <div className="p-2.5 bg-teal-50 border border-teal-200 rounded-lg text-xs text-teal-900 flex items-center justify-between">
                            <span className="font-bold flex items-center gap-1.5">
                              <CheckCircle2 className="w-3.5 h-3.5 text-teal-700" />
                              OPERATIONAL GEOMORPHIC OBSERVATION ACTIVE
                            </span>
                            <span className="text-[11px] text-teal-800">
                              Evaluated strictly on authentic 30m DEM terrain and landcover. Real-time gauges are unobserved at this cell (null under zero fabrication).
                            </span>
                          </div>
                        )
                      )}

                      {/* Primary Susceptibility Score & Grade Hero Row */}
                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                        {/* Score Box */}
                        <div className="p-4 rounded-xl bg-slate-50/80 border border-slate-200 flex flex-col justify-between">
                          <div>
                            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block mb-1">
                              Macro Susceptibility Score
                            </span>
                            <div className="text-2xl font-black text-slate-900 font-mono tracking-tight">
                              {nationalResult.susceptibility_probability !== null ? (
                                <span>{(nationalResult.susceptibility_probability * 100).toFixed(2)}%</span>
                              ) : (
                                <span className="text-slate-400 text-lg">Unavailable</span>
                              )}
                            </div>
                          </div>
                          <span className="text-[10px] text-slate-500 font-mono mt-2 block">
                            {nationalResult.susceptibility_probability !== null
                              ? `Raw Booster Score: ${nationalResult.susceptibility_probability.toFixed(4)}`
                              : 'Coordinates outside covered domain'}
                          </span>
                        </div>

                        {/* Grade Box */}
                        <div className="p-4 rounded-xl bg-slate-50/80 border border-slate-200 flex flex-col justify-between">
                          <div>
                            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block mb-1">
                              Susceptibility Band (Presentation Category)
                            </span>
                            <div className="mt-0.5">
                              {nationalResult.susceptibility_grade ? (
                                <span
                                  className={`inline-block px-3 py-1 rounded-lg text-sm font-extrabold tracking-wide ${nationalResult.susceptibility_grade === 'LOW'
                                      ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                                      : nationalResult.susceptibility_grade === 'MEDIUM'
                                        ? 'bg-amber-100 text-amber-800 border border-amber-300'
                                        : 'bg-rose-100 text-rose-800 border border-rose-300'
                                    }`}
                                >
                                  {nationalResult.susceptibility_grade} MODEL SCORE
                                </span>
                              ) : (
                                <span className="text-slate-400 text-sm font-medium">Unavailable</span>
                              )}
                            </div>
                          </div>
                          <span className="text-[10px] text-slate-500 mt-2 block">
                            Presentation category only; NOT a validated flood-risk classification or public warning.
                          </span>
                        </div>

                        {/* Geographic & Timestamp Metadata Box */}
                        <div className="p-4 rounded-xl bg-slate-50/80 border border-slate-200 flex flex-col justify-between text-xs">
                          <div>
                            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block mb-1">
                              Location & Timing
                            </span>
                            <div className="font-mono text-slate-800 font-semibold space-y-0.5 text-[11px]">
                              <div>Lat: {nationalResult.coordinates.latitude.toFixed(4)}°N</div>
                              <div>Lon: {nationalResult.coordinates.longitude.toFixed(4)}°E</div>
                            </div>
                          </div>
                          <div className="text-[10px] text-slate-500 flex items-center gap-1 mt-2 pt-2 border-t border-slate-200 font-mono">
                            <Clock className="w-3 h-3 text-slate-400" />
                            <span>
                              {nationalResult.provenance?.feature_provenance?.extraction_timestamp
                                ? new Date(nationalResult.provenance.feature_provenance.extraction_timestamp).toISOString().replace('T', ' ').substring(0, 19) + ' UTC'
                                : 'Live Pipeline Extraction'}
                            </span>
                          </div>
                        </div>
                      </div>

                      {/* Susceptibility Meter Bar */}
                      {nationalResult.susceptibility_probability !== null && (
                        <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200 space-y-2">
                          <div className="flex items-center justify-between text-[11px] font-bold text-slate-600">
                            <span>Susceptibility Spectrum:</span>
                            <span className="font-mono text-teal-800 font-extrabold">
                              {(nationalResult.susceptibility_probability * 100).toFixed(2)}%
                            </span>
                          </div>
                          <div className="relative h-3 w-full bg-slate-200 rounded-full overflow-hidden flex">
                            <div className="h-full bg-emerald-500 w-1/3" title="Low Susceptibility (< 33%)" />
                            <div className="h-full bg-amber-500 w-1/3" title="Medium Susceptibility (33% - 66%)" />
                            <div className="h-full bg-rose-500 w-1/3" title="High Susceptibility (> 66%)" />
                          </div>
                          <div className="flex items-center justify-between text-[10px] text-slate-500 font-semibold">
                            <span className="text-emerald-700">LOW (0% – 33%)</span>
                            <span className="text-amber-700">MEDIUM (33% – 66%)</span>
                            <span className="text-rose-700">HIGH (66% – 100%)</span>
                          </div>
                        </div>
                      )}
                    </>
                  )}

                  {/* Extracted 11 Core National Features & Data Provenance Table */}
                  {nationalResult.feature_values && (
                    <div className="space-y-2.5">
                      <div className="flex items-center justify-between">
                        <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
                          <Database className="w-3.5 h-3.5 text-[#008080]" />
                          Input Feature Values & Data Source Provenance (11 Core Predictors)
                        </h4>
                        <span className="text-[10px] text-slate-500 font-mono">
                          Phase 7E Schema: 11 Features Evaluated
                        </span>
                      </div>

                      <div className="overflow-x-auto border border-slate-200 rounded-xl">
                        <table className="w-full text-left text-xs">
                          <thead className="bg-slate-100/80 text-[11px] font-bold text-slate-700 uppercase tracking-wider border-b border-slate-200">
                            <tr>
                              <th className="py-2.5 px-3">Predictor Name</th>
                              <th className="py-2.5 px-3">Observed Value</th>
                              <th className="py-2.5 px-3">Primary Data Source</th>
                              <th className="py-2.5 px-3 text-right">Data Availability</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-100 bg-white">
                            {[
                              {
                                key: 'elevation_m',
                                label: 'Surface Elevation',
                                unit: 'm MSL',
                                source: nationalResult.provenance?.feature_provenance?.terrain_source && nationalResult.provenance.feature_provenance.terrain_source !== 'UNAVAILABLE'
                                  ? `Copernicus GLO-30 DEM (${nationalResult.provenance.feature_provenance.terrain_source})`
                                  : 'Copernicus GLO-30 DEM (Tile Unindexed)',
                                isMissing: nationalResult.feature_values.elevation_m === null,
                              },
                              {
                                key: 'slope_deg',
                                label: 'Topographic Slope',
                                unit: '° (degrees)',
                                source: nationalResult.provenance?.feature_provenance?.terrain_source && nationalResult.provenance.feature_provenance.terrain_source !== 'UNAVAILABLE'
                                  ? `Derived Gradient (${nationalResult.provenance.feature_provenance.terrain_source})`
                                  : 'Copernicus DEM Gradient Derivative',
                                isMissing: nationalResult.feature_values.slope_deg === null,
                              },
                              {
                                key: 'distance_to_river_m',
                                label: 'Distance to River/Drainage',
                                unit: 'meters',
                                source: nationalResult.provenance?.feature_provenance?.basin_source || 'HydroSHEDS v1 / HydroRIVERS Network',
                                isMissing: nationalResult.feature_values.distance_to_river_m === null,
                              },
                              {
                                key: 'landcover_class',
                                label: 'Landcover Classification',
                                unit: 'ESA Code',
                                source: 'ESA WorldCover 10m Classification',
                                isMissing: nationalResult.feature_values.landcover_class === null,
                              },
                              {
                                key: 'rainfall_24h_mm',
                                label: '24-Hour Accumulated Rainfall',
                                unit: 'mm',
                                source: nationalResult.provenance?.feature_provenance?.rainfall_is_benchmark
                                  ? 'BENCHMARK / HISTORICAL INPUT (IMD Daily Climatology Fixture)'
                                  : 'IMD AWS Operational Gauge Stream (Unobserved at this cell)',
                                isMissing: nationalResult.feature_values.rainfall_24h_mm === null,
                              },
                              {
                                key: 'rainfall_72h_mm',
                                label: '72-Hour Cumulative Rainfall',
                                unit: 'mm',
                                source: nationalResult.provenance?.feature_provenance?.rainfall_is_benchmark
                                  ? 'BENCHMARK / HISTORICAL INPUT (IMD Daily Climatology Fixture)'
                                  : 'IMD AWS Operational Gauge Stream (Unobserved at this cell)',
                                isMissing: nationalResult.feature_values.rainfall_72h_mm === null,
                              },
                              {
                                key: 'rainfall_anomaly_index',
                                label: 'Precipitation Anomaly Index',
                                unit: 'z-score index',
                                source: nationalResult.provenance?.feature_provenance?.rainfall_is_benchmark
                                  ? 'BENCHMARK / HISTORICAL INPUT (30-Year Climatology Reference)'
                                  : 'IMD 30-Year Climatology Reference (Unobserved at this cell)',
                                isMissing: nationalResult.feature_values.rainfall_anomaly_index === null,
                              },
                              {
                                key: 'rainfall_1h_mm',
                                label: '1-Hour Peak Rainfall',
                                unit: 'mm',
                                source: 'IMD Sub-Daily Automated Gauge Stream (Uningested)',
                                isMissing: true,
                              },
                              {
                                key: 'rainfall_3h_mm',
                                label: '3-Hour Accumulated Rainfall',
                                unit: 'mm',
                                source: 'IMD Sub-Daily Automated Gauge Stream (Uningested)',
                                isMissing: true,
                              },
                              {
                                key: 'rainfall_6h_mm',
                                label: '6-Hour Accumulated Rainfall',
                                unit: 'mm',
                                source: 'IMD Sub-Daily Automated Gauge Stream (Uningested)',
                                isMissing: true,
                              },
                              {
                                key: 'historical_flood_frequency',
                                label: 'Historical Flood Frequency',
                                unit: 'count',
                                source: 'DFO Multi-Event Archive (Quarantined)',
                                isMissing: true,
                                isQuarantined: true,
                              },
                            ].map((item) => {
                              const val = nationalResult.feature_values?.[item.key];
                              return (
                                <tr key={item.key} className="hover:bg-slate-50/60 transition-colors">
                                  <td className="py-2.5 px-3">
                                    <span className="font-bold text-slate-800 block">{item.label}</span>
                                    <span className="text-[10px] text-slate-400 font-mono">{item.key}</span>
                                  </td>
                                  <td className="py-2.5 px-3 font-mono font-bold">
                                    {val !== null && val !== undefined ? (
                                      <span className="text-slate-800">
                                        {typeof val === 'number' ? val.toLocaleString(undefined, { maximumFractionDigits: 2 }) : val}{' '}
                                        <span className="text-[10px] font-normal text-slate-500">{item.unit}</span>
                                      </span>
                                    ) : (
                                      <span className="text-amber-700 italic text-[11px] font-medium">
                                        Unavailable (null)
                                      </span>
                                    )}
                                  </td>
                                  <td className="py-2.5 px-3 text-slate-600 text-[11px]">
                                    {item.source}
                                  </td>
                                  <td className="py-2.5 px-3 text-right">
                                    {item.isQuarantined ? (
                                      <span className="inline-block px-2 py-0.5 rounded text-[10px] font-bold bg-purple-100 text-purple-800 border border-purple-200">
                                        Quarantined (Anti-leakage)
                                      </span>
                                    ) : val !== null && val !== undefined ? (
                                      nationalResult.provenance?.feature_provenance?.rainfall_is_benchmark && item.key.startsWith('rainfall') ? (
                                        <span className="inline-block px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-900 border border-amber-300">
                                          BENCHMARK INPUT
                                        </span>
                                      ) : (
                                        <span className="inline-block px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-200">
                                          Authentic Observed
                                        </span>
                                      )
                                    ) : (
                                      <span className="inline-block px-2 py-0.5 rounded text-[10px] font-bold bg-slate-100 text-slate-600 border border-slate-200">
                                        Unobserved (Null)
                                      </span>
                                    )}
                                  </td>
                                </tr>
                              );
                            })}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}

                  {/* Missing Inputs & Data Coverage Limitations Summary */}
                  <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200 space-y-1.5 text-xs text-slate-600">
                    <span className="font-bold text-slate-800 block flex items-center gap-1.5">
                      <Info className="w-3.5 h-3.5 text-[#008080]" />
                      Data Coverage & Zero-Fabrication Summary:
                    </span>
                    <p className="text-[11px] leading-relaxed">
                      • <strong>Sub-daily rainfall (1h, 3h, 6h):</strong> IMD automated real-time weather stations do not broadcast continuous sub-daily rainfall feeds for this grid cell. Under AQUORA zero-fabrication rules, these values remain <code>null</code> rather than inventing synthetic numbers.
                    </p>
                    <p className="text-[11px] leading-relaxed">
                      • <strong>Historical Flood Frequency:</strong> Explicitly quarantined and excluded from model inputs to prevent target label leakage.
                    </p>
                    <p className="text-[11px] leading-relaxed">
                      • <strong>Regional Domain Rasters & Input-Validity Policy:</strong> If geomorphic terrain features (Copernicus DEM 30m elevation, slope, HydroRIVERS distance) are unindexed, the location is strictly flagged as <code>INSUFFICIENT INPUT DATA</code> and inference is suppressed under the Phase 7E policy. XGBoost native NaN evaluation is never permitted to fabricate an arbitrary 1.30% base score on ungrounded points.
                    </p>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* TAB 3: REGIONAL BASIN DEMO */}
          {activeTab === 'regional' && (
            <div className="space-y-4">
              <div className="bg-slate-50 border border-slate-200 rounded-xl p-4">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700 mb-2">
                  Test Regional Watershed Intelligence (Level 2)
                </h3>
                <p className="text-xs text-slate-500 mb-3">
                  Evaluates 14 features across HydroBASINS watershed coverage. Population & Critical Facilities remain honest <code>None</code> with zero synthetic numbers.
                </p>

                <div className="flex flex-wrap gap-2 mb-3">
                  {[
                    { id: 'BASIN-GANGA', name: 'Ganga Basin (Patna)', lat: 25.60, lon: 85.15 },
                    { id: 'BASIN-BRAHMAPUTRA', name: 'Brahmaputra (Guwahati)', lat: 26.18, lon: 91.75 },
                    { id: 'BASIN-GODAVARI', name: 'Godavari (Nagpur / Nashik)', lat: 21.15, lon: 79.09 },
                    { id: 'BASIN-KRISHNA', name: 'Krishna (Vijayawada)', lat: 16.51, lon: 80.65 },
                    { id: 'BASIN-SABARMATI', name: 'Sabarmati (Ahmedabad)', lat: 23.02, lon: 72.57 },
                    { id: 'BASIN-WEST_COAST', name: 'West Coast / Konkan (Mumbai)', lat: 19.08, lon: 72.88 },
                    { id: 'BASIN-NARMADA', name: 'Narmada (Bharuch)', lat: 21.70, lon: 73.00 },
                    { id: 'BASIN-MAHANADI', name: 'Mahanadi (Cuttack / DFO 3382)', lat: 20.46, lon: 85.88 },
                  ].map((b) => (
                    <button
                      key={b.id}
                      onClick={() => {
                        setSelectedBasinId(b.id);
                        setRegionalLat(b.lat);
                        setRegionalLon(b.lon);
                        runRegionalScreening(b.lat, b.lon, b.id);
                      }}
                      className="px-3 py-1.5 text-xs font-bold rounded-lg bg-white border border-slate-200 text-slate-700 hover:bg-blue-50 hover:text-blue-700 transition-colors cursor-pointer"
                    >
                      {b.name}
                    </button>
                  ))}
                  <button
                    onClick={() => {
                      setSelectedBasinId('OUTSIDE');
                      setRegionalLat(12.0);
                      setRegionalLon(70.0);
                      runRegionalScreening(12.0, 70.0, 'OUTSIDE');
                    }}
                    className="px-3 py-1.5 text-xs font-bold rounded-lg bg-red-50 border border-red-200 text-red-700 hover:bg-red-100 transition-colors cursor-pointer"
                    title="Tests out of basin rejection without fallback"
                  >
                    Test Outside Basins (Arabian Sea)
                  </button>
                </div>

                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-1.5 text-xs">
                    <label className="text-slate-500 font-medium">Lat:</label>
                    <input
                      type="number"
                      step="0.01"
                      value={regionalLat}
                      onChange={(e) => setRegionalLat(parseFloat(e.target.value))}
                      className="w-24 px-2 py-1 text-xs border rounded font-mono"
                    />
                  </div>
                  <div className="flex items-center gap-1.5 text-xs">
                    <label className="text-slate-500 font-medium">Lon:</label>
                    <input
                      type="number"
                      step="0.01"
                      value={regionalLon}
                      onChange={(e) => setRegionalLon(parseFloat(e.target.value))}
                      className="w-24 px-2 py-1 text-xs border rounded font-mono"
                    />
                  </div>
                  <button
                    onClick={() => runRegionalScreening(regionalLat, regionalLon, selectedBasinId)}
                    disabled={regionalLoading}
                    className="px-4 py-1.5 text-xs font-bold text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors cursor-pointer disabled:opacity-50"
                  >
                    {regionalLoading ? 'Evaluating...' : 'Evaluate Basin'}
                  </button>
                </div>
              </div>

              {/* Basin Metadata Summary */}
              {basinSummary && (
                <div className="p-3 bg-blue-50/50 border border-blue-200 rounded-xl text-xs space-y-1">
                  <span className="font-bold text-blue-900 block">
                    🌊 {basinSummary.basin_name} ({basinSummary.basin_id})
                  </span>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px] text-slate-600 mt-1">
                    <div>Drainage Area: <strong>{basinSummary.drainage_area_km2 ? `${basinSummary.drainage_area_km2.toLocaleString()} km²` : 'N/A'}</strong></div>
                    <div>Status: <strong className="text-teal-700">{basinSummary.operational_status}</strong></div>
                    <div>Pfafstetter Code: <strong>{basinSummary.pfaf_code ?? 'Level 5/6'}</strong></div>
                    <div>States: <strong>{basinSummary.major_states?.join(', ') || 'Multi-state'}</strong></div>
                  </div>
                </div>
              )}

              {/* Regional Result */}
              {regionalResult && (
                <div className="border border-slate-200 rounded-xl p-4 bg-white space-y-3">
                  <div className="flex items-center justify-between pb-2 border-b border-slate-100">
                    <div className="flex items-center gap-2">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-extrabold uppercase ${regionalResult.status === 'READY'
                            ? 'bg-blue-100 text-blue-800'
                            : 'bg-red-100 text-red-800'
                          }`}
                      >
                        Status: {regionalResult.status}
                      </span>
                      <span className="text-xs font-semibold text-slate-700">
                        Exposure Grade: <strong>{regionalResult.exposure_grade}</strong>
                      </span>
                    </div>
                    <span className="text-xs font-bold text-slate-800 font-mono">
                      WEI: {regionalResult.watershed_exposure_index ?? 'N/A'}
                    </span>
                  </div>

                  {regionalResult.message && (
                    <p className="text-xs text-slate-700 bg-slate-50 p-2.5 rounded-lg border border-slate-100">
                      ℹ️ {regionalResult.message}
                    </p>
                  )}

                  {regionalResult.feature_values && (
                    <div>
                      <h4 className="text-xs font-bold text-slate-800 mb-2">
                        14 Authorized Regional Features (Zero Synthetic Values):
                      </h4>
                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px]">
                        {Object.entries(regionalResult.feature_values).map(([k, v]) => (
                          <div key={k} className="p-2 rounded bg-slate-50 border border-slate-100">
                            <span className="text-slate-500 block truncate">{k}</span>
                            <span className="font-bold text-slate-800 font-mono">
                              {v !== null ? v : <em className="text-slate-400">None (uningested)</em>}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* TAB 4: DEEP MITHI & RESTRICTIONS */}
          {activeTab === 'deep' && (
            <div className="space-y-4">
              <div className="bg-amber-50/70 border border-amber-200 rounded-xl p-4 text-xs text-amber-900 leading-relaxed">
                <span className="font-bold flex items-center gap-1.5 mb-1">
                  <ShieldCheck className="w-4 h-4 text-amber-700" />
                  Mumbai Mithi Is The Only Verified Deep Intelligence Zone:
                </span>
                <p>
                  Level 3 Deep Intelligence is supported exclusively in <strong>deep_mumbai_mithi</strong>.
                  Queries outside this zone strictly return <code>OUTSIDE_DEEP_ZONE_COVERAGE</code> with
                  <strong> zero silent fallback to Mumbai</strong>.
                </p>
              </div>

              <div className="bg-slate-50 border border-slate-200 rounded-xl p-4">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700 mb-2">
                  Test Deep Point Inspection & Restriction Gate
                </h3>
                <div className="flex flex-wrap gap-2 mb-3">
                  <button
                    onClick={() => {
                      setDeepLat(19.0728);
                      setDeepLon(72.8826);
                      runDeepInspection(19.0728, 72.8826);
                    }}
                    className="px-3 py-1.5 text-xs font-bold rounded-lg bg-teal-50 border border-teal-200 text-teal-800 hover:bg-teal-100 transition-colors cursor-pointer"
                  >
                    Valid Point: Kurla Junction (`19.07, 72.88`)
                  </button>
                  <button
                    onClick={() => {
                      setDeepLat(19.0650);
                      setDeepLon(72.8650);
                      runDeepInspection(19.0650, 72.8650);
                    }}
                    className="px-3 py-1.5 text-xs font-bold rounded-lg bg-teal-50 border border-teal-200 text-teal-800 hover:bg-teal-100 transition-colors cursor-pointer"
                  >
                    Valid Point: BKC Complex (`19.06, 72.86`)
                  </button>
                  <button
                    onClick={() => {
                      setDeepLat(25.60);
                      setDeepLon(85.15);
                      runDeepInspection(25.60, 85.15);
                    }}
                    className="px-3 py-1.5 text-xs font-bold rounded-lg bg-red-50 border border-red-200 text-red-700 hover:bg-red-100 transition-colors cursor-pointer"
                    title="Tests unsupported deep zone rejection without fallback"
                  >
                    Test Unsupported Deep Request: Patna (`25.60, 85.15`)
                  </button>
                  <button
                    onClick={() => {
                      setDeepLat(28.61);
                      setDeepLon(77.20);
                      runDeepInspection(28.61, 77.20);
                    }}
                    className="px-3 py-1.5 text-xs font-bold rounded-lg bg-red-50 border border-red-200 text-red-700 hover:bg-red-100 transition-colors cursor-pointer"
                    title="Tests unsupported deep zone rejection without fallback"
                  >
                    Test Unsupported Deep Request: Delhi (`28.61, 77.20`)
                  </button>
                </div>

                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-1.5 text-xs">
                    <label className="text-slate-500 font-medium">Lat:</label>
                    <input
                      type="number"
                      step="0.001"
                      value={deepLat}
                      onChange={(e) => setDeepLat(parseFloat(e.target.value))}
                      className="w-24 px-2 py-1 text-xs border rounded font-mono"
                    />
                  </div>
                  <div className="flex items-center gap-1.5 text-xs">
                    <label className="text-slate-500 font-medium">Lon:</label>
                    <input
                      type="number"
                      step="0.001"
                      value={deepLon}
                      onChange={(e) => setDeepLon(parseFloat(e.target.value))}
                      className="w-24 px-2 py-1 text-xs border rounded font-mono"
                    />
                  </div>
                  <button
                    onClick={() => runDeepInspection(deepLat, deepLon)}
                    disabled={deepLoading}
                    className="px-4 py-1.5 text-xs font-bold text-white bg-[#008080] hover:bg-teal-700 rounded-lg transition-colors cursor-pointer disabled:opacity-50"
                  >
                    {deepLoading ? 'Sampling...' : 'Inspect Deep Point'}
                  </button>
                </div>
              </div>

              {/* Deep Result */}
              {deepResult && (
                <div className="border border-slate-200 rounded-xl p-4 bg-white space-y-3">
                  <div className="flex items-center justify-between pb-2 border-b border-slate-100">
                    <div className="flex items-center gap-2">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-extrabold uppercase ${deepResult.point_in_zone
                            ? 'bg-teal-100 text-teal-800'
                            : 'bg-red-100 text-red-800'
                          }`}
                      >
                        Status: {deepResult.status}
                      </span>
                      <span className="text-xs text-slate-500">
                        In Zone: <strong>{deepResult.point_in_zone ? 'YES' : 'NO'}</strong>
                      </span>
                    </div>
                    <span className="text-xs text-slate-500">
                      Raster Sampled: <strong>{deepResult.raster_sampled ? 'YES (30m DEM)' : 'NO'}</strong>
                    </span>
                  </div>

                  <p className="text-xs text-slate-700 bg-slate-50 p-2.5 rounded-lg border border-slate-100">
                    ℹ️ {deepResult.message}
                  </p>

                  {deepResult.raster_sampled && (
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px]">
                      <div className="p-2 rounded bg-slate-50 border border-slate-100">
                        <span className="text-slate-500 block truncate">elevation_m</span>
                        <span className="font-bold text-slate-800 font-mono">
                          {deepResult.elevation_m !== null ? `${deepResult.elevation_m.toFixed(2)} m` : 'null'}
                        </span>
                      </div>
                      <div className="p-2 rounded bg-slate-50 border border-slate-100">
                        <span className="text-slate-500 block truncate">slope_degrees</span>
                        <span className="font-bold text-slate-800 font-mono">
                          {deepResult.slope_degrees !== null ? `${deepResult.slope_degrees.toFixed(2)}°` : 'null'}
                        </span>
                      </div>
                      <div className="p-2 rounded bg-slate-50 border border-slate-100">
                        <span className="text-slate-500 block truncate">aspect_degrees</span>
                        <span className="font-bold text-slate-800 font-mono">
                          {deepResult.aspect_degrees !== null ? `${deepResult.aspect_degrees.toFixed(2)}°` : 'null'}
                        </span>
                      </div>
                      <div className="p-2 rounded bg-slate-50 border border-slate-100">
                        <span className="text-slate-500 block truncate">flow_acc_cells</span>
                        <span className="font-bold text-slate-800 font-mono">
                          {deepResult.flow_accumulation_cells !== null ? deepResult.flow_accumulation_cells : 'null'}
                        </span>
                      </div>
                    </div>
                  )}

                  {deepResult.limitations && deepResult.limitations.length > 0 && (
                    <div className="p-2.5 rounded bg-amber-50/60 border border-amber-200 text-[11px] text-amber-900 space-y-1">
                      <span className="font-bold block">Scientific Governance Invariants:</span>
                      <ul className="list-disc list-inside space-y-0.5">
                        {deepResult.limitations.map((l, i) => (
                          <li key={i}>{l}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* TAB 5: SCIENTIFIC EVIDENCE & PROVENANCE */}
          {activeTab === 'provenance' && (
            <div className="space-y-4 text-xs">
              <div className="border border-slate-200 rounded-xl p-4 bg-slate-50/50 space-y-2">
                <h3 className="font-bold text-slate-900 text-sm flex items-center gap-2">
                  <Database className="w-4 h-4 text-[#008080]" />
                  Scientific Authority & Evidence Hierarchy
                </h3>
                <p className="text-slate-600 leading-relaxed">
                  AQUORA enforces a strict authority hierarchy to prevent uncalibrated machine learning models
                  or radar artifacts from overriding physical laws:
                </p>

                <div className="space-y-2 mt-3">
                  <div className="p-3 bg-white rounded-lg border border-teal-200 shadow-2xs">
                    <span className="font-extrabold text-teal-900 block">
                      1. Authoritative Physical Surface Flow Solver
                    </span>
                    <span className="text-slate-600">
                      Phase 6 Deterministic 2D Physical Flow & Drainage Coupling Engine (Copernicus GLO-30 DEM + rainfall-runoff + depression storage + D8 terrain-constrained routing + municipal drainage loss; mass conservation error &le; 1e-4 m³; simplified physical model, not a full 2D Saint-Venant shallow-water solver).
                    </span>
                  </div>

                  <div className="p-3 bg-white rounded-lg border border-amber-200 shadow-2xs">
                    <span className="font-extrabold text-amber-900 block">
                      2. Secondary Statistical Risk Signal (PROTOTYPE_ONLY)
                    </span>
                    <span className="text-slate-600">
                      XGBoost classifier (`aquora_xgboost_prototype.joblib`). Explicitly labeled as <code>NOT_CALIBRATED</code>. Provides relative ranking only; never overrides physical hydraulic depth.
                    </span>
                  </div>

                  <div className="p-3 bg-white rounded-lg border border-blue-200 shadow-2xs">
                    <span className="font-extrabold text-blue-900 block">
                      3. Corroborating Satellite Radar Evidence
                    </span>
                    <span className="text-slate-600">
                      Sentinel-1 GRD dual-polarization VV+VH bitemporal acquisitions for historical deluge events (E02–E07). Radar shadow, corner reflection, and wind-roughening limitations documented.
                    </span>
                  </div>
                </div>
              </div>

              <div className="border border-slate-200 rounded-xl p-4 bg-white space-y-2">
                <h4 className="font-bold text-slate-800">Precipitation Ingestion Provenance:</h4>
                <ul className="list-disc list-inside space-y-1 text-slate-600">
                  <li>
                    <strong>NASA GPM IMERG Final Daily V07B</strong>: 0.1° (~10km) calibration for historical Mumbai events E01–E07.
                  </li>
                  <li>
                    <strong>CHIRPS v2.0 Daily Precipitation</strong>: 0.05° (~5km) quasi-global historical records (1981–present) for national IFI v3 event reconciliation.
                  </li>
                  <li>
                    <strong>Zero Silent Zero-Filling Policy</strong>: All unextracted or missing observations strictly remain <code>NaN</code> / <code>null</code>.
                  </li>
                </ul>
              </div>
            </div>
          )}

        </div>

        {/* Modal Footer */}
        <div className="flex items-center justify-between px-6 py-3.5 border-t border-slate-200 bg-slate-50 text-xs">
          <span className="text-slate-500 font-medium">
            AQUORA 2.0 Governance: Zero Synthetic Labels · Real Primary Sources Only
          </span>
          <button
            onClick={onClose}
            className="px-4 py-2 font-bold text-white bg-[#008080] hover:bg-teal-700 rounded-xl transition-colors cursor-pointer"
          >
            Apply & View Dashboard
          </button>
        </div>

      </div>
    </div>
  );
};
