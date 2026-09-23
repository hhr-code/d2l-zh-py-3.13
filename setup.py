from setuptools import setup, find_packages
import d2l

# install_requires 里放的是 d2l 各后端「共用的第三方依赖」，即 d2l/*.py 实际
# import 的非标准库、非框架模块（实测穷举）：
#     IPython · PIL · matplotlib · matplotlib_inline · numpy · pandas · requests
# 深度学习框架本身（torch/torchvision、tensorflow、paddle、mxnet）由用户按需自装，
# 不在这里声明。
#
# 下界 = 各包「最早支持 Python 3.13 的版本」（实测 PyPI 元数据）：
#     numpy 2.1.0 · matplotlib 3.9.2 · pandas 2.2.3 · pillow 10.4.0
#     ipython / matplotlib-inline 是纯 py 包，无 wheel 标签，下界取 3.13 同期的稳定线
# 一律用 >= 而不是 ==：在 Google Colab 这类托管环境里，收紧依赖会把预装的
# numpy / pandas / matplotlib 降级，进而连带打坏 Colab 自带的 torch。
requirements = [
    'numpy>=2.1',
    'matplotlib>=3.9.2',
    'matplotlib-inline>=0.1.7',
    'requests>=2.32',
    'pandas>=2.2.3',
    'ipython>=8.28',
    'pillow>=10.4',
]

setup(
    name='d2l',
    version=d2l.__version__,
    python_requires='>=3.13',
    author='D2L Developers',
    author_email='d2l.devs@gmail.com',
    url='https://d2l.ai',
    description='Dive into Deep Learning',
    license='MIT-0',
    packages=find_packages(),
    zip_safe=True,
    install_requires=requirements,
    # jupyter 是「运行 notebook 的环境」，不是 d2l 库本身的依赖。
    # 托管环境（Colab）自带完整 notebook 栈；把它留在 install_requires 里
    # 会让 pip 去解析/升级 notebook、jupyterlab，有打坏宿主环境的风险。
    extras_require={
        'notebook': ['jupyter>=1.1'],
    },
)
