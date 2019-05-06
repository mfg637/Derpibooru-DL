#!/usr/bin/python3
# -*- coding: utf-8 -*-
import os, subprocess, math, apng, struct, io
from PIL import Image
import abc
import config

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
            '-pix_fmt', 'yuv420p',
            '-c:v', 'libvpx-vp9',
            '-crf', str(crf),
            '-b:v', '0',
            '-profile:v', '1',
            '-pix_fmt', 'yuv422p',
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
        return False
    elif os.path.splitext(source)[1].lower() == '.gif':
        return os.path.isfile(fname + '.webp') or os.path.isfile(fname+'.webm')


def transparency_check(img: Image.Image) -> bool:
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

    @abc.abstractmethod
    def _encode(self):
        pass

    @abc.abstractmethod
    def _save(self):
        pass

    def _record_timestamps(self):
        pass

    def _remove_temporal_file(self):
        pass

    @abc.abstractmethod
    def _remove_source(self):
        pass

    @abc.abstractmethod
    def _optimisationsFailed(self):
        pass

    def transcode(self):
        global sumsize
        global sumos
        global avq
        global items
        try:
            self._encode()
        except (
            AlreadyOptimizedSourceException,
            NotOptimizableSourceException
        ):
            pipe_send(self._pipe)
            return
        self._record_timestamps()
        self._remove_temporal_file()
        if (self._size > self._output_size) and (self._output_size > 0):
            self._save()
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
            self._optimisationsFailed()
        pipe_send(self._pipe)


class SourceRemovable(BaseTranscoder):
    def _remove_source(self):
        os.remove(self._source)


class UnremovableSource(BaseTranscoder):
    def _remove_source(self):
        pass


class FilePathSource(BaseTranscoder):
    def __init__(self, source:str, path:str, file_name:str, item_data:dict, pipe):
        BaseTranscoder.__init__(self, source, path, file_name, item_data, pipe)
        self._size = os.path.getsize(source)
        self._tmp_src = None

    def _record_timestamps(self):
        self._atime = os.path.getatime(self._source)
        self._mtime = os.path.getmtime(self._source)

    def _remove_temporal_file(self):
        if self._tmp_src is not None:
            os.remove(self._source)
            self._source = self._tmp_src


class InMemorySource(UnremovableSource):
    def __init__(self, source:bytearray, path:str, file_name:str, item_data:dict, pipe):
        BaseTranscoder.__init__(self, source, path, file_name, item_data, pipe)
        self._size = len(source)


