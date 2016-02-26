

import win32com.client
# import win32api
# import platform
import time
import os
import re
import math
from converter import SpaceCoordinate
from converter import ColorEditor
from converter import CADVariant
from entity import AutoCADEntity, AutoCADEntityError
import pylon
from pylon import puts
from collections import namedtuple
from collections import defaultdict







class AutoCADError(Exception):
  pass





class AutoCAD:
  """AutoCAD

   #####  ##   ## ####### #####   ######  #####  ######
  ##   ## ##   ##    ##  ##   ## ###     ##   ## ##   ##
  ####### ##   ##    ##  ##   ## ##      ####### ##   ##
  ##   ## ##   ##    ##  ##   ## ###     ##   ## ##   ##
  ##   ##  #####     ##   #####   ###### ##   ## ######

  """
  def __init__(self, path=None, visible=True):
    # if platform.uname().release == '8':
    #   app = win32com.client.Dispatch('AutoCAD.Application.20')
    # else:
    #   app = win32com.client.Dispatch('AutoCAD.Application')
    app = win32com.client.Dispatch('AutoCAD.Application')
    self.app = app
    try:
      self.app.ActiveDocument
      self.app.Visible = visible
    except Exception:
      self.create()

  def open(self, path, reuse=True):
    path = re.sub('/', '\\\\', path)
    if reuse:
      for doc in self.documents:
        if doc.FullName == path:
          doc.Activate()
          break
      else:
        self.app.Documents.Open(path)
    else:
      self.app.Documents.Open(path)

  def create(self, dwt_file='acad.dwt'):
    doc = self.app.Documents.Add(dwt_file)
    doc.Activate()
    return doc

  def close(self, current=False):
    if current:
      self.document.Close()

  def temp_open(self, paths):
    org_doc = self.document
    if type(paths) is str:
      paths = [paths]
    for path in paths:
      path, _ = re.subn('/', '\\\\', path)
      tmp_doc = self.app.Documents.Open(path)
      # @doc = tmp_doc
      yield tmp_doc
      tmp_doc.Close(False)
    org_doc.Activate()

  @property
  def documents(self):
    return self.app.Documents

  @property
  def document(self):
    return self.app.ActiveDocument

  @property
  def modelspace(self):
    return self.document.ModelSpace

  @property
  def path(self):
    return self.document.Path

  @property
  def title(self):
    return self.document.Name

  @property
  def is_modelspace(self):
    return self.document.ActiveSpace == 1

  @property
  def is_paperspace(self):
    return not self.is_modelspace







   ###### ####### ##      ####### ###### #######
  ##      ##      ##      ##     ###        ##
   #####  ######  ##      ###### ##         ##
       ## ##      ##      ##     ###        ##
  ######  ####### ####### ####### ######    ##

  @property
  def entities_count(self):
    return self.modelspace.Count

  def last_entity(self, position=0):
    if self.entities_count < position+1:
      return None
    else:
      en = self.modelspace.Item(self.entities_count-1-position)
      return AutoCADEntity.create(en)

  def last_entities(self, count=1):
    msitem = self.modelspace.Item
    total = self.entities_count
    if count > total:
      count = total
    for i in reversed(range(total)):
      if count <= 0:
        break
      else:
        count -= 1
        en = msitem(i)
        yield AutoCADEntity.create(en)

  def first_entities(self, count=1):
    msitem = self.modelspace.Item
    total = self.entities_count
    if count > total:
      count = total
    for i in range(count):
      en = msitem(i)
      yield AutoCADEntity.create(en)

  def entities(self, reverse=False):
    msitem = self.modelspace.Item
    indice = range(self.entities_count)
    if reverse:
      indice = reversed(indice)
    for i in indice:
      en = msitem(i)
      yield AutoCADEntity.create(en)

  def add_selection_set(self, name):
    ssets = self.document.SelectionSets
    if name in [x.Name for x in ssets]:
      ssets.Item(name).Delete()
    sset = ssets.Add(name)
    return sset

  def select_by_layer(self, layname):
    for en in self.entities():
      if hasattr(en, 'layer') and en.layer == layname:
        yield en

  def select_by_type(self, typename):
    for en in self.entities():
      if hasattr(en, 'entity_type') and en.entity_type == typename:
        yield en

  def selecting(self):
    ''' 取得当前鼠标选中的对象,
    如未选中对象则取得上一次选中的对象'''
    sset = self.add_selection_set('temp_for_previous')
    sset.Select(Mode=3)
    # Mode AcSelect 常数 仅用于输入
    # acSelectionSetWindow Mode=1
    # acSelectionSetCrossing Mode=2
    # acSelectionSetPrevious Mode=3
    # acSelectionSetLast Mode=4
    # acSelectionSetAll Mode=5
    for i in range(sset.Count):
      en = sset.Item(i)
      yield AutoCADEntity.create(en)
    sset.delete()
    self.send_lisp('select p  ')

  def match(self, source, entity):
    entity.layer = source.layer
    entity.color = source.color
    if entity.entity_type == 'Text' and source.entity_type == 'Text':
      entity.size = source.size
      entity.style = source.style
    if entity.entity_type == 'Polyline' and source.entity_type == 'Polyline':
      entity.constant_width = source.constant_width
    return entity

  def select(self, first=None, last=None, entity_type=None, layer=None):
    """
    如果不提供任何参数则选中最后一个对象

      cad = AutoCAD()
      objs = cad.select(last=3)
      puts('select(last=3)')
      puts(objs)

      cad.select(first=3)
      puts('select(first=3)')
      puts(objs)

      cad.select(entity_type=['Text', 'Circle'])
      puts('select(entity_type=[Text, Circle])')
      puts(objs)

      cad.select(layer='11')  # return selection
      puts('select(layer=11)')
      puts(objs)
    """
    if first is None and last is None:
      last = 1
    count = last or first

    if isinstance(entity_type, str):
      entity_type = [entity_type]
    if isinstance(layer, str):
      layer = [layer]

    ret = []

    for en in self.entities(reverse=bool(last)):
      # print('iter---', en)
      if entity_type and hasattr(en, 'entity_type') and (en.entity_type not in entity_type):
        continue
      if layer and hasattr(en, 'layer') and (en.layer not in layer):
        continue
      ret.append(en)
      count -= 1
      if count == 0:
        break
    return ret




  ##       #####  ##   ## ####### ######
  ##      ##   ## ##   ## ##      ##   ##
  ##      #######  #####  ######  ######
  ##      ##   ##    ##   ##      ##  ##
  ####### ##   ##    ##   ####### ##   ##
  @property
  def layers(self):
    return self.document.Layers

  @property
  def layer_names(self):
    return [layer.Name for layer in self.layers]

  @property
  def active_layer(self):
    return self.document.ActiveLayer.Name

  def delete_layer(self, layer_name, force=False):
    for lay in self.layers:
      if layer_name == lay.Name:
        try:
          lay.Delete()
        except Exception as e:
          if force:
            ens = list(self.select_by_layer(layer_name))
            for en in ens:
              en.delete()
            lay.Delete()
          else:
            raise e

  def switch_layer(self, layer_name, color=1, auto_create=True):
    for lay in self.layers:
      if layer_name == lay.Name:
        self.document.ActiveLayer = lay
        return lay
    else:
      if not auto_create:
        raise Exception('can not find layer: '+layer_name)
      new_layer = self.layers.Add(layer_name)
      puts(ColorEditor().to_index(color))
      new_layer.Color = ColorEditor().to_index(color)
      self.document.ActiveLayer = new_layer
      return new_layer
    # lay_obj.LayerOn TRUE: 图层为打开状态。 FALSE: 图层为关闭状态。
    # lay_obj.Freeze TRUE: 冻结图层。 FALSE: 解冻图层。
    # lay_obj.Lock TRUE: 图层锁定。 FALSE: 图层未锁定。
    # lay_obj.Plottable TRUE: 图层可打印。 FALSE: 图层不可打印。







   ###### #####  ##   ## ##   ##  #####  ##   ## ######
  ###    ##   ## ### ### ### ### ##   ## ###  ## ##   ##
  ##     ##   ## ## # ## ## # ## ####### ## # ## ##   ##
  ###    ##   ## ##   ## ##   ## ##   ## ##  ### ##   ##
   ###### #####  ##   ## ##   ## ##   ## ##   ## ######
  def send_lisp(self, cmd):
    if cmd[-1] != ' ':
      cmd += ' '
    self.document.SendCommand(cmd)

  def get_point(self, hint='选取点: '):
    self.prompt(hint)
    p = self.document.Utility.GetPoint()[:2]
    self.prompt(hint + ' ' + str(p))
    return p

  def prompt(self, msg='default prompt'):
    if not msg.endswith("\n"):
      msg += "\n"
    self.document.Utility.Prompt(msg)

  def plot_command(self, content_range, device, paper, export_path):
    ''' 拼接 plot lisp 字符串 '''
    if content_range is 'all':
      is_landscape = 'L'
    else:
      left_bottom, right_top = content_range
      is_landscape = 'L' if right_top[0] - left_bottom[0] > right_top[1] - left_bottom[1] else 'P'

    cmd_body = ['plot', 'Y', '', device, paper, 'M', is_landscape, 'N']
    # cmd_body = "plot|Y||{}|{}||{}||".format(device, paper, is_landscape)
    if content_range == 'all':
      cmd_body.append('E')
    else:
      cmd_body.append('W')
      cmd_body.append('{},{}'.format(left_bottom[0], left_bottom[1]))
      cmd_body.append('{},{}'.format(right_top[0], right_top[1]))

    # cmd_body+= "F|C|Y|acad.ctb|Y|A|"
    cmd_body.extend(['F', 'C', 'Y', 'acad.ctb', 'Y'])  # Y=是否打印线宽

    if self.is_modelspace:
      cmd_body.append('A')  # 着色打印设置 按显示(A) 仅模型空间有这一项
      if 'pdf' in device.lower():
        # plot pdf, this arg should be path for pdf
        cmd_body.append(re.sub(r'\\', '/', export_path))
      else:
        cmd_body.append('N')
    elif self.is_paperspace:
      cmd_body.extend(['N', 'N', 'N'])
      if 'pdf' in device.lower():
        cmd_body.append(re.sub(r'\\', '/', export_path))
      else:
        cmd_body.append('N')
      # 是否按打印比例缩放线宽？[是(Y)/否(N)] <否>:
      # 是否先打印图纸空间？[是(Y)/否(N)] <否>:
      # 是否隐藏图纸空间对象？[是(Y)/否(N)] <否>:

    cmd_body.extend(['N', 'Y'])
    # cmd_body+="N|N|Y"

    # 拼合 cmd_body 形成 lisp 命令字串
    joined = ' '.join('"'+x+'"' for x in cmd_body)
    return "(command {})".format(joined)

    '''
    # 命令: (COMMAND "plot" "Y" "" "Lenovo LJ2200" "A4 (210 x 297毫米)" "" PorL "" "W" "129428.1252, 294479.6633" "129652.9351, 294614.5018" "F" "C" "Y" "" "Y" "" "N" "N" "Y")
    # plot
    # 是否需要详细打印配置？[是(Y)/否(N)] <否>: Y
    # 输入布局名或 [?] <模型>:
    # 输入输出设备的名称或 [?] <无>: Lenovo LJ2200
    # 输入图纸尺寸或 [?] <A4 (210 x 297毫米)>: A4 (210 x 297毫米)
    # 输入图纸单位 [英寸(I)/毫米(M)] <毫米>:
    # 输入图形方向 [纵向(P)/横向(L)] <纵向>: L
    # 是否上下颠倒打印？[是(Y)/否(N)] <否>:
    # 输入打印区域 [显示(D)/范围(E)/图形界限(L)/视图(V)/窗口(W)] <范围>: W
    # 输入窗口的左下角 <0.000000,0.000000>: 129428.1252, 294479.6633
    # 输入窗口的右上角 <0.000000,0.000000>: 129652.9351, 294614.5018
    # 输入打印比例 (打印的 毫米=图形单位) 或 [布满(F)] <布满>: F
    # 输入打印偏移 (x,y) 或 [居中打印(C)] <-13.65,11.55>: C
    # 是否按样式打印？[是(Y)/否(N)] <是>: Y
    # 输入打印样式表名称或 [?] (输入 . 表示无) <>:
    # 是否打印线宽？[是(Y)/否(N)] <是>: Y

    # 输入着色打印设置 [按显示(A)/传统线框(W)/传统隐藏(H)/视觉样式(V)/渲染(R)] <按显示>:
    # 是否打印到文件(plt) [是(Y)/否(N)] <N>: N

    # 是否保存对页面设置的修改 [是(Y)/否(N)]? <N> N
    # 是否继续打印？[是(Y)/否(N)] <Y>: Y
    # 有效打印区域:  172.06 宽 X 286.87 高 正在打印视口 2。
    '''

    '''
    在图纸空间中
    输入打印样式表名称或 [?] (输入 . 表示无) <acad.ctb>:
    是否打印线宽？[是(Y)/否(N)] <是>: Y
    --
    是否按打印比例缩放线宽？[是(Y)/否(N)] <否>: -- N
    是否先打印图纸空间？[是(Y)/否(N)] <否>: -- N
    是否隐藏图纸空间对象？[是(Y)/否(N)] <否>: -- N
    是否打印到文件 [是(Y)/否(N)] <N>: n
    是否保存对页面设置的修改 [是(Y)/否(N)]? <N>
    '''



    '''
    reference 模型空间 -> PDF
    命令: -plot 是否需要详细打印配置？[是(Y)/否(N)] <否>: y
    输入布局名或 [?] <模型>:
    输入输出设备的名称或 [?] <Postscript Level 1.pc3>: DWG to PDF.pc3
    输入图纸尺寸或 [?] <ISO A4 (210.00 x 297.00 毫米)>:
    输入图纸单位 [英寸(I)/毫米(M)] <毫米>:
    输入图形方向 [纵向(P)/横向(L)] <纵向>:
    是否上下颠倒打印？[是(Y)/否(N)] <否>:
    输入打印区域 [显示(D)/范围(E)/图形界限(L)/视图(V)/窗口(W)] <窗口>: w
    输入窗口的左下角 <121731.975762,291107.575293>:
    输入窗口的右上角 <132123.231967,299482.830076>:
    输入打印比例 (打印的 毫米=图形单位) 或 [布满(F)] <布满>:
    输入打印偏移 (x,y) 或 [居中打印(C)] <中心>:
    是否按样式打印？[是(Y)/否(N)] <是>:
    输入打印样式表名称或 [?] (输入 . 表示无) <>:
    是否打印线宽？[是(Y)/否(N)] <是>: n
    输入着色打印设置 [按显示(A)/渲染(R)] <按显示>:
    是否保存对页面设置的修改 [是(Y)/否(N)]? <N> n
    是否继续打印？[是(Y)/否(N)] <Y>: y
    有效打印区域:  198.41 宽 X 159.92 高
    正在打印视口 2。


    reference 布局空间 -> PDF
    命令: -plot 是否需要详细打印配置？[是(Y)/否(N)] <否>: y
    输入布局名或 [?] <布局1>:
    输入输出设备的名称或 [?] <无>: DWG to PDF.pc3
    输入图纸尺寸或 [?] <ISO full bleed A2 (594.00 x 420.00 毫米)>:
    输入图纸单位 [英寸(I)/毫米(M)] <毫米>:
    输入图形方向 [纵向(P)/横向(L)] <纵向>:
    是否上下颠倒打印？[是(Y)/否(N)] <否>:
    输入打印区域 [显示(D)/范围(E)/布局(L)/视图(V)/窗口(W)] <布局>: w
    输入窗口的左下角 <0.000000,0.000000>:
    输入窗口的右上角 <0.000000,0.000000>:
    输入打印比例 (打印的 毫米=图形单位) 或 [布满(F)] <1:1>: f
    输入打印偏移 (x,y) 或 [居中打印(C)] <0.00,0.00>: c
    是否按样式打印？[是(Y)/否(N)] <是>:
    输入打印样式表名称或 [?] (输入 . 表示无) <>: .
    是否打印线宽？[是(Y)/否(N)] <是>: Y
    是否按打印比例缩放线宽？[是(Y)/否(N)] <否>:
    是否先打印图纸空间？[是(Y)/否(N)] <否>:
    是否隐藏图纸空间对象？[是(Y)/否(N)] <否>:
    是否保存对页面设置的修改 [是(Y)/否(N)]? <N>
    是否继续打印？[是(Y)/否(N)] <Y>: y
    有效打印区域:  324.75 宽 X 418.41 高
    有效打印区域:  246.08 宽 X 418.38 高
    正在打印视口 2。
    正在打印视口 1。

    '''

  def plot_content_range(self, mode='selecting'):
    '''获取打印CAD或输出CAD图片时的尺寸范围
    mode = selecting / points'''
    if 'selecting' == mode:
      ens = [en for en in self.selecting()]
      data = []
      for en in ens:
        box = en.bounding_box_point
        data.append((box[0][0], box[0][1], box[1][0], box[1][1]))
      data = list(pylon.transpose(data))
      # data -> min_coord_x, min_coord_y, max_coord_x, max_coord_y
      return (min(data[0]), min(data[1])), (max(data[2]), max(data[3]))
    elif 'points' == mode:
      p1 = self.get_point(hint='选取打印范围的角点1: ')
      p2 = self.get_point(hint='选取打印范围的角点2: ')
      return p1, p2
    else:
      raise

  def plot(self, device, paper, export_path='', content='selecting'):
    # mode = all / selecting / points
    # device = 'DWG To PDF.pc3'
    # paper = 'ISO A4 (210.00 x 297.00 毫米)'
    if content in ('selecting', 'points'):
      content_coordinate = self.plot_content_range(content)
    else:
      content_coordinate = 'all'
    # export_path = os.path.join(self.path, os.path.splitext(self.title)[0] + '.pdF')
    # puts(export_path)
    cmd = self.plot_command(content_coordinate, device, paper, export_path)
    self.send_lisp(cmd)















   ###### ######  #######  ##### ####### #######
  ###     ##   ## ##      ##   ##   ##   ##
  ##      ######  ######  #######   ##   ######
  ###     ##  ##  ##      ##   ##   ##   ##
   ###### ##   ## ####### ##   ##   ##   #######

  ####### ##   ## ####### ###### ####### ##   ##
  ##      ###  ##    ##     ##      ##   ##   ##
  ######  ## # ##    ##     ##      ##    #####
  ##      ##  ###    ##     ##      ##      ##
  ####### ##   ##    ##   ######    ##      ##

  def add_rectangle(self, bottomleft, topright=None, width=None, height=None):
    if not (width or height):
      width = topright[0] - bottomleft[0]
      height = topright[1] - bottomleft[1]
    originx = bottomleft[0]
    originy = bottomleft[1]
    rec = self.add_polyline((originx, originy),
                            (originx, originy+height),
                            (originx+width, originy+height),
                            (originx+width, originy),
                            closed=True)
    rec = AutoCADEntity.create(rec.entity)
    return rec


  def add_polyline(self, *coord, closed=False):
    com_points = CADVariant().points_list_to_variant(*coord)
    pline = self.modelspace.AddLightweightPolyline(com_points)
    pline = AutoCADEntity.create(pline)
    pline.closed = closed
    return pline

  def add_point(self, x=0, y=0):
    com_point = CADVariant().to_point(x, y)
    po = self.modelspace.AddPoint(com_point)
    po = AutoCADEntity.create(po)
    return po

  def add_line(self, start, end):
    com_start = CADVariant().to_point(start[0], start[1])
    com_end = CADVariant().to_point(end[0], end[1])
    line = self.modelspace.AddLine(com_start, com_end)
    return AutoCADEntity.create(line)

  def add_circle(self, origin=(0, 0), radius=1):
    com_point = CADVariant().to_point(origin)
    cir = self.modelspace.AddCircle(com_point, radius)
    cir = AutoCADEntity.create(cir)
    return cir


  # def add_arc(self, startp, endp, bulge):
  #   angle = math.atan(bulge)*4*360 / (2*math.pi)
  #   cmd("arc #{startp[0]},#{startp[1]} e #{endp[0]},#{endp[1]} a #{angle}")
  #   last_entity

  # "左对齐" Alignment 0
  # "底部居中" Alignment 1
  # "中间"  Alignment 4

  ALIGNMENT_SETTING = {'left': 0, 'bottom': 1, 'center': 4}

  def add_text(self, text_string, origin=(0, 0), height=1, alignment='center'):
    com_point = CADVariant().to_point(origin)
    text = self.modelspace.AddText(str(text_string), com_point, height)
    text.Alignment = self.ALIGNMENT_SETTING[alignment]
    if alignment != 'left':
      text.TextAlignmentPoint = com_point
    # 已证实 必须先 txtobj.Alignment 再 txtobj.TextAlignmentPoint
    # acAlignmentMiddleCenter 跟 acAlignmentMiddle 的区别
    # 后者在标注“第一大街”时，“一”的位置会出错
    text = AutoCADEntity.create(text)
    return text

  def to_hatch(self, polyline):
    if not polyline.closed:
      raise "Polyline must be closed"
    hatch = self.modelspace.AddHatch(0, 'ANSI31', True)
    # TODO(Probe): 如何解决 VT 数组的问题
    #AppendOuterLoop(val) 需要com的数组
    com_seq = CADVariant().to_array(polyline.entity)
    hatch.AppendOuterLoop(com_seq)
    return AutoCADEntity.create(hatch)

  def add_region(self, en):
    self.send_lisp("region {}  ".format(en.handle))
    return self.last_entity()

  def get_centroid(self, en):
    r = self.add_region(en.clone())
    centroid = r.centroid
    r.delete()
    return centroid









  ##   ##  #####  ##   ## ###### ######
  ### ### ##   ## ###  ##   ##   ##   ##
  ## # ## ####### ## # ##   ##   ######
  ##   ## ##   ## ##  ###   ##   ##
  ##   ## ##   ## ##   ## ###### ##

  def search_by_area(self, entities_iter, target, tolerance,
                     entype=('Polyline', 'Hatch', 'Text'),
                     only_closed=False,
                     marker=['circle']):
    total_count = 0
    matched = []
    errors = []
    for en in entities_iter:
      if en.entity_type not in entype:   # 滤掉不属于指定实体类型的
        continue
      if only_closed and en.entity_type == 'Polyline' and not en.closed:
        continue                         # 滤掉多段线不闭合的

      total_count += 1
      if en.entity_type == 'Text':
        matchobj = re.search(r'\d+(\.\d{1,3})?', en.text)
        if matchobj:
          area = float(matchobj.group())
          if abs(area - target) <= tolerance:
            matched.append(en)
      else:                              # 剩下来的是 polyline 和 hatch
        try:
          if abs(en.area - target) <= tolerance:
            matched.append(en)
        except AutoCADEntityError:
          errors.append('未取得面积 {}'.format(en))


    ret = ['总计检测了{}个有效对象'.format(total_count)]
    ret.append('{}个对象符合指定的面积'.format(len(matched)))


    circle = color = layer = None
    if 'circle' in marker:
      circle = True
    if 'color' in marker:
      color = 'red'
    if 'layer' in marker:
      layer = '.check_area'
    for en in matched:
      self._mark_entity(en, layer=layer, color=color, circle=circle)
      ret.append(' -- 符合要求的对象{}'.format(en))

    return ret








  ##   ##  #####  ##   ## ###### ######
  ### ### ##   ## ###  ##   ##   ##   ##
  ## # ## ####### ## # ##   ##   ######
  ##   ## ##   ## ##  ###   ##   ##
  ##   ## ##   ## ##   ## ###### ##

  ######   #####  ##   ##   ## ##      ###### ##   ## #######
  ##   ## ##   ## ##   ##   ## ##        ##   ###  ## ##
  ######  ##   ## ##    #####  ##        ##   ## # ## ######
  ##      ##   ## ##      ##   ##        ##   ##  ### ##
  ##       #####  ####### ##   ####### ###### ##   ## #######

  def redraw_vertex_sequence(self, pl, first=None, hint=False, auto_reverse=True):
    ''' 重绘多段线的顶点顺序
    首先调整为顺时针的 polyline
    然后取最接近第二象限的45度方向的节点作为顶点
    如果已经指定first的偏移，则在当前顺序基础上滑动这个偏移
    最后计算是否原图新图面积符合，如果成功，则删掉原图

    first: 手动指定新的首顶点应该在调整前首顶点的什么位置
    hint: 在编辑后的图形中显示节点顺序的数字，几秒后删掉

    '''
    # first => 1 表示在目前首顶点的方向上滑动1个顶点作为新的首顶点
    # puts(pl.vertex_spatial(start=0))
    if auto_reverse and (not pl.is_clockwise):   # 首先调整为顺时针polyline
      puts("detect counter-clockwise, reverting this ...")
      # self.send_lisp("pedit {} r  ".format(pl.handle))
      pl = pl.reverse()
      # print(self.get_centroid(pl))
    # return pl
    Vertex = namedtuple('Vertex', ['index', 'x', 'y', 'quadrant', 'point_angle'])
    center = self.get_centroid(pl)
    verts_count = pl.count

    space_coordinate = SpaceCoordinate()


    if first is None:   # 不指定将哪个顶点作为新的首顶点时，需自行计算出合适的首顶点
      # 取得备选的首顶点，计算重心到顶点的相对方向，取左上角区域内的
      vertexs = []
      for i in range(pl.count):
        vet = pl.vertex(i)
        quadrant = space_coordinate.quadrant(vet, center)
        vet_sin = space_coordinate.point_angle(vet, center)
        v = Vertex(i, vet[0], vet[1], quadrant, vet_sin)
        vertexs.append(v)
      quadrant_2_total = [v for v in vertexs if v.quadrant == 2]  # 取得所有第二象限的点
      # print(quadrant_2_total)
      # 取得最适合的左上角端点
      if len(quadrant_2_total) == 1:    # 第二象限只有一个节点
        best = quadrant_2_total[0]
      elif len(quadrant_2_total) == 0:  # 第二象限没有节点，取第一象限节点中，sin角度最大的
        quadrant_1_total = [v for v in vertexs if v.quadrant == 1]
        best = max(quadrant_1_total, key=lambda x: x.point_angle)
      else:                             # 第二象限具有多个合适的顶点，取最接近左上45角的
        best = min(quadrant_2_total, key=lambda x: abs(x.point_angle-45))

      slide_amount = best.index

    else:
      # 如果之前指定了首顶点，则优先使用之，负数n意味反向滑动n个顶点
      slide_amount = first % verts_count

    # puts(pl.vertex_spatial(start=0))
    vertex_spatial = pl.vertex_spatial(start=0)
    # 重排序顶点顺序
    vertexs_rotated = vertex_spatial[slide_amount:] + vertex_spatial[:slide_amount]
    # 画新poly，但现在全是直线连接的
    new_pl = self.add_polyline(*[(po.x, po.y) for po in vertexs_rotated], closed=pl.closed)
    # 重设poly内的圆弧
    [new_pl.set_bulge(i, v.bulge) for i, v in enumerate(vertexs_rotated)]
    if new_pl.area - pl.area < 0.00001:
      new_pl.color = pl.color
      new_pl.layer = pl.layer
      pl.delete()

    else:
      raise AutoCADEntityError("redraw polyline for better vertex sequence failed! area: old(#{pl.area}) != new(#{new_pl.area})")

    if hint:
      # 绘制一些点号表示目前的顺序，然后删掉
      bak_layer = self.active_layer
      timer = pylon.file_timer(prefix='.temp_point_index_')
      self.switch_layer(timer)

      height = new_pl.bounding_box_diagonal * 0.05
      for v in new_pl.vertex_spatial():
        t = self.add_text(v.index, origin=(v.x, v.y), height=height)
        t.color = 'green'
      self.switch_layer(bak_layer)
      time.sleep(3)
      self.delete_layer(timer, force=True)
    return new_pl

  def remove_same_points_polyline(self, polyline, threshold=0.001):
    ''' 移除poly中重复的节点
    不一定保留poly主要线条结构,
    如果一个顶点之前连接了较长的边, 之后连接到0.0001的边, 该顶点会被移除,
    重新生成图形的对应边会有少许位置变化
    '''
    # 取得vertex_spatial, 每个节点携带其后边的长度, 移除所有length小于阈值的节点
    vertex_spatial_trimed = [vt for vt in polyline.vertex_spatial() if vt.length >= threshold]
    coords = [(vt.x, vt.y) for vt in vertex_spatial_trimed]
    polyline_new = self.add_polyline(*coords, closed=polyline.closed)
    for i, vt in enumerate(vertex_spatial_trimed):
      polyline_new.set_bulge(i, vt.bulge)

    polyline_new.layer = polyline.layer
    polyline_new.color = 'orange'

    report = '原节点数={} 新节点数={} 原面积={:.4f} 新面积={:.4f} 面积相差={:.4f} '
    report = report.format(polyline.count, polyline_new.count,
                           polyline.area, polyline_new.area, polyline_new.area - polyline.area)
    return polyline_new, report

  def de_interpolate_polyline(self, polyline, threshold=0.5):
    ''' 优化抽稀多段线, 将阈值内顶点合并为同一点
    会保留poly主要线条结构, 如果一个顶点连接到至少一条较长的边, 则该顶点一定会被保留
    '''
    coords = polyline.coords
    # TODO(Probe) 检测 bulges 非常慢
    # if any(b != 0 for b in polyline.bulges()):
    #   raise AutoCADEntityError('cannot refine polyline with arc')
    count = polyline.count
    anchor = coords[0]
    result = [coords[0]]
    distance2 = SpaceCoordinate().distance2
    threshold2 = threshold**2
    for i, pv in enumerate(coords):
      if i == 0:
        continue
      dist = distance2(pv, anchor)            # 该点距锚点的距离
      pv_next = coords[(i+1) % count]
      dist_next = distance2(pv_next, anchor)  # 该点下一点距锚点的距离
      if threshold2 < dist or threshold2 < dist_next:
        # 在该点超过阈值或该点下一点超过阈值时 记录为有效的点
        # 同时设此为新比对点
        # 不满足条件的是废点 忽略之
        anchor = pv
        result.append(pv)
    newpl = self.add_polyline(*pylon.flatten(result), closed=polyline.closed)
    msg = "原节点数 {}, 新节点数 {}, 阈值 {}, 原面积 {:.3f}, 新面积 {:.3f}, 面积相差 {:.3f} ({:.4%})"
    msg = msg.format(polyline.count, newpl.count, threshold, polyline.area, newpl.area, newpl.area-polyline.area, (newpl.area-polyline.area)/polyline.area)
    return newpl, msg

  def interpolate_polyline(self, polyline, distance=0.2, delete_original=True, break_at_vertexes=False):
    '''多段线加密
    转换shp时可以得到相符的形状和面积
    先将多段线分解为直线圆弧
    圆弧部分细分为不大于distance的片段
    最后按照顺序连接起来，并检查面积是否吻合
    break_at_vertexes = True 则分割为多段线的碎片
    '''
    polyline_bk = polyline.clone()

    clips = list(polyline.explode())
    points_total = []  # 多原polyline整体加密, 存放所有点
    points_clips = []  # 炸开并加密圆弧, 分别存放每一段的点
    print(polyline_bk)
    current_tail = polyline_bk.vertex(0)
    # VBA版用 pedit->join连接，所以没有遇到圆弧起点顺序的问题
    # Python版用计算points_total表的方式生成polyline，圆弧部分可能会逆序，
    # 需要记录上一个Line/Arc尾点的位置
    for clip in clips:
      if clip.entity_type == 'Line':
        points_total.append(clip.start_point)
        points_clips.append([clip.start_point, clip.end_point])
        current_tail = clip.end_point
      else:  # 圆弧，永远是按逆时针定义角度，但连接时需要考虑上一个碎片的尾点
        vets = self._get_interpolate_arc_vertexes(clip, distance=distance)
        if not SpaceCoordinate().same_point(vets[0], current_tail):
          vets = list(reversed(vets))
        points_total.extend(vets[:-1])
        points_clips.append(vets)
        current_tail = vets[-1]
      clip.delete()

    if not polyline_bk.closed:
      raise Exception('polyline should be closed')

    if break_at_vertexes:
      break_segments = []
      for clip in points_clips:  # 描绘原始polyline的每一段
        if len(clip) == 2:       # 绘制为直线
          seg = self.add_line(*clip)
        else:                    # 绘制为多段线模拟的圆弧
          seg = self.add_polyline(clip, closed=False)
        seg.random_color()
        break_segments.append(seg)
      for clip in points_clips:  # 添加原始polyline的节点
        self.add_point(clip[0])
      self.send_lisp('pd2')
      break_segments_report = ' '.join(str(s) for s in break_segments)
      report = "加密完成, 分段数{}, 分段元素{}".format(len(break_segments), break_segments_report)
      print(report)
      polyline_bk.delete()
      return break_segments, report

    else:
      polyline_new = self.add_polyline(points_total, closed=True)

      report = "加密后节点数：{new_vertexs}\n加密距离：{distance}\n原面积：{area_old:.4f} -> 新面积：{area_new:.4f}\n面积相差：{area_delta:.4f} ({area_percent:.4%})".format(
                    new_vertexs=len(points_total),
                    distance=distance,
                    area_old=polyline_bk.area,
                    area_new=polyline_new.area,
                    area_delta=polyline_new.area-polyline_bk.area,
                    area_percent=(polyline_new.area-polyline_bk.area)/polyline_bk.area
        )
      if delete_original:
        polyline_bk.delete()
        pass

      print(report)
      return polyline_new, report



  def _get_interpolate_arc_vertexes(self, arc, distance=0.2, segment=None):
    '''圆弧插值加密，Arc对象 -> 加密后的多段线坐标
    distance = 分段后每段距离不超过该阈值
    segment = 直接指定分几段
    '''
    cenx, ceny = arc.center
    radius = arc.radius
    if not segment:
      segment = int(arc.arc_length / distance) + 1
    angle_segment = (arc.end_angle - arc.start_angle) / segment
    # 圆弧永远是按逆时针定义角度
    if angle_segment < 0:    # 处理end_angle已经转过一圈，回到start之前的情况
      angle_segment = (2 * math.pi + arc.end_angle - arc.start_angle) / segment

    points = []
    # 首端点，必须照抄圆弧的坐标
    points.append(arc.start_point)
    for i in range(segment-1):

      # For i = 3 To segment * 2 Step 2
      this_angle = arc.start_angle + angle_segment * (i+1)
      x = cenx + radius * math.cos(this_angle)
      y = ceny + radius * math.sin(this_angle)
      points.append((x, y))
    # 尾端点，必须照抄圆弧的坐标
    points.append(arc.end_point)
    return points

  def _mark_entity(self, entity, layer=None, color=None, circle=None):
    '''为对象添加标记, 选项包括: 放置到新图层, 变换颜色, 增加圆圈'''
    if layer:
      entity.layer = layer
    if color:
      entity.color = color
    if circle:
      radius = entity.bounding_box_diagonal
      cen = entity.mid_point
      circle = self.add_circle(cen, radius / 2 * 1.1)
      circle.layer = '.dim_circle'
    return entity


  def rebuild_arc_polyline(self, polyline, threshold=3.0, segment_points=None):
    '''将加密多段线返算为圆弧的多段线
    加密多段线应为多个直线段相连, 不含圆弧(未检测)

    [x] 多个圆弧相连时，需要识别中间的分界
    [x] 当多段线起点处在加密圆弧中时，应向前寻找合适的分界点作为起点, 否则该圆弧被分割为两部分
    [x] 最后需要把圆弧和直线拼起来，但经常拼合不全

    threshold - 阈值，连续的小于此长度的多段线碎片将被合并为圆弧
    segment_points - 点坐标(x y)pair的list, 用来额外指定一些打断点,
                     应对连续不同半径的密集圆弧点被识别为一个圆弧的情况
                     segment_points保留4位小数

    只处理封闭poly, 应该判断起点是否为关键节点, 否则挪到最近的关键节点上

    在下一点对该点超过阈值时，或尾点时(尾点被设成了必然超阈值)，标记结束，
    连接此点对下一点的直线，并计算之前缓存点的圆弧半径，之后重置 point cache
    连续5个密集点(数组数量为12，有一对废点)，则可计算拟合为圆弧，太少的不管
    '''

    if not polyline.closed:
      raise AutoCADEntityError('cannot rebuild_arc for polyline unclosed')

    get_dist = SpaceCoordinate().distance
    # vertex_spatial 太慢了, 改用 coords
    coords = polyline.coords
    straight_lengths = [get_dist(p1, p2) for p1, p2 in zip(coords, pylon.rotate(coords, 1))]

    vertex_count = polyline.count
    # puts('vertex_count=')
    if all(length < threshold for length in straight_lengths):
      raise AutoCADEntityError('cannot rebuild arc for polyline all length < threshold')


    start = 0   # 封闭polyline, 应该判断起点是否为关键节点, 否则向下一个节点探查, 挪到最近的关键节点上
    if straight_lengths[0] < threshold and straight_lengths[-1] < threshold:
      while True:
        if straight_lengths[start] > threshold:
          break
        else:
          start += 1


    coords = pylon.rotate(coords, start)  # 旋转array使起点为合适的分界点
    straight_lengths = pylon.rotate(straight_lengths, start)

    # 分节点出现在所有大于阈值的边长两端
    i_segments = [i for i, length in enumerate(straight_lengths) if length >= threshold]  # 收集大于阈值的边长的起点号
    i_segments += [(i+1) % vertex_count for i in i_segments]  # 收集大于阈值的边长的终点的索引号

    if segment_points:
      segment_points = [(round(p[0], 4), round(p[1], 4)) for p in segment_points]
      i_segments += [i for i, co in enumerate(coords) if (round(co[0], 4), round(co[1], 4)) in segment_points]

    i_segments = sorted(pylon.dedupe(i_segments))  # 分节点出现在所有大于阈值的边长两端

    # puts('i_segments=')

    bulges = []
    segment_vertexes = []

    for side_vertexes in self._polyline_to_segments(coords, i_segments):
      segment_vertexes.append(side_vertexes[0])
      if len(side_vertexes) > 5:                      # 有连续的5个以上密集点, 需转圆弧
        center, bulge = self._vertexes_to_arc(side_vertexes)
        bulges.append(bulge)
      elif len(side_vertexes) > 2:                      # 连续密集点, 但数量不够, 保留原折线不转圆弧
        segment_vertexes.extend(side_vertexes[1:-1])  # 之前已经添加了[0]点, 现在只添加[1:-1]
        bulges.extend([0] * (len(side_vertexes)-1))
      else:
        bulges.append(0)

    # puts('segment_vertexes=')
    # puts('bulges=')
    polyline_rebuild = self.add_polyline(*segment_vertexes, closed=True)
    for i, bulge in enumerate(bulges):
      polyline_rebuild.set_bulge(i, bulge)
    # puts(polyline.area)
    # puts(polyline_rebuild.area)
    return polyline_rebuild


  def _polyline_to_segments(self, coords, i_segments):
    """以i_segments作为关键节点打断polyline, 每段可能是直线(2个点) 可能是将返算圆弧的折线"""
    # puts(i_segments)
    side_vertexes = []
    for i, vt in enumerate(coords):
      side_vertexes.append(vt)
      if i in i_segments:
        if len(side_vertexes) > 1:
          yield side_vertexes
        side_vertexes = [vt]
    else:  # 循环结束
      side_vertexes.append(coords[0])
      yield side_vertexes


  def _vertexes_to_arc(self, vertexes, min_count=5, max_sample=100000):
    """多个节点返算为圆弧
    min_count - 提供节点数至少为 min_count 才返算, 否则保留原来的折线"""
    vertex_start, *vertexes_on_arc, vertex_end = vertexes

    if len(vertexes_on_arc) > max_sample:
      vertexes_on_arc = vertexes_on_arc.sample(max_sample)
    get_center = SpaceCoordinate().center
    # get_dist = SpaceCoordinate().distance
    same_point = SpaceCoordinate().same_point
    get_angle = SpaceCoordinate().point_angle
    centers = []
    for vertex in vertexes_on_arc:
      if not same_point(vertex_start, vertex) and not same_point(vertex_end, vertex):
        try:
          centers.append(get_center(vertex_start, vertex, vertex_end))
        except ZeroDivisionError:
          continue


    # centers = [get_center(vertex_start, vertex, vertex_end) for vertex in vertexes_on_arc
              # if not same_point(vertex_start, vertex) and not same_point(vertex_end, vertex)]
    # puts('vertexes=')
    # puts('centers=')
    center_x = sum(center[0] for center in centers) / len(centers)
    center_y = sum(center[1] for center in centers) / len(centers)
    center = center_x, center_y
    angle_start = get_angle(point=vertex_start, origin=center)
    angle_end = get_angle(point=vertex_end, origin=center)


    angle = (angle_end - angle_start + 360) % 360
    if angle > 180:
      angle = 360 - angle
    bulge = math.tan(angle / 360 * 2 * math.pi / 4)
    # 凸度是多段线顶点列表中选定顶点和下一顶点之间的圆弧所包含角度的 1/4 的正切值
    # 负的凸度值表示圆弧从选定顶点到下一顶点为顺时针方向
    # 凸度为0 表示直线段 凸度为1表示半圆
    # 判断圆弧方向
    if (angle_end - angle_start + 360) % 360 > 180:  # 顺时针
      bulge *= -1

    # debug 在圆弧处绘制circle
    # radius = get_dist(vertex_start, center)
    # c = self.add_circle(origin=center, radius=radius)
    # c.color = 'yellow'

    return center, bulge


  def dim_polyline_vertex_and_sides(self, polylines, height=1,
                                    vertex_index_start=1,
                                    vertex_label_prefix='',
                                    draw_vertex_label=True,
                                    draw_segment_length=True,
                                    vertex_label_layer='dim_jzd_index',
                                    side_length_label_layer='dim_length',
                                    ):
    '''
    标注 一组Polyline 各分段的直线长度，弧长
    polylines - 需要标注的 polyline 如为多个, 编号连续后推
    height=1 - 界址点和界址长度的字号
    vertex_index_start=1 - 第一个点的编号, 之后的类推
    vertex_label_prefix='' - 界址点前缀
    draw_vertex_label=True - 标注界址点编号
    draw_segment_length=True - 标注界址长度
    vertex_label_layer='dim_jzd_index' - 界址点编号图层
    side_length_label_layer='dim_length' - 界址长度图层

    [ ] 自适应文字大小，应该取得外框的较长边，以此决定
    [ ] 垂直边界 如矩形 计算 tan angle 角度出错
    [ ] 遇到圆弧时 界址边长位置出错

    '''
    radius_dist = height * 1.2
    get_dist = SpaceCoordinate().distance
    for polyline in polylines:
      polyline_offset = polyline.offset(0.001)
      vertex_spatial_offset = polyline_offset.vertex_spatial()
      middles_offset = polyline_offset.segment_middle_points()

      polyline_offset.delete()

      for postion_info in zip(polyline.vertex_spatial(),
                              vertex_spatial_offset,
                              middles_offset,
                              polyline.tan_angles(),
                              polyline.segment_middle_points(),
                              ):
        vt, vtoffset, segmidoffset, angle, segmid = postion_info

        if draw_vertex_label:
          'jzd label'
          dist = get_dist((vt.x, vt.y), (vtoffset.x, vtoffset.y))
          point_x = radius_dist / dist * (vtoffset.x - vt.x) + vt.x
          point_y = radius_dist / dist * (vtoffset.y - vt.y) + vt.y

          text = self.add_text(vertex_label_prefix + str(vertex_index_start),
                               origin=(point_x, point_y),
                               height=height)
          text.layer = vertex_label_layer

        if draw_segment_length:

          'segment length label'

          dist = get_dist(segmid, segmidoffset)
          midpt_x = radius_dist / dist * (segmidoffset[0] - segmid[0]) + segmid[0]
          midpt_y = radius_dist / dist * (segmidoffset[1] - segmid[1]) + segmid[1]
          text = self.add_text('{:.2f}'.format(vt.length),
                               origin=(midpt_x, midpt_y),
                               height=height)
          text.layer = side_length_label_layer
          text.angle = math.atan(angle)

        vertex_index_start += 1











  ######  ####### ######   #####  ###### #######
  ##   ## ##      ##   ## ##   ## ##   ##   ##
  ######  ######  ######  ##   ## ######    ##
  ##  ##  ##      ##      ##   ## ##  ##    ##
  ##   ## ####### ##       #####  ##   ##   ##

  def wipeout(self, en, segment=32):
    ''' 以指定的 circle 生成消隐, 并擦除内部
    只能用 Polygon 做擦除，不能用圆
    segment - Polygon 分段数
    '''
    # Dim size As Double: size = lineheight * 0.1
    # 返算合适的节点大小
    lisp = "_polygon {} {},{} i {}".format(segment, en.center[0], en.center[1], en.radius)
    self.send_lisp(lisp)
    polygon = self.last_entity()
    lisp = "_wipeout p {} n ".format(polygon.handle)
    polygon.layer = en.layer
    polygon.color = en.color
    self.send_lisp(lisp)
    wipeout = self.last_entity()
    wipeout.layer = en.layer
    wipeout.color = en.color
    lisp = "_draworder {}  f".format(wipeout.handle)
    en.delete()

  def generate_jzd_circle(self, polyline, size=5, layer='dim_jzd_point', segment=32):
    ''' 生成界址桩点圆圈
    提供多段线, 在其每个节点标注界址点圆圈，生成消隐, 并擦除内部
    '''
    for po in polyline.vertex_spatial():
      circle = self.add_circle((po.x, po.y), size)
      circle.layer = layer
      self.wipeout(circle, segment=segment)

  def report_area(self, *enlist, island=False):
    '''统计面积
    TODO(Probe): 应该改成统计更多的信息
    island=True 时将输入polyline视为岛状数据，总面积应为总边界和内部岛屿面积的差值
    '''
    ret = []
    for pl in self.selecting():
      if pl.closed:
        # print(pl)
        ret.append(pl)
    # report = [str(pl) for pl in ret]
    area = [pl.area for pl in ret]
    if len(list(pylon.dedupe(area))) != len(area):
      print('!!WARNNING!! seems has duplicate polyline')

    if island:   # 岛状的一组polyline，由一个面积很大的总边界，和一群小面积的边界线构成
      whole = max(area)
      real = whole*2 - sum(area)
      islands = ['{:.2f}'.format(a) for a in area if a != whole]
      log = ('面积统计(带环岛): \n实际 {:.2f}, \n最大边界 {:.2f}, \n其余内部地块 {}'.format(real, whole, islands))
    else:
      area_for_print = ['{:.2f}'.format(a) for a in area]
      log = ('面积统计: \n总计: {:.2f}, \n单独: {}'.format(sum(area), area_for_print))
    # puts(log)
    return log
    # puts "all areas : #{arr.join(' ')}"
    # others = arr - [arr.max]
    # area = arr.max - others.inject(&:+)
    # puts "area clear islands : #{area}"


  def arrange_text(self, texts, auto_size=False):
    ''' 重新排列选中的文字
    选中多个文字并指定两点, 将文字均匀排布至两点之间
    文字将被调整为中间对齐
    文字的顺序以原先位置决定,
    原有文字形成的矩形如果宽度大于高度,
    则以文字的横轴坐标决定重排的顺序, 否则以纵轴决定顺序

    auto_size - 自动调整文字大小, 将设为指定起点终点距离的 4%'''
    # origin
    if len(texts) <= 1:
      print('需至少选中两个文字对象')
      return False
    range_x = max(t.origin[0] for t in texts) - min(t.origin[0] for t in texts)
    range_y = max(t.origin[1] for t in texts) - min(t.origin[1] for t in texts)

    if range_x >= range_y:
      texts_sorted = sorted(texts, key=lambda text: text.origin[0])
    else:
      texts_sorted = sorted(texts, key=lambda text: text.origin[1] * -1)  # y轴顺序需要倒置

    count = len(texts_sorted)
    start_point = self.get_point(hint='指定重新排布的起点:')
    end_point = self.get_point(hint='指定重新排布的终点:')
    if auto_size:
      text_size = SpaceCoordinate().distance(start_point, end_point) * 0.04

    for i, text in enumerate(texts_sorted):
      x = start_point[0] + (end_point[0] - start_point[0]) * i/(count-1)
      y = start_point[1] + (end_point[1] - start_point[1]) * i/(count-1)
      com_point = CADVariant().to_point([x, y])
      text.origin = com_point
      text.entity.Alignment = 4  # 4 indicate center
      text.entity.TextAlignmentPoint = com_point
      if auto_size:
        text.size = text_size


  def dim_area(self, *enlist, unit='m²', precision=2, font_size='*0.05'):
    ''' 标注实体的面积
    先计算传入的一组对象的大小，决定用多大的字号
    然后换算单位和小数精度
    然后临时切换到标注面积的图层，把面积写在每个图形的正中 '''
    report = []
    enlist = [en for en in enlist if en.entity_type in ('Polyline', 'Hatch')]
    # print([en.bounding_box_diagonal for en in enlist])
    max_bounding_size = max(en.bounding_box_diagonal for en in enlist)
    # TODO(Probe): 这种单位转换和 *.0.01 的解释应该放在Converter
    SCALE_SETTING = {
      '': 1, 'm²': 1, 'm': 1, '平方米': 1,
      '公顷': 1/10000, 'hectare': 1/10000, 'hm²': 1/10000,
      '平方公里': 1/1000000, '平方千米': 1/1000000, 'km²': 1/1000000,
      '亩': 1/666.67, 'mu': 1/666.67,
    }
    scale = SCALE_SETTING[unit]
    if isinstance(font_size, str):
      height = round(max_bounding_size * float(font_size[1:]), 1)
    else:
      height = font_size
    layer_backup = self.active_layer
    self.switch_layer('.dim_area', color='red')
    for en in enlist:

      if en.entity_type == 'Polyline' and not en.closed:
        report.append(('Warning', '{} is not closed'.format(en)))
      try:
        area = en.area
        self._dim_area(en, area, scale=scale, precision=precision,
                       suffix=unit, height=height)
      except AutoCADEntityError as e:
        report.append(('Error', e))

    self.switch_layer(layer_backup)
    return report


  def _dim_area(self, en, area, scale, precision, suffix, height):
    if precision >= 0:
      text = ('{:.'+str(precision)+'f}{}').format(area * scale, suffix)
    else:
      text = '{}{}'.format(int(round(area * scale, precision)), suffix)
    self.add_text(text, origin=en.mid_point, height=height, alignment='center')



  def report_entities(self, entities, hole=False, error_color=None, error_layer=None):
    '''汇总选中元素的属性信息

    report like >
      选中对象数目: 23
      多段线: 16 (未闭合: 3)
      - 总面积 78124.3
      图案填充: 3 (无面积: 1)
      - 总面积 67812.4
      文字: 10
      直线: 3
      圆弧: 4
      圆: 7

    '''
    report = []
    endict = defaultdict(list)
    for en in entities:
      endict[en.entity_type].append(en)


    if endict['Polyline']:
      poly_all = endict['Polyline']
      report.append('多段线: {}'.format(len(poly_all)))

      poly_closed = [en for en in poly_all if en.closed]
      poly_open = [en for en in poly_all if not en.closed]
      if poly_closed:
        if hole and len(poly_closed) > 1:
          # 将多段线视为外部包裹线和内部孔洞,
          # 统计面积应以最大面积减去其他较小的
          max_area = max(en.area for en in poly_closed)
          area = max_area*2 - sum(en.area for en in poly_closed)
          report.append('- 闭合线: {}, 最大面积 {:.2f}, 刨除孔洞后 {:.2f}'.format(len(poly_closed), max_area, area))
        else:
          area = sum(en.area for en in poly_closed)
          report.append('- 闭合线: {}, 总面积 {:.2f}'.format(len(poly_closed), area))

      if poly_open:
        length = sum(en.length for en in poly_open)
        report.append('- 开放线: {}, 总长度 {:.2f}'.format(len(poly_open), length))

    if endict['Hatch']:
      hatches = endict['Hatch']
      report.append('图案填充: {}'.format(len(hatches)))
      hatch_total = defaultdict(list)
      for en in hatches:
        try:
          hatch_total['Normal'].append(en.area)
        except AutoCADEntityError:
          hatch_total['Error'].append(en)
      report.append('图案填充: {}, 总面积 {:.2f}'.format(len(hatch_total['Normal']), sum(hatch_total['Normal'])))
      if hatch_total['Error']:
        report.append('- 图案填充中 {} 个未取得面积'.format(len(hatch_total['Error'])))
        for en in hatch_total['Error']:
          if error_color:
            en.color = error_color
          if error_layer:
            en.layer = error_layer

    for entity_type in ('Text', 'Line', 'Arc', 'Circle', 'UnknownEntity'):
      if endict[entity_type]:
        report.append('{}: {}'.format(entity_type, len(endict[entity_type])))


    # return '\n'.join(report)
    return report


  def dim_road(self, name, rotate=True, match_existing=True, arc_path=False):
    '''标注道路名称
    指定道路名称, 通常是三到四个字, 以及起止点
    生成这些文字, 并将其均匀分布在起止点的路径上
    默认按照路径方向旋转
    如果之前已选中文字对象, 则模拟其样式(颜色, 图层, 高度)'''
    # 切换至捕捉模式 端点 最近点 垂足
    self.send_lisp('osmode 1665')
    count = len(name)
    template_text = None
    if match_existing:
      for en in self.selecting():
        if 'Text' == en.entity_type:
          template_text = en
          break

    if arc_path:
      startp = self.get_point(hint='指定道路标注的圆弧起点:')
      middlep = self.get_point(hint='指定道路标注的圆弧上任意点:')
      endp = self.get_point(hint='指定道路标注的圆弧终点:')
      self.send_lisp('arc {},{} {},{} {},{}'.format(
        startp[0], startp[1], middlep[0], middlep[1], endp[0], endp[1]))
      arc = self.last_entity()

      points = self._get_interpolate_arc_vertexes(arc, segment=count-1)
      if not SpaceCoordinate().same_point(points[0], startp):
        points.reverse()
      height = arc.arc_length / 15
      arc.delete()
    else:
      startp = self.get_point(hint='指定道路标注的起点:')
      endp = self.get_point(hint='指定道路标注的终点:')
      dx = endp[0]-startp[0]
      dy = endp[1]-startp[1]
      points = [(startp[0]+dx*i/(count-1), startp[1]+dy*i/(count-1)) for i in range(count)]
      height = math.sqrt(dx*dx+dy*dy) / 15

    # 处理道路文字应该旋转的角度，超过45度则要额外+-90度
    if not rotate or arc_path:  # 不允许旋转时或者使用弧线时
      angle = 0
    elif dx == 0:               # 横向无坐标变化时
      angle = 0
    else:
      angle = math.atan(dy/dx)
      if angle > math.pi/4 and angle < math.pi/2:
        angle -= math.pi/2
      elif angle < -math.pi/4 and angle > -math.pi/2:
        angle += math.pi/2

    ret = []
    for char, point in zip(name, points):
      text = self.add_text(text_string=char, origin=point, height=height)
      text.angle = angle
      ret.append(text)

    if template_text:
      for text in ret:
        self.match(template_text, text)

    return ret

  def compare_area(self, *entities, base='first'):
    '''比对面积, 生成文字报告
    算出输入列表中的多段线, 图案填充, 文字对象的面积
    以第一个或最后一个对象的面积为基准, 输出面积相差的报告
    形如
    [ '基准:45385.96',
      '面积:107513.29, 相差:+62127.33(+136.89%)',
      '面积:30283.04, 相差:-15102.92(-33.28%)'
    ]
    '''
    areas = []
    for en in entities:
      if en.entity_type in ('Polyline', 'Hatch'):
        try:
          areas.append(en.area)
        except AutoCADEntityError as e:
          print(e)
          raise
      elif en.entity_type == 'Text':
        matchobj = re.search(r'\d+(\.\d{1,3})?', en.text)
        if matchobj:
          # print(matchobj.group())
          areas.append(float(matchobj.group()))
    # print(areas)
    if 'first' == base:
      base = areas.pop(0)
    elif 'last' == base:
      base = areas.pop()
    else:
      raise
    ret = ['基准:{:.2f}'.format(base)]
    for a in areas:
      s = '面积:{:.2f}, 相差:{:+.2f}({:+.2%})'.format(a, a-base, (a-base)/base)
      ret.append(s)
    return ret



































