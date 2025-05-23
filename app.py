import streamlit as st
import streamlit.components.v1 as components
from agents.sourcing_agent import SourcingAgent
from agents.screening_agent import ScreeningAgent
from agents.engagement_agent import EngagementAgent
from agents.scheduling_agent import SchedulingAgent
import os
from dotenv import load_dotenv
import PyPDF2
import io
import pandas as pd
import base64
import time
from datetime import datetime, timedelta
import json

# Load environment variables
load_dotenv()

# Load custom CSS
def load_css():
    with open('static/css/custom.css') as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# Initialize agents
@st.cache_resource
def get_agents():
    return {
        "sourcing": SourcingAgent(),
        "screening": ScreeningAgent(),
        "engagement": EngagementAgent(),
        "scheduling": SchedulingAgent()
    }

def extract_text_from_pdf(pdf_file):
    """Extract text from a PDF file"""
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text

def extract_text_from_file(uploaded_file):
    """Extract text from either a text or PDF file"""
    if uploaded_file.type == "application/pdf":
        return extract_text_from_pdf(io.BytesIO(uploaded_file.read()))
    else:
        # Try different encodings for text files
        encodings = ['utf-8', 'latin-1', 'iso-8859-1']
        for encoding in encodings:
            try:
                return uploaded_file.read().decode(encoding)
            except UnicodeDecodeError:
                continue
        # If all encodings fail, try with error handling
        return uploaded_file.read().decode('utf-8', errors='replace')

# Utility functions for UI
def create_card(title, content, card_type="primary"):
    """Create a styled card with title and content"""
    html = f"""
    <div class="card card-{card_type}">
        <h3>{title}</h3>
        <div>{content}</div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

def render_header(title, subtitle):
    """Render a custom header with title and subtitle"""
    html = f"""
    <div class="custom-header">
        <div class="header-title">{title}</div>
        <div class="header-subtitle">{subtitle}</div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

def display_stat(value, label, color="primary-color"):
    """Display a statistic with value and label"""
    html = f"""
    <div class="stat-box">
        <h3 style="color: var(--{color});">{value}</h3>
        <p>{label}</p>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

def render_job_card(job):
    """Render a job card with title and details"""
    html = f"""
    <div class="job-header">
        <div class="job-title">{job['title']}</div>
    </div>
    <div class="job-content">
        <p><strong>Description:</strong><br/>{job['description']}</p>
        <p><strong>Requirements:</strong><br/>{job['requirements']}</p>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

def display_candidate_card(candidate):
    """Display a candidate's information in a nice card format"""
    # Name and basic info section
    st.markdown(f"""
    <div class="candidate-card">
        <div class="candidate-name">👤 {candidate['metadata'].get('name', 'No name provided')}</div>
        <div class="candidate-info">🏢 <strong>Company:</strong> {candidate['metadata'].get('company', 'Not specified')}</div>
        <div class="candidate-info">📍 <strong>Location:</strong> {candidate['metadata'].get('location', 'Not specified')}</div>
    """, unsafe_allow_html=True)
    
    # Bio section
    if candidate['metadata'].get('bio'):
        st.markdown(f"""
        <div class="candidate-bio">
            {candidate['metadata'].get('bio', 'No bio available')}
        </div>
        """, unsafe_allow_html=True)
    
    # Skills section
    skills_html = ""
    if candidate['metadata'].get('skills'):
        for skill in candidate['metadata'].get('skills', []):
            skills_html += f'<span class="skill-tag">{skill}</span>'
    
    st.markdown(f"""
    <div class="candidate-info">🛠️ <strong>Skills:</strong></div>
    <div>{skills_html}</div>
    """, unsafe_allow_html=True)
    
    # Experience and education
    st.markdown(f"""
    <div class="candidate-info">🎓 <strong>Experience:</strong> {candidate['metadata'].get('experience', 'Not specified')}</div>
    <div class="candidate-info">📚 <strong>Education:</strong> {candidate['metadata'].get('education', 'Not specified')}</div>
    """, unsafe_allow_html=True)
    
    # GitHub specific info
    if candidate.get('source') == 'GitHub':
        st.markdown(f"""
        <div class="candidate-info">💻 <strong>Contributions:</strong> {candidate.get('contributions', 'N/A')}</div>
        """, unsafe_allow_html=True)
    
    # Profile link
    if candidate.get('profile_url'):
        st.markdown(f"""
        <div class="candidate-info"><a href="{candidate['profile_url']}" target="_blank">🔗 View Profile</a></div>
        """, unsafe_allow_html=True)
    
    # Close the card div
    st.markdown("</div>", unsafe_allow_html=True)

