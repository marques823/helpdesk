
class DatabaseRouter:
    """
    Controla as operações de banco de dados para direcionar 
    sessões, cache e ratelimit para o banco de dados local.
    """
    
    local_apps = {'sessions', 'cache', 'django_ratelimit'}

    def db_for_read(self, model, **hints):
        if model._meta.app_label in self.local_apps:
            return 'local_db'
        return 'default'

    def db_for_write(self, model, **hints):
        if model._meta.app_label in self.local_apps:
            return 'local_db'
        return 'default'

    def allow_relation(self, obj1, obj2, **hints):
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label in self.local_apps:
            return db == 'local_db'
        return db == 'default'
