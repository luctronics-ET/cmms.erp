var vue_instance = new Vue({
    el: "#vue_root",
    data: function () {
        return {
            url_arduino: 'http://192.168.1.8/',
            acionado: false,
            user: "",
            password: "",
            user_to_change: "",
            password_to_change: "",
            password_to_change_confirmation: "",
            max_passwd_size: 10,
            msg_password_big: ""
        };
    },
    mounted() {
        acionado = fetch(this.url_arduino)
            .then((resp) => resp.json())
            .then((resp_json) => {
                this.acionado = resp_json.acionado;
            });
    },
    methods: {
        toggle_ar_condicionado: function () {
            fetch(this.url_arduino + '?USER=' + this.user + '&HASH=' + this.password, { method: "POST" })
                .then((resp) => resp.json())
                .then((resp_json) => {
                    if (this.acionado == resp_json.acionado) {
                        alert("Usuario ou senha incorreto(s)");
                    } else {
                        this.acionado = resp_json.acionado;
                    }
                });
        },
        change_user_password: function () {
            if (this.password_to_change != this.password_to_change_confirmation) {
                alert("Confirmacao de senha nao confere!");
                this.msg_password_big = "";
            } else {
                if (this.password_to_change.length >= this.max_passwd_size) {
                    this.msg_password_big = "Senha deve possuir no maximo 10 caracteres!";
                } else {
                    fetch(this.url_arduino +
                        '?USER=' + this.user +
                        '&HASH=' + this.password +
                        '&NEWUSER=' + this.user_to_change +
                        '&NEWHASH=' + this.password_to_change, { method: "POST" })
                        .then((resp) => resp.json()).then((resp_json) => {
                            this.updated_password = resp_json.updated;
                            if (this.updated_password) {
                                alert("Senha alterada com sucesso!");
                            } else {
                                alert("Usuario ou senha incorreto(s)")
                            }
                        });
                    this.msg_password_big = "";
                }
            }            
        }
    }
});