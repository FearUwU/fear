# -*- coding: utf-8 -*-
"""
All the code below was hacked together from https://github.com/mvictor212/pyBarcode
Which is itself a port of python-barcode which is no longer available

"""

import gzip
import os
import xml.dom
import string
from redbot.core.data_manager import bundled_data_path


try:
    import Image, ImageDraw, ImageFont
except ImportError:
    try:
        from PIL import Image, ImageDraw, ImageFont  # lint:ok
    except ImportError:
        import sys
        sys.stderr.write('PIL not found. Image output disabled.\n\n')
        Image = ImageDraw = ImageFont = None  # lint:ok

try:
    _strbase = basestring  # lint:ok
except NameError:
    _strbase = str


def mm2px(mm, dpi=300):
    return (mm * dpi) / 25.4


def pt2mm(pt):
    return pt * 0.352777778


def _set_attributes(element, **attributes):
    for key, value in attributes.items():
        element.setAttribute(key, value)


def create_svg_object():
    imp = xml.dom.getDOMImplementation()
    doctype = imp.createDocumentType(
        'svg',
        '-//W3C//DTD SVG 1.1//EN',
        'http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd'
    )
    document = imp.createDocument(None, 'svg', doctype)
    _set_attributes(document.documentElement, version='1.1',
                    xmlns='http://www.w3.org/2000/svg')
    return document


SIZE = '{0:.3f}mm'
COMMENT = 'Autogenerated with pyBarcode {0}'.format("TrustyCogs")
PATH = os.path.dirname(os.path.abspath(__file__))

# Sizes
MIN_SIZE = 0.2
MIN_QUIET_ZONE = 2.54


# Charsets for code 39
REF = (tuple(string.digits) + tuple(string.ascii_uppercase) +
       ('-', '.', ' ', '$', '/', '+', '%'))
B = '1'
E = '0'
CODES = (
    '101000111011101', '111010001010111', '101110001010111',
    '111011100010101', '101000111010111', '111010001110101',
    '101110001110101', '101000101110111', '111010001011101',
    '101110001011101', '111010100010111', '101110100010111',
    '111011101000101', '101011100010111', '111010111000101',
    '101110111000101', '101010001110111', '111010100011101',
    '101110100011101', '101011100011101', '111010101000111',
    '101110101000111', '111011101010001', '101011101000111',
    '111010111010001', '101110111010001', '101010111000111',
    '111010101110001', '101110101110001', '101011101110001',
    '111000101010111', '100011101010111', '111000111010101',
    '100010111010111', '111000101110101', '100011101110101',
    '100010101110111', '111000101011101', '100011101011101',
    '100010001000101', '100010001010001', '100010100010001',
    '101000100010001',
)

EDGE = '100010111011101'
MIDDLE = '0'

# MAP for assigning every symbol (REF) to (reference number, barcode)
MAP = dict(zip(REF, enumerate(CODES)))

class BarcodeError(Exception):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg


class IllegalCharacterError(BarcodeError):
    """Raised when a barcode-string contains illegal characters."""


class BarcodeNotFoundError(BarcodeError):
    """Raised when an unknown barcode is requested."""


class NumberOfDigitsError(BarcodeError):
    """Raised when the number of digits do not match."""


class WrongCountryCodeError(BarcodeError):
    """Raised when a JAN (Japan Article Number) don't starts with 450-459
    or 490-499.
    """





