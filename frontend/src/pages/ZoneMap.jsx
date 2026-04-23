import { useState, useEffect, useCallback, useRef } from 'react';
import { api } from '../api';
import { MapContainer, TileLayer, Polygon, Popup, useMap, useMapEvents } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { RefreshCw, MapPin, Layers, AlertTriangle, CheckCircle } from 'lucide-react';
import toast from 'react-hot-toast';

const ZONE_COLORS = {
  SCHOOL:       '#f59e0b',
  HOSPITAL:     '#ef4444',
  GOVT:         '#6366f1',
  LOW_EMISSION: '#22c55e',
  HIGHWAY:      '#06b6d4',
};

const ZONE_LABELS = {
  SCHOOL:       'School Zone',
  HOSPITAL:     'Hospital Zone',
  GOVT:         'Government',
  LOW_EMISSION: 'Low Emission',
  HIGHWAY:      'Highway',
};

const ZONE_PRIORITY_COLORS = {
  HIGH:   '#ef4444',
  MEDIUM: '#f59e0b',
  LOW:    '#22c55e',
};

// ── Fit map to all zone polygons on first load ──
function FitBounds({ zones }) {
  const map = useMap();
  const fitted = useRef(false);
  useEffect(() => {
    if (fitted.current || zones.length === 0) return;
    const allCoords = zones.flatMap(z => (z.polygon || []).map(c => [c[1], c[0]]));
    if (allCoords.length > 0) {
      map.fitBounds(allCoords, { padding: [40, 40], maxZoom: 14 });
      fitted.current = true;
    }
  }, [zones, map]);
  return null;
}

// ── Track map center as user pans ──
function MapCenterTracker({ onCenterChange }) {
  useMapEvents({
    moveend(e) {
      const { lat, lng } = e.target.getCenter();
      onCenterChange(lat, lng);
    },
  });
  return null;
}

