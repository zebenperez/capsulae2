function isEmail(email) 
{
	var regex = /^([a-zA-Z0-9_.+-])+\@(([a-zA-Z0-9-])+\.)+([a-zA-Z0-9]{2,4})+$/;
	return regex.test(email);
}

function checkConfirmedPasswd(form)
{
	passwordConfirmed = $("#"+form+ " :input[name='password']").val();
	password = $("#"+form+ " :input[name='password_confirm']").val();
	if (passwordConfirmed == password)
		return true;
	else
		return false;
}


function checkRegisterCondition(form)
{
    var f = `#${form}`;
    var msg = "";
    var isOk = false;
    var requiredFields = ["username", "passwd"]

    $(f).find('input').each(function(){
        if (($(this).prop("name").indexOf('csrf') == -1) && ($(this).prop("name") != "tos"))
            msg += "<br/> El campo " + $(this).prop('title') + " es requirido";
    });
    if ($("#email").val() != $("#email2").val())
        msg += "Los correos electrónicos no coinciden. <br/>";
    if (!$("#tos").prop("checked"))
        msg += "<br/> Debe aceptar las condiciones de uso.";

    if (!isOk)
        $("#div-errors").html(msg);

	/*aceptado = $("#"+form+ " :input[name='acceptconditions']").prop('checked');
	emailConfirmed = $("#"+form+ " :input[name='confirmedemail']").val();
	email = $("#"+form+ " :input[name='email']").val();
	strMsg = "";
	isOk = true;
	if (!aceptado)
	{
		$('.accept_error').show()
		isOk = false;
		strMsg = 'Debe aceptar las condiciones\n';
	}
	if ((email != emailConfirmed) || (!isEmail(email)))
	{
		isOk = false;
		$('.email_error').show();
		strMsg = strMsg + 'Error en los emails';
	}*/
    console.log(isOk);
	return (isOk);
}

function search_class(input_field, byclass)
{
	value_to_search = $('#' + input_field).val();
	if ((value_to_search.length) >= 3)
	{
		$("div." + byclass).parentsUntil("tr").hide();
		$("div." + byclass + ":contains('"+value_to_search+"')").parentsUntil("tr").show();
	}
	else
	{
		$("div." + byclass).parentsUntil("tr").show();
	}
}

function search_class_panel(input_field, byclass)
{
	value_to_search = $('#' + input_field).val();
	if ((value_to_search.length) >= 3)
	{
		$("div." + byclass).parentsUntil("tr").hide();
		$("div." + byclass + ":contains('"+value_to_search+"')").parentsUntil("div.panel").show();
	}
	else
	{
		$("div." + byclass).parentsUntil("div.panel").show();
	}
}

function search_class_row(input_field, byclass)
{
	value_to_search = $('#' + input_field).val();
	if ((value_to_search.length) >= 3)
	{
		$("div." + byclass).parentsUntil("div.row").hide();
		$("div." + byclass + ":contains('"+value_to_search+"')").parentsUntil("div.row").show();
	}
	else
	{
		$("div." + byclass).parentsUntil("div.row").show();
	}
}

function search_class_link(input_field, byclass)
{
	value_to_search = $('#' + input_field).val();
	if ((value_to_search.length) >= 2)
	{
		$("a." + byclass).hide();
		$("a." + byclass + ":contains('"+value_to_search+"')").parent().parent().show();
		$("a." + byclass + ":contains('"+value_to_search+"')").show();
	}
	else
	{
		//$("a." + byclass + ":contains('"+value_to_search+"')").parent().parent().hide();
		$("a." + byclass + ":contains('"+value_to_search+"')").hide();
	}
}


