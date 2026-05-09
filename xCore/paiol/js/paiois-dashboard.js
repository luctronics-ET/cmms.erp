const romanUnits = ["I", "II", "III", "IV", "V"];

function buildBlock(groupName, prefix, blockNumber, options = {}) {
    return romanUnits.map((unit, unitIndex) => {
        const id = `${prefix}-${blockNumber}-${unit}`;
        const ipBase = options.ipBase + unitIndex;
        const controllerId = options.hasHvac ? `${prefix}-${blockNumber}-V` : null;

        return buildAutomatedPaiol({
            id,
            groupName,
            block: `${prefix}-${blockNumber}`,
            street: String(blockNumber),
            sensorIp: `192.168.10.${ipBase}`,
            sensorModel: "DCM SE-10",
            cameraIp: `192.168.20.${ipBase}`,
            controllerId: unit === "V" && options.hasHvac ? "self" : controllerId,
            hasRelay: unit === "V" && options.hasHvac,
            hasHvac: options.hasHvac,
            notes: options.notes || [],
            limits: options.limits,
        });
    });
}

function buildAutomatedPaiol({
    id,
    groupName,
    block,
    street,
    sensorIp,
    sensorModel,
    cameraIp,
    controllerId,
    hasRelay,
    hasHvac,
    notes,
    limits,
}) {
    const seed = Array.from(id).reduce((sum, char) => sum + char.charCodeAt(0), 0);
    const baseTemperature = 22 + (seed % 70) / 10;
    const baseHumidity = 53 + (seed % 18);
    const forced = forcedReadings[id] || {};
    const temperature = forced.temperature ?? Number(baseTemperature.toFixed(1));
    const humidity = forced.humidity ?? Math.min(baseHumidity, 79);
    const updatedAt = forced.updatedAt || `23/04/2026 ${String(8 + (seed % 10)).padStart(2, "0")}:${String(seed % 60).padStart(2, "0")}`;
    const alarms = [...(forced.alarms || [])];
    const hvacState = hasHvac ? (forced.hvacState ?? ((seed % 3) !== 0)) : false;
    const cameraOnline = forced.cameraOnline ?? true;
    const status = alarms.length > 0 ? "alarm" : "ok";

    return {
        id,
        groupName,
        block,
        street,
        type: block ? "conjugado" : "isolado",
        className: "automatizado",
        sensorModel,
        sensorIp,
        sensorUrl: `http://${sensorIp}`,
        cameraIp,
        cameraUrl: cameraIp ? `http://${cameraIp}` : null,
        cameraOnline,
        cameraPreview: makeCameraPreview(id),
        controllerId,
        hasRelay,
        hasHvac,
        notes,
        readings: {
            temperature,
            humidity,
            externalTemperature: forced.externalTemperature ?? Number((temperature - 0.7).toFixed(1)),
            dewPoint: forced.dewPoint ?? Number((temperature - 5.8).toFixed(1)),
            input1: forced.input1 ?? 0,
            input2: forced.input2 ?? 0,
            output1: hvacState ? 1 : 0,
            updatedAt,
        },
        alarms,
        status,
        limits: limits || { tempMin: 18, tempMax: 27, humMin: 40, humMax: 65 },
    };
}

function buildManualPaiol(id, street) {
    return {
        id,
        groupName: `Rua ${street}`,
        block: null,
        street: String(street),
        type: "isolado",
        className: "manual",
        sensorModel: "Leitura manual",
        sensorIp: null,
        sensorUrl: null,
        cameraIp: null,
        cameraUrl: null,
        cameraOnline: false,
        cameraPreview: makeCameraPreview(id, true),
        controllerId: null,
        hasRelay: false,
        hasHvac: false,
        notes: ["Registro diario manual", "Sem telemetria integrada nesta fase"],
        readings: {
            temperature: null,
            humidity: null,
            externalTemperature: null,
            dewPoint: null,
            input1: null,
            input2: null,
            output1: null,
            updatedAt: "Aguardando integracao operacional",
        },
        alarms: ["Sem telemetria automatizada"],
        status: "manual",
        limits: { tempMin: 18, tempMax: 27, humMin: 40, humMax: 65 },
    };
}

