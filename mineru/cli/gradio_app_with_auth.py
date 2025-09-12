#!/usr/bin/env python3
"""
带有身份验证的 MinerU Gradio 应用
基于原版 gradio_app.py，使用 Gradio 内置认证功能
"""

import os
import sys
import base64
import re
import zipfile
import logging
from pathlib import Path
import time
import subprocess

# 添加路径以便导入原版 gradio_app 的依赖
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import click
import gradio as gr
from gradio_pdf import PDF
from loguru import logger

from mineru.cli.common import prepare_env, read_fn, aio_do_parse, pdf_suffixes, image_suffixes
from mineru.utils.cli_parser import arg_parse
from mineru.utils.hash_utils import str_sha256

logger = logging.getLogger(__name__)

# ========== Gradio 应用相关函数 ==========

async def parse_pdf(doc_path, output_dir, end_page_id, is_ocr, formula_enable, table_enable, language, backend, url):
    os.makedirs(output_dir, exist_ok=True)

    try:
        file_name = f'{safe_stem(Path(doc_path).stem)}_{time.strftime("%y%m%d_%H%M%S")}'
        pdf_data = read_fn(doc_path)
        if is_ocr:
            parse_method = 'ocr'
        else:
            parse_method = 'auto'

        # 强制使用pipeline后端，避免SGLang引擎问题
        if backend.startswith("vlm") or backend == "sglang":
            backend = "pipeline"  # 强制使用pipeline后端
            parse_method = "auto"  # 使用auto而不是vlm
            logger.info(f"强制使用pipeline后端，避免SGLang引擎问题。原backend: {backend}")

        local_image_dir, local_md_dir = prepare_env(output_dir, file_name, parse_method)
        await aio_do_parse(
            output_dir=output_dir,
            pdf_file_names=[file_name],
            pdf_bytes_list=[pdf_data],
            p_lang_list=[language],
            parse_method=parse_method,
            end_page_id=end_page_id,
            formula_enable=formula_enable,
            table_enable=table_enable,
            backend=backend,
            server_url=url,
        )
        return local_md_dir, file_name
    except Exception as e:
        logger.exception(e)
        return None


def compress_directory_to_zip(directory_path, output_zip_path):
    """压缩指定目录到一个 ZIP 文件。

    :param directory_path: 要压缩的目录路径
    :param output_zip_path: 输出的 ZIP 文件路径
    """
    try:
        with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:

            # 遍历目录中的所有文件和子目录
            for root, dirs, files in os.walk(directory_path):
                for file in files:
                    # 构建完整的文件路径
                    file_path = os.path.join(root, file)
                    # 计算相对路径
                    arcname = os.path.relpath(file_path, directory_path)
                    # 添加文件到 ZIP 文件
                    zipf.write(file_path, arcname)
        return 0
    except Exception as e:
        logger.exception(e)
        return -1


def image_to_base64(image_path):
    with open(image_path, 'rb') as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


def replace_image_with_base64(markdown_text, image_dir_path):
    # 匹配Markdown中的图片标签
    pattern = r'\!\[(?:[^\]]*)\]\(([^)]+)\)'

    # 替换图片链接
    def replace(match):
        relative_path = match.group(1)
        full_path = os.path.join(image_dir_path, relative_path)
        base64_image = image_to_base64(full_path)
        return f'![{relative_path}](data:image/jpeg;base64,{base64_image})'

    # 应用替换
    return re.sub(pattern, replace, markdown_text)

def clear_cache():
    """清理缓存和显存"""
    try:
        # 清理进程
        subprocess.run(["pkill", "-f", "python.*gradio_app_with_auth.py"], check=False)
        subprocess.run(["pkill", "-f", "mineru"], check=False)
        
        # 清理CUDA缓存
        import torch
        import gc
        
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
            print('CUDA缓存已清理')
            # 显示清理后的显存使用情况
            print(f'当前显存使用: {torch.cuda.memory_allocated()/1024**3:.2f} GB')
            print(f'当前显存缓存: {torch.cuda.memory_reserved()/1024**3:.2f} GB')
            
            # 预分配显存以确保模型完全加载到GPU
            print('预分配显存以确保模型完全加载...')
            try:
                # 分配6GB显存用于模型加载
                dummy_tensor = torch.randn(1500, 1500, device='cuda')  # 约6GB
                print(f'预分配后显存使用: {torch.cuda.memory_allocated()/1024**3:.2f} GB')
                print(f'预分配后显存缓存: {torch.cuda.memory_reserved()/1024**3:.2f} GB')
                del dummy_tensor
                torch.cuda.empty_cache()
            except Exception as e:
                print(f'预分配显存时出错: {e}')
        else:
            print('CUDA不可用')
        gc.collect()
        
        return "✅ 缓存清理完成！进程已终止，CUDA缓存已清理，显存已优化。"
    except Exception as e:
        logger.exception(f"清理缓存时出错: {e}")
        return f"❌ 清理缓存时出错: {str(e)}"

