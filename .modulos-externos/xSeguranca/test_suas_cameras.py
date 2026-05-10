#!/usr/bin/env python3
"""
Script de teste prático para 2 câmeras PTZ Hikvision
- Conecta e captura frames
- Mostra resolução e FPS
- Salva snapshots
- Testa detecção térmica se aplicável
"""

import cv2
import sys
import time
from pathlib import Path

# Suas 2 câmeras
CAMERAS = {
    "dome_1": {
        "ip": "192.168.0.198",
        "username": "admin",
        "password": "971001",
        "name": "Dome 1 - Entrada",
        "thermal": False,
    },
    "dome_2": {
        "ip": "192.168.0.199",
        "username": "admin",
        "password": "971001",
        "name": "Dome 2 - Perímetro (Térmica)",
        "thermal": True,
    },
}

def get_rtsp_url(cam_config):
    """Monta URL RTSP para Hikvision"""
    return f"rtsp://{cam_config['username']}:{cam_config['password']}@{cam_config['ip']}:554/stream0"

def test_camera(camera_id, camera_config):
    """Testa uma câmera: conecta, captura e analisa"""
    
    print(f"\n{'='*60}")
    print(f"🎥 Testando: {camera_config['name']}")
    print(f"{'='*60}")
    
    rtsp_url = get_rtsp_url(camera_config)
    print(f"📡 URL: {rtsp_url}")
    
    try:
        # 1. Conectar
        print(f"\n1️⃣  Conectando ao stream RTSP...", end=" ", flush=True)
        cap = cv2.VideoCapture(rtsp_url)
        cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 10000)
        
        if not cap.isOpened():
            print("❌ FALHA")
            return False
        
        print("✅ Conectado")
        
        # 2. Obter propriedades
        print(f"\n2️⃣  Obtendo propriedades do stream:")
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        print(f"   • Resolução: {width}x{height}")
        print(f"   • FPS: {fps}")
        
        # 3. Capturar frames e medir performance
        print(f"\n3️⃣  Capturando e analisando 30 frames...", end=" ", flush=True)
        
        frames = []
        start_time = time.time()
        frame_count = 0
        success_count = 0
        
        while frame_count < 30 and (time.time() - start_time) < 10:
            ret, frame = cap.read()
            frame_count += 1
            
            if ret:
                success_count += 1
                frames.append(frame)
            
            # Barra de progresso simples
            if frame_count % 10 == 0:
                print(".", end="", flush=True)
        
        elapsed = time.time() - start_time
        success_rate = (success_count / frame_count) * 100
        actual_fps = frame_count / elapsed
        
        print(f" ✅")
        print(f"   • Taxa de sucesso: {success_rate:.1f}% ({success_count}/{frame_count} frames)")
        print(f"   • FPS real (medido): {actual_fps:.1f}")
        
        # 4. Salvar snapshot
        print(f"\n4️⃣  Salvando snapshot...", end=" ", flush=True)
        
        if frames:
            snapshot_dir = Path("snapshots")
            snapshot_dir.mkdir(exist_ok=True)
            
            snapshot_path = snapshot_dir / f"{camera_id}_latest.jpg"
            cv2.imwrite(str(snapshot_path), frames[-1])
            print(f"✅ {snapshot_path}")
        else:
            print("❌ Nenhum frame capturado")
            return False
        
        # 5. Análise térmica (se aplicável)
        if camera_config["thermal"]:
            print(f"\n5️⃣  Analisando imagem térmica...")
            
            latest_frame = frames[-1]
            gray = cv2.cvtColor(latest_frame, cv2.COLOR_BGR2GRAY)
            
            # Distribuição de pixels
            mean = gray.mean()
            std = gray.std()
            min_val = gray.min()
            max_val = gray.max()
            
            print(f"   • Média de intensidade: {mean:.1f}")
            print(f"   • Desvio padrão: {std:.1f}")
            print(f"   • Min-Max: {min_val}-{max_val}")
            
            # Detectar regiões quentes (threshold simples)
            _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
            hot_pixels = cv2.countNonZero(thresh)
            hot_percent = (hot_pixels / thresh.size) * 100
            
            print(f"   • Pixels quentes (>150): {hot_percent:.1f}%")
            
            if std < 5:
                print(f"   ⚠️  Imagem muito uniforme (possível calibração)")
            else:
                print(f"   ✅ Distribuição térmica aparenta OK")
        else:
            print(f"\n5️⃣  Câmera RGB (não térmica)")
            
            latest_frame = frames[-1]
            gray = cv2.cvtColor(latest_frame, cv2.COLOR_BGR2GRAY)
            mean = gray.mean()
            std = gray.std()
            
            print(f"   • Média de brilho: {mean:.1f}")
            print(f"   • Variação: {std:.1f}")
            
            if std < 10:
                print(f"   ⚠️  Imagem muito uniforme (possível foco ruim)")
            else:
                print(f"   ✅ Qualidade aparenta OK")
        
        # Limpar
        cap.release()
        
        print(f"\n✅ TESTE PASSOU: {camera_config['name']}")
        return True
        
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        return False

def main():
    """Executa testes de ambas as câmeras"""
    
    print("\n" + "="*60)
    print("🎬 TESTE DE CÂMERAS PTZ HIKVISION")
    print("="*60)
    
    results = {}
    
    for camera_id, camera_config in CAMERAS.items():
        try:
            success = test_camera(camera_id, camera_config)
            results[camera_id] = "✅ PASSOU" if success else "❌ FALHOU"
        except KeyboardInterrupt:
            print("\n\n⚠️  Teste interrompido pelo usuário")
            break
        except Exception as e:
            print(f"\n❌ Erro inesperado: {e}")
            results[camera_id] = "❌ ERRO"
    
    # Relatório final
    print("\n" + "="*60)
    print("📊 RELATÓRIO FINAL")
    print("="*60)
    
    for camera_id, status in results.items():
        print(f"{status} {CAMERAS[camera_id]['name']}")
    
    passed = sum(1 for s in results.values() if "✅" in s)
    total = len(results)
    
    print(f"\nResultado: {passed}/{total} câmeras passaram ✅")
    
    if passed == total:
        print("\n🎉 Tudo OK! Próximo passo: rodar docker-compose up -d")
    else:
        print("\n⚠️  Verifique conectividade e credenciais")
    
    print("\n📂 Snapshots salvos em: ./snapshots/")
    print("="*60)

if __name__ == "__main__":
    main()
