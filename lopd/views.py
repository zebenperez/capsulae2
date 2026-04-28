import logging
import datetime
import os

from django.contrib.auth.decorators import login_required
from django.core.files import File
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_exempt
from weasyprint import HTML, CSS

#local imports
from capsulae2.settings import MEDIA_ROOT
from account.models import Company
from pharma.models import Pacientes
#from pharma.utils import is_group_member
#from companies.views import MANAGERS_GROUP
from .models import *

log = logging.getLogger(__name__)


@login_required
def consent_upload (request, paciente_id):
    return redirect("pharma-index")
#    context = {}
#    form = LOPDConsentForm()
#    try:
#
#        patient = Pacientes.objects.get(pk=paciente_id)
#        context['paciente'] = patient
#
#        if request.method == "POST":
#            form = LOPDConsentForm(request.POST, request.FILES)
#            if form.is_valid():
#                form.save()
#                request.session['success'] = True
#                return redirect('lopd_consents_patient', paciente_id=paciente_id)
#
#    except Exception as e:
#        log.error(str(e))
#        context['error'] = "No se ha encontrado al paciente"
#
#    context['form']  = form
#    return render(request, "lopd_consent_upload_form.html", context)
#

#@login_required
@login_required(login_url='/pharma/index/')
def generate_document(request, paciente_id):
    return redirect("pharma-index")
#    context={}
#
#    try:
#        patient = Pacientes.objects.get(pk=paciente_id)
#        log.info("Generando documento para {}".format(patient))
#        context['patient'] = patient
#        context['company'] = request.user.companies.all()[0]
#    except Exception as e:
#        log.error("{0}".format(str(e)))
#    
#    company = None
#    if is_group_member(request.user, MANAGERS_GROUP):
#        try:
#            company = request.user.companies.all()[0]
#        except Exception as e:
#            log.error(str(e))
#    else:
#        try:
#            company = request.user.facility.all().order_by('-start_date')[0].company
#        except Exception as e:
#            log.error(str(e))
#            
#    
#    log.debug("{0}".format(str(context)))
#    return render(request, "lopd_document_template.html", context)
#
#@login_required
def generate_signed_document(request, paciente_id):
    return redirect("pharma-index")
#    context = {}
#    response ="<h3>400 BAD REQUEST</h3>"
#    if request.method =="POST":
#        print(request.POST)
#        company_id = request.POST.get("company", None)
#        signature = request.POST.get("patient_signature", None)
#        check1 = request.POST.get("check1", "True")
#        check2 = request.POST.get("check2", "True")
#        check3 = request.POST.get("check3", "True")
#        prof_signature = request.POST.get('professional_signature', None)
#        if company_id != None and signature != None:
#            patient = Pacientes.objects.get(pk=paciente_id)
#            company = Company.objects.get(pk = company_id)
#            log.info("Generando documento firmado por el paciente {0} para la empresa {1}".format(patient, company))
#            
#            check1 = "checked.png" if check1 == "True" else "unchecked.png"
#            check2 = "checked.png" if check2 == "True" else "unchecked.png"
#            check3 = "checked.png" if check3 == "True" else "unchecked.png"
#
#            context = {
#                'request' : request,
#                'patient' : patient,
#                'company' : company,
#                'signature': signature,
#                'check1_img': check1,
#                'check2_img': check2,
#                'check3_img': check3,
#                'signing': True,
#                'host': "%s://%s"%(request.scheme, request.META['HTTP_HOST']),
#
#            }
#            html_template = render_to_string("lopd_signed_template.html", context)  
#                
#            lopd_dir = os.path.abspath(os.path.join(MEDIA_ROOT,'lopd_files'))
#            if not os.path.exists(lopd_dir):
#                os.makedirs(lopd_dir)
#            
#            date_str = datetime.datetime.now().strftime("%d%m%Y%H%M")
#            filename = "signed_consent_{0}_{1}.pdf".format(patient.nif, date_str)
#            filepath = os.path.join(lopd_dir,filename)
#            
#            consent = LOPDConsents(paciente=patient)
#            with open(filepath, 'wb+') as pdf_file :
#                filepath = os.path.join(lopd_dir, filename )    
#                pdf_content = HTML(string=html_template).write_pdf()
#                pdf_file.write(pdf_content) 
#                consent.document.save(filename,File(pdf_file), save=True)
#                consent.save()
#
#            response = HttpResponse(pdf_content, content_type="application/pdf")
#            response['Content-Disposition'] = 'filename="{0}"'.format(filename)
#            response['Content-Transfer-Encoding']= 'binary'
#            return response
#            
#    return HttpResponse(response)
#

@login_required
def patient_consents(request, paciente_id):
    return redirect("pharma-index")
#    context = {}
#    if 'success' in request.session:
#        context['success'] = True
#        del request.session['success']
#    
#    if 'error' in request.session:
#        context['error']  = request.session['error']
#        del request.session['error']
#
#    try:
#        patient = Pacientes.objects.get(pk=paciente_id) 
#        consents = LOPDConsents.objects.filter(paciente=patient).order_by('-date')
#        context['patient'] = patient
#        context['consents'] = consents
#        
#    except Exception as e:
#        log.error("{}".format(str(e)))
#        context['error'] = "No se ha encontrado el paciente"
#
#    return render(request, "patient_consents.html", context)
#
@login_required
def delete_document (request, paciente_id, consent_id):
    return redirect("pharma-index")
#    
#    try:
#        consent = LOPDConsents.objects.get(pk=consent_id, paciente__id=paciente_id)
#        try:
#            os.remove(os.path.abspath(consent.document.path))
#            
#        except Exception as e:
#            log.error(str(e))
#            request.session['error'] = "No se ha podido eliminar el fichero asociado"
#        consent.delete()
#        request.session['success'] = True
#    except Exception as e:
#        log.error(str(e))
#        request.session['error'] = "No se ha podido eliminar el elemento"
#
#    
#    return redirect('lopd_consents_patient',paciente_id=paciente_id)
#
    
        