def main():
    st.set_page_config(
        page_title="AI Talent Acquisition Platform",
        page_icon="🧠",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Load custom CSS
    load_css()

    # Initialize session state
    if "current_candidate" not in st.session_state:
        st.session_state.current_candidate = None
    if "current_job" not in st.session_state:
        st.session_state.current_job = None
    if "sourced_candidates" not in st.session_state:
        st.session_state.sourced_candidates = []
    if "search_query" not in st.session_state:
        st.session_state.search_query = ""
    if "analytics" not in st.session_state:
        st.session_state.analytics = {
            "jobs_posted": 0,
            "candidates_sourced": 0,
            "interviews_scheduled": 0,
            "messages_sent": 0,
        }

    # Get agents
    agents = get_agents()

    # Sidebar with logo and navigation
    with st.sidebar:
        st.markdown("<h1 style='text-align: center;'>🧠 TalentAI</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #8392ab;'>Intelligent Talent Acquisition</p>", unsafe_allow_html=True)
        st.markdown("---")
        
        # Navigation menu
        page = st.radio(
            "Navigation",
            ["Dashboard", "Job Posting", "Candidate Sourcing", "Resume Screening", 
             "Candidate Engagement", "Interview Scheduling"],
            format_func=lambda x: f"{'📊' if x == 'Dashboard' else '📝' if x == 'Job Posting' else '🔍' if x == 'Candidate Sourcing' else '📋' if x == 'Resume Screening' else '💬' if x == 'Candidate Engagement' else '📅'} {x}"
        )
        
        st.markdown("---")
        
        # Show current job badge if available
        if st.session_state.current_job:
            st.markdown(f"""
            <div style='background-color: rgba(67, 97, 238, 0.1); padding: 10px; border-radius: 5px;'>
                <p style='margin:0; color: #4361ee; font-size: 12px;'>CURRENT JOB</p>
                <p style='margin:0; font-weight: bold;'>{st.session_state.current_job['title']}</p>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("❌ Clear Job"):
                st.session_state.current_job = None
                st.session_state.sourced_candidates = []
                st.experimental_rerun()
                
        st.markdown("---")
        st.markdown("<div style='position: absolute; bottom: 20px; left: 0; width: 100%; text-align: center;'><p style='color: #8392ab; font-size: 12px;'>© 2025 TalentAI Platform</p></div>", unsafe_allow_html=True)

    # Main content area
    if page == "Dashboard":
        render_header("Recruitment Dashboard", "Analytics & Insights for your hiring pipeline")
        
        # Overview metrics
        st.markdown("### Key Metrics")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            display_stat(st.session_state.analytics["jobs_posted"], "Jobs Posted")
        with col2:
            display_stat(st.session_state.analytics["candidates_sourced"], "Candidates Found", "success-color")
        with col3:
            display_stat(st.session_state.analytics["interviews_scheduled"], "Interviews", "accent-color")
        with col4:
            display_stat(st.session_state.analytics["messages_sent"], "Messages Sent", "warning-color")
            
        # Current job section
        st.markdown("### Current Hiring Status")
        col1, col2 = st.columns([2, 3])
        
        with col1:
            if st.session_state.current_job:
                render_job_card(st.session_state.current_job)
            else:
                create_card("No Active Job", "Post a job to start the recruitment process", "warning")
        
        with col2:
            if st.session_state.sourced_candidates:
                create_card(
                    f"Candidate Pool: {len(st.session_state.sourced_candidates)} candidates",
                    f"GitHub: {sum(1 for c in st.session_state.sourced_candidates if c.get('source') == 'GitHub')} | " + 
                    f"LinkedIn: {sum(1 for c in st.session_state.sourced_candidates if c.get('source') == 'LinkedIn')} | " +
                    f"Internal: {sum(1 for c in st.session_state.sourced_candidates if c.get('source') == 'Internal Database')}",
                    "success"
                )
            else:
                create_card("No Candidates", "Source candidates to build your talent pool", "warning")
                
        # Recent activity (placeholder for now)
        st.markdown("### Recent Activity")
        activity_data = [
            {"action": "Job Posted", "details": "Senior Python Developer", "time": "Today, 10:30 AM"},
            {"action": "Candidate Sourced", "details": "15 new candidates from GitHub", "time": "Today, 11:45 AM"},
            {"action": "Message Sent", "details": "Interview invitation to John Doe", "time": "Yesterday, 3:20 PM"},
        ]
        
        for activity in activity_data:
            st.markdown(f"""
            <div style='display: flex; margin-bottom: 10px; padding: 10px; background-color: var(--card-bg); border-radius: 5px; color: var(--text-color); box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);'>
                <div style='margin-right: 20px;'>
                    <span style='background-color: #374151; border-radius: 50%; width: 40px; height: 40px; display: flex; align-items: center; justify-content: center; color: white;'>
                        {"📝" if activity["action"] == "Job Posted" else "🔍" if activity["action"] == "Candidate Sourced" else "💬"}
                    </span>
                </div>
                <div>
                    <p style='margin: 0; font-weight: bold; color: var(--text-color);'>{activity["action"]}</p>
                    <p style='margin: 0; color: var(--text-color);'>{activity["details"]}</p>
                    <p style='margin: 0; color: #a3adc2; font-size: 12px;'>{activity["time"]}</p>
                </div>
            </div>
            """, unsafe_allow_html=True)

    elif page == "Job Posting":
        st.header("📝 Post a New Job")
        with st.form("job_posting_form"):
            job_title = st.text_input("Job Title")
            job_description = st.text_area("Job Description")
            requirements = st.text_area("Requirements")
            
            if st.form_submit_button("Post Job"):
                if job_title and job_description and requirements:
                    st.session_state.current_job = {
                        "title": job_title,
                        "description": job_description,
                        "requirements": requirements
                    }
                    st.success("Job posted successfully!")
                    st.session_state.sourced_candidates = []  # Reset candidates when new job is posted

    elif page == "Candidate Sourcing":
        render_header("AI-Powered Candidate Sourcing", "Find the perfect candidates for your job openings")
        
        # Job details section
        if not st.session_state.current_job:
            create_card(
                "No Active Job", 
                "Please post a job first to start sourcing candidates.",
                "warning"
            )
            
            # Quick job posting form
            st.markdown("### Quick Job Posting")
            with st.form("quick_job_form"):
                job_title = st.text_input("Job Title")
                job_description = st.text_area("Job Description")
                requirements = st.text_area("Requirements")
                
                if st.form_submit_button("Create Job & Continue"):
                    if job_title and job_description and requirements:
                        st.session_state.current_job = {
                            "title": job_title,
                            "description": job_description,
                            "requirements": requirements
                        }
                        st.session_state.analytics["jobs_posted"] += 1
                        st.success("Job created successfully!")
                        st.experimental_rerun()
            st.stop()
        
        # Show current job details
        with st.expander("📋 Current Job Details", expanded=False):
            st.markdown(f"### {st.session_state.current_job['title']}")
            
            tab1, tab2 = st.tabs(["Description", "Requirements"])
            with tab1:
                st.markdown(st.session_state.current_job['description'])
            with tab2:
                st.markdown(st.session_state.current_job['requirements'])

        # Search section with better UI
        st.markdown("### 🔍 Find Candidates")
        
        search_col1, search_col2 = st.columns([3, 1])
        with search_col1:
            search_query = st.text_input(
                "Search Query",
                value=st.session_state.search_query,
                placeholder="e.g., python machine learning expert",
                help="Enter keywords related to skills, roles, or experience"
            )
        
        with search_col2:
            st.markdown("<br>", unsafe_allow_html=True)  # Add spacing
            search_button = st.button("🔎 Search", type="primary", use_container_width=True)
        
        # Search sources selection
        source_col1, source_col2 = st.columns(2)
        with source_col1:
            search_sources = st.multiselect(
                "Search Sources",
                ["GitHub", "LinkedIn", "Internal Database"],
                default=["GitHub"],
                help="Select where to look for candidates"
            )
        
        with source_col2:
            max_results = st.slider(
                "Max Results per Source",
                min_value=5,
                max_value=50,
                value=10,
                help="Limit the number of results to improve search speed"
            )
        
        # Execute search
        if search_button:
            with st.spinner("🔍 Searching for candidates..."):
                # Progress bar animation
                progress_bar = st.progress(0)
                for i in range(100):
                    time.sleep(0.01)
                    progress_bar.progress(i + 1)
                
                # Use custom query if provided, otherwise use job details
                if search_query:
                    st.session_state.search_query = search_query
                    results = agents["sourcing"].source_candidates(search_query, search_query)
                else:
                    results = agents["sourcing"].source_candidates(
                        st.session_state.current_job["description"],
                        st.session_state.current_job["requirements"]
                    )
                
                candidates = results["candidates"]
                # Filter by selected sources
                candidates = [c for c in candidates if c.get('source', '') in search_sources]
                
                st.session_state.sourced_candidates = candidates
                st.session_state.analytics["candidates_sourced"] += len(candidates)
                
                # Clear progress bar
                progress_bar.empty()
                
                # Show a success message
                if candidates:
                    st.success(f"Found {len(candidates)} candidates matching your criteria!")
                else:
                    st.warning("No candidates found. Try broadening your search.")

        # Show results with proper filtering and sorting
        if st.session_state.sourced_candidates:
            # Display tabs for different views
            view_tab1, view_tab2 = st.tabs(["Card View", "Table View"])
            
            with view_tab1:
                # Filters in columns
                st.markdown("#### Filter Candidates")
                filter_col1, filter_col2, filter_col3 = st.columns(3)
                
                with filter_col1:
                    source_filter = st.multiselect(
                        "Source",
                        options=list(set(c.get('source', '') for c in st.session_state.sourced_candidates)),
                        default=list(set(c.get('source', '') for c in st.session_state.sourced_candidates)),
                        key="source_filter_cards"
                    )
                
                with filter_col2:
                    # Extract all skills from candidates
                    all_skills = set()
                    for c in st.session_state.sourced_candidates:
                        all_skills.update(c['metadata'].get('skills', []))
                    
                    skills_filter = st.multiselect(
                        "Skills",
                        options=sorted(list(all_skills)),
                        key="skills_filter_cards"
                    )
                
                with filter_col3:
                    sort_by = st.selectbox(
                        "Sort by",
                        ["Relevance", "Experience", "Contributions"],
                        key="sort_by_cards"
                    )
                
                # Apply filters
                filtered_candidates = [
                    c for c in st.session_state.sourced_candidates
                    if (not source_filter or c.get('source', '') in source_filter) and
                       (not skills_filter or any(skill in c['metadata'].get('skills', []) for skill in skills_filter))
                ]
                
                # Sort candidates
                if sort_by == "Experience":
                    filtered_candidates.sort(
                        key=lambda x: int(''.join(filter(str.isdigit, x['metadata'].get('experience', '0') or '0')) or 0),
                        reverse=True
                    )
                elif sort_by == "Contributions":
                    filtered_candidates.sort(
                        key=lambda x: x.get('contributions', 0) if isinstance(x.get('contributions'), (int, float)) else 0,
                        reverse=True
                    )
                
                # Show count
                st.markdown(f"Showing {len(filtered_candidates)} candidates")
                
                # Display candidates in cards (2 columns)
                if filtered_candidates:
                    for i in range(0, len(filtered_candidates), 2):
                        cols = st.columns(2)
                        if i < len(filtered_candidates):
                            with cols[0]:
                                display_candidate_card(filtered_candidates[i])
                        if i + 1 < len(filtered_candidates):
                            with cols[1]:
                                display_candidate_card(filtered_candidates[i + 1])
                
            with view_tab2:
                # Table filters
                st.markdown("#### Filter Candidates")
                filter_cols = st.columns(3)
                
                with filter_cols[0]:
                    source_filter_table = st.multiselect(
                        "Source",
                        options=list(set(c.get('source', '') for c in st.session_state.sourced_candidates)),
                        default=list(set(c.get('source', '') for c in st.session_state.sourced_candidates)),
                        key="source_filter_table"
                    )
                
                with filter_cols[1]:
                    # Extract all skills for table view
                    all_skills_table = set()
                    for c in st.session_state.sourced_candidates:
                        all_skills_table.update(c['metadata'].get('skills', []))
                    
                    skills_filter_table = st.multiselect(
                        "Skills",
                        options=sorted(list(all_skills_table)),
                        key="skills_filter_table"
                    )
                
                with filter_cols[2]:
                    sort_by_table = st.selectbox(
                        "Sort by",
                        ["Relevance", "Experience", "Contributions"],
                        key="sort_by_table"
                    )
                
                # Apply table filters
                filtered_candidates_table = [
                    c for c in st.session_state.sourced_candidates
                    if (not source_filter_table or c.get('source', '') in source_filter_table) and
                       (not skills_filter_table or any(skill in c['metadata'].get('skills', []) for skill in skills_filter_table))
                ]
                
                # Sort candidates for table
                if sort_by_table == "Experience":
                    filtered_candidates_table.sort(
                        key=lambda x: int(''.join(filter(str.isdigit, x['metadata'].get('experience', '0') or '0')) or 0),
                        reverse=True
                    )
                elif sort_by_table == "Contributions":
                    filtered_candidates_table.sort(
                        key=lambda x: x.get('contributions', 0) if isinstance(x.get('contributions'), (int, float)) else 0,
                        reverse=True
                    )
                
                # Convert to DataFrame for table display
                if filtered_candidates_table:
                    candidates_data = []
                    for c in filtered_candidates_table:
                        data = {
                            'Name': c['metadata'].get('name', ''),
                            'Title': c['metadata'].get('title', ''),
                            'Location': c['metadata'].get('location', ''),
                            'Company': c['metadata'].get('company', ''),
                            'Skills': ', '.join(c['metadata'].get('skills', [])[:3]) + ('...' if len(c['metadata'].get('skills', [])) > 3 else ''),
                            'Experience': c['metadata'].get('experience', ''),
                            'Source': c.get('source', ''),
                            'URL': c.get('profile_url', '')
                        }
                        candidates_data.append(data)
                    
                    df = pd.DataFrame(candidates_data)
                    st.dataframe(df, use_container_width=True)
                    
                    # Export options
                    col1, col2 = st.columns(2)
                    with col1:
                        csv = df.to_csv(index=False)
                        st.download_button(
                            "📥 Export as CSV",
                            csv,
                            "candidates.csv",
                            "text/csv",
                            key='download-csv',
                            use_container_width=True
                        )
                    
                    with col2:
                        # Export as Excel (would need additional package)
                        st.download_button(
                            "📊 Export as Excel",
                            csv,  # Using CSV as a placeholder
                            "candidates.xlsx",
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key='download-excel',
                            use_container_width=True
                        )

            # Actions section
            st.markdown("### 🚀 Actions")
            action_col1, action_col2, action_col3 = st.columns(3)
            
            with action_col1:
                if st.button("📋 Shortlist Selected", use_container_width=True):
                    st.success("Candidates shortlisted successfully!")
            
            with action_col2:
                if st.button("💬 Contact Selected", use_container_width=True):
                    st.session_state.analytics["messages_sent"] += 3
                    st.success("Contact messages sent to selected candidates!")
            
            with action_col3:
                if st.button("📊 Generate Report", use_container_width=True):
                    st.success("Report generated and saved!")

    elif page == "Resume Screening":
        st.header("📋 Screen Resumes")
        if st.session_state.current_job:
            uploaded_file = st.file_uploader("Upload Resume", type=["txt", "pdf"])
            
            if uploaded_file:
                try:
                    resume_text = extract_text_from_file(uploaded_file)
                    if st.button("Screen Resume"):
                        with st.spinner("Screening resume..."):
                            analysis = agents["screening"].screen_candidate(
                                resume_text,
                                st.session_state.current_job["description"]
                            )
                            
                            st.subheader("Screening Results")
                            st.write(f"Recommendation: {analysis['recommendation']}")
                            
                            st.subheader("Key Points")
                            for key, value in analysis["key_points"].items():
                                st.write(f"**{key.replace('_', ' ').title()}**: {value}")
                except Exception as e:
                    st.error(f"Error processing file: {str(e)}")
        else:
            st.warning("Please post a job first!")

    elif page == "Candidate Engagement":
        st.header("💬 Engage with Candidates")
        candidate_id = st.text_input("Candidate ID")
        
        if candidate_id:
            if "messages" not in st.session_state:
                st.session_state.messages = []
            
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.write(message["content"])
            
            if prompt := st.chat_input("Type your message..."):
                st.session_state.messages.append({"role": "user", "content": prompt})
                with st.chat_message("user"):
                    st.write(prompt)
                
                with st.spinner("Generating response..."):
                    response = agents["engagement"].handle_candidate_response(
                        candidate_id,
                        prompt
                    )
                    st.session_state.messages.append({"role": "assistant", "content": response})
                    with st.chat_message("assistant"):
                        st.write(response)

    elif page == "Interview Scheduling":
        st.header("📅 Schedule Interviews")
        candidate_id = st.text_input("Candidate ID")
        
        if candidate_id:
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Candidate Availability")
                candidate_availability = {
                    "Monday": st.multiselect("Monday", ["9AM-12PM", "1PM-5PM"]),
                    "Tuesday": st.multiselect("Tuesday", ["9AM-12PM", "1PM-5PM"]),
                    "Wednesday": st.multiselect("Wednesday", ["9AM-12PM", "1PM-5PM"]),
                    "Thursday": st.multiselect("Thursday", ["9AM-12PM", "1PM-5PM"]),
                    "Friday": st.multiselect("Friday", ["9AM-12PM", "1PM-5PM"])
                }
            
            with col2:
                st.subheader("Interviewer Availability")
                interviewer_availability = {
                    "Monday": st.multiselect("Monday (Interviewer)", ["9AM-12PM", "1PM-5PM"]),
                    "Tuesday": st.multiselect("Tuesday (Interviewer)", ["9AM-12PM", "1PM-5PM"]),
                    "Wednesday": st.multiselect("Wednesday (Interviewer)", ["9AM-12PM", "1PM-5PM"]),
                    "Thursday": st.multiselect("Thursday (Interviewer)", ["9AM-12PM", "1PM-5PM"]),
                    "Friday": st.multiselect("Friday (Interviewer)", ["9AM-12PM", "1PM-5PM"])
                }
            
            if st.button("Find Available Slots"):
                with st.spinner("Finding available time slots..."):
                    slots = agents["scheduling"].find_available_slots(
                        candidate_availability,
                        interviewer_availability
                    )
                    
                    st.subheader("Available Time Slots")
                    if slots:
                        # Create a form for slot selection
                        with st.form("slot_selection_form"):
                            selected_slot = st.radio(
                                "Select a time slot:",
                                options=[slot['time'] for slot in slots],
                                format_func=lambda x: x
                            )
                            
                            if st.form_submit_button("Schedule Interview"):
                                # Find the selected slot object
                                selected_slot_obj = next(
                                    slot for slot in slots if slot['time'] == selected_slot
                                )
                                
                                interview = agents["scheduling"].schedule_interview(
                                    candidate_id,
                                    selected_slot_obj
                                )
                                st.success(f"Interview scheduled for {interview['time']}")
                    else:
                        st.info("No available time slots found. Please adjust the availability.")

if __name__ == "__main__":
    main()