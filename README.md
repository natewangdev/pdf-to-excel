# pdf-to-excel

从 PDF 文件（包括扫描件）中提取表格数据，导出到 Excel 文件。PDF 中的每个表格对应 Excel 中的一个 Sheet。

## 功能特性

- 支持扫描件 / 图片型 PDF 的表格提取
- 基于 PaddleOCR (PP-OCRv4)，中文识别效果优秀
- 自动检测 PDF 中的多个表格
- 每个表格导出为独立的 Excel Sheet
- 支持指定页码范围处理
- 支持有边框和无边框表格检测

## 系统依赖

无需安装额外的系统级依赖。PDF 渲染使用 `pypdfium2`（由 `img2table` 自动安装），OCR 使用 PaddleOCR + PaddlePaddle。

> **重要**：安装依赖后请确保系统中只有一个 OpenCV 包（`opencv-contrib-python`），多版本共存会导致程序死锁。如遇到问题，运行：
> ```bash
> pip uninstall opencv-python opencv-contrib-python-headless opencv-python-headless -y
> pip install opencv-contrib-python==4.10.0.84
> ```

## 安装

```bash
# 克隆仓库
git clone https://github.com/your-username/pdf-to-excel.git
cd pdf-to-excel

# 创建并激活虚拟环境
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

# 安装 Python 依赖
pip install -r requirements.txt
```

## 使用方法

### 基本用法

```bash
# 提取 PDF 中的表格，输出为同名 .xlsx 文件
python -m pdf_to_excel input.pdf

# 指定输出文件路径
python -m pdf_to_excel input.pdf -o output.xlsx
```

### 高级选项

```bash
# 仅处理第 1、3、5 页
python -m pdf_to_excel input.pdf --pages 1,3,5

# 检测无边框表格
python -m pdf_to_excel input.pdf --borderless

# 设置 OCR 最低置信度（默认 50）
python -m pdf_to_excel input.pdf --min-confidence 30

# 指定 OCR 语言（默认中文 ch）
python -m pdf_to_excel input.pdf --lang en

# 显示详细日志
python -m pdf_to_excel input.pdf -v
```

### 全部参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `PDF_PATH` | PDF 文件路径（必需） | - |
| `-o, --output` | 输出 Excel 文件路径 | 与 PDF 同名 .xlsx |
| `-l, --lang` | OCR 识别语言 | `ch` |
| `--borderless` | 检测无边框表格 | 关闭 |
| `--min-confidence` | OCR 最低置信度 (0-99) | `50` |
| `--pages` | 要处理的页码，逗号分隔 | 全部页 |
| `-v, --verbose` | 显示详细日志 | 关闭 |

## 项目结构

```
pdf-to-excel/
├── README.md
├── requirements.txt
└── pdf_to_excel/
    ├── __init__.py        # 包定义
    ├── __main__.py        # python -m 入口
    ├── cli.py             # 命令行接口
    ├── extractor.py       # PDF 表格检测 + OCR 提取
    ├── ocr_adapter.py     # PaddleOCR 适配 img2table 接口
    └── exporter.py        # Excel 导出
```

## 注意事项

- `img2table` 主要依赖表格的可见边框线来检测表格结构。如果表格无边框，请使用 `--borderless` 参数
- 首次运行时 PaddleOCR 会自动下载模型文件，需要网络连接
- 扫描件的识别效果与扫描质量密切相关，建议使用 300 DPI 以上的扫描件
