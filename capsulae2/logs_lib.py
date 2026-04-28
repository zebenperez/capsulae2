from django.conf import settings
import os

def get_path(name):
    path = os.path.join(settings.BASE_DIR, name)
    if not os.path.exists(path):
        os.makedirs(path)
    return path

def write_in_file(path, text):
    f = open(path, "a", encoding='utf-8')
    f.write("{}\n".format(text))
    f.close()

def write_log(msg, file_name, folder=""):
    path = get_path("media/logs/{}/".format(folder)) if folder != "" else get_path("media/logs/")
    log_path = "{}{}".format(path, file_name)
    write_in_file(log_path, msg)

def get_logs(folder=""):
    path = get_path("media/logs/{}/".format(folder)) if folder != "" else get_path("media/logs/")
    try:
        return [f for f in os.listdir(path)]
    except:
        return []

def get_log(file_name, folder=""):
    path = get_path("media/logs/{}/".format(folder)) if folder != "" else get_path("media/logs/")
    log_path = "{}{}".format(path, file_name)
    f = open(log_path, "r", encoding='utf-8')
    content = f.read()
    f.close()
    return content
#    size = os.path.getsize(current_log)
#    text = ""
#    if size < 1000:
#        text = f.read()
#    else:
#        i = 0
#        for line in f.readlines():
#            if i > 1000:
#                break
#            text += line
#            i += 1

