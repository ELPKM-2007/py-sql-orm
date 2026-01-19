# 为了您方便使用，请读完以下内容
# 这是一个python与sql间适用sqlite和mysql的简单ORM框架，可以实现大部分日常使用与开发，
# 如果能够对您产生帮助，或者您认为做得不错，希望能够得到您的star，感激不尽
# 5步上手这个ORM(你也可以直接看example.py中的模板和示例)
# 1.把这个文件夹“ORM”和你的python文件在同一个文件夹中
# 2.在你的python文件开头，复制这行代码：
    from ORM import Model,Foreignkey,Field
# 3.配置MySQL连接（必须如果你要用于MySQL），sqlite数据库文件（建议如果你要用于sqlite），连接池大小（可选如果你的使用规模并不大）
    方法如下(本文件最后会给模板，可以跳过这里然后直接复制模板)：
        先从ORM.config导入DatabaseConfig，数据库连接数据就是用的这个的数据。有以下三个方法：
            1.configure_mysql(host,user,password,database,port)
            2.configure_sqlite(db_file=myorm.db)
            3.set_pool_size(size=5)

# 4.定义你的表(类)，格式(模板)如下：
    class "这里类名就是你的表名"(Model):     ---如果没有表需要创建，语法是：   类名(也就是表名).create_table()
        字段1 = Field("字段类型")
        字段2 = Field("字段类型")
        ......
    这里可以传入参数primary_key=(True or False),之后该字段为主键，一个表只能有一个

    Field的一个特殊形式：Foreignkey，是一种简单处理“表连接”的特殊外交字段：每个表只能有一个(若多个则按第一个Foreignkey处理)
    当我们连接两个表时，需要传参数condition表示连接条件，如果不传condition参数，则两个表的连接条件就是：两个表的外交字段对应的值相等
# 5.如果你要操作Mysql表，你需要再加一行：
    类名.use_db('mysql')
    默认使用sqlite
# 接下来你就可以使用你的py文件操作你的sql了！以下内容是增删改查教程
# 以下例子中，表(类)为User(字段为id和name),实例为u
# 增：
    u = User()
    u.id=1
    u.name='ELPKM'
    u.save()
    这样就保存成功啦！如果primary_key冲突，就会自动改为update语句！
    当然，你也可以：
        u = User(id=1,name='ELPKM')
        u.save()
    或者类似于以下操作也是允许的:
        u = User(id=1)
        u.name = 'ELPKM'
        u.save()
# 删:
    删除某一行：
    u = User()
    u.delete(id=1)   ---括号中类似于WHERE条件，传多少都可以
    清空整个表(谨慎使用)
    u.truncate()

改操作需要建立在查的基础上，所以先介绍最重要的查
    
# 查：(注意，查询结果需要print出来)
    所有查操作的开头都应该以以下方法开头:
        User.query()
        返回的是查询器，然后就可以添加各种各样的查询条件了
    所有查操作的最后都应该以以下方法结尾：
        .all()  返回查询到的所有记录
        .first()    返回查询到的记录中的第一条
        .part(field)    返回查询结果中的field字段
        .聚合函数(field)    聚合函数
    增加查询条件的方法：
        改where条件：
            .filter(**kwargs),kwarg是输入查询条件
            例如查询id为1的字段
                User.query().filter(id=1).all()
            默认为等于，也可以实现其它条件
            约定如下，注意是双下划线
            __gt：大于 >
             __lt：小于 <
             __gte：大于等于 >=
             __lte：小于等于 <=
             __like：模糊匹配 LIKE
             __in：在列表中 IN
             __ne：不等于 !=
            例如查询id大于1的字段
                User.query().filter(id__gt=1)
        改limit条件：
            .limit(m)，m是数字
            例如查询只查询两条数据：
                User.query().limit(2).all()
        改offset条件(也就是limit m offset n):
            .offset(n)，n是跳过前n条
            例如取第11-20条：
                User.query().limit(10).offset(10).all()
        改order by条件：
            .order_by(field,way) field是字段名，way是排序方法（默认ASC）
            例如按照id升序排序：
                User.query().order_by(id,asc).all()
        改group by条件：
            .group_by(field) field是字段名
            例如按照id分组（实际上不太可能用这个，仅作为参考）
                User.query().group_by(id).all()
    使用聚合函数的方法:（注意使用字符串）
        函数名（字段名）
            支持的聚合函数：count，max，min，sum，avg
            例如：查询id大于1的字段的数量
                User.query().filter(id__gt=1).count('id')
改:
    要改某条数据，首先查到“某条数据”
    例如把id为1的那条数据的name改为“小明”:
        u = User.query().filter(id=1).first()   ---注意要用first，或者用all后取[0]，否则无法正确定位
        u.name = '小明'
        u.save()

连接查询：
    join(表名,条件,方式)
    表名就是要连接的表名
    条件要自己写sql，如果没有条件，那就会尝试用两表的外交键，如果任意一表缺少外交键，那么报错
            

其它类方法:
    use_db(),参数可传"mysql"或"sqlite"，代表切换那个表的数据库类型(除了mysql用户要使用一次，大概也用不到)