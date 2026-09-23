from setuptools import setup, find_packages
import d2l

# install_requires 里放的是 d2l 各后端「共用的第三方依赖」，即 d2l/*.py 实际
# import 的非标准库、非框架模块（实测穷举）：
#     IPython · PIL · matplotlib · matplotlib_inline · numpy · pandas · requests
# 深度学习框架本身（torch/torchvision、tensorflow、paddle、mxnet）由用户按需自装，
# 不在这里声明。
#
# 下界策略分两类，判据是「这个下界会不会触发对宿主环境的升级」：
#
# 1) 有 C 扩展、按 CPython ABI 发 wheel 的包 —— 写字面下界。
#    取自「首个提供 cp313 wheel 的版本」：
#        numpy 2.1.0 · matplotlib 3.9.2 · pandas 2.2.3 · pillow 10.4.0
#    在 Python 3.13 上这个下界是**恒真**的（更老的版本根本没有 cp313 wheel，
#    装不上），所以写出来既表达了真实最低要求，又不可能把已装的包升级掉。
#
# 2) 纯 Python 包（requests / ipython / matplotlib-inline）—— **不给版本下界**。
#    它们在能跑 notebook 的环境里必然已存在，而 d2l 只用到极老且稳定的 API
#    （display.display / display.clear_output / set_matplotlib_formats）。
#    给纯 py 包写下界 = 凭空制造一个真实约束，只会把宿主环境里的
#    ipython / requests 升级掉，收益为零。
#    实测教训：曾写 ipython>=8.28，结果在 Colab 上把预装的 ipython 7.34.0
#    升级成 9.17.1，触发 `google-colab 1.0.0 requires ipython==7.34.0` 冲突。
#    裸包名（无约束）的语义正是我们要的：**已装即满足、就不动它**；
#    只有在完全缺失的环境里才会去装一个最新版。
requirements = [
    'numpy>=2.1',
    'matplotlib>=3.9.2',
    'pandas>=2.2.3',
    'pillow>=10.4',
    'requests',
    'ipython',
    'matplotlib-inline',
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
        'notebook': ['jupyter'],
    },
)