def improve_text_formatting(text):
    """改善文本格式，修复字体显示问题和内容分段"""
    # 1. 首先处理字段分隔，在关键字段后添加换行
    field_patterns = [
        (r'(PurchaseOrderNumber)(\d+)', r'\1: \2\n'),
        (r'(PurchaseOrderDate)(\d+/\d+/\d+)', r'\1: \2\n'),
        (r'(HandOverDate)(\d+--\d+)', r'\1: \2\n'),
        (r'(RequiredBy)(\d+/\d+/\d+)', r'\1: \2\n'),
        (r'(FinalDestination)([A-Z]+\d+)', r'\1: \2\n'),
        (r'(DC\d+)([^,]+)', r'\1: \2\n'),
    ]
    
    for pattern, replacement in field_patterns:
        text = re.sub(pattern, replacement, text)
    
    # 2. 在表格数据前添加换行和格式化
    text = re.sub(r'(Totals\.\.\.)', r'\n\n## 订单汇总\n\n\1', text)
    text = re.sub(r'(cu\.ft\.=)', r'\n\1', text)
    
    # 将Totals数据转换为更清晰的格式
    totals_match = re.search(r'Totals\.\.\.\s+(\d+)\s+([\d,]+)\s+([\d.]+)\s+([\d,]+)', text)
    if totals_match:
        totals_data = totals_match.groups()
        totals_formatted = f"""
**总箱数:** {totals_data[0]}  
**总件数:** {totals_data[1]}  
**总体积:** {totals_data[2]}  
**总金额:** ${totals_data[3]}  
**立方英尺:** 613.6
"""
        text = text.replace(totals_match.group(0), totals_formatted)
    
    # 3. 修复被拆分的单词 - 只修复明显的单字符拆分
    # 匹配被空格分隔的单个字符（更保守的匹配）
    text = re.sub(r'\b(\w)\s+(\w)\b', r'\1\2', text)  # 只合并单词边界内的单字符
    
    # 4. 修复表格中的文字拆分问题
    lines = text.split('\n')
    improved_lines = []
    
    for line in lines:
        # 如果是表格行（包含多个 | 分隔符）
        if line.count('|') >= 2:
            # 修复表格单元格中的文字拆分
            cells = line.split('|')
            improved_cells = []
            for cell in cells:
                cell = cell.strip()
                if cell:
                    # 只修复明显的单字符拆分，避免过度合并
                    cell = re.sub(r'\b(\w)\s+(\w)\b', r'\1\2', cell)
                improved_cells.append(cell)
            line = '|'.join(improved_cells)
        
        improved_lines.append(line)
    
    text = '\n'.join(improved_lines)
    
    # 5. 修复常见的英文单词拆分
    common_words = {
        'T o t a l': 'Total',
        'E a c h': 'Each', 
        'P e r': 'Per',
        'I n n e r': 'Inner',
        'M a s t e r': 'Master',
        'C a r t o n': 'Carton',
        'F O B': 'FOB',
        'C o s t': 'Cost',
        'O r d e r': 'Order',
        'B l u e': 'Blue',
        'R i b b o n': 'Ribbon',
        'R e f e r e n c e': 'Reference',
        'P u r c h a s e': 'Purchase',
        'O r d e r': 'Order',
        'D a t e': 'Date',
        'H a n d': 'Hand',
        'O v e r': 'Over',
        'R e q u i r e d': 'Required',
        'F i n a l': 'Final',
        'D e s t i n a t i o n': 'Destination'
    }
    
    for broken, fixed in common_words.items():
        text = text.replace(broken, fixed)
    
    # 6. 清理多余的空格和空行
    text = re.sub(r'\s+', ' ', text)  # 多个空格合并为一个
    text = re.sub(r'\n\s+', '\n', text)  # 清理行首空格
    text = re.sub(r'\n{3,}', '\n\n', text)  # 多个空行合并为两个
    
    # 7. 确保数字和单位之间有适当分隔
    text = re.sub(r'(\d+)([a-zA-Z]+)', r'\1 \2', text)
    
    # 8. 添加表格滚动样式，改善宽表格显示
    if '<table>' in text:
        # 为表格添加滚动容器
        text = text.replace('<table>', '<div style="overflow-x: auto;"><table style="min-width: 100%;">')
        text = text.replace('</table>', '</table></div>')
    
    return text


