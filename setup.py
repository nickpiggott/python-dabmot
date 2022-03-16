#!/usr/bin/env python

from distutils.core import setup

setup(name='dabmot',
      version='1.1',
      description='DAB MOT object assembly and decoding',
      author='Ben Poor',
      author_email='poor@ebu.ch',
      url='https://github.com/OpenDigitalRadio/python-dabmot',
      packages=['mot'],
      package_dir = {'' : 'src'},
      keywords = ['dab', 'mot', 'radio'],
      test_requires = ['unittest2'],
      tests = ['test']
     )
