#!/usr/bin/env python
import os
import subprocess
import time
from setuptools import find_packages, setup

import torch
from torch.utils.cpp_extension import (BuildExtension, CppExtension,
                                       CUDAExtension)


def readme():
    with open('README.md', encoding='utf-8') as f:
        content = f.read()
    return content


version_file = 'mmdet/version.py'


def get_git_hash():

    def _minimal_ext_cmd(cmd):
        # construct minimal environment
        env = {}
        for k in ['SYSTEMROOT', 'PATH', 'HOME']:
            v = os.environ.get(k)
            if v is not None:
                env[k] = v
        # LANGUAGE is used on win32
        env['LANGUAGE'] = 'C'
        env['LANG'] = 'C'
        env['LC_ALL'] = 'C'
        out = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, env=env).communicate()[0]
        return out

    try:
        out = _minimal_ext_cmd(['git', 'rev-parse', 'HEAD'])
        sha = out.strip().decode('ascii')
    except OSError:
        sha = 'unknown'

    return sha


def get_hash():
    if os.path.exists('.git'):
        sha = get_git_hash()[:7]
    elif os.path.exists(version_file):
        try:
            from mmdet.version import __version__
            sha = __version__.split('+')[-1]
        except ImportError:
            raise ImportError('Unable to get git version')
    else:
        sha = 'unknown'

    return sha


def write_version_py():
    content = """# GENERATED VERSION FILE
# TIME: {}

__version__ = '{}'
short_version = '{}'
version_info = ({})
"""
    sha = get_hash()
    with open('mmdet/VERSION', 'r') as f:
        SHORT_VERSION = f.read().strip()
    VERSION_INFO = ', '.join(SHORT_VERSION.split('.'))
    VERSION = SHORT_VERSION + '+' + sha

    version_file_str = content.format(time.asctime(), VERSION, SHORT_VERSION,
                                      VERSION_INFO)
    with open(version_file, 'w') as f:
        f.write(version_file_str)


def get_version():
    with open(version_file, 'r') as f:
        exec(compile(f.read(), version_file, 'exec'))
    return locals()['__version__']


def make_cuda_ext(name, module, sources, sources_cuda=[]):

    define_macros = []
    extra_compile_args = {
        'cxx': ['-std=c++14'],
        'nvcc': [
            '-D__CUDA_NO_HALF_OPERATORS__',
            '-D__CUDA_NO_HALF_CONVERSIONS__',
            '-D__CUDA_NO_HALF2_OPERATORS__',
            '-std=c++14',
            '-Xcompiler=-fPIC',
            '-gencode=arch=compute_89,code=sm_89',
            '-gencode=arch=compute_80,code=sm_80',
            '-gencode=arch=compute_86,code=sm_86',
            '-gencode=arch=compute_70,code=compute_70'
        ]
    }

    if torch.cuda.is_available() or os.getenv('FORCE_CUDA', '0') == '1':
        define_macros += [('WITH_CUDA', None)]
        extension = CUDAExtension
        extra_compile_args['nvcc'] = [
            '-D__CUDA_NO_HALF_OPERATORS__',
            '-D__CUDA_NO_HALF_CONVERSIONS__',
            '-D__CUDA_NO_HALF2_OPERATORS__',
        ]
        sources += sources_cuda
    else:
        print(f'Compiling {name} without CUDA')
        extension = CppExtension
        # raise EnvironmentError('CUDA is required to compile MMDetection!')

    return extension(
        name=f'{module}.{name}',
        sources=[os.path.join(*module.split('.'), p) for p in sources],
        define_macros=define_macros,
        extra_compile_args=extra_compile_args)


def parse_requirements(fname='requirements.txt', with_version=True):
    """
    Parse the package dependencies listed in a requirements file but strips
    specific versioning information.

    Args:
        fname (str): path to requirements file
        with_version (bool, default=False): if True include version specs

    Returns:
        List[str]: list of requirements items

    CommandLine:
        python -c "import setup; print(setup.parse_requirements())"
    """
    import sys
    from os.path import exists
    import re
    require_fpath = fname

    def parse_line(line):
        """
        Parse information from a line in a requirements text file
        """
        if line.startswith('-r '):
            # Allow specifying requirements in other files
            target = line.split(' ')[1]
            for info in parse_require_file(target):
                yield info
        else:
            info = {'line': line}
            if line.startswith('-e '):
                info['package'] = line.split('#egg=')[1]
            else:
                # Remove versioning from the package
                pat = '(' + '|'.join(['>=', '==', '>']) + ')'
                parts = re.split(pat, line, maxsplit=1)
                parts = [p.strip() for p in parts]

                info['package'] = parts[0]
                if len(parts) > 1:
                    op, rest = parts[1:]
                    if ';' in rest:
                        # Handle platform specific dependencies
                        # http://setuptools.readthedocs.io/en/latest/setuptools.html#declaring-platform-specific-dependencies
                        version, platform_deps = map(str.strip,
                                                     rest.split(';'))
                        info['platform_deps'] = platform_deps
                    else:
                        version = rest  # NOQA
                    info['version'] = (op, version)
            yield info

    def parse_require_file(fpath):
        with open(fpath, 'r') as f:
            for line in f.readlines():
                line = line.strip()
                if line and not line.startswith('#'):
                    for info in parse_line(line):
                        yield info

    def gen_packages_items():
        if exists(require_fpath):
            for info in parse_require_file(require_fpath):
                parts = [info['package']]
                if with_version and 'version' in info:
                    parts.extend(info['version'])
                if not sys.version.startswith('3.4'):
                    # apparently package_deps are broken in 3.4
                    platform_deps = info.get('platform_deps')
                    if platform_deps is not None:
                        parts.append(';' + platform_deps)
                item = ''.join(parts)
                yield item

    packages = list(gen_packages_items())
    return packages


