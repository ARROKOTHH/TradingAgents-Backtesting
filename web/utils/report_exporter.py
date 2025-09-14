#!/usr/bin/env python3
"""
报告导出工具
支持将分析结果导出为多种格式
"""

import streamlit as st
import json
import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import tempfile
import base64

# 导入日志模块
from tradingagents.utils.logging_manager import get_logger
logger = get_logger('web')

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 导入相关库
try:
    import pypandoc
    PANDOC_AVAILABLE = True
except ImportError:
    PANDOC_AVAILABLE = False
    logger.warning("pypandoc not found. Word and PDF export will be disabled.")

EXPORT_AVAILABLE = True

class ReportExporter:
    """报告导出器"""

    def __init__(self):
        self.export_available = EXPORT_AVAILABLE
        self.pandoc_available = PANDOC_AVAILABLE

    def _clean_text_for_markdown(self, text: Any) -> str:
        if not text: return "N/A"
        return str(text).replace('---', '—').replace('...', '…')

    def generate_markdown_report(self, results: Dict[str, Any], report_type: str = "完整报告") -> str:
        stock_symbol = self._clean_text_for_markdown(results.get('stock_symbol', 'N/A'))
        decision = results.get('decision', {})
        state = results.get('state', {})
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        md_content = f"# {stock_symbol} 股票分析报告 ({report_type})\n\n"
        md_content += f"**生成时间**: {timestamp}\n\n"
        md_content += "## 🎯 投资决策摘要\n"
        
        action = self._clean_text_for_markdown(decision.get('action', 'N/A')).upper()
        target_price = self._clean_text_for_markdown(decision.get('target_price', 'N/A'))
        reasoning = self._clean_text_for_markdown(decision.get('reasoning', '暂无分析推理'))

        md_content += f"""
| 指标 | 数值 |
|:---|:---|
| **投资建议** | {action} |
| **置信度** | {decision.get('confidence', 0):.1%} |
| **风险评分** | {decision.get('risk_score', 0):.1%} |
| **目标价位** | {target_price} |

### 分析推理
{reasoning}
---
"""
        md_content += "\n## 📊 核心分析报告\n"
        user_selected_analysts = results.get('analysts', [])
        analyst_map = {
            'market': ('market_report', '📈 市场技术分析'),
            'fundamentals': ('fundamentals_report', '💰 基本面分析'),
            'social': ('sentiment_report', '💭 市场情绪分析'),
            'news': ('news_report', '📰 新闻事件分析'),
        }
        for analyst_key in user_selected_analysts:
            if analyst_key in analyst_map:
                state_key, title = analyst_map[analyst_key]
                md_content += f"\n### {title}\n\n"
                content = state.get(state_key, "暂无数据")
                md_content += f"{self._clean_text_for_markdown(str(content))}\n\n"

        if 'trader_investment_plan' in state and state['trader_investment_plan']:
            md_content += "\n---\n\n## 💼 交易团队计划\n\n"
            md_content += f"{self._clean_text_for_markdown(state['trader_investment_plan'])}\n\n"

        if report_type == "完整报告":
            md_content += self._add_full_report_details(state)

        md_content += f"""
---
## ⚠️ 重要风险提示
**投资风险提示**:
- **仅供参考**: 本分析结果仅供参考，不构成投资建议
- **投资风险**: 股票投资有风险，可能导致本金损失
- **理性决策**: 请结合多方信息进行理性投资决策
- **专业咨询**: 重大投资决策建议咨询专业财务顾问
- **自担风险**: 投资决策及其后果由投资者自行承担
---
*报告生成时间: {timestamp}*
"""
        return md_content

    def _add_full_report_details(self, state: Dict[str, Any]) -> str:
        full_content = ""
        if 'investment_debate_state' in state and state['investment_debate_state']:
            full_content += "\n---\n\n## 🔬 研究团队决策\n\n"
            debate_state = state['investment_debate_state']
            if debate_state.get('bull_history'):
                full_content += f"### 📈 多头研究员分析\n\n{self._clean_text_for_markdown(debate_state['bull_history'])}\n\n"
            if debate_state.get('bear_history'):
                full_content += f"### 📉 空头研究员分析\n\n{self._clean_text_for_markdown(debate_state['bear_history'])}\n\n"
            if debate_state.get('judge_decision'):
                full_content += f"### 🎯 研究经理综合决策\n\n{self._clean_text_for_markdown(debate_state['judge_decision'])}\n\n"
        return full_content

    def export_report(self, results: Dict[str, Any], format_type: str, report_type: str) -> Optional[bytes]:
        if not self.export_available:
            st.error("导出功能不可用")
            return None
        try:
            md_content = self.generate_markdown_report(results, report_type)
            if format_type == 'markdown':
                return md_content.encode('utf-8')
            
            if not self.pandoc_available:
                st.error(f"Pandoc不可用，无法生成{format_type.upper()}文档")
                return None

            with tempfile.NamedTemporaryFile(suffix=f'.{format_type}', delete=False) as tmp_file:
                output_file = tmp_file.name
            
            pypandoc.convert_text(md_content, format_type, format='markdown', outputfile=output_file)
            
            with open(output_file, 'rb') as f:
                content = f.read()
            os.unlink(output_file)
            return content
        except Exception as e:
            st.error(f"导出失败: {e}")
            return None

report_exporter = ReportExporter()

def render_export_buttons(results: Dict[str, Any]):
    if not results:
        return

    st.markdown("---")
    st.subheader("📤 导出报告")

    if not report_exporter.export_available:
        st.warning("导出功能依赖包缺失")
        return

    report_type = st.selectbox(
        "选择报告类型:",
        options=["完整报告", "策略引导报告"],
        index=0,
        key="report_type_selector",
        help="**完整报告**: 包含所有分析师的详细分析和辩论过程。\n\n**策略引导报告**: 精简版，只包含最终决策和用于生成策略的核心信息。"
    )

    stock_symbol = results.get('stock_symbol', 'analysis')
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    type_suffix = "full" if report_type == "完整报告" else "strategy_guided"
    
    col1, col2, col3 = st.columns(3)

    def handle_export(format_type: str):
        extension = {"markdown": "md", "docx": "docx", "pdf": "pdf"}[format_type]
        filename = f"{stock_symbol}_analysis_{timestamp}_{type_suffix}.{extension}"
        
        with st.spinner(f"正在生成 {format_type.upper()}..."):
            try:
                content_bytes = report_exporter.export_report(results, format_type, report_type)
                if content_bytes:
                    project_root = Path(__file__).parent.parent.parent
                    save_dir = project_root / "analysis reports"
                    save_dir.mkdir(exist_ok=True)
                    file_path = save_dir / filename
                    with open(file_path, "wb") as f:
                        f.write(content_bytes)
                    st.success(f"✅ {report_type}已保存！")
                    st.info(f"路径: `{file_path}`")
                else:
                    st.error(f"生成 {format_type.upper()} 失败")
            except Exception as e:
                st.error(f"导出失败: {e}")

    with col1:
        if st.button("📄 保存为 Markdown", key="save_md"):
            handle_export("markdown")
    with col2:
        if st.button("📝 保存为 Word", key="save_docx"):
            if not report_exporter.pandoc_available: st.error("Pandoc不可用")
            else: handle_export("docx")
    with col3:
        if st.button("📊 保存为 PDF", key="save_pdf"):
            if not report_exporter.pandoc_available: st.error("Pandoc不可用")
            else: handle_export("pdf")