/**
 * A real map for a real route.
 *
 * The first version of this was hand-drawn SVG — stops plotted against their
 * own bounding box on a grid. It showed the SHAPE of a run and nothing else,
 * and Aidan was right that it is not a map: a detailer looking at two dots
 * cannot tell whether they are across a bridge or across a car park, and that
 * difference is the entire question the screen exists to answer.
 *
 * Leaflet with CARTO's dark basemap. Chosen for three reasons: no API key, so
 * nothing here is blocked on an account; a dark style that belongs in this
 * portal rather than a white rectangle stapled into it; and it is the
 * boringly standard choice, which matters for a component that has to keep
 * working without anyone thinking about it.
 *
 * ⚠️ TILE POLICY. CARTO's free basemaps are fine for a demo and light use and
 * are NOT a production plan for a merchant fleet. Before this ships to paying
 * merchants it needs a tile provider with a contract — MapTiler, Stadia or
 * Mapbox — which is a key and a bill, not a rewrite: swap TILE_URL.
 */
import { useEffect, useMemo } from 'react'
import { MapContainer, Marker, Polyline, Popup, TileLayer, useMap } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

export interface MapPoint {
  lat: number
  lng: number
  label: string
  sub?: string
}

const TILE_URL = 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png'
const ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'

/**
 * Numbered pins, drawn as markup rather than image assets.
 *
 * Leaflet's default marker icons are loaded from a bundler-relative path that
 * breaks in most build setups — the classic "markers are invisible" bug. A
 * divIcon avoids that entirely AND lets the stop number live inside the pin,
 * which is what ties the map to the list beside it.
 */
function pin(n: number | string, tone: 'stop' | 'origin' = 'stop'): L.DivIcon {
  const bg = tone === 'origin' ? '#0E0E11' : '#1A8FD6'
  const border = tone === 'origin' ? '#A1A1A8' : '#1A8FD6'
  const color = tone === 'origin' ? '#A1A1A8' : '#FFFFFF'
  return L.divIcon({
    className: '',
    html: `<div style="
      width:26px;height:26px;border-radius:50%;
      background:${bg};border:2px solid ${border};
      color:${color};font:600 11px ui-monospace,monospace;
      display:flex;align-items:center;justify-content:center;
      box-shadow:0 2px 8px rgba(0,0,0,.5)">${n}</div>`,
    iconSize: [26, 26],
    iconAnchor: [13, 13],
  })
}

/** Keep every stop in frame when the day changes. */
function FitBounds({ points }: { points: MapPoint[] }) {
  const map = useMap()
  useEffect(() => {
    if (points.length === 0) return
    if (points.length === 1) {
      map.setView([points[0].lat, points[0].lng], 13)
      return
    }
    map.fitBounds(
      L.latLngBounds(points.map((p) => [p.lat, p.lng] as [number, number])),
      { padding: [36, 36], maxZoom: 14 },
    )
  }, [map, points])
  return null
}

export default function RouteMap({
  origin, stops, height = 320,
}: {
  origin: MapPoint
  stops: MapPoint[]
  height?: number
}) {
  const all = useMemo(() => [origin, ...stops], [origin, stops])
  const line = useMemo(
    () => all.map((p) => [p.lat, p.lng] as [number, number]),
    [all],
  )

  if (stops.length === 0) return null

  return (
    <div
      className="overflow-hidden rounded-lg border border-[#1F1F23]"
      style={{ height }}
    >
      <MapContainer
        center={[origin.lat, origin.lng]}
        zoom={12}
        scrollWheelZoom={false}
        style={{ height: '100%', width: '100%', background: '#0E0E11' }}
        attributionControl
      >
        <TileLayer url={TILE_URL} attribution={ATTRIBUTION} />
        <FitBounds points={all} />

        {/* Dashed, because it is the ORDER of the stops, not the roads taken.
            A solid line would imply a route we have not actually computed. */}
        <Polyline
          positions={line}
          pathOptions={{ color: '#1A8FD6', weight: 2, opacity: 0.85, dashArray: '6 5' }}
        />

        <Marker position={[origin.lat, origin.lng]} icon={pin('◆', 'origin')}>
          <Popup>{origin.label}</Popup>
        </Marker>

        {stops.map((s, i) => (
          <Marker key={`${s.lat}-${s.lng}-${i}`} position={[s.lat, s.lng]} icon={pin(i + 1)}>
            <Popup>
              <strong>{s.label}</strong>
              {s.sub && <div>{s.sub}</div>}
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </div>
  )
}
