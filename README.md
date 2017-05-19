

# Darter

Darter 是基于 Python3 win32com 实现的 AutoCAD API, 实现了部分绘图, 查询功能, 提供了一些适用于建筑, 地形图绘制的工具.



## 使用方式:

获取当前文档的基本信息

    cad = AutoCAD()
    cad.open('/path/tp/file.dwg')
    print(cad.path)
    print(cad.title)

创建 AutoCAD 对象

    cad = AutoCAD()
    cad.add_text("foo", (100, 200), height=5, alignment='center')
    cad.add_text("bar", [100, 200], height=5, alignment='left')
    rectang = cad.add_rectangle((10, 10), (300, 400))
    print(rectang, rectang.color, rectang.entity_type, rectang.area)
    circle = cad.add_circle([3.2, 5.3], radius=10)
    print(circle)

使用 AutoCAD 内建 CMD

    cad.send_command('zoom e')


