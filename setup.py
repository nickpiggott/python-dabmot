#!/usr/bin/env python

from setuptools import setup, find_packages

setup(name='dabmot',
      version = '1.2',
      description = 'DAB MOT object assembly and decoding',
      author = 'Ben Poor',
      author_email = 'poor@ebu.ch',
      url ='https://github.com/OpenDigitalRadio/python-dabmot',
      packages = find_packages(),
      package_dir = {'' : 'src'},
      keywords = ['dab', 'mot', 'radio'],
      test_suite = "mot.test",
      install_requires = ['bitarray', 'unittest2', 'python-dateutil', 'julian']
     )