if __name__ == '__main__':
    write_version_py()
    setup(
        name='mmdet',
        version=get_version(),
        description='Open MMLab Detection Toolbox and Benchmark',
        long_description=readme(),
        author='OpenMMLab',
        author_email='chenkaidev@gmail.com',
        keywords='computer vision, object detection',
        url='https://github.com/open-mmlab/mmdetection',
        packages=find_packages(exclude=('configs', 'tools', 'demo')),
        package_data={'mmdet.ops': ['*/*.so']},
        classifiers=[
            'Development Status :: 4 - Beta',
            'License :: OSI Approved :: Apache Software License',
            'Operating System :: OS Independent',
            'Programming Language :: Python :: 3',
            'Programming Language :: Python :: 3.5',
            'Programming Language :: Python :: 3.6',
            'Programming Language :: Python :: 3.7',
        ],
        license='Apache License 2.0',
        setup_requires=parse_requirements('requirements/build.txt'),
        tests_require=parse_requirements('requirements/tests.txt'),
        install_requires=parse_requirements('requirements/runtime.txt'),
        extras_require={
            'all': parse_requirements('requirements.txt'),
            'tests': parse_requirements('requirements/tests.txt'),
            'build': parse_requirements('requirements/build.txt'),
            'optional': parse_requirements('requirements/optional.txt'),
        },
        ext_modules=[
            make_cuda_ext(
                name='compiling_info',
                module='mmdet.ops.utils',
                sources=['src/compiling_info.cpp']),
            make_cuda_ext(
                name='nms_ext',
                module='mmdet.ops.nms',
                sources=['src/nms_ext.cpp', 'src/cpu/nms_cpu.cpp'],
                sources_cuda=[
                    'src/cuda/nms_cuda.cpp', 'src/cuda/nms_kernel.cu'
                ]),
            make_cuda_ext(
                name='roi_align_ext',
                module='mmdet.ops.roi_align',
                sources=[
                    'src/roi_align_ext.cpp',
                    'src/cpu/roi_align_v2.cpp',
                ],
                sources_cuda=[
                    'src/cuda/roi_align_kernel.cu',
                    'src/cuda/roi_align_kernel_v2.cu'
                ]),
            make_cuda_ext(
                name='roi_pool_ext',
                module='mmdet.ops.roi_pool',
                sources=['src/roi_pool_ext.cpp'],
                sources_cuda=['src/cuda/roi_pool_kernel.cu']),
            make_cuda_ext(
                name='deform_conv_ext',
                module='mmdet.ops.dcn',
                sources=['src/deform_conv_ext.cpp'],
                sources_cuda=[
                    'src/cuda/deform_conv_cuda.cpp',
                    'src/cuda/deform_conv_cuda_kernel.cu'
                ]),
            make_cuda_ext(
                name='deform_pool_ext',
                module='mmdet.ops.dcn',
                sources=['src/deform_pool_ext.cpp'],
                sources_cuda=[
                    'src/cuda/deform_pool_cuda.cpp',
                    'src/cuda/deform_pool_cuda_kernel.cu'
                ]),
            make_cuda_ext(
                name='sigmoid_focal_loss_ext',
                module='mmdet.ops.sigmoid_focal_loss',
                sources=['src/sigmoid_focal_loss_ext.cpp'],
                sources_cuda=['src/cuda/sigmoid_focal_loss_cuda.cu']),
            make_cuda_ext(
                name='masked_conv2d_ext',
                module='mmdet.ops.masked_conv',
                sources=['src/masked_conv2d_ext.cpp'],
                sources_cuda=[
                    'src/cuda/masked_conv2d_cuda.cpp',
                    'src/cuda/masked_conv2d_kernel.cu'
                ]),
            make_cuda_ext(
                name='carafe_ext',
                module='mmdet.ops.carafe',
                sources=['src/carafe_ext.cpp'],
                sources_cuda=[
                    'src/cuda/carafe_cuda.cpp',
                    'src/cuda/carafe_cuda_kernel.cu'
                ]),
            make_cuda_ext(
                name='carafe_naive_ext',
                module='mmdet.ops.carafe',
                sources=['src/carafe_naive_ext.cpp'],
                sources_cuda=[
                    'src/cuda/carafe_naive_cuda.cpp',
                    'src/cuda/carafe_naive_cuda_kernel.cu'
                ])
        ],
        cmdclass={'build_ext': BuildExtension},
        zip_safe=False)
