#!/usr/bin/python3
# -*- coding: utf-8 -*-
import os, subprocess, math, apng, threading, time, json, sys
from PIL import Image

MAX_SIZE = 16383

def loading_thread(encoder, outbuf, i):
    outbuf[i] += encoder.communicate()[0]

sumos = 0
sumsize = 0
avq = 0
items = 0

getExt = {
    'png': 'webp',
    'jpg': 'jpg',
    'jpeg': 'jpg',
    'gif': 'png'
}

def transcode(source, path, filename, data):
    global sumos
    global sumsize
    global avq
    global items
    quality=95
    size = os.path.getsize(source)
    outf = os.path.join(path, filename)
    if os.path.splitext(source)[1].lower()=='.png':
        apngtest = apng.PNG.open(source)
        isAPNG=False
        for chunk in apngtest.chunks:
            if chunk.type=='acTL':
                isAPNG=True
        if isAPNG:
            return None
        img = Image.open(source)
        if img.mode in set(['1', 'P']):
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
        if (img.width>MAX_SIZE) | (img.height>MAX_SIZE):
            if img.width>img.height:
                tmpimg=img.resize(MAX_SIZE, int(round(MAX_SIZE/(img.width/float(img.height)), 0)))
            elif img.width<img.height:
                tmpimg=img.resize(int(round(MAX_SIZE*(img.width/float(img.height)), 0)), MAX_SIZE)
            else:
                tmpimg=img.resize(MAX_SIZE, MAX_SIZE)
            source='/tmp/'+filename+'.png'
            print("convert to {} ({}x{})".format(source, tmpimg.width, tmpimg.height))
            #logfile.write("convert to "+infile+' '+str(img.width)+'x'+str(img.height)+'\n')
            tmpimg.save(filename=source)
        img.close()
        ratio=80
        if lossless:
            lossless_encoder = subprocess.Popen(
                ['cwebp', '-lossless', '-quiet', source, '-o', '-'],
                stdout=subprocess.PIPE
            )
            lossy_encoder = subprocess.Popen(
                ['cwebp', '-q', str(quality), '-quiet', source, '-o', '-'],
                stdout=subprocess.PIPE
            )
            some_data = [b'', b'']
            lossless_loading_thread = threading.Thread(
                target = loading_thread,
                args = (lossless_encoder, some_data, 1)
            )
            lossy_loading_thread = threading.Thread(
                target = loading_thread,
                args = (lossy_encoder, some_data, 0)
            )
            lossy_loading_thread.start()
            lossless_loading_thread.start()
            lossy_loading_thread.join()
            if lossless_loading_thread.isAlive():
                lossless_loading_thread.join()
            lossy_data, lossless_data = some_data
            del some_data
        else:
            lossy_data = subprocess.check_output(
                ['cwebp', '-q', str(quality), '-quiet', source, '-o', '-']
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
                    ['cwebp', '-q', str(quality), '-quiet', source, '-o', '-']
                )
                outsize=len(lossydata)
                ratio=math.ceil(ratio//2)
    elif os.path.splitext(source)[1].lower() in set(['.jpg', '.jpeg']):
        quality=100
        img_metadata = json.loads(str(
            subprocess.check_output(['exiftool', '-j', source]
        ),'utf-8'))
        if 'arithmetic coding' in img_metadata[0]["EncodingProcess"]:
            return None
        if 'Make' in img_metadata[0] and 'Model' in img_metadata[0]:
            meta_copy = 'all'
        else:
            meta_copy = 'none'
        optimized_data = subprocess.check_output(
            ['jpegtran', '-copy', meta_copy, '-arithmetic', source])
        outsize=len(optimized_data)
    elif os.path.splitext(source)[1].lower()=='.gif':
        quality=100
        os.chdir(path)
        encoder = subprocess.Popen(
            ['gif2apng', os.path.basename(source),
                '{}.png'.format(filename)],
        )
        encoder.wait()
        outsize = os.path.getsize('{}.png'.format(filename))
    if (size > outsize) and ( outsize > 0 ):
        print(('save {} kbyte ({}%) quality = {}').format(
            round((size-outsize)/1024,2),
            round((1-outsize/size)*100,2),
            quality
        ))
        atime = os.path.getatime(source)
        mtime = os.path.getmtime(source)
        if os.path.splitext(source)[1].lower()=='.png':
            outfile=open(outf+'.webp', 'wb')
            if lossless:
                outfile.write(lossless_data)
            else:
                outfile.write(lossy_data)
            outfile.close()
            os.utime(outf+'.webp', (atime, mtime))
        elif os.path.splitext(source)[1].lower() in set(['.jpg', '.jpeg']):
            outfile=open(outf+'.jpg', 'wb')
            outfile.write(optimized_data)
            outfile.close()
            os.utime(outf+'.jpg', (atime, mtime))
        elif os.path.splitext(source)[1].lower()=='.gif':
            os.utime(outf+'.png', (atime, mtime))
        sumsize+=size
        sumos+=outsize
        avq+=quality
        items+=1
        os.remove(source)
    elif os.path.splitext(source)[1].lower() not in set(['.jpg', '.jpeg']):
        print("save "+source)
        if os.path.splitext(source)[1].lower()=='.png':
            os.remove(outf+'.webp')
        elif os.path.splitext(source)[1].lower()=='.gif':
            os.remove(outf+'.png')

def printStats():
    if items:
        print(('total save: {} MByte ({}%) average quality={} of {} pictures').format(
            round((sumsize-sumos)/1024/1024, 2),
            round((1-sumos/sumsize)*100,2),
            round(avq/items, 1),
            items
        ))