export default function ZoneMap() {
  const [zones, setZones]               = useState([]);
  const [loading, setLoading]           = useState(true);
  const [refreshing, setRefreshing]     = useState(false);
  const [selectedType, setSelectedType] = useState('ALL');
  const [osmMessage, setOsmMessage]     = useState('');
  const [mapCenter, setMapCenter]       = useState({ lat: 17.385, lon: 78.4867 });
  const [radiusM, setRadiusM]           = useState(3000);
  const [lastRefreshed, setLastRefreshed] = useState(null);

  // ── Initial load ──
  useEffect(() => {
    api.getZones()
      .then(d => setZones(d.zones || []))
      .catch(() => toast.error('Failed to load zones'))
      .finally(() => setLoading(false));
  }, []);

  // ── OSM Dynamic Refresh ──
  const handleOsmRefresh = useCallback(async () => {
    setRefreshing(true);
    setOsmMessage('');
    try {
      const data = await api.refreshZones(mapCenter.lat, mapCenter.lon, radiusM);
      setZones(data.zones || []);
      setLastRefreshed(new Date());
      const msg = data.message || `+${data.osm_zones_added} OSM zone(s) added`;
      setOsmMessage(msg);
      if (data.osm_zones_added > 0) {
        toast.success(msg);
      } else {
        toast(`No new OSM zones found near this location. Showing ${data.total_zones} total zones.`, { icon: '🗺️' });
      }
    } catch (err) {
      toast.error('OSM refresh failed: ' + (err.message || 'Network error'));
    } finally {
      setRefreshing(false);
    }
  }, [mapCenter, radiusM]);

  if (loading) return (
    <div className="page" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: 400 }}>
      <div style={{ textAlign: 'center', color: 'var(--text-secondary)' }}>
        <div className="spinner" style={{ margin: '0 auto 1rem' }} />
        Loading zones...
      </div>
    </div>
  );

  const filteredZones = selectedType === 'ALL'
    ? zones
    : zones.filter(z => z.type === selectedType);

  const zoneTypes = [...new Set(zones.map(z => z.type))].sort();
  const osmZones  = zones.filter(z => z.source === 'openstreetmap');
  const staticZones = zones.filter(z => z.source !== 'openstreetmap');

  const center = zones.length > 0 && zones[0].center
    ? [zones[0].center.lat, zones[0].center.lon]
    : [17.385, 78.4867];

  return (
    <div className="page vehicle-management">
      <div className="page-header">
        <h2>Geofence Zone Map</h2>
        <p>Live enforcement zones — static + dynamic from OpenStreetMap</p>
      </div>

      {/* Stats bar */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 12, marginBottom: 16 }}>
        {[
          { label: 'Total Zones',   value: zones.length,        color: '#6366f1' },
          { label: 'Static (JSON)', value: staticZones.length,  color: '#06b6d4' },
          { label: 'OSM Dynamic',   value: osmZones.length,     color: '#22c55e' },
          { label: 'High Priority', value: zones.filter(z => z.priority === 'HIGH').length, color: '#ef4444' },
        ].map(s => (
          <div key={s.label} className="card" style={{ padding: '14px 18px' }}>
            <div style={{ fontSize: '1.5rem', fontWeight: 800, color: s.color }}>{s.value}</div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 2 }}>{s.label}</div>
          </div>
        ))}
      </div>

      {/* Controls */}
      <div className="card" style={{ padding: '14px 20px', marginBottom: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>

          {/* Filter buttons */}
          <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Filter:</span>
          <button
            className={`btn btn-sm ${selectedType === 'ALL' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setSelectedType('ALL')}
          >
            All ({zones.length})
          </button>
          {zoneTypes.map(type => (
            <button
              key={type}
              className={`btn btn-sm ${selectedType === type ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setSelectedType(type)}
              style={selectedType !== type ? { borderColor: ZONE_COLORS[type] || '#6366f1', color: ZONE_COLORS[type] || '#6366f1' } : {}}
            >
              <span style={{ display: 'inline-block', width: 7, height: 7, borderRadius: '50%', background: ZONE_COLORS[type] || '#6366f1', marginRight: 5 }} />
              {ZONE_LABELS[type] || type} ({zones.filter(z => z.type === type).length})
            </button>
          ))}

          {/* Spacer */}
          <div style={{ flex: 1 }} />

          {/* Radius selector */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>Radius:</span>
            <select
              className="form-input"
              value={radiusM}
              onChange={e => setRadiusM(Number(e.target.value))}
              style={{ appearance: 'none', padding: '4px 10px', fontSize: '0.82rem', cursor: 'pointer', width: 100 }}
            >
              <option value={1000}>1 km</option>
              <option value={2000}>2 km</option>
              <option value={3000}>3 km</option>
              <option value={5000}>5 km</option>
              <option value={10000}>10 km</option>
            </select>
          </div>

          {/* OSM Refresh button */}
          <button
            className="btn btn-primary"
            onClick={handleOsmRefresh}
            disabled={refreshing}
            style={{ gap: 8, display: 'flex', alignItems: 'center' }}
            title="Pan the map to a location, then click to pull real schools/hospitals/govt buildings from OpenStreetMap"
          >
            <RefreshCw size={15} style={{ animation: refreshing ? 'spin 1s linear infinite' : 'none' }} />
            {refreshing ? 'Fetching OSM...' : 'Refresh from OSM'}
          </button>
        </div>

        {/* OSM status message */}
        {osmMessage && (
          <div style={{ marginTop: 10, fontSize: '0.8rem', color: '#22c55e', display: 'flex', alignItems: 'center', gap: 6 }}>
            <CheckCircle size={13} />
            {osmMessage}
            {lastRefreshed && <span style={{ color: 'var(--text-muted)', marginLeft: 8 }}>
              Last updated: {lastRefreshed.toLocaleTimeString()}
            </span>}
          </div>
        )}

        {/* Map center indicator */}
        <div style={{ marginTop: osmMessage ? 4 : 10, fontSize: '0.75rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 5 }}>
          <MapPin size={11} />
          Map centre: {mapCenter.lat.toFixed(4)}, {mapCenter.lon.toFixed(4)} — Pan the map then click "Refresh from OSM" to load real zones from that area
        </div>
      </div>

      {/* Map */}
      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        <div style={{ height: 540 }}>
          <MapContainer center={center} zoom={12} style={{ height: '100%', width: '100%' }} scrollWheelZoom={true}>
            <TileLayer
              attribution='&copy; <a href="https://osm.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/">CARTO</a>'
              url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png"
            />
            <FitBounds zones={filteredZones} />
            <MapCenterTracker onCenterChange={(lat, lon) => setMapCenter({ lat, lon })} />

            {filteredZones.map(z => {
              const positions = (z.polygon || []).map(c => [c[1], c[0]]);
              const color = ZONE_COLORS[z.type] || '#6366f1';
              const isOsm = z.source === 'openstreetmap';
              return (
                <Polygon key={z.id} positions={positions}
                  pathOptions={{
                    color,
                    fillColor: color,
                    fillOpacity: isOsm ? 0.15 : 0.22,
                    weight: isOsm ? 2 : 3,
                    dashArray: isOsm ? '6 4' : null,  // dashed border = OSM zone
                  }}
                >
                  <Popup>
                    <div style={{ fontFamily: 'Inter, sans-serif', minWidth: 200 }}>
                      <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 6 }}>{z.name}</div>
                      <div style={{ display: 'grid', gridTemplateColumns: 'auto 1fr', gap: '4px 10px', fontSize: 12 }}>
                        <span style={{ color: '#888' }}>Type</span>
                        <span style={{ color, fontWeight: 600 }}>{ZONE_LABELS[z.type] || z.type}</span>
                        <span style={{ color: '#888' }}>Priority</span>
                        <span style={{ color: ZONE_PRIORITY_COLORS[z.priority] || '#888', fontWeight: 600 }}>{z.priority}</span>
                        <span style={{ color: '#888' }}>Risk Multiplier</span>
                        <span style={{ color: '#f59e0b', fontWeight: 700 }}>{z.multiplier}x</span>
                        <span style={{ color: '#888' }}>Source</span>
                        <span style={{ fontStyle: 'italic' }}>{isOsm ? '🌍 OpenStreetMap' : '📁 Static JSON'}</span>
                      </div>
                    </div>
                  </Popup>
                </Polygon>
              );
            })}
          </MapContainer>
        </div>
      </div>

      {/* Legend */}
      <div className="card" style={{ padding: '12px 20px', marginTop: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 24, flexWrap: 'wrap', fontSize: '0.78rem' }}>
          <span style={{ color: 'var(--text-muted)', fontWeight: 600 }}>LEGEND:</span>
          {Object.entries(ZONE_COLORS).map(([type, color]) => (
            <span key={type} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ width: 12, height: 12, background: color, borderRadius: 3, display: 'inline-block' }} />
              {ZONE_LABELS[type] || type}
            </span>
          ))}
          <span style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--text-muted)' }}>
            <span style={{ width: 20, height: 2, background: '#999', display: 'inline-block', borderTop: '2px dashed #999' }} />
            OSM Dynamic Zone
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--text-muted)' }}>
            <span style={{ width: 20, height: 2, background: '#999', display: 'inline-block' }} />
            Static Zone
          </span>
        </div>
      </div>

      {/* Zone Cards Grid */}
      {filteredZones.length > 0 && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 12, marginTop: 16 }}>
          {filteredZones.map(z => {
            const isOsm = z.source === 'openstreetmap';
            return (
              <div className="card" key={z.id} style={{
                borderLeft: `3px solid ${ZONE_COLORS[z.type] || '#6366f1'}`,
                padding: 16,
                opacity: 1,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 10 }}>
                  <div style={{ fontWeight: 700, fontSize: 14, color: 'var(--text-primary)', flex: 1 }}>{z.name}</div>
                  {isOsm && (
                    <span style={{ fontSize: '0.65rem', background: 'rgba(34,197,94,0.15)', color: '#22c55e', padding: '2px 6px', borderRadius: 4, whiteSpace: 'nowrap', marginLeft: 8 }}>
                      OSM
                    </span>
                  )}
                </div>
                <div className="info-row"><span className="info-label">Type</span><span className="info-value" style={{ color: ZONE_COLORS[z.type] }}>{ZONE_LABELS[z.type] || z.type}</span></div>
                <div className="info-row">
                  <span className="info-label">Priority</span>
                  <span className="info-value" style={{ color: ZONE_PRIORITY_COLORS[z.priority] || 'var(--text-primary)', fontWeight: 700 }}>{z.priority}</span>
                </div>
                <div className="info-row"><span className="info-label">Multiplier</span><span className="info-value" style={{ color: '#f59e0b', fontWeight: 700 }}>{z.multiplier}x</span></div>
                <div className="info-row">
                  <span className="info-label">Zone ID</span>
                  <span className="info-value" style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10 }}>{z.id}</span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
