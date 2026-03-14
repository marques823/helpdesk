document.addEventListener("DOMContentLoaded", function() {
    var cnpjField = document.getElementById("id_cnpj");

    if (!cnpjField) {
        return;
    }

    // Remover limite de 14 dígitos do HTML para poder colar o valor formatado com pontuação sem ser cortado pelo browser
    cnpjField.removeAttribute("maxlength");

    var helpText = document.createElement("span");
    helpText.className = "help-block";
    helpText.id = "cnpj-help-text";
    helpText.style.cssText = "color: #666; margin-left: 10px; font-weight: bold;";
    cnpjField.parentNode.insertBefore(helpText, cnpjField.nextSibling);

    // Permitir colar e formatar
    cnpjField.addEventListener("input", handleInputChange);
    cnpjField.addEventListener("blur", handleInputChange);

    // Quando for salvar o formulário, limpar os pontos/traços para o Django aceitar no banco de dados
    var form = cnpjField.form;
    if (form) {
        form.addEventListener("submit", function() {
            cnpjField.value = cnpjField.value.replace(/[^\d]/g, "");
        });
    }

    // Estado da requisição para não engolir chamadas duplicadas
    var isFetching = false;
    var lastFetchedCnpj = "";

    function handleInputChange() {
        var value = cnpjField.value.replace(/[^\d]/g, "");

        // Aplicar máscara: 00.000.000/0000-00
        if (value.length > 0) {
            var maskedValue = value;
            if (value.length > 2) maskedValue = value.substring(0, 2) + "." + value.substring(2);
            if (value.length > 5) maskedValue = maskedValue.substring(0, 6) + "." + value.substring(5);
            if (value.length > 8) maskedValue = maskedValue.substring(0, 10) + "/" + value.substring(8);
            if (value.length > 12) maskedValue = maskedValue.substring(0, 15) + "-" + value.substring(12, 14);
            
            // Atualizar o campo com a máscara (limitando visualmente ao tamanho correto da máscara)
            if (cnpjField.value !== maskedValue && maskedValue.length <= 18) {
                cnpjField.value = maskedValue;
            }
        }

        // Fazer a busca somente se tiver exatos 14 números preenchidos
        if (value.length === 14) {
            if (isFetching || value === lastFetchedCnpj) {
                return;
            }
            
            isFetching = true;
            lastFetchedCnpj = value;
            helpText.textContent = "⏳ Buscando dados do CNPJ...";
            helpText.style.color = "#666";

            // Tentaremos duas APIs, caso uma falhe (ex: uso de adblockers, falha de rede ou queda da API)
            fetch("https://brasilapi.com.br/api/cnpj/v1/" + value)
                .then(function(response) {
                    if (!response.ok) throw new Error("BrasilAPI Error");
                    return response.json();
                })
                .then(function(data) {
                    preencherFormulario({
                        razao_social: data.razao_social || data.nome_fantasia || "",
                        email: data.email || "",
                        telefone: data.ddd_telefone_1 || "",
                        endereco: formatarEnderecoBrasilApi(data)
                    });
                })
                .catch(function(err) {
                    console.warn("BrasilAPI falhou, tentando CNPJ.ws...", err);
                    
                    fetch("https://publica.cnpj.ws/cnpj/" + value)
                        .then(function(res2) {
                            if (!res2.ok) throw new Error("CNPJ não encontrado nas bases públicas ou inválido.");
                            return res2.json();
                        })
                        .then(function(dataWS) {
                            preencherFormulario({
                                razao_social: dataWS.razao_social || dataWS.nome_fantasia || "",
                                email: (dataWS.estabelecimento && dataWS.estabelecimento.email) ? dataWS.estabelecimento.email : "",
                                telefone: (dataWS.estabelecimento && dataWS.estabelecimento.ddd1) ? (dataWS.estabelecimento.ddd1 + dataWS.estabelecimento.telefone1) : "",
                                endereco: formatarEnderecoCnpjWSApi(dataWS)
                            });
                        })
                        .catch(function(errorFinal) {
                            isFetching = false;
                            lastFetchedCnpj = ""; // Permitir tentar novamente
                            helpText.textContent = "❌ Erro: Não foi possível obter os dados (CNPJ inválido ou falha de rede)";
                            helpText.style.color = "red";
                        });
                });
        } else {
            helpText.textContent = "";
            lastFetchedCnpj = "";
        }
    }

    function preencherFormulario(dados) {
        isFetching = false;
        helpText.textContent = "✅ Dados encontrados e preenchidos!";
        helpText.style.color = "green";

        if (dados.razao_social) {
            var elNome = document.getElementById("id_nome");
            if (elNome && !elNome.value) elNome.value = dados.razao_social;
        }

        if (dados.email) {
            var elEmail = document.getElementById("id_email");
            if (elEmail && !elEmail.value) elEmail.value = dados.email.toLowerCase();
        }

        if (dados.telefone) {
            var elTel = document.getElementById("id_telefone");
            if (elTel && !elTel.value) elTel.value = dados.telefone;
        }

        if (dados.endereco) {
            var elEnd = document.getElementById("id_endereco");
            if (elEnd && !elEnd.value) elEnd.value = dados.endereco;
        }

        setTimeout(function() {
            if (helpText.textContent.indexOf("✅") !== -1) {
                helpText.textContent = "";
            }
        }, 5000);
    }

    function formatarEnderecoBrasilApi(data) {
        if (!data.logradouro) return "";
        var endereco = data.logradouro;
        if (data.numero) endereco += ", " + data.numero;
        if (data.complemento) endereco += " - " + data.complemento;
        if (data.bairro) endereco += "\n" + data.bairro;
        if (data.municipio && data.uf) endereco += "\n" + data.municipio + " - " + data.uf;
        if (data.cep) endereco += "\nCEP: " + data.cep;
        return endereco;
    }

    function formatarEnderecoCnpjWSApi(data) {
        if (!data.estabelecimento || !data.estabelecimento.logradouro) return "";
        var e = data.estabelecimento;
        var endereco = e.logradouro;
        if (e.numero) endereco += ", " + e.numero;
        if (e.complemento) endereco += " - " + e.complemento;
        if (e.bairro) endereco += "\n" + e.bairro;
        if (e.cidade && e.estado) endereco += "\n" + e.cidade.nome + " - " + e.estado.sigla;
        if (e.cep) endereco += "\nCEP: " + e.cep;
        return endereco;
    }
});
