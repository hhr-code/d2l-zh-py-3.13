# d2l-zh 升级到 Python 3.13 —— 工作清单

> 目标场景：本仓库的 notebook 能在 **Google Colab（真机实测 Python 3.13.15）** 上原样跑通，且 `pip install` 不产生依赖冲突。
> 状态：L1 调研已完成；**L2 依赖层已动手（`setup.py` 已改）**；L3/L4/L5 待做。

---

## 实施进度

| 批次 | 内容 | 状态 |
|---|---|---|
| Batch 0 | 固化基线 | ✅ Colab = Python 3.13.15（老马真机确认） |
| Batch 1 | `setup.py` 依赖下界 + `python_requires` | ✅ **已实施**（含一次回归修复），见 §1.4 |
| Batch 2.3 | PyTorch tab 语义层核对 | 🟡 **部分**：`d2l.torch` smoke 7/7 通过；notebook 级逐章验证未做 |
| Batch 3.1/3.3/3.4 | d2lbook / Colab 安装 URL / 安装文档 | ⬜ 待做 |
| Batch 4 | 3.13 门禁 | ⬜ 待做 |

**本次范围（老马 2026-09-23 拍板）**：第一批只做 PyTorch；MXNet 冻结不参与。

---

## 0. 结论先行

把「一个项目支持 Python 3.13」拆成 5 层必要条件，逐层实测：

| 层 | 判据 | 实测结论 | 工作量 |
|---|---|---|---|
| **L1 解释器层** | 3.13 能否解释现有代码 | ✅ **已通过**：2694 个代码块 0 语法错误、0 处引用已移除 stdlib、0 处 SyntaxWarning；`d2l/*.py`（9386 行）全部编译通过 | 几乎为零 |
| **L2 依赖层** | 依赖能否在 3.13 装出来 | ✅ **已修复**：`setup.py` 改为宽松下界，wheel 构建 + 依赖解析 + `pip check` 全通；MXNet 结构性无解但已冻结（DEFECT-001） | 已落地 |
| **L3 语义层** | 装出来后行为是否还对 | ⚠️ **未验证**：numpy 1→2、pandas 1→3、torch 1.12→2.x 三组行为变更需逐项核（TF/Paddle 延后） | 中～大 |
| **L4 构建发布层** | d2lbook / CI / Colab / 文档 | ⚠️ 全部 pin 在 2022 年；`d2lbook 1.0.3` 本身在 3.13 实测可 import | 中 |
| **L5 验证层** | 有没有可复现的 3.13 门禁 | ❌ 目前不存在 | 中 |

**一句话**：这次升级的难点**不在「代码兼容 3.13」**（那部分几乎是零），而在**依赖大版本跃迁**和**框架取舍**。

---

## 1. 决策（已拍板 2026-09-23）

### D1：MXNet —— **冻结，记录缺陷，不参与本次升级** ✅ 已决策

**缺陷记录（DEFECT-001，状态：WONTFIX / 冻结）**

> **标题**：MXNet 后端在 Python 3.13 上无法安装，`@tab mxnet` 全部笔记本不可用
> **影响**：`#@tab ...mxnet` 标记 74 处、`:begin_tab:\`mxnet\`` 174 处、涉及 **106 个文件**、独立 mxnet 代码块 3 个
> **根因**：`mxnet 1.9.1` 的 `requires_dist` 为 `numpy<2.0.0`（PyPI 元数据实测）；而 numpy 在 Python 3.13 上**最早提供 wheel 的版本是 2.1.0**（1.26.4 只有 cp312 及以下）。
> 两者交集为**空集** → 不是「难装」，是依赖关系不可满足。
> **加剧因素**：MXNet 已于 2023-02 发布最后一版（1.9.1）后被 Apache 归档停更，上游不会提供 cp313 wheel；mxnet 的 `py3-none-*` wheel 是 ctypes 加载 `libmxnet.so`，但依赖解析阶段就先失败了。
> **处理**：**冻结**。不改动 `d2l/mxnet.py`、不删 notebook 里的 mxnet tab 内容、不升级 mxnet 相关 Dockerfile 与 CI 脚本。
> **边界**：本次「支持 Python 3.13」的交付范围**明确不含 MXNet**。若未来需要，唯一路径是移除对 numpy<2 的约束并自行重编译 libmxnet，成本远超收益。
> **复现**：`python3.13 -m pip install mxnet` → `ERROR: No matching distribution found`

