package tratamento;

public class Camera {
    private int id;
    private String ip;
    private String local;
    private String tipoEquipamento;
    private String marca;
    private String modelo;
    private String mac;

    public Camera() {}

    public Camera(int id, String ip, String local, String tipoEquipamento, String marca, String modelo, String mac) {
        this.id = id;
        this.ip = ip;
        this.local = local;
        this.tipoEquipamento = tipoEquipamento;
        this.marca = marca;
        this.modelo = modelo;
        this.mac = mac;
    }

    public int getId() { return id; }
    public void setId(int id) { this.id = id; }

    public String getIp() { return ip; }
    public void setIp(String ip) { this.ip = ip; }

    public String getLocal() { return local; }
    public void setLocal(String local) { this.local = local; }

    public String getTipoEquipamento() { return tipoEquipamento; }
    public void setTipoEquipamento(String tipoEquipamento) { this.tipoEquipamento = tipoEquipamento; }

    public String getMarca() { return marca; }
    public void setMarca(String marca) { this.marca = marca; }

    public String getModelo() { return modelo; }
    public void setModelo(String modelo) { this.modelo = modelo; }

    public String getMac() { return mac; }
    public void setMac(String mac) { this.mac = mac; }
}
