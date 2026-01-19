from .query import Query
from .connections import ConnectionFactory
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

#定义字段类型    
class Field:
    def __init__(self,ftype,primary_key = False):
        self.ftype = ftype
        self.primary_key = primary_key
class Foreignkey(Field):
    def __init__(self, ftype, primary_key=False):
        super().__init__(ftype, primary_key)

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