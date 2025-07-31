$("#register_nl").click(function (){
        let cp_name = $("#company_newsletter").val();
        let em_nl = $("#email_newsletter").val();
        let tp_area = "1";
        let url = "https://bizanalytic.com/logiflex/newsletters/subscrib/";
        const formData = new FormData();
        formData.append('cp_name', cp_name);
        formData.append('em_nl', em_nl);
        formData.append('tp_area', tp_area);

        $.ajax({
            type: 'POST',
            url: url,
            data: formData,
            processData: false,
            contentType: false,
            headers: {'X-CSRFToken': $('input[name=csrfmiddlewaretoken]').val()},
            success: function (data) {
                if (data) {
                    var result = data;
                    var message = result.submessage;
                    if(message){
                        $("#alert-message").html('<div class="alert alert-success d-flex align-items-center" role="alert"><svg class="bi flex-shrink-0 me-2" width="24" height="24" role="img" aria-label="Success:"><use xlink:href="#check-circle-fill"/></svg><div>' +
                            message + '</div>')
                    }
                }
            }
        })
    });

