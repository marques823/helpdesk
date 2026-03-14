(function($) {
    // We use jQuery since Django admin provides it natively in django.jQuery
    var $jq = django.jQuery || jQuery;

    $jq(document).ready(function() {
        var $cnpjField = $jq("#id_cnpj");

        if ($cnpjField.length === 0) {
            return;
        }

        // Add a message container to show loading/error
        var $helpText = $jq('<span class="help-block" id="cnpj-help-text" style="color: #666; margin-left: 10px; font-weight: bold;"></span>');
        $cnpjField.after($helpText);

        $cnpjField.on("input blur", function() {
            var el = $jq(this);
            var value = el.val().replace(/[^\d]/g, "");

            // Apply basic mask: 00.000.000/0000-00
            if (value.length > 0) {
                var maskedValue = value;
                if (value.length > 2) maskedValue = value.substring(0, 2) + "." + value.substring(2);
                if (value.length > 5) maskedValue = maskedValue.substring(0, 6) + "." + value.substring(5);
                if (value.length > 8) maskedValue = maskedValue.substring(0, 10) + "/" + value.substring(8);
                if (value.length > 12) maskedValue = maskedValue.substring(0, 15) + "-" + value.substring(12, 14);
                
                if (el.val() !== maskedValue && maskedValue.length <= 18) {
                    el.val(maskedValue);
                }
            }

            if (value.length === 14) {
                // Fetch basic data
                $helpText.text("⏳ Buscando informações do CNPJ...");
                
                fetch("https://brasilapi.com.br/api/cnpj/v1/" + value)
                    .then(response => {
                        if (!response.ok) {
                            throw new Error("CNPJ não encontrado ou erro na API");
                        }
                        return response.json();
                    })
                    .then(data => {
                        $helpText.text("✅ Dados encontrados!");
                        $helpText.css("color", "green");
                        
                        // Fill nome
                        if (!$jq("#id_nome").val()) {
                            $jq("#id_nome").val(data.razao_social || data.nome_fantasia || "");
                        }
                        
                        // Fill email
                        if (!$jq("#id_email").val() && data.email) {
                            $jq("#id_email").val(data.email.toLowerCase());
                        }

                        // Fill telefone
                        if (!$jq("#id_telefone").val() && data.ddd_telefone_1) {
                            $jq("#id_telefone").val(data.ddd_telefone_1);
                        }

                        // Fill endereco combining parts
                        if (!$jq("#id_endereco").val() && data.logradouro) {
                            var endereco = data.logradouro;
                            if (data.numero) endereco += ", " + data.numero;
                            if (data.complemento) endereco += " - " + data.complemento;
                            if (data.bairro) endereco += "\n" + data.bairro;
                            if (data.municipio && data.uf) endereco += "\n" + data.municipio + " - " + data.uf;
                            if (data.cep) endereco += "\nCEP: " + data.cep;
                            
                            $jq("#id_endereco").val(endereco);
                        }
                        
                        // Fade out the success message after 3 seconds
                        setTimeout(function() {
                            if ($helpText.text() === "✅ Dados encontrados!") {
                                $helpText.text("");
                            }
                        }, 3000);
                    })
                    .catch(error => {
                        console.error(error);
                        $helpText.text("❌ " + error.message);
                        $helpText.css("color", "red");
                    });
            } else if (value.length > 0 && value.length < 14) {
                $helpText.text("");
                $helpText.css("color", "#666");
            }
        });
    });
})(django.jQuery);