class BaseWriter(object):
    """Baseclass for all writers.

    Initializes the basic writer options. Childclasses can add more
    attributes and can set them directly or using
    `self.set_options(option=value)`.

    :parameters:
        initialize : Function
            Callback for initializing the inheriting writer.
            Is called: `callback_initialize(raw_code)`
        paint_module : Function
            Callback for painting one barcode module.
            Is called: `callback_paint_module(xpos, ypos, width, color)`
        paint_text : Function
            Callback for painting the text under the barcode.
            Is called: `callback_paint_text(xpos, ypos)` using `self.text`
            as text.
        finish : Function
            Callback for doing something with the completely rendered
            output.
            Is called: `return callback_finish()` and must return the
            rendered output.
    """

    def __init__(self, initialize=None, paint_module=None, paint_text=None,
                 finish=None):
        self._callbacks = dict(initialize=initialize, paint_module=paint_module,
                               paint_text=paint_text, finish=finish)
        self.module_width = 10
        self.module_height = 10
        self.font_size = 10
        self.quiet_zone = 6.5
        self.background = 'white'
        self.foreground = 'black'
        self.text = ''
        self.human = '' # human readable text
        self.text_distance = 5
        self.center_text = True

    def calculate_size(self, modules_per_line, number_of_lines, dpi=300):
        """Calculates the size of the barcode in pixel.

        :parameters:
            modules_per_line : Integer
                Number of modules in one line.
            number_of_lines : Integer
                Number of lines of the barcode.
            dpi : Integer
                DPI to calculate.

        :returns: Width and height of the barcode in pixel.
        :rtype: Tuple
        """
        width = 2 * self.quiet_zone + modules_per_line * self.module_width
        height = 2.0 + self.module_height * number_of_lines
        if self.font_size and self.text:
            height += pt2mm(self.font_size) / 2 + self.text_distance
        return int(mm2px(width, dpi)), int(mm2px(height, dpi))

    def save(self, filename, output):
        """Saves the rendered output to `filename`.

        :parameters:
            filename : String
                Filename without extension.
            output : String
                The rendered output.

        :returns: The full filename with extension.
        :rtype: String
        """
        raise NotImplementedError

    def register_callback(self, action, callback):
        """Register one of the three callbacks if not given at instance
        creation.

        :parameters:
            action : String
                One of 'initialize', 'paint_module', 'paint_text', 'finish'.
            callback : Function
                The callback function for the given action.
        """
        self._callbacks[action] = callback

    def set_options(self, options):
        """Sets the given options as instance attributes (only
        if they are known).

        :parameters:
            options : Dict
                All known instance attributes and more if the childclass
                has defined them before this call.

        :rtype: None
        """
        for key, val in options.items():
            key = key.lstrip('_')
            if hasattr(self, key):
                setattr(self, key, val)

    def render(self, code):
        """Renders the barcode to whatever the inheriting writer provides,
        using the registered callbacks.

        :parameters:
            code : List
                List of strings matching the writer spec
                (only contain 0 or 1).
        """
        if self._callbacks['initialize'] is not None:
            self._callbacks['initialize'](code)
        ypos = 0.25
        for cc, line in enumerate(code):
            """
            Pack line to list give better gfx result, otherwise in can result in aliasing gaps
            '11010111' -> [2, -1, 1, -1, 3]
            """         
            line += ' ' 
            c = 1
            mlist = []
            for i in range(0, len(line) - 1):
                if line[i] == line[i+1]:
                    c += 1
                else:
                    if line[i] == "1":
                        mlist.append(c)
                    else:
                        mlist.append(-c)
                    c = 1
            # Left quiet zone is x startposition
            xpos = self.quiet_zone
            bxs = xpos # x start of barcode         
            for mod in mlist:
                if mod < 1:
                    color = self.background
                else:
                    color = self.foreground
                self._callbacks['paint_module'](xpos, ypos, self.module_width * abs(mod), color) # remove painting for background colored tiles?
                xpos += self.module_width * abs(mod)
            bxe = xpos
            # Add right quiet zone to every line, except last line, quiet zone already provided with background, should it be removed complety?
            if (cc + 1) != len(code):
                self._callbacks['paint_module'](xpos, ypos, self.quiet_zone, self.background)
            ypos += self.module_height
        if self.text and self._callbacks['paint_text'] is not None:
            ypos += self.text_distance
            if self.center_text:
                xpos = bxs + ((bxe - bxs) / 2.0) # better center position for text
            else:
                xpos = bxs
            self._callbacks['paint_text'](xpos, ypos)
        return self._callbacks['finish']()


