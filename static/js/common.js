function setWait() { $("body").addClass("loading"); }
function unsetWait() { $("body").removeClass("loading"); }

function ajaxGet(url, datas, target, modal_target)
{
    setWait();
    $.ajax({
        url : url,
        type : 'GET',
        data : datas,
        cache : false,
        dataType : 'html',
        beforeSend : function(){},
        success : function(data){
            if (modal_target != "")
            {
                if (data != "")
                {
                    $('#'+modal_target+"-body").html(data);
                    $('#'+modal_target).modal('show');
                }
            }
            else
                if (target != "")
                    $('#'+target).html(data);
        },
        error : function(e){alert("Error: "+e.responseText);},
        complete : function(){unsetWait();}
        //complete : function(){$("body").css("cursor", "default"); $("body").removeClass("loading-");}
    });
};

function ajaxGetAppend(url, datas, target, modal_target)
{
    $("body").css("cursor", "progress");
    $.ajax({
        url : url,
        type : 'GET',
        data : datas,
        cache : false,
        dataType : 'html',
        beforeSend : function(){},
        success : function(data){
            if (modal_target != "")
            {
                $('#'+modal_target+"-body").append(data);
                $('#'+modal_target).modal('show');
            }
            else
                if (target != "")
                    $('#'+target).append(data);
        },
        error : function(e){alert("Error: "+e.responseText);},
        complete : function(){$("body").css("cursor", "default");}
    });
};

function ajaxGetAutosave(url, datas, target)
{
    $("body").css("cursor", "progress");
    $.ajax({
        url : url,
        type : 'GET',
        data : datas,
        dataType : 'html',
        cache : false,
        beforeSend : function(){},
        success : function(data){
            $("#"+target).html(data).show().fadeTo(5000, 500).slideUp(500, function(){
                $("#"+target).slideUp(500);
            });
        },
        error : function(e){alert("Error: "+e.responseText);},
        complete : function(){$("body").css("cursor", "default");}
    }); 
};

function ajaxGetEnabled(url, datas, target, modal_target, obj)
{
    $("body").css("cursor", "progress");
    $.ajax({
        url : url,
        type : 'GET',
        data : datas,
        cache : false,
        dataType : 'html',
        beforeSend : function(){},
        success : function(data){
            if (modal_target != "")
            {
                if (data != "")
                {
                    $('#'+modal_target+"-body").html(data);
                    $('#'+modal_target).modal('show');
                }
            }
            else
                if (target != "")
                    $('#'+target).html(data);
            obj.prop("disabled", "")
        },
        error : function(e){alert("Error: "+e.responseText);},
        complete : function(){$("body").css("cursor", "default");}
    });
};

function ajaxGetSearchMed(url, datas, target_prefix1, target_prefix2)
{
    setWait();
    $.ajax({
        url : url,
        type : 'GET',
        data : datas,
        cache : false,
        dataType : 'json',
        beforeSend : function(){},
        success : function(data){
            //console.log(data);
            let expiration_date =""
            try{
                expiration_date = `20${data.expiration_date.substring(0,2)}-${data.expiration_date.substring(2,4)}-${data.expiration_date.substring(4,2)}`
            }catch{}

            $("#"+target_prefix1+"_"+data.pdm_id).val(data.batch_code).change();
            $("#"+target_prefix2+"_"+data.pdm_id).val(expiration_date).change();
        },
        error : function(e){alert("Error: "+e.responseText);},
        complete : function(){unsetWait();}
    });
};


function ajaxPostAutosave(url, datas, target)
{
    $("body").css("cursor", "progress");
    $.ajax({
        url : url,
        type : 'POST',
        data : datas,
        dataType : 'html',
        cache : false,
        beforeSend : function(){},
        success : function(data){
            $("#"+target).html(data).show().fadeTo(5000, 500).slideUp(500, function(){
                $("#"+target).slideUp(500);
            });
        },
        error : function(e){alert("Error: "+e.responseText);},
        complete : function(){$("body").css("cursor", "default");}
    }); 
};


function ajaxGetRemove(url, datas, target)
{
    $.ajax({
        url : url,
        type : 'GET',
        data : datas,
        cache : false,
        dataType : 'html',
        beforeSend : function(){},
        success : function(data){
            if(data != "")
                $('#'+target).html(data);
            else
                $('#'+target).remove();
        },
        error : function(e){alert("Error: "+e.responseText);},
        complete : function(){}
    }); 
};

