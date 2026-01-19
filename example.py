注意！这个文件不能正常工作，只是一个模板！需要保持文件夹ORM与你的py文件同等级

# 改配置模板和例子如下，放在您的py文件开头即可
from ORM.config import DatabaseConfig
# 配置MySQL（如果你是MySQL用户）
DatabaseConfig.configure_mysql(
    host='127.0.0.1', #主机名
    user='root',  #改为用户名
    password='123456',   #改为您的密码
    database='database_name',  #改为您的数据库名
    port=3306
)
# 配置sqlite（如果你是sqlite用户）
DatabaseConfig.configure_sqlite(db_file='file_name.db')
# 连接池大小
DatabaseConfig.set_pool_size(size=10)
# 然后正常使用ORM即可
from ORM import Model, Field, Foreignkey
# 例子：
class User(Model):
    id = Field("INTEGER", primary_key=True)
    name = Field("TEXT")
    age = Field("INTEGER")

User.use_db('mysql')

# 创建表（如果不存在）
User.create_table()

# 插入数据
user = User(id=1, name="张三", age=25)
user.save()

# 查询数据
users = User.query().filter(age__gte=18).all()
for u in users:
    print(f"{u.id}: {u.name}, {u.age}")