# Toyota GR Cup Racing Replay & Analysis

[![Python 3.13](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **Interactive Racing Telemetry Replay & AI Coaching System**
> Real-time race data visualization with intelligent performance analysis

## 🏁 Project Overview

This is an interactive web-based racing replay application that visualizes Toyota GR Cup telemetry data with an integrated AI racing coach. The system provides comprehensive race analysis, telemetry visualization, and AI-powered coaching insights for racing performance improvement.

### 🚀 Core Features

- **Interactive Race Replay**: Real-time visualization of car movement on track with full telemetry data
- **AI Racing Coach**: Powered by Strands Agents SDK with access to comprehensive racing data
- **PDF Report Generation**: Professional performance analysis reports with optimized formatting
- **Live Telemetry Display**: Real-time speed, RPM, throttle, brake, steering, and G-force data
- **Lap Analysis**: Detailed lap timing, sector analysis, and performance comparisons
- **GPS Trace Visualization**: Precise car positioning with racing line overlay
- **Auto-Detection**: Automatic AWS region and account detection for seamless setup

## 🗺️ Available Data

Datasets are available here: [https://trddev.com/hackathon-2025/](https://trddev.com/hackathon-2025/)

The application includes comprehensive Toyota GR Cup racing data from Barber Motorsports Park:

- **Race Data**: R1 (Race 1) and R2 (Race 2) complete datasets
- **Telemetry**: High-frequency GPS, speed, throttle, brake, steering, G-forces
- **Lap Timing**: Sector splits, best laps, lap comparisons, pit stop analysis
- **Weather Data**: Track conditions, temperature, humidity, wind data
- **Track Layout**: 15-turn circuit with sector boundaries and corner analysis

## 🚀 Quick Start

### Prerequisites

- Python 3.13+
- [uv](https://github.com/astral-sh/uv) package manager
- Git LFS (for large telemetry files)

### Installation

```bash
# Clone the repository
git clone https://github.com/your-username/trd-hackathon.git
cd trd-hackathon

# Install dependencies
uv sync

# Start the application
python api_server.py
```

### Access the Application

1. **Start the server**: `python api_server.py`
2. **Open browser**: Navigate to `http://localhost:8001`
3. **Select race**: Choose R1 or R2 from the dropdown
4. **Select car**: Pick a car from the available vehicles
5. **Explore**: Use playback controls to replay races and analyze performance

## 🏗️ Application Architecture

```
trd-hackathon/
├── api_server.py              # Flask backend with telemetry API
├── racing_agent.py            # Strands AI agent for racing analysis
├── race_replay/               # Frontend web application
│   ├── index.html            # Main application interface
│   ├── track-map.js          # D3.js visualization & controls
│   └── race_maps/            # Track map images
├── dataset/                  # Racing telemetry data (Git LFS)
├── pyproject.toml           # Dependencies and configuration
└── .gitattributes          # Git LFS configuration for data files
```

## 🎯 Key Components

### Backend (api_server.py)
- **Flask REST API** with CORS support for browser requests
- **Chunked data loading** for smooth telemetry playback
- **AWS auto-detection** using boto3 for seamless cloud deployment
- **Caching system** for optimized data access
- **Multi-race support** with R1/R2 datasets

### AI Racing Coach (racing_agent.py)
- **Strands Agents SDK** integration for intelligent analysis
- **6 specialized tools** for comprehensive racing data access:
  - Telemetry Analysis (throttle, brake, steering technique)
  - Best Laps Data (competitive performance rankings)
  - Race Results Analysis (positions, gaps, finishing data)
  - Lap Sector Analysis (sector splits, improvements, pit stops)
  - Track Position Analysis (corner-by-corner location awareness)
  - Weather Conditions (environmental impact on performance)

### Frontend (race_replay/)
- **Interactive track map** with D3.js visualization
- **Real-time telemetry display** with live data updates
- **Video-style controls** (play, pause, step forward/backward)
- **Lap jumping** with dropdown navigation
- **AI chat interface** for performance coaching questions
- **PDF report generation** with jsPDF for downloadable analysis
- **Responsive design** for desktop and mobile

## 📊 Racing Analytics Features

### Telemetry Visualization
- GPS-based car positioning on accurate track map
- Real-time speed, RPM, gear, throttle, and brake display
- G-force visualization for cornering and braking analysis
- Steering angle and lap distance tracking

### Performance Analysis
- Best lap identification and comparison
- Sector time analysis with improvement tracking
- Gap analysis between drivers and optimal performance
- Weather impact assessment on lap times

### AI Coaching
- Context-aware coaching based on current track position
- Technique analysis using high-resolution telemetry data
- Comparative performance insights vs. field leaders
- Strategic recommendations for improvement
- **Professional PDF reports** with comprehensive lap analysis
  - Optimized formatting with minimal whitespace
  - Color-coded performance indicators (green for achievements, red for critical findings)
  - Detailed sector-by-sector breakdowns
  - Comparative analysis tables and data visualization
  - Downloadable for offline review and sharing

## 🛠️ API Endpoints

The backend provides comprehensive REST API endpoints:

### Race Management
- `GET /api/races` - Available races
- `GET /api/races/{race_id}/cars` - Cars for specific race

### Telemetry Data
- `GET /api/telemetry/{race_id}/{vehicle_id}/timeline` - Timeline metadata
- `GET /api/telemetry/{race_id}/{vehicle_id}/chunk` - Chunked telemetry data
- `GET /api/telemetry/{race_id}/{vehicle_id}/position` - Position at timestamp

### Performance Data
- `GET /api/laps/{race_id}/{vehicle_id}` - Lap timing and analysis

### AI Assistant
- `GET /api/ai/regions` - AWS region auto-detection
- `POST /api/ai/test-connection` - AI agent connection test
- `POST /api/ai/analyze` - Racing performance analysis

## 🏁 Usage Examples

### Interactive Race Replay
1. Select a race (R1/R2) and car from the dropdowns
2. Use the timeline slider to scrub through the race
3. Watch real-time telemetry data as the car moves around the track
4. Use play/pause controls for automatic playback

### AI Coaching
Ask the AI racing coach questions like:
- "What could I have done better on this lap?"
- "Why was I slower in sector 2?"
- "Compare my braking points to the fastest lap"
- "How can I improve my cornering technique?"
- "Generate a comprehensive performance report for this lap"

**Generate PDF Reports**: Click the "Generate Report" button in the AI Racing Coach panel to create a professional, downloadable PDF analysis of your current lap performance.

### Performance Analysis
- Jump to specific laps using the lap dropdown
- Compare current lap times to your best lap
- Analyze sector splits and identify improvement areas
- Review weather conditions that affected performance

## 🔧 Development

### Dependencies
All dependencies are managed through `pyproject.toml`:
- **Flask & Flask-CORS** for web API
- **Pandas & NumPy** for data processing
- **Boto3** for AWS integration
- **Strands Agents** for AI coaching
- **D3.js** (CDN) for frontend visualization
- **jsPDF** (CDN) for PDF report generation

### Data Management
Large telemetry CSV files are managed using Git LFS:
- Configured in `.gitattributes` for automatic handling
- Local data stored in `dataset/data_files/barber/`
- Efficient chunked loading prevents memory issues

## 📈 Performance Optimizations

- **Chunked data loading** (60-second segments) for smooth playback
- **In-memory caching** with LRU cache for frequently accessed data
- **Background preloading** of upcoming data chunks
- **Efficient GPS coordinate conversion** for track positioning
- **Optimized telemetry sampling** for AI analysis

## 🌐 Deployment

The application automatically detects AWS environment settings:
- **Region detection** via boto3 Session, EC2 metadata, or environment variables
- **Account identification** using AWS STS for proper context
- **Fallback mechanisms** ensure functionality in any environment

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

This racing replay application demonstrates advanced telemetry visualization and AI-powered racing analysis. The codebase showcases integration of modern web technologies with intelligent data processing for motorsports applications.

## 📞 Contact

**TRD Hackathon Team**
Project: Interactive Racing Telemetry Replay & AI Coaching System

---

**Built with ❤️ for the racing community**
