import React, { useState, useEffect, useRef, useCallback } from 'react';
import './App.css';

// ============================================================================
// TIPOS
// ============================================================================

interface Camera {
  id: string;
  name: string;
  type: 'ptz' | 'fixed';
  thermal: boolean;
  position: { x: number; y: number };
  fov: { horizontal: number; vertical: number };
  status: 'online' | 'offline';
}

interface Detection {
  camera_id: string;
  camera_name: string;
  timestamp: string;
  detections: Array<{
    type: string;
    bbox?: { x: number; y: number; w: number; h: number };
    confidence?: number;
    area?: number;
    movement_percent?: number;
  }>;
}

interface MapArea {
  x: number;
  y: number;
  w: number;
  h: number;
}

// ============================================================================
// COMPONENTES
// ============================================================================

const CameraIcon: React.FC<{
  camera: Camera;
  isSelected: boolean;
  panAngle: number;
  onClick: () => void;
}> = ({ camera, isSelected, panAngle, onClick }) => {
  const iconColor = camera.status === 'online' ? '#22c55e' : '#ef4444';
  const iconType = camera.thermal ? '🌡️' : camera.type === 'ptz' ? '🎥' : '📹';
  const rad = panAngle * (Math.PI / 180);
  const arrowLen = 32;
  const ax = Math.cos(rad) * arrowLen;
  const ay = Math.sin(rad) * arrowLen;

  return (
    <g
      onClick={onClick}
      style={{ cursor: 'pointer' }}
      transform={`translate(${camera.position.x}, ${camera.position.y})`}
    >
      {/* Seta de direção (somente PTZ) */}
      {camera.type === 'ptz' && (
        <line x1="0" y1="0" x2={ax} y2={ay}
          stroke={isSelected ? '#60a5fa' : 'rgba(147,197,253,0.75)'}
          strokeWidth={isSelected ? 3 : 2}
          strokeLinecap="round"
          pointerEvents="none"
        />
      )}
      {/* Círculo base */}
      <circle
        r="18"
        fill={iconColor}
        opacity={isSelected ? 0.9 : 0.6}
        style={{ transition: 'opacity 0.2s' }}
      />
      {/* Ícone */}
      <text fontSize="13" textAnchor="middle" dominantBaseline="middle" fill="white">
        {iconType}
      </text>
      {/* Rótulo */}
      <text y="32" fontSize="10" textAnchor="middle" fill="white"
        style={{ pointerEvents: 'none' }}>
        {camera.name.split(' ').pop()}
      </text>
    </g>
  );
};

const CameraFOV: React.FC<{ camera: Camera; angle: number; isActive: boolean }> = ({ camera, angle, isActive }) => {
  const range = 160;
  const halfRad = (camera.fov.horizontal / 2) * (Math.PI / 180);
  const dirRad = angle * (Math.PI / 180);
  const cx = camera.position.x;
  const cy = camera.position.y;
  const x1 = cx + range * Math.cos(dirRad - halfRad);
  const y1 = cy + range * Math.sin(dirRad - halfRad);
  const x2 = cx + range * Math.cos(dirRad + halfRad);
  const y2 = cy + range * Math.sin(dirRad + halfRad);
  const largeArc = camera.fov.horizontal > 180 ? 1 : 0;

  return (
    <path
      d={`M ${cx} ${cy} L ${x1} ${y1} A ${range} ${range} 0 ${largeArc} 1 ${x2} ${y2} Z`}
      fill={isActive ? 'rgba(59,130,246,0.15)' : 'rgba(100,150,255,0.05)'}
      stroke={isActive ? 'rgba(59,130,246,0.7)' : 'rgba(100,150,255,0.25)'}
      strokeWidth={isActive ? 2 : 1}
      strokeDasharray={isActive ? undefined : '5,5'}
      pointerEvents="none"
    />
  );
};

