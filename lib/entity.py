
import os
import time
import pylon
from pylon import puts
from converter import SpaceCoordinate
from converter import ColorEditor
from converter import CADVariant
from collections import namedtuple


import math




class AutoCADEntityError(Exception):
  pass






class AutoCADEntity(object):
  """CAD元素基类，生成所有多段线、文字等对象
  应该使用AutoDelegator

  ooooooooooo             o8   o88    o8
   888    88  oo oooooo o888oo oooo o888oo oooo   oooo
   888ooo8     888   888 888    888  888    888   888
   888    oo   888   888 888    888  888     888 888
  o888ooo8888 o888o o888o 888o o888o  888o     8888
                                            o8o888
  """

  ENTITY_TYPES = 'Text Circle Polyline Arc Line Region Hatch Point Wipeout'.split(' ')

  @staticmethod
  def create(entity):
    entity_type = entity.EntityName[4:]
    if entity_type in AutoCADEntity.ENTITY_TYPES:
      en = eval('AutoCAD{}(entity)'.format(entity_type))
      en.entity_type = entity_type
      return en
    else:
      en = eval('AutoCADEntity(entity)')
      en.entity_type = 'UnknownEntity'
      return en

  def __init__(self, entity):
    super(AutoCADEntity, self).__init__()
    self.entity = entity
    self.objectid = entity.ObjectID
    self.document = entity.Document
    self.entity_type = entity.EntityName[4:]

  @pylon.nested_property
  def color():
    doc = "color for CAD Entity"
    def fget(self):
      return ColorEditor().to_name(self.entity.color)
    def fset(self, value):
      if type(value) is int:
        self.entity.color = value
      elif type(value) is str:
        self.entity.color = ColorEditor().to_index(value)
    return locals()

  def random_color(self):
    self.entity.color = ColorEditor().random_index()

  @pylon.nested_property
  def layer():
    doc = "layer for CAD Entity"
    def fget(self):
      return self.entity.Layer
    def fset(self, lay_name):
      for lay in self.entity.Document.Layers:
        if lay_name == lay.Name:
          break
      else:
        self.entity.Document.Layers.Add(lay_name)
      self.entity.Layer = lay_name
    return locals()

  @property
  def area(self):
    try:
      return self.entity.Area
    except:
      raise AutoCADEntityError("can not find area attribute")

  def pr(self):
    return
    print(self.entity.objecttype)

  def __str__(self):
    return "<AutoCAD{} '{}' {}>".format(self.entity_type, self.entity.Handle, self.detail)

  @property
  def detail(self):
    return 'unknown'

  def delete(self):
    self.entity.Delete()
  # def methods; @entity.ole_get_methods.uniq.join(', '); end

  @property
  def handle(self):
    return "(handent \"{}\")".format(self.entity.Handle)

  @property
  def mid_point(self):
    min_point, max_point = self.entity.GetBoundingBox()
    return (min_point[0] + max_point[0])/2, (min_point[1] + max_point[1])/2

  @property
  def bounding_box_point(self):
    min_point, max_point = self.entity.GetBoundingBox()
    return min_point, max_point

  @property
  def bounding_box_size(self):
    min_point, max_point = self.entity.GetBoundingBox()
    return max_point[0] - min_point[0], max_point[1] - min_point[1]

  @property
  def bounding_box_diagonal(self):
    min_point, max_point = self.entity.GetBoundingBox()
    w, h = max_point[0] - min_point[0], max_point[1] - min_point[1]
    return math.sqrt(w*w+h*h)

  def clone(self):
    new_entity = self.entity.Copy()
    return AutoCADEntity.create(new_entity)

  def explode(self, WrapEntity=True):
    '''
    WrapEntity=True 返回炸开后的碎片
    WrapEntity=False 则不返回任何对象，适合炸开后会生成大量元素的场合

    Explode 不会删除原对象，需手动删，
    # 但是在AutoCAD2013调用Delete会报错，在2004没事
    '''
    if WrapEntity:
      ret = [AutoCADEntity.create(clip) for clip in self.entity.Explode()]
      # self.entity = None
    else:
      self.entity.Explode()
      ret = None

    self.document.SendCommand('erase {}  '.format(self.handle))
    return ret










