import os
from distutils.core import setup

def _read(fn):
    path = os.path.join(os.path.dirname(__file__), fn)
    data = open(path).read()
    return data

setup(name='bluelet',
      version='0.2',
      description='pure-Python asynchronous I/O using coroutines',
      author='Adrian Sampson',
      author_email='adrian@radbox.org',
      url='https://github.com/sampsyo/bluelet',
      license='MIT',
      platforms='ALL',
      long_description=_read('README.rst'),

      py_modules=['bluelet'],

      classifiers=[
          'Topic :: Internet',
          'Topic :: System :: Networking',
          'Intended Audience :: Developers',
          'Programming Language :: Python :: 2',
          'Programming Language :: Python :: 3',
      ],
)
