from setuptools import setup, find_packages
import d2l

# 依赖下界 = 各包「最早提供 cp313 wheel 的版本」（实测 PyPI 元数据）：
#   numpy 2.1.0 / matplotlib 3.9.2 / pandas 2.2.3
# 一律用 >= 而不是 ==：在 Google Colab 这类托管环境里，收紧紧依赖会把预装的
# numpy / pandas / matplotlib 降级，进而连带打坏 Colab 自带的 torch。
requirements = [
    'numpy>=2.1',
    'matplotlib>=3.9.2',
    'requests>=2.32',
    'pandas>=2.2.3',
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
