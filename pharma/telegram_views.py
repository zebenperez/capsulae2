from django.http import HttpResponse
from django.shortcuts import render, redirect, reverse
from django.views.decorators.csrf import csrf_exempt

from telegram import Update

from capsulae2.decorators import group_required
from capsulae2.commons import get_or_none, get_param, show_exc
from .treatment_models import Tratamiento
from .params_models import BloodPressure
from .telegram_models import TelegramUserChat
from .models import Pacientes
from .telegram_lib import TG_BOT, patient_register_confirm, get_message


'''
    Telegram
'''
def check_chat(patient, chat):
    if not chat or not patient:
        return "El código indicado no existe"
    if chat.patient is not None:
        return "Este chat ya corresponde a un paciente"
    return ""

@group_required("admins","managers")
def patient_telegram_register(request):
    try:
        patient = get_or_none(Pacientes, get_param(request.GET, "patient_id"))
        if patient == None:
            return render(request, 'error_exception.html', {'exc':'Paciente no encontrado!'})

        return render(request, "patient/telegram/telegram-register.html", {'obj': patient})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins","managers")
def patient_telegram_register_send(request):
    try:
        patient = get_or_none(Pacientes, get_param(request.POST, "patient_id"))
        chat = get_or_none(TelegramUserChat, get_param(request.POST, "chat_code"), 'code')
        obs = get_param(request.POST, "observations") 

        msg = check_chat(patient, chat)
        if msg == "":
            chat.patient = patient
            chat.observations = obs
            chat.save()
        patient_register_confirm(TG_BOT, chat.telegram_chat_id)
        return render(request, "patient/telegram/chat-list.html", {'obj': patient})

    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins","managers")
def patient_telegram_register_check(request):
    try:
        patient = get_or_none(Pacientes, get_param(request.GET, "obj_id"))
        chat = get_or_none(TelegramUserChat, get_param(request.GET, "chat_code"), 'code')
        msg = check_chat(patient, chat)
        return render(request, "patient/telegram/code-checked.html", {'msg': msg})
        #return HttpResponse(msg)
    except Exception as e:
        print(e)
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins","managers")
def patient_telegram_register_remove(request):
    try:
        obj = get_or_none(TelegramUserChat, request.GET["obj_id"])
        patient = obj.patient
        obj.delete()

        return render(request, "patient/telegram/chat-list.html", {'obj': patient})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins","managers")
def patient_telegram_message(request):
    try:
        patient = get_or_none(Pacientes, get_param(request.GET, "patient_id"))
        chat = get_or_none(TelegramUserChat, get_param(request.GET, "obj_id"))

        return render(request, "patient/telegram/telegram-message.html", {'patient': patient, 'chat': chat})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins","managers")
def patient_telegram_message_send(request):
    try:
        patient = get_or_none(Pacientes, get_param(request.POST, "patient_id"))
        chat = get_or_none(TelegramUserChat, get_param(request.POST, "chat_id"))
        subject = get_param(request.POST, "subject")
        message = get_param(request.POST, "message")

        send_result = False #True: envío correcto, False: envío incorrecto
        msg = ""
        if subject != "":
            msg = "<b>{}</b> \n".format(subject)
        if message != "":
            msg += message

        if chat.confirmed:
            send_result = TG_BOT.send_message(chat.telegram_chat_id, message)

        return render(request, "patient/telegram/chat-list.html", {'obj': patient})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})


def pillbox_deliver_notification(request):
    try:
        patient = get_or_none(Pacientes, request.GET["obj_id"])
        chats = patient.patient_telegram.filter()
        message = get_message('pillbox_notification', {'full_name': patient.full_name})

        sended = False
        for item in chats:
            #if item.code == "da2d0c9c":
            sended = TG_BOT.send_message(item.telegram_chat_id, message)
            #sended = sended + 1 if send_result else sended

        return render(request, "patient/telegram/telegram-confirm.html", {'sended': sended})
        #return HttpResponse(get_sended_result(sended))
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