const DetectionTimeline: React.FC<{
  detections: Detection[];
}> = ({ detections }) => {
  const getDetectionIcon = (type: string) => {
    switch (type) {
      case 'person':
        return '👤';
      case 'fire_or_vehicle':
        return '🔥';
      case 'aerial_object':
        return '🎈';
      case 'boat':
        return '⛵';
      case 'person_in_water':
        return '🏊';
      case 'movement':
        return '⚡';
      default:
        return '❓';
    }
  };

  const getDetectionColor = (type: string) => {
    switch (type) {
      case 'person':
        return '#3b82f6';
      case 'fire_or_vehicle':
        return '#ef4444';
      case 'aerial_object':
        return '#f59e0b';
      case 'boat':
        return '#06b6d4';
      case 'person_in_water':
        return '#8b5cf6';
      case 'movement':
        return '#ec4899';
      default:
        return '#6b7280';
    }
  };

  return (
    <div className="timeline-container">
      <h3>📊 Eventos Recentes</h3>
      <div className="timeline-list">
        {detections.length === 0 ? (
          <p className="text-gray-400">Nenhuma detecção no momento</p>
        ) : (
          detections.map((detection, idx) => (
            <div key={idx} className="timeline-item">
              <div className="timeline-header">
                <span className="camera-badge" style={{
                  backgroundColor: detection.detections.some(d => d.type === 'fire_or_vehicle' || d.type === 'aerial_object')
                    ? '#fee2e2'
                    : '#e0f2fe'
                }}>
                  {detection.camera_name}
                </span>
                <span className="timestamp">
                  {new Date(detection.timestamp).toLocaleTimeString('pt-BR')}
                </span>
              </div>
              <div className="detections-list">
                {detection.detections.map((det, detIdx) => (
                  <span
                    key={detIdx}
                    className="detection-badge"
                    style={{
                      backgroundColor: getDetectionColor(det.type),
                      color: 'white',
                    }}
                  >
                    {getDetectionIcon(det.type)} {det.type}
                    {det.confidence && ` (${det.confidence}%)`}
                  </span>
                ))}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

const StreamViewer: React.FC<{
  camera: Camera;
  onClose: () => void;
  onAngleChange: (delta: number) => void;
}> = ({ camera, onClose, onAngleChange }) => {
  const [snapshotUrl, setSnapshotUrl] = useState<string>('');
  const [error, setError] = useState(false);
  const [fps, setFps] = useState(0);
  const prevUrlRef = useRef<string>('');
  const frameCountRef = useRef(0);
  const lastFpsRef = useRef(Date.now());

  useEffect(() => {
    let active = true;

    const fetchSnapshot = async () => {
      try {
        const res = await fetch(`/api/cameras/${camera.id}/snapshot`);
        if (!res.ok) { if (active) setError(true); return; }
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        if (!active) { URL.revokeObjectURL(url); return; }
        setSnapshotUrl(url);
        setError(false);
        if (prevUrlRef.current) URL.revokeObjectURL(prevUrlRef.current);
        prevUrlRef.current = url;
        frameCountRef.current++;
        const now = Date.now();
        const elapsed = (now - lastFpsRef.current) / 1000;
        if (elapsed >= 2) {
          setFps(Math.round(frameCountRef.current / elapsed));
          frameCountRef.current = 0;
          lastFpsRef.current = now;
        }
      } catch {
        if (active) setError(true);
      }
    };

    fetchSnapshot();
    const interval = setInterval(fetchSnapshot, 1500);

    return () => {
      active = false;
      clearInterval(interval);
      if (prevUrlRef.current) { URL.revokeObjectURL(prevUrlRef.current); prevUrlRef.current = ''; }
    };
  }, [camera.id]);

  const statusColor = camera.status === 'online' ? '#22c55e' : '#f59e0b';

  return (
    <div className="sidebar-stream">
      {/* Cabeçalho */}
      <div className="sidebar-stream-header">
        <div className="modal-title">
          <span className="modal-status-dot" style={{ background: statusColor }} />
          <div>
            <h2>{camera.name}</h2>
            <span className="modal-meta">
              {camera.type === 'ptz' ? 'PTZ' : 'Fixa'}
              {camera.thermal ? ' · Térmica' : ''}
              {fps > 0 ? ` · ~${fps} fps` : ''}
            </span>
          </div>
        </div>
        <button className="close-btn" onClick={onClose}>×</button>
      </div>

      {/* Stream */}
      <div className="sidebar-stream-video">
        {error ? (
          <div className="stream-offline">
            <div style={{ fontSize: 36 }}>📵</div>
            <div>Câmera inacessível</div>
          </div>
        ) : snapshotUrl ? (
          <img src={snapshotUrl} alt="Stream câmera" className="stream-img" />
        ) : (
          <div className="stream-loading">
            <div className="spinner" />
            <div>Conectando...</div>
          </div>
        )}
      </div>

      {/* Controles PTZ */}
      {camera.type === 'ptz' && <PTZControls camera={camera} onAngleChange={onAngleChange} />}
    </div>
  );
};

const STEP_SIZES: [string, number][] = [['P', 120], ['M', 250], ['G', 500]];
const DEG_PER_MS = 5 / 250; // ~5° por 250ms

const PTZControls: React.FC<{ camera: Camera; onAngleChange: (d: number) => void }> =
  ({ camera, onAngleChange }) => {
  const [stepMs, setStepMs] = useState(250);
  const [feedback, setFeedback] = useState('');
  const [busy, setBusy] = useState(false);

  const sendCmd = async (pan: number, tilt: number, zoom: number, label: string) => {
    if (busy) return;
    setBusy(true);
    setFeedback(label);
    try {
      const res = await fetch(`/api/ptz/${camera.id}/command`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pan, tilt, zoom, duration_ms: stepMs }),
      });
      if (res.ok && pan !== 0 && zoom === 0) {
        onAngleChange(pan * stepMs * DEG_PER_MS);
      }
      if (!res.ok) setFeedback('Erro ✗');
      else setTimeout(() => setFeedback(''), 600);
    } catch {
      setFeedback('Erro ✗');
    } finally {
      setBusy(false);
    }
  };

  const presetGo = async (n: number) => {
    setFeedback(`▶ P${n}`);
    try {
      await fetch(`/api/ptz/${camera.id}/preset/${n}/go`, { method: 'POST' });
      setTimeout(() => setFeedback(''), 800);
    } catch { setFeedback('Erro ✗'); }
  };

  const presetSave = async (n: number) => {
    setFeedback(`💾 P${n}`);
    try {
      await fetch(`/api/ptz/${camera.id}/preset/${n}/save`, { method: 'POST' });
      setTimeout(() => setFeedback(''), 800);
    } catch { setFeedback('Erro ✗'); }
  };

  const B = (label: string, pan: number, tilt: number, zoom = 0, cls = '') => (
    <button key={label}
      className={`ptz-btn ${cls}${busy ? ' ptz-busy' : ''}`}
      disabled={busy}
      onClick={() => sendCmd(pan, tilt, zoom, label)}
    >{label}</button>
  );

  return (
    <div className="ptz-section">
      {/* Tamanho do passo */}
      <div className="ptz-row">
        <span className="ptz-label">Passo:</span>
        {STEP_SIZES.map(([lbl, ms]) => (
          <button key={ms}
            className={`ptz-step-btn${stepMs === ms ? ' active' : ''}`}
            onClick={() => setStepMs(ms)}
          >{lbl}</button>
        ))}
        {feedback && <span className="ptz-feedback">{feedback}</span>}
      </div>

      {/* Direcionais + Zoom */}
      <div className="ptz-controls-row">
        <div className="ptz-dir">
          {B('↖',-1,-1)}{B('▲',0,-1)}{B('↗',1,-1)}
          {B('◄',-1,0)}{B('■',0,0,0,'ptz-stop')}{B('►',1,0)}
          {B('↙',-1,1)}{B('▼',0,1)}{B('↘',1,1)}
        </div>
        <div className="ptz-zoom-col">
          {B('Z+',0,0,1,'ptz-zoom-btn')}
          {B('Z−',0,0,-1,'ptz-zoom-btn')}
        </div>
      </div>

      {/* Presets */}
      <div className="ptz-presets">
        <span className="ptz-label">Presets:</span>
        <div className="preset-grid">
          {[1,2,3,4,5,6].map(n => (
            <div key={n} className="preset-item">
              <button className="preset-go" onClick={() => presetGo(n)}>▶P{n}</button>
              <button className="preset-save" title={`Salvar como P${n}`} onClick={() => presetSave(n)}>💾</button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

// ============================================================================
// APLICAÇÃO PRINCIPAL
// ============================================================================

const App: React.FC = () => {
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [detections, setDetections] = useState<Detection[]>([]);
  const [selectedCamera, setSelectedCamera] = useState<string | null>(null);
  const [selectedAreas, setSelectedAreas] = useState<Camera[]>([]);
  const [showFOV, setShowFOV] = useState(false);
  const [loading, setLoading] = useState(true);
  const [angleDeltas, setAngleDeltas] = useState<Record<string, number>>({});
  const wsRef = useRef<WebSocket | null>(null);

  const getCameraAngle = (camera: Camera): number => {
    // Ângulo padrão: câmera aponta para o centro do mapa (400,300)
    const defAngle = Math.atan2(300 - camera.position.y, 400 - camera.position.x) * (180 / Math.PI);
    return defAngle + (angleDeltas[camera.id] ?? 0);
  };

  const updateAngleDelta = (camId: string, delta: number) => {
    setAngleDeltas(prev => ({ ...prev, [camId]: (prev[camId] ?? 0) + delta }));
  };

  // Carregar câmeras
  useEffect(() => {
    const fetchCameras = async () => {
      try {
        const response = await fetch('/api/cameras');
        const data = await response.json();
        setCameras(data.cameras);
        setLoading(false);
      } catch (error) {
        console.error('Erro ao carregar câmeras:', error);
        setLoading(false);
      }
    };

    fetchCameras();
  }, []);

  // WebSocket para eventos
  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/events`;

    wsRef.current = new WebSocket(wsUrl);

    wsRef.current.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.type === 'detection') {
        setDetections((prev) => [msg.data, ...prev].slice(0, 50));
      }
    };

    wsRef.current.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  const handleMapClick = (x: number, y: number) => {
    // Encontrar câmeras que enxergam essa área (baseado em FOV)
    const visibleCameras = cameras.filter((cam) => {
      const dx = x - cam.position.x;
      const dy = y - cam.position.y;
      const distance = Math.sqrt(dx * dx + dy * dy);
      const fovRadius = (cam.fov.horizontal / 180) * 150; // Escala visual
      return distance < fovRadius;
    });

    setSelectedAreas(visibleCameras);
  };

  if (loading) {
    return <div className="loading-screen">Carregando sistema...</div>;
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>🎥 Sistema de Vigilância Integrado</h1>
        <div className="status-bar">
          <span className="online-count">
            🟢 {cameras.filter((c) => c.status === 'online').length}/{cameras.length} câmeras online
          </span>
          <label className="toggle-fov">
            <input
              type="checkbox"
              checked={showFOV}
              onChange={(e) => setShowFOV(e.target.checked)}
            />
            Mostrar FOV
          </label>
        </div>
      </header>

      <div className="main-container">
        <div className="map-container">
          <svg className="map" onClick={(e) => {
            const rect = e.currentTarget.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            handleMapClick(x, y);
          }}>
            {/* Mapa de fundo (SVG tático) */}
            <rect x="0" y="0" width="800" height="600" fill="#0d1f0d" />
            {/* Grid */}
            {Array.from({ length: 17 }, (_, i) => (
              <line key={`vg${i}`} x1={i * 50} y1="0" x2={i * 50} y2="600"
                stroke="rgba(0,255,0,0.06)" strokeWidth="1" />
            ))}
            {Array.from({ length: 13 }, (_, i) => (
              <line key={`hg${i}`} x1="0" y1={i * 50} x2="800" y2={i * 50}
                stroke="rgba(0,255,0,0.06)" strokeWidth="1" />
            ))}
            {/* Zonas táticas */}
            <rect x="30" y="30" width="740" height="540" fill="none"
              stroke="rgba(0,255,0,0.15)" strokeWidth="2" strokeDasharray="10,5" />
            <ellipse cx="400" cy="300" rx="180" ry="130" fill="rgba(0,100,0,0.08)"
              stroke="rgba(0,200,0,0.12)" strokeWidth="1" strokeDasharray="8,4" />
            {/* Edifícios / estruturas */}
            <rect x="380" y="190" width="80" height="60" fill="rgba(100,120,100,0.3)"
              stroke="rgba(150,180,150,0.4)" strokeWidth="1.5" />
            <rect x="250" y="340" width="60" height="50" fill="rgba(100,120,100,0.3)"
              stroke="rgba(150,180,150,0.4)" strokeWidth="1.5" />
            <rect x="540" y="360" width="70" height="55" fill="rgba(100,120,100,0.3)"
              stroke="rgba(150,180,150,0.4)" strokeWidth="1.5" />
            {/* Estradas */}
            <line x1="0" y1="300" x2="800" y2="300" stroke="rgba(180,160,80,0.2)" strokeWidth="8" />
            <line x1="400" y1="0" x2="400" y2="600" stroke="rgba(180,160,80,0.2)" strokeWidth="8" />
            {/* Rótulos */}
            <text x="10" y="20" fontSize="10" fill="rgba(0,255,0,0.3)" fontFamily="monospace">ÁREA DE VIGILÂNCIA</text>
            <text x="690" y="595" fontSize="9" fill="rgba(0,255,0,0.2)" fontFamily="monospace">GRID 800×600</text>

            {/* FOV das câmeras */}
            {showFOV && cameras.map((camera) => (
              <CameraFOV key={camera.id} camera={camera}
                angle={getCameraAngle(camera)}
                isActive={selectedCamera === camera.id} />
            ))}

            {/* Ícones das câmeras */}
            {cameras.map((camera) => (
              <CameraIcon
                key={camera.id}
                camera={camera}
                isSelected={selectedCamera === camera.id}
                panAngle={getCameraAngle(camera)}
                onClick={() => setSelectedCamera(camera.id)}
              />
            ))}

            {/* Área selecionada (clique no mapa) */}
            {selectedAreas.length > 0 && (
              <g>
                <circle cx="0" cy="0" r="5" fill="#fbbf24" />
                {selectedAreas.map((camera) => (
                  <line
                    key={`line-${camera.id}`}
                    x1="0"
                    y1="0"
                    x2={camera.position.x}
                    y2={camera.position.y}
                    stroke="#fbbf24"
                    strokeWidth="1"
                    strokeDasharray="3,3"
                    pointerEvents="none"
                  />
                ))}
              </g>
            )}
          </svg>

          {/* Legenda */}
          <div className="legend">
            <h4>Legenda</h4>
            <div>🎥 PTZ | 📹 Fixa | 🌡️ Térmica</div>
            <div>🟢 Online | 🔴 Offline</div>
          </div>
        </div>

        <div className="sidebar">
          {selectedCamera ? (
            <StreamViewer
              camera={cameras.find((c) => c.id === selectedCamera)!}
              onClose={() => setSelectedCamera(null)}
              onAngleChange={(delta) => updateAngleDelta(selectedCamera, delta)}
            />
          ) : (
            <div className="instructions">
              <h3>ℹ️ Instruções</h3>
              <ul>
                <li>Clique em uma câmera para abrir o stream</li>
                <li>Clique no mapa para encontrar câmeras</li>
                <li>Ative "Mostrar FOV" para ver área de cobertura</li>
              </ul>
            </div>
          )}

          {!selectedCamera && <DetectionTimeline detections={selectedAreas.length > 0
            ? detections.filter((d) =>
              selectedAreas.some((cam) => cam.id === d.camera_id)
            )
            : detections.slice(0, 10)
          } />}
        </div>
      </div>
    </div>
  );
};

export default App;