### D2：第一批只做 PyTorch ✅ 已决策

- **PyTorch**：3.13 最早可用 **2.5.0**，当前 2.14.0。教学主战场，风险最低。
- **TensorFlow**（延后）：3.13 最早可用 **2.20.0**，必须跨 **Keras 3**（11 处 `tf.keras.Model` 子类 / 4 处 `.compile()` / 7 处 `tf.data`）。
- **PaddlePaddle**（延后）：3.13 最早可用 **3.0.0**，跨 2.3→3.x 大版本。

### D3：Colab 上的依赖必须用宽松下界 ✅ 已决策并实施

在 Colab 这类托管环境里，收紧依赖会把预装的 numpy / pandas / matplotlib **降级**，进而连带打坏 Colab 自带的 torch。因此 `install_requires` 一律 `>=`，不用 `==`。**已实施，见 §1.4。**

### 1.4 本次已实施的改动（`setup.py`）

依赖清单不再凭感觉维护，改成**按 AST 穷举** `d2l/*.py` 的非标准库、非框架 import。结果是恰好 7 个共用依赖：`IPython · PIL · matplotlib · matplotlib_inline · numpy · pandas · requests`（框架本身 torch/torchvision、tensorflow、paddle、mxnet 仍由用户按需自装，保持原设计）。

| 项 | 改前 | 改后 | 依据 |
|---|---|---|---|
| `python_requires` | `>=3.5` | `>=3.13` | 唯一验证过的版本；原值本就与依赖矛盾（`numpy==1.21.5` 无 3.11+ wheel） |
| `numpy` | `==1.21.5` | `>=2.1` | 2.1.0 首个带 cp313 wheel |
| `matplotlib` | `==3.5.1` | `>=3.9.2` | 3.9.2 首个带 cp313 wheel |
| `pandas` | `==1.2.4` | `>=2.2.3` | 2.2.3 首个带 cp313 wheel |
| `requests` | `==2.25.1` | `>=2.32` | 纯 py，但 2.25 系列的 urllib3 组合过老 |
| `jupyter` | `==1.0.0`（主依赖） | 移入 `extras_require['notebook']` | jupyter 是运行环境而非库依赖；留主依赖会促使 pip 解析/升级 notebook、jupyterlab，有打坏宿主环境（Colab）的风险 |
| `matplotlib-inline` | **缺失** | `>=0.1.7` | `d2l/*.py` 用 `backend_inline` 画图 |
| `ipython` | **缺失** | `>=8.28` | `d2l/*.py` 用 `IPython.display` |
| `pillow` | **缺失** | `>=10.4` | `d2l/torch.py`、`paddle.py` 用 `PIL.Image`；10.4.0 首个带 cp313 wheel |

> ⚠️ **回归教训（已修复，见 commit `b54d4e`）**：把 `jupyter` 移出主依赖时，`IPython` 断了——它原先是通过 `jupyter → notebook → IPython` 这条**隐式链路**带进来的，移走后 `from d2l import torch` 立刻 `ModuleNotFoundError: No module named 'IPython'`。
> 这个回归是**本机 torch smoke 测出来的**，不是读代码看出来的。结论：动依赖声明后必须跑一次真实 import + 调用，静态检查发现不了隐式依赖链路断裂。

**验证证据（本机 Python 3.13.12）**

```
# 1) wheel 构建（Colab 走的就是这条非 editable 路径）
$ pip wheel --no-deps .        →  d2l-2.0.0-py3-none-any.whl 构建成功

# 2) 产物元数据
Requires-Python: >=3.13
Requires-Dist: numpy>=2.1
Requires-Dist: matplotlib>=3.9.2
Requires-Dist: matplotlib-inline>=0.1.7
Requires-Dist: requests>=2.32
Requires-Dist: pandas>=2.2.3
Requires-Dist: ipython>=8.28
Requires-Dist: pillow>=10.4
Provides-Extra: notebook
Requires-Dist: jupyter>=1.1; extra == "notebook"

# 3) 干净 venv 完整安装（模拟 Colab）
$ pip install <wheel>          →  d2l 2.0.0 + numpy 2.5.3 + matplotlib 3.11.2
                                  + pandas 3.0.6 + requests 2.34.2 + pillow 12.3.0
$ pip check                    →  No broken requirements found.

# 4) d2l.torch 真实 smoke（torch 2.14.0 / numpy 2.5.3 / matplotlib 3.11.2）
[1] from d2l import torch      OK
[2] d2l.synthetic_data         OK  (1000, 2) (1000, 1)
[3] d2l.load_array             OK  (10, 2) (10, 1)
[4] d2l.Timer                  OK
[5] d2l.set_figsize + d2l.plt  OK
[6] 3 步训练循环（SGD+MSE）    OK  final loss = 23.565546
[7] d2l.Accumulator            OK
```

