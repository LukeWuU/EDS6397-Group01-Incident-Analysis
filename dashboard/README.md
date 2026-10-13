# Integration & Dashboard (Audrey)

## 🌐 Live Dashboard

**Application:** Real-Time Incident Tracker

Incident Tracker Dashboard:
https://incident-tracker.audreyrah.com/

This folder contains the final integration and dashboard components for the **EDS6397 Group 01 Incident Analysis Project**. The interactive dashboard is deployed on my website and demonstrates real-time incident monitoring, severity prioritization, geographic hotspot analysis, confidence assessment, and operational decision support using the integrated multimodal incident dataset. :contentReference[oaicite:0]{index=0}

---
# Dashboard Preview

## Real-Time Incident Intelligence Dashboard

<p align="center">
  <img src="file/real_time_incident_intelligence_dashboard.png" width="100%">
</p>

**Figure 1.** Real-Time Incident Intelligence Dashboard for multimodal incident monitoring, severity prioritization, confidence assessment, geographic hotspot analysis, and operational decision support.

---

## Incident Command Center Dashboard

<p align="center">
  <img src="file/Incident Command Center Dashboard.png" width="100%">
</p>

**Figure 2.** Incident Command Center Dashboard illustrating real-time incident tracking, operational monitoring, incident prioritization, geographic awareness, and response decision support.

---

## Input Files

Expected outputs:

- audio_incidents.csv
- document_incidents.csv
- image_incidents.csv
- video_incidents.csv
- text_incidents.csv

## Integration Tasks

- Validate Incident_ID ranges
- Verify schema consistency
- Merge component outputs
- Handle missing values
- Generate severity classifications
- Create unified dataset

## Common Schema

- Incident_ID
- Event_Type
- Source_Type
- Date_Time
- Location
- Confidence_Score
- Summary

Generated during integration:

- Severity

## Output

- final_incidents.csv

## Dashboard Features

- Executive Summary
- Real-Time Incident Monitoring
- Incident Priority Queue
- Severity Analysis
- Event Type Analysis
- Source Type Distribution
- Confidence Score Analysis
- Timeline Analysis
- Geographic Hotspot Analysis
- Data Quality Assessment
- Incident Investigation Table
- Operational Decision Support

## Components

- [x] Document
- [x] Image
- [x] Video
- [x] Text
- [x] Audio



