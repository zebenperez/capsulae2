from django.contrib.auth.models import User, Group

#from datetime import datetime
from pharma.models import Pacientes
from .models import *

import datetime, csv, xlrd, random, string, pandas as pd

def get_date(date, time=""):
    try:
        if time != "":
            return datetime.datetime.strptime("{} {}".format(date, time), "%Y-%m-%d %H:%M")
        else:
            return datetime.datetime.strptime("{}".format(date), "%Y-%m-%d")
    except Exception as e:
        return datetime.datetime.min

def get_born_date(cip):
    try:
        if len(cip) == 16:
            year_cip = cip[4:6]
            month_cip = cip[6:8]
            day_cip = cip[8:10]
            limit_year = 2000 - datetime.datetime.now().year
            year = "19%s" % year_cip if int(year_cip) > limit_year else "20%s" % year_cip
            day = str(int(day_cip) - 40).zfill(2) if int(day_cip) > 39 else day_cip
            if int(month_cip) > 0 and int(month_cip) < 13 and int(day) > 0 and int(day) < 32:
                return "%s-%s-%s" % (year, month_cip, day)
    except Exception as e:
        print(e)
    return datetime.datetime.min

def get_sex(cip):
    try:
        if len(cip) == 16:
            return "M" if int(cip[8:10]) > 39 else "H"
    except Exception as e:
        print(e)
    return ""

def get_json_date(val):
    try:
        return xlrd.xldate_as_datetime(float(val), 0)
    except:
        return ""

def get_json_datas(f, ods=False):
    from pyexcel_ods import get_data
    datas = {"dispensations": []}

    if ods:
#         data = pd.read_excel(f, engine="odf")
        data = get_data(f)
        for key, value in data.items():
            for idx, row in enumerate(value):
                if idx > 0:
                    if len(row) > 0:
                        node = {}
                        item = [ row[0], row[1],  row[3],  row[6],  row[7],  row[8], 
                                row[10], row[11], row[12], row[13], row[19], row[20], 
                                row[14], row[15], row[21], row[22], row[23], row[24], 
                                row[25], row[26], row[27], row[29], row[34], row[35], 
                                row[36], row[28], row[31], row[32], row[18], row[17], 
                                row[33], row[30], row[5]]

                        node["date"] = item[0]
                        node["code"] = item[3]
                        node["treatment"] = item[4]
                        node["order"] = item[5]
                        node["units"] = item[6]
                        node["pvp"] = item[7]
                        node["bill_pvp"] = item[8]
                        node["amount"] = item[9]
                        node["ini_date"] = item[10]
                        node["end_date"] = item[11]
                        node["num"] = item[12]
                        node["pre_code"] = item[14]
                        node["pre_name"] = item[15]
                        node["pre_pvp"] = item[16]
                        node["pre_bill_pvp"] = item[17]
                        node["pre_amount"] = item[18]
                        node["next_date"] = item[29]

                        node["name"] = item[19]
                        node["cip"] = item[20]
                        node["nif"] = item[30]
                        datas["dispensations"].append(node)
            break

    else:
        book = xlrd.open_workbook(file_contents=f.read())
        sh = book.sheet_by_index(0)
        i = 0
        for rx in range(sh.nrows):
            if i == 0:
                i += 1
            else:
                node = {}
                #node["date"] = sh.cell_value(rowx=rx, colx=0)
                #node["time"] = sh.cell_value(rowx=rx, colx=1)
                node["date"] = get_json_date(sh.cell_value(rowx=rx, colx=1))
                node["code"] = sh.cell_value(rowx=rx, colx=3)
                node["treatment"] = sh.cell_value(rowx=rx, colx=4)
                node["order"] = sh.cell_value(rowx=rx, colx=5)
                node["units"] = sh.cell_value(rowx=rx, colx=6)
                node["pvp"] = sh.cell_value(rowx=rx, colx=7)
                node["bill_pvp"] = sh.cell_value(rowx=rx, colx=8)
                node["amount"] = sh.cell_value(rowx=rx, colx=9)
                node["ini_date"] = get_json_date(sh.cell_value(rowx=rx, colx=10))
                node["end_date"] = get_json_date(sh.cell_value(rowx=rx, colx=11))
                node["num"] = sh.cell_value(rowx=rx, colx=12)
                node["pre_code"] = sh.cell_value(rowx=rx, colx=14)
                node["pre_name"] = sh.cell_value(rowx=rx, colx=15)
                node["pre_pvp"] = sh.cell_value(rowx=rx, colx=16)
                node["pre_bill_pvp"] = sh.cell_value(rowx=rx, colx=17)
                node["pre_amount"] = sh.cell_value(rowx=rx, colx=18)
                node["next_date"] = sh.cell_value(rowx=rx, colx=29)

                node["name"] = sh.cell_value(rowx=rx, colx=19)
                node["cip"] = sh.cell_value(rowx=rx, colx=20)
                node["nif"] = sh.cell_value(rowx=rx, colx=30)
                datas["dispensations"].append(node)
    return datas