def treatment_notification(request):
    try:
        treatment = get_or_none(Tratamiento, request.GET["obj_id"])
        chats = treatment.paciente.patient_telegram.filter()
        message = get_message('treatment_notification', {'full_name': treatment.paciente.full_name, 'treatment_name': treatment.name})

        sended = False
        for item in chats:
            #if item.code == "da2d0c9c":
            sended = TG_BOT.send_message(item.telegram_chat_id, message)
            #sended = sended + 1 if send_result else sended

        return render(request, "patient/telegram/telegram-confirm.html", {'sended': sended})
 
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})
#    sended = 0
#    patient = get_or_none(Pacientes, patient_id)
#    treatment = patient.tratamientos.filter(pk=treatment_id).first()
#    message = None
#    if treatment:
#        message = get_message("treatment_notification", {'full_name': patient.full_name, 'treatment_name': treatment.name})
#
#    if message:
#        chats = patient.patient_telegram.filter()
#        for item in chats:
#            send_result = TG_BOT.send_message(item.telegram_chat_id, message)
#            sended = sended + 1 if send_result else sended
#
#    return HttpResponse(get_sended_result(sended))

def params_notification(request):
    try:
        params = get_or_none(BloodPressure, request.GET["obj_id"])
        chats = params.patient.patient_telegram.filter()

        params_dict = {'weight':params.weight, 'bpressure_min':params.bpressure_min, 'bpressure_max':params.bpressure_max, 'bmi':params.bmi, 'hdl':params.hdl, 'glucose':params.glucose, 'height':params.height}
        for key in params_dict.keys():
            value = params_dict.get(key, None)
            if value:
                if key == "height":
                    params_dict[key] = "%.2f" % value
                else:
                    params_dict[key] = ("%.1f" % value).replace(".", ',')
            else:
                params_dict[key] = "Sin medida"
        message = get_message("params_notification", params_dict)

        sended = False
        for item in chats:
            #if item.code == "da2d0c9c":
            sended = TG_BOT.send_message(item.telegram_chat_id, message)
            #sended = sended + 1 if send_result else sended

        return render(request, "patient/telegram/telegram-confirm.html", {'sended': sended})
 
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

#def params_info_notification(request, patient_id, bpressure_id):
#    sended = 0
#    patient = get_or_none(Pacientes, patient_id)
#    params = patient.blood_pressure.get(pk=bpressure_id)  # .all().order_by("-date", "-creation_date").first()
#
#    if params:
#        params_dict = {'weight': params.weight, 'bpressure_min': params.bpressure_min,
#                       'bpressure_max': params.bpressure_max,
#                       'bmi': params.bmi, 'hdl': params.hdl,
#                       'glucose': params.glucose, 'height': params.height}
#        for key in params_dict.keys():
#            value = params_dict.get(key, None)
#            if value:
#                if key == "height":
#                    params_dict[key] = "%.2f" % value
#                else:
#                    params_dict[key] = ("%.1f" % value).replace(".", ',')
#            else:
#                params_dict[key] = "Sin medida"
#        message = get_message("params_notification", params_dict)
#
#    if message:
#        chats = patient.patient_telegram.filter()
#        for item in chats:
#            print (item)
#            send_result = TG_BOT.send_message(item.telegram_chat_id, message)
#            sended = sended + 1 if send_result else sended
#
#    return HttpResponse(get_sended_result(sended))
#

'''
    Webhook
'''
@csrf_exempt
def telegram_web_hook(request):
    if request.method == "POST":
        update = Update.de_json(json.loads(request.body.decode("utf-8")), TG_BOT)
        chat_id = update.callback_query.message.chat_id if update.callback_query else update.message.chat.id
        #tg_chat = get_or_create_query(TelegramUserChat, {"telegram_chat_id": chat_id})
        tg_chat, created = TelegramUserChat.objects.get_or_create(telegram_chat_id=chat_id)

        allow = tg_chat.confirmed
        if not allow:
            try:
                try:
                    allow = update.message.text == "/start"
                except AttributeError:
                    allow = True if update.callback_query else False
            except Exception as e:
                logger.error(str(e))

        if allow:
            TG_BOT._dispatcher.process_update(update)
        else:
            TG_BOT.send_message(update.message.chat.id, get_message("confirmation_required"))
        # telegram_queue.put(update)

    return JsonResponse({'body': str(request.body), 'error': "wrong_method"})