'''
####### #######  ###### #######
   ##   ##      ##         ##
   ##   ######   #####     ##
   ##   ##           ##    ##
   ##   ####### ######     ##
'''

def test_cad_app():
  '''测试打开CAD文件'''
  cad = AutoCAD()
  cad.open(os.getcwd() + '/../test/file1.dwg')
  cad.open(os.getcwd() + '/../test/file2.dwg')
  for doc in cad.temp_open(os.getcwd() + '/../test/open_cad.dwg'):
    puts(cad.path)
    pl = cad.last_entity()
    print(pl)

def test_cad_listing_entity():
  '''测试取得CAD元素'''
  cad = AutoCAD()
  print(cad.title)
  for en in cad.entities():
    print(en.color)
  for en in cad.entities(reverse=True):
    print(en.layer)
  puts('cad')

def test_cad_autolisp_and_vba():
  '''测试CAD lisp对接'''
  cad = AutoCAD()
  puts(cad.path)
  puts(cad.title)
  cad.send_lisp('circle 0,0 2')
  cad.send_lisp('circle 0,0 5')
  cad.send_lisp('circle 0,0 6')
  cad.send_lisp('circle 0,0 7')

def test_create_cad_entity():
  '测试文档创建CAD文字'
  cad = AutoCAD()
  title = cad.title
  puts('title')
  cad.add_text("111", origin=(100, 200), height=5, alignment='center')
  cad.add_text("222", origin=(100, 200), height=5, alignment='left')
  rec = cad.add_rectangle((10, 10), (300, 400))
  puts(rec.color)
  puts(rec)
  puts(rec.entity_type)
  puts(rec.mid_point)
  cad.add_text("{:.2f}m²".format(rec.area), origin=rec.mid_point, height=5)

  circle = cad.add_circle(origin=(3, 4), radius=10)
  puts(circle)
  for i in range(5):
    circle = cad.add_circle(origin=(2, 3), radius=0.3*i+10)
    circle.color = ColorEditor().random_index()
  pl = cad.last_entity()
  puts(pl)

