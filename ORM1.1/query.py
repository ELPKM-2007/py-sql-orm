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