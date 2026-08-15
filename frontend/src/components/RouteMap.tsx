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
function pin(
  n: number | string,
  tone: 'stop' | 'origin' | 'tight' = 'stop',
  active = false,
): L.DivIcon {
  const bg = tone === 'origin' ? '#0E0E11' : tone === 'tight' ? '#E5484D' : '#1A8FD6'
  const border = tone === 'origin' ? '#A1A1A8' : bg
  const color = tone === 'origin' ? '#A1A1A8' : '#FFFFFF'
  const size = active ? 34 : 26
  // A ring rather than a size jump alone: the pin has to stay where it is on
  // the map while it highlights, or the eye reads it as a different stop.
  const ring = active ? 'box-shadow:0 0 0 4px rgba(255,255,255,.22),0 2px 10px rgba(0,0,0,.6);' : 'box-shadow:0 2px 8px rgba(0,0,0,.5);'
  return L.divIcon({
    className: '',
    html: `<div style="
      width:${size}px;height:${size}px;border-radius:50%;
      background:${bg};border:2px solid ${border};
      color:${color};font:600 ${active ? 13 : 11}px ui-monospace,monospace;
      display:flex;align-items:center;justify-content:center;
      transition:width .12s,height .12s;${ring}">${n}</div>`,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
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
  origin, stops, height = 320, tightLegs = [], activeIndex = null, onHover,
}: {
  origin: MapPoint
  stops: MapPoint[]
  height?: number
  /** Index of each leg (0 = origin→stop 1) the clock does not allow. The map
   *  has to show the problem, not just the shape — a run drawn all in one
   *  colour hides the only thing on this screen worth acting on. */
  tightLegs?: number[]
  /** Stop the operator is pointing at in the list, so the two stay in sync. */
  activeIndex?: number | null
  onHover?: (index: number | null) => void
}) {
  const all = useMemo(() => [origin, ...stops], [origin, stops])

  /** One polyline PER LEG rather than a single line through every stop, so a
   *  leg that will not make it can be drawn differently from one that will. */
  const legs = useMemo(
    () => all.slice(0, -1).map((from, i) => ({
      index: i,
      tight: tightLegs.includes(i),
      positions: [
        [from.lat, from.lng] as [number, number],
        [all[i + 1].lat, all[i + 1].lng] as [number, number],
      ],
    })),
    [all, tightLegs],
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
        {legs.map((leg) => (
          <Polyline
            key={leg.index}
            positions={leg.positions}
            pathOptions={{
              color: leg.tight ? '#E5484D' : '#1A8FD6',
              weight: leg.tight ? 3 : 2,
              opacity: leg.tight ? 0.95 : 0.8,
              dashArray: '6 5',
            }}
          />
        ))}

        <Marker position={[origin.lat, origin.lng]} icon={pin('◆', 'origin')}>
          <Popup>{origin.label}</Popup>
        </Marker>

        {stops.map((s, i) => (
          <Marker
            key={`${s.lat}-${s.lng}-${i}`}
            position={[s.lat, s.lng]}
            icon={pin(i + 1, tightLegs.includes(i) ? 'tight' : 'stop', activeIndex === i)}
            eventHandlers={{
              mouseover: () => onHover?.(i),
              mouseout: () => onHover?.(null),
            }}
          >
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
