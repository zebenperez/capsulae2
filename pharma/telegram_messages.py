"""
    Plantillas para los textos del bot.
"""
MESSAGES = {
    'es': {

        'active_treatments': "\n <b>Éstos son sus tratamientos activos: </b>\n\n",
        'confirmation_required': "Lo siento, pero no podré atenderte hasta que tu registro se haya completado",
        'no_text_allowed': (
            "<b> ⚠ No puedo responderte </b>\n"
            "Soy un asistente automático, por el momento no soy capaz de responderte. Si tienes alguna duda, ponte en "
            "contacto con el personal de tu farmacia"
        ),
        'params_notification': (
            "<b> Nuevos Parámetros registrados </b>\n"
            "<pre>·Peso: $weight Kg \n"
            "·BMI: $bmi \n"
            "·Pres. Arterial Máx: $bpressure_max\n"
            "·Pres. Arterial Mín: $bpressure_min\n"
            "·Altura: $height\n"
            "·Glucosa: $glucose\n"
            "</pre>"
        ),
        'pillbox_notification': (
            "<b>Pastillero Preparado: </b>\n"
            "Estimado $full_name, su pastillero está preparado y listo para que lo recoja lo antes posible"),
        'register_confirmed': "✓ Su registro ha sido confirmado correctamente",
        'register_rejected': "✗ Su registro se ha cancelado, Si desea registrarse puede volver a solicitarlo en cualquier momento",
        'register_confirm_ask': ("Hemos recibido una solicitud de registro correspondiente a este dispositivo, ¿Desea confirmarla?"),
        'register_confirm_btn': "Si, deseo confirmar mi registro",
        'register_reject_btn': "No, deseo rechazar mi registro",
        'treatment_notification': (
            "<b> Nuevo Tratamiento </b>\n"
            "Estimado $full_name, <i>$treatment_name</i> ha sido añadido a su plan de tratamientos, en caso de error "
            "no dude en ponerse en contacto con nosotros "
        ),
        'treatment_line': "▶ $med\n\n",
        'welcome': (
            "Bienvenido, soy Nieves, el Asistente Virtual Inteligente de Capsulae.\n"
            "Antes de comenzar a beneficiarse de todo lo que puedo ofrecerle, debe acudir a su farmacia y mostrar "
            "el código de identificación que se le ha asignado, para que puedan verificar su identidad\n"
            " Su código es <b>$code</b>"),
    }
}

