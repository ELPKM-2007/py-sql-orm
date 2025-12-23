#针对整个表操作，用类方法（查）
#针对特定数据行，用实例方法（增删改）
import sqlite3
import pymysql
import queue
#元类,收集field字段创建映射关系
class ModelMeta(type):
    #cls:自己(ModelMeta) name:创建的类(User)  bases:类的父亲(Model)  attrs创建的类的类属性(id:实例,name:实例)等
    def __new__(cls,name,bases,attrs):
        fields = {}
        for key,value in attrs.items():
            if isinstance(value,Field):
                fields[key] = value
            elif isinstance(value,Foreignkey):
                fields[key] = value
        attrs['_fields'] = fields
        for key,value in attrs.items():
            if isinstance(value,Foreignkey):
                attrs['_foreign_key_field'] = key
                break
        return super().__new__(cls,name,bases,attrs)

# 连接工厂,选择连接的数据库类型(sqlite or mysql)
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


#定义字段类型    
class Field:
    def __init__(self,ftype,primary_key = False):
        self.ftype = ftype
        self.primary_key = primary_key
class Foreignkey(Field):
    def __init__(self, ftype, primary_key=False):
        super().__init__(ftype, primary_key)
#创建sql查询条件(比如where)
class Query:
    def __init__(self,model_class,conn):#model_class是个类(表名USER)
        self._conn = conn
        self.table = model_class.__name__
        self.model_class = model_class
        self.where_sql = ""
        self.join_sql = ""
        self.limit_sql = ""
        self.order_by_sql = ""
        self.group_by_sql = ""
        self.offset_sql = ""
        self.values = []
        self.option_map = {'gt':'>','lt':'<','gte':'>=','lte':'<=','like':'like','in':'in','ne':'!='}
    #way可以是left，right，inner
    def join(self,table,condition=None,way=None):
        if condition:
            table_name = table.__name__ if hasattr(table,'__name__') else str(table)
            if not way:
                self.join_sql += f" JOIN {table_name} ON {condition} "
            if way:
                self.join_sql += f" {way} JOIN {table_name} ON {condition} "
            return self
        else:
            fk1 = getattr(self.model_class,'_foreign_key_field',None)
            fk2 = getattr(table,'_foreign_key_field',None)
            if not fk1 or not fk2:
                raise ValueError("表缺少外交键,无法自动推导,请手动输入condition")
            condition = f"{self.model_class.__name__}.{fk1}={table.__name__}.{fk2}"
            if condition:
                table_name = table.__name__ if hasattr(table,'__name__') else str(table)
            if not way:
                self.join_sql += f" JOIN {table_name} ON {condition} "
            if way:
                self.join_sql += f" {way} JOIN {table_name} ON {condition} "
            return self
            
    def count(self,field_name):
        self.limit_sql = ''
        self.order_by_sql = ''
        if not field_name in self.model_class._fields.keys() and field_name != '*':
            raise ValueError(f"没有该键{field_name}")
        else:
            sql = f"SELECT COUNT({field_name}) FROM {self.model_class.__name__}" + self.where_sql
            result = self._conn.execute(sql,self.values)
            return result[0][0] if result else 0
    def max(self,field_name):
        self.limit_sql = ''
        self.order_by_sql = ''
        if not field_name in self.model_class._fields.keys():
            raise ValueError(f"没有该键{field_name}")
        else:
            sql = f"SELECT MAX({field_name}) FROM {self.table}" + self.where_sql
            result = self._conn.execute(sql,self.values)
            return result[0][0] if result else None
    def min(self,field_name):
        self.limit_sql = ''
        self.order_by_sql = ''
        if not field_name in self.model_class._fields.keys():
            raise ValueError(f"没有该键{field_name}")
        else:
            sql = f"SELECT MIN({field_name}) FROM {self.table}" + self.where_sql
            result = self._conn.execute(sql,self.values)
            return result[0][0] if result else None
    def sum(self,field_name):
        self.limit_sql = ''
        self.order_by_sql = ''
        if not field_name in self.model_class._fields.keys():
            raise ValueError(f"不存在的键{field_name}")
        else:
            sql = f'SELECT SUM({field_name}) FROM {self.table}' + self.where_sql
            result = self._conn.execute(sql,self.values)
            return result[0][0] if result else None
    def avg(self,field_name):
        self.limit_sql = ''
        self.order_by_sql = ''
        if not field_name in self.model_class._fields.keys():
            raise ValueError(f"不存在的键{field_name}")
        else:
            sql = f'SELECT AVG({field_name}) FROM {self.table}' + self.where_sql
            result = self._conn.execute(sql,self.values)
            return result[0][0] if result else None
    def first(self):
        sql = f"SELECT * FROM {self.table}"+self.where_sql+self.order_by_sql+self.limit_sql
        results = self._conn.execute(sql,self.values)
        if results:
            row = results[0]
            instance = self.model_class()
            for i,field in enumerate(self.model_class._fields.keys()):
                setattr(instance,field,row[i])
            return instance
        else:
            return None
    def order_by(self,field,way='ASC'):
        if way.upper() not in ['DESC','ASC']:
            raise ValueError("排序方法key只能是desc或asc")
        if not self.order_by_sql:
            self.order_by_sql = f" ORDER BY {field} {way}"
        else:
            self.order_by_sql += f",{field} {way}"
        return self
    def group_by(self,field_name):
        if field_name not in self.model_class._fields.keys():
            raise ValueError(f"不存在键{field_name}")
        else:
            self.group_by_sql += f" GROUP BY {field_name} "
    def limit(self,n):
        self.limit_sql += f" LIMIT {n} "
        return self
    def offset(self,start_index):
        self.offset_sql += f"OFFSET {start_index}"
        return self
    #约定
    #__gt：大于 >
    # __lt：小于 <
    # __gte：大于等于 >=
    # __lte：小于等于 <=
    # __like：模糊匹配 LIKE
    # __in：在列表中 IN
    # __ne：不等于 !=
    def filter(self,**kwargs):
        if not kwargs:
            return self
        conditions = []
        for key,value in kwargs.items():
            if '__' in str(key):
                try:
                    field_name,option = key.rsplit('__',1)
                except ValueError:
                    print('最多存在一个"__"符号')
                if field_name not in self.model_class._fields.keys():
                    raise KeyError(f"不存在这个键{field_name}")
                if option.upper()=='IN' and isinstance(value,list):
                    condition = ','.join(['?']*len(value))
                    conditions.append(f'{field_name} IN ({condition})')
                    self.values.extend(value)
                    continue
                elif option in self.option_map:
                    conditions.append(f'{field_name} {self.option_map[option]}?')
                else:
                    raise ValueError(f"不支持这个操作符:{option}")
            elif '.' in str(key):
                conditions.append(f"{key}=?")
            else:
                conditions.append(f"{key}=?")
            self.values.append(value)
        if not self.where_sql:
            self.where_sql =" WHERE "+" AND ".join(conditions)
        else:
            self.where_sql+=" AND " + " AND ".join(conditions)
        return self
    
    
    def get_cache_key(self, *fields):
        parts = [
            str(self.table),
            str(self.join_sql),
            str(self.where_sql),
            str(self.order_by_sql),
            str(self.limit_sql),
            str(self.offset_sql),
            str(self.group_by_sql),
            str(tuple(self.values)),
            str(fields)
        ]
        return hash('-'.join(parts))
    _cache = {}
    @classmethod
    def clear_cache(cls):
        cls._cache.clear()
    def all(self):#返回的是user的列表，可以用类似于user.id的格式查询属性,或者使用getattr方法
        cache_key = self.get_cache_key()
        if cache_key in Query._cache:
            print("从缓存中获取结果")
            return Query._cache[cache_key]
        instances = []
        sql = f"SELECT {self.table}.* FROM {self.table} {self.join_sql}"+self.where_sql+self.order_by_sql+self.limit_sql+self.offset_sql+self.group_by_sql
        print(sql,self.values)
        rows = self._conn.execute(sql,self.values)
        fields = list(self.model_class._fields.keys())#储存所有字段名
        for row in rows:
            instance = self.model_class()
            for i,field in enumerate(fields):
                setattr(instance,field,row[i])
            instances.append(instance)
        Query._cache[cache_key] = instances
        return instances    

    def part(self,*fields):
        cache_key = self.get_cache_key(*fields)
        if cache_key in Query._cache:
            print("走缓存！")
            return Query._cache[cache_key]
        instances=[]
        select_fields="*" if not fields else ",".join(fields)
        sql=f"SELECT {select_fields} FROM {self.table}"+self.where_sql+self.order_by_sql+self.limit_sql+self.offset_sql+self.group_by_sql
        rows=self._conn.execute(sql,self.values)
        model_fields=list(self.model_class._fields.keys())
        for row in rows:
            instance=self.model_class()
            for f in model_fields:
                setattr(instance,f,None)
            if select_fields=="*":
                for i,f in enumerate(model_fields):setattr(instance,f,row[i])
            else:
                for i,f in enumerate(fields):setattr(instance,f,row[i])
            instances.append(instance)
        Query._cache[cache_key]=instances
        return instances

