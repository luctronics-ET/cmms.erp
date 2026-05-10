package tratamento;

import java.util.List;
import javax.faces.application.FacesMessage;
import javax.faces.bean.ManagedBean;
import javax.faces.bean.ManagedProperty;
import javax.faces.bean.RequestScoped;
import javax.faces.context.FacesContext;

@ManagedBean(name = "camerasBean")
@RequestScoped
public class CamerasBean {
    @ManagedProperty(value = "#{cameraManager}")
    private CameraManager cameraManager;

    private Camera selectedCamera;
    private String selectedLocal = "";
    private String newIPValue = "";
    private String filterTipo = "";

    public List<Camera> getCameras() {
        if (cameraManager == null) return java.util.Collections.emptyList();
        return cameraManager.getCameras();
    }

    public List<Camera> getCamerasFiltradas() {
        if (cameraManager == null) return java.util.Collections.emptyList();
        if (filterTipo == null || filterTipo.isEmpty()) {
            return cameraManager.getCameras();
        }
        return cameraManager.getCamerasByTipo(filterTipo);
    }

    public List<String> getLocaisComCamera() {
        if (cameraManager == null) return java.util.Collections.emptyList();
        return cameraManager.getLocaisComCamera();
    }

    public void selectCamera(Camera camera) {
        this.selectedCamera = new Camera(camera.getId(), camera.getIp(), camera.getLocal(),
                camera.getTipoEquipamento(), camera.getMarca(), camera.getModelo(), camera.getMac());
    }

    public void saveCameraEdit() {
        if (selectedCamera != null && cameraManager != null) {
            cameraManager.updateCamera(selectedCamera);
            addMessage("Câmera atualizada com sucesso", FacesMessage.SEVERITY_INFO);
            selectedCamera = null;
        }
    }

    public void cancelEdit() {
        selectedCamera = null;
    }

    public void changeIPByLocal() {
        if (cameraManager == null) {
            addMessage("Manager não inicializado", FacesMessage.SEVERITY_ERROR);
            return;
        }
        if (selectedLocal == null || selectedLocal.isEmpty()) {
            addMessage("Selecione um local", FacesMessage.SEVERITY_WARN);
            return;
        }
        if (newIPValue == null || newIPValue.isEmpty()) {
            addMessage("Digite um IP", FacesMessage.SEVERITY_WARN);
            return;
        }

        Camera cam = cameraManager.getCameraByLocal(selectedLocal);
        if (cam != null) {
            cam.setIp(newIPValue);
            cameraManager.updateCamera(cam);
            addMessage("IP alterado para " + newIPValue, FacesMessage.SEVERITY_INFO);
            newIPValue = "";
        } else {
            addMessage("Câmera não encontrada", FacesMessage.SEVERITY_WARN);
        }
    }

    private void addMessage(String text, String severity) {
        FacesContext context = FacesContext.getCurrentInstance();
        if (context != null) {
            context.addMessage(null, new FacesMessage(severity, text, ""));
        }
    }

    // Getters e Setters
    public CameraManager getCameraManager() { return cameraManager; }
    public void setCameraManager(CameraManager cameraManager) { this.cameraManager = cameraManager; }

    public Camera getSelectedCamera() { return selectedCamera; }
    public void setSelectedCamera(Camera selectedCamera) { this.selectedCamera = selectedCamera; }

    public String getSelectedLocal() { return selectedLocal; }
    public void setSelectedLocal(String selectedLocal) { this.selectedLocal = selectedLocal; }

    public String getNewIPValue() { return newIPValue; }
    public void setNewIPValue(String newIPValue) { this.newIPValue = newIPValue; }

    public String getFilterTipo() { return filterTipo; }
    public void setFilterTipo(String filterTipo) { this.filterTipo = filterTipo; }
}