> 注 1：`pip install -e .` 在本机沙箱会因 `editable_wheel` 创建临时目录报 `EEXIST`（沙箱限制，非项目问题）；Colab 走的是**非 editable 的 wheel 构建路径**，已实测通过。
> 注 2：在**全新环境**里 pip 会把 pandas 解析到 **3.0.6**——pandas 3.0 的 CoW / str dtype 行为变更因此对全新安装是「活的」，见 Batch 2.2。Colab 上若已预装 pandas 2.x，则会被保留（下界 `>=2.2.3` 满足），不受影响。
> 注 3：构建残留 `build/` 会让二次 `pip wheel` 报 `[Errno 17] File exists: 'build/bdist.*/wheel/d2l-2.0.0.dist-info'`，重新构建前先 `rm -rf build d2l.egg-info`。

---

## 2. 完整工作清单

### Batch 0 —— 固化基线

- [x] **0.1 目标运行时版本** ✅ **Colab = Python 3.13.15**（老马真机确认，2026-09-23）。
      ~~（此前根据第三方引用的 Google past-runtime 2026.07 快照推测为 3.12.13，作废。）~~
      仍需补记的是 Colab 3.13 runtime **预装的 numpy / torch / pandas / matplotlib 具体版本**——它决定我们的下界是否真的「已满足、不触发升级」：
  ```python
  import sys, platform, numpy, torch, pandas, matplotlib
  print(sys.version, platform.platform())
  for m in (numpy, torch, pandas, matplotlib): print(m.__name__, m.__version__)
  ```
- [ ] **0.2 明确验收定义**（建议写进 README/INFO.md）：
  - Colab 上 `pip install git+https://github.com/<fork>@<branch>` 成功，且 `pip check` 干净
  - Colab 上 `torch` tab 的 notebook 可执行、无 ImportError
  - 本地 `py -3.13` 干净 venv 里 wheel 构建 + 安装成功、`from d2l import torch` 可用
  - CI 的 `d2lbook build outputcheck tabcheck` 在 3.13 镜像里全绿

  > 已达成（本机 py3.13.12）：前两条的前半段 ✅，其余待做。
  > 注：`pip install -e .`（editable）**不是 Colab 的路径**——Colab 用 `git+` 会走非 editable 的 wheel 构建，本机实测该路径通过。
- [ ] **0.3 确认是否只需支持 Colab**。如果还要支持 「本地 conda + py3.13」「Windows」，验证矩阵要扩。

### Batch 1 —— L2 依赖层 ✅ 已实施

**1.1 `setup.py`**（原 5 个 pin 全部无 cp313 轮子）——**已改，见 §1.4**

| 依赖 | 原 pin | 3.13 下 | 最早支持 cp313 | 已改为 |
|---|---|---|---|---|
| `numpy` | `==1.21.5` | ❌ 无 cp313 | **2.1.0** | `numpy>=2.1` |
| `matplotlib` | `==3.5.1` | ❌ 无 cp313 | **3.9.2** | `matplotlib>=3.9.2` |
| `pandas` | `==1.2.4` | ❌ 无 cp313 | **2.2.3** | `pandas>=2.2.3` |
| `requests` | `==2.25.1` | ⚠️ 纯 py 可装但过老 | — | `requests>=2.32` |
| `jupyter` | `==1.0.0` | ⚠️ 纯 py 可装但过老 | — | 移入 `extras_require['notebook']` |
| `python_requires` | `>=3.5` | 与依赖自相矛盾 | — | `>=3.13` |

> 每一条 `==` 都要问一句：**这个上限是必要的还是历史遗留？** 在 Colab 场景下收紧上限 = 主动破坏用户环境。

- [ ] **1.2 `d2l` 的分发方式待统一**：仓库内 `d2l/__init__.py` 是 `2.0.0`（本次安装的就是它），但 CI 脚本和 `chapter_installation/index.md` 装的是 PyPI 上的 `d2l==0.17.6`（**另一个包**）。本次不改，但要在 Batch 3 一并理顺，否则文档和 CI 会继续指向老包。

