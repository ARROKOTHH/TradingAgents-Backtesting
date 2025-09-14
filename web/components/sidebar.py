"""
侧边栏组件
"""

import streamlit as st
import os
import logging
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from web.utils.persistence import load_model_selection, save_model_selection

logger = logging.getLogger(__name__)

def render_sidebar():
    """渲染侧边栏配置"""

    # 添加localStorage支持的JavaScript
    st.markdown("""
    <script>
    // 保存到localStorage
    function saveToLocalStorage(key, value) {
        localStorage.setItem('tradingagents_' + key, value);
        console.log('Saved to localStorage:', key, value);
    }

    // 从localStorage读取
    function loadFromLocalStorage(key, defaultValue) {
        const value = localStorage.getItem('tradingagents_' + key);
        console.log('Loaded from localStorage:', key, value || defaultValue);
        return value || defaultValue;
    }

    // 页面加载时恢复设置
    window.addEventListener('load', function() {
        console.log('Page loaded, restoring settings...');
    });
    </script>
    """, unsafe_allow_html=True)

    # 优化侧边栏样式
    st.markdown("""
    <style>
    /* 优化侧边栏宽度 - 调整为320px */
    section[data-testid="stSidebar"] {
        width: 320px !important;
        min-width: 320px !important;
        max-width: 320px !important;
    }

    /* 优化侧边栏内容容器 */
    section[data-testid="stSidebar"] > div {
        width: 320px !important;
        min-width: 320px !important;
        max-width: 320px !important;
    }

    /* 强制减少侧边栏内边距 - 多种选择器确保生效 */
    section[data-testid="stSidebar"] .block-container,
    section[data-testid="stSidebar"] > div > div,
    .css-1d391kg,
    .css-1lcbmhc,
    .css-1cypcdb {
        padding-top: 0.75rem !important;
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
        padding-bottom: 0.75rem !important;
    }

    /* 侧边栏内所有元素的边距控制 */
    section[data-testid="stSidebar"] * {
        box-sizing: border-box !important;
    }

    /* 优化selectbox容器 */
    section[data-testid="stSidebar"] .stSelectbox {
        margin-bottom: 0.4rem !important;
        width: 100% !important;
    }

    /* 优化selectbox下拉框 - 调整为适合320px */
    section[data-testid="stSidebar"] .stSelectbox > div > div,
    section[data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] {
        width: 100% !important;
        min-width: 260px !important;
        max-width: 280px !important;
    }

    /* 优化下拉框选项文本 */
    section[data-testid="stSidebar"] .stSelectbox label {
        font-size: 0.85rem !important;
        font-weight: 600 !important;
        margin-bottom: 0.2rem !important;
    }

    /* 优化文本输入框 */
    section[data-testid="stSidebar"] .stTextInput > div > div > input {
        font-size: 0.8rem !important;
        padding: 0.3rem 0.5rem !important;
        width: 100% !important;
    }

    /* 优化按钮样式 */
    section[data-testid="stSidebar"] .stButton > button {
        width: 100% !important;
        font-size: 0.8rem !important;
        padding: 0.3rem 0.5rem !important;
        margin: 0.1rem 0 !important;
        border-radius: 0.3rem !important;
    }

    /* 优化标题样式 */
    section[data-testid="stSidebar"] h3 {
        font-size: 1rem !important;
        margin-bottom: 0.5rem !important;
        margin-top: 0.3rem !important;
        padding: 0 !important;
    }

    /* 优化info框样式 */
    section[data-testid="stSidebar"] .stAlert {
        padding: 0.4rem !important;
        margin: 0.3rem 0 !important;
        font-size: 0.75rem !important;
    }

    /* 优化markdown文本 */
    section[data-testid="stSidebar"] .stMarkdown {
        margin-bottom: 0.3rem !important;
        padding: 0 !important;
    }

    /* 优化分隔线 */
    section[data-testid="stSidebar"] hr {
        margin: 0.75rem 0 !important;
    }

    /* 确保下拉框选项完全可见 - 调整为适合320px */
    .stSelectbox [data-baseweb="select"] {
        min-width: 260px !important;
        max-width: 280px !important;
    }

    /* 优化下拉框选项列表 */
    .stSelectbox [role="listbox"] {
        min-width: 260px !important;
        max-width: 290px !important;
    }

    /* 额外的边距控制 - 确保左右边距减小 */
    .sidebar .element-container {
        padding: 0 !important;
        margin: 0.2rem 0 !important;
    }

    /* 强制覆盖默认样式 */
    .css-1d391kg .element-container {
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
    }
    </style>
    """, unsafe_allow_html=True)

    with st.sidebar:
        # 使用组件来从localStorage读取并初始化session state
        st.markdown("""
        <div id="localStorage-reader" style="display: none;">
            <script>
            // 从localStorage读取设置并发送给Streamlit
            const provider = loadFromLocalStorage('llm_provider', 'dashscope');
            const category = loadFromLocalStorage('model_category', 'openai');
            const model = loadFromLocalStorage('llm_model', '');

            // 通过自定义事件发送数据
            window.parent.postMessage({
                type: 'localStorage_data',
                provider: provider,
                category: category,
                model: model
            }, '*');
            </script>
        </div>
        """, unsafe_allow_html=True)

        # 从持久化存储加载配置
        saved_config = load_model_selection()

        # Initialize session state, prioritizing saved config
        if 'llm_provider' not in st.session_state:
            st.session_state.llm_provider = saved_config.get('provider', 'dashscope')
        if 'model_category' not in st.session_state:
            st.session_state.model_category = saved_config.get('category', 'openai')
        if 'quick_think_llm' not in st.session_state:
            st.session_state.quick_think_llm = saved_config.get('quick_model') or saved_config.get('model', 'qwen-turbo')
        if 'deep_think_llm' not in st.session_state:
            st.session_state.deep_think_llm = saved_config.get('deep_model') or saved_config.get('model', 'qwen-plus-latest')

        # 显示当前session state状态（调试用）
        logger.debug(f"🔍 [Session State] 当前状态 - provider: {st.session_state.llm_provider}, category: {st.session_state.model_category}, quick_model: {st.session_state.quick_think_llm}, deep_model: {st.session_state.deep_think_llm}")

        # AI模型配置
        st.markdown("### 🧠 AI模型配置")

        # LLM提供商选择
        llm_provider = st.selectbox(
            "LLM提供商",
            options=["dashscope", "deepseek", "google", "openai", "openrouter", "siliconflow","custom_openai"],
            index=["dashscope", "deepseek", "google", "openai", "openrouter","siliconflow", "custom_openai"].index(st.session_state.llm_provider) if st.session_state.llm_provider in ["siliconflow", "dashscope", "deepseek", "google", "openai", "openrouter", "custom_openai"] else 0,
            format_func=lambda x: {
                "dashscope": "🇨🇳 阿里百炼",
                "deepseek": "🚀 DeepSeek V3",
                "google": "🌟 Google AI",
                "openai": "🤖 OpenAI",
                "openrouter": "🌐 OpenRouter",
                "siliconflow": "🇨🇳 硅基流动",
                "custom_openai": "🔧 自定义OpenAI端点"
            }[x],
            help="选择AI模型提供商",
            key="llm_provider_select"
        )

        # 更新session state和持久化存储
        if st.session_state.llm_provider != llm_provider:
            logger.info(f"🔄 [Persistence] 提供商变更: {st.session_state.llm_provider} → {llm_provider}")
            st.session_state.llm_provider = llm_provider
            # 提供商变更时清空模型选择
            st.session_state.llm_model = ""
            st.session_state.model_category = "openai"  # 重置为默认类别
            logger.info(f"🔄 [Persistence] 清空模型选择")

            # 保存到持久化存储
            save_model_selection(llm_provider, st.session_state.model_category, "")
        else:
            st.session_state.llm_provider = llm_provider

        # 根据提供商显示不同的模型选项
        if llm_provider == "dashscope":
            quick_think_options = ["qwen-turbo", "qwen-plus-latest", "qwen-max"]
            deep_think_options = ["qwen-plus-latest", "qwen-max", "qwen-turbo"]
            
            quick_think_llm = st.selectbox(
                "快速思考模型",
                options=quick_think_options,
                index=0, # Default to turbo
                format_func=lambda x: f"⚡ {x}"
            )
            deep_think_llm = st.selectbox(
                "深度思考模型",
                options=deep_think_options,
                index=0, # Default to plus
                format_func=lambda x: f"🧠 {x}"
            )
            st.session_state.quick_think_llm = quick_think_llm
            st.session_state.deep_think_llm = deep_think_llm
            save_model_selection(llm_provider, "default", quick_think_llm, deep_think_llm)

        elif llm_provider == "google":
            quick_think_options = ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-2.5-flash-lite-preview-06-17"]
            deep_think_options = ["gemini-1.5-pro", "gemini-2.5-pro", "gemini-2.0-flash"]

            quick_think_llm = st.selectbox(
                "快速思考模型",
                options=quick_think_options,
                index=0, # Default to flash
                format_func=lambda x: f"⚡ {x}"
            )
            deep_think_llm = st.selectbox(
                "深度思考模型",
                options=deep_think_options,
                index=0, # Default to pro
                format_func=lambda x: f"🧠 {x}"
            )
            st.session_state.quick_think_llm = quick_think_llm
            st.session_state.deep_think_llm = deep_think_llm
            save_model_selection(llm_provider, "default", quick_think_llm, deep_think_llm)
        
        # ... (other providers would follow the same pattern) ...

        else:
            st.warning(f"模型选择尚未对 {llm_provider} 进行适配。")
            # Fallback to a single model input for un-adapted providers
            llm_model = st.text_input("模型名称", value=st.session_state.get('llm_model', ''))
            st.session_state.quick_think_llm = llm_model
            st.session_state.deep_think_llm = llm_model
            save_model_selection(llm_provider, "default", llm_model, llm_model)
        
        # 高级设置
        with st.expander("⚙️ 高级设置"):
            enable_memory = st.checkbox(
                "启用记忆功能",
                value=False,
                help="启用智能体记忆功能（可能影响性能）"
            )
            
            enable_debug = st.checkbox(
                "调试模式",
                value=False,
                help="启用详细的调试信息输出"
            )
            
            max_tokens = st.slider(
                "最大输出长度",
                min_value=1000,
                max_value=8000,
                value=4000,
                step=500,
                help="AI模型的最大输出token数量"
            )
        
        st.markdown("---")

        # 系统配置
        st.markdown("**🔧 系统配置**")

        # API密钥状态
        st.markdown("**🔑 API密钥状态**")

        def validate_api_key(key, expected_format):
            """验证API密钥格式"""
            if not key:
                return "未配置", "error"

            if expected_format == "dashscope" and key.startswith("sk-") and len(key) >= 32:
                return f"{key[:8]}...", "success"
            elif expected_format == "deepseek" and key.startswith("sk-") and len(key) >= 32:
                return f"{key[:8]}...", "success"
            elif expected_format == "finnhub" and len(key) >= 20:
                return f"{key[:8]}...", "success"
            elif expected_format == "tushare" and len(key) >= 32:
                return f"{key[:8]}...", "success"
            elif expected_format == "google" and key.startswith("AIza") and len(key) >= 32:
                return f"{key[:8]}...", "success"
            elif expected_format == "openai" and key.startswith("sk-") and len(key) >= 40:
                return f"{key[:8]}...", "success"
            elif expected_format == "anthropic" and key.startswith("sk-") and len(key) >= 40:
                return f"{key[:8]}...", "success"
            elif expected_format == "reddit" and len(key) >= 10:
                return f"{key[:8]}...", "success"
            else:
                return f"{key[:8]}... (格式异常)", "warning"

        # 必需的API密钥
        st.markdown("*必需配置:*")

        # 阿里百炼
        dashscope_key = os.getenv("DASHSCOPE_API_KEY")
        status, level = validate_api_key(dashscope_key, "dashscope")
        if level == "success":
            st.success(f"✅ 阿里百炼: {status}")
        elif level == "warning":
            st.warning(f"⚠️ 阿里百炼: {status}")
        else:
            st.error("❌ 阿里百炼: 未配置")

        # FinnHub
        finnhub_key = os.getenv("FINNHUB_API_KEY")
        status, level = validate_api_key(finnhub_key, "finnhub")
        if level == "success":
            st.success(f"✅ FinnHub: {status}")
        elif level == "warning":
            st.warning(f"⚠️ FinnHub: {status}")
        else:
            st.error("❌ FinnHub: 未配置")

        # 可选的API密钥
        st.markdown("*可选配置:*")

        # DeepSeek
        deepseek_key = os.getenv("DEEPSEEK_API_KEY")
        status, level = validate_api_key(deepseek_key, "deepseek")
        if level == "success":
            st.success(f"✅ DeepSeek: {status}")
        elif level == "warning":
            st.warning(f"⚠️ DeepSeek: {status}")
        else:
            st.info("ℹ️ DeepSeek: 未配置")

        # Tushare
        tushare_key = os.getenv("TUSHARE_TOKEN")
        status, level = validate_api_key(tushare_key, "tushare")
        if level == "success":
            st.success(f"✅ Tushare: {status}")
        elif level == "warning":
            st.warning(f"⚠️ Tushare: {status}")
        else:
            st.info("ℹ️ Tushare: 未配置")

        # Google AI
        google_key = os.getenv("GOOGLE_API_KEY")
        status, level = validate_api_key(google_key, "google")
        if level == "success":
            st.success(f"✅ Google AI: {status}")
        elif level == "warning":
            st.warning(f"⚠️ Google AI: {status}")
        else:
            st.info("ℹ️ Google AI: 未配置")

        # OpenAI (如果配置了且不是默认值)
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key and openai_key != "your_openai_api_key_here":
            status, level = validate_api_key(openai_key, "openai")
            if level == "success":
                st.success(f"✅ OpenAI: {status}")
            elif level == "warning":
                st.warning(f"⚠️ OpenAI: {status}")

        # Anthropic (如果配置了且不是默认值)
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        if anthropic_key and anthropic_key != "your_anthropic_api_key_here":
            status, level = validate_api_key(anthropic_key, "anthropic")
            if level == "success":
                st.success(f"✅ Anthropic: {status}")
            elif level == "warning":
                st.warning(f"⚠️ Anthropic: {status}")

        st.markdown("---")

        # 系统信息
        st.markdown("**ℹ️ 系统信息**")
        
        st.info(f"""
        **版本**: cn-0.1.13
        **框架**: Streamlit + LangGraph
        **AI模型**: 
         - ⚡ {st.session_state.quick_think_llm}
         - 🧠 {st.session_state.deep_think_llm}
        **数据源**: Tushare + FinnHub API
        """)
        
        # 帮助链接
        st.markdown("**📚 帮助资源**")
        
        st.markdown("""
        - [📖 使用文档](https://github.com/TauricResearch/TradingAgents)
        - [🐛 问题反馈](https://github.com/TauricResearch/TradingAgents/issues)
        - [💬 讨论社区](https://github.com/TauricResearch/TradingAgents/discussions)
        - [🔧 API密钥配置](../docs/security/api_keys_security.md)
        """)
    
    # 确保返回session state中的值，而不是局部变量
    final_provider = st.session_state.llm_provider
    quick_model = st.session_state.quick_think_llm
    deep_model = st.session_state.deep_think_llm

    logger.debug(f"🔄 [Session State] 返回配置 - provider: {final_provider}, quick: {quick_model}, deep: {deep_model}")

    return {
        'llm_provider': final_provider,
        'quick_think_llm': quick_model,
        'deep_think_llm': deep_model,
        'enable_memory': enable_memory,
        'enable_debug': enable_debug,
        'max_tokens': max_tokens
    }
