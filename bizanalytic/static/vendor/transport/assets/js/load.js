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
        let client_nm = $("#client_nm").val();
        let cp_nm = $("#company_nm").val();
        let email_nm = $("#email_nm").val();
        var fileName_b = $("#route_fl").val();
        var file_b = $('#route_fl')[0].files[0];

        let url = "https://bizanalytic.com/logiflex/reports/sample-report-create/";
        const formData = new FormData();
        if (fileName_b && email_nm && cp_nm && client_nm){
            formData.append('client_nm', client_nm);
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
        }else{
                let message = 'You need to fill all the required information';
            $("#report-message").html('<div class="alert alert-danger d-flex align-items-center" role="alert"><svg class="bi flex-shrink-0 me-2" width="24" height="24" role="img" aria-label="Success:"><use xlink:href="#check-circle-fill"/></svg><div>' +
                                    message + '</div>')
            }


    });


$("#request_call").click(function (){
        let cp_nm = $("#company_nm").val();
        let email_nm = $("#email_nm").val();
        let client_nm = $("#client_nm").val();
        let phone_nb = $("#phone_nb").val();
        let agree_call = "2";
        if ($("#agree_call").prop("checked")){
             agree_call = "1";
         }
        let url = "https://bizanalytic.com/logiflex/bookcall/";
        const formData = new FormData();
        if(agree_call == "1") {
            if (client_nm && email_nm && cp_nm && phone_nb) {
                formData.append('cp_nm', cp_nm);
                formData.append('email_nm', email_nm);
                formData.append('client_nm', client_nm);
                formData.append('phone_nb', phone_nb);
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
                            if (message) {
                                $("#report-message").html('<div class="alert alert-success d-flex align-items-center" role="alert"><svg class="bi flex-shrink-0 me-2" width="24" height="24" role="img" aria-label="Success:"><use xlink:href="#check-circle-fill"/></svg><div>' +
                                    message + '</div>')
                            }
                        }
                    }
                })
            }else{
                let message = 'You need to fill all the required information';
            $("#report-message").html('<div class="alert alert-danger d-flex align-items-center" role="alert"><svg class="bi flex-shrink-0 me-2" width="24" height="24" role="img" aria-label="Success:"><use xlink:href="#check-circle-fill"/></svg><div>' +
                                    message + '</div>')
            }
        }else {
            let message = 'You need to check first the "Agree to receive a call" option';
            $("#report-message").html('<div class="alert alert-danger d-flex align-items-center" role="alert"><svg class="bi flex-shrink-0 me-2" width="24" height="24" role="img" aria-label="Success:"><use xlink:href="#check-circle-fill"/></svg><div>' +
                                    message + '</div>')
        }


    });

$("#generate_full_rp").click(function (){
        let client_nm = $("#client_nm").val();
        let cp_nm = $("#company_nm").val();
        let email_nm = $("#email_nm").val();
        var fileName_b = $("#route_fl").val();
        var file_b = $('#route_fl')[0].files[0];
        // let cixphoto = $('#ci-x-photo').val();
        let agree_create = "2";
        if ($("#agree_create").prop("checked")){
             agree_create = "1";
         }
        if(agree_create == "1") {

            let url = "https://bizanalytic.com/logiflex/reports/full-report-create/";
            // let url = "https://bizanalytic.com/logiflex/clean-csv/";
            console.log(url);
            const formData = new FormData();

            if (fileName_b && email_nm && cp_nm && client_nm) {
                $("#loadingstate").show();
                $("#report-message").hide();
                formData.append('client_nm', client_nm);
                formData.append('cp_nm', cp_nm);
                formData.append('email_nm', email_nm);
                formData.append('route_file', file_b);
                formData.append('filename', fileName_b);
                $.ajax({
                    type: 'POST',
                    url: url,
                    data: formData,
                    processData: false,
                    contentType: false,
                    headers: {'X-CSRFToken': $('input[name=csrfmiddlewaretoken]').val(),
                              },
                    success: function (data) {
                        if (data) {
                            var result = data;
                            var message = result.submessage;
                            $("#loadingstate").hide();
                            if (message) {
                                $("#report-message").html('<div class="alert alert-success d-flex align-items-center" role="alert"><svg class="bi flex-shrink-0 me-2" width="24" height="24" role="img" aria-label="Success:"><use xlink:href="#check-circle-fill"/></svg><div>' +
                                    message + '</div>');
                                $("#report-message").show();
                                var toastElList = [].slice.call(document.querySelectorAll('.toast'))
                                var toastList = toastElList.map(function (toastEl) {
                                  return new bootstrap.Toast(toastEl, option)
                                })
                            }
                        }
                    }
                })
            } else {
                let message = 'You need to fill all the required information';
                $("#report-message").html('<div class="alert alert-danger d-flex align-items-center" role="alert"><svg class="bi flex-shrink-0 me-2" width="24" height="24" role="img" aria-label="Success:"><use xlink:href="#check-circle-fill"/></svg><div>' +
                    message + '</div>')
            }
        }else{
            let message = 'You need to check first the "Agree to Create a Full Report" option';
            $("#report-message").html('<div class="alert alert-danger d-flex align-items-center" role="alert"><svg class="bi flex-shrink-0 me-2" width="24" height="24" role="img" aria-label="Success:"><use xlink:href="#check-circle-fill"/></svg><div>' +
                                    message + '</div>')
        }

    });