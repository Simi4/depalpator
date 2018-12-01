import shutil
import os
from collections import defaultdict
from glob import glob
from xml.etree import ElementTree as ET
import pydotplus
from PIL import Image


all_groups = set()
unique_names = set()


if os.path.isdir('graph_data'):
    shutil.rmtree('graph_data')
os.mkdir('graph_data')


def get_bndbox(obj):
    xmin = int(obj.find('bndbox/xmin').text)
    ymin = int(obj.find('bndbox/ymin').text)
    xmax = int(obj.find('bndbox/xmax').text)
    ymax = int(obj.find('bndbox/ymax').text)
    return (xmin, ymin, xmax, ymax)



class Group:

    def __init__(self, obj, path, img):
        self.filePath = path.replace('\\', '/')
        self.imgPath = None
        self.img = img
        self.rect = get_bndbox(obj)
        self.symbols = set()

    def contains(self, symbol):
        return (self.rect[0] < symbol.x < self.rect[2] and
                self.rect[1] < symbol.y < self.rect[3])

    def add(self, symbol):
        self.symbols.add(symbol)

    def freeze(self):
        self.symbols = tuple(sorted(self.symbols))

    def save_image(self, index):
        if self.imgPath:
            return self.imgPath
        self.index = index
        im = self.img.crop(self.rect)
        self.imgPath = f'graph_data/{index}.png'
        im.save(self.imgPath)
        return self.imgPath

    def __hash__(self):
        return hash(tuple(sorted(self.symbols)))

    def __eq__(self, other):
        if not other:
            return False
        a = tuple(sorted(self.symbols))
        b = tuple(sorted(other.symbols))
        return a == b

    def __lt__(self, other):
        return repr(self) < repr(other)

    def __repr__(self):
        return ', '.join(map(repr, sorted(self.symbols)))



class Symbol:

    def __init__(self, obj):
        xmin, ymin, xmax, ymax = get_bndbox(obj)
        self.name = obj.find('name').text
        self.x = (xmin + xmax) // 2
        self.y = (ymin + ymax) // 2

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        return str(self) == str(other)

    def __lt__(self, other):
        return repr(self) < repr(other)

    def __repr__(self):
        return self.name



for path in glob('data/PascalVOC/*.xml'):
    xml = ET.parse(path)

    img = Image.open('data/images/' + xml.find('filename').text)

    groups = []
    symbols = []
    for obj in xml.findall('object'):
        objName = obj.find('name').text
        if objName == 'group':
            groups.append(Group(obj, path, img))
        elif objName != 'symbol':
            unique_names.add(objName)
            symbols.append(Symbol(obj))

    for symbol in symbols:
        for group in groups:
            if group.contains(symbol):
                group.add(symbol)

    all_groups |= set(groups)



all_symbols = defaultdict(list)
all_groups = tuple(sorted(all_groups))
root = ET.Element('root')
tree = ET.ElementTree(root)

for i, group in enumerate(all_groups):
    group.freeze()
    group.save_image(i)

    for symbol in group.symbols:
        all_symbols[symbol].append(i + 1)

    node = ET.SubElement(root, 'group')
    ET.SubElement(node, 'name').text = repr(group)
    ET.SubElement(node, 'id').text = str(i + 1)
    ET.SubElement(node, 'image').text = group.imgPath
    #ET.SubElement(node, 'rect').text = str(group.rect)
    

tree.write('graph_data/groups.xml', encoding='utf-8')
del tree
del root



def find(key, parent=None, gr=None, depth=0):
    if not gr:
        node = pydotplus.Node(str(key))
    else:
        node = pydotplus.Node(f'f{gr!r}', shape='box')
    graph.add_node(node)
    if parent:
        graph.add_edge(pydotplus.Edge(parent, node))
    if depth > 3:
        return
    for group in all_groups:
        if group == gr:
            continue
        if key in group.symbols:
            for symbol in group.symbols:
                if symbol == key:
                    continue
                find(symbol, node, group, depth + 1)

graph = pydotplus.Dot(graph_type = 'digraph', simplify=True)

find('T.вр.дискр')

graph.write_dot('result.dot')





tree = ET.parse('data/symbols.xml')
root = tree.getroot()
for element in root.findall('symbol/name'):
    if element.text in unique_names:
        unique_names.remove(element.text)

for name in unique_names:
    node = ET.SubElement(root, 'symbol')
    ET.SubElement(node, 'name').text = name
    ET.SubElement(node, 'descr').text = ''


tree.write('data/symbols2.xml', encoding='utf-8')
