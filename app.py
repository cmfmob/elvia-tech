#!/usr/bin/env python3
"""
UPI Details Extractor Web Application
A comprehensive Streamlit-based web app for extracting UPI details from phone numbers
"""

import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import time
import os
from datetime import datetime
from collections import defaultdict, Counter
import io
import base64
import threading
import queue


# Page configuration
st.set_page_config(
    page_title="UPI Details Extractor",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        text-align: center;
        color: #1f77b4;
        margin-bottom: 30px;
    }
    .success-message {
        color: #28a745;
        font-weight: bold;
    }
    .error-message {
        color: #dc3545;
        font-weight: bold;
    }
    .info-message {
        color: #17a2b8;
        font-weight: bold;
    }
    .stats-container {
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
    }
    .metric-card {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin: 10px;
    }
</style>
""", unsafe_allow_html=True)


class UPIExtractorWeb:
    def __init__(self):
        # Initialize session state variables
        if 'results' not in st.session_state:
            st.session_state.results = []
        
        if 'processing_status' not in st.session_state:
            st.session_state.processing_status = 'idle'  # idle, running, paused, completed
        
        if 'phone_numbers' not in st.session_state:
            st.session_state.phone_numbers = []
        
        if 'current_index' not in st.session_state:
            st.session_state.current_index = 0
        
        if 'stats' not in st.session_state:
            st.session_state.stats = {
                'total_processed': 0,
                'successful': 0,
                'failed': 0,
                'bank_distribution': Counter(),
                'start_time': None,
                'processing_speed': 0
            }
        
        if 'bank_data' not in st.session_state:
            st.session_state.bank_data = defaultdict(list)
        
        if 'api_url' not in st.session_state:
            st.session_state.api_url = "https://spyshadow.site/upi.php?upi_id={}@ybl"
        
        if 'processing_logs' not in st.session_state:
            st.session_state.processing_logs = []
        
        # Create output directories
        os.makedirs('output', exist_ok=True)
        os.makedirs('logs', exist_ok=True)
    
    def run(self):
        """Main application runner"""
        # Title and header
        st.markdown('<h1 class="main-header">💳 UPI Details Extractor</h1>', unsafe_allow_html=True)
        st.markdown("---")
        
        # Sidebar for navigation and controls
        self.create_sidebar()
        
        # Main content area with tabs
        tab1, tab2, tab3, tab4 = st.tabs(["📁 File Upload", "⚙️ Processing", "📊 Results", "📈 Statistics"])
        
        with tab1:
            self.file_upload_tab()
        
        with tab2:
            self.processing_tab()
        
        with tab3:
            self.results_tab()
        
        with tab4:
            self.statistics_tab()
    
    def create_sidebar(self):
        """Create sidebar with controls and settings"""
        st.sidebar.title("🔧 Controls & Settings")
        
        # API Configuration
        st.sidebar.subheader("API Configuration")
        api_url = st.sidebar.text_input(
            "API Endpoint:",
            value=st.session_state.api_url,
            help="UPI lookup API endpoint with {} placeholder for phone number (will be replaced with number@ybl)"
        )
        if api_url != st.session_state.api_url:
            st.session_state.api_url = api_url
        
        # Processing Speed
        st.sidebar.subheader("Processing Settings")
        speed = st.sidebar.slider(
            "Requests per second:",
            min_value=0.1,
            max_value=5.0,
            value=1.0,
            step=0.1,
            help="Control the speed of API requests"
        )
        
        # Quick Stats in Sidebar
        st.sidebar.subheader("📊 Quick Stats")
        col1, col2 = st.sidebar.columns(2)
        
        with col1:
            st.metric("Total", st.session_state.stats['total_processed'])
            st.metric("Failed", st.session_state.stats['failed'])
        
        with col2:
            st.metric("Success", st.session_state.stats['successful'])
            if st.session_state.stats['total_processed'] > 0:
                success_rate = (st.session_state.stats['successful'] / st.session_state.stats['total_processed']) * 100
                st.metric("Success Rate", f"{success_rate:.1f}%")
        
        # Processing Speed Display
        if st.session_state.stats['start_time']:
            elapsed = (datetime.now() - st.session_state.stats['start_time']).total_seconds()
            if elapsed > 0:
                current_speed = st.session_state.stats['total_processed'] / elapsed
                st.sidebar.metric("Current Speed", f"{current_speed:.2f}/sec")
        
        return speed
    
    def file_upload_tab(self):
        """File upload interface"""
        st.subheader("📁 Upload Phone Numbers File")
        
        # File uploader
        uploaded_file = st.file_uploader(
            "Choose a text file with phone numbers (one per line)",
            type=['txt'],
            help="Upload a text file containing phone numbers, one per line"
        )
        
        col1, col2 = st.columns([2, 1])
        
        if uploaded_file is not None:
            # Read and process file
            try:
                content = uploaded_file.read().decode('utf-8')
                lines = content.strip().split('\n')
                
                valid_numbers = []
                invalid_numbers = []
                
                for line_num, line in enumerate(lines, 1):
                    number = line.strip()
                    if number and number.isdigit() and len(number) == 10:
                        valid_numbers.append(number)
                    elif number:
                        invalid_numbers.append(f"Line {line_num}: {number}")
                
                with col1:
                    st.success(f"✅ File processed successfully!")
                    
                    # File information
                    st.write("**File Information:**")
                    info_data = {
                        "Metric": ["Total lines", "Valid phone numbers", "Invalid entries"],
                        "Count": [len(lines), len(valid_numbers), len(invalid_numbers)]
                    }
                    st.table(pd.DataFrame(info_data))
                    
                    # Show valid numbers preview
                    if valid_numbers:
                        st.write("**Valid Numbers (Preview):**")
                        preview_df = pd.DataFrame({
                            "Index": range(1, min(11, len(valid_numbers) + 1)),
                            "Phone Number": valid_numbers[:10]
                        })
                        st.dataframe(preview_df, use_container_width=True)
                        
                        if len(valid_numbers) > 10:
                            st.info(f"... and {len(valid_numbers) - 10} more numbers")
                    
                    # Show invalid entries if any
                    if invalid_numbers:
                        st.write("**Invalid Entries:**")
                        for invalid in invalid_numbers[:5]:
                            st.error(invalid)
                        if len(invalid_numbers) > 5:
                            st.warning(f"... and {len(invalid_numbers) - 5} more invalid entries")
                
                with col2:
                    if st.button("📥 Load Numbers", type="primary", use_container_width=True):
                        st.session_state.phone_numbers = valid_numbers
                        st.session_state.current_index = 0
                        st.session_state.results = []
                        st.session_state.bank_data.clear()
                        st.session_state.stats = {
                            'total_processed': 0,
                            'successful': 0,
                            'failed': 0,
                            'bank_distribution': Counter(),
                            'start_time': None,
                            'processing_speed': 0
                        }
                        st.session_state.processing_logs = []
                        st.success(f"Loaded {len(valid_numbers)} phone numbers!")
                        st.rerun()
                
            except Exception as e:
                st.error(f"❌ Error reading file: {str(e)}")
        
        # Sample file download
        st.markdown("---")
        st.subheader("📄 Sample File")
        
        sample_numbers = [
            "8900200543", "9876543210", "9123456789", "8765432109", "7890123456",
            "9988776655", "8877665544", "7766554433", "9955443322", "8844332211"
        ]
        
        sample_content = "\n".join(sample_numbers)
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.write("Download a sample file to test the application:")
        with col2:
            st.download_button(
                label="📥 Download Sample",
                data=sample_content,
                file_name="sample_numbers.txt",
                mime="text/plain"
            )
    
    def processing_tab(self):
        """Processing interface with controls and progress"""
        st.subheader("⚙️ Processing Controls")
        
        if not st.session_state.phone_numbers:
            st.warning("⚠️ Please upload and load phone numbers first!")
            return
        
        # Control buttons
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.session_state.processing_status in ['idle', 'paused']:
                if st.button("▶️ Start Processing", type="primary", use_container_width=True):
                    self.start_processing()
        
        with col2:
            if st.session_state.processing_status == 'running':
                if st.button("⏸️ Pause", use_container_width=True):
                    st.session_state.processing_status = 'paused'
                    st.rerun()
        
        with col3:
            if st.session_state.processing_status in ['running', 'paused']:
                if st.button("⏹️ Stop", use_container_width=True):
                    st.session_state.processing_status = 'idle'
                    # Don't reset index to allow resuming from current position
                    self.add_log("Processing stopped by user", "warning")
                    st.rerun()
        
        with col4:
            if st.button("🔄 Reset", use_container_width=True):
                self.reset_processing()
        
        # Progress section
        st.markdown("---")
        st.subheader("📊 Progress Tracking")
        
        if st.session_state.phone_numbers:
            progress = (st.session_state.current_index / len(st.session_state.phone_numbers)) * 100
            st.progress(progress / 100)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Progress", f"{st.session_state.current_index}/{len(st.session_state.phone_numbers)}")
            with col2:
                st.metric("Percentage", f"{progress:.1f}%")
            with col3:
                if st.session_state.current_index < len(st.session_state.phone_numbers):
                    current_number = st.session_state.phone_numbers[st.session_state.current_index]
                    st.metric("Current Number", current_number)
                else:
                    st.metric("Status", "Completed" if st.session_state.processing_status == 'completed' else "Ready")
        
        # Live processing logs
        st.markdown("---")
        st.subheader("📝 Live Processing Console")
        
        if st.session_state.processing_logs:
            # Show last 20 log entries
            log_container = st.container()
            with log_container:
                for log_entry in st.session_state.processing_logs[-20:]:
                    timestamp = log_entry['timestamp']
                    message = log_entry['message']
                    level = log_entry['level']
                    
                    if level == 'success':
                        st.markdown(f'<p class="success-message">[{timestamp}] ✅ {message}</p>', unsafe_allow_html=True)
                    elif level == 'error':
                        st.markdown(f'<p class="error-message">[{timestamp}] ❌ {message}</p>', unsafe_allow_html=True)
                    else:
                        st.markdown(f'<p class="info-message">[{timestamp}] ℹ️ {message}</p>', unsafe_allow_html=True)
        else:
            st.info("No processing logs yet. Start processing to see live updates.")
        
        # Auto-refresh and continue processing
        if st.session_state.processing_status == 'running':
            # Continue processing the next number
            if st.session_state.current_index < len(st.session_state.phone_numbers):
                time.sleep(1)  # Add delay to prevent excessive refreshing
                self.process_next_number()
            st.rerun()
    
    def start_processing(self):
        """Start the processing with real-time updates"""
        st.session_state.processing_status = 'running'
        if st.session_state.stats['start_time'] is None:
            st.session_state.stats['start_time'] = datetime.now()
        
        self.add_log("Processing started!", "info")
        st.rerun()
    
    def process_next_number(self):
        """Process the next number in the queue with multiple UPI handle retries"""
        if st.session_state.current_index >= len(st.session_state.phone_numbers):
            st.session_state.processing_status = 'completed'
            self.add_log("Processing completed!", "success")
            st.balloons()  # Celebration effect
            return
        
        number = st.session_state.phone_numbers[st.session_state.current_index]
        
        # List of UPI handles to try in order
        upi_handles = ["@ybl", "@axl", "@ptsbi", "@upi", "@oksbi", "@okaxis", "@okicici", "@ibl", "@okhdfcbank", "@ptyes"]
        
        # Update current processing status
        self.add_log(f"Processing {number}...", "info")
        
        success = False
        last_error = None
        
        for handle in upi_handles:
            try:
                # Build API URL with current handle
                base_url = "https://spyshadow.site/upi.php?upi_id={}"
                url = base_url.format(f"{number}{handle}")
                
                self.add_log(f"Trying {number}{handle}...", "info")
                
                response = requests.get(url, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Check if we got valid data
                    if self.is_valid_response(data):
                        self.process_api_response(number, data, handle)
                        success = True
                        break
                    else:
                        self.add_log(f"No valid data for {number}{handle}", "warning")
                        continue
                else:
                    last_error = f"HTTP {response.status_code}"
                    continue
                    
            except requests.exceptions.Timeout:
                last_error = "Request timeout"
                continue
            except requests.exceptions.RequestException as e:
                last_error = f"Request error: {str(e)}"
                continue
            except json.JSONDecodeError:
                last_error = "Invalid JSON response"
                continue
            except Exception as e:
                last_error = f"Unexpected error: {str(e)}"
                continue
        
        # If no handle worked, log as failed
        if not success:
            self.log_api_error(number, f"All UPI handles failed. Last error: {last_error}")
        
        # Update counters
        st.session_state.current_index += 1
        st.session_state.stats['total_processed'] += 1
    
    def is_valid_response(self, data):
        """Check if API response contains valid UPI data"""
        try:
            # Check if response has valid structure and data
            if not isinstance(data, dict):
                return False
            
            # Check for vpa_details with name
            vpa_details = data.get('data', {}).get('vpa_details', {})
            name = vpa_details.get('name', '').strip()
            
            # Valid if we have a non-empty name
            return bool(name and name.upper() != 'N/A')
            
        except Exception:
            return False
    
    def process_api_response(self, number, data, handle="@ybl"):
        """Process successful API response"""
        try:
            vpa_details = data.get('data', {}).get('vpa_details', {})
            bank_details = data.get('data', {}).get('bank_details_raw', {})
            
            name = vpa_details.get('name', 'N/A')
            bank = bank_details.get('BANK', 'Unknown Bank')
            vpa = vpa_details.get('vpa', 'N/A')
            ifsc = vpa_details.get('ifsc', 'N/A')
            
            result = {
                'mobile': number,
                'name': name,
                'bank': bank,
                'vpa': vpa,
                'ifsc': ifsc,
                'upi_handle': handle,
                'status': 'Success',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'raw_data': data
            }
            
            st.session_state.results.append(result)
            st.session_state.bank_data[bank].append(result)
            st.session_state.stats['successful'] += 1
            st.session_state.stats['bank_distribution'][bank] += 1
            
            self.add_log(f"✅ {number}{handle} → {name} ({bank})", "success")
            
        except Exception as e:
            self.log_api_error(number, f"Data parsing error: {str(e)}")
    
    def log_api_error(self, number, error_msg):
        """Log API error"""
        result = {
            'mobile': number,
            'name': 'N/A',
            'bank': 'N/A',
            'vpa': 'N/A',
            'ifsc': 'N/A',
            'status': 'Failed',
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'error': error_msg
        }
        
        st.session_state.results.append(result)
        st.session_state.stats['failed'] += 1
        
        self.add_log(f"{number} → {error_msg}", "error")
    
    def add_log(self, message, level="info"):
        """Add log entry"""
        log_entry = {
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'message': message,
            'level': level
        }
        st.session_state.processing_logs.append(log_entry)
        
        # Keep only last 100 log entries
        if len(st.session_state.processing_logs) > 100:
            st.session_state.processing_logs = st.session_state.processing_logs[-100:]
    
    def reset_processing(self):
        """Reset all processing data"""
        st.session_state.current_index = 0
        st.session_state.results = []
        st.session_state.bank_data.clear()
        st.session_state.stats = {
            'total_processed': 0,
            'successful': 0,
            'failed': 0,
            'bank_distribution': Counter(),
            'start_time': None,
            'processing_speed': 0
        }
        st.session_state.processing_logs = []
        st.session_state.processing_status = 'idle'
        st.success("✅ Processing data reset successfully!")
        st.rerun()
    
    def results_tab(self):
        """Display results with search and filter capabilities"""
        st.subheader("📊 Extraction Results")
        
        if not st.session_state.results:
            st.info("No results yet. Start processing to see extracted UPI details.")
            return
        
        # Search and filter controls
        col1, col2, col3 = st.columns([2, 2, 1])
        
        with col1:
            search_term = st.text_input("🔍 Search:", placeholder="Search by name, bank, mobile, or VPA")
        
        with col2:
            # Get unique banks for filter
            banks = list(set([r['bank'] for r in st.session_state.results if r['bank'] != 'N/A']))
            bank_filter = st.selectbox("🏦 Filter by Bank:", ['All'] + sorted(banks))
        
        with col3:
            if st.button("🗑️ Clear Filters"):
                st.rerun()
        
        # Filter results
        filtered_results = st.session_state.results.copy()
        
        if search_term:
            filtered_results = [
                r for r in filtered_results
                if search_term.lower() in f"{r['mobile']} {r['name']} {r['bank']} {r['vpa']}".lower()
            ]
        
        if bank_filter and bank_filter != 'All':
            filtered_results = [r for r in filtered_results if r['bank'] == bank_filter]
        
        # Display results summary
        st.markdown("---")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Results", len(filtered_results))
        with col2:
            successful = len([r for r in filtered_results if r['status'] == 'Success'])
            st.metric("Successful", successful)
        with col3:
            failed = len([r for r in filtered_results if r['status'] == 'Failed'])
            st.metric("Failed", failed)
        with col4:
            if len(filtered_results) > 0:
                success_rate = (successful / len(filtered_results)) * 100
                st.metric("Success Rate", f"{success_rate:.1f}%")
        
        # Results table
        if filtered_results:
            df = pd.DataFrame(filtered_results)
            columns_to_show = ['mobile', 'name', 'bank', 'vpa', 'ifsc', 'status', 'timestamp']
            # Add UPI handle column if it exists
            if any('upi_handle' in result for result in filtered_results):
                columns_to_show.insert(-2, 'upi_handle')
            
            df = df[columns_to_show].copy()
            df.columns = ['Mobile', 'Name', 'Bank', 'VPA', 'IFSC'] + (['UPI Handle', 'Status', 'Timestamp'] if 'upi_handle' in columns_to_show else ['Status', 'Timestamp'])
            
            # Add status emoji
            status_mapping = {'Success': '✅ Success', 'Failed': '❌ Failed'}
            df.loc[:, 'Status'] = df['Status'].replace(status_mapping)
            
            st.dataframe(
                df,
                use_container_width=True,
                height=400,
                column_config={
                    "Mobile": st.column_config.TextColumn("Mobile", width="medium"),
                    "Name": st.column_config.TextColumn("Name", width="large"),
                    "Bank": st.column_config.TextColumn("Bank", width="large"),
                    "VPA": st.column_config.TextColumn("VPA", width="large"),
                    "IFSC": st.column_config.TextColumn("IFSC", width="medium"),
                    "Status": st.column_config.TextColumn("Status", width="small"),
                }
            )
        
        # Export options
        st.markdown("---")
        st.subheader("📤 Export Options")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("📊 Export CSV", use_container_width=True):
                self.export_csv(filtered_results)
        
        with col2:
            if st.button("📈 Export Excel", use_container_width=True):
                self.export_excel(filtered_results)
        
        with col3:
            if st.button("📁 Bank-wise Files", use_container_width=True):
                self.export_bank_wise()
        
        with col4:
            if st.button("📋 Summary Report", use_container_width=True):
                self.generate_summary_report()
    
    def statistics_tab(self):
        """Display statistics and charts"""
        st.subheader("📈 Statistics & Analytics")
        
        if not st.session_state.results:
            st.info("No data available. Start processing to see statistics.")
            return
        
        # Overall statistics
        successful_results = [r for r in st.session_state.results if r['status'] == 'Success']
        failed_results = [r for r in st.session_state.results if r['status'] == 'Failed']
        
        # Metrics row
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Processed", st.session_state.stats['total_processed'])
        with col2:
            st.metric("Successful", st.session_state.stats['successful'])
        with col3:
            st.metric("Failed", st.session_state.stats['failed'])
        with col4:
            if st.session_state.stats['total_processed'] > 0:
                success_rate = (st.session_state.stats['successful'] / st.session_state.stats['total_processed']) * 100
                st.metric("Success Rate", f"{success_rate:.1f}%")
        
        if not st.session_state.stats['bank_distribution']:
            st.warning("No successful extractions yet to display bank statistics.")
            return
        
        # Bank distribution charts
        st.markdown("---")
        st.subheader("🏦 Bank Distribution Analysis")
        
        # Prepare data for charts
        banks = list(st.session_state.stats['bank_distribution'].keys())
        counts = list(st.session_state.stats['bank_distribution'].values())
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Pie chart
            fig_pie = px.pie(
                values=counts,
                names=banks,
                title="Bank Distribution (Pie Chart)",
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with col2:
            # Bar chart
            fig_bar = px.bar(
                x=banks,
                y=counts,
                title="Bank Distribution (Bar Chart)",
                labels={'x': 'Banks', 'y': 'Count'},
                color=counts,
                color_continuous_scale='viridis'
            )
            fig_bar.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig_bar, use_container_width=True)
        
        # Detailed bank statistics table
        st.markdown("---")
        st.subheader("📊 Detailed Bank Statistics")
        
        bank_stats = []
        for bank, count in st.session_state.stats['bank_distribution'].most_common():
            percentage = (count / st.session_state.stats['successful']) * 100
            bank_stats.append({
                'Bank': bank,
                'Count': count,
                'Percentage': f"{percentage:.1f}%"
            })
        
        st.dataframe(pd.DataFrame(bank_stats), use_container_width=True)
        
        # Processing timeline (if available)
        if st.session_state.stats['start_time']:
            st.markdown("---")
            st.subheader("⏱️ Processing Performance")
            
            elapsed = (datetime.now() - st.session_state.stats['start_time']).total_seconds()
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Processing Time", f"{elapsed:.1f} seconds")
            with col2:
                if elapsed > 0:
                    avg_speed = st.session_state.stats['total_processed'] / elapsed
                    st.metric("Average Speed", f"{avg_speed:.2f}/sec")
            with col3:
                if st.session_state.stats['total_processed'] > 0:
                    avg_time_per_request = elapsed / st.session_state.stats['total_processed']
                    st.metric("Avg Time/Request", f"{avg_time_per_request:.2f}s")
    
    def export_csv(self, results):
        """Export results to CSV"""
        try:
            df = pd.DataFrame(results)
            columns_to_export = ['mobile', 'name', 'bank', 'vpa', 'ifsc', 'status', 'timestamp']
            # Add UPI handle column if it exists
            if any('upi_handle' in result for result in results):
                columns_to_export.insert(-2, 'upi_handle')
            df = df[columns_to_export]
            
            csv_buffer = io.StringIO()
            df.to_csv(csv_buffer, index=False)
            csv_data = csv_buffer.getvalue()
            
            st.download_button(
                label="📥 Download CSV",
                data=csv_data,
                file_name=f"upi_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
            
        except Exception as e:
            st.error(f"❌ Failed to export CSV: {str(e)}")
    
    def export_excel(self, results):
        """Export results to Excel"""
        try:
            df = pd.DataFrame(results)
            columns_to_export = ['mobile', 'name', 'bank', 'vpa', 'ifsc', 'status', 'timestamp']
            # Add UPI handle column if it exists
            if any('upi_handle' in result for result in results):
                columns_to_export.insert(-2, 'upi_handle')
            df = df[columns_to_export]
            
            excel_buffer = io.BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='UPI Results', index=False)
            excel_buffer.seek(0)
            
            excel_data = excel_buffer.getvalue()
            
            st.download_button(
                label="📥 Download Excel",
                data=excel_data,
                file_name=f"upi_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
        except Exception as e:
            st.error(f"❌ Failed to export Excel: {str(e)}")
    
    def export_bank_wise(self):
        """Generate bank-wise text files"""
        if not st.session_state.bank_data:
            st.warning("No bank data available for export.")
            return
        
        try:
            exported_files = []
            
            for bank, records in st.session_state.bank_data.items():
                # Clean bank name for filename
                safe_bank_name = "".join(c for c in bank if c.isalnum() or c in (' ', '-', '_')).strip()
                safe_bank_name = safe_bank_name.replace(' ', '_')
                
                # Create file content
                content = []
                content.append(f"Bank: {bank}")
                content.append(f"Total Records: {len(records)}")
                content.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                content.append("-" * 50)
                content.append("")
                
                for record in records:
                    content.append(f"Mobile: {record['mobile']}")
                    content.append(f"Name: {record['name']}")
                    content.append(f"VPA: {record['vpa']}")
                    content.append(f"IFSC: {record['ifsc']}")
                    if 'upi_handle' in record:
                        content.append(f"UPI Handle: {record['upi_handle']}")
                    content.append(f"Status: {record['status']}")
                    content.append(f"Timestamp: {record['timestamp']}")
                    content.append("-" * 30)
                
                file_content = "\n".join(content)
                
                # Create download button for this bank
                st.download_button(
                    label=f"📥 Download {bank} Data",
                    data=file_content,
                    file_name=f"{safe_bank_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                    mime="text/plain",
                    key=f"bank_{safe_bank_name}"  # Unique key for each button
                )
                
                exported_files.append(bank)
            
            st.success(f"✅ Generated {len(exported_files)} bank-wise files: {', '.join(exported_files)}")
            
        except Exception as e:
            st.error(f"❌ Failed to generate bank-wise files: {str(e)}")
    
    def generate_summary_report(self):
        """Generate comprehensive summary report"""
        try:
            summary = []
            summary.append("UPI DETAILS EXTRACTION SUMMARY REPORT")
            summary.append("=" * 50)
            summary.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            summary.append("")
            
            # Overall statistics
            summary.append("OVERALL STATISTICS:")
            summary.append(f"Total Numbers Processed: {st.session_state.stats['total_processed']}")
            summary.append(f"Successful Extractions: {st.session_state.stats['successful']}")
            summary.append(f"Failed Attempts: {st.session_state.stats['failed']}")
            if st.session_state.stats['total_processed'] > 0:
                success_rate = (st.session_state.stats['successful'] / st.session_state.stats['total_processed']) * 100
                summary.append(f"Success Rate: {success_rate:.2f}%")
            summary.append("")
            
            # Processing time
            if st.session_state.stats['start_time']:
                elapsed = (datetime.now() - st.session_state.stats['start_time']).total_seconds()
                summary.append(f"Processing Time: {elapsed:.2f} seconds")
                if elapsed > 0:
                    avg_speed = st.session_state.stats['total_processed'] / elapsed
                    summary.append(f"Average Speed: {avg_speed:.2f} requests/second")
                summary.append("")
            
            # Bank distribution
            if st.session_state.stats['bank_distribution']:
                summary.append("BANK DISTRIBUTION:")
                for bank, count in st.session_state.stats['bank_distribution'].most_common():
                    percentage = (count / st.session_state.stats['successful']) * 100
                    summary.append(f"{bank}: {count} ({percentage:.1f}%)")
                summary.append("")
            
            # Sample successful extractions
            successful_results = [r for r in st.session_state.results if r['status'] == 'Success']
            if successful_results:
                summary.append("SAMPLE SUCCESSFUL EXTRACTIONS (First 10):")
                for i, result in enumerate(successful_results[:10], 1):
                    summary.append(f"{i:2d}. {result['mobile']} -> {result['name']} ({result['bank']})")
                summary.append("")
            
            summary_text = "\n".join(summary)
            
            # Create download button
            st.download_button(
                label="📥 Download Summary Report",
                data=summary_text,
                file_name=f"summary_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain"
            )
            
            # Also display in expandable section
            with st.expander("📋 View Summary Report"):
                st.text(summary_text)
            
        except Exception as e:
            st.error(f"❌ Failed to generate summary report: {str(e)}")


def main():
    """Main function to run the Streamlit app"""
    app = UPIExtractorWeb()
    app.run()


if __name__ == "__main__":
    main()