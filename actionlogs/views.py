from django.shortcuts import render
from capsulae2.decorators import group_required
from .models import *


class LogManager():
    app = ""
    user =""

    def __init__(self, app, user):
        self.app = app
        self.user = user

    def save_action(self, url, action, model=None, object_id=None):
        try:
            log_type = None
            try :
                log_type = ContentType.objects.get(app_label=self.app, model=model)
            except :
                pass

            actionlog = ActionLog.objects.create(
                user= self.user,
                object_id = object_id,
                content_type = log_type,
                app=self.app,
                url = url,
                action = action,
            )
            return True
        except Exception as e:
            print (str(e))
            logger.error(str(e))
        return False

    def save_err (self, url, action, model=None, object_id=None):
        return self.save_action(url, "ERR: %s"%(action), model, object_id)


    def save_post(self, url, action , model=None, object_id=None):
        return self.save_action(url, "POST: %s"%(action), model, object_id)


    def save_get(self, url, action , model=None, object_id=None):
        return self.save_action(url, "GET: %s"%(action), model, object_id)


    #introduce la accion solo una vez al dia
    def save_action_for_day(self, url, action, model=None , object_id=None):
        now = datetime.now()
        today_str = "%s/%s/%s 00:00:00"%(str(now.day), str(now.month), str(now.year))
        today = datetime.strptime(today_str, "%d/%m/%Y %H:%M:%S")

        actions = ActionLog.objects.filter(user = self.user,
                                action=action, url = url, date__gte=today)
        if actions.count() < 1:
            return self.save_action(url, action, model, object_id)
        return None