class SVGWriter(BaseWriter):

    def __init__(self):
        BaseWriter.__init__(self, self._init, self._create_module,
                            self._create_text, self._finish)
        self.compress = False
        self.dpi = 25.4
        self._document = None
        self._root = None
        self._group = None

    def _init(self, code):
        width, height = self.calculate_size(len(code[0]), len(code), self.dpi)
        self._document = create_svg_object()
        self._root = self._document.documentElement
        attributes = dict(width=SIZE.format(width), height=SIZE.format(height))
        _set_attributes(self._root, **attributes)
        self._root.appendChild(self._document.createComment(COMMENT))
        # create group for easier handling in 3th party software like corel draw, inkscape, ...
        group = self._document.createElement('g')
        attributes = dict(id='barcode_group')
        _set_attributes(group, **attributes)
        self._group = self._root.appendChild(group)     
        background = self._document.createElement('rect')
        attributes = dict(width='100%', height='100%',
                          style='fill:{0}'.format(self.background))
        _set_attributes(background, **attributes)
        self._group.appendChild(background)

    def _create_module(self, xpos, ypos, width, color):
        element = self._document.createElement('rect')
        attributes = dict(x=SIZE.format(xpos), y=SIZE.format(ypos),
                          width=SIZE.format(width),
                          height=SIZE.format(self.module_height),
                          style='fill:{0};'.format(color))
        _set_attributes(element, **attributes)
        self._group.appendChild(element)

    def _create_text(self, xpos, ypos):
        element = self._document.createElement('text')
        attributes = dict(x=SIZE.format(xpos), y=SIZE.format(ypos),
                          style='fill:{0};font-size:{1}pt;text-anchor:'
                                'middle;'.format(self.foreground,
                                                 self.font_size))
        _set_attributes(element, **attributes)
        # check option to override self.text with self.human (barcode as human readable data, can be used to print own formats)
        if self.human != '':
            barcodetext = self.human
        else:
            barcodetext = self.text
        text_element = self._document.createTextNode(barcodetext)
        element.appendChild(text_element)
        self._group.appendChild(element)

    def _finish(self):
        if self.compress:
            return self._document.toxml(encoding='UTF-8')
        else:
            return self._document.toprettyxml(indent=4 * ' ', newl=os.linesep,
                                              encoding='UTF-8')

    def save(self, filename, output):
        if self.compress:
            _filename = '{0}.svgz'.format(filename)
            f = gzip.open(_filename, 'wb')
            f.write(output)
            f.close()
        else:
            _filename = '{0}.svg'.format(filename)
            with open(_filename, 'wb') as f:
                f.write(output)
        return _filename


if Image is None:
    ImageWriter = None