function do_fill_div(input_field, id_div, val)
{
	value_to_search = $('#' + input_field).val();
	if (((value_to_search.length) >= 4) && (val == value_to_search))
	{
		div = $('#'+id_div);
		div.html("<div class='alert alert-warning'>Buscando...</div>");
		$.ajax({
            type:'POST',
            url:'/pharma/medicamentos/search_remote/',
            data: {'especialidad':value_to_search, 'comercializado':'S', 'prActiv1':value_to_search, 'codATC':value_to_search, 'cn':value_to_search},
            success: function(response_data) {
                msg = response_data["medicamentos"];
                error = response_data["error"];
                newHtml = "";
                if (msg.length == 0) {
                    if ((error != 'null') && (error != null))
                        newHtml = "<div class='alert alert-danger'>" + error + "</div>";
                    else
                        newHtml = "<div class='alert alert-danger'>No hay resultados</div>";
                } else {
                    if ((error != null) && (error != 'null')) {
                        newHtml = "<div class='alert alert-warning'>" + error + "</div>";
                    }
                }
                for (i = 0; i < msg.length; i++) {
                    item = msg[i];
                    newHtml = (newHtml+"<a id='medic_"+ item.code+"' href=\'#search_anchor\' class=\'btn btn-default medic_item_search small btn-block\' onclick=\"add_code_medic('" +item.cn + "', \'"+item.name+"\');\" title=\'" + item.principles + "\' style=\'overflow-x:hidden;\'><p class='wrap_content'>" + item.name  +"["+item.cod_atc +" - " + item.cn +"]</p><p style='text-align:center'><small>"+item.family+"</small></p></a>");
                } 
                div.html(newHtml);
            }
		});
    } else { $('#'+id_div).html(""); }
}


timer=null;
function fill_div(input_field, id_div)
{
    value_to_search = $('#' + input_field).val();
    timer = setTimeout(do_fill_div, 400, input_field, id_div, value_to_search);
}

function gotoelement(id, padding = 120)
{
    offset = $('#'+id).offset().top - parseInt(padding);
    $('html,body').animate({scrollTop:offset}, 1000);
}

$.expr[":"].contains = $.expr.createPseudo(function(arg) { return function (elem) {return $(elem).text().toUpperCase().indexOf(arg.toUpperCase()) >= 0; }; });

$(document).ready(()=>{
    $("body").on("click", "#btn-register-send", function(e){
        e.preventDefault();
        //e.stopPropagation();

        var obj = $(this);
        var msg = "";
        var isOk = true;

        obj.find('input').each(function(){
            if (($(this).prop("name").indexOf('csrf') == -1) && ($(this).prop("name") != "tos"))
            {
                msg += "<br/> El campo " + $(this).prop('title') + " es requirido";
                isOk = false;
            }
        });
        if (!isEmail($("#email1").val()) || $("#email1").val() != $("#email2").val())
        {
            msg += "Los correos electrónicos no coinciden. <br/>";
            isOk = false;
        }
        if (!$("#tos").prop("checked"))
        {
            msg += "<br/> Debe aceptar las condiciones de uso.";
            isOk = false;
        }

        if (!isOk)
            $("#div-errors").html(msg).show();
        else
            $("#frmRegister").submit();
    });

    $("body").on("click", "#btn-donation-send", function(e){
        e.preventDefault();

        var obj = $(this);
        var msg = "";
        var isOk = true;

        obj.find('input').each(function(){
            if (($(this).prop("name").indexOf('csrf') == -1) && ($(this).prop("name") != "tos"))
            {
                msg += "<br/> El campo " + $(this).prop('title') + " es requirido";
                isOk = false;
            }
        });
        if ($("#plan-d").val() == "")
        {
            msg += "Debe seleccionar una periodicidad. <br/>";
            isOk = false;
        }
        if ($("#donation-amount").val() == "")
        {
            msg += "Debe seleccionar una cantidad. <br/>";
            isOk = false;
        }
        if (!isEmail($("#email-d1").val()) || $("#email-d1").val() != $("#email-d2").val())
        {
            msg += "Los correos electrónicos no coinciden. <br/>";
            isOk = false;
        }
        if (!$("#tos-d").prop("checked"))
        {
            msg += "<br/> Debe aceptar las condiciones de uso.";
            isOk = false;
        }

        if (!isOk)
            $("#div-donation-errors").html(msg).show();
        else
            $("#frmDonation").submit();
    });

});
