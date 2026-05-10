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
  onClick: () => void;
}> = ({ camera, isSelected, onClick }) => {
  const iconColor = camera.status === 'online' ? '#22c55e' : '#ef4444';
  const iconType = camera.thermal ? '🌡️' : camera.type === 'ptz' ? '🎥' : '📹';

  return (
    <g
      onClick={onClick}
      style={{ cursor: 'pointer' }}
      transform={`translate(${camera.position.x}, ${camera.position.y})`}
    >
      {/* Circlebase */}
      <circle
        r="20"
        fill={iconColor}
        opacity={isSelected ? 0.8 : 0.5}
        style={{ transition: 'opacity 0.2s' }}
      />
      {/* Ícone */}
      <text
        fontSize="16"
        textAnchor="middle"
        dominantBaseline="middle"
        fill="white"
      >
        {iconType}
      </text>
      {/* Rótulo */}
      <text
        y="30"
        fontSize="11"
        textAnchor="middle"
        fill="white"
        style={{
          textShadow: '0 0 3px black',
          pointerEvents: 'none',
        }}
      >
        {camera.name.split(' ').pop()}
      </text>
    </g>
  );
};

const CameraFOV: React.FC<{ camera: Camera }> = ({ camera }) => {
  // Desenhar cone de visão (FOV) em torno da câmera
  const { horizontal, vertical } = camera.fov;
  const width = (horizontal / 180) * 200; // Escala visual
  const height = (vertical / 180) * 200;

  return (
    <ellipse
      cx={camera.position.x}
      cy={camera.position.y}
      rx={width}
      ry={height}
      fill="rgba(100, 150, 255, 0.05)"
      stroke="rgba(100, 150, 255, 0.2)"
      strokeWidth="1"
      strokeDasharray="5,5"
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
  isOpen: boolean;
  onClose: () => void;
}> = ({ camera, isOpen, onClose }) => {
  const [snapshot, setSnapshot] = useState<string>('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!isOpen) return;

    setLoading(true);
    const fetchSnapshot = async () => {
      try {
        const response = await fetch(`/api/cameras/${camera.id}/snapshot`);
        if (response.ok) {
          const blob = await response.blob();
          const url = URL.createObjectURL(blob);
          setSnapshot(url);
        }
      } catch (error) {
        console.error('Erro ao carregar snapshot:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchSnapshot();
    const interval = setInterval(fetchSnapshot, 2000); // Atualizar a cada 2s

    return () => clearInterval(interval);
  }, [isOpen, camera.id]);

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>{camera.name}</h2>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>
        <div className="stream-container">
          {loading ? (
            <div className="loading">Carregando...</div>
          ) : snapshot ? (
            <img src={snapshot} alt="Câmera" style={{ maxWidth: '100%' }} />
          ) : (
            <div className="offline">Câmera offline</div>
          )}
        </div>
        {camera.type === 'ptz' && (
          <PTZControls camera={camera} />
        )}
      </div>
    </div>
  );
};

const PTZControls: React.FC<{ camera: Camera }> = ({ camera }) => {
  const handleCommand = async (pan: number, tilt: number, zoom: number) => {
    try {
      await fetch(`/api/ptz/${camera.id}/command`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pan, tilt, zoom, speed: 5 }),
      });
    } catch (error) {
      console.error('Erro ao enviar comando PTZ:', error);
    }
  };

  return (
    <div className="ptz-controls">
      <div className="ptz-grid">
        <button onClick={() => handleCommand(0, -1, 0)}>⬆️</button>
        <button onClick={() => handleCommand(0, 0, 1)}>🔍+</button>
        <button onClick={() => handleCommand(-1, 0, 0)}>⬅️</button>
        <button onClick={() => handleCommand(0, 0, 0)}>⏹️</button>
        <button onClick={() => handleCommand(1, 0, 0)}>➡️</button>
        <button onClick={() => handleCommand(0, 0, -1)}>🔍-</button>
        <button onClick={() => handleCommand(0, 1, 0)}>⬇️</button>
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
  const wsRef = useRef<WebSocket | null>(null);

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
            {/* Imagem do mapa de fundo */}
            <image
              href="/map.png"
              x="0"
              y="0"
              width="800"
              height="600"
              style={{ pointerEvents: 'none' }}
            />

            {/* FOV das câmeras */}
            {showFOV && cameras.map((camera) => (
              <CameraFOV key={camera.id} camera={camera} />
            ))}

            {/* Ícones das câmeras */}
            {cameras.map((camera) => (
              <CameraIcon
                key={camera.id}
                camera={camera}
                isSelected={selectedCamera === camera.id}
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
            <div className="camera-details">
              <h3>{cameras.find((c) => c.id === selectedCamera)?.name}</h3>
              <button
                className="btn-primary"
                onClick={() => {}}
              >
                📺 Abrir Stream
              </button>
              <button
                className="btn-secondary"
                onClick={() => setSelectedCamera(null)}
              >
                Fechar
              </button>
            </div>
          ) : (
            <div className="instructions">
              <h3>ℹ️ Instruções</h3>
              <ul>
                <li>Clique em uma câmera para ver detalhes</li>
                <li>Clique no mapa para encontrar câmeras</li>
                <li>Ative "Mostrar FOV" para ver área de cobertura</li>
              </ul>
            </div>
          )}

          <DetectionTimeline detections={selectedAreas.length > 0
            ? detections.filter((d) =>
              selectedAreas.some((cam) => cam.id === d.camera_id)
            )
            : detections.slice(0, 10)
          } />
        </div>
      </div>

      {selectedCamera && (
        <StreamViewer
          camera={cameras.find((c) => c.id === selectedCamera)!}
          isOpen={!!selectedCamera}
          onClose={() => setSelectedCamera(null)}
        />
      )}
    </div>
  );
};

export default App;
