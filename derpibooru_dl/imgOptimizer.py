#!/usr/bin/python3
# -*- coding: utf-8 -*-
import os, subprocess, math, struct, io
from PIL import Image
import abc
import config

MAX_SIZE = 16383

if config.MAX_SIZE is not None:
    MAX_SIZE = min(16383, config.MAX_SIZE)


def loading_thread(encoder, outbuf, i):
    outbuf[i] += encoder.communicate()[0]


sumos = 0
sumsize = 0
avq = 0
items = 0


def pipe_send(pipe):
    if pipe is not None:
        pipe.send((sumos, sumsize, avq, items))
        pipe.close()


is_arithmetic_SOF = {
    b'\xff\xc0': False,
    b'\xff\xc1': False,
    b'\xff\xc2': False,
    b'\xff\xc3': False,
    b'\xff\xc5': False,
    b'\xff\xc6': False,
    b'\xff\xc7': False,
    b'\xff\xc8': True,
    b'\xff\xc9': True,
    b'\xff\xca': True,
    b'\xff\xcb': True,
    b'\xff\xcd': True,
    b'\xff\xce': True,
    b'\xff\xcf': True
}


class Converter():
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def __init__(self, path):
        self._path = ""
        self._images = []
        self._loop = 0
        self._duration = []

    @abc.abstractmethod
    def close(self):
        pass

    def compress(self, quality: int = 90, fast: bool = True, lossless: bool = False) -> memoryview:
        print('try to convert, quality={}, f={}'.format(quality, fast))
        out_io = io.BytesIO()
        kwargs = dict()
        if fast and not lossless:
            kwargs = {
                'method': 3,
                'loop': self._loop,
                'duration': self._duration,
                'quality': quality,
            }
        elif fast and lossless:
            kwargs = {
                'method': 3,
                'loop': self._loop,
                'duration': self._duration,
            }
        elif not fast and not lossless:
            kwargs = {
                'loop': self._loop,
                'duration': self._duration,
                'quality': quality,
                'method': 6
            }
        elif not fast and lossless:
            kwargs = {
                'loop': self._loop,
                'duration': self._duration,
                'method': 6,
                'lossless': True,
                'quality': 100
            }
        if len(self._images) > 1:
            self._images[0].save(
                out_io,
                'WEBP',
                save_all=True,
                append_images=self._images[1:],
                **kwargs
            )
        else:
            self._images[0].save(
                out_io,
                'WEBP',
                **kwargs
            )
        return out_io.getbuffer()


class GIFconverter(Converter):

    def __init__(self, gif):
        # self._path = gif_path
        in_io = io.BytesIO()
        img = None
        if type(gif) is str:
            img = Image.open(gif)
        elif isinstance(gif, (bytes, bytearray)):
            in_io = io.BytesIO(gif)
            img = Image.open(in_io)
        else:
            raise Exception()
        if 'duration' in img.info:
            self._duration = img.info['duration']
        else:
            self._duration = 0
        if 'loop' in img.info:
            self._loop = img.info['loop']
        else:
            self._loop = 1
        self._width = img.width
        self._height = img.height
        img.close()
        self._images = []
        ffprocess = None
        tmpfilename = None
        if type(gif) is str:
            commandline = ['ffmpeg',
                           '-loglevel', 'error',
                           '-i', gif,
                           '-f', 'image2pipe',
                           '-pix_fmt', 'rgba',
                           '-an',
                           '-vcodec', 'rawvideo', '-']
            ffprocess = subprocess.Popen(commandline, stdout=subprocess.PIPE)
        elif isinstance(gif, (bytes, bytearray)):
            tmpfilename = "ffmpeg_processing.gif"
            tmpfile = open(tmpfilename, 'bw')
            tmpfile.write(gif)
            tmpfile.close()
            commandline = ['ffmpeg',
                           '-loglevel', 'error',
                           '-i', tmpfilename,
                           '-f', 'image2pipe',
                           '-pix_fmt', 'rgba',
                           '-an',
                           '-vcodec', 'rawvideo', '-']
            ffprocess = subprocess.Popen(commandline, stdout=subprocess.PIPE)
        frame_size = self._width * self._height * 4
        buffer = ffprocess.stdout.read(frame_size)
        while len(buffer) == frame_size:
            self._images.append(Image.frombuffer("RGBA", (self._width, self._height), buffer, "raw", "RGBA", 0, 1))
            buffer = ffprocess.stdout.read(frame_size)
        ffprocess.stdout.close()
        if tmpfilename is not None:
            os.remove(tmpfilename)

    def close(self):
        for frame in self._images:
            frame.close()


