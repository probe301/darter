
import win32com.client
import pythoncom
import pylon
import math




class SpaceCoordinate(pylon.Singleton):
  """docstring for Space"""
  def __init__(self):
    pass


  def same_point(self, p1, p2, threshold=0.0000001):
    return ((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2) < threshold

  def distance(self, p1, p2):
    return math.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)

  def distance2(self, p1, p2):
    return (p1[0]-p2[0])**2 + (p1[1]-p2[1])**2


  def center(self, p1, p2, p3):
    '''已知三点求圆心'''
    a1, b1 = p1
    a2, b2 = p2
    a3, b3 = p3
    u = (a1**2 - a2**2 + b1**2 - b2**2) / (2*a1 - 2*a2)
    v = (a1**2 - a3**2 + b1**2 - b3**2) / (2*a1 - 2*a3)
    k1 = (b1-b2) / (a1-a2)
    k2 = (b1-b3) / (a1-a3)
    centerx = v - (u-v)*k2 / (k1-k2)
    centery = (u-v) / (k1-k2)
    return (centerx, centery)


  def point_angle(self, point, origin):
    """计算圆上点的角度
    角度制 范围 0-359"""
    x = point[0] - origin[0]
    y = point[1] - origin[1]

    if x == 0 and y == 0:
      raise ValueError('can not parse angle at origin')
    if x == 0:
      return 90 if y > 0 else 270
    if y == 0:
      return 0 if x > 0 else 180

    # r = self.distance(point, origin)
    # print('asin', math.asin(0.5) / (2 * math.pi) * 360)
    angle = math.atan(y / x) / (2 * math.pi) * 360
    if x < 0 and y < 0:
      angle += 180
    elif x < 0 and y > 0:
      angle += 180
    elif x > 0 and y < 0:
      angle += 360

    return angle


  def quadrant(self, point, origin=(0, 0)):
    x = point[0] - origin[0]
    y = point[1] - origin[1]
    if x * y == 0:
      return 0
    elif x > 0 and y > 0:
      return 1
    elif x < 0 and y > 0:
      return 2
    elif x < 0 and y < 0:
      return 3
    elif x > 0 and y < 0:
      return 4

  # 求直角三角形斜边长
  # print(math.hypot(3,4))
  # 求x的y次方
  # print(math.pow(2,3))
  # 求x的开平方
  # print(math.sqrt(4))
  # 截断，只取整数部分
  # print(math.trunc(2.3))
  # 判断是否NaN(not a number)
  # print(math.isnan(2.3333))







class ColorEditor(pylon.Singleton):
  """转换 AutoCAD 颜色 index 和颜色常用名"""
  def __init__(self):
    pass

  COLORS_DICT = {
    'by_block': 0,
    'by_layer': 256,
    'block': 0,
    'layer': 256,
    'red': 1,      'yellow': 2,   'green': 3,      'cyan': 4,      'blue': 5,
    'magenta': 6,  'white': 7,    'black': 7,      'grey': 8,      'red+': 12,
    'red-': 11,    'blue+': 174,  'blue-': 171,    'green+': 96,
    'green-': 91,  'cyan+': 142,  'cyan-': 121,    'orange': 30,
    'orange+': 32, 'orange-': 31, 'megenta+': 202, 'megenta-': 211,
    '102': 252,    '128': 8,      '192': 9,        '204': 254,      'white': 255
  }

  COLOR_NAMES_DICT = dict((v, k) for k, v in COLORS_DICT.items())

  def to_index(self, name):
    if isinstance(name, int):
      return name
    else:
      return self.COLORS_DICT.get(name, 256)

  def to_name(self, index):
    return self.COLOR_NAMES_DICT.get(index, index)

  def random_index(self, bright=True):
    if bright:
      # index color 12,22,32...242 and 13,23,33...243
      clr = (self.rand(24)+1)*10 + (self.rand(2)+2)
    else:
      clr = self.rand(1, 256)
    return clr

  def rand(self, a, b=None):
    return pylon.rand(a, b)










