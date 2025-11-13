# Toyota GR Cup Race Replay Viewer

A comprehensive web-based race replay and telemetry visualization application for the Toyota GR Cup North America series. This interactive application displays race track maps, real-time telemetry data, and provides race replay functionality with timeline controls.

## Features

- **Interactive Track Map Display**: View detailed race track maps with full zoom and pan capabilities
- **Race Telemetry Visualization**: Real-time display of car positions, telemetry data, and race progress
- **Multi-Race Support**: Select and view different races (Race 1, Race 2) with separate datasets
- **Car Selection**: Choose specific cars to follow and analyze their performance
- **Timeline Controls**:
  - Scrub through race time with an interactive slider
  - Jump forward/backward by 10 seconds
  - Jump to specific laps
  - View current lap information and race time
- **Toyota GR Cup Branding**: Official branding and track information integration
- **D3.js Powered**: Smooth SVG-based rendering for optimal performance
- **Responsive Design**: Works across desktop and mobile devices
- **Cache Management**: Built-in cache clearing functionality for development

## Project Structure

### Core Application Files
- `index.html` - Main application interface with Toyota GR Cup branding
- `track-map.js` - Main JavaScript application with D3.js visualization and telemetry handling
- `serve.py` - Custom Python HTTP server with CORS support and proper MIME types

### Assets and Data
- `gr_cup_namer.png` - Official Toyota GR Cup North America logo
- `gr_cup_track_info.csv` - Track information database (dates, lengths, locations)
- `race_maps/barber motorsports park.png` - High-resolution track map image

### Telemetry Data Files
- `R1_sample_telemetry.csv` - Race 1 sample telemetry data
- `R2_sample_telemetry.csv` - Race 2 sample telemetry data
- `R1_barber_telemetry_data_copy.csv` - Race 1 Barber Motorsports Park telemetry
- `R2_barber_telemetry_data_copy.csv` - Race 2 Barber Motorsports Park telemetry
- `R1_full_gps_sample.csv` - Race 1 GPS positioning data sample
- `R1_full_track_gps.csv` - Complete Race 1 track GPS data
- `R1_complete_race_gps.csv` - Full Race 1 GPS dataset
- `R1_full_race_balanced.csv` - Balanced Race 1 dataset
- `R1_smooth_race_gps.csv` - Smoothed Race 1 GPS data for visualization
- `R1_sample_telemetry.csv` - Race 1 sample telemetry data

### Utility Files
- `clear-cache.html` - Development utility for clearing browser cache and localStorage

## Getting Started

### Prerequisites
- Python 3.x for running the local server
- Modern web browser with JavaScript and SVG support
- CSV telemetry data files (included in the project)

### Option 1: Custom Python Server (Recommended)

The project includes a custom Python server with CORS support and proper MIME type handling:

1. Navigate to the `race_replay` directory
2. Run the custom server:
   ```bash
   python serve.py
   ```
3. Open your browser and navigate to `http://localhost:8000`

The custom server provides:
- CORS headers for local file access
- Proper MIME types for JavaScript and PNG files
- Automatic directory serving from the script location
- Error handling for port conflicts

### Option 2: Alternative HTTP Servers

You can use any HTTP server, but may need to handle CORS manually:

```bash
# Using Python's built-in server
python -m http.server 8000

# Using Node.js http-server (if installed)
npx http-server -p 8000 --cors

# Using PHP (if installed)
php -S localhost:8000
```

### Option 3: Cache Clearing (Development)

For development or if you encounter caching issues:
1. Navigate to `http://localhost:8000/clear-cache.html`
2. This will clear localStorage/sessionStorage and reload the application

## User Interface Controls

### Race Selection
- **Race Dropdown**: Switch between Race 1 and Race 2 datasets
- **Car Dropdown**: Select specific cars to follow and analyze
- **Dynamic Loading**: Car list updates automatically based on selected race

### Timeline Navigation
- **Time Slider**: Scrub through the entire race duration
- **Jump Controls**: Quick navigation buttons
  - `-10s` / `+10s`: Jump backward/forward by 10 seconds
  - **Lap Selector**: Jump directly to any lap in the race
- **Time Display**: Shows current time, total race time, and current lap

### Map Interaction
- **Mouse Wheel**: Zoom in/out on the track map
- **Click and Drag**: Pan around the map
- **Touch Support**: Full mobile device support for touch gestures

## Technical Details

### Dependencies
- **D3.js v7**: Loaded from CDN for SVG manipulation and data visualization
- **Python 3.x**: For the custom HTTP server
- **CSV Data**: Telemetry and GPS data in CSV format for race replay

### Architecture
- **Frontend**: Vanilla JavaScript with D3.js for visualization
- **Backend**: Python HTTP server with CORS and MIME type support
- **Data Format**: CSV files for telemetry data with timestamps and vehicle information
- **No Build Process**: Runs directly in the browser without compilation

