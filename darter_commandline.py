

from pylon import datalines
from pylon import puts
from lib.autocad import AutoCAD
# from lib.entity import AutoCADEntityError

cad = AutoCAD()
entities = list(cad.selecting())



def test_dim_area():
  '标注对象面积'
  cad.dim_area(entities)
  '标注对象面积 加单位后缀 保留5位小数'
  cad.dim_area(entities, unit='m²', precision=5)
  print(list(entities))


def test_dim_road():
  '''标注道路名称'''
  cad.prompt('----------------\n--------------')
  cad.prompt('标注道路名称 鼠标指定起点终点')
  r = cad.dim_road(name='测试道路', rotate=True, match_existing=False, arc_path=False)
  print(r)

  cad.prompt('----------------\n--------------')
  cad.prompt('标注道路名称 如果之前已选中文字则匹配选中文字样式')
  r = cad.dim_road(name='测试道路', rotate=True, match_existing=True, arc_path=False)
  print(r)

  cad.prompt('----------------\n--------------')
  cad.prompt('标注道路名称 不旋转文字')
  r = cad.dim_road(name='测试道路', rotate=False, match_existing=False, arc_path=False)
  print(r)

  cad.prompt('----------------\n--------------')
  cad.prompt('标注道路名称 指定圆弧起点 弧顶点 终点')
  r = cad.dim_road(name='测试道路', rotate=True, match_existing=False, arc_path=True)
  print(r)


def test_arrange_text():
  '''重新排布文字位置使之变整齐'''
  cad.arrange_text(entities, auto_size=True)



def test_dim_polyline_vertex_and_sides():
  ''' 标注 Polyline 界址点号 界址边长 界址点圆圈消隐
      多个Polyline则按照选定顺序连续标记'''
  polylines = entities
  cad.dim_polyline_vertex_and_sides(polylines,
                                    height=5,
                                    vertex_index_start=1,
                                    vertex_label_prefix='J',
                                    draw_vertex_label=True,
                                    draw_segment_length=True,
                                    vertex_label_layer='dim_jzd_index',
                                    side_length_label_layer='dim_length',
                                    generate_vertex_circle=True
                                    )

def test_dim_polyline_vertex_and_sides_auto():
  '''标注 Polyline 界址点号 界址边长 界址点圆圈消隐 自动选择文字大小'''
  polylines = entities
  cad.dim_polyline_vertex_and_sides(polylines, height='auto')










# ==========================



def todo_dim_polyline_vertex_and_sides_arc():
  '''标注 Polyline 界址点号 界址边长 正确处理圆弧 反尖角'''
  polylines = entities
  cad.dim_polyline_vertex_and_sides(polylines, height='auto')









def test_report_entities():
  '报告选中对象的信息'
  cad = AutoCAD()
  entities = list(cad.selecting())
  r = cad.report_entities(entities, hole=False, error_color=None, error_layer=None)
  print(r)



def test_report_area():
  '统计面积'
  cad = AutoCAD()
  entities = list(cad.selecting())
  r = cad.report_area(*entities, island=False)
  print(r)





def test_add_polyline():
  '''以输入坐标画polyline'''

  cad.add_polyline(430710.1, 856920.4,
                   430715.1, 856825.4,
                   430650.1, 856950.4)

  cad.add_polyline([430731.8, 856931.9],
                   [430735.8, 856841.9],
                   [430632.8, 856933.9],
                   closed=True)










######   #####  ##   ##   ## ##      ###### ##   ## #######
##   ## ##   ## ##   ##   ## ##        ##   ###  ## ##
######  ##   ## ##    #####  ##        ##   ## # ## ######
##      ##   ## ##      ##   ##        ##   ##  ### ##
##       #####  ####### ##   ####### ###### ##   ## #######

####### ###### ###### #######
##      ##   ##  ##      ##
######  ##   ##  ##      ##
##      ##   ##  ##      ##
####### ###### ######    ##

def test_remove_same_point_polyline():
  '移除poly中的重复节点'
  cad = AutoCAD()
  for pl in cad.selecting():
    plnew, report = cad.remove_same_points_polyline(pl, threshold=0.0001)
    puts(report)

def test_rebuild_arc_polyline():
  '''将加密后的poly转为圆弧poly
  处理选中的多段线
  如果有选中的点, 将这些点作为分隔符'''
  cad = AutoCAD()
  polylines = []
  points = []
  for en in cad.selecting():
    if en.entity_type == 'Point':
      points.append(en)
    elif en.entity_type == 'Polyline' and en.closed:
      polylines.append(en)

  dist = 3

  for pl in polylines:
    arcpl = cad.rebuild_arc_polyline(pl, threshold=dist,
                                     segment_points=[(p.x, p.y) for p in points])
    arcpl.color = 'yellow'
    report = '转为圆弧poly 原面积={:.4f} 新面积={:.4f} 相差={:.4f} ({:.4%})'
    puts(report.format(pl.area, arcpl.area, arcpl.area - pl.area, (arcpl.area-pl.area)/pl.area))


