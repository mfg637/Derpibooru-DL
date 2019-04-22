#!/usr/bin/python3
# -*- coding: utf-8 -*-
import os, subprocess, math, apng, struct
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

    def compress(self, quality: int = 90, fast: bool = True, lossless: bool = False) -> str:
        print('try to convert, quality={}, f={}'.format(quality, fast))
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
                os.path.splitext(self._path)[0]+'.webp',
                'WEBP',
                save_all=True,
                append_images=self._images[1:],
                **kwargs
            )
        else:
            self._images[0].save(
                os.path.splitext(self._path)[0]+'.webp',
                'WEBP',
                **kwargs
            )
        return os.path.splitext(self._path)[0]+'.webp'

class ImagemagickConverterBug(Exception):
    pass

class GIFconverter(Converter):
    def __init__(self, gif_path):
        self._path = gif_path
        img = Image.open(gif_path)
        if 'duration' in img.info:
            self._duration = img.info['duration']
        else:
            self._duration = 0
        if 'loop' in img.info:
            self._loop = img.info['loop']
        else:
            self._loop = 1
        img.close()
        commandline = ['convert', '-coalesce', gif_path, 'frame%05d.png']
        subprocess.run(commandline)
        self._images = []
        i=0
        while os.path.isfile('frame'+(str(i).zfill(5))+'.png'):
            self._images.append(Image.open('frame'+(str(i).zfill(5))+'.png'))
            i += 1
        if len(self._images)==0:
            raise ImagemagickConverterBug()
    def close(self):
        for frame in self._images:
            frame.close()
        i=0
        while os.path.isfile('frame'+(str(i).zfill(5))+'.png'):
            os.remove('frame'+(str(i).zfill(5))+'.png')
            i += 1

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
                outf=converter.compress(quality)
                outsize = os.path.getsize(outf)
                while (( (outsize/size) > ((100-ratio)*0.01) ) or ( outsize>size )) and quality>60:
                    quality -= 5
                    converter.compress(quality)
                    outsize = os.path.getsize(outf)
                    ratio=math.ceil(ratio//2)
        else:
            img = Image.open(source)
            if img.mode in set(['1', 'P']):
                pipe_send(pipe)
                return None
            if img.mode=='RGBA':
                alpha_histogram = img.histogram()[768:]
                if alpha_histogram[255]==img.width*img.height:
                    lossless=False
                else:
                    sumpixels=0
                    for value in alpha_histogram[:128]:
                        sumpixels+=value
                    if sumpixels/(img.width*img.height)>=0.05:
                        lossless=True
                    else:
                        lossless=False
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
    elif os.path.splitext(source)[1].lower() in set(['.jpg', '.jpeg']):
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
        try:
            converter = GIFconverter(source)
        except ImagemagickConverterBug:
            pipe_send(pipe)
            return None
        outf=converter.compress(quality)
        outsize = os.path.getsize(outf)
        while (( (outsize/size) > ((100-ratio)*0.01) ) or ( outsize>size )) and quality>60:
            quality -= 5
            converter.compress(quality)
            outsize = os.path.getsize(outf)
            ratio=math.ceil(ratio//2)
    atime = os.path.getatime(source)
    mtime = os.path.getmtime(source)
    if tmp_src is not None:
        os.remove(source)
        source = tmp_src
    if (size > outsize) and ( outsize > 0 ):
        if os.path.splitext(source)[1].lower()=='.png':
            if not animated:
                outfile=open(outf+'.webp', 'wb')
                if lossless:
                    outfile.write(lossless_data)
                else:
                    outfile.write(lossy_data)
                outfile.close()
                os.utime(outf+'.webp', (atime, mtime))
            else:
                converter.compress(quality, fast=False)
                converter.close()
                outsize = os.path.getsize(outf)
                os.utime(outf, (atime, mtime))
        elif os.path.splitext(source)[1].lower() in set(['.jpg', '.jpeg']):
            outfile=open(source, 'wb')
            outfile.write(optimized_data)
            outfile.close()
            os.utime(source, (atime, mtime))
        elif os.path.splitext(source)[1].lower()=='.gif':
            outf=converter.compress(quality, fast=False)
            converter.close()
            outsize = os.path.getsize(outf)
            os.utime(outf, (atime, mtime))
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
            elif os.path.splitext(source)[1].lower()=='.gif':
                print("save "+source)
                os.remove(outf)
            elif animated:
                converter.compress(lossless=True)
                outsize = os.path.getsize(outf)
                if outsize>=size:
                    print("save "+source)
                    os.remove(outf)
                else:
                    converter.compress(lossless=True, fast=False)
                    os.utime(outf, (atime, mtime))
                    os.remove(source)
                converter.close()
        except FileNotFoundError as e:
            pipe_send(pipe)
            return None
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