**1.3 框架依赖矩阵**（实测 PyPI 元数据）—— 本次只取 PyTorch 行（D2 决策）

| 框架 | 仓库/CI 现值 | 3.13 最早可用 | 当前最新 | 本次是否处理 |
|---|---|---|---|---|
| PyTorch | 1.12（Docker 基础镜像） | **2.5.0** | 2.14.0 | ✅ 本批 |
| torchvision | 0.13.0 | **0.21.0** | 0.29.0 | ✅ 本批 |
| TensorFlow | 2.8.0 | **2.20.0** | 2.21.0 | ⬜ 后续 |
| tensorflow-probability | 0.16.0 | 需单独核实 | — | ⬜ 后续 |
| PaddlePaddle | 2.3.2 | **3.0.0** | 3.3.1 | ⬜ 后续 |
| MXNet | 1.7.0 / 1.9.1 | **无解** | 1.9.1（EOL） | 🧊 冻结（DEFECT-001） |

- [x] **1.4 在干净 venv 里验证依赖集可解** ✅ 见 §1.4 的验证证据（wheel 构建 + 元数据正确；完整依赖解析结果见下方「实测记录」）。

### Batch 2 —— L3 语义层（逐项核，每项都要跑一遍 notebook 才算数）

**2.1 numpy 1.x → 2.x**

- [ ] 仓库内**无**已移除别名（`np.float` / `np.int` / `np.bool` / `np.object` / `np.str` / `np.alltrue` / `np.NaN` 等）——实测 0 处 ✅
- [ ] `d2l/*.py` 的 numpy 面很小，风险低：`torch.py` 只用 3 个 numpy 属性（`genfromtxt`/`float32`/`array`），`paddle.py` 3 个，`tensorflow.py` 8 个，`mxnet.py` 36 个
- [ ] **重点核 NEP 50 标量提升**：`np.float32(a) + 1.0` 在 numpy 2 下不再提升到 float64。这**会改变数值结果**，书上打印的数字可能与现有缓存输出不一致。
- [ ] 核 `np.array(..., copy=False)` 语义变更（numpy 2 下需要拷贝时会直接抛错）
- [ ] 核 `np.genfromtxt`（`kaggle-house-price` 数据加载路径）

**2.2 pandas 1.2 → 2.2/3.x**

- [ ] **Copy-on-Write 在 pandas 3.0 已是默认**：链式赋值会静默失效。重点核 `chapter_multilayer-perceptrons/kaggle-house-price.md`（`pd.read_csv` → `all_features` 拼接 → 独热编码）、`kaggle-cifar10.md`、`object-detection-dataset.md`
- [ ] pandas 3.0 的 `str` dtype 默认变化：`pd.read_csv` 出来的字符串列 dtype 与 1.2 完全不同，会影响 `dtypes` 打印输出
- [ ] `chapter_attention-mechanisms/transformer.md` 里 4 处 `pd.DataFrame(...).fillna(0.0).values` —— 需确认 `values` 在新 dtype 下仍是 float

**2.3 PyTorch 1.12 → 2.x**

- [x] **`d2l/torch.py` 的 import + 典型调用 smoke** ✅ **已通过 7/7**（见 §1.4 第 4 段）：
      `from d2l import torch` / `synthetic_data` / `load_array` / `Timer` /
      `set_figsize`+`plt` / 3 步 SGD 训练循环 / `Accumulator`，跑在 torch 2.14.0 +
      numpy 2.5.3 + matplotlib 3.11.2 + Python 3.13.12 上。
      140 个顶层符号里，「线性网络 / MLP / 基础训练工具」这一层已经覆盖。
- [ ] **`torch.load` 默认 `weights_only=True`（torch 2.6+）**：实测仓库有 **5 处** 调用
      （`chapter_deep-learning-computation/read-write.md` 4 处、`natural-language-inference-bert.md` 1 处）。
      存的是 Tensor / Tensor 列表 / dict / state_dict，**预计兼容，但必须逐处实跑确认**（smoke 未覆盖）。
