# Overview

This is a GUI-based UPI (Unified Payments Interface) details extractor application built with Python and Tkinter. The application allows users to input phone numbers and extract associated UPI payment details by making API calls to an external service. It features a comprehensive interface for batch processing phone numbers, visualizing results with charts, and exporting data in multiple formats.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Frontend Architecture
- **GUI Framework**: Tkinter-based desktop application with ttk widgets for modern styling
- **Layout Design**: Multi-tab interface supporting input, processing, results visualization, and statistics
- **User Interaction**: File upload for batch phone number processing, real-time progress tracking, and interactive data visualization

## Core Processing Engine
- **Threading Model**: Asynchronous processing using Python threading to prevent GUI freezing during API calls
- **State Management**: Centralized application state tracking processing status, pause/resume functionality, and current progress
- **Error Handling**: Comprehensive error tracking and logging for failed API requests and invalid responses

## Data Processing Pipeline
- **Input Validation**: Phone number format validation and duplicate removal
- **API Integration**: HTTP requests to external UPI lookup service with rate limiting and retry mechanisms
- **Result Processing**: JSON response parsing and data normalization for consistent output format

## Visualization Components
- **Charts and Graphs**: Matplotlib integration for bank distribution charts and processing statistics
- **Real-time Updates**: Live progress bars and status indicators during batch processing
- **Data Tables**: Scrollable result tables with sorting and filtering capabilities

## Export Functionality
- **Multiple Formats**: CSV, JSON, and Excel export options for processed data
- **Bank-wise Segmentation**: Separate data exports organized by banking institution
- **Report Generation**: Statistical summaries and processing reports

# External Dependencies

## Third-party APIs
- **UPI Lookup Service**: External API endpoint at `Spyshadow.site/upi.php` for UPI details retrieval
- **Rate Limiting**: Built-in delays and request throttling to respect API limitations

## Python Libraries
- **GUI Framework**: `tkinter` and `ttk` for user interface components
- **HTTP Client**: `requests` library for API communication
- **Data Processing**: `pandas` for data manipulation and analysis
- **Visualization**: `matplotlib` for chart generation and statistical plots
- **File Handling**: Built-in `csv` and `json` modules for data export

## System Dependencies
- **File System**: Local file operations for input/output and temporary data storage
- **Threading**: Python's built-in threading module for concurrent processing
- **Logging**: Standard logging framework for error tracking and debugging