class APNGconverter(Converter):
    def __init__(self, png_path):
        self._path = png_path
        subprocess.run(['apngdis', png_path])
        os.chdir(os.path.dirname(png_path))
        self._duration = []
        self._loop = 0
        self._images = []
        self._fname = []
        zeroes_count = 0
        i = 1
        test_zeroes = ''
        while not os.path.isfile('apngframe' + test_zeroes + str(i) + '.png'):
            zeroes_count += 1
            test_zeroes += '0'
        file_name = 'apngframe'
        file_name += str(i).zfill(zeroes_count + 1)

        while os.path.isfile(file_name + '.png'):
            try:
                info_file = open(file_name + '.txt')
            except FileNotFoundError:
                break
            info_file.seek(6)
            self._duration.append(int(round(eval(info_file.read()) * 1000)))
            info_file.close()
            self._fname.append(file_name + '.png')
            self._images.append(Image.open(file_name + '.png'))
            os.remove(file_name + '.txt')
            file_name = 'apngframe'
            i += 1
            file_name += str(i).zfill(zeroes_count + 1)

    def close(self):
        for frame in self._fname:
            os.remove(frame)
        for frame in self._images:
            frame.close()


def is_arithmetic_jpg(file_path):
    file = open(file_path, 'rb')
    header = file.read(2)
    if header != b'\xff\xd8':
        file.close()
        raise OSError
    arithmetic = None
    marker = b"aaa"
    while len(marker):
        marker = file.read(2)
        if marker in is_arithmetic_SOF.keys():
            file.close()
            arithmetic = is_arithmetic_SOF[marker]
            return arithmetic
        elif len(marker):
            frame_len = struct.unpack('>H', file.read(2))[0]
            file.seek(frame_len - 2, 1)
    file.close()
    return None


def animation2webm(source, out_file, crf=32):
    fname = ""
    if type(source) is str:
        fname = source
    elif isinstance(source, (bytes, bytearray)):
        fname = "transcode"
        file = open(fname, "bw")
        file.write(source)
        file.close()
    subprocess.call(
        [
            'ffmpeg',
            '-loglevel', 'error',
            '-i', fname,
            '-pix_fmt', 'yuv422p',
            '-c:v', 'libvpx-vp9',
            '-crf', str(crf),
            '-b:v', '0',
            '-profile:v', '1',
            '-f', 'webm',
            out_file
        ]
    )
    if isinstance(source, (bytes, bytearray)):
        os.remove(fname)


def check_exists(source, path, filename):
    fname = os.path.join(path, filename)
    if os.path.splitext(source)[1].lower() == '.png':
        return os.path.isfile(fname + '.webp') or os.path.isfile(fname + '.webm')
    elif os.path.splitext(source)[1].lower() in {'.jpg', '.jpeg'}:
        return os.path.isfile(fname + '.webp')
    elif os.path.splitext(source)[1].lower() == '.gif':
        return os.path.isfile(fname + '.webp') or os.path.isfile(fname+'.webm')


class AlreadyOptimizedSourceException(Exception):
    pass


class NotOptimizableSourceException(Exception):
    pass