class AutoCADPolyline(AutoCADEntity):
  """多段线实体

  oooooooooo            o888            o888  o88
   888    888  ooooooo   888 oooo   oooo 888  oooo  oo oooooo   ooooooooo8
   888oooo88 888     888 888  888   888  888   888   888   888 888oooooo8
   888       888     888 888   888 888   888   888   888   888 888
  o888o        88ooo88  o888o    8888   o888o o888o o888o o888o  88oooo888
                              o8o888
  """
  def __init__(self, polyline):
    super(AutoCADPolyline, self).__init__(polyline)

  @property
  def detail(self):
    if self.closed:
      return 'vertex_count={0.count}, area="{0.area:.2f}"'.format(self)
    else:
      return 'vertex_count={0.count}'.format(self)

  @property
  def coords(self):
    coords = list(self.entity.Coordinates)
    return list(zip(coords[::2], coords[1::2]))

  @property
  def count(self):
    return int(list(self.entity.Coordinates).__len__() / 2)

  def vertex(self, i):
    if i >= self.count:
      raise "hasnot more vertex"
    return self.coords[i]



  @pylon.nested_property
  # def closed?; @entity.closed; end
  def closed():
    doc = "set Polyline Closed"
    def fget(self):
      return self.entity.Closed
    def fset(self, value):
      self.entity.Closed = value
    return locals()

  # def centroid(self):
  #   # create an region
  #   region = self.entity.Document.add_region(self.clone)
  #   if region.type == "Polyline":
  #     raise "can not convert Polyline to Region <#{handle}>"
  #   cen = region.centroid
  #   region.delete
  #   return cen


  @property
  def constant_width(self):
    return self.entity.ConstantWidth


    # def vertexs
    #   @entity.coordinates.each_slice(2).map.to_a
    # end

    # def bounding_box_point
    #   all_x = vertexs.map(&:first)
    #   all_y = vertexs.map(&:last)
    #   [[all_x.min, all_y.min], [all_x.max, all_y.max]]
    # end

    # def bounding_size
    #   all_x = vertexs.map(&:first)
    #   all_y = vertexs.map(&:last)
    #   [all_x.max - all_x.min, all_y.max - all_y.min]
    # end



  def vertex_spatial(self, start=1):
    """ 返回polyline的每个节点信息, 其中 length radius 等是记录在该段的起点上的
    polyline是否闭合不会影响这些数据
    比如将一个polyline取消闭合, 最后一个节点仍然具有 length radius bulge
    start - 开始节点的标记索引号, 并不是rotate所有节点"""

    PolylineVertex = namedtuple('PolylineVertex', ['index', 'x', 'y', 'length', 'radius', 'bulge'])

    ret = []
    for i in range(0, self.count):
      pv = PolylineVertex(start+i,
                          self.vertex(i)[0],
                          self.vertex(i)[1],
                          self.segment_length(i),
                          self.segment_radius(i),
                          self.get_bulge(i)
                          )
      ret.append(pv)
    return ret





  def get_bulge(self, i):
    if i >= self.count:
      raise "hasnot more vertex"
    return self.entity.GetBulge(i)

  def bulges(self):
    return [self.get_bulge(i) for i in range(0, self.count)]
    # (0...count).map { |i| get_bulge(i)}

  def set_bulge(self, i, b):
    self.entity.SetBulge(i, b)


  def segment_length(self, i):
    if self.get_bulge(i) != 0:  # 需要计算圆弧弧长
      # radius * angle
      arc_len = self.segment_radius(i) * math.atan(self.get_bulge(i))*4
      return arc_len
    else:
      return self.segment_straight_length(i)


  def segments_lengths(self):
    # (0...vertex_count()).map { |i| length = segment_length(i) }
    return [self.segment_length(i) for i in range(self.count)]

  @property
  def length_total(self):
    if self.closed:
      return sum(self.segments_lengths())
    else:
      return sum(self.segments_lengths()) - self.segment_length(self.count-1)

  @property
  def length(self):
    return self.entity.Length


  def segment_straight_length(self, i):
    p1 = self.vertex(i)
    p2 = self.vertex(i+1) if i < self.count-1 else self.vertex(0)
    return SpaceCoordinate().distance(p2, p1)



  def segment_radius(self, i):
    if self.get_bulge(i) != 0:  # 需要计算圆弧弧长
      angle = math.atan(self.get_bulge(i))*4
      return 0.5 * self.segment_straight_length(i) / math.sin(angle/2)
    else:
      return 0

  @property
  def is_clockwise(self):
    area = self.entity.area
    pl_offset = self.entity.Offset(area * 0.0001)[0]
    offset_area = pl_offset.area
    pl_offset.delete()
    return offset_area < area

  def reverse(self):
    vertex_spatial = list(reversed(self.vertex_spatial(start=0)))

    coord = [(v.x, v.y) for v in vertex_spatial]
    com_points = CADVariant().points_list_to_variant(*coord)
    # 画新poly，但现在全是直线连接的
    pline = self.entity.Document.ModelSpace.AddLightweightPolyline(com_points)
    pline = AutoCADEntity.create(pline)
    pline.closed = self.closed
    # 重设poly内的圆弧
    # 原来2->3的bulge是记录在点2的，现在变成了点3。且bulge要取负数
    [pline.set_bulge(i, -vertex_spatial[(i+1) % self.count].bulge) for i, v in enumerate(vertex_spatial)]

    pline.color = self.color
    pline.layer = self.layer
    self.delete()
    return pline


  def offset(self, dist, outside=True):
    pl = self.entity.Offset(dist)[0]
    if outside and pl.area < self.entity.area:
      # p "reverting"
      pl.Delete()
      pl = self.entity.Offset(-dist)[0]
    return AutoCADEntity.create(pl)



  def get_segment_middle_point(self, i):
    v1 = self.vertex(i)
    v2 = self.vertex((i+1) % self.count)
    direct_mid = [(v1[0]+v2[0]) / 2, (v1[1]+v2[1]) / 2]
    if self.get_bulge(i) == 0:  # segment是直线
      return direct_mid
    else:  # segment是圆弧线, 需计算弧顶位置
      content_angle = math.atan(self.get_bulge(i)) * 4
      height = (1.0 - math.cos(content_angle/2)) * self.segment_radius(i)
      angle = math.asin((v2[1]-v1[1]) / SpaceCoordinate().distance(v1, v2)) - math.pi / 2
      return [height * math.cos(angle) + direct_mid[0], height * math.sin(angle) + direct_mid[1]]


  def segment_middle_points(self):
    return [self.get_segment_middle_point(i) for i in range(self.count)]

  def get_sin_angle(self, i):
    v1 = self.vertex(i)
    v2 = self.vertex((i+1) % self.count)
    return (v2[1]-v1[1]) / SpaceCoordinate.distance(v1, v2)

  def get_tan_angle(self, i):
    v1 = self.vertex(i)
    v2 = self.vertex((i+1) % self.count)
    return (v2[1]-v1[1]) / (v2[0]-v1[0])

  def tan_angles(self):
    return [self.get_tan_angle(i) for i in range(self.count)]



















