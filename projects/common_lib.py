from django.core.files.base import ContentFile
from django.shortcuts import reverse

from datetime import datetime

from projects.models import Folder

#import pyAesCrypt
#import io


'''
    Common
'''
def get_folder_path(folder):
    path = ""
    if folder != None and folder != "" and folder.parent != None:
        path = get_folder_path(folder.parent)
    path = "{} / {}".format(path, folder.name) if folder != None and folder != "" else "/"
    return path

def get_folder_path_link(folder, current, project_id):
    path = ""
    if folder != None and folder != "":
        path = get_folder_path_link(folder.parent, current, project_id)

    target = "div-container"
    if folder != None and folder != "":
        if folder == current:
            return "{} / {}".format(path, folder.name)
        else:
            url = reverse('project-folder-change')
            obj_id = folder.id
            name = folder.name
            link = "<a class='ark pathway' data-url='{}' data-target='{}' data-obj_id='{}' data-enter='True'>{}</a>".format(url, target, obj_id, name)
            return "{} / {}".format(path, link)
        #return "{} / {}".format(path, link) if folder != current else "{} / ".format(path)
    else:
        url = reverse('project-drive')
        link = "<a class='ark pathway' data-url='{}' data-target='{}' data-obj_id='{}'>Carpeta Raiz</a>".format(url, target, project_id)
        return "{}&nbsp;".format(link) 

#'''
#    Crypto
#'''
#def encrypt(f, password):
#    bufferSize = 64 * 1024
#
#    pbdata = f.read()
#    fIn = io.BytesIO(pbdata)
#    fCiph = io.BytesIO()
#    pyAesCrypt.encryptStream(fIn, fCiph, password, bufferSize)
#
#    fOut = ContentFile(fCiph.getvalue())
#    fOut.name = "%s.aes" % (f.name)
#
#    return fOut
#
#def decrypt(f, password):
#    bufferSize = 64 * 1024
#
#    fDec = io.BytesIO()
#    fCiph = io.BytesIO(f.read())
#    ctlen = len(fCiph.getvalue())
#    pyAesCrypt.decryptStream(fCiph, fDec, password, bufferSize, ctlen)
#
#    fOut = ContentFile(fDec.getvalue())
#    fOut.name = f.name.replace(".aes", "")
#
#    return fOut
#