class BaseTranscoder:
    __metaclass__ = abc.ABCMeta

    def __init__(self, source, path:str, file_name:str, item_data:dict, pipe):
        self._source = source
        self._path = path
        self._file_name = file_name
        self._item_data = item_data
        self._pipe = pipe
        self._size = 0
        self._output_file = os.path.join(path, file_name)
        self._output_size = 0
        self._quality = 95
        self._fext = 'webp'
        self._webp_output = False

    @abc.abstractmethod
    def _encode(self):
        pass

    @abc.abstractmethod
    def _save(self):
        pass

    def _record_timestamps(self):
        pass

    @abc.abstractmethod
    def _remove_source(self):
        pass

    @abc.abstractmethod
    def _optimisations_failed(self):
        pass

    @abc.abstractmethod
    def _open_image(self) -> Image.Image:
        pass

    @abc.abstractmethod
    def _get_source_size(self) -> int:
        pass

    @abc.abstractmethod
    def _set_utime(self) -> None:
        pass

    def transcode(self):
        global sumsize
        global sumos
        global avq
        global items
        self._size = self._get_source_size()
        try:
            self._encode()
        except (
            AlreadyOptimizedSourceException,
            NotOptimizableSourceException
        ):
            pipe_send(self._pipe)
            return
        self._record_timestamps()
        if (self._size > self._output_size) and (self._output_size > 0):
            self._save()
            self._set_utime()
            print(('save {} kbyte ({}%) quality = {}').format(
                round((self._size - self._output_size) / 1024, 2),
                round((1 - self._output_size / self._size) * 100, 2),
                self._quality
            ))
            sumsize += self._size
            sumos += self._output_size
            avq += self._quality
            items += 1
            self._remove_source()
        else:
            self._optimisations_failed()
        if config.enable_multiprocessing:
            pipe_send(self._pipe)


class SourceRemovable(BaseTranscoder):
    __metaclass__ = abc.ABCMeta

    def _remove_source(self):
        os.remove(self._source)


class UnremovableSource(BaseTranscoder):
    __metaclass__ = abc.ABCMeta

    def _remove_source(self):
        pass


class FilePathSource(BaseTranscoder):
    __metaclass__ = abc.ABCMeta

    def __init__(self, source:str, path:str, file_name:str, item_data:dict, pipe):
        BaseTranscoder.__init__(self, source, path, file_name, item_data, pipe)
        self._tmp_src = None

    def _record_timestamps(self):
        self._atime = os.path.getatime(self._source)
        self._mtime = os.path.getmtime(self._source)

    def _open_image(self) -> Image.Image:
        return Image.open(self._source)

    def _get_source_size(self) -> int:
        return os.path.getsize(self._source)


class InMemorySource(UnremovableSource):
    __metaclass__ = abc.ABCMeta

    def __init__(self, source:bytearray, path:str, file_name:str, item_data:dict, pipe):
        BaseTranscoder.__init__(self, source, path, file_name, item_data, pipe)

    def _open_image(self) -> Image.Image:
        src_io = io.BytesIO(self._source)
        return Image.open(src_io)

    def _get_source_size(self) -> int:
        return len(self._source)

    def _set_utime(self) -> None:
        pass


class WEBM_VideoOutputFormat(BaseTranscoder):
    def animation_encode(self):
        self._quality = 85
        animation2webm(self._source, self._output_file + '.webm')
        self._output_size = os.path.getsize(self._output_file + '.webm')

    @abc.abstractmethod
    def _all_optimisations_failed(self):
        pass

    @abc.abstractmethod
    def get_converter_type(self):
        pass

    def gif_optimisations_failed(self):
        print("optimisations_failed")
        global sumsize
        global sumos
        global avq
        global items
        os.remove(self._output_file + '.webm')
        self._fext = 'webp'
        converter = self.get_converter_type()(self._source)
        out_data = converter.compress(lossless=True)
        self._output_size = len(out_data)
        if self._output_size >= self._size:
            self._all_optimisations_failed()
        else:
            out_data = converter.compress(lossless=True, fast=False)
            self._output_size = len(out_data)
            outfile = open(self._output_file + '.webp', 'wb')
            outfile.write(out_data.tobytes())
            outfile.close()
            print(('save {} kbyte ({}%) quality = {}').format(
                round((self._size - self._output_size) / 1024, 2),
                round((1 - self._output_size / self._size) * 100, 2),
                self._quality
            ))
            self._set_utime()
            self._remove_source()
            sumsize += self._size
            sumos += self._output_size
            avq += self._quality
            items += 1
        converter.close()