### Data Structure
The telemetry CSV files contain:
- `timestamp`: Race time for each data point
- `vehicle_id` / `vehicle_number`: Car identification
- `telemetry_name`: Type of telemetry data (accx_can, accy_can, aps, etc.)
- `telemetry_value`: Sensor readings and measurements
- `lap`: Current lap number
- `meta_*` fields: Event, session, and source metadata

### Browser Compatibility
- Modern browsers with SVG, JavaScript ES6+, and Fetch API support
- Chrome 60+, Firefox 55+, Safari 12+, Edge 79+
- Mobile browsers with touch gesture support

### Performance Optimizations
- **Efficient Data Loading**: Asynchronous CSV parsing with fetch API
- **SVG Rendering**: Hardware-accelerated vector graphics
- **Event Debouncing**: Smooth timeline scrubbing without performance loss
- **Memory Management**: Efficient handling of large telemetry datasets

## Data Management

### Telemetry Data Format
The application supports multiple data types:
- **Sample Data**: `R1_sample_telemetry.csv`, `R2_sample_telemetry.csv`
- **Full Datasets**: Complete race telemetry with all sensors
- **GPS Data**: Positioning data for track visualization
- **Processed Data**: Smoothed and balanced datasets for optimal display

### Track Information
- `gr_cup_track_info.csv`: Contains track metadata including:
  - Track names and locations
  - Race dates and event information
  - Track lengths and specifications

## Customization

### Adding New Tracks
1. Add track map image to `race_maps/` directory
2. Update `gr_cup_track_info.csv` with track information
3. Modify `loadTrackData()` function in `track-map.js` to handle new track
4. Update telemetry data file naming convention

### Adding New Races
1. Create new CSV files following naming pattern: `R#_*_telemetry.csv`
2. Update race selector options in `index.html`
3. Modify `selectedRace` handling in `track-map.js`

### Styling Customization
- **CSS Variables**: Modify color scheme in `index.html` styles
- **Layout**: Adjust responsive breakpoints and container sizes
- **Branding**: Update logos and Toyota GR Cup branding elements
- **Timeline**: Customize slider appearance and control styling

## Troubleshooting

### Common Issues

**Server Not Starting**
- **Port 8000 in use**: The custom server checks for port conflicts
- **Solution**: Stop existing server or the script will suggest alternatives
- **Check**: Use `lsof -i :8000` to see what's using the port

**Data Not Loading**
- **CSV files missing**: Ensure all telemetry CSV files are in the directory
- **CORS errors**: Use the provided `serve.py` instead of basic HTTP servers
- **File paths**: Check browser console for 404 errors on missing files

**Performance Issues**
- **Large datasets**: Some telemetry files contain extensive data
- **Memory usage**: Monitor browser memory with large GPS datasets
- **Rendering**: Reduce timeline scrubbing speed for smoother performance

**UI Not Responsive**
- **JavaScript errors**: Check browser developer console for errors
- **D3.js loading**: Verify CDN connection and D3.js library loading
- **Cache issues**: Use `clear-cache.html` to reset application state

### Development Issues

**Race/Car Selection Not Working**
- Verify CSV file naming matches expected patterns (`R1_*`, `R2_*`)
- Check `vehicle_id` and `vehicle_number` fields in telemetry data
- Ensure proper CSV parsing in `loadTelemetryData()` function

**Timeline Not Updating**
- Check timestamp format in CSV files (should be ISO 8601)
- Verify lap number data consistency across telemetry files
- Monitor console for data parsing errors

## Development and Enhancement

### Current Toyota GR Cup Integration
- **Barber Motorsports Park**: Currently configured track
- **Multi-race Support**: Race 1 and Race 2 dataset handling
- **Official Branding**: Toyota GR Cup North America logos and styling
- **Track Database**: CSV-based track information system

### Planned Enhancements
Based on the current codebase structure, potential improvements include:

**Multi-Track Support**
- Extend `gr_cup_track_info.csv` with additional Toyota GR Cup venues
- Dynamic track map loading based on event selection
- Track-specific telemetry data organization

**Enhanced Telemetry Visualization**
- Real-time car position markers on track map
- Telemetry data overlays (speed, acceleration, brake pressure)
- Sector timing analysis and comparison tools
- Racing line visualization from GPS data

**Advanced Race Analysis**
- Lap time comparison between cars and races
- Telemetry data graphing and analysis tools
- Race strategy analysis using crew chief data
- Performance metrics and driver comparison

**Data Export and Sharing**
- Export race replay segments
- Share specific race moments with timestamps
- Data analysis report generation
- Integration with racing analysis tools

### Contributing to Development
1. Follow the existing code structure and naming conventions
2. Test with provided sample data before adding new features
3. Ensure mobile responsiveness for all new UI elements
4. Maintain Toyota GR Cup branding consistency
5. Document any new CSV data format requirements