class AutoCADHatch(AutoCADEntity):
  """Hatch实体

  ooooo ooooo            o8            oooo
   888   888   ooooooo o888oo ooooooo   888ooooo
   888ooo888   ooooo888 888 888     888 888   888
   888   888 888    888 888 888         888   888
  o888o o888o 88ooo88 8o 888o 88ooo888 o888o o888o

  """
  def __init__(self, hatch):
    super(AutoCADHatch, self).__init__(hatch)

  @property
  def detail(self):
    return 'pattern={0.pattern_name}'.format(self)

  @pylon.nested_property
  def pattern_name():
    doc = "set hatch pattern name"
    def fget(self):
      return self.entity.PatternName
    def fset(self, value):
      self.entity.SetPattern(1, value)
      # self.entity.Evaluate
      # self.document.Regen(True)
    return locals()

  def create_border(self):
    pass


class AutoCADRegion(AutoCADEntity):
  """Region实体"""
  def __init__(self, po):
    super(AutoCADRegion, self).__init__(po)

  @property
  def detail(self):
    return 'centroid={0.centroid}'.format(self)

  @property
  def centroid(self):
      return self.entity.Centroid[:2]








class AutoCADText(AutoCADEntity):
  """文字实体

  ooooooooooo                          o8
  88  888  88 ooooooooo8 oooo   oooo o888oo
      888    888oooooo8    888o888    888
      888    888           o88 88o    888
     o888o     88oooo888 o88o   o88o   888o

  """
  def __init__(self, entity):
    super(AutoCADText, self).__init__(entity)

  @property
  def detail(self):
    t = self.text
    if len(t) > 15:
      t = t[:10] + '...' + t[-5:]
    return 'text="{}"'.format(t)

  @pylon.nested_property
  def text():
    doc = "set text string"
    def fget(self):
      return self.entity.TextString
    def fset(self, value):
      self.entity.TextString = value
    return locals()

  @pylon.nested_property
  def size():
    doc = "set text size"
    def fget(self):
      return self.entity.Height
    def fset(self, value):
      self.entity.Height = value
    return locals()

  @pylon.nested_property
  def origin():
    doc = "set text origin"
    def fget(self):
      return self.entity.InsertionPoint[:2]
    def fset(self, value):
      self.entity.InsertionPoint = value
    return locals()

  @pylon.nested_property
  def style():
    doc = "set text style"
    def fget(self): return self.entity.StyleName
    def fset(self, value): self.entity.StyleName = value
    return locals()

  @pylon.nested_property
  def angle():
    doc = "set text angle"
    def fget(self): return self.entity.Rotation
    def fset(self, value): self.entity.Rotation = value
    return locals()

  @pylon.nested_property
  def width():
    doc = "set text width"
    def fget(self): return self.entity.ScaleFactor
    def fset(self, value): self.entity.ScaleFactor = value
    return locals()

  # From PyAuotocad
  @property
  def text_width(self, text_item):
    """Returns width of Autocad `Text` or `MultiText` object
    """
    bbox_min, bbox_max = self.bounding_box_point
    return bbox_max[0] - bbox_min[0]

  # TODO(Probe): 无法正确改变alignment点，需要再研究
  # ALIGNMENT_SETTING = {'left': 0, 'bottom': 1, 'center': 4}
  # ALIGNMENT_SETTING_DISPLAY = {0: 'left', 1: 'bottom', 4: 'center'}
  # @pylon.nested_property
  # def alignment():
  #   doc = "set text alignment"
  #   # "左对齐" Alignment 0
  #   # "底部居中" Alignment 1
  #   # "中间"  Alignment 4
  #   def fget(self):
  #     return self.ALIGNMENT_SETTING_DISPLAY[self.entity.Alignment]
  #   def fset(self, value): self.entity.Alignment = self.ALIGNMENT_SETTING[value]
  #   return locals()










