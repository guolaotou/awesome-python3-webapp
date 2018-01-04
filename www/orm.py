#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# https://www.liaoxuefeng.com/wiki/0014316089557264a6b348958f449949df42a6d3a2e542c000/0014323389656575142d0bcfeec434e9639a80d3684a7da000#0

import asyncio, logging
import aiomysql

def log(sql, args=()):
    logging.info('SQL: %s' % sql)

# 创建连接池
@asyncio.coroutine
def create_pool(loop, **kw):
    logging.info('create database connection pool...')
    global __pool
    __pool = yield from aiomysql.create_pool(
        host = kw.get('host', 'localhost'),
        port = kw.get('port', 3306),
        user = kw['root'],
        password = kw['admin'],
        db = kw['db'],
        charset = kw.get('charset', 'utf8'),
        autocommit = kw.get('autocommit', True),
        maxsize = kw.get('maxsize', 10),
        minsize = kw.get('minsize', 1),
        loop = loop
    )


# select; 传入SQL语句和SQL参数
@asyncio.coroutine
def select(sql, args, size = None):
    log(sql, args)
    global __pool
    with (yield from __pool) as conn:
        cur = yield from conn.cursor(aiomysql.DictCursor)
        yield from cur.execute(sql.replace('?', '%s'), args or ())
        if size:
            rs = yield from cur.fetchmany(size)
        else:
            rs = yield from cur.fetchall()
        yield from cur.close()
        logging.info('rows returned: %s' %len(rs))
        return rs

# Insert, Update, Delete 统一函数 （需要在github上找完整代码）
@asyncio.coroutine
def execute(sql, args):
    log(sql)
    with(yield from __pool) as conn:
        try:
            cur = yield from conn.cursor()
            yield from cur.execute(sql.replace('?', '%s'), args)
            affected = cur.rowcount
            yield from cur.close()
        except BaseException as e:
            raise
        return affected

# 以下是ORM

# from orm import Model, StringField, IntegerField
#
# class User(Model):
#     __table__ = 'user'
#
#     id = IntegerField(primary_key = True)
#     name = StringField()

# 定义Model
# 1. 定义所有ORM映射的基类；
class Model(dict, metaclass=ModelMetaclass):
    def __init__(self, **kw):
        super(Model, self).__init__(**kw)

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"'Model' object has no attribute '%s'" %key)

    def __setattr__(self, key, value):
        self[key] = value

    def getValue(self, key):
        return getattr(self, key, None)

    def getValueOrDefault(self, key):
        value = getattr(self, key, None)
        if value is None:
            field = self.__mappings__[key]
            if field.default() is not None:
                value = field.default() if callable(field.default) else field.default
                logging.debug('using default value for %s: %s' % (key, str(value)))
                setattr(self, key, value)
        return value

    # 5. 往Model类添加实例方法，就可以让所有子类调用实例方法：
    # 直接复制 https://github.com/michaelliao/awesome-python3-webapp/blob/day-03/www/orm.py
    @classmethod
    async def findAll(cls, where=None, args=None, **kw):
        ' find objects by where clause. '
        sql = [cls.__select__]
        if where:
            sql.append('where')
            sql.append(where)
        if args is None:
            args = []
        orderBy = kw.get('orderBy', None)
        if orderBy:
            sql.append('order by')
            sql.append(orderBy)
        limit = kw.get('limit', None)
        if limit is not None:
            sql.append('limit')
            if isinstance(limit, int):
                sql.append('?')
                args.append(limit)
            elif isinstance(limit, tuple) and len(limit) == 2:
                sql.append('?, ?')
                args.extend(limit)
            else:
                raise ValueError('Invalid limit value: %s' % str(limit))
        rs = await select(' '.join(sql), args)
        return [cls(**r) for r in rs]

    @classmethod
    async def findNumber(cls, selectField, where=None, args=None):
        ' find number by select and where. '
        sql = ['select %s _num_ from `%s`' % (selectField, cls.__table__)]
        if where:
            sql.append('where')
            sql.append(where)
        rs = await select(' '.join(sql), args, 1)
        if len(rs) == 0:
            return None
        return rs[0]['_num_']

    @classmethod
    async def find(cls, pk):
        ' find object by primary key. '
        rs = await select('%s where `%s`=?' % (cls.__select__, cls.__primary_key__), [pk], 1)
        if len(rs) == 0:
            return None
        return cls(**rs[0])

    async def save(self):
        args = list(map(self.getValueOrDefault, self.__fields__))
        args.append(self.getValueOrDefault(self.__primary_key__))
        rows = await execute(self.__insert__, args)
        if rows != 1:
            logging.warn('failed to insert record: affected rows: %s' % rows)

    async def update(self):
        args = list(map(self.getValue, self.__fields__))
        args.append(self.getValue(self.__primary_key__))
        rows = await execute(self.__update__, args)
        if rows != 1:
            logging.warn('failed to update by primary key: affected rows: %s' % rows)

    async def remove(self):
        args = [self.getValue(self.__primary_key__)]
        rows = await execute(self.__delete__, args)
        if rows != 1:
            logging.warn('failed to remove by primary key: affected rows: %s' % rows)