def get_json_datas_farmatic(f):
    from pyexcel_ods import get_data
    datas = {"dispensations": []}

    book = xlrd.open_workbook(file_contents=f.read())
    sh = book.sheet_by_index(0)
    i = 0
    for rx in range(sh.nrows):
        if i == 0:
            i += 1
        else:
            node = {}
            node["date"] = "{} {}".format(sh.cell_value(rowx=rx, colx=0), sh.cell_value(rowx=rx, colx=1))
            node["name"] = sh.cell_value(rowx=rx, colx=2)
            node["cip"] = sh.cell_value(rowx=rx, colx=3)
            #Tratamiento
            #C. Cliente
            #Cliente
            node["num"] = sh.cell_value(rowx=rx, colx=7)
            node["code"] = sh.cell_value(rowx=rx, colx=8)
            node["treatment"] = sh.cell_value(rowx=rx, colx=9)
            node["pre_code"] = sh.cell_value(rowx=rx, colx=10)
            node["pre_name"] = sh.cell_value(rowx=rx, colx=11)
            #T.A.
            node["units"] = sh.cell_value(rowx=rx, colx=12)
            node["pvp"] = sh.cell_value(rowx=rx, colx=13)
            node["bill_pvp"] = sh.cell_value(rowx=rx, colx=14)
            node["next_date"] = sh.cell_value(rowx=rx, colx=15)
            #Vendedor
            #Maquina
            node["nif"] = ""
            node["order"] = ""
            node["amount"] = ""
            node["ini_date"] = ""
            node["end_date"] = ""
            node["pre_pvp"] = ""
            node["pre_bill_pvp"] = ""
            node["pre_amount"] = ""
            datas["dispensations"].append(node)
    return datas


def set_patient_datas(obj, nif, cip, name, user):
    obj.nif = nif
    obj.n_orden = ""
    obj.fecha_nacimiento = get_born_date(cip)
    obj.cod_postal = 0
    obj.dieta = ""
    obj.facultativo = ""
    obj.alergias = ""
    obj.plan_cuidados = ""
    obj.sexo = get_sex(cip)
    obj.observaciones = ""
    obj.borrado = False
    obj.me_prescriptor= ""
    obj.cip = cip
    obj.nombre = name
    obj.apellido = ""
    obj.fotografia = ""
    obj.n_historial = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(8))
    obj.nass = ""
    obj.domicilio = ""
    obj.telefono1 = 0
    obj.cama = 0
    obj.habitacion = 0
    obj.tipo_paciente = ""
    obj.pastillero = ""
    obj.otras_alergias = ""
    obj.use_poli = ""
    obj.id_user = user
    obj.created_at = datetime.datetime.now()
    obj.email = ""
    obj.slug_address = ""
    obj.save()

def set_patient_json(values, user):
    nif = values["nif"]
    cip = values["cip"]
    name = values["name"]
    obj = Pacientes.objects.filter(cip=cip, id_user=user).first()
    if obj == None and name != "" and cip != "":
        obj = Pacientes()
        set_patient_datas(obj, nif, cip, name, user)
    return obj

def set_dispensations_json(values, patient):
    if patient != None:
        kwargs = {'patient': patient}
        #kwargs["date"] = get_date(values["date"], values["time"])
        kwargs["date"] = values["date"]
        kwargs["code"] = values["code"]
        kwargs["name"] = values["name"]
        kwargs["order"] = values["order"]
        kwargs["units"] = values["units"]
        kwargs["pvp"] = values["pvp"]
        kwargs["bill_pvp"] = values["bill_pvp"]
        kwargs["amount"] = values["amount"]
        kwargs["ini_date"] = values["ini_date"]
        kwargs["end_date"] = values["end_date"]
        #kwargs["ini_date"] = get_date(values["ini_date"])
        #kwargs["end_date"] = get_date(values["end_date"])
        #kwargs["num"] = values["num"]
        kwargs["pre_code"] = values["pre_code"]
        kwargs["pre_name"] = values["pre_name"]
        kwargs["pre_pvp"] = values["pre_pvp"]
        kwargs["pre_bill_pvp"] = values["pre_bill_pvp"]
        kwargs["pre_amount"] = values["pre_amount"]
        kwargs["next_date"] = values["next_date"]
        #kwargs["next_date"] = get_date(values["next_date"])
        obj, created = Dispensation.objects.get_or_create(**kwargs)
        return obj
    return None

#def import_datas(f):
#    dataReader = csv.reader(f.read().decode("utf-8").splitlines(), delimiter=",", quotechar='"')
#    for row in dataReader:
#        if len(row) == 33:
#            set_dispensations(row)

#def set_dispensations(row):
#    cip = row[20]
#    patient = Pacientes.objects.filter(cip=cip).first()
#    if patient != None:
#        #obj = Dispensation.objects.filter(patient = patient, date = row[0], time = row[1], code = row[3], name = row[4]).first()
#        #if obj == None:
#        obj = Dispensation(patient = patient)
#        #obj.date = row[0]
#        #obj.time = row[1]
#        #try:
#        #    obj.date = datetime.strptime("{} {}".format(row[0], row[1]), "%d/%m/%Y %H:%M")
#        #except Exception as e:
#            #print(e)
#        #    pass
#        obj.date = get_date(row[0], row[1])
#        obj.code = row[3]
#        obj.name = row[4]
#        obj.order = row[5]
#        obj.units = row[6]
#        obj.pvp = row[7]
#        obj.bill_pvp = row[8]
#        obj.amount = row[9]
#        #obj.ini_date = row[10]
#        #obj.end_date = row[11]
#        obj.ini_date = get_date(row[10])
#        obj.end_date = get_date(row[11])
#        obj.num = row[12]
#        obj.pre_code = row[14]
#        obj.pre_name = row[15]
#        obj.pre_pvp = row[16]
#        obj.pre_bill_pvp = row[17]
#        obj.pre_amount = row[18]
#        #obj.next_date = row[29]
#        obj.next_date = get_date(row[29])
#        obj.save()