def test_cad_read_coords():
  '读取polygon坐标'
  cad = AutoCAD()
  puts(cad.title)
  pl = cad.last_entity()
  print(pl)
  vs = pl.vertex_spatial()
  puts(vs)


def test_select_entity():
  '测试查询CAD中的对象'
  cad = AutoCAD()
  cad.open(os.getcwd() + '/../test/open_cad.dwg')
  objs = cad.select()
  print('\n  select()')
  puts(objs)

  objs = cad.select(last=3)
  print('\n  select(last=3)')
  puts(objs)

  objs = cad.select(first=3)
  print('\n  select(first=3)')
  puts(objs)

  objs = cad.select(last=3, entity_type=['Text', 'Circle'])
  print('\n  select(entity_type=[Text, Circle])')
  puts(objs)

  objs = cad.select(last=3, entity_type='Text')
  print('\n  select(entity_type=Text)')
  puts(objs)

  objs = cad.select(first=7, layer='11')  # return selection
  print('\n  select(layer=11)')
  puts(objs)


def test_add_recangle_and_circle():
  cad = AutoCAD()
  from pylon import rand
  width = rand(30, 40)
  height = rand(10, 15)
  bottomleft = 20 + rand(10.0), 20 + rand(10.0)
  topright = 50 + rand(10.0), 50 + rand(10.0)
  rec = cad.add_rectangle(bottomleft, topright)
  rec.color = rand(255)
  print(rec)
  bottomleft = 20 + rand(10.0), 20 + rand(10.0)
  rec = cad.add_rectangle(bottomleft, width=width, height=height)
  rec.color = rand(255)
  print(rec)
  circle = cad.add_circle([3 + rand(0.2), 5 + rand(0.3)], radius=rand(20, 30))
  print(circle)




