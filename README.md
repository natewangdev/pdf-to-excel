# PDF 表格提取到 Excel

本项目使用 Python 实现扫描版 PDF 表格提取，支持以下流程：

1. 输入 PDF 若为竖版，先旋转为横版并输出 `input-out.pdf`；若已横版直接复制输出。
2. 对 `input-out.pdf` 做格线检测并输出单元格坐标 `cells.json`。
3. 在 `input-out.pdf` 绘制单元格框与索引，输出 `input-out-boxed.pdf`。
4. 将 `input-out.pdf` 按指定 DPI 转成 `input-out.png`，并输出缩放坐标 `cells-<dpi>.json`。
5. PaddleOCR 默认 GPU，若不可用自动回退 CPU，并打印实际模式。
6. 按坐标区域逐个 OCR 识别，逐条打印区域、识别文本、耗时日志，支持最大识别次数限制。
7. 识别结果按从上到下、从左到右写入 `input-out.xlsx`。

## 1. 安装 Python（清华源）

可从清华镜像下载 Windows Python 安装包：

- <https://mirrors.tuna.tsinghua.edu.cn/python/>

建议安装 Python 3.10 或 3.11，并勾选“Add python.exe to PATH”。

## 2. 创建虚拟环境并安装依赖（所有命令在虚拟环境执行）

以下示例为 PowerShell：

```powershell
# 在项目根目录执行（指定 Python 3.10）
py -3.10 -m venv .venv
.venv\Scripts\Activate.ps1

# 升级 pip（清华源）
python -m pip install -U pip -i https://pypi.tuna.tsinghua.edu.cn/simple

# 安装基础依赖（清华源）
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 安装 PaddlePaddle（按设备选择）

> `paddleocr` 需要 `paddlepaddle` 或 `paddlepaddle-gpu`。
>
> 重要：`paddlepaddle`（CPU）与 `paddlepaddle-gpu`（GPU）必须二选一，不能同时安装，否则可能出现导入冲突导致 OCR 初始化失败。

#### CPU 版本

```powershell
pip install paddlepaddle -i https://pypi.tuna.tsinghua.edu.cn/simple
```

#### GPU 版本（NVIDIA CUDA 环境）

```powershell
pip install paddlepaddle-gpu -i https://pypi.tuna.tsinghua.edu.cn/simple
```

#### 如果曾经混装，先清理再装

```powershell
pip uninstall -y paddlepaddle paddlepaddle-gpu
# 然后按上面 CPU/GPU 二选一重新安装
```

## 3. 运行

```powershell
python main.py --input .\input.pdf --out .\out --dpi 200 --detect-dpi 300 --max-recognitions 500 --lang ch --min-cell-width-px 20 --min-cell-height-px 20 --min-cell-area-px 400 --max-cell-width-ratio 0.95 --max-cell-height-ratio 0.95 --max-cell-area-ratio 0.6 --dedup-overlap-ratio 0.98 --container-min-children 4 --container-child-overlap-ratio 0.95
```

参数说明：

- `--input`：输入 PDF 文件（当前实现仅支持单页）。
- `--out`：输出目录。
- `--dpi`：`input-out.pdf` 转 PNG 的 DPI（默认 `200`）。
- `--detect-dpi`：表格检测使用的 PDF 渲染 DPI（默认 `300`）。
- `--max-recognitions`：最大 OCR 识别区域数（默认 `500`）。
- `--lang`：PaddleOCR 语言模型（默认 `ch`）。
- `--min-cell-width-px`：检测图中最小单元格宽度（默认 `15`）。
- `--min-cell-height-px`：检测图中最小单元格高度（默认 `15`）。
- `--min-cell-area-px`：检测图中最小单元格面积（默认 `225`）。
- `--max-cell-width-ratio`：检测图中最大单元格宽度占页面宽度比例（默认 `0.98`）。
- `--max-cell-height-ratio`：检测图中最大单元格高度占页面高度比例（默认 `0.98`）。
- `--max-cell-area-ratio`：检测图中最大单元格面积占页面面积比例（默认 `0.95`）。
- `--dedup-overlap-ratio`：两框在较小框上的重叠比例超过该值时，视为重复框并过滤较大的框（默认 `0.98`）。
- `--container-min-children`：某大框若包含至少这么多个小框，则视为外层容器框并过滤（默认 `4`）。
- `--container-child-overlap-ratio`：判断“小框被大框包含”的重叠比例阈值（默认 `0.95`）。

## 4. 输出文件

若输入是 `input.pdf`，输出目录会得到：

- `input-out.pdf`
- `cells.json`
- `input-out-boxed.pdf`
- `input-out.png`
- `cells-200.json`（当 `--dpi 200`）
- `input-out.xlsx`
