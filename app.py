import streamlit as st
import time
from orchestrator import run_secureops_pipeline_generator

# Page Configuration
st.set_page_config(
    page_title="SecureOps - AI ITSM Dashboard",
    page_icon="🛡️",
    layout="wide",
)

# Custom Sleek CSS for Premium Styling
st.markdown(
    """
    <style>
    /* Main Layout Adjustments */
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 1.5rem;
    }
    
    /* Header Styling */
    .main-header {
        font-family: 'Outfit', 'Inter', sans-serif;
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(135deg, #4A90E2, #9B59B6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    
    .sub-header {
        font-family: 'Inter', sans-serif;
        font-size: 1rem;
        color: #7F8C8D;
        margin-bottom: 2rem;
    }

    /* Agent Card Styling */
    .agent-card {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 1rem;
        margin-bottom: 0.75rem;
        backdrop-filter: blur(10px);
        transition: all 0.3s ease;
    }
    .agent-card:hover {
        border-color: rgba(74, 144, 226, 0.5);
        transform: translateY(-2px);
    }
    
    /* Status Badge styling */
    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.6rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        margin-bottom: 0.5rem;
    }
    .badge-running { background-color: #F39C12; color: #FFF; }
    .badge-completed { background-color: #2ECC71; color: #FFF; }
    .badge-failed { background-color: #E74C3C; color: #FFF; }
    
    /* Panel Containers */
    .panel-container {
        border-radius: 16px;
        padding: 1.5rem;
        border: 1px solid rgba(255, 255, 255, 0.08);
        background: rgba(30, 30, 30, 0.2);
        height: 80vh;
        overflow-y: auto;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Header Section
st.markdown("<div class='main-header'>🛡️ SecureOps Portal</div>", unsafe_allow_html=True)
st.markdown(
    "<div class='sub-header'>Secured Multi-Agent IT Service Management. Powered by Google ADK & Gemini.</div>",
    unsafe_allow_html=True,
)

# Initialize Session State
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "Hello! I am SecureOps Agent. Submit your IT support issue below, and my pipeline will validate and resolve it.",
        }
    ]

# Layout: Two panels (Left for Chat, Right for Agent Activity)
col_left, col_right = st.columns([3, 2], gap="large")

with col_left:
    st.subheader("💬 Incident Desk")
    
    # Message display container
    chat_container = st.container(height=500)
    with chat_container:
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    # Chat Input
    prompt = st.chat_input("Describe your IT issue...")

with col_right:
    st.subheader("⚡ Agent Activity")
    
    # Placeholder containers for each agent stage
    activity_container = st.container()
    
    with activity_container:
        # We define a persistent state helper to show previous run activity if it exists
        if "activity_steps" not in st.session_state:
            st.session_state.activity_steps = {}
            
        # Draw placeholder or current activity boxes
        steps = [
            ("security_guardian", "🛡️ Security Guardian Check"),
            ("intake_agent", "📝 Ticket Intake & Classification"),
            ("knowledge_retrieval_agent", "🔍 Knowledge Vector Lookup"),
            ("resolution_agent", "💡 Resolution Draft & Evaluation"),
            ("knowledge_extraction_agent", "🔄 Knowledge Flywheel Extraction"),
        ]
        
        step_placeholders = {}
        for step_key, step_title in steps:
            step_placeholders[step_key] = st.empty()
            
            # If there is cached activity from a previous run, display it
            if step_key in st.session_state.activity_steps:
                info = st.session_state.activity_steps[step_key]
                with step_placeholders[step_key].container():
                    status_class = "badge-completed" if info["status"] == "completed" else "badge-failed" if info["status"] == "failed" else "badge-running"
                    st.markdown(
                        f"""
                        <div class="agent-card">
                            <span class="status-badge {status_class}">{info['status']}</span>
                            <div style="font-weight: 600; font-size: 1.05rem; margin-bottom: 0.25rem;">{step_title}</div>
                            <div style="font-size: 0.9rem; opacity: 0.85;">{info['message']}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
            else:
                # Default empty/inactive state
                with step_placeholders[step_key].container():
                    st.markdown(
                        f"""
                        <div class="agent-card" style="opacity: 0.4;">
                            <div style="font-weight: 600; font-size: 1.05rem;">{step_title}</div>
                            <div style="font-size: 0.9rem; font-style: italic;">Awaiting input...</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
        
        # Expander for raw JSON trace data
        raw_trace_placeholder = st.empty()
        if "raw_trace" in st.session_state and st.session_state.raw_trace:
            with raw_trace_placeholder.expander("📦 Raw Agent Trace JSON"):
                st.json(st.session_state.raw_trace)


# Handle user interaction
if prompt:
    # 1. Add and display user message immediately
    st.session_state.messages.append({"role": "user", "content": prompt})
    with chat_container:
        with st.chat_message("user"):
            st.markdown(prompt)

    # 2. Reset activity states in session
    st.session_state.activity_steps = {}
    st.session_state.raw_trace = None
    
    # Reset all placeholders to "Awaiting input..."
    for step_key, step_title in steps:
        with step_placeholders[step_key].container():
            st.markdown(
                f"""
                <div class="agent-card" style="opacity: 0.4;">
                    <div style="font-weight: 600; font-size: 1.05rem;">{step_title}</div>
                    <div style="font-size: 0.9rem; font-style: italic;">Awaiting input...</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            
    raw_trace_placeholder.empty()

    # 3. Stream pipeline execution steps
    pipeline = run_secureops_pipeline_generator(prompt)
    final_output = None
    
    for event in pipeline:
        # Check if the yielded item is the final result dict
        if isinstance(event, dict) and "step" not in event:
            final_output = event
            break
            
        step_key = event["step"]
        step_title = dict(steps).get(step_key, step_key.replace("_", " ").title())
        status = event["status"]
        message = event["message"]
        
        # Cache in session state
        st.session_state.activity_steps[step_key] = {"status": status, "message": message}
        
        # Render the updated state
        with step_placeholders[step_key].container():
            status_class = "badge-running" if status == "running" else "badge-completed" if status == "completed" else "badge-failed"
            st.markdown(
                f"""
                <div class="agent-card">
                    <span class="status-badge {status_class}">{status}</span>
                    <div style="font-weight: 600; font-size: 1.05rem; margin-bottom: 0.25rem;">{step_title}</div>
                    <div style="font-size: 0.9rem; opacity: 0.85;">{message}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        
        # Brief pause to make transition/progress readable for demonstration
        time.sleep(0.5)

    # 4. Handle final result output
    if final_output:
        st.session_state.raw_trace = final_output
        with raw_trace_placeholder.expander("📦 Raw Agent Trace JSON"):
            st.json(final_output)

        # Formulate assistant message
        if final_output["status"] == "rejected":
            response_text = f"🛑 **Security Alert: Request Rejected**\n\n**Reason**: {final_output['rejection_reason']}\n\n**Risk Flags**: `{final_output['risk_flags']}`"
        else:
            action = final_output["action"]
            if action == "auto_resolve":
                response_text = f"✅ **Issue Auto-Resolved!**\n\n**Category**: `{final_output['category']}` | **Priority**: `{final_output['priority']}`\n\n**Proposed Resolution**:\n{final_output['resolution_text']}"
                if final_output.get("article_created"):
                    response_text += f"\n\n📂 *A new knowledge article (`{final_output['article_id'][:8]}`) has been automatically added to the database from this resolution.*"
            else:
                response_text = f"⚠️ **Issue Escalated to Human Support**\n\n**Category**: `{final_output['category']}` | **Priority**: `{final_output['priority']}`\n\n**Escalation Reason**:\n{final_output['escalation_reason']}"

        # Save to history and display
        st.session_state.messages.append({"role": "assistant", "content": response_text})
        with chat_container:
            with st.chat_message("assistant"):
                st.markdown(response_text)
                
        # Force a rerun to lock in UI changes
        st.rerun()