# 2. Field 和各种Field子类
class Field(object):
    def __init__(self, name, column_type, primary_key, default):
        self.name = name
        self.column_type = column_type
        self.primary_key = primary_key
        self.default = default

    def __str__(self):
        return '<%s, %s:%s>' % (self.__class__.__name__, self.column_type, self,name)

# 3. 映射varchar的StringField 等等
class StringField(Field):
    def __init__(self, name = None, primary_key = False, defalt = None, ddl = 'varchar(100)'):
        super().__init__(name, ddl, primary_key, default)

    class BooleanField(Field):
        def __init__(self, name=None, default=False):
            super().__init__(name, 'boolean', False, default)

    class IntegerField(Field):
        def __init__(self, name=None, primary_key=False, default=0):
            super().__init__(name, 'bigint', primary_key, default)

    class FloatField(Field):
        def __init__(self, name=None, primary_key=False, default=0.0):
            super().__init__(name, 'real', primary_key, default)

    class TextField(Field):
        def __init__(self, name=None, default=None):
            super().__init__(name, 'text', False, default)
# 4. 读取具体的子类映射的信息
class ModelMetaclass(type):
    def __new__(cls, name, bases, attrs):
        # 排除Model类本身：
        if name == 'Model':
            return type.__new__(cls, name, bases, attrs)
        # 获取table名称：
        tableName = attrs.get('__table__', None) or name
        logging.info('found model: %s (table: %s)' % (name, tableName))
        # 获取所有的Field和主键名：
        mappings = dict()
        fields = []
        primaryKey = None
        for k, v in attrs.items():
            if isinstance(v, Field):
                logging.info('  found mapping: %s ==> %s' %(k, v))
                mappings[k] = v
                if v.primary_key:
                    # 找到主键
                    if primaryKey:
                        raise RuntimeError('Duplicate primary key for field: %s' %k)
                    primaryKey = k;
                else:
                    fields.append(k)
        if not primaryKey:
            raise RuntimeError('Primary key not found.')
        for k in mappings.key():
            attrs.pop(k)
        escaped_fields = list(map(lambda f: '`%s`' % f, fields))
        attrs['__mappings__'] = mappings # 保存属性和列的映射关系
        attrs['__table__'] = tableName
        attrs['__primary_key__'] = primaryKey # 主键属性名
        attrs['__fields__'] = fields # 除主键外的属性名
        # 构造默认的SELECT, INSERT, UPDATE和DELETE语句：
        attrs['__select__'] = 'select `%s`, %s from `%s`' %(primaryKey, ', '.join(escaped_fields), tableName)
        attrs['__insert__'] = 'insert into `%s` (%s, `%s`) values (%s)' % (tableName, ', '.join(escaped_fields), primaryKey, create_args_string(len(escaped_fields) + 1))
        attrs['__update__'] = 'update `%s` set %s where `%s`=?' % (tableName, ', '.join(map(lambda f: '`%s`=?' % (mappings.get(f).name or f), fields)), primaryKey)
        attrs['__delete__'] = 'delete from `%s` where `%s`=?' % (tableName, primaryKey)
        return type.__new__(cls, name, bases, attrs)




