function autoSearch(obj, num_rows=0)
{
    url = obj.data("url");
    target = obj.data("target");
    datas = {'num_rows': num_rows,};
    if (obj.data("related"))
    {
        related = obj.data("related").split(",");
        for(i in related)
        {
            key = $("#"+related[i]).attr('name');
            value = $("#"+related[i]).val();
            datas[key] = value;
        }
    }
    if (obj.data("append"))
        ajaxGetAppend(url, datas, target, '');
    else
        ajaxGet(url, datas, target, '');
}

function uploadObjFile(obj, url, target, obj_id, field, token)
{
    var data = new FormData();
    data.append("file", obj[0].files[0]);
    data.append('obj_id', obj_id);
    data.append('field', field);
    data.append("csrfmiddlewaretoken", token);

    $.ajax({
        url: url,
        data: data,
        cache: false,
        contentType: false,
        processData: false,
        type: 'post',
        success: function (data) {
            $('#'+target).html(data);
            //$('#'+target).trigger('create');
        },
        error : function(e){alert("Error: "+e.responseText);},
    });
}

function submitForm(frm, target)
{
    setWait();
    $.ajax({
        url: frm.attr('action'),
        type: frm.attr('method'),
        data: frm.serialize(),
        success: function (data) {
            $('#'+target).html(data);
        },
        error: function (data) { alert("Error: "+data.responseText); },
        complete : function(){unsetWait();}
        //complete : function(){$("body").css("cursor", "default");}
    });
}

function uploadMulti(obj, url, target, obj_id, field, folder, token)
{
    var data = new FormData();
    $.each(obj[0].files, function(i, file) {
        data.append("file", file);
    });
    data.append('obj_id', obj_id);
    data.append('field', field);
    data.append('folder', folder);
    data.append("csrfmiddlewaretoken", token);

    $.ajax({
        url: url,
        data: data,
        cache: false,
        contentType: false,
        processData: false,
        type: 'post',
        success: function (data) {
            if (target.indexOf("alert") >= 0)
            {
                $("#"+target).html(data).fadeTo(5000, 500).slideUp(500, function(){
                    $("#"+target).slideUp(500);
                });
            }
            else
            {
                $('#'+target).html(data);
				$('#'+target).trigger('create');
            }
        },
        error : function(e){alert("Error: "+e.responseText);},
    });
}

function closeWin(divName)
{
    setTimeout(function(){
        $(divName).fadeOut('slow');
        setTimeout(function(){
            //window.history.back();
            history.go(-1);
            window.close();
        }, 300);
    }, 2000);
    return false;
}

function closeModal(divName)
{
    setTimeout(function(){
        $(divName).modal('hide');
        setTimeout(function(){
            $('body').removeClass('modal-open');
            $('.modal-backdrop').remove();
        }, 100);
    }, 200);
    return false;
}

function validateField(field)
{
    msg_id = "#" + field.attr("id") + "__msg";
    if (field[0].checkValidity())
    {
        $(msg_id).html("");
        field.removeClass("invalid");
        return true;
    }
    else
    {
        $(msg_id).html("this field is required");
        field.removeClass("valid").addClass("invalid");
        return false;
    }
}

function validateFields(validate_class)
{
    valid = true;
    $("."+validate_class).each(function(){
        if ($(this).data("check"))
        {
            if (!$(this)[0].checkValidity() && !$("#"+$(this).data("check"))[0].checkValidity())
            {
                valid = false;
                validateField($(this));
                validateField($("#"+$(this).data("check")));
            }
        }
        else
            if (!validateField($(this)))
                valid = false;
    });
    return valid;
}

function validateCheckIn()
{
    var ini_date = $("#check_in").val();
    var ini_time = $("#check_in_time").val();
    var end_date = $("#check_out").val();
    var end_time = $("#check_out_time").val();
    var ini = new Date(ini_date+"T"+ini_time)
    var end = new Date(end_date+"T"+end_time)
    if (end < ini)
    {
        $("#check_out__msg").html("This date must be greater than check in");
        field.removeClass("valid").addClass("invalid");
        return false;
    }
    return true;
}

