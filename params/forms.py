#!/usr/bin/python
# -*- coding: utf-8 -*-

# general imports
import random
import string

from datetime import datetime
from ckeditor.widgets import CKEditorWidget
from crispy_forms.helper import FormHelper
from crispy_forms.layout import *
from crispy_forms.bootstrap import *

# django imports
from django import forms
from django.core.urlresolvers import reverse
from django.forms import ModelForm
from django.utils.translation import ugettext as _
# project imports

from .models import *

class BloodPresureForm(ModelForm):
    # date = forms.DateTimeField(widget=forms.TextInput(attrs={'type':'datetime-local', 'name':'date', 'id':'id_date'}), label="Fecha")
    date = forms.DateTimeField(widget=forms.DateInput(format='%Y-%m-%d %H:%M', attrs={'type': 'datetime', 'name': 'date', 'id': 'id_date'}), label="Fecha")
    # observations = forms.CharField(widget=CKEditorWidget(), label="Observaciones", required=False)

    def __init__(self, *args, **kwargs):
        super(BloodPresureForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.fields['date'].initial = datetime.now()
        self.helper.layout = Layout(
        TabHolder(
                Tab( _('Antropométricos'),
                    Div(Hidden('patient', "{{ paciente.pk }}"),
                        Div('weight', css_class="col-xs-4 form-block"),
                        Div('height', css_class="col-xs-4 form-block"),
                        Div(Field('bmi', readonly='True'), css_class="col-xs-4 form-block"),
                    ),
                    Div(Div('bicipital', css_class="col-xs-2 fold_value form-block"),
                        Div('tricipital', css_class="col-xs-2 fold_value form-block"),
                        Div('suprailiac', css_class="col-xs-2 fold_value form-block"),
                        Div('subscapular', css_class="col-xs-2 fold_value form-block"),
                        Div('abdominal', css_class="col-xs-2 form-block"),
                    ),
                    Div(
                         Div('belt', css_class="col-xs-2 form-block"),
                         Div('hip', css_class="col-xs-2 form-block"),
                         Div(Field('belt_hip_index', readonly="True"), css_class="col-xs-2 form-block"),
                         Div(Field('fat_index', readonly="True", css_class="fat_value"), css_class="col-xs-2 form-block"),
                         Div(Field('fat_weight', readonly="True", css_class="fat_value"), css_class="col-xs-2 form-block"),
                         Div(Field('muscle_weight', readonly="True", css_class="fat_value"), css_class="col-xs-2 form-block"),

                        ),
                ),
                Tab(_("Cardiovasculares"),
                    Div(
                        Div('bpressure_max', css_class="col-xs-6 small form-block"),
                        Div('bpressure_min', css_class="col-xs-6 small form-block"),
                        css_class="col-xs-12"
                    ),
                    Div(
                        Div('hearth_rate', css_class="col-xs-3 small form-block"),
                        Div('inr', css_class="col-xs-3 small form-block"),
                        #Div('framingham', css_class="col-xs-3 small readonly"),
                        Div(Field('framingham', readonly='True'), css_class="col-xs-3 small form-block"),
                        Div(HTML("<a href='/pharma/assets/tablasdereferencia.html' style='margin-top:1em;' class='btn btn-link ga-ajax-load' data-ga-target='modal' data-ga-modal-title='Tablas de Referencia' ><i class='fa fa-table'></i> Tablas</a>"), css_class="col-xs-3"),
                        css_class="col-xs-12"
                    ),
                ),
                Tab(_("Respiratorios"),
                    Div(
                        Div('fem', css_class="col-xs-4 form-block"),
                        Div('fev1', css_class="col-xs-4 form-block"),
                        Div('fev6', css_class="col-xs-4 form-block"),
                    ),
                    Div(
                        Div(Field('coef_fev1_fev6', readonly=True), css_class="col-xs-4 form-block"),
                        Div('epe', css_class="col-xs-4 form-block"),
                    )
                ),
                Tab(_("Endocrinos"),
                    Div(
                        Div('glucose', css_class="col-xs-6 form-block"),
                        Div('glicosylated', css_class="col-xs-6 form-block"),
                    )
                ),
                Tab(_("Perfil Lip-Uric"),Div(
                        Div('total_cholesterol', css_class="col-xs-4 form-block"),
                        Div('hdl', css_class="col-xs-4 form-block"),
                        Div('ldl', css_class="col-xs-4 form-block"), css_class="col-xs-12"
                    ),
                    Div(
                        Div('triglycerides', css_class="col-xs-4 form-block"),
                        Div('uric_acid', css_class="col-xs-4 form-block"),
                        css_class="col-xs-12"
                    )

                ),
                Tab(_("Func. Renal"),Div(
                        Div('serin_creatine_index', css_class="col-xs-6 form-block"),
                        Div(Field('mdrd_4', readonly=True), css_class="col-xs-6 form-block"),
                        Div(Field('mdrd_4_ims', readonly=True), css_class="col-xs-6 form-block"),
                        Div(Field('cdk_epi_creatinine', readonly=True), css_class="col-xs-6 form-block"),

                    ),
                ),
                Tab(_("Func. Hepática"),Div(
                        Div('got', css_class="col-xs-6 form-block"),
                        Div('gpt', css_class="col-xs-6 form-block"),
                    ),
                    Div(
                        Div(Field('got_gpt', readonly=True), css_class="col-xs-3 form-block"),
                        Div('ggt', css_class="col-xs-5 form-block"),
                        Div('alkaline_phosphatase', css_class='col-xs-4'), css_class="col-xs-12 form-block"
                    ),
                ),
                Tab(_("Dolor"), 
                    Div('eva', css_class="col-xs-12 form-block"),

                ),

         ),
         Div (
            HTML("<hr/>"),
            Div(Field('date', name="Fecha"), css_class="col-xs-12"),
            Div('observations', css_class="col-xs-12"),
         )
#               Tab(_(""),
#               
#           Div(
#               Div('glicosylated', css_class="col-xs-4"),
#               Div('glucose', css_class="col-xs-4"),
#           ),
#           Div('fem', css_class="col-xs-12"),
#           Div('observations', css_class="col-xs-12"),
        )
        
        #self.fields['date'].initial = date_str

    class Meta:
        model = BloodPressure
        exclude=['creation_date']