- [ ] **`torchvision.models.*(pretrained=True)` 共 15 处**：deprecated 但仍工作；建议改 `weights=` 枚举，并确认在 torchvision 0.29 下未被移除。
- [x] `torch.meshgrid` 已显式传 `indexing='ij'` ✅（`computer-vision/anchor.md`），无需改
- [ ] `torchvision.transforms` v1 API（79 处 `ToTensor`/`Resize`/`Normalize`/`RandomResizedCrop`）：v1 仍可用，需在 notebook 级验证时确认。
- [ ] 进阶模块（`RNNModel` / `MultiHeadAttention` / `BERTModel` / `TokenEmbedding` / `Seq2SeqEncoder` / 各类 `train_ch*`）**尚未 smoke**——它们涉及自定义 `torch.nn.Module` 子类与数据管道，是 L3 剩余的主要风险面。

**2.4 TensorFlow 2.8 → 2.20（跨 Keras 3）**

- [ ] 11 处 `tf.keras.Model` 子类：Keras 3 下 `train_step`/`test_step` 的契约、`model.metrics` 行为有变
- [ ] 4 处 `model.compile()`：Keras 3 的参数与默认值有变
- [ ] 7 处 `tf.data`：管道 API 基本稳定，但 `tf.data.Dataset.from_tensor_slices` 与 Keras 3 的 batch/PRNG 交互需核
- [ ] 1 处 `jit_compile`、1 处 `tensorflow_probability`（`chapter_preliminaries/probability.md`）—— tfp 对 TF 2.20 + Keras 3 的支持需单独确认
- [Paddle] `paddle 2.3 → 3.x`：跨大版本，`paddle.vision.transforms` / `paddle.nn.Layer` 需核

**2.5 Python 3.13 自身语义**

- [ ] 实测**无**影响：0 处引用 3.13 移除的 stdlib（`cgi`/`telnetlib`/`audioop`/`distutils`/`imp`/`lib2to3` …）、0 处 SyntaxWarning（含无效转义序列）、0 处已移除的 `typing.io`/`typing.re`
- [ ] `multiprocessing` 默认 start method 在 3.14 才改，不在本次范围
- [ ] `d2l.get_dataloader_workers()` 在 Colab 上返回的核数假设需核（与 3.13 无关，但顺手看）

### Batch 3 —— L4 构建 / 发布层

**3.1 d2lbook 构建链**

- [ ] 实测：`d2lbook 1.0.3` 在 Python **3.13.12** 下 `import d2lbook` **成功** ✅（本机 venv 验证）
- [ ] 但它 pin 了 `sphinx==5.3.0`、`recommonmark`（已废弃）、`sphinxcontrib-bibtex==2.4.2` 等 2022 年的版本 —— 纯 Python 装得上，**但 `d2lbook build tabcheck` / HTML 构建要在 3.13 下实跑才算数**
- [ ] `d2lbook build outputcheck tabcheck` 作为 3.13 门禁

**3.2 CI / Docker**

- [ ] 4 个基础镜像全部是 py3.8～3.10 时代，必须换或分离：
      `Dockerfile.d2l-zh-torch` → `nvcr.io/nvidia/pytorch:22.06-py3`
      `Dockerfile.d2l-zh-tf` → `nvcr.io/nvidia/tensorflow:22.09-tf2-py3`
      `Dockerfile.d2l-zh-mxnet` → `nvcr.io/nvidia/mxnet:23.04-py3`
      `Dockerfile.d2l-zh-paddle` → `nvcr.io/nvidia/paddlepaddle:22.12-py3`
      另有 `Dockerfile.d2l-builder` → `ubuntu:latest`（这个反而最省事）
- [ ] `.github/workflow_scripts/build_pytorch.sh` 等 5 个脚本里：`pip3 install d2l==0.17.6`（5 处）、`pip3 install numpy==1.24.4`（1 处）—— 都要换
- [ ] `ci/docker/print_versions.py` 仍在 import `gym` / `gpytorch` / `syne_tune` —— 已过时
- [ ] `ci/docker/entry.sh`、`d2l_job.sh` 里的 `python3` 假设
- [ ] 决策：**AWS Batch CI 是否跟着升到 3.13**，还是只保证「源码 + 本地/Colab 支持 3.13」而 CI 维持旧链（成本更低）

**3.3 Colab / SageMaker 集成**