def test_add_text():
  cad = AutoCAD()
  t1 = cad.add_text("111", origin=(100, 200), height=5, alignment='center')
  t2 = cad.add_text("222", origin=(100, 200), height=5, alignment='left')
  assert t1.size == 5
  t2.size = 20
  assert t2.size == 20
  height = pylon.rand(10, 15)
  bottomleft = (120, 120)
  cad.add_rectangle(bottomleft, width=50, height=height)
  cad.add_text("text123", origin=bottomleft, height=height, alignment='left')


def test_add_point():
  cad = AutoCAD()
  rand = pylon.rand
  p2 = cad.add_point(rand(3.0, 50.0), rand(3.0, 50.0))
  p2.color = ColorEditor().random_index()
  print(p2)
  print(p2.color)


def test_add_polyline2():
  cad = AutoCAD()
  rand = pylon.rand
  pl = cad.add_polyline((rand(10.0, 12), rand(20.0, 22)),
                        (rand(30.0, 31), rand(20.0, 22)),
                        (rand(40.0, 41), rand(50.0, 52)),
                        (rand(20.0, 31), rand(20.0, 32)),
                        closed=True)
  pl.color = ColorEditor().random_index()
  print(pl)


def test_dim_polygon():
  cad = AutoCAD()
  enlist = list(cad.selecting())
  for en in cad.selecting():
    print(en)
  cad.dim_area(*enlist, unit='m²', precision=-2)
  cad.dim_area(*enlist, unit='m²', precision=-3, font_size='*.01')
  cad.dim_area(*enlist, unit='m²', precision=1, font_size=10)