def test_de_intepolate_polyline():
  '''多段线抽稀'''
  cad = AutoCAD()
  for pl in cad.selecting():
    interpl, report = cad.de_interpolate_polyline(pl, threshold=3)
    if abs(interpl.area - pl.area) < 30:
      interpl.color = 'green'
      pl.delete()
    else:
      interpl.delete()
    puts('多段线抽稀 report=')


def test_intepolate_polyline():
  '''多段线加密'''
  cad = AutoCAD()
  for pl in cad.selecting():
    # distance = 0.3
    distance = 0.2
    interpl, report = cad.interpolate_polyline(pl, distance=distance, delete_original=True, break_at_vertexes=False)
    interpl.color = 'green'
    puts('多段线加密')


def test_intepolate_polyline_dx():
  '''多段线加密 and 分割为多段线的碎片'''
  cad = AutoCAD()
  for pl in cad.selecting():
    # distance = 0.3
    distance = 0.2
    interpl, report = cad.interpolate_polyline(pl, distance=distance, delete_original=True, break_at_vertexes=True)
    puts('多段线加密 分割为多段线的碎片')



def test_redraw_vertex_sequence():
  '''重绘多段线的顶点顺序'''
  cad = AutoCAD()
  for pl in cad.selecting():

    first = None  # first = -1
    redrawpl = cad.redraw_vertex_sequence(pl, first=first,
                                          hint=False,
                                          auto_reverse=True)
    redrawpl.color = 'yellow'
    puts('重绘顶点顺序')










def test_gcd():
  '''读取高程点'''
  cad = AutoCAD()
  file_path = 'path'
  for line in datalines(open(file_path).read()):
    index, _, x, y, elevation = line.split(',')
    cad.add_text(elevation, origin=(float(x), float(y)))
    cad.add_point(float(x), float(y))




def test_gcd_string():
  '''读取高程点 读取坐标点'''
  s = '''

  # 01,,376173,875806,20.812
  # 01,,376167,875809,20.881
  # 01,,376298,875822,20.780
  # 01,,376295,875827,20.744
  # 01,,376399,875735,20.760
  # 01,,376405,875734,20.872

  j6,,376230.527,875750.679,20.947
  j5,,376226.292,875743.894,20.787
  j8,,376314.162,875580.859,20.039
  j7,,376308.053,875584.223,20.903
  j1,,376051.421,875669.464,20.911
  j2,,376122.484,875534.670,20.916
  j3,,376121.527,875531.260,20.973

  '''


  s = '''

    376897.510 871120.891
    376917.510 871120.891
    376917.510 871100.891
    376897.510 871100.891
    376127.488 878184.564
    376172.488 878184.564
    376172.488 878174.564
    376127.488 878174.564

  '''
  cad = AutoCAD()
  for line in datalines(s):
    index, _, x, y, elevation = line.split(',')
    cad.add_text(elevation, origin=(float(x), float(y)))
    cad.add_point(float(x), float(y))











def test_windows_com():
  '测试windows com接口'
  import win32com.client
  # import pythoncom
  # import win32api
  import platform
  v = platform.uname().release
  print(v)
  print(platform.uname())
  app = win32com.client.Dispatch('AutoCAD.Application.20')
  # app.ActiveDocument
  app.Visible = True



def test_sum_area():
  print(111)
  cad = AutoCAD()
  areas = []
  for text in cad.selecting():
    print(text.text)
    areas.append(float(text.text))

  print('sum', sum(areas))



def test_detect_duplicate():
  cad = AutoCAD()
  heding = []
  dk = []
  for en in cad.selecting():
    if en.layer == '0':
      dk.append(en)
    else:
      heding.append(en)
  areas = set(round(en.area, 0) for en in heding)
  mid_points = set('{:.0f}-{:.0f}'.format(*en.mid_point) for en in heding)
  print(areas)
  print(mid_points)

  for en in dk:
    if round(en.area, 0) in areas:
      if '{:.0f}-{:.0f}'.format(*en.mid_point) in mid_points:
        print(en)
        # en.layer = '重复'
        en.color = 'yellow'







def test_report_entities_1():
  cad = AutoCAD()
  s = set()
  for en in cad.selecting():
    if en.entity_type == 'Hatch':
      s.add(en.layer)
  print(s)



def test_compare_area():
  cad = AutoCAD()
  r = cad.compare_area(*list(cad.selecting()))
  print(r)




def test_find_nearest_text():
  cad = AutoCAD()
  entities = list(cad.selecting())
  numbers = []
  names = []
  for text in entities:
    if text.color == 'black':
      names.append(text)
    else:
      numbers.append(text)
  from Converter import SpaceCoordinate
  dist = SpaceCoordinate().distance2
  for number in numbers:
    near = min(names, key=lambda name: dist(name.mid_point, number.mid_point)) | puts()
    near.color = 'cyan'



def exec_ascii():
  from pylon import generate_figlet
  generate_figlet('polyline', fonts=['space_op'])
  generate_figlet('edit', fonts=['space_op'])

