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

$("#generate_rp").click(function (){
        let cp_nm = $("#company_nm").val();
        let email_nm = $("#email_nm").val();
        var fileName_b = $("#route_fl").val();
        var file_b = $('#route_fl')[0].files[0];
        console.log(fileName_b);

        let url = "https://bizanalytic.com/logiflex/reports/create/";
        const formData = new FormData();
        if (fileName_b && email_nm && cp_nm){
            formData.append('cp_nm', cp_nm);
            formData.append('email_nm', email_nm);
            formData.append('route_file', file_b);
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
                            $("#report-message").html('<div class="alert alert-success d-flex align-items-center" role="alert"><svg class="bi flex-shrink-0 me-2" width="24" height="24" role="img" aria-label="Success:"><use xlink:href="#check-circle-fill"/></svg><div>' +
                                message + '</div>')
                        }
                    }
                }
            })
        }


    });


$("#request_call").click(function (){
        let cp_nm = $("#company_nm").val();
        let email_nm = $("#email_nm").val();
        let client_nm = $("#client_nm").val();

        let url = "https://bizanalytic.com/logiflex/bookcall/";
        const formData = new FormData();
        if (client_nm && email_nm && cp_nm){
            formData.append('cp_nm', cp_nm);
            formData.append('email_nm', email_nm);
            formData.append('client_nm', client_nm);
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
                            $("#report-message").html('<div class="alert alert-success d-flex align-items-center" role="alert"><svg class="bi flex-shrink-0 me-2" width="24" height="24" role="img" aria-label="Success:"><use xlink:href="#check-circle-fill"/></svg><div>' +
                                message + '</div>')
                        }
                    }
                }
            })
        }


    });
