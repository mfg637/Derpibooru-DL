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
    __metaclass__=abc.ABCMeta
    @abc.abstractclassmethod
    def __init__(self, path):
        self._path=""
        self._images=[]
        self._loop = 0
        self._duration=[]

    @abc.abstractclassmethod
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
                'method':3,
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
        if len(self._images)>1:
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
        #self._path = gif_path
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
            commandline = [ 'ffmpeg',
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
            commandline = [ 'ffmpeg',
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
        while not os.path.isfile('apngframe'+test_zeroes+str(i)+'.png'):
            zeroes_count+=1
            test_zeroes += '0'
        file_name = 'apngframe'
        file_name += str(i).zfill(zeroes_count+1)

        while os.path.isfile(file_name+'.png'):
            try:
                info_file = open(file_name+'.txt')
            except FileNotFoundError:
                break
            info_file.seek(6)
            self._duration.append(int(round(eval(info_file.read())*1000)))
            info_file.close()
            self._fname.append(file_name+'.png')
            self._images.append(Image.open(file_name+'.png'))
            os.remove(file_name+'.txt')
            file_name = 'apngframe'
            i += 1
            file_name += str(i).zfill(zeroes_count+1)
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
            file.seek(frame_len-2, 1)
    file.close()
    return None


def check_exists(source, path, filename):
    if os.path.splitext(source)[1].lower() == '.png':
        return os.path.isfile(os.path.join(path, filename) + '.webp')
    elif os.path.splitext(source)[1].lower() in {'.jpg', '.jpeg'}:
        return False
    elif os.path.splitext(source)[1].lower()=='.gif':
        return os.path.isfile(os.path.splitext(source)[0]+'.webp')


def transparency_check(img:Image.Image) -> bool:
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


def transcode(source, path, filename, data, pipe):
    global sumos
    global sumsize
    global avq
    global items
    quality=95
    tmp_src = None
    size = os.path.getsize(source)
    outf = os.path.join(path, filename)
    if os.path.splitext(source)[1].lower()=='.png':
        animated = False
        lossless = False
        lossless_data = b''
        apngtest = apng.PNG.open(source)
        isAPNG=False
        for chunk in apngtest.chunks:
            if chunk.type=='acTL':
                isAPNG=True
        if isAPNG:
                animated = True
                lossless = False
                ratio=50
                converter = APNGconverter(source)
                lossy_data = converter.compress(quality)
                outsize = len(lossy_data)
                while (( (outsize/size) > ((100-ratio)*0.01) ) or ( outsize>size )) and quality>60:
                    quality -= 5
                    lossy_data = converter.compress(quality)
                    outsize = len(lossy_data)
                    ratio=math.ceil(ratio//2)
        else:
            img = Image.open(source)
            if img.mode in {'1', 'P'}:
                pipe_send(pipe)
                return None
            if img.mode=='RGBA':
                lossless = transparency_check(img)
            else:
                lossless=False
            try:
                if (img.width>MAX_SIZE) | (img.height>MAX_SIZE):
                    if img.width>img.height:
                        tmpimg=img.resize(
                            (MAX_SIZE, int(round(MAX_SIZE/(img.width/float(img.height)), 0))),
                            Image.LANCZOS
                        )
                    elif img.width<img.height:
                        tmpimg=img.resize(
                            (int(round(MAX_SIZE*(img.width/float(img.height)), 0)), MAX_SIZE),
                            Image.LANCZOS
                        )
                    else:
                        tmpimg=img.resize((MAX_SIZE, MAX_SIZE), Image.LANCZOS)
                    infile='/tmp/'+filename+'.png'
                    print("convert to {} ({}x{})".format(infile, tmpimg.width, tmpimg.height))
                    tmpimg.save(infile)
                    tmp_src = source
                    source = infile
                else:
                    img.load()
            except OSError as e:
                print('invalid file '+source+' ({})'.format(e))
                os.remove(source)
                pipe_send(pipe)
                return
            img.close()
            ratio=80
            if 'vector' in data['art_type']:
                quality = 100
                lossless = True
                lossless_data = subprocess.check_output(
                    ['cwebp', '-m', '6', '-lossless', '-quiet', source, '-o', '-']
                )
                outsize = len(lossless_data)
            else:
                if lossless:
                    lossless_data = subprocess.check_output(
                        ['cwebp', '-m', '6', '-lossless', '-quiet', source, '-o', '-']
                    )
                lossy_data = subprocess.check_output(
                    ['cwebp', '-m', '6', '-q', str(quality), '-quiet', source, '-o', '-']
                )
                outsize = len(lossy_data)
                if lossless and len(lossless_data)<outsize:
                    lossless=True
                    outsize = len(lossless_data)
                    quality=100
                    lossy_data = None
                else:
                    lossless_data = None
                    lossless=False
                    while ( (outsize/size) > ((100-ratio)*0.01) ) and ( quality >=60 ):
                        quality -= 5
                        lossydata = subprocess.check_output(
                            ['cwebp', '-m', '6', '-q', str(quality), '-quiet', source, '-o', '-']
                        )
                        outsize=len(lossydata)
                        ratio=math.ceil(ratio//2)
    elif os.path.splitext(source)[1].lower() in {'.jpg', '.jpeg'}:
        quality=100
        try:
            if is_arithmetic_jpg(source):
                pipe_send(pipe)
                return None
        except OSError:
            pipe_send(pipe)
            return None
        meta_copy = 'all'
        source_file = open(source, 'br')
        raw_data = source_file.read()
        source_file.close()
        process = subprocess.Popen(['jpegtran', '-copy', meta_copy, '-arithmetic'],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        process.stdin.write(raw_data)
        process.stdin.close()
        raw_data = None
        optimized_data = process.stdout.read()
        process.stdout.close()
        process.terminate()
        outsize=len(optimized_data)
    elif os.path.splitext(source)[1].lower()=='.gif':
        quality=95
        animated = True
        ratio=50
        converter = GIFconverter(source)
        out_data = converter.compress(quality)
        outsize = len(out_data)
        while (( (outsize/size) > ((100-ratio)*0.01) ) or ( outsize>size )) and quality>60:
            quality -= 5
            out_data = converter.compress(quality)
            outsize = len(out_data)
            ratio=math.ceil(ratio//2)
    atime = os.path.getatime(source)
    mtime = os.path.getmtime(source)
    if tmp_src is not None:
        os.remove(source)
        source = tmp_src
    if (size > outsize) and ( outsize > 0 ):
        if os.path.splitext(source)[1].lower()=='.png':
            if animated:
                lossy_data = converter.compress(quality, fast=False)
                converter.close()
                outsize = len(lossy_data)
            outfile = open(outf + '.webp', 'wb')
            if lossless:
                outfile.write(lossless_data)
            else:
                outfile.write(lossy_data)
            outfile.close()
            os.utime(outf + '.webp', (atime, mtime))
        elif os.path.splitext(source)[1].lower() in {'.jpg', '.jpeg'}:
            outfile=open(source, 'wb')
            outfile.write(optimized_data)
            outfile.close()
            os.utime(source, (atime, mtime))
        elif os.path.splitext(source)[1].lower()=='.gif':
            out_data = converter.compress(quality, fast=False)
            converter.close()
            outsize = len(out_data)
            outfile = open(outf + '.webp', 'wb')
            outfile.write(out_data)
            outfile.close()
            os.utime(outf + '.webp', (atime, mtime))
        print(('save {} kbyte ({}%) quality = {}').format(
            round((size-outsize)/1024,2),
            round((1-outsize/size)*100,2),
            quality
        ))
        sumsize+=size
        sumos+=outsize
        avq+=quality
        items+=1
        if os.path.splitext(source)[1].lower() not in set(['.jpg', '.jpeg']):
            os.remove(source)
    elif os.path.splitext(source)[1].lower() not in set(['.jpg', '.jpeg']):
        try:
            if os.path.splitext(source)[1].lower()=='.png' and not animated:
                print("save "+source)
                os.remove(outf+'.webp')
            elif animated:
                out_data = converter.compress(lossless=True)
                outsize = len(out_data)
                if outsize>=size:
                    print("save "+source)
                    os.remove(outf)
                else:
                    out_data = converter.compress(lossless=True, fast=False)
                    outsize = len(out_data)
                    outfile = open(outf + '.webp', 'wb')
                    outfile.write(out_data)
                    outfile.close()
                    print(('save {} kbyte ({}%) quality = {}').format(
                        round((size - outsize) / 1024, 2),
                        round((1 - outsize / size) * 100, 2),
                        quality
                    ))
                    os.utime(outf, (atime, mtime))
                    os.remove(source)
                converter.close()
        except FileNotFoundError as e:
            pipe_send(pipe)
            return None
    pipe_send(pipe)


PNG_HEADER = b'\x89PNG'
JPEG_HEADER = b'\xff\xd8'
GIF_HEADERS = {b'GIF87a', b'GIF89a'}


def isPNG(data:bytearray) -> bool:
    return data[:4] == PNG_HEADER


def isJPEG(data:bytearray) -> bool:
    return data[:2] == JPEG_HEADER


def isGIF(data:bytearray) -> bool:
    return bytes(data[:6]) in GIF_HEADERS


def inMemoryTranscode(source:bytearray, path:str, filename:str, data:dict, pipe = None):
    global sumos
    global sumsize
    global avq
    global items
    quality=95
    tmp_src = None
    size = len(source)
    outf = os.path.join(path, filename)
    if isPNG(source):
        animated = False
        src_io = io.BytesIO(source)
        img = Image.open(src_io)
        if img.mode in {'1', 'P'}:
            pipe_send(pipe)
            return None
        if img.mode == 'RGBA':
            lossless = transparency_check(img)
        else:
            lossless = False
        try:
            if (img.width > MAX_SIZE) | (img.height > MAX_SIZE):
                img.thumbnail((MAX_SIZE, MAX_SIZE), Image.LANCZOS)
            else:
                img.load()
        except OSError as e:
            print('invalid png data')
            pipe_send(pipe)
            return
        ratio = 80
        lossless_data = None
        lossy_data = None
        if 'vector' in data['art_type']:
            quality = 100
            lossless = True
            lossless_out_io = io.BytesIO()
            img.save(lossless_out_io, format="WEBP", lossless = True, quality = 100, method=6)
            lossless_data = lossless_out_io.getbuffer()
            outsize = len(lossless_data)
        else:
            lossy_out_io = io.BytesIO()
            if lossless:
                lossless_out_io = io.BytesIO()
                img.save(lossless_out_io, format="WEBP", lossless=True, quality=100, method=6)
                lossless_data = lossless_out_io.getbuffer()
            img.save(lossy_out_io, format="WEBP", lossless=False, quality=quality, method=6)
            lossy_data = lossy_out_io.getbuffer()
            if lossless and len(lossless_data) < len(lossy_data):
                lossless = True
                lossy_data = None
                outsize = len(lossless_data)
                quality = 100
            else:
                lossless_data = None
                lossless = False
                outsize = len(lossy_data)
                while ((outsize / size) > ((100 - ratio) * 0.01)) and (quality >= 60):
                    quality -= 5
                    lossy_out_io = io.BytesIO()
                    img.save(lossy_out_io, format="WEBP", lossless=False, quality=quality, method=6)
                    lossy_data = lossy_out_io.getbuffer()
                    outsize = len(lossy_data)
                    ratio = math.ceil(ratio // 2)
        img.close()
    elif isJPEG(source):
        quality=100
        process = subprocess.Popen(['jpegtran', '-arithmetic'],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        process.stdin.write(source)
        process.stdin.close()
        optimized_data = process.stdout.read()
        process.stdout.close()
        process.terminate()
        outsize=len(optimized_data)
    elif isGIF(source):
        quality=95
        animated = True
        ratio=50
        converter = GIFconverter(source)
        out_data = converter.compress(quality)
        outsize = len(out_data)
        while (( (outsize/size) > ((100-ratio)*0.01) ) or ( outsize>size )) and quality>60:
            quality -= 5
            out_data = converter.compress(quality)
            outsize = len(out_data)
            ratio=math.ceil(ratio//2)
    else:
        print(source[:16])
        exit()
    if (size > outsize) and ( outsize > 0 ):
        if isPNG(source):
            outfile = open(outf + '.webp', 'wb')
            if lossless:
                outfile.write(lossless_data.tobytes())
            else:
                outfile.write(lossy_data.tobytes())
            outfile.close()
        elif isJPEG(source):
            outfile=open(outf+".jpg", 'wb')
            outfile.write(optimized_data)
            outfile.close()
        elif isGIF(source):
            out_data = converter.compress(quality, fast=False)
            converter.close()
            outsize = len(out_data)
            outfile = open(outf + '.webp', 'wb')
            outfile.write(out_data.tobytes())
            outfile.close()
        print(('save {} kbyte ({}%) quality = {}').format(
            round((size-outsize)/1024,2),
            round((1-outsize/size)*100,2),
            quality
        ))
        sumsize+=size
        sumos+=outsize
        avq+=quality
        items+=1
    elif not isJPEG(source):
        if isPNG(source) and not animated:
            outfile = open(outf+".png", "bw")
            outfile.write(source)
            outfile.close()
            print("save " + outf + ".png")
        elif animated:
            out_data = converter.compress(lossless=True)
            outsize = len(out_data)
            if outsize >= size:
                if isGIF(source):
                    outfile = open(outf + ".gif", "bw")
                    outfile.write(source)
                    outfile.close()
                    print("save " + outf + ".gif")
                elif isPNG(source):
                    outfile = open(outf + ".png", "bw")
                    outfile.write(source)
                    outfile.close()
                    print("save " + outf + ".png")
            else:
                out_data = converter.compress(lossless=True, fast=False)
                outsize = len(out_data)
                outfile = open(outf + '.webp', 'wb')
                outfile.write(out_data)
                outfile.close()
                print(('save {} kbyte ({}%) quality = {}').format(
                    round((size - outsize) / 1024, 2),
                    round((1 - outsize / size) * 100, 2),
                    quality
                ))
                sumsize += size
                sumos += outsize
                avq += quality
                items += 1
            converter.close()
    elif isJPEG(source):
        outfile = open(outf + ".jpg", "bw")
        outfile.write(source)
        outfile.close()
        print("save " + outf + ".jpg")
    pipe_send(pipe)


def printStats():
    if items:
        print(('total save: {} MBytes ({}%) from {} total MBytes \n'
                'final size = {} MByte\n'
                'average quality={} of {} pictures'
                ).format(
            round((sumsize-sumos)/1024/1024, 2),
            round((1-sumos/sumsize)*100,2),
            round(sumsize/1024/1024, 2),
            round(sumos/1024/1024, 2),
            round(avq/items, 1),
            items
        ))