class WEBP_output(WEBM_VideoOutputFormat):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def _apng_test_convert(self, img):
        pass

    @abc.abstractmethod
    def _transparency_check(self, img: Image.Image) -> bool:
        pass

    @abc.abstractmethod
    def _invalid_file_exception_handle(self, e):
        pass

    def _lossless_encode(self, img:Image.Image) -> None:
        lossless_out_io = io.BytesIO()
        img.save(lossless_out_io, format="WEBP", lossless=True, quality=100, method=6)
        self._lossless_data = lossless_out_io.getbuffer()

    def _lossy_encode(self, img:Image.Image) -> None:
        lossy_out_io = io.BytesIO()
        img.save(lossy_out_io, format="WEBP", lossless=False, quality=self._quality, method=6)
        self._lossy_data = lossy_out_io.getbuffer()

    def _webp_encode(self, img):
        self._lossless = False
        self._animated = False
        self._apng_test_convert(img)
        if img.mode in {'1', 'P'}:
            raise NotOptimizableSourceException()
        if img.mode == 'RGBA':
            self._lossless = self._transparency_check(img)
        try:
            if (img.width > MAX_SIZE) | (img.height > MAX_SIZE):
                img.thumbnail((MAX_SIZE, MAX_SIZE), Image.LANCZOS)
            else:
                img.load()
        except OSError as e:
            self._invalid_file_exception_handle(e)
            raise NotOptimizableSourceException()
        ratio = 80
        if 'vector' in self._item_data['content']:
            self._quality = 100
            self._lossless = True
            self._lossless_encode(img)
            self._output_size = len(self._lossless_data)
        else:
            if self._lossless:
                self._lossless_encode(img)
            self._lossy_encode(img)
            if self._lossless and len(self._lossless_data) < len(self._lossy_data):
                self._lossless = True
                self._lossy_data = None
                self._output_size = len(self._lossless_data)
                self._quality = 100
            else:
                self._lossless_data = None
                self._lossless = False
                self._output_size = len(self._lossy_data)
                while ((self._output_size / self._get_source_size()) > ((100 - ratio) * 0.01)) and (self._quality >= 60):
                    self._quality -= 5
                    self._lossy_encode(img)
                    self._output_size = len(self._lossy_data)
                    ratio = math.ceil(ratio // 2)
        img.close()

    def _save_webp(self):
        if not self._animated:
            outfile = open(self._output_file + '.webp', 'wb')
            if self._lossless:
                outfile.write(self._lossless_data)
            else:
                outfile.write(self._lossy_data)
            outfile.close()


class PNGTranscode(WEBP_output):
    __metaclass__ = abc.ABCMeta

    def _apng_test_convert(self, img):
        if img.custom_mimetype == "image/apng":
            self._animated = True
            self._fext = 'webm'
            self.animation_encode()
            img.close()
            return None

    def __init__(self, source, path, file_name, item_data, pipe):
        BaseTranscoder.__init__(self, source, path, file_name, item_data, pipe)
        self._animated = False
        self._lossless = False
        self._lossless_data = b''
        self._lossy_data = b''

    def get_converter_type(self):
        return APNGconverter

    def _transparency_check(self, img: Image.Image) -> bool:
        alpha_histogram = img.histogram()[768:]
        if alpha_histogram[255] == img.width * img.height:
            return False
        else:
            sum = 0
            for value in alpha_histogram[:128]:
                sum += value
            if sum / (img.width * img.height) >= 0.05:
                return True
            else:
                return False

    def _encode(self):
        img = self._open_image()
        self._webp_encode(img)

    def _save(self):
        self._save_webp()


class JPEGTranscode(WEBP_output):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def _arithmetic_check(self):
        pass

    @abc.abstractmethod
    def _get_source_data(self):
        pass

    def _transparency_check(self, img: Image.Image) -> bool:
        return False

    def _apng_test_convert(self, img):
        pass

    def _all_optimisations_failed(self):
        pass

    def get_converter_type(self):
        return None

    def _encode(self):
        self._arithmetic_check()
        img = self._open_image()
        if (img.width>1024) or (img.height>1024):
            self._webp_output = True
            self._webp_encode(img)
        else:
            img.close()
            meta_copy = 'all'
            source_data = self._get_source_data()
            process = subprocess.Popen(['jpegtran', '-copy', meta_copy, '-arithmetic'],
                                       stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            process.stdin.write(source_data)
            process.stdin.close()
            self._optimized_data = process.stdout.read()
            process.stdout.close()
            process.terminate()
            self._output_size = len(self._optimized_data)

    def _save(self):
        if self._webp_output:
            self._save_webp()
        else:
            outfile = open(self._output_file + ".jpg", 'wb')
            outfile.write(self._optimized_data)
            outfile.close()


class GIFTranscode(WEBM_VideoOutputFormat):
    __metaclass__ = abc.ABCMeta

    def _encode(self):
        img = self._open_image()
        self._animated = img.is_animated
        if not self._animated:
            raise NotOptimizableSourceException()
        self._quality = 85
        animation2webm(self._source, self._output_file + '.webm')
        self._output_size = os.path.getsize(self._output_file + '.webm')

    def _save(self):
        pass

    @abc.abstractmethod
    def _all_optimisations_failed(self):
        pass

    def get_converter_type(self):
        return GIFconverter

    def _optimisations_failed(self):
        self.gif_optimisations_failed()


class PNGFileTranscode(FilePathSource, SourceRemovable, PNGTranscode):
    def __init__(self, source: str, path: str, file_name: str, item_data: dict, pipe):
        FilePathSource.__init__(self, source, path, file_name, item_data, pipe)
        PNGTranscode.__init__(self, source, path, file_name, item_data, pipe)

    def _invalid_file_exception_handle(self, e):
        print('invalid file ' + self._source + ' ({}) has been deleted'.format(e))
        os.remove(self._source)

    def _set_utime(self) -> None:
        os.utime(self._output_file + '.' + self._fext, (self._atime, self._mtime))

    def _optimisations_failed(self):
        if self._animated:
            self.gif_optimisations_failed()
        print("save " + self._source)
        os.remove(self._output_file + '.webp')

    def _all_optimisations_failed(self):
        print("save " + self._source)
        os.remove(self._output_file)


class JPEGFileTranscode(FilePathSource, UnremovableSource, JPEGTranscode):
    def __init__(self, source: str, path: str, file_name: str, item_data: dict, pipe):
        FilePathSource.__init__(self, source, path, file_name, item_data, pipe)
        self._quality = 100
        self._optimized_data = b''

    def _arithmetic_check(self):
        try:
            if is_arithmetic_jpg(self._source):
                raise AlreadyOptimizedSourceException()
        except OSError:
            raise NotOptimizableSourceException()

    def _get_source_data(self):
        source_file = open(self._source, 'br')
        raw_data = source_file.read()
        source_file.close()
        return raw_data

    def _set_utime(self) -> None:
        os.utime(self._source, (self._atime, self._mtime))

    def _optimisations_failed(self):
        pass

    def _invalid_file_exception_handle(self, e):
        print('invalid file ' + self._source + ' ({}) has been deleted'.format(e))
        os.remove(self._source)


class GIFFileTranscode(FilePathSource, SourceRemovable, GIFTranscode):

    def __init__(self, source: str, path: str, file_name: str, item_data: dict, pipe):
        FilePathSource.__init__(self, source, path, file_name, item_data, pipe)
        img = Image.open(source)
        self._animated = img.is_animated
        img.close()

    def _set_utime(self) -> None:
        os.utime(self._output_file+'.webm', (self._atime, self._mtime))

    def _all_optimisations_failed(self):
        print("save " + self._source)
        os.remove(self._output_file)


def get_file_transcoder(source: str, path: str, filename: str, data: dict, pipe=None):
    if os.path.splitext(source)[1].lower() == '.png':
        return PNGFileTranscode(source, path, filename, data, pipe)
    elif os.path.splitext(source)[1].lower() in {'.jpg', '.jpeg'}:
        return JPEGFileTranscode(source, path, filename, data, pipe)
    elif os.path.splitext(source)[1].lower() == '.gif':
        return GIFFileTranscode(source, path, filename, data, pipe)


PNG_HEADER = b'\x89PNG'
JPEG_HEADER = b'\xff\xd8'
GIF_HEADERS = {b'GIF87a', b'GIF89a'}


def isPNG(data: bytearray) -> bool:
    return data[:4] == PNG_HEADER


def isJPEG(data: bytearray) -> bool:
    return data[:2] == JPEG_HEADER


def isGIF(data: bytearray) -> bool:
    return bytes(data[:6]) in GIF_HEADERS


class PNGInMemoryTranscode(InMemorySource, PNGTranscode):

    def __init__(self, source:bytearray, path:str, file_name:str, item_data:dict, pipe):
        InMemorySource.__init__(self, source, path, file_name, item_data, pipe)
        PNGTranscode.__init__(self, source, path, file_name, item_data, pipe)

    def _invalid_file_exception_handle(self, e):
        print('invalid png data')

    def _optimisations_failed(self):
        if self._animated:
            self.gif_optimisations_failed()
        else:
            outfile = open(self._output_file + ".png", "bw")
            outfile.write(self._source)
            outfile.close()
            print("save " + self._output_file + ".png")

    def _all_optimisations_failed(self):
        self._animated = False
        self._optimisations_failed()


class JPEGInMemoryTranscode(InMemorySource, JPEGTranscode):
    def __init__(self, source:bytearray, path:str, file_name:str, item_data:dict, pipe):
        InMemorySource.__init__(self, source, path, file_name, item_data, pipe)
        self._quality = 100
        self._optimized_data = b''

    def _optimisations_failed(self):
        outfile = open(self._output_file + ".jpg", "bw")
        outfile.write(self._source)
        outfile.close()
        print("save " + self._output_file + ".jpg")

    def _arithmetic_check(self):
        pass

    def _get_source_data(self):
        return self._source

    def _invalid_file_exception_handle(self, e):
        print('invalid jpeg data')


class GIFInMemoryTranscode(InMemorySource, GIFTranscode):

    def __init__(self, source:bytearray, path:str, file_name:str, item_data:dict, pipe):
        InMemorySource.__init__(self, source, path, file_name, item_data, pipe)
        in_io = io.BytesIO(self._source)
        img = Image.open(in_io)
        self._animated = img.is_animated
        img.close()
        self._quality = 85

    def _all_optimisations_failed(self):
        outfile = open(self._output_file + ".gif", "bw")
        outfile.write(self._source)
        outfile.close()
        print("save " + self._output_file + ".gif")


def get_memory_transcoder(source: bytearray, path: str, filename: str, data: dict, pipe=None):
    global sumos
    global sumsize
    global avq
    global items
    if isPNG(source):
        return PNGInMemoryTranscode(source, path, filename, data, pipe)
    elif isJPEG(source):
        return JPEGInMemoryTranscode(source, path, filename, data, pipe)
    elif isGIF(source):
        return GIFInMemoryTranscode(source, path, filename, data, pipe)
    else:
        print(source[:16])
        exit()


def printStats():
    if items:
        print(('total save: {} MBytes ({}%) from {} total MBytes \n'
               'final size = {} MByte\n'
               'average quality={} of {} pictures'
               ).format(
            round((sumsize - sumos) / 1024 / 1024, 2),
            round((1 - sumos / sumsize) * 100, 2),
            round(sumsize / 1024 / 1024, 2),
            round(sumos / 1024 / 1024, 2),
            round(avq / items, 1),
            items
        ))