- [ ] `config.ini [colab] libs` 的 4 条 `git+https://github.com/d2l-ai/d2l-zh@release`
- [ ] `config.ini [colab]` 的 mxnet 分支 `-U mxnet-cu101==1.7.0`（随 D1 处理）
- [ ] `config.ini [sagemaker] kernel` 里的 `conda_mxnet_p36` / `conda_pytorch_p36` 等已不存在的 kernel 名
- [ ] 下游 4 个 Colab 仓库（`d2l-zh-colab` / `-pytorch-colab` / `-tensorflow-colab` / `-paddle-colab`）的 notebook 副本需同步重新生成
- [ ] 每个 notebook 顶部的安装 cell（对应 Colab 仓库），确保不降级 Colab 预装包

**3.4 文档**

- [ ] `chapter_installation/index.md` 整章重写：`python=3.9` → 3.13；`mxnet-cu101==1.7.0`、`torch==1.12.0`、`torchvision==0.13.0`、`tensorflow==2.8.0`、`tensorflow-probability==0.16.0`、`paddlepaddle==2.3.2`、`pip install d2l==0.17.6` 全部要更新
- [ ] `INFO.md` 里 `conda env update -f build/env.yml` + `make html`（`build/` 目录当前仓库里并不存在，是未初始化的 submodule `.gitmodules` → `build/mx-theme` / `build/utils`）
- [ ] `README.md` / `INFO.md` 里加「支持的 Python 版本」一节
- [ ] `config.ini [build] tabs` 的 tab 列表（随 D1/D2 调整）

### Batch 4 —— L5 验证层（把上面每一条变成可复跑的门禁）

- [ ] **G1 静态门禁**：`python -W error::SyntaxWarning -m compileall d2l/ setup.py` + notebook 代码块 AST 扫描（脚本已有，见附录）
- [ ] **G2 安装门禁**：干净 py3.13 venv `pip install -e .` → `pip check` 干净 → `python -c "from d2l import torch; ..."`
- [ ] **G3 构建门禁**：3.13 容器里 `d2lbook build outputcheck tabcheck`
- [ ] **G4 全量 eval 门禁**：`d2lbook build eval --tab pytorch`（成本最高：INFO.md 记载单 notebook 限制 20min，共 117 个含代码的 md）
- [ ] **G5 Colab 冒烟**：在真实 Colab runtime 上跑基线脚本 + 前 3 章 notebook
- [ ] **G6 依赖冲突门禁**：Colab 里 `pip check`，专门防 D3 那个坑

---

## 3. 建议推进顺序

```
Batch 0（基线+拍板 D1/D2/D3）
   └→ Batch 1（setup.py + 依赖矩阵，本机 venv 验）
        └→ Batch 2.1/2.3（numpy2 + torch2，只做 PyTorch tab）  ← M1 到此可交付
             └→ Batch 3.1/3.3/3.4（d2lbook + Colab + 文档）
                  └→ Batch 4 G1–G3 + G5/G6
                       └→ Batch 2.4（TF/Paddle）              ← M2
                            └→ Batch 3.2（CI/Docker）+ G4 全量 eval  ← M3
```

理由：PyTorch tab 风险最低、Colab 主用例、能最快拿到「3.13 可用」的可验证结论；TF（Keras 3）和 Paddle（3.x）是可独立并行、可延后的大坑；MXNet 不参与。

---

## 附录 A：实测证据汇总

| 项 | 命令 / 来源 | 结果 |
|---|---|---|
| notebook 代码块语法 | AST 扫描 2694 个 `.python` 代码块 | 0 语法错误、0 SyntaxWarning |
| 已移除 stdlib 引用 | AST 扫描 + 全库 grep | 0 处 |
| numpy 旧别名 | AST 扫描 | 0 处 |
| `d2l/*.py` 编译 | `py_compile` with `-W error::SyntaxWarning` | 全部通过 |
| `d2lbook` on py3.13 | venv + `import d2lbook` | ✅ 1.0.3 成功 |
| 各包 cp313 轮子 | PyPI JSON API 元数据 | 见 §1.1 / §1.3 表 |
| mxnet 依赖冲突 | PyPI `requires_dist` = `numpy<2.0.0`，numpy cp313 起点 2.1.0 | 无解 |
| tab 规模 | 正则统计 | pytorch 562 块 / paddle 595 / tensorflow 412 / all 1008 |