function makeCameraPreview(id, isManual = false) {
    const background = isManual ? "#9a8f83" : "#1b5c77";
    const accent = isManual ? "#f1e8da" : "#f5efe1";
    const svg = `
        <svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720" viewBox="0 0 1280 720">
            <defs>
                <linearGradient id="bg" x1="0" x2="1" y1="0" y2="1">
                    <stop stop-color="${background}" offset="0"/>
                    <stop stop-color="#1f2a2c" offset="1"/>
                </linearGradient>
            </defs>
            <rect width="1280" height="720" fill="url(#bg)"/>
            <rect x="72" y="82" width="1136" height="556" rx="28" fill="rgba(255,255,255,0.08)" stroke="rgba(255,255,255,0.18)"/>
            <text x="110" y="180" fill="${accent}" font-size="64" font-family="Trebuchet MS, sans-serif">${id}</text>
            <text x="110" y="250" fill="${accent}" font-size="28" font-family="Trebuchet MS, sans-serif">${isManual ? "Camera pendente / uso manual" : "Preview da camera IP para integracao local"}</text>
            <circle cx="1080" cy="190" r="84" fill="rgba(255,255,255,0.14)"/>
            <rect x="320" y="364" width="640" height="120" rx="60" fill="rgba(255,255,255,0.12)"/>
            <text x="394" y="442" fill="${accent}" font-size="42" font-family="Trebuchet MS, sans-serif">xPaiol monitor operacional</text>
        </svg>`;

    return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`;
}

const forcedReadings = {
    "G-7-IV": {
        temperature: 31.4,
        humidity: 74,
        alarms: ["Temperatura alta", "Umidade alta"],
        hvacState: true,
        input1: 1,
    },
    "U-6-II": {
        temperature: 40.1,
        humidity: 77,
        alarms: ["Temperatura critica", "Umidade alta"],
        hvacState: true,
        input2: 1,
    },
    "D-5": {
        temperature: 30.5,
        humidity: 67,
        alarms: ["Temperatura alta"],
        hvacState: true,
    },
    "Q-6": {
        temperature: 28.7,
        humidity: 63,
        alarms: ["Camera offline"],
        hvacState: false,
        cameraOnline: false,
        online: false,
    },
    "U-5-III": {
        temperature: 29.4,
        humidity: 70,
        alarms: ["Sem refrigeracao neste bloco"],
        hvacState: false,
    },
};

const paiois = [
    ...buildBlock("Golf", "G", 5, { ipBase: 39, hasHvac: true, notes: ["Reles do bloco no paiol V", "Casa de maquinas compartilhada"] }),
    ...buildBlock("Golf", "G", 6, { ipBase: 44, hasHvac: true, notes: ["Reles do bloco no paiol V", "Casa de maquinas compartilhada"] }),
    ...buildBlock("Golf", "G", 7, { ipBase: 49, hasHvac: true, notes: ["Reles do bloco no paiol V", "Casa de maquinas compartilhada"] }),
    ...buildBlock("Golf", "G", 8, { ipBase: 54, hasHvac: true, notes: ["Reles do bloco no paiol V", "Casa de maquinas compartilhada"] }),

    ...buildBlock("Uniform", "U", 5, { ipBase: 59, hasHvac: false, notes: ["Sem casa de maquinas", "Somente monitoramento ambiental e camera"] }),
    ...buildBlock("Uniform", "U", 6, { ipBase: 64, hasHvac: true, notes: ["Reles do bloco no paiol V", "Casa de maquinas compartilhada"] }),
    ...buildBlock("Uniform", "U", 7, { ipBase: 69, hasHvac: true, notes: ["Reles do bloco no paiol V", "Casa de maquinas compartilhada"] }),
    ...buildBlock("Uniform", "U", 8, { ipBase: 74, hasHvac: true, notes: ["Reles do bloco no paiol V", "Casa de maquinas compartilhada"] }),

    buildAutomatedPaiol({
        id: "D-5",
        groupName: "Rua 5",
        block: null,
        street: "5",
        sensorIp: "192.168.10.79",
        sensorModel: "DCM SE-10",
        cameraIp: "192.168.20.79",
        controllerId: "self",
        hasRelay: true,
        hasHvac: true,
        notes: ["Paiol isolado com refrigeracao individual"],
    }),
    buildAutomatedPaiol({
        id: "K-6",
        groupName: "Rua 6",
        block: null,
        street: "6",
        sensorIp: "192.168.10.80",
        sensorModel: "DCM SE-10",
        cameraIp: "192.168.20.80",
        controllerId: "self",
        hasRelay: true,
        hasHvac: true,
        notes: ["Paiol isolado com refrigeracao individual"],
    }),
    buildAutomatedPaiol({
        id: "L-6",
        groupName: "Rua 6",
        block: null,
        street: "6",
        sensorIp: "192.168.10.81",
        sensorModel: "DCM SE-10",
        cameraIp: "192.168.20.81",
        controllerId: "self",
        hasRelay: true,
        hasHvac: true,
        notes: ["Paiol isolado com refrigeracao individual"],
    }),
    buildAutomatedPaiol({
        id: "M-6",
        groupName: "Rua 6",
        block: null,
        street: "6",
        sensorIp: "192.168.10.82",
        sensorModel: "DCM SE-10",
        cameraIp: "192.168.20.82",
        controllerId: "self",
        hasRelay: true,
        hasHvac: true,
        notes: ["Paiol isolado com refrigeracao individual"],
    }),
    buildAutomatedPaiol({
        id: "O-6",
        groupName: "Rua 6",
        block: null,
        street: "6",
        sensorIp: "192.168.10.83",
        sensorModel: "DCM SE-10",
        cameraIp: "192.168.20.83",
        controllerId: "self",
        hasRelay: true,
        hasHvac: true,
        notes: ["Paiol isolado com refrigeracao individual"],
    }),
    buildAutomatedPaiol({
        id: "Q-6",
        groupName: "Rua 6",
        block: null,
        street: "6",
        sensorIp: "192.168.10.84",
        sensorModel: "DCM SE-10",
        cameraIp: "192.168.20.84",
        controllerId: "self",
        hasRelay: true,
        hasHvac: true,
        notes: ["Paiol isolado com refrigeracao individual"],
    }),

    ...["J-7", "L-7", "P-7", "R-7"].map((id) => buildManualPaiol(id, 7)),
    ...["I-8", "J-8", "K-8", "L-8", "M-8", "O-8", "Q-8"].map((id) => buildManualPaiol(id, 8)),
    ...["H-9", "J-9", "L-9", "P-9"].map((id) => buildManualPaiol(id, 9)),
    ...["K-10", "M-10", "O-10", "Q-10"].map((id) => buildManualPaiol(id, 10)),
    buildManualPaiol("P-11", 11),
];

const heroStats = document.getElementById("heroStats");
const sectionsRoot = document.getElementById("sectionsRoot");
const modal = document.getElementById("paiolModal");
const closeModal = document.getElementById("closeModal");
const obsInput = document.getElementById("obsInput");
const obsMeta = document.getElementById("obsMeta");
const limitTempMinInput = document.getElementById("limitTempMin");
const limitTempMaxInput = document.getElementById("limitTempMax");
const limitHumMinInput = document.getElementById("limitHumMin");
const limitHumMaxInput = document.getElementById("limitHumMax");
const limitsMeta = document.getElementById("limitsMeta");
const sensorTempInput = document.getElementById("sensorTemp");
const sensorHumInput = document.getElementById("sensorHum");
const sensorTempExtInput = document.getElementById("sensorTempExt");
const sensorDewInput = document.getElementById("sensorDew");
const sensorIn1Input = document.getElementById("sensorIn1");
const sensorIn2Input = document.getElementById("sensorIn2");
const sensorOut1Input = document.getElementById("sensorOut1");
const sensorValuesMeta = document.getElementById("sensorValuesMeta");

const alarmStateByPaiol = Object.fromEntries(paiois.map((paiol) => {
    const activeMessages = detectLatchedInputMessages(paiol);

    return [paiol.id, {
        latched: activeMessages.length > 0,
        messages: activeMessages,
        handling: activeMessages.length > 0 ? "PENDENTE" : "OP",
        observation: "",
        updatedAt: paiol.readings.updatedAt,
    }];
}));

let activePaiolId = null;

if (heroStats) {
    renderHero();
}
renderSections();

document.getElementById("btnFalseAlarm").addEventListener("click", () => handleAlarmAction("FALSO AL"));
document.getElementById("btnOp").addEventListener("click", () => handleAlarmAction("OP"));
document.getElementById("btnEmerg").addEventListener("click", () => handleAlarmAction("EMERG"));
document.getElementById("btnAcao").addEventListener("click", () => handleAlarmAction("ACAO"));
document.getElementById("btnSaveLimits").addEventListener("click", saveLimits);
document.getElementById("btnSaveSensorValues").addEventListener("click", saveSensorValues);

closeModal.addEventListener("click", closePaiolModal);
modal.addEventListener("click", (event) => {
    if (event.target.dataset.close === "true") {
        closePaiolModal();
    }
});

document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
        closePaiolModal();
    }
});

function renderHero() {
    const automaticCount = paiois.filter((paiol) => paiol.status !== "manual").length;
    const alarmCount = paiois.filter((paiol) => hasVisualAlarm(paiol)).length;
    const offlineCount = paiois.filter((paiol) => isOffline(paiol)).length;
    const cameraCount = paiois.filter((paiol) => paiol.cameraUrl).length;

    heroStats.innerHTML = [
        statCard(automaticCount, "Paiois com sensor"),
        statCard(alarmCount, "Cards em alarme"),
        statCard(offlineCount, "Sensores offline/manual"),
        statCard(cameraCount, "Cameras previstas"),
    ].join("");
}

function statCard(value, label) {
    return `<div class="stat-card"><strong>${value}</strong><span>${label}</span></div>`;
}

function renderSections() {
    sectionsRoot.innerHTML = `<div class="paiol-grid">${paiois.map(renderPaiolCard).join("")}</div>`;

    sectionsRoot.querySelectorAll("[data-paiol-id]").forEach((card) => {
        card.addEventListener("click", () => {
            const paiol = paiois.find((item) => item.id === card.dataset.paiolId);
            openPaiolModal(paiol);
        });
    });
}

function renderPaiolCard(paiol) {
    const classes = ["paiol-card"];
    const alarmState = alarmStateByPaiol[paiol.id];
    const offline = isOffline(paiol);

    if (hasVisualAlarm(paiol)) {
        classes.push("is-alarm");
    }

    if (alarmState.latched) {
        classes.push("is-latched");
    }

    if (offline) {
        classes.push("is-offline");
    }

    const temperatureAlert = paiol.readings.temperature !== null && paiol.readings.temperature >= paiol.limits.tempMax;
    const humidityAlert = paiol.readings.humidity !== null && paiol.readings.humidity >= paiol.limits.humMax;

    return `
        <article class="${classes.join(" ")}" data-paiol-id="${paiol.id}">
            <div class="card-topline">
                <h3 class="card-id">${paiol.id}</h3>
                <div class="input-badges">${renderInputBadges(paiol)}</div>
            </div>

            <div class="card-metrics">
                <div class="metric">
                    <span class="metric-label">UMD %</span>
                    <span class="metric-value ${humidityAlert ? "is-alert" : ""}">${formatCardValue(paiol.readings.humidity)}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">TEMP C</span>
                    <span class="metric-value ${temperatureAlert ? "is-alert" : ""}">${formatCardValue(paiol.readings.temperature)}</span>
                </div>
            </div>
        </article>
    `;
}

function openPaiolModal(paiol) {
    activePaiolId = paiol.id;
    const alarmState = alarmStateByPaiol[paiol.id];

    document.getElementById("modalEyebrow").textContent = `${paiol.groupName}${paiol.block ? ` • ${paiol.block}` : ""}`;
    document.getElementById("modalTitle").textContent = paiol.id;

    const modalStatus = document.getElementById("modalStatus");
    modalStatus.textContent = alarmState.latched ? `Alarme Latch (${alarmState.handling})` : "Operacao normal";
    modalStatus.className = `status-pill${alarmState.latched ? " is-alarm" : ""}${paiol.status === "manual" ? " is-manual" : ""}`;

    const camera = document.getElementById("modalCamera");
    camera.src = paiol.cameraPreview;

    const cameraAction = document.getElementById("cameraAction");
    applyLink(cameraAction, paiol.cameraUrl, paiol.cameraUrl ? "Abrir stream ou pagina da camera" : "Camera pendente");

    const sensorAction = document.getElementById("sensorAction");
    applyLink(sensorAction, paiol.sensorUrl, paiol.sensorUrl ? `Abrir pagina do sensor (${paiol.sensorIp})` : "Sensor nao disponivel");

    const cameraPageAction = document.getElementById("cameraPageAction");
    applyLink(cameraPageAction, paiol.cameraUrl, paiol.cameraUrl ? `Abrir pagina da camera (${paiol.cameraIp})` : "Pagina da camera indisponivel");

    document.getElementById("sensorDetails").innerHTML = [
        detailRow("Classe", paiol.className),
        detailRow("Tipo", paiol.type),
        detailRow("Sensor", paiol.sensorModel),
        detailRow("IP sensor", paiol.sensorIp || "Sem IP"),
        detailRow("Controlador", paiol.controllerId || "Nao aplicavel"),
        detailRow("Rele", paiol.hasRelay ? "Sim" : "Nao"),
        detailRow("Camera", paiol.cameraOnline ? "Integrada" : "Pendente/offline"),
        detailRow("TMP (Min/Max)", `${paiol.limits.tempMin} / ${paiol.limits.tempMax} °C`),
        detailRow("UMD (Min/Max)", `${paiol.limits.humMin} / ${paiol.limits.humMax} %`),
        detailRow("Notas", paiol.notes.join(" / ")),
    ].join("");

    document.getElementById("readingGrid").innerHTML = [
        readingItem("Temperatura", formatReading(paiol.readings.temperature, "°C"), paiol.readings.temperature !== null && paiol.readings.temperature >= paiol.limits.tempMax),
        readingItem("Umidade", formatReading(paiol.readings.humidity, "%"), paiol.readings.humidity !== null && paiol.readings.humidity >= paiol.limits.humMax),
        readingItem("Temp. sonda", formatReading(paiol.readings.externalTemperature, "°C"), false),
        readingItem("Orvalho", formatReading(paiol.readings.dewPoint, "°C"), false),
        readingItem("Entrada 1", formatBinary(paiol.readings.input1), false),
        readingItem("Entrada 2", formatBinary(paiol.readings.input2), false),
        readingItem("Saida rele", formatBinary(paiol.readings.output1), alarmState.latched && paiol.hasHvac),
        readingItem("Atualizado", paiol.readings.updatedAt, false),
    ].join("");

    const sensorMessages = detectSensorAlarmMessages(paiol);
    const allMessages = [...sensorMessages, ...alarmState.messages];

    document.getElementById("alarmList").innerHTML = allMessages.length > 0
        ? allMessages.map((alarm) => `<span class="alarm-tag">${alarm}</span>`).join("")
        : '<span class="alarm-tag" style="background: rgba(47, 111, 79, 0.12); color: var(--ok);">Sem alarmes ativos</span>';

    obsInput.value = alarmState.observation;
    obsMeta.textContent = alarmState.updatedAt ? `Ultima atualizacao: ${alarmState.updatedAt}` : "";
    limitTempMinInput.value = paiol.limits.tempMin;
    limitTempMaxInput.value = paiol.limits.tempMax;
    limitHumMinInput.value = paiol.limits.humMin;
    limitHumMaxInput.value = paiol.limits.humMax;
    limitsMeta.textContent = "";
    sensorTempInput.value = paiol.readings.temperature ?? "";
    sensorHumInput.value = paiol.readings.humidity ?? "";
    sensorTempExtInput.value = paiol.readings.externalTemperature ?? "";
    sensorDewInput.value = paiol.readings.dewPoint ?? "";
    sensorIn1Input.value = paiol.readings.input1 ?? 0;
    sensorIn2Input.value = paiol.readings.input2 ?? 0;
    sensorOut1Input.value = paiol.readings.output1 ?? 0;
    sensorValuesMeta.textContent = "";

    modal.classList.add("is-open");
    modal.setAttribute("aria-hidden", "false");
}

function closePaiolModal() {
    activePaiolId = null;
    modal.classList.remove("is-open");
    modal.setAttribute("aria-hidden", "true");
}

function detailRow(label, value) {
    return `<div><dt>${label}</dt><dd>${value}</dd></div>`;
}

function readingItem(label, value, isAlert) {
    return `<div class="reading-item${isAlert ? " is-alert" : ""}"><strong>${label}</strong><span>${value}</span></div>`;
}

function formatReading(value, suffix) {
    if (value === null || value === undefined) {
        return "--";
    }

    return `<span class="num">${value}</span><span class="unit">${suffix}</span>`;
}

function formatCardValue(value) {
    if (value === null || value === undefined) {
        return "--";
    }

    const numeric = Number(value);
    if (!Number.isFinite(numeric)) {
        return "--";
    }

    const rounded = Math.round(numeric);
    if (rounded >= 0 && rounded < 10) {
        return `0${rounded}`;
    }

    return String(rounded);
}

function formatBinary(value) {
    if (value === null || value === undefined) {
        return "--";
    }

    return value ? "Ativo" : "Inativo";
}

function applyLink(element, href, label) {
    element.textContent = label;

    if (href) {
        element.href = href;
        element.target = "_blank";
        element.rel = "noreferrer";
        element.classList.remove("action-link--muted");
        return;
    }

    element.href = "#";
    element.removeAttribute("target");
    element.classList.add("action-link--muted");
}

function isOffline(paiol) {
    if (paiol.status === "manual") {
        return true;
    }

    const forced = forcedReadings[paiol.id] || {};
    return forced.online === false;
}

function detectLatchedInputMessages(paiol) {
    const messages = [];

    if (paiol.readings.input1 === 1 && !messages.includes("A1:FUM ativo")) {
        messages.push("A1:FUM ativo");
    }

    if (paiol.readings.input2 === 1 && !messages.includes("A2:MOV ativo")) {
        messages.push("A2:MOV ativo");
    }

    return [...new Set(messages)];
}

function detectSensorAlarmMessages(paiol) {
    const messages = [...paiol.alarms];

    if (paiol.readings.humidity !== null && paiol.readings.humidity >= paiol.limits.humMax && !messages.includes("Umidade alta")) {
        messages.push("Umidade alta");
    }

    if (paiol.readings.temperature !== null && paiol.readings.temperature >= paiol.limits.tempMax + 10 && !messages.includes("Temperatura critica")) {
        messages.push("Temperatura critica");
    } else if (paiol.readings.temperature !== null && paiol.readings.temperature >= paiol.limits.tempMax && !messages.includes("Temperatura alta")) {
        messages.push("Temperatura alta");
    }

    if (isOffline(paiol) && !messages.includes("Sensor offline/manual")) {
        messages.push("Sensor offline/manual");
    }

    return [...new Set(messages)];
}

function hasVisualAlarm(paiol) {
    const humidityAlert = paiol.readings.humidity !== null && paiol.readings.humidity >= paiol.limits.humMax;
    const tempAlert = paiol.readings.temperature !== null && paiol.readings.temperature >= paiol.limits.tempMax;
    return humidityAlert || tempAlert || alarmStateByPaiol[paiol.id].latched;
}

function renderInputBadges(paiol) {
    const badges = [];

    if (paiol.readings.input1 === 1) {
        badges.push('<span class="mini-badge">A1:FUM</span>');
    }

    if (paiol.readings.input2 === 1) {
        badges.push('<span class="mini-badge">A2:MOV</span>');
    }

    return badges.join("");
}

function nowLabel() {
    return new Date().toLocaleString("pt-BR", { hour12: false });
}

function handleAlarmAction(actionType) {
    if (!activePaiolId) {
        return;
    }

    const paiol = paiois.find((item) => item.id === activePaiolId);
    const state = alarmStateByPaiol[activePaiolId];
    const note = obsInput.value.trim();

    if (actionType === "FALSO AL" || actionType === "OP") {
        state.latched = false;
        state.messages = [];
        state.handling = actionType;
    }

    if (actionType === "ACAO") {
        state.handling = "ACAO";
        if (state.messages.length > 0 && !state.messages.includes("Acao requerida pelo operador")) {
            state.messages.push("Acao requerida pelo operador");
        }
    }

    if (actionType === "EMERG") {
        state.latched = state.messages.length > 0;
        state.handling = "EMERG";
        if (state.messages.length > 0 && !state.messages.includes("Emergencia acionada")) {
            state.messages.push("Emergencia acionada");
        }
    }

    if (note.length > 0) {
        state.observation = note;
    }

    state.updatedAt = nowLabel();

    if (heroStats) {
        renderHero();
    }
    renderSections();
    openPaiolModal(paiol);
}

function saveLimits() {
    if (!activePaiolId) {
        return;
    }

    const paiol = paiois.find((item) => item.id === activePaiolId);
    const tempMin = Number(limitTempMinInput.value);
    const tempMax = Number(limitTempMaxInput.value);
    const humMin = Number(limitHumMinInput.value);
    const humMax = Number(limitHumMaxInput.value);

    if (!Number.isFinite(tempMin) || !Number.isFinite(tempMax) || !Number.isFinite(humMin) || !Number.isFinite(humMax)) {
        limitsMeta.textContent = "Preencha limites validos para salvar.";
        return;
    }

    if (tempMin >= tempMax || humMin >= humMax) {
        limitsMeta.textContent = "Os limites minimos devem ser menores que os maximos.";
        return;
    }

    paiol.limits = { tempMin, tempMax, humMin, humMax };
    limitsMeta.textContent = `Limites atualizados em ${nowLabel()}`;

    if (heroStats) {
        renderHero();
    }
    renderSections();
    openPaiolModal(paiol);
}

function saveSensorValues() {
    if (!activePaiolId) {
        return;
    }

    const paiol = paiois.find((item) => item.id === activePaiolId);
    const temperature = Number(sensorTempInput.value);
    const humidity = Number(sensorHumInput.value);
    const externalTemperature = Number(sensorTempExtInput.value);
    const dewPoint = Number(sensorDewInput.value);
    const input1 = Number(sensorIn1Input.value);
    const input2 = Number(sensorIn2Input.value);
    const output1 = Number(sensorOut1Input.value);

    if (!Number.isFinite(temperature) || !Number.isFinite(humidity) || !Number.isFinite(externalTemperature) || !Number.isFinite(dewPoint)) {
        sensorValuesMeta.textContent = "Preencha valores numericos validos para temperatura, umidade, sonda e orvalho.";
        return;
    }

    if (![0, 1].includes(input1) || ![0, 1].includes(input2) || ![0, 1].includes(output1)) {
        sensorValuesMeta.textContent = "IN1, IN2 e Saida Rele devem ser Ativo ou Inativo.";
        return;
    }

    paiol.readings.temperature = temperature;
    paiol.readings.humidity = humidity;
    paiol.readings.externalTemperature = externalTemperature;
    paiol.readings.dewPoint = dewPoint;
    paiol.readings.input1 = input1;
    paiol.readings.input2 = input2;
    paiol.readings.output1 = output1;
    paiol.readings.updatedAt = nowLabel();

    const latchedMessages = detectLatchedInputMessages(paiol);
    const state = alarmStateByPaiol[paiol.id];
    state.latched = latchedMessages.length > 0;
    state.messages = latchedMessages;
    state.handling = state.latched ? "PENDENTE" : "OP";
    state.updatedAt = paiol.readings.updatedAt;

    sensorValuesMeta.textContent = `Valores atualizados em ${paiol.readings.updatedAt}`;

    if (heroStats) {
        renderHero();
    }
    renderSections();
    openPaiolModal(paiol);
}