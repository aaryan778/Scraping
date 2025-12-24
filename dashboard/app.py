"""
Streamlit Dashboard for Job Scraping System
Interactive dashboard to visualize and export job data

Phase 5: Added basic authentication and multi-label classification support
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import sys
import os
from pathlib import Path
from sqlalchemy import func

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from models.database import Job, ScrapingLog, SessionLocal
from utils.auth import verify_password_hash

# Page config
st.set_page_config(
    page_title="Job Scraping Dashboard",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        padding: 1rem 0;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        text-align: center;
    }
    .stDownloadButton {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)


def check_authentication():
    """
    Check if user is authenticated

    Returns:
        bool: True if authenticated, False otherwise
    """
    # Get credentials from environment variables
    auth_enabled = os.getenv('DASHBOARD_AUTH_ENABLED', 'true').lower() == 'true'

    # If auth is disabled, allow access
    if not auth_enabled:
        return True

    # Initialize session state
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False

    # If already authenticated, return True
    if st.session_state.authenticated:
        return True

    # Show login form
    st.markdown('<div class="main-header">🔐 Login Required</div>', unsafe_allow_html=True)

    with st.form("login_form"):
        st.markdown("### Please enter your credentials")

        username = st.text_input("Username", key="username_input")
        password = st.text_input("Password", type="password", key="password_input")

        submit = st.form_submit_button("Login", use_container_width=True)

        if submit:
            # Get credentials from env
            correct_username = os.getenv('DASHBOARD_USERNAME', 'admin')
            password_hash = os.getenv('DASHBOARD_PASSWORD_HASH')

            # Support both hashed and legacy plaintext passwords
            if password_hash:
                # Secure: Use hashed password
                password_valid = verify_password_hash(password, password_hash)
            else:
                # Legacy: Fallback to plaintext (not recommended)
                correct_password = os.getenv('DASHBOARD_PASSWORD', 'changeme456')
                password_valid = password == correct_password

            if username == correct_username and password_valid:
                st.session_state.authenticated = True
                st.success("✅ Login successful!")
                st.rerun()
            else:
                st.error("❌ Invalid username or password")

    st.markdown("---")
    st.info("💡 **Default credentials:**\n- Username: admin\n- Password: changeme456\n\n"
            "Change these in your .env file (DASHBOARD_USERNAME and DASHBOARD_PASSWORD)")

    return False


@st.cache_resource
def get_db_session():
    """Get database session"""
    return SessionLocal()


@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_jobs_data():
    """Load all jobs from database"""
    db = SessionLocal()
    try:
        jobs = db.query(Job).filter(Job.is_active == True).all()
        return pd.DataFrame([job.to_dict() for job in jobs])
    finally:
        db.close()


@st.cache_data(ttl=300)
def load_stats():
    """Load statistics with multi-label classification support"""
    db = SessionLocal()
    try:
        total_jobs = db.query(func.count(Job.id)).filter(Job.is_active == True).scalar()

        jobs_by_country = db.query(
            Job.country,
            func.count(Job.id).label('count')
        ).filter(Job.is_active == True).group_by(Job.country).all()

        jobs_by_industry = db.query(
            Job.industry,
            func.count(Job.id).label('count')
        ).filter(Job.is_active == True).group_by(Job.industry).all()

        # Use primary_category instead of category
        jobs_by_category = db.query(
            Job.primary_category,
            func.count(Job.id).label('count')
        ).filter(Job.is_active == True).group_by(Job.primary_category).all()

        return {
            "total_jobs": total_jobs or 0,
            "by_country": dict(jobs_by_country) if jobs_by_country else {},
            "by_industry": dict(jobs_by_industry) if jobs_by_industry else {},
            "by_category": dict(jobs_by_category) if jobs_by_category else {}
        }
    finally:
        db.close()


def export_to_excel(df, filename="jobs_export.xlsx"):
    """Export dataframe to Excel"""
    output_path = Path("data/exports") / filename
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Select columns for export (with multi-label classification)
    export_columns = [
        'title', 'company', 'location', 'country', 'city', 'remote',
        'industry', 'primary_category', 'secondary_categories',
        'classification_confidence', 'experience_level',
        'all_skills', 'salary_min', 'salary_max', 'salary_currency',
        'source_platform', 'source_url', 'posted_date', 'scraped_date'
    ]

    # Filter columns that exist in df
    export_columns = [col for col in export_columns if col in df.columns]

    export_df = df[export_columns].copy()

    # Convert list columns to strings
    if 'all_skills' in export_df.columns:
        export_df['all_skills'] = export_df['all_skills'].apply(
            lambda x: ', '.join(x) if isinstance(x, list) else ''
        )

    if 'secondary_categories' in export_df.columns:
        export_df['secondary_categories'] = export_df['secondary_categories'].apply(
            lambda x: ', '.join(x) if isinstance(x, list) else ''
        )

    # Export to Excel
    export_df.to_excel(output_path, index=False, engine='openpyxl')

    return output_path


# Main app
def main():
    # Check authentication first
    if not check_authentication():
        return

    st.markdown('<div class="main-header">💼 Job Scraping Dashboard</div>', unsafe_allow_html=True)

    # Sidebar with logout button
    st.sidebar.title("🔍 Filters")

    # Logout button at the top of sidebar
    if os.getenv('DASHBOARD_AUTH_ENABLED', 'true').lower() == 'true':
        if st.sidebar.button("🚪 Logout", use_container_width=True):
            st.session_state.authenticated = False
            st.rerun()

    # Load data
    try:
        df = load_jobs_data()
        stats = load_stats()
    except Exception as e:
        st.error(f"Error loading data: {e}")
        st.info("Make sure to initialize the database and run the scraper first!")
        return

    if df.empty:
        st.warning("No jobs found in database. Run the scraper to collect jobs!")
        return

    # Sidebar filters
    countries = ['All'] + sorted(df['country'].dropna().unique().tolist())
    selected_country = st.sidebar.selectbox("Country", countries)

    industries = ['All'] + sorted(df['industry'].dropna().unique().tolist())
    selected_industry = st.sidebar.selectbox("Industry", industries)

    # Use primary_category for filtering
    categories = ['All'] + sorted(df['primary_category'].dropna().unique().tolist())
    selected_category = st.sidebar.selectbox("Primary Category", categories)

    remote_only = st.sidebar.checkbox("Remote Only")

    # Apply filters
    filtered_df = df.copy()

    if selected_country != 'All':
        filtered_df = filtered_df[filtered_df['country'] == selected_country]

    if selected_industry != 'All':
        filtered_df = filtered_df[filtered_df['industry'] == selected_industry]

    if selected_category != 'All':
        filtered_df = filtered_df[filtered_df['primary_category'] == selected_category]

    if remote_only:
        filtered_df = filtered_df[filtered_df['remote'] == True]

    # Metrics
    st.markdown("### 📊 Key Metrics")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Jobs", len(filtered_df))

    with col2:
        remote_count = filtered_df['remote'].sum()
        st.metric("Remote Jobs", int(remote_count))

    with col3:
        avg_salary = filtered_df['salary_min'].mean()
        st.metric("Avg Min Salary", f"${avg_salary:,.0f}" if pd.notna(avg_salary) else "N/A")

    with col4:
        unique_companies = filtered_df['company'].nunique()
        st.metric("Companies", unique_companies)

    st.markdown("---")

    # Tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📈 Overview", "🗺️ Geographic", "💡 Skills", "📋 Job Listings", "📥 Export"
    ])

    # Tab 1: Overview
    with tab1:
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### Jobs by Industry")
            if not filtered_df.empty:
                industry_counts = filtered_df['industry'].value_counts()
                fig = px.pie(
                    values=industry_counts.values,
                    names=industry_counts.index,
                    title="Distribution by Industry"
                )
                st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown("#### Jobs by Primary Category")
            if not filtered_df.empty:
                category_counts = filtered_df['primary_category'].value_counts()
                fig = px.bar(
                    x=category_counts.index,
                    y=category_counts.values,
                    title="Jobs by Primary Category",
                    labels={'x': 'Primary Category', 'y': 'Number of Jobs'}
                )
                fig.update_xaxes(tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)

        col3, col4 = st.columns(2)

        with col3:
            st.markdown("#### Experience Level Distribution")
            if 'experience_level' in filtered_df.columns:
                exp_counts = filtered_df['experience_level'].value_counts()
                fig = px.bar(
                    x=exp_counts.index,
                    y=exp_counts.values,
                    title="Jobs by Experience Level",
                    labels={'x': 'Experience Level', 'y': 'Count'}
                )
                st.plotly_chart(fig, use_container_width=True)

        with col4:
            st.markdown("#### Top Companies Hiring")
            top_companies = filtered_df['company'].value_counts().head(10)
            fig = px.bar(
                x=top_companies.values,
                y=top_companies.index,
                orientation='h',
                title="Top 10 Companies",
                labels={'x': 'Number of Jobs', 'y': 'Company'}
            )
            st.plotly_chart(fig, use_container_width=True)

    # Tab 2: Geographic
    with tab2:
        st.markdown("#### Jobs by Country")

        country_counts = filtered_df['country'].value_counts()
        fig = px.bar(
            x=country_counts.index,
            y=country_counts.values,
            title="Jobs by Country",
            labels={'x': 'Country', 'y': 'Number of Jobs'}
        )
        st.plotly_chart(fig, use_container_width=True)

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### Top Cities")
            if 'city' in filtered_df.columns:
                city_counts = filtered_df['city'].dropna().value_counts().head(15)
                fig = px.bar(
                    x=city_counts.values,
                    y=city_counts.index,
                    orientation='h',
                    title="Top 15 Cities",
                    labels={'x': 'Number of Jobs', 'y': 'City'}
                )
                st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown("#### Remote vs On-site")
            remote_counts = filtered_df['remote'].value_counts()
            fig = px.pie(
                values=remote_counts.values,
                names=['On-site', 'Remote'],
                title="Remote vs On-site Jobs"
            )
            st.plotly_chart(fig, use_container_width=True)

    # Tab 3: Skills
    with tab3:
        st.markdown("#### Top Skills in Demand")

        # Extract all skills
        all_skills = []
        for skills_list in filtered_df['all_skills'].dropna():
            if isinstance(skills_list, list):
                all_skills.extend(skills_list)

        if all_skills:
            skills_df = pd.DataFrame({'skill': all_skills})
            top_skills = skills_df['skill'].value_counts().head(30)

            col1, col2 = st.columns([2, 1])

            with col1:
                fig = px.bar(
                    x=top_skills.values,
                    y=top_skills.index,
                    orientation='h',
                    title="Top 30 Skills",
                    labels={'x': 'Number of Jobs', 'y': 'Skill'}
                )
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                st.markdown("##### Top 20 Skills Table")
                skills_table = pd.DataFrame({
                    'Skill': top_skills.head(20).index,
                    'Count': top_skills.head(20).values
                })
                st.dataframe(skills_table, use_container_width=True, height=600)
        else:
            st.info("No skills data available")

        # Skills by category
        if 'primary_category' in filtered_df.columns and 'all_skills' in filtered_df.columns:
            st.markdown("#### Skills by Job Category")

            category_skills = {}
            for idx, row in filtered_df.iterrows():
                cat = row['primary_category']
                skills = row['all_skills']
                if cat and isinstance(skills, list):
                    if cat not in category_skills:
                        category_skills[cat] = []
                    category_skills[cat].extend(skills)

            # Show top 10 skills for each category
            for category, skills in category_skills.items():
                if skills:
                    skills_count = pd.Series(skills).value_counts().head(10)
                    st.markdown(f"**{category}**")
                    st.write(", ".join([f"{skill} ({count})" for skill, count in skills_count.items()]))

    # Tab 4: Job Listings
    with tab4:
        st.markdown("#### Job Listings")

        # Search
        search_term = st.text_input("🔍 Search jobs by title, company, or location")

        display_df = filtered_df.copy()

        if search_term:
            mask = (
                display_df['title'].str.contains(search_term, case=False, na=False) |
                display_df['company'].str.contains(search_term, case=False, na=False) |
                display_df['location'].str.contains(search_term, case=False, na=False)
            )
            display_df = display_df[mask]

        st.write(f"Showing {len(display_df)} jobs")

        # Display jobs
        for idx, job in display_df.iterrows():
            with st.expander(f"**{job['title']}** at {job['company']} ({job['location']})"):
                col1, col2 = st.columns([2, 1])

                with col1:
                    # Multi-label classification display
                    primary_cat = job.get('primary_category', 'N/A')
                    st.write(f"**Primary Category:** {primary_cat}")

                    secondary_cats = job.get('secondary_categories', [])
                    if isinstance(secondary_cats, list) and secondary_cats:
                        st.write(f"**Secondary Categories:** {', '.join(secondary_cats)}")

                    confidence = job.get('classification_confidence')
                    if confidence:
                        st.write(f"**Classification Confidence:** {confidence:.1%}")

                    st.write(f"**Industry:** {job.get('industry', 'N/A')}")
                    st.write(f"**Experience Level:** {job.get('experience_level', 'N/A')}")
                    st.write(f"**Remote:** {'Yes' if job.get('remote') else 'No'}")

                    if job.get('all_skills'):
                        skills = job['all_skills']
                        if isinstance(skills, list) and skills:
                            st.write(f"**Skills:** {', '.join(skills[:10])}")

                with col2:
                    salary_min = job.get('salary_min')
                    salary_max = job.get('salary_max')
                    if salary_min and salary_max:
                        st.write(f"**Salary:** ${salary_min:,.0f} - ${salary_max:,.0f}")

                    st.write(f"**Source:** {job.get('source_platform', 'N/A')}")

                    if job.get('source_url'):
                        st.markdown(f"[View Job]({job['source_url']})")

                if job.get('description'):
                    with st.container():
                        st.write("**Description:**")
                        st.text_area("", job['description'][:500] + "...", height=100, key=f"desc_{idx}", label_visibility="collapsed")

    # Tab 5: Export
    with tab5:
        st.markdown("### 📥 Export Data")

        st.write(f"Ready to export {len(filtered_df)} jobs based on current filters")

        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("📊 Export IT Jobs", use_container_width=True):
                it_df = filtered_df[filtered_df['industry'] == 'IT']
                if not it_df.empty:
                    try:
                        path = export_to_excel(it_df, "IT_jobs_export.xlsx")
                        st.success(f"✅ Exported {len(it_df)} IT jobs to {path}")
                        # Provide download
                        with open(path, 'rb') as f:
                            st.download_button(
                                label="Download IT Jobs Excel",
                                data=f,
                                file_name="IT_jobs.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
                    except Exception as e:
                        st.error(f"Error exporting: {e}")
                else:
                    st.warning("No IT jobs to export")

        with col2:
            if st.button("🏥 Export Healthcare Jobs", use_container_width=True):
                healthcare_df = filtered_df[filtered_df['industry'] == 'Healthcare']
                if not healthcare_df.empty:
                    try:
                        path = export_to_excel(healthcare_df, "Healthcare_jobs_export.xlsx")
                        st.success(f"✅ Exported {len(healthcare_df)} Healthcare jobs to {path}")
                        with open(path, 'rb') as f:
                            st.download_button(
                                label="Download Healthcare Jobs Excel",
                                data=f,
                                file_name="Healthcare_jobs.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
                    except Exception as e:
                        st.error(f"Error exporting: {e}")
                else:
                    st.warning("No Healthcare jobs to export")

        with col3:
            if st.button("📦 Export All Jobs", use_container_width=True):
                try:
                    path = export_to_excel(filtered_df, "All_jobs_export.xlsx")
                    st.success(f"✅ Exported {len(filtered_df)} jobs to {path}")
                    with open(path, 'rb') as f:
                        st.download_button(
                            label="Download All Jobs Excel",
                            data=f,
                            file_name="All_jobs.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                except Exception as e:
                    st.error(f"Error exporting: {e}")

        st.markdown("---")
        st.markdown("#### Custom Export")
        st.write("Current filters applied:")
        st.write(f"- Country: {selected_country}")
        st.write(f"- Industry: {selected_industry}")
        st.write(f"- Category: {selected_category}")
        st.write(f"- Remote Only: {remote_only}")

        custom_filename = st.text_input("Custom filename (without .xlsx)", "custom_export")

        if st.button("Export with Current Filters", use_container_width=True):
            try:
                path = export_to_excel(filtered_df, f"{custom_filename}.xlsx")
                st.success(f"✅ Exported {len(filtered_df)} jobs to {path}")
                with open(path, 'rb') as f:
                    st.download_button(
                        label="Download Custom Export",
                        data=f,
                        file_name=f"{custom_filename}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
            except Exception as e:
                st.error(f"Error exporting: {e}")

    # Footer
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"**Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    with col2:
        st.markdown(f"**Total Jobs in DB:** {stats['total_jobs']}")
    with col3:
        if st.button("🔄 Refresh Data"):
            st.cache_data.clear()
            st.rerun()


if __name__ == "__main__":
    main()