class PNGFileTranscode(FilePathSource, SourceRemovable):
    def __init__(self, source: str, path: str, file_name: str, item_data: dict, pipe):
        FilePathSource.__init__(self, source, path, file_name, item_data, pipe)
        self._animated = False
        self._lossless = False
        self._lossless_data = b''
        self._lossy_data = b''

    def _encode(self):
        apngtest = apng.PNG.open(self._source)
        isAPNG = False
        for chunk in apngtest.chunks:
            if chunk.type == 'acTL':
                isAPNG = True
        if isAPNG:
            self._animated = True
            self._lossless = False
            self._quality = 85
            animation2webm(self._source, self._output_file + '.webm')
            self._output_size = os.path.getsize(self._output_file + '.webm')
        else:
            img = Image.open(self._source)
            if img.mode in {'1', 'P'}:
                raise NotOptimizableSourceException()
            if img.mode == 'RGBA':
                self._lossless = transparency_check(img)
            else:
                self._lossless = False
            try:
                if (img.width > MAX_SIZE) | (img.height > MAX_SIZE):
                    tmp_img = None
                    if img.width > img.height:
                        tmpimg = img.resize(
                            (MAX_SIZE, int(round(MAX_SIZE / (img.width / float(img.height)), 0))),
                            Image.LANCZOS
                        )
                    elif img.width < img.height:
                        tmpimg = img.resize(
                            (int(round(MAX_SIZE * (img.width / float(img.height)), 0)), MAX_SIZE),
                            Image.LANCZOS
                        )
                    else:
                        tmpimg = img.resize((MAX_SIZE, MAX_SIZE), Image.LANCZOS)
                    infile = '/tmp/' + self._file_name + '.png'
                    print("convert to {} ({}x{})".format(infile, tmpimg.width, tmpimg.height))
                    tmpimg.save(infile)
                    self._tmp_src = self._source
                    self._source = infile
                else:
                    img.load()
            except OSError as e:
                print('invalid file ' + self._source + ' ({}) has been deleted'.format(e))
                os.remove(self._source)
                raise NotOptimizableSourceException()
            img.close()
            ratio = 80
            if 'vector' in self._item_data['art_type']:
                self._quality = 100
                self._lossless = True
                self._lossless_data = subprocess.check_output(
                    ['cwebp', '-m', '6', '-lossless', '-quiet', self._source, '-o', '-']
                )
                self._output_size = len(self._lossless_data)
            else:
                if self._lossless:
                    self._lossless_data = subprocess.check_output(
                        ['cwebp', '-m', '6', '-lossless', '-quiet', self._source, '-o', '-']
                    )
                self._lossy_data = subprocess.check_output(
                    ['cwebp', '-m', '6', '-q', str(self._quality), '-quiet', self._source, '-o', '-']
                )
                self._output_size = len(self._lossy_data)
                if self._lossless and len(self._lossless_data) < self._output_size:
                    self._lossless = True
                    self._output_size = len(self._lossless_data)
                    self._quality = 100
                    self._lossy_data = None
                else:
                    self._lossless_data = None
                    self._lossless = False
                    while ((self._output_size / self._size) > ((100 - ratio) * 0.01)) and (self._quality >= 60):
                        self._quality -= 5
                        self._lossy_data = subprocess.check_output(
                            ['cwebp', '-m', '6', '-q', str(self._quality), '-quiet', self._source, '-o', '-']
                        )
                        self._outsize = len(self._lossy_data)
                        ratio = math.ceil(ratio // 2)

    def _save(self):
        if not self._animated:
            outfile = open(self._output_file + '.webp', 'wb')
            if self._lossless:
                outfile.write(self._lossless_data)
            else:
                outfile.write(self._lossy_data)
            outfile.close()
            os.utime(self._output_file + '.webp', (self._atime, self._mtime))
        else:
            os.utime(self._output_file + '.webp', (self._atime, self._mtime))

    def _optimisationsFailed(self):
        global sumsize
        global sumos
        global avq
        global items
        if self._animated:
            os.remove(self._output_file + '.webm')
            converter = APNGconverter(self._source)
            out_data = converter.compress(lossless=True)
            self._output_size = len(out_data)
            if self._output_size >= self._size:
                print("save " + self._source)
                os.remove(self._output_file)
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
                os.utime(self._output_file, (self._atime, self._mtime))
                os.remove(self._source)
                sumsize += self._size
                sumos += self._output_size
                avq += self._quality
                items += 1
            converter.close()
        else:
            print("save " + self._source)
            os.remove(self._output_file + '.webp')


class JPEGFileTranscode(FilePathSource, UnremovableSource):
    def __init__(self, source: str, path: str, file_name: str, item_data: dict, pipe):
        FilePathSource.__init__(self, source, path, file_name, item_data, pipe)
        self._quality = 100
        self._optimized_data = b''

    def _encode(self):
        try:
            if is_arithmetic_jpg(self._source):
                raise AlreadyOptimizedSourceException()
        except OSError:
            raise NotOptimizableSourceException()
        meta_copy = 'all'
        source_file = open(self._source, 'br')
        raw_data = source_file.read()
        source_file.close()
        process = subprocess.Popen(['jpegtran', '-copy', meta_copy, '-arithmetic'],
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        process.stdin.write(raw_data)
        process.stdin.close()
        self._optimized_data = process.stdout.read()
        process.stdout.close()
        process.terminate()
        self._output_size = len(self._optimized_data)

    def _save(self):
        outfile = open(self._source, 'wb')
        outfile.write(self._optimized_data)
        outfile.close()
        os.utime(self._source, (self._atime, self._mtime))

    def _optimisationsFailed(self):
        pass


class GIFFileTranscode(FilePathSource, SourceRemovable):
    def __init__(self, source: str, path: str, file_name: str, item_data: dict, pipe):
        FilePathSource.__init__(self, source, path, file_name, item_data, pipe)
        img = Image.open(source)
        self._animated = img.is_animated
        img.close()

    def _encode(self):
        if not self._animated:
            raise NotOptimizableSourceException()
        self._quality = 85
        animation2webm(self._source, self._output_file + '.webm')
        self._output_size = os.path.getsize(self._output_file + '.webm')

    def _save(self):
        os.utime(self._output_file+'.webm', (self._atime, self._mtime))

    def _optimisationsFailed(self):
        global sumsize
        global sumos
        global avq
        global items
        os.remove(self._output_file + '.webm')
        converter = GIFconverter(self._source)
        out_data = converter.compress(lossless=True)
        self._output_size = len(out_data)
        if self._output_size >= self._size:
            print("save " + self._source)
            os.remove(self._output_file)
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
            os.utime(self._output_file, (self._atime, self._mtime))
            os.remove(self._source)
            sumsize += self._size
            sumos += self._output_size
            avq += self._quality
            items += 1
        converter.close()


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


class PNGInMemoryTranscode(InMemorySource):
    def __init__(self, source:bytearray, path:str, file_name:str, item_data:dict, pipe):
        InMemorySource.__init__(self, source, path, file_name, item_data, pipe)
        self._lossless = False
        self._lossless_data = b''
        self._lossy_data = b''

    def _encode(self):
        src_io = io.BytesIO(self._source)
        img = Image.open(src_io)
        if img.mode in {'1', 'P'}:
            raise NotOptimizableSourceException()
        if img.mode == 'RGBA':
            self._lossless = transparency_check(img)
        else:
            self._lossless = False
        try:
            if (img.width > MAX_SIZE) | (img.height > MAX_SIZE):
                img.thumbnail((MAX_SIZE, MAX_SIZE), Image.LANCZOS)
            else:
                img.load()
        except OSError as e:
            print('invalid png data')
            raise NotOptimizableSourceException()
        ratio = 80
        self._lossless_data = None
        self._lossy_data = None
        if 'vector' in self._item_data['art_type']:
            self._quality = 100
            self._lossless = True
            lossless_out_io = io.BytesIO()
            img.save(lossless_out_io, format="WEBP", lossless=True, quality=100, method=6)
            self._lossless_data = lossless_out_io.getbuffer()
            self._output_size = len(self._lossless_data)
        else:
            lossy_out_io = io.BytesIO()
            if self._lossless:
                lossless_out_io = io.BytesIO()
                img.save(lossless_out_io, format="WEBP", lossless=True, quality=100, method=6)
                self._lossless_data = lossless_out_io.getbuffer()
            img.save(lossy_out_io, format="WEBP", lossless=False, quality=self._quality, method=6)
            self._lossy_data = lossy_out_io.getbuffer()
            if self._lossless and len(self._lossless_data) < len(self._lossy_data):
                self._lossless = True
                self._lossy_data = None
                self._output_size = len(self._lossless_data)
                self._quality = 100
            else:
                self._lossless_data = None
                self._lossless = False
                self._output_size = len(self._lossy_data)
                while ((self._output_size / self._size) > ((100 - ratio) * 0.01)) and (self._quality >= 60):
                    self._quality -= 5
                    lossy_out_io = io.BytesIO()
                    img.save(lossy_out_io, format="WEBP", lossless=False, quality=self._quality, method=6)
                    self._lossy_data = lossy_out_io.getbuffer()
                    self._output_size = len(self._lossy_data)
                    ratio = math.ceil(ratio // 2)
        img.close()

    def _save(self):
        outfile = open(self._output_file + '.webp', 'wb')
        if self._lossless:
            outfile.write(self._lossless_data)
        else:
            outfile.write(self._lossy_data)
        outfile.close()

    def _optimisationsFailed(self):
        outfile = open(self._output_size + ".png", "bw")
        outfile.write(self._source)
        outfile.close()
        print("save " + self._output_file + ".png")


class JPEGInMemoryTranscode(InMemorySource):

    def __init__(self, source:bytearray, path:str, file_name:str, item_data:dict, pipe):
        InMemorySource.__init__(self, source, path, file_name, item_data, pipe)
        self._quality = 100
        self._optimized_data = b''

    def _encode(self):
        process = subprocess.Popen(['jpegtran', '-arithmetic'],
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        process.stdin.write(self._source)
        process.stdin.close()
        self._optimized_data = process.stdout.read()
        process.stdout.close()
        process.terminate()
        self._output_size = len(self._optimized_data)

    def _save(self):
        outfile = open(self._output_file + ".jpg", 'wb')
        outfile.write(self._optimized_data)
        outfile.close()

    def _optimisationsFailed(self):
        outfile = open(self._output_file + ".jpg", "bw")
        outfile.write(self._source)
        outfile.close()
        print("save " + self._output_file + ".jpg")


class GIFInMemoryTranscode(InMemorySource):

    def __init__(self, source:bytearray, path:str, file_name:str, item_data:dict, pipe):
        InMemorySource.__init__(self, source, path, file_name, item_data, pipe)
        in_io = io.BytesIO(self._source)
        img = Image.open(in_io)
        self._animated = img.is_animated
        img.close()
        self._quality = 85

    def _encode(self):
        if not self._animated:
            raise NotOptimizableSourceException()
        animation2webm(self._source, self._output_file + '.webm')
        self._output_size = os.path.getsize(self._output_file + '.webm')

    def _save(self):
        pass

    def _optimisationsFailed(self):
        global sumsize
        global sumos
        global avq
        global items
        converter = GIFconverter(self._source)
        out_data = converter.compress(lossless=True)
        self._output_size = len(out_data)
        if self._output_size >= self._size:
            outfile = open(self._output_file + ".gif", "bw")
            outfile.write(self._source)
            outfile.close()
            print("save " + self._output_file + ".gif")
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
            sumsize += self._size
            sumos += self._output_size
            avq += self._quality
            items += 1
        converter.close()


def get_memory_transcoder(source: bytearray, path: str, filename: str, data: dict, pipe=None):
    global sumos
    global sumsize
    global avq
    global items
    quality = 95
    tmp_src = None
    size = len(source)
    outf = os.path.join(path, filename)
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
