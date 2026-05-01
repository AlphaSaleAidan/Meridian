import { useState, useMemo } from 'react'
import Map, { Source, Layer, type ViewStateChangeEvent } from 'react-map-gl'
import type { CircleLayer, HeatmapLayer } from 'react-map-gl'
import 'mapbox-gl/dist/mapbox-gl.css'

interface CustomerLocation {
  id: string
  lat: number
  lng: number
  spend_cents: number
  visits: number
  name?: string
}

interface GeoMapProps {
  customers: CustomerLocation[]
  mapboxToken?: string
  mode?: 'heatmap' | 'points'
  className?: string
}

const MAPBOX_TOKEN = import.meta.env.VITE_MAPBOX_TOKEN || ''

function spendColor(cents: number): string {
  if (cents >= 50000) return '#17C5B0'  // green — high spender
  if (cents >= 15000) return '#F5A623'  // yellow — medium
  return '#EF4444'                       // red — low
}

export default function GeoMap({
  customers,
  mapboxToken = MAPBOX_TOKEN,
  mode = 'heatmap',
  className = '',
}: GeoMapProps) {
  const [viewState, setViewState] = useState({
    longitude: -98.5,
    latitude: 39.8,
    zoom: 3.5,
  })

  const geojson = useMemo(() => ({
    type: 'FeatureCollection' as const,
    features: customers.map((c) => ({
      type: 'Feature' as const,
      geometry: {
        type: 'Point' as const,
        coordinates: [c.lng, c.lat],
      },
      properties: {
        id: c.id,
        spend_cents: c.spend_cents,
        visits: c.visits,
        name: c.name || '',
        color: spendColor(c.spend_cents),
      },
    })),
  }), [customers])

  const heatmapLayer: HeatmapLayer = {
    id: 'customer-heat',
    type: 'heatmap',
    paint: {
      'heatmap-weight': ['interpolate', ['linear'], ['get', 'spend_cents'], 0, 0, 100000, 1],
      'heatmap-intensity': ['interpolate', ['linear'], ['zoom'], 0, 1, 9, 3],
      'heatmap-radius': ['interpolate', ['linear'], ['zoom'], 0, 2, 9, 20],
      'heatmap-color': [
        'interpolate', ['linear'], ['heatmap-density'],
        0, 'rgba(0,0,0,0)',
        0.2, '#3B0764',
        0.4, '#7C3AED',
        0.6, '#F59E0B',
        0.8, '#F97316',
        1, '#17C5B0',
      ],
      'heatmap-opacity': 0.8,
    },
  }

  const pointLayer: CircleLayer = {
    id: 'customer-points',
    type: 'circle',
    paint: {
      'circle-radius': ['interpolate', ['linear'], ['get', 'visits'], 1, 4, 50, 16],
      'circle-color': ['get', 'color'],
      'circle-opacity': 0.8,
      'circle-stroke-width': 1,
      'circle-stroke-color': '#1F1F23',
    },
  }

  if (!mapboxToken) {
    return (
      <div className={`bg-[#1F1F23] rounded-xl border border-[#2A2A2E] p-8 flex items-center justify-center ${className}`}>
        <p className="text-[#A1A1A8] text-sm">
          Set VITE_MAPBOX_TOKEN to enable the geospatial map
        </p>
      </div>
    )
  }

  return (
    <div className={`rounded-xl overflow-hidden border border-[#2A2A2E] ${className}`}>
      <Map
        {...viewState}
        onMove={(e: ViewStateChangeEvent) => setViewState(e.viewState)}
        mapboxAccessToken={mapboxToken}
        mapStyle="mapbox://styles/mapbox/dark-v11"
        style={{ width: '100%', height: '100%', minHeight: 400 }}
      >
        <Source id="customers" type="geojson" data={geojson}>
          {mode === 'heatmap' ? (
            <Layer {...heatmapLayer} />
          ) : (
            <Layer {...pointLayer} />
          )}
        </Source>
      </Map>

      <div className="bg-[#1F1F23] px-4 py-2 flex items-center gap-4 text-xs text-[#A1A1A8]">
        <span className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-[#17C5B0]" />
          High ($500+)
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-[#F5A623]" />
          Medium ($150-500)
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-[#EF4444]" />
          Low (&lt;$150)
        </span>
        <span className="ml-auto">{customers.length} customers</span>
      </div>
    </div>
  )
}
