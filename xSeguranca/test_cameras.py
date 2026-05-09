#!/usr/bin/env python3
"""
Script de validação de câmeras
- Testa conectividade RTSP
- Verifica resolução e FPS
- Captura snapshots
- Valida detecção térmica
"""

import cv2
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
import subprocess
import time

# Configuração de câmeras (copiar de app.py)
CAMERAS_CONFIG = {
    "dome_1": {
        "ip": "192.168.0.198",
        "username": "admin",
        "password": "971001",
        "name": "Dome PTZ - Entrada",
        "type": "ptz",
        "thermal": False,
        "rtsp_port": 554,
    },
    "dome_2": {
        "ip": "192.168.0.199",
        "username": "admin",
        "password": "971001",
        "name": "Dome PTZ Térmica - Perímetro",
        "type": "ptz",
        "thermal": True,
        "rtsp_port": 554,
    },
}

def get_rtsp_url(camera_config):
    """Monta URL RTSP"""
    return f"rtsp://{camera_config['username']}:{camera_config['password']}@{camera_config['ip']}:{camera_config['rtsp_port']}/stream0"

def test_connectivity(camera_id, camera_config):
    """Testa conectividade básica com ping"""
    print(f"\n[{camera_id}] Testando conectividade...")
    try:
        result = subprocess.run(
            ["ping", "-c", "1", "-W", "2", camera_config['ip']],
            capture_output=True,
            timeout=5
        )
        if result.returncode == 0:
            print(f"  ✓ Ping OK")
            return True
        else:
            print(f"  ✗ Ping falhou")
            return False
    except Exception as e:
        print(f"  ✗ Erro: {e}")
        return False

def test_rtsp_stream(camera_id, camera_config, duration=5):
    """Conecta ao stream RTSP e coleta informações"""
    print(f"\n[{camera_id}] Testando stream RTSP...")
    
    rtsp_url = get_rtsp_url(camera_config)
    print(f"  URL: {rtsp_url}")
    
    try:
        cap = cv2.VideoCapture(rtsp_url)
        cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 10000)
        
        if not cap.isOpened():
            print(f"  ✗ Falha ao abrir stream")
            return False
        
        # Obter propriedades
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        codec = int(cap.get(cv2.CAP_PROP_FOURCC))
        
        print(f"  ✓ Stream aberto")
        print(f"    Resolução: {width}x{height}")
        print(f"    FPS: {fps}")
        print(f"    Codec: {codec}")
        
        # Capturar alguns frames
        print(f"  Capturando {duration} frames...")
        frame_count = 0
        success_count = 0
        start_time = time.time()
        
        while (time.time() - start_time) < duration:
            ret, frame = cap.read()
            frame_count += 1
            
            if ret:
                success_count += 1
            else:
                print(f"    ✗ Frame {frame_count} falhou")
            
            time.sleep(0.033)  # ~30 FPS
        
        success_rate = (success_count / frame_count) * 100 if frame_count > 0 else 0
        print(f"  ✓ Taxa de sucesso: {success_rate:.1f}% ({success_count}/{frame_count})")
        
        cap.release()
        return True
        
    except Exception as e:
        print(f"  ✗ Erro: {e}")
        return False

def capture_snapshot(camera_id, camera_config, output_dir="snapshots"):
    """Captura e salva um snapshot"""
    print(f"\n[{camera_id}] Capturando snapshot...")
    
    rtsp_url = get_rtsp_url(camera_config)
    
    try:
        cap = cv2.VideoCapture(rtsp_url)
        cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 10000)
        
        if not cap.isOpened():
            print(f"  ✗ Falha ao abrir stream")
            return False
        
        ret, frame = cap.read()
        cap.release()
        
        if not ret:
            print(f"  ✗ Falha ao capturar frame")
            return False
        
        # Salvar snapshot
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        filename = output_path / f"{camera_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        cv2.imwrite(str(filename), frame)
        
        print(f"  ✓ Snapshot salvo: {filename}")
        return True
        
    except Exception as e:
        print(f"  ✗ Erro: {e}")
        return False

def analyze_thermal(camera_id, camera_config):
    """Analisa qualidade da imagem térmica"""
    if not camera_config.get('thermal'):
        print(f"\n[{camera_id}] Não é câmera térmica, pulando análise")
        return True
    
    print(f"\n[{camera_id}] Analisando imagem térmica...")
    
    rtsp_url = get_rtsp_url(camera_config)
    
    try:
        cap = cv2.VideoCapture(rtsp_url)
        cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 10000)
        
        if not cap.isOpened():
            print(f"  ✗ Falha ao abrir stream")
            return False
        
        # Capturar um frame
        ret, frame = cap.read()
        cap.release()
        
        if not ret:
            print(f"  ✗ Falha ao capturar frame")
            return False
        
        # Análises básicas
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Verificar variação (entropia)
        mean = gray.mean()
        std = gray.std()
        
        print(f"  Média de intensidade: {mean:.1f}")
        print(f"  Desvio padrão: {std:.1f}")
        
        if std < 5:
            print(f"  ⚠️  Imagem muito uniforme (possível problema de calibração)")
        else:
            print(f"  ✓ Distribuição de intensidade OK")
        
        # Detectar regiões quentes
        _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
        hot_pixels = cv2.countNonZero(thresh)
        hot_percent = (hot_pixels / thresh.size) * 100
        
        print(f"  Pixels quentes: {hot_percent:.1f}%")
        
        if hot_percent < 1:
            print(f"  ⚠️  Poucos pixels quentes (pode não estar detectando bem)")
        elif hot_percent > 50:
            print(f"  ⚠️  Muitos pixels quentes (possível saturação)")
        else:
            print(f"  ✓ Nível de detecção aparenta OK")
        
        return True
        
    except Exception as e:
        print(f"  ✗ Erro: {e}")
        return False