function pushHistory(url) { history.pushState({}, 'main', window.location.href); }

function showAlert(body, close) {
    var text="<p>"+body+"</p><div class='text-end'><button type='button' class='btn btn-marine' data-bs-dismiss='modal'>"+close+"</button></div>";
    $('#common-modal-body').html(text);
    $('#common-modal').modal('show');
}

function activeEditor(obj) {
    var id = obj.attr("id");
    var ref = obj.data("ref");
    CKEDITOR.replace(id).on('change', function(){$("#"+ref).html(this.getData()).change();});
}

$(document).ready(()=>{
    $("body").on("keyup", ".autosearch", function(e){
        var obj = $(this);
        setTimeout(function(){
            autoSearch(obj);
        }, 1000);
        e.preventDefault();
    });

    $("body").on("change", ".autosearch_change", function(e){
        var obj = $(this);
        autoSearch(obj);
        e.preventDefault();
    });

    $("body").on("click", ".ark", function(e){
        var obj = $(this);
        if (((obj.data("confirm")) && confirm(obj.data("confirm"))) || !(obj.data("confirm")))
        {
            url = obj.data("url");
            var target = "";
            var target_modal = "";
            if (obj.data("target"))
                target = obj.data("target");
            if (obj.data("target-modal"))
                target_modal = obj.data("target-modal");

            var datas = {};
            var args = obj.data();
            for(var i in args)
                if (i != "url")
                    datas[i] = args[i]
            ajaxGet(url, datas, target, target_modal);
            if (obj.data("show"))
                $("#" + obj.data("show")).show();
            if (obj.data("hide"))
                $("#" + obj.data("hide")).hide();

            e.preventDefault();
            e.stopImmediatePropagation();
        }
    });

    $("body").on("click", ".ark-append", function(e){
        var obj = $(this);
        if (((obj.data("confirm")) && confirm(obj.data("confirm"))) || !(obj.data("confirm")))
        {
            url = obj.data("url");
            var target = "";
            var target_modal = "";
            if (obj.data("target"))
                target = obj.data("target");
            if (obj.data("target-modal"))
                target_modal = obj.data("target-modal");

            var datas = {};
            var args = obj.data();
            for(var i in args)
                if (i != "url")
                    datas[i] = args[i]
            ajaxGetAppend(url, datas, target, target_modal);
            if (obj.data("show"))
                $("#" + obj.data("show")).show();
            if (obj.data("hide"))
                $("#" + obj.data("hide")).hide();
            e.preventDefault();
        }
    });

    $("body").on("click", ".ark-disabled", function(e){
        var obj = $(this);
        if (((obj.data("confirm")) && confirm(obj.data("confirm"))) || !(obj.data("confirm")))
        {
            obj.prop("disabled", "disabled");
            url = obj.data("url");
            var target = "";
            var target_modal = "";
            if (obj.data("target"))
                target = obj.data("target");
            if (obj.data("target-modal"))
                target_modal = obj.data("target-modal");

            var datas = {};
            var args = obj.data();
            for(var i in args)
                if (i != "url")
                    datas[i] = args[i]
            ajaxGetEnabled(url, datas, target, target_modal, obj);
            if (obj.data("show"))
                $("#" + obj.data("show")).show();
            if (obj.data("hide"))
                $("#" + obj.data("hide")).hide();

            e.preventDefault();
            e.stopImmediatePropagation();
        }
    });


    $("body").on("change", ".ark_change", function(e){
        var obj = $(this);
        if (((obj.data("confirm")) && confirm(obj.data("confirm"))) || !(obj.data("confirm")))
        {
            var url = obj.data("url");
            var value = obj.val();
            var target = "";
            var target_modal = "";
            if (obj.data("target"))
                target = obj.data("target");
            if (obj.data("target-modal"))
                target_modal = obj.data("target-modal");

            var datas = {'value': value};
            var args = obj.data();
            for(var i in args)
                if (i != "url")
                    datas[i] = args[i]
            ajaxGet(url, datas, target, target_modal);

            if (obj.data("clear"))
                clearHtml($("#" + obj.data("clear")));
            if (obj.data("show"))
                $("#" + obj.data("show")).show();
            e.preventDefault();
        }
    });

    $("body").on("click", ".ark-validate", function(e){
        var obj = $(this);
        var validate_check_in = true;
        if (obj.data("check_in"))
            validate_check_in = validateCheckIn();
        if (validateFields(obj.data("validate")) && validate_check_in)
        {
            url = obj.data("url");
            var target = "";
            var target_modal = "";
            if (obj.data("target"))
                target = obj.data("target");
            if (obj.data("target-modal"))
                target_modal = obj.data("target-modal");

            var datas = {};
            var args = obj.data();
            for(var i in args)
                if (i != "url")
                    datas[i] = args[i]
            ajaxGet(url, datas, target, target_modal);
            if (obj.data("show"))
                $("#" + obj.data("show")).show();

            closeModal("#"+obj.data("modal"));
            e.preventDefault();
            e.stopImmediatePropagation();
        }
    });

    $("body").on("change", ".autosave", function(e){
        var obj = $(this);
        msg_id = "#" + obj.attr("id") + "__msg";
        if (obj[0].checkValidity())
        {
            $(msg_id).html("");
            obj.removeClass("invalid");
        }
        else
        {
            $(msg_id).html(obj.attr("title"));
            obj.removeClass("valid").addClass("invalid");
        }

        model_name = obj.data("model-name");
        obj_id = obj.data("obj-id");
        url = obj.data("url");
        target = obj.data("target");
        field = obj.attr("name");
        if (obj.data("ref-field"))
            ref_field = obj.data("ref-field");
        else
            ref_field = "pk";

        if (obj.data("bool"))
            if (obj.data("bool") == "False")
                if (obj.is(':checked'))
                    value = "False";
                else
                    value = "True";
            else
                if (obj.is(':checked'))
                    value = "True";
                else
                    value = "False";
        else
            value = obj.val();

        datas = {'model_name': model_name, 'obj_id': obj_id, 'field': field, 'value': value, "ref_field":ref_field};
        if (obj.data('lang'))
            datas['lang'] = obj.data('lang');
        ajaxGetAutosave(url, datas, target);
        e.preventDefault();
    });

    $("body").on("change", ".autosavepost", function(e){
        var obj = $(this);
        msg_id = "#" + obj.attr("id") + "__msg";
        if (obj[0].checkValidity())
        {
            $(msg_id).html("");
            obj.removeClass("invalid");
        }
        else
        {
            $(msg_id).html(obj.attr("title"));
            obj.removeClass("valid").addClass("invalid");
        }

        model_name = obj.data("model-name");
        obj_id = obj.data("obj-id");
        url = obj.data("url");
        target = obj.data("target");
        field = obj.attr("name");
        if (obj.data("ref-field"))
            ref_field = obj.data("ref-field");
        else
            ref_field = "pk";

        if (obj.data("bool"))
            if (obj.is(':checked'))
                value = "True";
            else
                value = "False";
        else
            value = obj.val();

        datas = {'model_name': model_name, 'obj_id': obj_id, 'field': field, 'value': value, "ref_field":ref_field};
        if (obj.data('lang'))
            datas['lang'] = obj.data('lang');
        ajaxPostAutosave(url, datas, target);
        e.preventDefault();
    });

    $("body").on("click", ".autoremove", function(e){
        if (confirm("Esta seguro/a de que desea borrar el elemento?"))
        {
            model_name = $(this).data("model-name");
            obj_id = $(this).data("obj-id");
            url = $(this).data("url");
            target = $(this).data("target");
            datas = {'model_name': model_name, 'obj_id': obj_id};
            ajaxGetRemove(url, datas, target);
            if ($(this).data("hide"))
                $("#" + $(this).data("hide")).hide();
            e.preventDefault();
        }
    });

    $("body").on("change", ".upload", function(e){
        var obj = $(this);
        var url = obj.data("url");
        var target = obj.data("target");
        var obj_id = obj.data("obj-id");
        var field = "";
        if (obj.data("field"))
            field = obj.data("field");
        var token = obj.data("csrf-token");
        uploadObjFile(obj, url, target, obj_id, field, token);
        e.preventDefault();
    });

    $("body").on("click", ".saveform", function(e){
        var obj = $(this);
        if (((obj.data("confirm")) && confirm(obj.data("confirm"))) || !(obj.data("confirm")))
        {
            form_id = $(this).data("form");
            frm = $('#'+form_id);
            target = $(this).data("target");
            submitForm(frm, target);
            if (obj.data("update"))
                $("#"+obj.data("update")).html($("#"+obj.data("update-val")).val())
            e.preventDefault();
        }
    });

    $("body").on("change", ".multiupload", function(e){
        var obj = $(this);
        var url = obj.data("url");
        var target = obj.data("target");
        var obj_id = obj.data("obj-id");
        var field = obj.data("field");
        var folder = obj.data("folder");
        var token = obj.data("csrf-token");
        uploadMulti(obj, url, target, obj_id, field, folder, token);
        e.preventDefault();
    });

    $("body").on("keyup", ".autocomplete", function(e){
        url = $(this).data("url");
        target = $(this).data("target");
        obj_id = $(this).data("obj_id");
        value = $(this).val()
        datas = {'obj_id': obj_id, 'value': value};
        ajaxGet(url, datas, target, '');
        if ($(this).data("show"))
            $("#" + $(this).data("show")).show();
        e.preventDefault();
    });

    $("body").on("keypress", ".ark_intro", function(e){
        var obj = $(this);
        if(e.which == 13) {
            url = obj.data("url");
            target = obj.data("target");
            value = obj.val();

            var datas = {};
            var args = obj.data();
            for(var i in args)
                if (i != "url")
                    datas[i] = args[i]
            datas['value'] = value;
            ajaxGet(url, datas, target, '');
            obj.val("");
            e.preventDefault();
        }
    });

    $("body").on("click", ".toggle-editor", function(e){
        var editor = $(this).data("editor");
        var source = $(this).data("source");
        $("#editor").toggle();
        $("#source").toggle();
        $(".ql-toolbar").toggle();
        if ($(this).html().indexOf("html") == -1)
            $(this).html("html");
        else
            $(this).html("editor");
        e.preventDefault();
    });

    $("body").on("click", ".toggle-btn", function(e){
        var obj = $(this);
        var target = obj.data("target");
        var text = obj.data("text");
        var textAlt = obj.data("text-alt");

        $("#"+target).slideToggle();
        if (obj.data("id-change"))
            $("#"+$(obj.data("id-change"))).html(obj.html() == textAlt ? text : textAlt);
        else
            obj.html(obj.html() == textAlt ? text : textAlt);
        if (obj.data("set-focus"))
            $("#"+obj.data("set-focus")).focus()
    });

    $("body").on("click", ".toggle-tags", function(e){
        var class_name = $(this).data("class-name");
        if ($(this).is(":checked"))
        {
            $("."+class_name).prop("disabled", true);
            $(this).prop("disabled", false);
        }
        else
            $("."+class_name).prop("disabled", false);
    });

    $("body").on("click", ".toggle-edit", function(e){
        var obj = $(this);
        var class_name = obj.data("class-name");
        var text = obj.data("text");
        var textAlt = obj.data("text-alt");

        if (obj.html() == textAlt)
        {
            obj.html(text);
            $("."+class_name).prop("disabled", "disabled");
            $("."+class_name).addClass("view");
        }
        else
        {
            obj.html(textAlt);
            $("."+class_name).prop("disabled", "");
            $("."+class_name).removeClass("view");
        }
    });

    $("body").on("click", ".sh-accordion", function(e){
        var obj = $(this);
        $("#"+obj.data("accordion-id")).slideToggle();
        obj.find('i').toggleClass('fa-chevron-down fa-chevron-up')
    });

    $("body").on("click", ".check-row", function(e){
        var active = $(this).data("active");
        var row = $(this).data("row");
        if (active != "")
        {
            $("."+row).hide();
            $("."+row).each(function(){
                if ($(this).data("active") == active)
                    $(this).show();
            });
        }
        else
            $("."+row).show();

    });

    $("body").on("keyup", ".front-search", function(e){
        var value = $(this).val();
        var row = $(this).data("row-class");
        if(value == "")
            $("."+row).show();
        else
        {
            $("."+row).each(function(){
                var id = $(this).attr("id");
                if (id.indexOf(value.toUpperCase()) != -1)
                    $(this).show();
                else
                    $(this).hide();
            });
        }
    });

});


