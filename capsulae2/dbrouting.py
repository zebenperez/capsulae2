class CapsulaeRouter(object):
    database = 'mylogin'
    apps = ['mylogin']
    """
    A router to control all database operations on models in the
    oldversion application.
    """
    def db_for_read(self, model, **hints):
        """
        Attempts to read oldversion models go to version1.
        """
        if model._meta.app_label in self.apps:
            return self.database
        return 'default'

    def db_for_write(self, model, **hints):
        """
        Attempts to write oldversion models go to version1.
        """
        if model._meta.app_label in self.apps:
            return self.database
        return 'default'

    def allow_relation(self, obj1, obj2, **hints):
        """
        Allow relations if a model in the oldversion app is involved.
        """
        if obj1._meta.app_label in self.apps or obj2._meta.app_label in self.apps:
            return True
        return 'default'

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Make sure the oldversion app only appears in the 'version1' database.
        """
        if app_label in self.apps:
            return self.database
        return 'default'