else:
    class ImageWriter(BaseWriter):


        def __init__(self, COG):
            BaseWriter.__init__(self, self._init, self._paint_module,
                                self._paint_text, self._finish)
            self.format = 'PNG'
            self.dpi = 300
            self._image = None
            self._draw = None
            self.FONT = str(bundled_data_path(COG)/ "arial.ttf")

        def _init(self, code):
            size = self.calculate_size(len(code[0]), len(code), self.dpi)
            self._image = Image.new('RGB', size, self.background)
            self._draw = ImageDraw.Draw(self._image)

        def _paint_module(self, xpos, ypos, width, color):
            size = [(mm2px(xpos, self.dpi), mm2px(ypos, self.dpi)),
                    (mm2px(xpos + width, self.dpi),
                     mm2px(ypos + self.module_height, self.dpi))]
            self._draw.rectangle(size, outline=color, fill=color)

        def _paint_text(self, xpos, ypos):
            font = ImageFont.truetype(self.FONT, self.font_size * 2)
            width, height = font.getsize(self.text)
            pos = (mm2px(xpos, self.dpi) - width // 2,
                   mm2px(ypos, self.dpi) - height // 4)
            self._draw.text(pos, self.text, font=font, fill=self.foreground)

        def _finish(self):
            return self._image

        def save(self, filename, output):
            filename = '{0}.{1}'.format(filename, self.format.lower())
            output.save(filename, self.format.upper())
            return filename

class Barcode(object):

    name = ''

    raw = None

    digits = 0

    default_writer = SVGWriter

    default_writer_options = {
        'module_width': 0.2,
        'module_height': 15.0,
        'quiet_zone': 6.5,
        'font_size': 10,
        'text_distance': 5.0,
        'background': 'white',
        'foreground': 'black',
        'write_text': True,
        'text': '',
    }

    def to_ascii(self):
        code = self.build()
        for i, line in enumerate(code):
            code[i] = line.replace('1', 'X').replace('0', ' ')
        return '\n'.join(code)

    def __repr__(self):
        return '<{0}({1!r})>'.format(self.__class__.__name__,
                                     self.get_fullcode())

    def build(self):
        raise NotImplementedError

    def get_fullcode(self):
        """Returns the full code, encoded in the barcode.

        :returns: Full human readable code.
        :rtype: String
        """
        raise NotImplementedError

    def save(self, filename, options=None):
        """Renders the barcode and saves it in `filename`.

        :parameters:
            filename : String
                Filename to save the barcode in (without filename
                extension).
            options : Dict
                The same as in `self.render`.

        :returns: The full filename with extension.
        :rtype: String
        """
        output = self.render(options)
        _filename = self.writer.save(filename, output)
        return _filename

    def write(self, fp, options=None):
        """Renders the barcode and writes it to the file like object
        `fp`.

        :parameters:
            fp : File like object
                Object to write the raw data in.
            options : Dict
                The same as in `self.render`.
        """
        output = self.render(options)
        if hasattr(output, 'tostring'):
            output.save(fp, format=self.writer.format)
        else:
            fp.write(output)

    def render(self, writer_options=None):
        """Renders the barcode using `self.writer`.

        :parameters:
            writer_options : Dict
                Options for `self.writer`, see writer docs for details.

        :returns: Output of the writers render method.
        """
        options = Barcode.default_writer_options.copy()
        options.update(writer_options or {})
        if options['write_text']:
            if options['text'] != '':
                options['text'] += ' - ' + self.get_fullcode()
            else:
                options['text'] = self.get_fullcode()
        self.writer.set_options(options)
        code = self.build()
        raw = Barcode.raw = self.writer.render(code)
        return raw

def check_code(code, name, allowed):
    wrong = []
    for char in code:
        if char not in allowed:
            wrong.append(char)
    if wrong:
        raise IllegalCharacterError('The following characters are not '
            'valid for {name}: {wrong}'.format(name=name,
                wrong=', '.join(wrong)))

class Code39(Barcode):
    r"""Initializes a new Code39 instance.

    :parameters:
        code : String
            Code 39 string without \* and checksum (added automatically if
            `add_checksum` is True).
        writer : barcode.writer Instance
            The writer to render the barcode (default: SVGWriter).
        add_checksum : Boolean
            Add the checksum to code or not (default: True).
    """

    name = 'Code 39'

    def __init__(self, code, writer=None, add_checksum=True):
        self.code = code.upper()
        if add_checksum:
            self.code += self.calculate_checksum()
        self.writer = writer or Barcode.default_writer()
        check_code(self.code, self.name, REF)

    def __unicode__(self):
        return self.code

    __str__ = __unicode__

    def get_fullcode(self):
        return self.code

    def calculate_checksum(self):
        check = sum([MAP[x][0] for x in self.code]) % 43
        for k, v in MAP.items():
            if check == v[0]:
                return k

    def build(self):
        chars = [EDGE]
        for char in self.code:
            chars.append(MAP[char][1])
        chars.append(EDGE)
        return [MIDDLE.join(chars)]

    def render(self, writer_options):
        options = dict(module_width=MIN_SIZE, quiet_zone=MIN_QUIET_ZONE)
        options.update(writer_options or {})
        return Barcode.render(self, options)

def get_barcode(name, code=None, writer=None):
    try:
        barcode = Code39
    except KeyError:
        raise BarcodeNotFoundError('The barcode {0!r} you requested is not '
                                   'known.'.format(name))
    if code is not None:
        return barcode(code, writer)
    else:
        return barcode


def generate(name, code, writer=None, output=None, writer_options=None):
    options = writer_options or {}
    barcode = get_barcode(name, code, writer)
    if isinstance(output, _strbase):
        fullname = barcode.save(output, options)
        return fullname
    else:
        barcode.write(output, options)



