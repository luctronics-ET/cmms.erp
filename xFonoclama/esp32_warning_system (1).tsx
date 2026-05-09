import React, { useState } from 'react';
import { Mic, Speaker, Wifi, Radio, Server, Smartphone, AlertCircle, Volume2, Bell } from 'lucide-react';

const ESP32WarningSystem = () => {
  const [activeTab, setActiveTab] = useState('arquitetura');

  const TabButton = ({ id, label, icon: Icon }) => (
    <button
      onClick={() => setActiveTab(id)}
      className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
        activeTab === id
          ? 'bg-blue-600 text-white'
          : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
      }`}
    >
      <Icon size={18} />
      {label}
    </button>
  );

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-6">
      <div className="max-w-6xl mx-auto">
        <div className="bg-white rounded-2xl shadow-xl p-8">
          <div className="flex items-center gap-3 mb-6">
            <Radio className="text-blue-600" size={40} />
            <div>
              <h1 className="text-3xl font-bold text-gray-800">
                Sistema de Avisos Wireless ESP32
              </h1>
              <p className="text-gray-600">Comunicação de áudio em tempo real via ESP-NOW/WiFi</p>
            </div>
          </div>

          <div className="flex flex-wrap gap-2 mb-6">
            <TabButton id="arquitetura" label="Arquitetura" icon={Wifi} />
            <TabButton id="hardware" label="Hardware" icon={Speaker} />
            <TabButton id="master" label="Node Master" icon={Mic} />
            <TabButton id="slave" label="Node Slave" icon={Volume2} />
            <TabButton id="servidor" label="Servidor" icon={Server} />
            <TabButton id="webapp" label="Web/App" icon={Smartphone} />
            <TabButton id="melhorias" label="Melhorias" icon={AlertCircle} />
          </div>

          <div className="bg-gray-50 rounded-xl p-6">
            {activeTab === 'arquitetura' && (
              <div className="space-y-6">
                <h2 className="text-2xl font-bold text-gray-800 flex items-center gap-2">
                  <Wifi className="text-blue-600" />
                  Arquitetura do Sistema
                </h2>
                
                <div className="bg-white rounded-lg p-6 border-2 border-blue-200">
                  <h3 className="font-bold text-lg mb-4 text-blue-800">Topologia de Rede</h3>
                  <div className="grid md:grid-cols-3 gap-4">
                    <div className="bg-green-50 p-4 rounded-lg border-2 border-green-300">
                      <h4 className="font-bold text-green-800 mb-2">Node Master</h4>
                      <ul className="text-sm space-y-1 text-gray-700">
                        <li>• Microfone INMP441</li>
                        <li>• 2 entradas de áudio</li>
                        <li>• Botão PTT</li>
                        <li>• Display OLED</li>
                        <li>• LEDs indicadores</li>
                      </ul>
                    </div>
                    <div className="bg-yellow-50 p-4 rounded-lg border-2 border-yellow-300">
                      <h4 className="font-bold text-yellow-800 mb-2">Servidor Local</h4>
                      <ul className="text-sm space-y-1 text-gray-700">
                        <li>• ESP32 ou Raspberry Pi</li>
                        <li>• Armazena mensagens</li>
                        <li>• WebSocket server</li>
                        <li>• Interface web</li>
                        <li>• MQTT broker</li>
                      </ul>
                    </div>
                    <div className="bg-purple-50 p-4 rounded-lg border-2 border-purple-300">
                      <h4 className="font-bold text-purple-800 mb-2">Nodes Slave (1-N)</h4>
                      <ul className="text-sm space-y-1 text-gray-700">
                        <li>• Speaker MAX98357A</li>
                        <li>• Sirene piezo</li>
                        <li>• LEDs e display</li>
                        <li>• Botões controle</li>
                        <li>• Recebe broadcasts</li>
                      </ul>
                    </div>
                  </div>
                </div>

                <div className="bg-blue-50 p-5 rounded-lg border-l-4 border-blue-600">
                  <h3 className="font-bold text-blue-900 mb-3">Protocolos de Comunicação</h3>
                  <div className="space-y-2 text-sm">
                    <div className="flex items-start gap-2">
                      <span className="bg-blue-600 text-white px-2 py-1 rounded font-mono text-xs">ESP-NOW</span>
                      <p className="text-gray-700">Para transmissão de áudio tempo real (baixa latência, ~10ms)</p>
                    </div>
                    <div className="flex items-start gap-2">
                      <span className="bg-green-600 text-white px-2 py-1 rounded font-mono text-xs">MQTT</span>
                      <p className="text-gray-700">Para comandos de controle e mensagens gravadas</p>
                    </div>
                    <div className="flex items-start gap-2">
                      <span className="bg-purple-600 text-white px-2 py-1 rounded font-mono text-xs">HTTP/WS</span>
                      <p className="text-gray-700">Para interface web e upload de áudios</p>
                    </div>
                  </div>
                </div>

                <div className="bg-orange-50 p-5 rounded-lg border-l-4 border-orange-500">
                  <h3 className="font-bold text-orange-900 mb-3">Fluxo de Áudio</h3>
                  <ol className="space-y-2 text-sm text-gray-700">
                    <li><strong>1. Captura:</strong> Microfone I2S → ADC 16-bit @ 16kHz</li>
                    <li><strong>2. Codificação:</strong> Opus codec ou G.711 para compressão</li>
                    <li><strong>3. Pacotes:</strong> 250 bytes por pacote (20-40ms áudio)</li>
                    <li><strong>4. Transmissão:</strong> ESP-NOW broadcast para todos slaves</li>
                    <li><strong>5. Buffer:</strong> Ring buffer de 4KB nos receptores</li>
                    <li><strong>6. Reprodução:</strong> DAC I2S → Amplificador → Speaker</li>
                  </ol>
                </div>
              </div>
            )}

            {activeTab === 'hardware' && (
              <div className="space-y-6">
                <h2 className="text-2xl font-bold text-gray-800">Lista de Componentes</h2>
                
                <div className="grid md:grid-cols-2 gap-6">
                  <div className="bg-white rounded-lg p-5 border-2 border-gray-200">
                    <h3 className="font-bold text-lg mb-4 text-gray-800 flex items-center gap-2">
                      <Mic className="text-green-600" />
                      Node Master
                    </h3>
                    <table className="w-full text-sm">
                      <thead className="bg-gray-100">
                        <tr>
                          <th className="p-2 text-left">Componente</th>
                          <th className="p-2 text-left">Modelo</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y">
                        <tr><td className="p-2">Microcontrolador</td><td className="p-2 font-mono">ESP32-WROOM-32</td></tr>
                        <tr><td className="p-2">Microfone I2S</td><td className="p-2 font-mono">INMP441</td></tr>
                        <tr><td className="p-2">Entradas Áudio</td><td className="p-2 font-mono">2x Jack 3.5mm</td></tr>
                        <tr><td className="p-2">ADC Áudio</td><td className="p-2 font-mono">PCM1808 (estéreo)</td></tr>
                        <tr><td className="p-2">Display</td><td className="p-2 font-mono">OLED 128x64 I2C</td></tr>
                        <tr><td className="p-2">Botão PTT</td><td className="p-2 font-mono">Push button + LED</td></tr>
                        <tr><td className="p-2">LEDs Status</td><td className="p-2 font-mono">3x RGB (WS2812B)</td></tr>
                        <tr><td className="p-2">Alimentação</td><td className="p-2 font-mono">5V 2A ou bateria</td></tr>
                      </tbody>
                    </table>
                  </div>

                  <div className="bg-white rounded-lg p-5 border-2 border-gray-200">
                    <h3 className="font-bold text-lg mb-4 text-gray-800 flex items-center gap-2">
                      <Speaker className="text-purple-600" />
                      Node Slave
                    </h3>
                    <table className="w-full text-sm">
                      <thead className="bg-gray-100">
                        <tr>
                          <th className="p-2 text-left">Componente</th>
                          <th className="p-2 text-left">Modelo</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y">
                        <tr><td className="p-2">Microcontrolador</td><td className="p-2 font-mono">ESP32-WROOM-32</td></tr>
                        <tr><td className="p-2">Amplificador I2S</td><td className="p-2 font-mono">MAX98357A</td></tr>
                        <tr><td className="p-2">Speaker</td><td className="p-2 font-mono">3W 4Ω ou 8Ω</td></tr>
                        <tr><td className="p-2">Sirene</td><td className="p-2 font-mono">Buzzer piezo</td></tr>
                        <tr><td className="p-2">Display</td><td className="p-2 font-mono">OLED 128x64 I2C</td></tr>
                        <tr><td className="p-2">Botões</td><td className="p-2 font-mono">3x push button</td></tr>
                        <tr><td className="p-2">LEDs Status</td><td className="p-2 font-mono">3x RGB (WS2812B)</td></tr>
                        <tr><td className="p-2">Alimentação</td><td className="p-2 font-mono">5V 2A</td></tr>
                      </tbody>
                    </table>
                  </div>
                </div>

                <div className="bg-indigo-50 p-5 rounded-lg">
                  <h3 className="font-bold text-indigo-900 mb-3">Pinout ESP32 - Master</h3>
                  <div className="grid md:grid-cols-2 gap-4 text-sm font-mono">
                    <div className="space-y-1">
                      <p><span className="bg-green-600 text-white px-2 py-1 rounded">GPIO25</span> I2S BCLK (mic)</p>
                      <p><span className="bg-green-600 text-white px-2 py-1 rounded">GPIO26</span> I2S WS (mic)</p>
                      <p><span className="bg-green-600 text-white px-2 py-1 rounded">GPIO27</span> I2S SD (mic)</p>
                      <p><span className="bg-blue-600 text-white px-2 py-1 rounded">GPIO21</span> I2C SDA (display)</p>
                      <p><span className="bg-blue-600 text-white px-2 py-1 rounded">GPIO22</span> I2C SCL (display)</p>
                    </div>
                    <div className="space-y-1">
                      <p><span className="bg-purple-600 text-white px-2 py-1 rounded">GPIO32</span> Botão PTT</p>
                      <p><span className="bg-purple-600 text-white px-2 py-1 rounded">GPIO33</span> LED RGB Data</p>
                      <p><span className="bg-orange-600 text-white px-2 py-1 rounded">GPIO34</span> Entrada Áudio L</p>
                      <p><span className="bg-orange-600 text-white px-2 py-1 rounded">GPIO35</span> Entrada Áudio R</p>
                    </div>
                  </div>
                </div>

                <div className="bg-indigo-50 p-5 rounded-lg">
                  <h3 className="font-bold text-indigo-900 mb-3">Pinout ESP32 - Slave</h3>
                  <div className="grid md:grid-cols-2 gap-4 text-sm font-mono">
                    <div className="space-y-1">
                      <p><span className="bg-green-600 text-white px-2 py-1 rounded">GPIO25</span> I2S BCLK (speaker)</p>
                      <p><span className="bg-green-600 text-white px-2 py-1 rounded">GPIO26</span> I2S LRCK (speaker)</p>
                      <p><span className="bg-green-600 text-white px-2 py-1 rounded">GPIO27</span> I2S DIN (speaker)</p>
                      <p><span className="bg-blue-600 text-white px-2 py-1 rounded">GPIO21</span> I2C SDA (display)</p>
                      <p><span className="bg-blue-600 text-white px-2 py-1 rounded">GPIO22</span> I2C SCL (display)</p>
                    </div>
                    <div className="space-y-1">
                      <p><span className="bg-purple-600 text-white px-2 py-1 rounded">GPIO32</span> Botão 1</p>
                      <p><span className="bg-purple-600 text-white px-2 py-1 rounded">GPIO33</span> Botão 2</p>
                      <p><span className="bg-purple-600 text-white px-2 py-1 rounded">GPIO14</span> LED RGB Data</p>
                      <p><span className="bg-red-600 text-white px-2 py-1 rounded">GPIO13</span> Sirene PWM</p>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'master' && (
              <div className="space-y-6">
                <h2 className="text-2xl font-bold text-gray-800">Código Node Master (Transmissor)</h2>
                
                <div className="bg-gray-900 text-green-400 p-4 rounded-lg overflow-x-auto text-xs">
                  <pre>{`// Código completo disponível para download
// Este é um exemplo simplificado da estrutura

#include <esp_now.h>
#include <WiFi.h>
#include <driver/i2s.h>

#define I2S_WS 26
#define I2S_SD 27
#define I2S_SCK 25
#define BTN_PTT 32

typedef struct audio_packet {
  uint32_t timestamp;
  uint16_t sequence;
  uint16_t dataSize;
  uint8_t audioData[240];
} audio_packet;

void setup() {
  Serial.begin(115200);
  setupI2S();
  setupESPNow();
}

void loop() {
  if (isPTTPressed()) {
    captureAndTransmitAudio();
  }
}`}</pre>
                </div>

                <div className="bg-yellow-50 p-4 rounded-lg">
                  <h3 className="font-bold mb-2">Características Master</h3>
                  <ul className="space-y-1 text-sm">
                    <li>• Captura 16kHz 16-bit via I2S</li>
                    <li>• Broadcast ESP-NOW</li>
                    <li>• PTT para transmissão</li>
                    <li>• Display mostra status</li>
                  </ul>
                </div>
              </div>
            )}

            {activeTab === 'slave' && (
              <div className="space-y-6">
                <h2 className="text-2xl font-bold text-gray-800">Código Node Slave (Receptor)</h2>
                
                <div className="bg-gray-900 text-green-400 p-4 rounded-lg overflow-x-auto text-xs">
                  <pre>{`// Código completo disponível para download
// Este é um exemplo simplificado da estrutura

#include <esp_now.h>
#include <WiFi.h>
#include <driver/i2s.h>

#define RING_BUFFER_SIZE 8192
uint8_t ringBuffer[RING_BUFFER_SIZE];

void onDataReceive(const uint8_t *mac, 
                   const uint8_t *data, int len) {
  // Adiciona ao ring buffer
  // Reproduz via I2S
}

void setup() {
  Serial.begin(115200);
  setupI2S();
  setupESPNow();
  esp_now_register_recv_cb(onDataReceive);
}

void loop() {
  playAudioFromBuffer();
}`}</pre>
                </div>

                <div className="bg-green-50 p-4 rounded-lg">
                  <h3 className="font-bold mb-2">Características Slave</h3>
                  <ul className="space-y-1 text-sm">
                    <li>• Ring buffer 8KB</li>
                    <li>• Reprodução I2S</li>
                    <li>• Timeout automático</li>
                    <li>• Sirene integrada</li>
                  </ul>
                </div>
              </div>
            )}

            {activeTab === 'servidor' && (
              <div className="space-y-6">
                <h2 className="text-2xl font-bold text-gray-800">Servidor Local</h2>
                
                <div className="bg-white rounded-lg p-5 border-2 border-blue-200">
                  <h3 className="font-bold mb-3">Node.js + MQTT</h3>
                  <div className="bg-gray-900 text-green-400 p-4 rounded-lg text-xs">
                    <pre>{`const express = require('express');
const mqtt = require('mqtt');
const app = express();
const client = mqtt.connect('mqtt://localhost');

app.get('/play/:file', (req, res) => {
  client.publish('audio/play', req.params.file);
  res.json({ success: true });
});

app.listen(3000);`}</pre>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'webapp' && (
              <div className="space-y-6">
                <h2 className="text-2xl font-bold text-gray-800">Interface Web</h2>
                
                <div className="bg-white rounded-lg p-5 border-2 border-indigo-200">
                  <h3 className="font-bold mb-3">PWA com MediaRecorder API</h3>
                  <div className="bg-gray-900 text-green-400 p-4 rounded-lg text-xs">
                    <pre>{`let mediaRecorder;
const ws = new WebSocket('ws://192.168.1.100:8080');

async function startRecording() {
  const stream = await navigator.mediaDevices
    .getUserMedia({ audio: true });
  mediaRecorder = new MediaRecorder(stream);
  mediaRecorder.ondataavailable = (e) => {
    ws.send(e.data);
  };
  mediaRecorder.start(100);
}`}</pre>
                  </div>
                </div>

                <div className="bg-blue-50 p-4 rounded-lg">
                  <h3 className="font-bold mb-2">Recursos PWA</h3>
                  <ul className="space-y-1 text-sm">
                    <li>• Funciona em qualquer dispositivo</li>
                    <li>• Não precisa instalar app</li>
                    <li>• Transmissão ao vivo</li>
                    <li>• Upload de mensagens</li>
                  </ul>
                </div>
              </div>
            )}

            {activeTab === 'melhorias' && (
              <div className="space-y-6">
                <h2 className="text-2xl font-bold text-gray-800">Melhorias Recomendadas</h2>

                <div className="bg-gradient-to-r from-green-50 to-green-100 rounded-lg p-6 border-2 border-green-300">
                  <h3 className="font-bold text-xl mb-4 text-green-900 flex items-center gap-2">
                    🚀 Melhorias de Hardware
                  </h3>
                  
                  <div className="space-y-4">
                    <div className="bg-white p-4 rounded-lg">
                      <h4 className="font-bold text-green-800 mb-2">1. Codec de Áudio Dedicado</h4>
                      <p className="text-sm text-gray-700 mb-2">
                        <strong>Problema atual:</strong> Compressão em software consome CPU
                      </p>
                      <p className="text-sm text-gray-700 mb-2">
                        <strong>Solução:</strong> Adicionar chip UDA1334A ou PCM5102A (DAC I2S) + Opus codec
                      </p>
                      <div className="bg-green-50 p-3 rounded mt-2 text-xs">
                        <p className="font-bold mb-1">Benefícios:</p>
                        <ul className="space-y-1">
                          <li>• Reduz latência de ~100ms para ~30ms</li>
                          <li>• Qualidade de áudio superior (até 48kHz)</li>
                          <li>• Libera 40% da CPU do ESP32</li>
                          <li>• Permite compressão Opus 6:1 em hardware</li>
                        </ul>
                      </div>
                    </div>

                    <div className="bg-white p-4 rounded-lg">
                      <h4 className="font-bold text-green-800 mb-2">2. Bateria com Backup</h4>
                      <p className="text-sm text-gray-700 mb-2">
                        <strong>Adicionar:</strong> LiPo 3.7V 2000mAh + TP4056 (carregador) + boost 5V
                      </p>
                      <div className="bg-green-50 p-3 rounded mt-2 text-xs">
                        <p className="font-bold mb-1">Benefícios:</p>
                        <ul className="space-y-1">
                          <li>• Autonomia ~6-8h de uso contínuo</li>
                          <li>• Funciona durante quedas de energia</li>
                          <li>• Node master portátil tipo walkie-talkie</li>
                        </ul>
                      </div>
                    </div>

                    <div className="bg-white p-4 rounded-lg">
                      <h4 className="font-bold text-green-800 mb-2">3. Antena Externa</h4>
                      <p className="text-sm text-gray-700 mb-2">
                        <strong>Upgrade:</strong> ESP32 com conector U.FL + antena 5dBi
                      </p>
                      <div className="bg-green-50 p-3 rounded mt-2 text-xs">
                        <p className="font-bold mb-1">Benefícios:</p>
                        <ul className="space-y-1">
                          <li>• Alcance de 50m → 150-200m</li>
                          <li>• Melhor penetração em paredes</li>
                          <li>• Custo adicional: ~R$ 15-30</li>
                        </ul>
                      </div>
                    </div>

                    <div className="bg-white p-4 rounded-lg">
                      <h4 className="font-bold text-green-800 mb-2">4. Amplificador de Áudio Mais Potente</h4>
                      <p className="text-sm text-gray-700 mb-2">
                        <strong>Substituir:</strong> MAX98357A (3W) por PAM8403 (2x3W) ou TPA3110 (2x15W)
                      </p>
                      <div className="bg-green-50 p-3 rounded mt-2 text-xs">
                        <p className="font-bold mb-1">Benefícios:</p>
                        <ul className="space-y-1">
                          <li>• Volume até 5x maior para áreas amplas</li>
                          <li>• Speakers estéreo para melhor cobertura</li>
                          <li>• Ideal para ambientes industriais/ruidosos</li>
                        </ul>
                      </div>
                    </div>

                    <div className="bg-white p-4 rounded-lg">
                      <h4 className="font-bold text-green-800 mb-2">5. Cartão SD para Storage Local</h4>
                      <p className="text-sm text-gray-700 mb-2">
                        <strong>Adicionar:</strong> Módulo SD Card SPI nos slaves
                      </p>
                      <div className="bg-green-50 p-3 rounded mt-2 text-xs">
                        <p className="font-bold mb-1">Benefícios:</p>
                        <ul className="space-y-1">
                          <li>• Cache local de 100+ mensagens pré-gravadas</li>
                          <li>• Funcionamento offline sem servidor</li>
                          <li>• Gravação de logs de eventos</li>
                        </ul>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="bg-gradient-to-r from-blue-50 to-blue-100 rounded-lg p-6 border-2 border-blue-300">
                  <h3 className="font-bold text-xl mb-4 text-blue-900 flex items-center gap-2">
                    💻 Melhorias de Software
                  </h3>
                  
                  <div className="space-y-4">
                    <div className="bg-white p-4 rounded-lg">
                      <h4 className="font-bold text-blue-800 mb-2">1. Sistema de Zonas/Grupos</h4>
                      <div className="bg-blue-50 p-3 rounded text-xs">
                        <p className="mb-2"><strong>Implementação:</strong></p>
                        <pre className="bg-gray-900 text-green-400 p-2 rounded overflow-x-auto">{`// Cada slave tem ID de zona
uint8_t myZone = 1; // Zona A

void onDataReceive(const uint8_t *mac, 
                   const uint8_t *data, int len) {
  audio_packet *pkt = (audio_packet *)data;
  
  // Só reproduz se for para sua zona ou broadcast
  if (pkt->targetZone == myZone || 
      pkt->targetZone == 0xFF) {
    playAudio(pkt);
  }
}`}</pre>
                        <p className="mt-2 font-bold">Benefícios:</p>
                        <ul className="space-y-1 mt-1">
                          <li>• Envie avisos para setores específicos</li>
                          <li>• Ex: "Zona A = Produção, Zona B = Escritório"</li>
                          <li>• Reduz tráfego de rede</li>
                        </ul>
                      </div>
                    </div>

                    <div className="bg-white p-4 rounded-lg">
                      <h4 className="font-bold text-blue-800 mb-2">2. Confirmação de Recebimento (ACK)</h4>
                      <div className="bg-blue-50 p-3 rounded text-xs">
                        <p className="mb-2"><strong>Implementação:</strong></p>
                        <pre className="bg-gray-900 text-green-400 p-2 rounded overflow-x-auto">{`// Slave envia ACK após reproduzir
void sendAck(uint16_t messageId) {
  ack_packet ack;
  ack.slaveId = MY_ID;
  ack.messageId = messageId;
  ack.rssi = WiFi.RSSI();
  esp_now_send(masterAddress, (uint8_t*)&ack, 
               sizeof(ack));
}

// Master mostra no display quais slaves confirmaram
display.println("Enviado para 5/7 nodes");`}</pre>
                        <p className="mt-2 font-bold">Benefícios:</p>
                        <ul className="space-y-1 mt-1">
                          <li>• Garante que mensagem chegou a todos</li>
                          <li>• Identifica nodes offline</li>
                          <li>• Dashboard mostra cobertura em tempo real</li>
                        </ul>
                      </div>
                    </div>

                    <div className="bg-white p-4 rounded-lg">
                      <h4 className="font-bold text-blue-800 mb-2">3. Priorização de Mensagens</h4>
                      <div className="bg-blue-50 p-3 rounded text-xs">
                        <p className="mb-2"><strong>Sistema de 3 níveis:</strong></p>
                        <div className="space-y-2">
                          <div className="flex items-start gap-2">
                            <span className="bg-red-600 text-white px-2 py-1 rounded font-bold">P1</span>
                            <div>
                              <p className="font-bold">EMERGÊNCIA</p>
                              <p className="text-gray-600">Interrompe tudo, sirene + flash vermelho, volume máximo</p>
                            </div>
                          </div>
                          <div className="flex items-start gap-2">
                            <span className="bg-yellow-600 text-white px-2 py-1 rounded font-bold">P2</span>
                            <div>
                              <p className="font-bold">AVISO</p>
                              <p className="text-gray-600">Aguarda mensagem atual terminar, LED amarelo</p>
                            </div>
                          </div>
                          <div className="flex items-start gap-2">
                            <span className="bg-blue-600 text-white px-2 py-1 rounded font-bold">P3</span>
                            <div>
                              <p className="font-bold">INFORMAÇÃO</p>
                              <p className="text-gray-600">Enfileira normalmente, LED azul</p>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>

                    <div className="bg-white p-4 rounded-lg">
                      <h4 className="font-bold text-blue-800 mb-2">4. Retry Automático com FEC</h4>
                      <div className="bg-blue-50 p-3 rounded text-xs">
                        <p className="mb-2"><strong>Forward Error Correction:</strong></p>
                        <pre className="bg-gray-900 text-green-400 p-2 rounded overflow-x-auto">{`// Envia cada pacote 2x com XOR parity
for (int i = 0; i < packetCount; i++) {
  esp_now_send(broadcast, packet[i], size);
  delay(5); // Espaçamento 5ms
  
  // Segundo envio com paridade XOR
  if (i % 2 == 1) {
    createParityPacket(packet[i-1], packet[i]);
    esp_now_send(broadcast, parityPkt, size);
  }
}`}</pre>
                        <p className="mt-2 font-bold">Benefícios:</p>
                        <ul className="space-y-1 mt-1">
                          <li>• Recupera até 50% de pacotes perdidos</li>
                          <li>• Áudio sem falhas mesmo com RSSI baixo</li>
                          <li>• Aumenta overhead em apenas 10-15%</li>
                        </ul>
                      </div>
                    </div>

                    <div className="bg-white p-4 rounded-lg">
                      <h4 className="font-bold text-blue-800 mb-2">5. Agendamento de Mensagens</h4>
                      <div className="bg-blue-50 p-3 rounded text-xs">
                        <p className="mb-2"><strong>Scheduler com RTC:</strong></p>
                        <pre className="bg-gray-900 text-green-400 p-2 rounded overflow-x-auto">{`// Adiciona DS3231 RTC via I2C
schedule_t schedules[] = {
  {.hour=8, .min=0, .msg="inicio_turno.wav"},
  {.hour=12, .min=0, .msg="almoco.wav"},
  {.hour=17, .min=0, .msg="fim_turno.wav"}
};

void loop() {
  checkSchedule();
}`}</pre>
                        <p className="mt-2 font-bold">Uso:</p>
                        <ul className="space-y-1 mt-1">
                          <li>• Avisos automáticos de horários</li>
                          <li>• Lembretes de segurança</li>
                          <li>• Música/jingle em horários específicos</li>
                        </ul>
                      </div>
                    </div>

                    <div className="bg-white p-4 rounded-lg">
                      <h4 className="font-bold text-blue-800 mb-2">6. Text-to-Speech (TTS)</h4>
                      <div className="bg-blue-50 p-3 rounded text-xs">
                        <p className="mb-2"><strong>Integração com Google TTS ou Azure:</strong></p>
                        <pre className="bg-gray-900 text-green-400 p-2 rounded overflow-x-auto">{`// No servidor
app.post('/speak', async (req, res) => {
  const text = req.body.text;
  const audioUrl = await textToSpeech(text);
  broadcastToSlaves(audioUrl);
});

// Interface: "Digite a mensagem e envie"
// Ex: "Atenção: teste de evacuação em 5 minutos"`}</pre>
                        <p className="mt-2 font-bold">Benefícios:</p>
                        <ul className="space-y-1 mt-1">
                          <li>• Crie avisos instantâneos sem gravar</li>
                          <li>• Suporte a múltiplos idiomas</li>
                          <li>• Vozes naturais e personalizáveis</li>
                        </ul>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="bg-gradient-to-r from-purple-50 to-purple-100 rounded-lg p-6 border-2 border-purple-300">
                  <h3 className="font-bold text-xl mb-4 text-purple-900 flex items-center gap-2">
                    🔐 Melhorias de Segurança
                  </h3>
                  
                  <div className="space-y-4">
                    <div className="bg-white p-4 rounded-lg">
                      <h4 className="font-bold text-purple-800 mb-2">1. Criptografia AES-128</h4>
                      <div className="bg-purple-50 p-3 rounded text-xs">
                        <pre className="bg-gray-900 text-green-400 p-2 rounded overflow-x-auto">{`// ESP-NOW já suporta criptografia nativa
esp_now_peer_info_t peerInfo = {};
memcpy(peerInfo.peer_addr, slaveAddress, 6);
peerInfo.encrypt = true;
memcpy(peerInfo.lmk, encryptionKey, 16);
esp_now_add_peer(&peerInfo);`}</pre>
                        <p className="mt-2">Protege contra interceptação de áudio</p>
                      </div>
                    </div>

                    <div className="bg-white p-4 rounded-lg">
                      <h4 className="font-bold text-purple-800 mb-2">2. Autenticação de Dispositivos</h4>
                      <div className="bg-purple-50 p-3 rounded text-xs">
                        <p className="mb-1">• Lista branca de MACs autorizados</p>
                        <p className="mb-1">• Handshake com token único</p>
                        <p>• Rejeita dispositivos não autorizados</p>
                      </div>
                    </div>

                    <div className="bg-white p-4 rounded-lg">
                      <h4 className="font-bold text-purple-800 mb-2">3. Logs de Auditoria</h4>
                      <div className="bg-purple-50 p-3 rounded text-xs">
                        <p className="mb-1">• Registra quem enviou cada mensagem</p>
                        <p className="mb-1">• Timestamp completo</p>
                        <p>• Exportação para análise</p>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="bg-gradient-to-r from-orange-50 to-orange-100 rounded-lg p-6 border-2 border-orange-300">
                  <h3 className="font-bold text-xl mb-4 text-orange-900 flex items-center gap-2">
                    ⚡ Melhorias de Performance
                  </h3>
                  
                  <div className="space-y-4">
                    <div className="bg-white p-4 rounded-lg">
                      <h4 className="font-bold text-orange-800 mb-2">1. Dual Core Processing</h4>
                      <div className="bg-orange-50 p-3 rounded text-xs">
                        <pre className="bg-gray-900 text-green-400 p-2 rounded overflow-x-auto">{`// Core 0: Captura/transmissão de áudio
xTaskCreatePinnedToCore(audioTask, "audio", 
                        4096, NULL, 1, NULL, 0);

// Core 1: Display, botões, WiFi
xTaskCreatePinnedToCore(uiTask, "ui", 
                        2048, NULL, 1, NULL, 1);`}</pre>
                        <p className="mt-2">Latência reduzida em 40%</p>
                      </div>
                    </div>

                    <div className="bg-white p-4 rounded-lg">
                      <h4 className="font-bold text-orange-800 mb-2">2. Buffer Adaptativo</h4>
                      <div className="bg-orange-50 p-3 rounded text-xs">
                        <p className="mb-1">• Aumenta buffer se detectar perda de pacotes</p>
                        <p className="mb-1">• Reduz buffer em condições ideais</p>
                        <p>• Balanceia latência vs qualidade automaticamente</p>
                      </div>
                    </div>

                    <div className="bg-white p-4 rounded-lg">
                      <h4 className="font-bold text-orange-800 mb-2">3. Downsampling Inteligente</h4>
                      <div className="bg-orange-50 p-3 rounded text-xs">
                        <p className="mb-1">• 16kHz para voz normal</p>
                        <p className="mb-1">• 8kHz se RSSI &lt; -70dBm (economia de banda)</p>
                        <p>• 24kHz para música (quando disponível)</p>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="bg-gradient-to-r from-red-50 to-red-100 rounded-lg p-6 border-2 border-red-300">
                  <h3 className="font-bold text-xl mb-4 text-red-900 flex items-center gap-2">
                    🚨 Features Avançados
                  </h3>
                  
                  <div className="grid md:grid-cols-2 gap-4 text-sm">
                    <div className="bg-white p-4 rounded-lg">
                      <h4 className="font-bold text-red-800 mb-2">Intercom Bidirecional</h4>
                      <p className="text-xs text-gray-700">Slaves podem responder ao master (modo walkie-talkie)</p>
                    </div>
                    <div className="bg-white p-4 rounded-lg">
                      <h4 className="font-bold text-red-800 mb-2">Detecção de Ruído Ambiente</h4>
                      <p className="text-xs text-gray-700">Ajusta volume automaticamente baseado no ruído local</p>
                    </div>
                    <div className="bg-white p-4 rounded-lg">
                      <h4 className="font-bold text-red-800 mb-2">Integração com Sensores</h4>
                      <p className="text-xs text-gray-700">Dispara avisos automáticos (fumaça, temperatura, movimento)</p>
                    </div>
                    <div className="bg-white p-4 rounded-lg">
                      <h4 className="font-bold text-red-800 mb-2">Mesh Network</h4>
                      <p className="text-xs text-gray-700">Slaves retransmitem para aumentar alcance (painlessMesh)</p>
                    </div>
                    <div className="bg-white p-4 rounded-lg">
                      <h4 className="font-bold text-red-800 mb-2">Voice Activation (VOX)</h4>
                      <p className="text-xs text-gray-700">Transmite automaticamente ao detectar voz (sem PTT)</p>
                    </div>
                    <div className="bg-white p-4 rounded-lg">
                      <h4 className="font-bold text-red-800 mb-2">Multi-Master</h4>
                      <p className="text-xs text-gray-700">Vários nodes podem transmitir (com fila de prioridade)</p>
                    </div>
                  </div>
                </div>

                <div className="bg-gray-800 text-white rounded-lg p-6">
                  <h3 className="font-bold text-xl mb-4">📊 Roadmap de Implementação</h3>
                  <div className="space-y-3 text-sm">
                    <div className="flex items-start gap-3">
                      <span className="bg-green-600 px-3 py-1 rounded font-bold">Fase 1</span>
                      <div>
                        <p className="font-bold">Sistema Básico (2-4 semanas)</p>
                        <p className="text-gray-300">Master + Slaves + ESP-NOW + Interface Web</p>
                      </div>
                    </div>
                    <div className="flex items-start gap-3">
                      <span className="bg-yellow-600 px-3 py-1 rounded font-bold">Fase 2</span>
                      <div>
                        <p className="font-bold">Melhorias Essenciais (2-3 semanas)</p>
                        <p className="text-gray-300">Zonas + ACK + Prioridades + Bateria</p>
                      </div>
                    </div>
                    <div className="flex items-start gap-3">
                      <span className="bg-blue-600 px-3 py-1 rounded font-bold">Fase 3</span>
                      <div>
                        <p className="font-bold">Features Avançados (3-4 semanas)</p>
                        <p className="text-gray-300">TTS + Agendamento + Criptografia + FEC</p>
                      </div>
                    </div>
                    <div className="flex items-start gap-3">
                      <span className="bg-purple-600 px-3 py-1 rounded font-bold">Fase 4</span>
                      <div>
                        <p className="font-bold">Produção (2-3 semanas)</p>
                        <p className="text-gray-300">Testes extensivos + PCB customizado + Case 3D</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="mt-8 bg-gradient-to-r from-blue-600 to-purple-600 rounded-xl p-6 text-white">
          <h3 className="text-xl font-bold mb-3">Próximos Passos</h3>
          <div className="grid md:grid-cols-3 gap-4 text-sm">
            <div>
              <h4 className="font-bold mb-2">1. Protótipo</h4>
              <p>Monte 1 master + 1 slave e teste ESP-NOW</p>
            </div>
            <div>
              <h4 className="font-bold mb-2">2. Servidor</h4>
              <p>Configure MQTT e interface web</p>
            </div>
            <div>
              <h4 className="font-bold mb-2">3. Expansão</h4>
              <p>Adicione mais slaves e zonas</p>
            </div>
          </div>
        </div>

        <div className="mt-6 bg-yellow-50 border-l-4 border-yellow-500 p-4">
          <div className="flex items-start gap-3">
            <AlertCircle className="text-yellow-600 flex-shrink-0" size={24} />
            <div className="text-sm text-gray-700">
              <p className="font-bold text-yellow-900 mb-2">Considerações</p>
              <ul className="space-y-1">
                <li>• Alcance: ~50m ambientes internos</li>
                <li>• Latência: 50-100ms fim-a-fim</li>
                <li>• Máx 20 slaves oficialmente</li>
                <li>• 16kHz suficiente para voz</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ESP32WarningSystem;