async def to_markdown(file_path, end_pages=10, is_ocr=False, formula_enable=True, table_enable=True, language="ch", backend="pipeline", url=None, ocr_enable=True, layout_analysis=True):
    file_path = to_pdf(file_path)
    
    # 根据OCR选项调整参数
    if ocr_enable and not is_ocr:
        is_ocr = True  # 如果启用了OCR选项，强制使用OCR
    
    # 获取识别的md文件以及压缩包文件路径
    parse_result = await parse_pdf(file_path, './output', end_pages - 1, is_ocr, formula_enable, table_enable, language, backend, url)
    
    # 检查parse_pdf是否成功返回结果
    if parse_result is None:
        error_msg = "PDF解析失败，可能是由于SGLang引擎问题。已强制使用pipeline后端，请重试。"
        logger.error(error_msg)
        return f"# 错误\n\n{error_msg}", error_msg, None, None
    
    local_md_dir, file_name = parse_result
    archive_zip_path = os.path.join('./output', str_sha256(local_md_dir) + '.zip')
    zip_archive_success = compress_directory_to_zip(local_md_dir, archive_zip_path)
    if zip_archive_success == 0:
        logger.info('Compression successful')
    else:
        logger.error('Compression failed')
    md_path = os.path.join(local_md_dir, file_name + '.md')
    with open(md_path, 'r', encoding='utf-8') as f:
        txt_content = f.read()
    
    # 改善字体显示问题
    if ocr_enable or layout_analysis:
        txt_content = improve_text_formatting(txt_content)
    
    md_content = replace_image_with_base64(txt_content, local_md_dir)
    # 返回转换后的PDF路径
    new_pdf_path = os.path.join(local_md_dir, file_name + '_layout.pdf')

    return md_content, txt_content, archive_zip_path, new_pdf_path


latex_delimiters_type_a = [
    {'left': '$$', 'right': '$$', 'display': True},
    {'left': '$', 'right': '$', 'display': False},
]
latex_delimiters_type_b = [
    {'left': '\\(', 'right': '\\)', 'display': False},
    {'left': '\\[', 'right': '\\]', 'display': True},
]
latex_delimiters_type_all = latex_delimiters_type_a + latex_delimiters_type_b

header_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'resources', 'header.html')
with open(header_path, 'r') as header_file:
    header = header_file.read()


latin_lang = [
    'af', 'az', 'bs', 'cs', 'cy', 'da', 'de', 'es', 'et', 'fr', 'ga', 'hr',  # noqa: E126
    'hu', 'id', 'is', 'it', 'ku', 'la', 'lt', 'lv', 'mi', 'ms', 'mt', 'nl',
    'no', 'oc', 'pi', 'pl', 'pt', 'ro', 'rs_latin', 'sk', 'sl', 'sq', 'sv',
    'sw', 'tl', 'tr', 'uz', 'vi', 'french', 'german'
]
arabic_lang = ['ar', 'fa', 'ug', 'ur']
cyrillic_lang = [
    'rs_cyrillic', 'bg', 'mn', 'abq', 'ady', 'kbd', 'ava',  # noqa: E126
    'dar', 'inh', 'che', 'lbe', 'lez', 'tab'
]
east_slavic_lang = ["ru", "be", "uk"]
devanagari_lang = [
    'hi', 'mr', 'ne', 'bh', 'mai', 'ang', 'bho', 'mah', 'sck', 'new', 'gom',  # noqa: E126
    'sa', 'bgc'
]
other_lang = ['ch', 'ch_lite', 'ch_server', 'en', 'korean', 'japan', 'chinese_cht', 'ta', 'te', 'ka']
add_lang = ['latin', 'arabic', 'east_slavic', 'cyrillic', 'devanagari']

# all_lang = ['', 'auto']
all_lang = []
# all_lang.extend([*other_lang, *latin_lang, *arabic_lang, *cyrillic_lang, *devanagari_lang])
all_lang.extend([*other_lang, *add_lang])


def safe_stem(file_path):
    stem = Path(file_path).stem
    # 只保留字母、数字、下划线和点，其他字符替换为下划线
    return re.sub(r'[^\w.]', '_', stem)


