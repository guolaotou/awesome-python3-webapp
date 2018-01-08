#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'Laotou Guo'

'''
Configuration
'''

import config_default
def merge(defaults,override):#收集参数
    r = {}
    for name,value in defaults.items():
        if name in override: #覆盖文件有此参数
            if isinstance(value,dict): #判断是否其value为dict
                r[name] = merge(value,override[name]) #是的话，则创建新的字典后，调用原函数（递归）
            else:
                r[name] = override[name] #否则把覆盖配置文件的值导入
        else:
            r[name] = defaults[name] #如果覆盖文件没有，就继续使用默认值
    return r

configs = config_default.configs

try:
    import config_override
    merge(configs, config_override.configs)
    print(merge(configs, config_override.configs))
except ImportError:
    pass
