import queue
import sqlite3
import pymysql
class ConnectionFactory:
    def get_connection(db_type='sqlite'):
        if db_type.upper() == 'MYSQL':
            return Connection_mysql()
        elif db_type.upper() == 'SQLITE':
            return Connection()
#连接池,使得连接更高效
class ConnectionPool:
    def __init__(self,n=None):
        try:
            from .config import DatabaseConfig
        except Exception:
            from config import DatabaseConfig
        pool_size = DatabaseConfig.POOL_SIZE if n is None else n
        self._pool = queue.Queue(maxsize=pool_size)
        db_file = DatabaseConfig.SQLITE_DB_FILE
        for i in range(pool_size):
            self._pool.put(sqlite3.connect(db_file))
    def get_conn(self):
        return self._pool.get(timeout=10)
    def return_conn(self,conn):
        self._pool.put(conn)

#封装数据库连接,执行sql
class Connection():
    def __init__(self):
        self.connpool = ConnectionPool()
        self.conn = self.connpool.get_conn()
        self.cursor = self.conn.cursor()
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    def execute(self,sql,values=None):
        self.cursor.execute(sql,values or ())
        if sql.strip().upper().startswith('SELECT'):
            return self.cursor.fetchall()
        else:   
            self.conn.commit()
            return self.cursor.rowcount
    def close(self):
        self.connpool.return_conn(self.conn)

#连接池mysql版,使得连接更高效
class ConnectionPool_Mysql:
    def __init__(self, n=None):
        try:
            from .config import DatabaseConfig
        except Exception:
            from config import DatabaseConfig
        pool_size = DatabaseConfig.POOL_SIZE if n is None else n
        self._pool = queue.Queue(maxsize=pool_size)
        mysql_config = DatabaseConfig.MYSQL_CONFIG
        for i in range(pool_size):
            conn = pymysql.connect(
                host=mysql_config['host'],
                port=mysql_config['port'],
                user=mysql_config['user'],  # 替用户名
                password=mysql_config['password'],  # 密码
                database=mysql_config['database'],  # 数据库名
                charset=mysql_config['charset'],
                cursorclass=pymysql.cursors.Cursor
            )
            self._pool.put(conn)
    
    def get_conn(self):
        return self._pool.get(timeout=10)
    
    def return_conn(self, conn):
        self._pool.put(conn)

class Connection_mysql():
    def __init__(self):
        self.connpool = ConnectionPool_Mysql()
        self.conn = self.connpool.get_conn()
        self.cursor = self.conn.cursor()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    def execute(self, sql, values=None):
        sql = sql.replace('?','%s')
        self.cursor.execute(sql, values or ())
        if sql.strip().upper().startswith('SELECT'):
            return self.cursor.fetchall()
        else:   
            self.conn.commit()
            return self.cursor.rowcount
    
    def close(self):
        self.connpool.return_conn(self.conn)