def test_onvif(camera_id, camera_config):
    """Testa ONVIF (futuro: controle PTZ)"""
    if camera_config['type'] != 'ptz':
        print(f"\n[{camera_id}] Não é câmera PTZ, pulando ONVIF")
        return True
    
    print(f"\n[{camera_id}] Testando ONVIF...")
    
    try:
        from onvif import ONVIFCamera
        
        camera = ONVIFCamera(
            camera_config['ip'],
            80,  # Porta ONVIF padrão
            camera_config['username'],
            camera_config['password']
        )
        
        # Obter capabilities
        capabilities = camera.GetCapabilities()
        print(f"  ✓ ONVIF conectado")
        print(f"    Capabilities: {capabilities}")
        return True
        
    except ImportError:
        print(f"  ⚠️  python-onvif não instalado (pip install python-onvif)")
        return False
    except Exception as e:
        print(f"  ✗ Erro ONVIF: {e}")
        return False

def generate_report(results):
    """Gera relatório de teste"""
    print("\n" + "="*60)
    print("RELATÓRIO DE TESTE")
    print("="*60)
    
    print(f"\nData/Hora: {datetime.now().isoformat()}")
    print(f"\nCâmeras testadas: {len(results)}")
    
    passed = sum(1 for r in results.values() if r['status'] == 'OK')
    print(f"✓ Passou: {passed}/{len(results)}")
    
    print("\nDetalhes:\n")
    for camera_id, result in results.items():
        status_icon = "✓" if result['status'] == 'OK' else "✗"
        print(f"{status_icon} {camera_id}: {result['status']}")
        for test, passed in result['tests'].items():
            test_icon = "✓" if passed else "✗"
            print(f"  {test_icon} {test}")

def main():
    parser = argparse.ArgumentParser(description='Validar câmeras IP')
    parser.add_argument('--camera', help='Testar apenas uma câmera (ID)')
    parser.add_argument('--snapshot', action='store_true', help='Capturar snapshots')
    parser.add_argument('--all', action='store_true', help='Todos os testes')
    
    args = parser.parse_args()
    
    cameras_to_test = {}
    if args.camera:
        if args.camera in CAMERAS_CONFIG:
            cameras_to_test = {args.camera: CAMERAS_CONFIG[args.camera]}
        else:
            print(f"Câmera '{args.camera}' não encontrada")
            sys.exit(1)
    else:
        cameras_to_test = CAMERAS_CONFIG
    
    results = {}
    
    for camera_id, camera_config in cameras_to_test.items():
        results[camera_id] = {
            'status': 'OK',
            'tests': {}
        }
        
        # Teste 1: Conectividade
        ping_ok = test_connectivity(camera_id, camera_config)
        results[camera_id]['tests']['Conectividade'] = ping_ok
        
        if not ping_ok:
            results[camera_id]['status'] = 'FALHA'
            continue
        
        # Teste 2: RTSP
        rtsp_ok = test_rtsp_stream(camera_id, camera_config)
        results[camera_id]['tests']['Stream RTSP'] = rtsp_ok
        
        if not rtsp_ok:
            results[camera_id]['status'] = 'FALHA'
            continue
        
        # Teste 3: Snapshot (opcional)
        if args.snapshot or args.all:
            snapshot_ok = capture_snapshot(camera_id, camera_config)
            results[camera_id]['tests']['Snapshot'] = snapshot_ok
        
        # Teste 4: Análise Térmica (se aplicável)
        if camera_config.get('thermal') or args.all:
            thermal_ok = analyze_thermal(camera_id, camera_config)
            results[camera_id]['tests']['Imagem Térmica'] = thermal_ok
        
        # Teste 5: ONVIF (se aplicável)
        if camera_config['type'] == 'ptz' or args.all:
            onvif_ok = test_onvif(camera_id, camera_config)
            results[camera_id]['tests']['ONVIF'] = onvif_ok
    
    # Gerar relatório
    generate_report(results)
    
    # Retornar código de saída
    all_passed = all(r['status'] == 'OK' for r in results.values())
    sys.exit(0 if all_passed else 1)

if __name__ == '__main__':
    main()
