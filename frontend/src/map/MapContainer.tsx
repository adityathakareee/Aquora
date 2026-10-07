import React from 'react';
import { LeafletMap } from './LeafletMap';
import { useLocationStore } from '@/store/useLocationStore';

export const MapContainer: React.FC<{
  center?: [number, number];
  zoom?: number;
  className?: string;
  height?: string;
  floodIntensityMultiplier?: number;
}> = ({ center, zoom, className, height = '400px', floodIntensityMultiplier = 1.0 }) => {
  const storeCenter = useLocationStore((s) => s.mapCenter);
  const storeZoom = useLocationStore((s) => s.mapZoom);
  const effectiveCenter = center || storeCenter;
  const effectiveZoom = zoom !== undefined ? zoom : storeZoom;

  return (
    <LeafletMap
      center={effectiveCenter}
      zoom={effectiveZoom}
      height={height}
      className={className}
      floodIntensityMultiplier={floodIntensityMultiplier}
      polylines={[
        {
          id: 'mithi_river_main',
          title: 'Mithi River Corridor',
          positions: [
            [19.120, 72.895],
            [19.102, 72.885],
            [19.088, 72.880],
            [19.072, 72.872],
            [19.055, 72.860],
            [19.040, 72.850],
          ],
          color: '#0284c7',
          weight: 4,
          opacity: 0.9,
        },
      ]}
      polygons={[]}
      markers={[
        {
          id: 'kurla_junction',
          position: [19.072, 72.880],
          title: 'Kurla Junction',
          subtitle: 'High risk',
          color: '#dc2626',
          badge: '!',
        },
        {
          id: 'sion_hospital',
          position: [19.050, 72.862],
          title: 'Sion Hospital',
          subtitle: 'Access at risk',
          color: '#dc2626',
          badge: '+',
        },
        {
          id: 'bkc_center',
          position: [19.065, 72.865],
          title: 'Bandra Kurla Complex',
          subtitle: 'Command Hub',
          color: '#1a56db',
          badge: 'C',
        },
      ]}
    />
  );
};

export default MapContainer;
