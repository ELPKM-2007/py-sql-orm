class DatabaseConfig:
    MYSQL_CONFIG = {
        'host': '127.0.0.1',
        'port': 3306,
        'user': 'root',
        'password': '',
        'database': 'test',
        'charset': 'utf8mb4'
    }
    SQLITE_DB_FILE = 'myorm.db'
    POOL_SIZE = 5
    
    @classmethod
    def configure_mysql(cls, **kwargs):
        cls.MYSQL_CONFIG.update(kwargs)
    
    @classmethod
    def configure_sqlite(cls, db_file):
        if db_file:
            cls.SQLITE_DB_FILE = db_file
    
    @classmethod
    def set_pool_size(cls, size):
        cls.POOL_SIZE = size