def test_layer():
  cad = AutoCAD()
  puts(cad.layer_names)
  cad.switch_layer('test_create_new_layer', color='green')
  for lay in cad.layers:
    print(lay.color)


def test_circle_to_wipeout():
  cad = AutoCAD()
  for circle in cad.selecting():
    print(circle)
    cad.wipeout(circle)


def test_vertex_spacial():
  cad = AutoCAD()
  cad.open(os.getcwd() + '/../test/polyline.dwg')
  en = cad.last_entity()
  puts(en.vertex_spatial())
  # en.closed = True
  puts(en.vertex_spatial())
  # [(1, 197.939, 85.264, 9.247, 0, 0.000),
  # (2, 204.743, 91.526, 9.247, 0, 0.000),
  # (3, 211.546, 85.264, 13.698, 0, 0.000),
  # (4, 211.546, 98.962, 38.482, 42.805, 0.229),
  # (5, 174.347, 98.962, 9.199, 0, 0.000),
  # (6, 178.753, 90.887, 7.143, 0, 0.000),
  # (7, 174.347, 85.264, 23.592, 0, 0.000)
  # ]


def test_interpolate_polyline():
  '''测试加密poly'''
  cad = AutoCAD()
  pl = cad.last_entity()
  cad.interpolate_polyline(polyline=pl, distance=1.5,
                           delete_original=False,
                           break_at_vertexes=False)