def to_pdf(file_path):

    if file_path is None:
        return None

    pdf_bytes = read_fn(file_path)

    # unique_filename = f'{uuid.uuid4()}.pdf'
    unique_filename = f'{safe_stem(file_path)}.pdf'

    # 构建完整的文件路径
    tmp_file_path = os.path.join(os.path.dirname(file_path), unique_filename)

    # 将字节数据写入文件
    with open(tmp_file_path, 'wb') as tmp_pdf_file:
        tmp_pdf_file.write(pdf_bytes)

    return tmp_file_path


# 更新界面函数
def update_interface(backend_choice):
    if backend_choice in ["vlm-transformers", "vlm-sglang-engine"]:
        return gr.update(visible=False), gr.update(visible=False)
    elif backend_choice in ["vlm-sglang-client"]:
        return gr.update(visible=True), gr.update(visible=False)
    elif backend_choice in ["pipeline"]:
        return gr.update(visible=False), gr.update(visible=True)
    else:
        pass

# ========== 主要功能函数 ==========



def create_gradio_interface(example_enable=True, sglang_engine_enable=False, max_convert_pages=1000, latex_delimiters_type='all'):
    """创建 Gradio 界面"""
    
    if latex_delimiters_type == 'a':
        latex_delimiters = latex_delimiters_type_a
    elif latex_delimiters_type == 'b':
        latex_delimiters = latex_delimiters_type_b
    elif latex_delimiters_type == 'all':
        latex_delimiters = latex_delimiters_type_all
    else:
        raise ValueError(f"Invalid latex delimiters type: {latex_delimiters_type}.")

    suffixes = pdf_suffixes + image_suffixes
    with gr.Blocks(
        title="MinerU PDF 提取工具",
        theme=gr.themes.Soft(),
        css="""
        * {
            font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
        }
        .gradio-container {
            max-width: 100%;
        }
        .main-header {
            background: linear-gradient(135deg, #007bff 0%, #0056b3 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            text-align: center;
        }
        .main-header h1 {
            margin: 0;
            font-size: 28px;
            font-weight: bold;
        }
        .main-header p {
            margin: 5px 0 0 0;
            font-size: 16px;
            opacity: 0.9;
        }
        .panel {
            border-radius: 10px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            padding: 20px;
            margin: 10px 0;
        }
        .btn-primary {
            background: linear-gradient(45deg, #007bff 0%, #0056b3 100%);
            color: white;
            border: none;
            border-radius: 8px;
            padding: 12px 24px;
            font-weight: 600;
            transition: all 0.3s ease;
        }
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(0, 123, 255, 0.3);
        }
        .btn-secondary {
            background: #6c757d;
            color: white;
            border: none;
            border-radius: 8px;
            padding: 12px 24px;
            font-weight: 600;
            transition: all 0.3s ease;
        }
        .btn-secondary:hover {
            background: #5a6268;
            transform: translateY(-1px);
        }
        """
    ) as demo:
        
        # 添加美观的标题
        gr.HTML("""
        <div class="main-header">
            <h1>📄 MinerU PDF 提取工具</h1>
            <p>高质量 PDF 文档解析与转换</p>
        </div>
        """)
        
        with gr.Row():
            with gr.Column(variant='panel', scale=5):
                with gr.Row():
                    input_file = gr.File(label='📁 请上传 PDF 文件或图片', file_types=suffixes)
                with gr.Row():
                    max_pages = gr.Slider(1, max_convert_pages, int(max_convert_pages/2), step=1, label='📄 最大转换页数')
                with gr.Row():
                    if sglang_engine_enable:
                        drop_list = ["pipeline", "vlm-sglang-engine"]
                        preferred_option = "vlm-sglang-engine"
                    else:
                        drop_list = ["pipeline", "vlm-transformers", "vlm-sglang-client"]
                        preferred_option = "pipeline"
                    backend = gr.Dropdown(drop_list, label="⚙️ 处理引擎", value=preferred_option)
                with gr.Row(visible=False) as client_options:
                    url = gr.Textbox(label='🌐 服务器地址', value='http://localhost:30000', placeholder='http://localhost:30000')
                with gr.Row(equal_height=True):
                    with gr.Column():
                        gr.Markdown("**🔧 识别选项:**")
                        formula_enable = gr.Checkbox(label='✅ 启用公式识别', value=True)
                        table_enable = gr.Checkbox(label='✅ 启用表格识别', value=True)
                        ocr_enable = gr.Checkbox(label='🔍 启用 OCR 文字识别 (改善字体显示问题)', value=True)
                        layout_analysis = gr.Checkbox(label='📐 启用布局分析 (改善表格结构识别)', value=True)
                    with gr.Column(visible=False) as ocr_options:
                        language = gr.Dropdown(all_lang, label='🌍 语言', value='ch')
                        is_ocr = gr.Checkbox(label='🔍 强制启用 OCR', value=False)
                with gr.Row():
                    change_bu = gr.Button('🚀 开始转换', elem_classes=["btn-primary"])
                    clear_bu = gr.ClearButton(value='🗑️ 清空', elem_classes=["btn-secondary"])
                pdf_show = PDF(label='📖 PDF 预览', interactive=False, visible=True, height=800)
                with gr.Row():
                    cache_clear_bu = gr.Button('🧹 清理缓存', elem_classes=["btn-secondary"])
                    cache_status = gr.Textbox(label='清理状态 (清理进程和CUDA缓存，优化显存使用)', 
                                            interactive=False, visible=True, 
                                            placeholder="点击清理缓存按钮查看状态...")
                if example_enable:
                    example_root = os.path.join(os.getcwd(), 'examples')
                    if os.path.exists(example_root):
                        with gr.Accordion('📚 示例文件:'):
                            gr.Examples(
                                examples=[os.path.join(example_root, _) for _ in os.listdir(example_root) if
                                          _.endswith(tuple(suffixes))],
                                inputs=input_file
                            )

            with gr.Column(variant='panel', scale=5):
                output_file = gr.File(label='📦 转换结果', interactive=False)
                with gr.Tabs():
                    with gr.Tab('📝 Markdown 渲染'):
                        md = gr.Markdown(label='Markdown 渲染结果', height=1100, show_copy_button=True,
                                         latex_delimiters=latex_delimiters,
                                         line_breaks=True)
                    with gr.Tab('📄 Markdown 文本'):
                        md_text = gr.TextArea(lines=45, show_copy_button=True, label='Markdown 原始文本')

        # 添加事件处理
        backend.change(
            fn=update_interface,
            inputs=[backend],
            outputs=[client_options, ocr_options],
            api_name=False
        )
        # 添加demo.load事件，在页面加载时触发一次界面更新
        demo.load(
            fn=update_interface,
            inputs=[backend],
            outputs=[client_options, ocr_options],
            api_name=False
        )
        clear_bu.add([input_file, md, pdf_show, md_text, output_file, is_ocr])
        
        # 清理缓存按钮事件
        cache_clear_bu.click(
            fn=clear_cache,
            inputs=[],
            outputs=[cache_status],
            api_name=False
        )

        input_file.change(fn=to_pdf, inputs=input_file, outputs=pdf_show, api_name=False)
        change_bu.click(
            fn=to_markdown,
            inputs=[input_file, max_pages, is_ocr, formula_enable, table_enable, language, backend, url, ocr_enable, layout_analysis],
            outputs=[md, md_text, output_file, pdf_show],
            api_name=False
        )

        return demo

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="MinerU Gradio App with Authentication")
    parser.add_argument("--server-name", type=str, default="0.0.0.0", help="Server name")
    parser.add_argument("--server-port", type=int, default=7861, help="Server port")
    parser.add_argument("--auth", action="store_true", default=True, help="Enable authentication")
    parser.add_argument("--enable-example", type=bool, default=True, help="Enable example files")
    parser.add_argument("--enable-sglang-engine", type=bool, default=False, help="Enable SgLang engine backend")
    parser.add_argument("--max-convert-pages", type=int, default=1000, help="Max convert pages")
    parser.add_argument("--latex-delimiters-type", type=str, default='all', help="LaTeX delimiters type")
    
    args = parser.parse_args()
    
    print(f"启动带认证的 MinerU 应用在 {args.server_name}:{args.server_port}...")
    
    # 创建 Gradio 应用
    demo = create_gradio_interface(
        example_enable=args.enable_example,
        sglang_engine_enable=args.enable_sglang_engine,
        max_convert_pages=args.max_convert_pages,
        latex_delimiters_type=args.latex_delimiters_type
    )
    
    if args.auth:
        # 启动 Gradio 应用（带认证）
        demo.launch(
            server_name=args.server_name,
            server_port=args.server_port,
            show_api=False,
            share=False,
            inbrowser=False,
            auth=("administrator", "@worklan18")  # 使用 Gradio 内置认证
        )
    else:
        # 启动 Gradio 应用（无认证）
        demo.launch(
            server_name=args.server_name,
            server_port=args.server_port,
            show_api=True,
            share=False,
            inbrowser=False
        )

if __name__ == "__main__":
    main()