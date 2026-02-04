# Steam Game Data Acquisition Pipeline

## 🎯 Project Objective
This project focuses on API-based data acquisition from SteamSpy and the official Steam Web API.  
The goal is to collect, clean, and aggregate large-scale Steam game data, then construct standardized metrics to evaluate game popularity and player engagement across the platform.

---

## 🕹️ Project Overview
This project retrieves data for **1,500 Steam games** using public APIs rather than traditional web crawling techniques.  
Multiple indicators—including ownership estimates, recent player activity, review sentiment, achievement completion rates, and peak concurrent users—are integrated into a unified dataset.  

A composite **heat score** is then calculated to rank games based on overall market activity and player engagement.

---

## 🔧 Key Features

### API-Based Data Collection
- Collects data exclusively from SteamSpy API and the official Steam Web API  
- Avoids HTML parsing and browser simulation  

### Multi-Source Metric Aggregation
- Ownership estimates  
- Recent two-week player activity  
- Review sentiment (positive / negative ratio)  
- Global achievement completion rates  
- Peak concurrent user counts  

### Engagement-Oriented Indicators
- Active owner rate (recent players / total owners)  
- Average achievement completion as a proxy for engagement depth  

### Heat Score Construction
- Normalizes key indicators to a 0–1 scale  
- Computes a weighted composite popularity index  
- Produces interpretable rankings rather than black-box outputs  

### Rate-Limit Friendly Design
- Implements sleep intervals between API requests  
- Includes retry logic to improve execution stability  

---

## 📁 Project Structure
.
```
├── Steam Game Data Acquisition Pipeline.py   # Main data acquisition and metric pipeline
├── .gitignore
└── README.md
```

---

## 🚀 Quick Start

### Requirements
- Python 3.8+
- requests
- pandas

### Install Dependencies
```bash
pip install requests pandas
```

### Run the Script
```bash
python steam_collect_1500.py
```

---

### 📤 Output
```text
steam_1500_games_metrics_with_heat.csv
```

---

### 🧠 Design Notes
- Data collection relies entirely on structured JSON APIs rather than web crawling techniques  
- Metric normalization is applied to reduce scale differences across indicators  
- The heat score is designed as an interpretable composite index rather than a black-box model  

---

### 📌 Notes
This project is intended for **data analysis, research, and portfolio demonstration purposes**.  
It emphasizes **data acquisition methodology, metric design, and analytical structure**, rather than real-time system optimization or production-level deployment.