def test_rebuild_arc_polyline():
  '''测试加密poly返算圆弧'''
  cad = AutoCAD()
  for pl in cad.selecting():
    newpl = cad.rebuild_arc_polyline(pl, threshold=3, segment_points=None)
    newpl.color = 'red'


def test_rebuild_arc_polyline2():
  ''' 测试加密poly返算圆弧 指定部分节点作为端点
     此类端点两侧不应出于同一个圆弧'''
  cad = AutoCAD()
  segment_points = [(p.x, p.y) for p in cad.select_by_type('Point')]
  segment_points | puts()
  for pl in cad.selecting():
    newpl = cad.rebuild_arc_polyline(pl, threshold=3,
                                     segment_points=segment_points)
    newpl.color = 'red'








######  ####### ##   ## ###### ###### ##   ##  ######
##   ## ##      ###  ## ##   ##  ##   ###  ## ##
######  ######  ## # ## ##   ##  ##   ## # ## ##  ###
##      ##      ##  ### ##   ##  ##   ##  ### ##   ##
##      ####### ##   ## ###### ###### ##   ##  #####

def pending_create_hatch():
  cad = AutoCAD()
  cad.to_hatch(pl)
  for en in cad.selecting():
    print(en)



def pending_cad_undo_group():
  cad = AutoCAD()
  with cad.undo_group():
    cad.send_command(...)
    cad.send_command(...)
    cad.send_command(...)