class CADVariant(pylon.Singleton):
  """数字或数组转换 win32com Variant 对象"""
  def __init__(self):
    pass

  def points_list_to_variant(self, coord):
    import pylon
    data = list(float(x) for x in pylon.flatten(coord)) | pylon.puts()
    if len(data) % 2 == 1:
      raise AttributeError("point_to_variant: coord length must be even")
    com_seq = win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, data)
    return com_seq

  def to_array(self, *array):
    com_seq = win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, array)
    return com_seq


  def to_point(self, x=0, y=0):
    ''' Point3D '''
    if isinstance(x, (tuple, list)):
      if len(x) == 2:
        _x = float(x[0])
        _y = float(x[1])
      else:
        raise AttributeError('point coordination should be len 2')
    else:
      _x = float(x)
      _y = float(y)
    # data = (x, y)
    data = (_x, _y, 0.0)
    # print(data)
    com_point = win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, data)
    return com_point

  def to_point_2d(self, x=0, y=0):
    ''' Point2D '''
    if isinstance(x, (tuple, list)):
      if len(x) == 2:
        _x = float(x[0])
        _y = float(x[1])
      else:
        raise AttributeError('point coordination should be len 2')
    else:
      _x = float(x)
      _y = float(y)
    data = (_x, _y)
    com_point = win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, data)
    return com_point











































def test_same_inst():
  assert ColorEditor() is ColorEditor()
  assert CADVariant() is CADVariant()


def test_point_2_variant():
  po = CADVariant().to_point_2d(2, 3)
  print(po)
  po = CADVariant().to_point_2d(2, 3.4)
  print(po)
  po = CADVariant().to_point_2d(2, 3)
  print(po)
  po = CADVariant().to_point_2d((2.5, 20))
  print(po)

def test_points_list_2_variant():
  li = CADVariant().points_list_to_variant(2, 3, 4, 5, 6, 7, 8, 9)
  print(li)
  # li = Converter().points_list_to_variant(2,3,4,5,6,7,8,)
  # print(li) # raise must be even
  seq = [[2, 3], [4, 5], [6, 7], [8, 9]]
  li = CADVariant().points_list_to_variant(seq)
  print(li)


def test_color():
  assert ColorEditor().to_index('red') == 1
  assert ColorEditor().to_index('block') == 0
  assert ColorEditor().to_index('orange-') == 31
  assert ColorEditor().to_index('cyan') == 4
  from collections import Counter
  randoms = [ColorEditor().random_index() for i in range(10000)]
  c = Counter(randoms)
  print(sorted(c.keys()))


def test_random():
  from collections import Counter
  randoms = [ColorEditor().rand(10) for i in range(10000)]
  c = Counter(randoms)
  print(sorted(c.keys()))


def test_space():
  sc = SpaceCoordinate()
  # print(sc.point_angle((math.sin(math.pi/6),math.cos(math.pi/6)), (0,0)))
  assert round(sc.point_angle((math.sin(math.pi/6), math.cos(math.pi/6)), (0, 0)), 4) == 60.0


def test_point_angle():
  pa = SpaceCoordinate().point_angle
  # print(result - should)
  print(round(pa([1, 1], [0, 0]), 4),    ': should be (45)')
  print(round(pa([-1, 1], [0, 0]), 4),   ': should be (135)')
  print(round(pa([1, 0], [0, 0]), 4),    ': should be (0)')
  print(round(pa([1, -0.1], [0, 0]), 4), ': should be (354)')
  print(round(pa([-1, -1], [0, 0]), 4),  ': should be (225)')
  print(round(pa([-1, 0], [0, 0]), 4),   ': should be (180)')
  print(round(pa([0.5, 1], [0, 0]), 4),  ': should be (63.4349)')
  print(round(pa([1, 0.5], [0, 0]), 4),  ': should be (26.5650)')
  print(round(pa([0, -3], [0, 0]), 4),   ': should be (270)')
  print(round(pa([0, 3], [0, 0]), 4),    ': should be (90)')