class AutoCADPoint(AutoCADEntity):
  """Point实体

  oooooooooo            o88               o8
   888    888  ooooooo  oooo  oo oooooo o888oo
   888oooo88 888     888 888   888   888 888
   888       888     888 888   888   888 888
  o888o        88ooo88  o888o o888o o888o 888o

  """
  def __init__(self, po):
    super(AutoCADPoint, self).__init__(po)

  @property
  def detail(self):
    return 'x={0.x:.3f}, y={0.y:.3f}'.format(self)

  @property
  def x(self):
      return self.entity.Coordinates[0]

  @property
  def y(self):
      return self.entity.Coordinates[1]

  @property
  def origin(self):
      return tuple(self.entity.Coordinates)


class AutoCADCircle(AutoCADEntity):
  """Circle实体"""
  def __init__(self, circle):
    super(AutoCADCircle, self).__init__(circle)

  @property
  def detail(self):
    return 'x={0.x:.3f}, y={0.y:.3f}, R={0.radius:.2f}'.format(self)

  @property
  def radius(self):
      return self.entity.Radius

  @property
  def x(self):
      return self.entity.Center[0]

  @property
  def y(self):
      return self.entity.Center[1]

  @property
  def center(self):
      return tuple(self.entity.Center[:2])

  @property
  def origin(self):
      return self.center



class AutoCADArc(AutoCADEntity):
  """Arc实体"""
  def __init__(self, arc):
    super(AutoCADArc, self).__init__(arc)

  @property
  def detail(self):
    return 'R={0.radius:.2f}'.format(self)

  @property
  def radius(self):
    return self.entity.Radius

  @property
  def center(self):
    return tuple(self.entity.Center[:2])

  @property
  def origin(self):
    return self.center

  @property
  def angles(self):
    return (self.entity.StartAngle,self.entity.EndAngle)

  @property
  def start_angle(self):
    return self.entity.StartAngle

  @property
  def end_angle(self):
    return self.entity.EndAngle

  @property
  def start_point(self):
    return self.entity.StartPoint[:2]

  @property
  def end_point(self):
    return self.entity.EndPoint[:2]

  @property
  def arc_length(self):
    return self.entity.ArcLength





