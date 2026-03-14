document.addEventListener("DOMContentLoaded", function() {
    console.log("CNPJ Autofill script loaded.");
    
    var cnpjField = document.getElementById("id_cnpj");

    if (!cnpjField) {
        console.log("CNPJ field not found.");
        return;
    }

    var helpText = document.createElement("span");
    helpText.className = "help-block";
    helpText.id = "cnpj-help-text";
    helpText.style.cssText = "color: #666; margin-left: 10px; font-weight: bold;";
    cnpjField.parentNode.insertBefore(helpText, cnpjField.nextSibling);

    cnpjField.addEventListener("input", handleInputChange);
    cnpjField.addEventListener("blur", handleInputChange);

    function handleInputChange() {
        var value = cnpjField.value.replace(/[^\d]/g, "");

        // Apply basic mask: 00.000.000/0000-00
        if (value.length > 0) {
            var maskedValue = value;
            if (value.length > 2) maskedValue = value.substring(0, 2) + "." + value.substring(2);
            if (value.length > 5) maskedValue = maskedValue.substring(0, 6) + "." + value.substring(5);
            if (value.length > 8) maskedValue = maskedValue.substring(0, 10) + "/" + value.substring(8);
            if (value.length > 12) maskedValue = maskedValue.substring(0, 15) + "-" + value.substring(12, 14);
            
            if (cnpjField.value !== maskedValue && maskedValue.length <= 18) {
                cnpjField.value = maskedValue;
            }
        }

        if (value.length === 14) {
            // Only fetch if we haven't just fetched
            if (helpText.textContent.indexOf("Buscando") !== -1 || helpText.textContent.indexOf("encontrados") !== -1) {
                return;
            }
            
            helpText.textContent = "⏳ Buscando informações do CNPJ...";
            
            fetch("https://brasilapi.com.br/api/cnpj/v1/" + value)
                .then(function(response) {
                    if (!response.ok) {
                        throw new Error("CNPJ não encontrado na Receita Federal");
                    }
                    return response.json();
                })
                .then(function(data) {
                    helpText.textContent = "✅ Dados encontrados!";
                    helpText.style.color = "green";
                    
                    var fields = {
                        "id_nome": data.razao_social || data.nome_fantasia || "",
                        "id_email": data.email ? data.email.toLowerCase() : "",
                        "id_telefone": data.ddd_telefone_1 || ""
                    };

                    for (var id in fields) {
                        var el = document.getElementById(id);
                        if (el && !el.value) {
                            el.value = fields[id];
                        }
                    }

                    var enderecoEl = document.getElementById("id_endereco");
                    if (enderecoEl && !enderecoEl.value && data.logradouro) {
                        var endereco = data.logradouro;
                        if (data.numero) endereco += ", " + data.numero;
                        if (data.complemento) endereco += " - " + data.complemento;
                        if (data.bairro) endereco += "\n" + data.bairro;
                        if (data.municipio && data.uf) endereco += "\n" + data.municipio + " - " + data.uf;
                        if (data.cep) endereco += "\nCEP: " + data.cep;
                        
                        enderecoEl.value = endereco;
                    }
                    
                    setTimeout(function() {
                        if (helpText.textContent === "✅ Dados encontrados!") {
                            helpText.textContent = "";
                        }
                    }, 4000);
                })
                .catch(function(error) {
                    console.error(error);
                    helpText.textContent = "❌ " + error.message;
                    helpText.style.color = "red";
                });
        } else if (value.length > 0 && value.length < 14) {
            helpText.textContent = "";
            helpText.style.color = "#666";
        }
    }
});
