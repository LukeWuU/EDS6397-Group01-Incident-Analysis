# EDS6397-Group01-Incident-Analysis

**University of Houston**
**EDS 6397 – Summer 2026**
**Group 01 Project Repository**


This repository contains the Group 01 project for EDS 6397. The project focuses on extracting and analyzing incident-related information from multiple data sources, including audio, documents, images, video, and text. The outputs from all components will be integrated into a unified incident dataset and presented through a dashboard.

## Team Members & Roles

* Audio Processing: Kashfin, MD
* Document Processing: Francisco H. Reyes
* Image Processing: Alex Landon
* Video Processing: Roberto Gomez
* Text Processing: Lujia Wu
* Integration & Dashboard Lead: Audrey Rah

## Common Output Format

* Incident_ID (Format: INC-YYYY-NNNNNN)
* Event_Type
* Source_Type
* Date_Time
* Location
* Confidence_Score
* Summary

## Incident_ID Allocation

To avoid duplicate Incident_ID values during integration, each component uses a reserved ID range:

* Audio: INC-2026-000001 to INC-2026-000999
* Document: INC-2026-001000 to INC-2026-001999
* Image: INC-2026-002000 to INC-2026-002999
* Video: INC-2026-003000 to INC-2026-003999
* Text: INC-2026-004000 to INC-2026-004999

## Final Integration Task

* Define a common Incident_ID key across all outputs
* Merge all component outputs into a unified dataset
* Handle missing values where a modality has no data
* Generate final severity classifications
* Build a dashboard for filtering and viewing incidents

## Integration and Dashboard

* Use the Incident_ID format: INC-YYYY-NNNNNN
* Follow the reserved Incident_ID ranges defined above
* Merge outputs from all project components
* Handle missing values
* Create severity classifications
* Build the final dashboard

## Project Deadline

June 28, 2026
