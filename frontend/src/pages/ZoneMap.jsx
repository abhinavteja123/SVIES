import { useState, useEffect } from 'react';
import { api } from '../api';
import { MapContainer, TileLayer, Polygon, Popup, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';

const ZONE_COLORS = {
    SCHOOL: '#f59e0b',
    HOSPITAL: '#ef4444',
    GOVT: '#6366f1',
    LOW_EMISSION: '#22c55e',
    HIGHWAY: '#06b6d4',
};

const ZONE_LABELS = {
    SCHOOL: 'School Zone',
    HOSPITAL: 'Hospital Zone',
    GOVT: 'Government',
    LOW_EMISSION: 'Low Emission',
    HIGHWAY: 'Highway',
};

function FitBounds({ zones }) {
    const map = useMap();
    useEffect(() => {
        if (zones.length === 0) return;
        const allCoords = zones.flatMap(z =>
            (z.polygon || []).map(c => [c[1], c[0]])
        );
        if (allCoords.length > 0) {
            map.fitBounds(allCoords, { padding: [40, 40], maxZoom: 14 });
        }
    }, [zones, map]);
    return null;
}

export default function ZoneMap() {
    const [zones, setZones] = useState([]);
    const [loading, setLoading] = useState(true);
    const [selectedType, setSelectedType] = useState('ALL');

    useEffect(() => {
        api.getZones()
            .then(d => setZones(d.zones || []))
            .catch(console.error)
            .finally(() => setLoading(false));
    }, []);

    if (loading) return <div className="loading"><div className="spinner"></div>Loading zones...</div>;

    const center = zones.length > 0 && zones[0].center
        ? [zones[0].center.lat, zones[0].center.lon]
        : [17.385, 78.4867]; // Hyderabad default

    const filteredZones = selectedType === 'ALL'
        ? zones
        : zones.filter(z => z.type === selectedType);

    const zoneTypes = [...new Set(zones.map(z => z.type))];

    return (
        <div className="page">
            <div className="page-header">
                <h2>Geofence Zone Map</h2>
                <p>Monitored enforcement zones across Hyderabad — priority areas with risk multipliers</p>
            </div>

            {/* Legend + Filter */}
            <div className="card" style={{ padding: '14px 20px', marginBottom: 16 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 16, flexWrap: 'wrap' }}>
                    <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                        Filter:
                    </span>
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
                            <span style={{
                                display: 'inline-block', width: 8, height: 8, borderRadius: '50%',
                                background: ZONE_COLORS[type] || '#6366f1', marginRight: 6,
                            }} />
                            {ZONE_LABELS[type] || type} ({zones.filter(z => z.type === type).length})
                        </button>
                    ))}
                </div>
            </div>

            <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
                <div className="map-container" style={{ height: 520 }}>
                    <MapContainer center={center} zoom={12} style={{ height: '100%', width: '100%' }}
                        scrollWheelZoom={true}>
                        <TileLayer
                            attribution='&copy; <a href="https://osm.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/">CARTO</a>'
                            url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png"
                        />
                        <FitBounds zones={filteredZones} />
                        {filteredZones.map(z => {
                            const positions = (z.polygon || []).map(c => [c[1], c[0]]);
                            const color = ZONE_COLORS[z.type] || '#6366f1';
                            return (
                                <Polygon key={z.id} positions={positions}
                                    pathOptions={{ color, fillColor: color, fillOpacity: 0.2, weight: 3 }}>
                                    <Popup>
                                        <div style={{ fontFamily: 'Inter, sans-serif', minWidth: 180 }}>
                                            <strong style={{ fontSize: 14 }}>{z.name}</strong>
                                            <div style={{ marginTop: 8, fontSize: 12, lineHeight: 1.8 }}>
                                                <div><span style={{ color: '#666' }}>Type:</span> <span style={{ color, fontWeight: 600 }}>{ZONE_LABELS[z.type] || z.type}</span></div>
                                                <div><span style={{ color: '#666' }}>Priority:</span> <strong>{z.priority}</strong></div>
                                                <div><span style={{ color: '#666' }}>Risk Multiplier:</span> <strong style={{ color: '#f59e0b' }}>{z.multiplier}x</strong></div>
                                            </div>
                                        </div>
                                    </Popup>
                                </Polygon>
                            );
                        })}
                    </MapContainer>
                </div>
            </div>

            {/* Zone Cards Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 16, marginTop: 20 }}>
                {filteredZones.map(z => (
                    <div className="card" key={z.id} style={{ borderLeft: `3px solid ${ZONE_COLORS[z.type] || '#6366f1'}`, padding: 18 }}>
                        <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 10, color: 'var(--text-primary)' }}>{z.name}</div>
                        <div className="info-row"><span className="info-label">Type</span><span className="info-value" style={{ color: ZONE_COLORS[z.type] }}>{ZONE_LABELS[z.type] || z.type}</span></div>
                        <div className="info-row"><span className="info-label">Priority</span><span className="info-value">{z.priority}</span></div>
                        <div className="info-row"><span className="info-label">Multiplier</span><span className="info-value" style={{ color: '#f59e0b' }}>{z.multiplier}x</span></div>
                        <div className="info-row"><span className="info-label">Zone ID</span><span className="info-value" style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11 }}>{z.id}</span></div>
                    </div>
                ))}
            </div>
        </div>
    );
}