class AutoCADLine(AutoCADEntity):
  """Line实体"""
  def __init__(self, line):
    super(AutoCADLine, self).__init__(line)

  @property
  def detail(self):
    return 'L={0.length:.2f}'.format(self)

  @property
  def length(self):
    return self.entity.Length

  @property
  def start_point(self):
    return self.entity.StartPoint[:2]

  @property
  def end_point(self):
    return self.entity.EndPoint[:2]

  @property
  def center(self):
    return tuple(self.entity.Center[:2])

  @property
  def origin(self):
    return self.start_point

  @property
  def angle(self):
    return self.entity.Angle











class AutoCADRectangle(AutoCADPolyline):
  """Rectangle 多段线的特例，用于处理图边界，打印范围等"""
  def __init__(self, rec):
    super(AutoCADRectangle, self).__init__(rec)
    coords = self.coords()
    bottomleft = coords[0]
    self.origin = (bottomleft[0], bottomleft[1])
    topright = coords[2]
    self.width = topright[0] - bottomleft[0]
    self.height = topright[1] - bottomleft[1]






class AutoCADWipeout(AutoCADEntity):
  """Wipeout """
  def __init__(self, wipeout):
    super(AutoCADWipeout, self).__init__(wipeout)






















'''
ooooooooooo                         o8
88  888  88 ooooooooo8  oooooooo8 o888oo
    888    888oooooo8  888ooooooo  888
    888    888                 888 888
   o888o     88oooo888 88oooooo88   888o
'''



def test_cad_objs():
  from autocad import AutoCAD
  cad = AutoCAD()
  test_cad_path = './test_entity/'

  for doc in cad.temp_open(os.path.abspath(test_cad_path+'circle.dwg')):
    '''面域和图案填充'''

    cir = cad.last_entity()
    # puts(cir)
    assert cir.x == 3.0
    assert cir.y == 3.0
    assert cir.radius == 4.0
    # puts(cir.origin)
    assert cir.origin == (3.0, 3.0)

  for doc in cad.temp_open(os.path.abspath(test_cad_path+'point.dwg')):
    '''面域和图案填充'''
    po1, po2 = list(cad.last_entities(2))
    assert po1.x == 6.0
    assert po1.y == 8.0
    assert po2.x == 3.0
    assert po2.y == 3.0

  for doc in cad.temp_open(os.path.abspath(test_cad_path+'region_hatch.dwg')):
    '''面域和图案填充'''
    puts(list(cad.first_entities(2)))
    hat, reg = list(cad.first_entities(2))
    puts(hat)
    puts(reg)
    assert reg.centroid == (10.0, 5.0)
    assert reg.area == 8.0
    # assert hat.centroid == (5.0, 5.0)
    assert hat.area == 8.0
    assert hat.pattern_name == 'ANSI31'
    hat.pattern_name = 'SOLID'
    puts(hat)
    time.sleep(2)
    assert hat.pattern_name == 'SOLID'

  for doc in cad.temp_open(os.path.abspath(test_cad_path+'arc.dwg')):
    '''Arc'''
    arc = cad.last_entity()
    assert arc.center == (4.0, 6.0)
    assert arc.origin == (4.0, 6.0)
    assert arc.radius == 2.0
    puts(arc)
    puts(arc.arc_length, arc.start_angle)

  for doc in cad.temp_open(os.path.abspath(test_cad_path+'text.dwg')):
    '''text'''
    t = cad.last_entity(2)
    puts(t.text)
    t.text = 'another中文'
    assert t.text == 'another中文'
    assert t.size == 3.0
    t.size = 5
    assert t.size == 5.0
    puts(t.origin)
    t = cad.last_entity(1)
    assert t.style == '宋体'
    t.style = 'standard'
    assert t.angle == 0
    t.angle = 1
    assert t.angle == 1.0
    t = cad.last_entity()
    puts(t)
    time.sleep(2)


def test_cad_objs_alive():
  from autocad import AutoCAD
  cad = AutoCAD()
  for t in cad.last_entities(3):
    print(t)
    print(t.alignment)
    t.alignment = 'center'

    # assert text.center == (4.0, 6.0)
    # assert text.origin == (4.0, 6.0)
    # assert text.radius == 2.0
    # puts(text)
    # puts(text.arc_length, text.start_angle)











def exec_generate_ascii():
  pylon.generate_figlet(text='Entity', fonts=['o8'])
  pylon.generate_figlet(text='Test', fonts=['o8'])
  pylon.generate_figlet(text='Text', fonts=['o8'])
  pylon.generate_figlet(text='Point', fonts=['o8'])
  pylon.generate_figlet(text='Block', fonts=['o8'])
  pylon.generate_figlet(text='Hatch', fonts=['o8'])