def pending_cad_silent_executing():
  cad = AutoCAD()
  # should not show cmd excuting methods
  with cad.selence_exceute():
    cad.send_command(...)
    cad.send_command(...)
    cad.send_command(...)


def pending_test_select_entity_on_screen_last():
  '测试查询CAD中的对象 select_on_screen select_last'
  cad = AutoCAD()
  cad.open(os.getcwd() + '/../test/open_cad.dwg')
  cad.select_on_screen()
  cad.select_last()



def pending_test_insert_cad_entitiesu():
  from AutoCADEntity import AutoCADPolyline, AutoCADPoint
  cad = AutoCAD()
  po = cad.add_point(2, 4)
  po = cad.add_point([2, 4])
  type(po)                   # AutoCADPoint
  po = AutoCADPoint(2, 4)    # point,not inserted
  cad.insert(po, x=0, y=0)
  cad.insert(block, x=0, y=0)

  pline = cad.add_polyline([(1, 3), (2, 4), (3, 3)], close=True)
  pline = AutoCADPolyline([(1, 3), (2, 4), (3, 3)], close=True)
  # pline.draw_frame()
  pline.coordinates
  pline.coordinates_info
  cad.draw_frame(pline)
  cad.draw_frame(entities, padding='20%')


def pending_fetch_road_names():
  '''
  依据坐标生成周边道路 ★★★★★
  - 道路信息记录
  - dwg 图, 仅含路中线和道路名称
  - 中线为连续join过的线
  - 以中线和其上的名称压盖判断道路名称
  - 使用shp版?
  - 地块裁切后检测矩形区域内的切出的道路
  - 按照虚拟中线位置标注路名称

  从巨大地形图中裁切polygon区域 ★★★★★
  - 首先矩形区域
  - 加工 : 断线 过滤部分图层 转换颜色 成块
  - 巨大图形时防止当机
  '''





def exec_figlet():
  pylon.generate_figlet(text='AutoCAD', fonts=['space_op'])
  pylon.generate_figlet(text='select', fonts=['space_op'])
  pylon.generate_figlet(text='create', fonts=['space_op'])
  pylon.generate_figlet(text='entity', fonts=['space_op'])
  pylon.generate_figlet(text='command', fonts=['space_op'])
  pylon.generate_figlet(text='layer', fonts=['space_op'])
  pylon.generate_figlet(text='test', fonts=['space_op'])
  pylon.generate_figlet(text='label', fonts=['space_op'])

