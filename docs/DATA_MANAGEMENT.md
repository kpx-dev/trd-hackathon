# Data Management Strategy

## Large File Handling

The telemetry datasets are extremely large (1-3GB+ each) and exceed GitHub's file size limits. Here's our approach:

### What's Tracked in Git
- ✅ Lap timing data (small CSV files)
- ✅ Weather data 
- ✅ Analysis files (best laps, endurance data)
- ✅ Track maps and documentation
- ✅ Code and analysis notebooks

### What's Excluded (Too Large)
- ❌ Raw telemetry data files (*_telemetry_data.csv)
- ❌ Files over 100MB

## Local Development Setup

1. **Keep telemetry files locally** in `dataset/data_files/` for development
2. **Use smaller sample datasets** for initial prototyping
3. **Focus on lap timing and weather data** which contain the key insights
4. **Create processed/aggregated datasets** from telemetry for sharing

## Alternative Data Sharing Options

For the hackathon submission:

1. **Cloud Storage**: Upload large files to Google Drive/Dropbox and share links
2. **Data Sampling**: Create representative samples of telemetry data
3. **Processed Features**: Extract key features from telemetry into smaller files
4. **Documentation**: Clearly document data sources and processing steps

## Recommended Workflow

1. Develop using available smaller datasets (lap times, weather, analysis files)
2. Use telemetry data locally for model training
3. Create feature extraction pipeline to reduce data size
4. Share processed features and models in the repository
5. Document full data pipeline for judges

This approach keeps the repository manageable while maintaining full analytical capability.