#提供save,delete,query等基础方法
class Model(metaclass=ModelMeta):
    _db_type_ = 'sqlite'
    def __init__(self, **kwargs):
        if kwargs:
            for key, value in kwargs.items():
                setattr(self, key, value)

    @classmethod
    def use_db(cls,_db_type_ = 'sqlite'):
        setattr(cls,'_db_type_',_db_type_)
    
    @classmethod
    def query(cls):
        db_type = getattr(cls,'_db_type_','sqlite')
        with ConnectionFactory.get_connection(db_type) as conn:
            return Query(cls,conn)
    def __repr__(self):
        fields=[]
        for field in self._fields.keys():
            value=getattr(self,field,None)
            if value is not None:  
                fields.append(f"{field}={value}")
        return f"<{self.__class__.__name__}>({', '.join(fields)})\n"
    
    def save(self):
        db_type = getattr(self.__class__,'_db_type_','sqlite')
        pk_field = None
        for field_name,field_obj in self._fields.items():
            if field_obj.primary_key:
                pk_field = field_name
        field_names = list(self._fields.keys())
        values = [getattr(self,f) for f in field_names]
        if not pk_field:
            pk_field = field_names[0]
        if db_type.upper() == 'SQLITE':
            sql = f"""
                    INSERT INTO {self.__class__.__name__} ({','.join(field_names)})
                    VALUES ({','.join(['?']*len(field_names))})
                    ON CONFLICT({pk_field}) DO UPDATE SET {','.join([f'{f}=excluded.{f}' for f in field_names])}
                """
        elif db_type.upper() == 'MYSQL':
            existed = self.__class__.query().part(pk_field)
            pk_values = [getattr(instance, pk_field) for instance in existed]
            if getattr(self,pk_field) in pk_values:
                set_sql = ','.join([f"{f}=?" for f in field_names if f != pk_field])
                where_sql = f'{pk_field}=?'
                values = [getattr(self, f) for f in field_names if f != pk_field]
                values.append(getattr(self, pk_field))
                sql =f"""
UPDATE {self.__class__.__name__} SET {set_sql} WHERE {where_sql}
"""
            else:
                sql = f"""
                    INSERT INTO {self.__class__.__name__} ({','.join(field_names)})
                    VALUES ({','.join(['?']*len(field_names))})"""
        with ConnectionFactory.get_connection(db_type) as conn:
            conn.execute(sql,values)
            print(sql,values)
            Query.clear_cache()

    #删除字段(DELETE)
    def delete(self,**kwargs):
        db_type = getattr(self.__class__, '_db_type_').lower()
        with ConnectionFactory.get_connection(db_type) as conn:
            values = [value for value in kwargs.values()]
            condition_sql = []
            for key in kwargs.keys():
                condition_sql.append(f"{key}=?")
            sql = f"DELETE FROM {self.__class__.__name__} WHERE {' AND '.join(condition_sql)}"

            conn.execute(sql,values)
            Query.clear_cache()
    #清空表
    def truncate(self):
        db_type = getattr(self.__class__, '_db_type_').lower()
        with ConnectionFactory.get_connection(db_type) as conn:
            sql = f"DELETE FROM {self.__class__.__name__}"
            conn.execute(sql)
    @classmethod
    def create_table(cls):
        db_type = getattr(cls,'_db_type_','sqlite')
        with ConnectionFactory.get_connection(db_type) as conn:
            li = []
            for field_name,field_obj in cls._fields.items():
                if isinstance(field_obj,Field):
                    col_def = field_obj.ftype
                    if field_obj.primary_key:
                        col_def+=f' PRIMARY KEY'
                    li.append(f"{field_name} {col_def}")
            sql = f"CREATE TABLE IF NOT EXISTS {cls.__name__}({",".join(li)})"
            conn.execute(sql)