**未能在本机验证的**（沙箱限制，需真机补）：
1. **Colab 真实 Python 版本** —— 沙箱访问不到 Colab。公开资料（引用 Google past-runtime 列表的 2026.07 快照）显示是 Python **3.12.13** + NumPy 2.0.2 + PyTorch 2.11.0 + TF 2.20.0，与「3.13.15」不一致，需以 Batch 0.1 的实测为准。
2. **`d2lbook build` 完整链路在 3.13 下能否跑通** —— 已确认 `import d2lbook` 成功，但补齐 `nbformat`/`sphinx` 等依赖时被沙箱的 pip 临时目录问题卡住（`EEXIST`），随后网络停滞，未跑出 `tabcheck` 结果。
3. **`d2l.torch` 在 py3.13 + torch 2.x 下的 import / 调用 smoke** —— 装 torch 的 venv 在下载阶段停滞（18 分钟无进展）后中止，未取得结果。

> 三条都属于「本机受限」而非「项目有问题」。前两条在真机（或 Colab）上几分钟就能补上，建议直接作为 Batch 4 的 G5 一起做。

## 附录 B：扫描脚本（G1 门禁的现成实现）

下面的扫描器就是本报告所有「实测」数字的来源。它会：解析 tab 化 notebook 的 `.python` 代码块 → 按 3.13 语法编译并捕获 SyntaxWarning → AST 遍历查已移除 stdlib / numpy 旧别名 / pandas / matplotlib 弃用 API → 统计每个 tab 的代码块数。
**建议收进仓库**（如 `ci/scripts/check_py313.py`），作为 G1 门禁的常驻实现，并在 CI 里加 `python ci/scripts/check_py313.py .` 一步。

