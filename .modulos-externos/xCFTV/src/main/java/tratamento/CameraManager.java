package tratamento;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import javax.faces.bean.ApplicationScoped;
import javax.faces.bean.ManagedBean;

@ManagedBean(name = "cameraManager", eager = true)
@ApplicationScoped
public class CameraManager {
    private List<Camera> cameras = new ArrayList<>();
    private String csvPath = "CFTV_plantas/IP_CFTB_SENS.csv";

    public CameraManager() {
        try {
            loadCameras();
        } catch (Exception e) {
            System.err.println("Erro ao carregar câmeras: " + e.getMessage());
            e.printStackTrace();
        }
    }

    public void loadCameras() {
        cameras.clear();
        try {
            Path filePath = findCSVFile();
            if (filePath != null && Files.exists(filePath)) {
                List<String> lines = Files.readAllLines(filePath, StandardCharsets.UTF_8);
                for (int i = 1; i < lines.size(); i++) {
                    String line = lines.get(i).trim();
                    if (!line.isEmpty()) {
                        Camera cam = parseCSVLine(line);
                        if (cam != null) cameras.add(cam);
                    }
                }
                System.out.println("Carregadas " + cameras.size() + " câmeras de " + filePath);
            } else {
                System.err.println("Arquivo CSV não encontrado");
            }
        } catch (Exception e) {
            System.err.println("Erro ao carregar CSV: " + e.getMessage());
        }
    }

    private Path findCSVFile() {
        String[] basePaths = {
            System.getProperty("user.dir"),
            System.getProperty("catalina.base"),
            "/opt/tomcat",
            "/usr/local/tomcat"
        };

        for (String basePath : basePaths) {
            if (basePath == null) continue;
            Path[] candidates = {
                Paths.get(basePath, "src/main/webapp", csvPath),
                Paths.get(basePath, "target/ControlCAM-1.0-SNAPSHOT", csvPath),
                Paths.get(basePath, csvPath),
                Paths.get(basePath, "webapps/ROOT", csvPath),
                Paths.get(basePath, "webapps/ControlCAM", csvPath)
            };
            for (Path candidate : candidates) {
                if (Files.exists(candidate)) {
                    System.out.println("CSV encontrado em: " + candidate);
                    return candidate;
                }
            }
        }
        System.err.println("CSV não encontrado em nenhum local esperado");
        return null;
    }

    private Camera parseCSVLine(String line) {
        try {
            String[] parts = line.split(",", -1);
            if (parts.length >= 7) {
                int id = Integer.parseInt(parts[0].trim());
                String ip = parts[1].trim();
                String local = parts[2].trim();
                String tipo = parts[3].trim();
                String marca = parts[4].trim();
                String modelo = parts[5].trim();
                String mac = parts[6].trim();
                return new Camera(id, ip, local, tipo, marca, modelo, mac);
            }
        } catch (Exception e) {
            System.err.println("Erro ao parsear linha: " + line + " - " + e.getMessage());
        }
        return null;
    }

    public void saveCameras() {
        try {
            Path filePath = findCSVFile();
            if (filePath == null) {
                filePath = Paths.get(System.getProperty("user.dir"), "src/main/webapp", csvPath);
                Files.createDirectories(filePath.getParent());
            }

            StringBuilder sb = new StringBuilder();
            sb.append("id,IP,LOCAL,tipo_equipamento,Marca,Modelo,MAC\n");
            for (Camera cam : cameras) {
                sb.append(cam.getId()).append(",").append(cam.getIp()).append(",")
                  .append(cam.getLocal()).append(",").append(cam.getTipoEquipamento()).append(",")
                  .append(cam.getMarca()).append(",").append(cam.getModelo()).append(",")
                  .append(cam.getMac()).append("\n");
            }
            Files.write(filePath, sb.toString().getBytes(StandardCharsets.UTF_8));
        } catch (Exception e) {
            System.err.println("Erro ao salvar CSV: " + e.getMessage());
        }
    }

    public List<Camera> getCameras() {
        return new ArrayList<>(cameras);
    }

    public Camera getCameraByLocal(String local) {
        for (Camera cam : cameras) {
            if (local != null && local.equalsIgnoreCase(cam.getLocal())) {
                return cam;
            }
        }
        return null;
    }

    public List<Camera> getCamerasByTipo(String tipo) {
        List<Camera> result = new ArrayList<>();
        if (tipo != null && !tipo.isEmpty()) {
            for (Camera cam : cameras) {
                if (cam.getTipoEquipamento().toLowerCase().contains(tipo.toLowerCase())) {
                    result.add(cam);
                }
            }
        }
        return result;
    }

    public List<String> getLocaisComCamera() {
        Set<String> locais = new LinkedHashSet<>();
        for (Camera cam : cameras) {
            String local = cam.getLocal();
            if (local != null && !local.isEmpty() && !local.contains("DHCP") && !local.contains("gateway")) {
                locais.add(local);
            }
        }
        return new ArrayList<>(locais);
    }

    public void addCamera(Camera camera) {
        if (camera.getId() == 0) {
            camera.setId(getNextId());
        }
        cameras.add(camera);
        saveCameras();
    }

    public void updateCamera(Camera camera) {
        for (int i = 0; i < cameras.size(); i++) {
            if (cameras.get(i).getId() == camera.getId()) {
                cameras.set(i, camera);
                saveCameras();
                return;
            }
        }
    }

    public void deleteCamera(int id) {
        cameras.removeIf(cam -> cam.getId() == id);
        saveCameras();
    }

    public int getNextId() {
        return cameras.stream().mapToInt(Camera::getId).max().orElse(0) + 1;
    }
}