```python
"""扫描 d2l-zh 的 tab 化 notebook，找出 Python 3.13 迁移风险点。用法: python3 check_py313.py <repo_root>"""
import ast, collections, pathlib, re, sys, warnings

ROOT = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".")
FENCE = re.compile(r"^\s*(`{3,})\s*(\{?[^`]*?)\s*$")

REMOVED_MODULES = {
    "aifc", "audioop", "cgi", "cgitb", "chunk", "crypt", "imghdr", "mailcap",
    "msilib", "nis", "nntplib", "ossaudiodev", "pipes", "sndhdr", "spwd",
    "sunau", "telnetlib", "uu", "xdrlib", "lib2to3", "distutils", "imp",
    "asynchat", "asyncore", "smtpd", "binhex", "formatter", "parser",
    "symbol", "tkinter.tix",
}
NUMPY_REMOVED = {
    "float", "int", "bool", "object", "str", "complex", "unicode", "long",
    "alltrue", "sometrue", "cumproduct", "product", "round_", "NaN", "Inf",
    "NINF", "PINF", "PZERO", "NZERO", "infty", "mat", "asfarray", "issctype",
    "set_string_function", "get_array_wrap", "byte_bounds", "safe_eval",
}
STDLIB_ATTR_RISKS = {
    ("ast", "Num"), ("ast", "Str"), ("ast", "Bytes"), ("ast", "NameConstant"),
    ("ast", "Ellipsis"), ("ast", "Index"), ("ast", "ExtSlice"),
    ("datetime", "utcnow"), ("datetime", "utcfromtimestamp"),
    ("locale", "resetlocale"),
}
PANDAS_ATTR_RISKS = {
    "append", "applymap", "iteritems", "swapaxes", "lookup", "get_values",
    "set_axis", "first", "last", "mad", "tshift", "pct_change",
}
MATPLOTLIB_ATTR_RISKS = {"get_cmap", "register_cmap", "hold", "ishold", "axes"}


def iter_blocks():
    """yield (path, fence_line_no, info, tab, source)"""
    for p in sorted(ROOT.rglob("*.md")):
        if "_origin" in p.name or "_build" in p.parts:
            continue
        lines = p.read_text(encoding="utf-8").split("\n")
        i = 0
        while i < len(lines):
            m = FENCE.match(lines[i])
            if not m:
                i += 1
                continue
            fence, info = m.group(1), m.group(2)
            if ".python" not in info and "python" not in info:
                i += 1
                continue
            start, buf = i + 1, []
            i += 1
            while i < len(lines):
                if lines[i].strip() == fence:
                    break
                buf.append(lines[i])
                i += 1
            src = "\n".join(buf)
            tabs = re.findall(r"^#@tab\s+(.+)$", src, re.M)
            yield p, start, info, (tabs[0].strip() if tabs else "all"), src
            i += 1


def strip_magic(src):
    """剥掉 IPython 魔法与 shell 转义，否则 ast 解析不了"""
    return "\n".join(
        "pass" if l.lstrip().startswith(("%", "!", "?")) else l
        for l in src.split("\n")
    )


def main():
    blocks = list(iter_blocks())
    print(f"python 代码块: {len(blocks)}  "
          f"({dict(collections.Counter(b[3] for b in blocks))})\n")

    parse_errors, warn_counter, warn_example = [], collections.Counter(), {}
    for p, ln, info, tab, src in blocks:
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            try:
                compile(strip_magic(src), str(p), "exec")
            except SyntaxError as e:
                parse_errors.append((p, ln, tab, f"{e.msg} (行 {e.lineno})"))
                continue
            for x in w:
                key = f"{x.category.__name__}: {x.message}"
                warn_counter[key] += 1
                warn_example.setdefault(key, f"{p}:{ln}")

    print("== 语法解析失败 ==")
    print(*parse_errors, sep="\n   ") if parse_errors else print("   (无)")
    print("\n== 编译期告警 ==")
    if warn_counter:
        for k, c in warn_counter.most_common():
            print(f"   x{c:<4} {k}   e.g. {warn_example[k]}")
    else:
        print("   (无)")
    print()

    hits = collections.defaultdict(list)
    for p, ln, info, tab, src in blocks:
        try:
            tree = ast.parse(strip_magic(src))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    if a.name.split(".")[0] in REMOVED_MODULES or a.name in REMOVED_MODULES:
                        hits["移除的标准库 import"].append(f"{p}:{ln} {tab} -> import {a.name}")
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                if mod.split(".")[0] in REMOVED_MODULES or mod in REMOVED_MODULES:
                    hits["移除的标准库 import"].append(f"{p}:{ln} {tab} -> from {mod} import ...")
            elif isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
                base = node.value.id
                if base == "np" and node.attr in NUMPY_REMOVED:
                    hits["numpy 旧别名"].append(f"{p}:{ln} {tab} -> np.{node.attr}")
                elif (base, node.attr) in STDLIB_ATTR_RISKS:
                    hits["标准库弃用属性"].append(f"{p}:{ln} {tab} -> {base}.{node.attr}")
                elif base == "pd" and node.attr in PANDAS_ATTR_RISKS:
                    hits["pandas 弃用属性"].append(f"{p}:{ln} {tab} -> pd.{node.attr}")
                elif base == "plt" and node.attr in MATPLOTLIB_ATTR_RISKS:
                    hits["matplotlib 弃用属性"].append(f"{p}:{ln} {tab} -> plt.{node.attr}")
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                a = node.func
                if isinstance(a.value, ast.Name) and a.value.id == "df" and a.attr in PANDAS_ATTR_RISKS:
                    hits["pandas 弃用方法"].append(f"{p}:{ln} {tab} -> df.{a.attr}()")

    print("== AST 级 API 风险 ==")
    for k in ["移除的标准库 import", "numpy 旧别名", "标准库弃用属性",
              "pandas 弃用属性", "pandas 弃用方法", "matplotlib 弃用属性"]:
        v = hits.get(k, [])
        print(f"-- {k}: {len(v)}")
        for x in v[:12]:
            print("   ", x)
        if len(v) > 12:
            print(f"    ... 另有 {len(v) - 12} 处")

    print("\n== d2l 后端 API 面 ==")
    for f in sorted((ROOT / "d2l").glob("*.py")):
        tree = ast.parse(f.read_text(encoding="utf-8"))
        npattrs = collections.Counter()
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
                if node.value.id in ("np", "numpy"):
                    npattrs[node.attr] += 1
        print(f"   {f.name}: {len(npattrs)} 个 numpy 属性, top={npattrs.most_common(8)}")


if __name__ == "__main__":
    main()
```

### 本机实测复现命令

```bash
# L1 解释器层
python3.13 -W error::SyntaxWarning -m py_compile d2l/*.py setup.py
python3.13 ci/scripts/check_py313.py .

# L2 依赖层（干净 venv）
python3.13 -m venv /tmp/v313 && /tmp/v313/bin/pip install -e . && /tmp/v313/bin/pip check
/tmp/v313/bin/python -c "from d2l import torch as d2l; print(d2l.__version__)"
```

> 沙箱提示：本机 pip 在受限环境下会把临时目录创建拦成 `EEXIST`，需要 `TMPDIR=<真实可写目录> pip install --no-cache-dir`。这不是项目问题。
