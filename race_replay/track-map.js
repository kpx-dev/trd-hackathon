class TrackMapViewer {
    constructor() {
        this.svg = null;
        this.g = null;
        this.zoom = null;
        this.currentZoom = 1;
        this.imageWidth = 0;
        this.imageHeight = 0;
        this.containerWidth = Math.min(window.innerWidth * 0.9, 1400);
        this.containerHeight = Math.min(window.innerHeight * 0.765, 900);
        this.trackData = null;
        this.selectedRace = 'race1'; // Default to Race 1
        this.telemetryData = [];
        this.availableCars = [];
        this.selectedCar = null;
        this.timelineData = [];
        this.carMarker = null;
        this.showFullTrace = false;

        // Video playback controls
        this.isPlaying = false;
        this.playbackInterval = null;
        this.playbackSpeed = 1; // 1x speed = real race speed

        // Speed unit toggle (default: mph)
        this.speedUnit = 'mph';

        // Lap data
        this.lapData = {
            lapStarts: {},
            lapEnds: {},
            lapTimes: {}
        };

        this.init();
    }

    init() {
        // Set up SVG container
        this.svg = d3.select("#track-map")
            .attr("width", this.containerWidth)
            .attr("height", this.containerHeight);

        // Create main group for transformations
        this.g = this.svg.append("g");

        // Set up zoom behavior
        this.zoom = d3.zoom()
            .scaleExtent([0.1, 10])
            .on("zoom", (event) => {
                this.g.attr("transform", event.transform);
                this.currentZoom = event.transform.k;
            });

        this.svg.call(this.zoom);

        // Load track data first, then the map
        this.loadTrackData();

        // Set up race selector
        this.setupRaceSelector();

        // Set up car selector and timeline
        this.setupCarSelector();
        this.setupTimeline();

        // Handle window resize
        window.addEventListener('resize', () => {
            this.updateContainerSize();
        });
    }

    async loadTrackData() {
        try {
            const response = await fetch('gr_cup_track_info.csv');
            const csvText = await response.text();

            // Parse CSV
            const lines = csvText.trim().split('\n');
            const headers = lines[0].split(',').map(h => h.trim());

            const tracks = [];
            for (let i = 1; i < lines.length; i++) {
                const values = lines[i].split(',').map(v => v.trim());
                const track = {};
                headers.forEach((header, index) => {
                    track[header] = values[index];
                });
                tracks.push(track);
            }

            // Find Barber Motorsports Park data
            this.trackData = tracks.find(track =>
                track.track_name === 'Barber Motorsports Park'
            );

            if (this.trackData) {
                this.updateTitle();
            }

            console.log('Track data loaded:', this.trackData);
        } catch (error) {
            console.error('Failed to load track data:', error);
        }

        // Load the track map image, telemetry data, and lap data
        this.loadTrackMap();
        this.loadTelemetryData();
        this.loadLapData();
    }

    async loadLapData() {
        try {
            console.log('Loading lap data...');

            // Load all lap data files for both races
            const files = [
                'dataset/data_files/barber/R1_barber_lap_start.csv',
                'dataset/data_files/barber/R1_barber_lap_end.csv',
                'dataset/data_files/barber/R1_barber_lap_time.csv',
                'dataset/data_files/barber/R2_barber_lap_start.csv',
                'dataset/data_files/barber/R2_barber_lap_end.csv',
                'dataset/data_files/barber/R2_barber_lap_time.csv'
            ];

            // Load all files in parallel
            const filePromises = files.map(file => this.loadLapDataFile(file));
            await Promise.all(filePromises);

            console.log('All lap data loaded successfully');
            console.log('Lap data structure:', this.lapData);

        } catch (error) {
            console.error('Failed to load lap data:', error);
        }
    }

    async loadLapDataFile(filePath) {
        try {
            const response = await fetch(filePath);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const csvText = await response.text();
            const lines = csvText.trim().split('\n');
            const headers = lines[0].split(',').map(h => h.trim());

            // Parse CSV data
            for (let i = 1; i < lines.length; i++) {
                const values = lines[i].split(',').map(v => v.trim());
                const row = {};
                headers.forEach((header, index) => {
                    row[header] = values[index];
                });

                const vehicleId = row.vehicle_id;
                const lap = parseInt(row.lap);
                const race = row.meta_session; // R1 or R2
                const timestamp = row.timestamp;

                if (!vehicleId || !lap || !race || !timestamp) continue;

                // Determine data type from file path
                let dataType;
                if (filePath.includes('lap_start')) {
                    dataType = 'lapStarts';
                } else if (filePath.includes('lap_end')) {
                    dataType = 'lapEnds';
                } else if (filePath.includes('lap_time')) {
                    dataType = 'lapTimes';
                }

                // Initialize nested structure if needed
                if (!this.lapData[dataType][race]) {
                    this.lapData[dataType][race] = {};
                }
                if (!this.lapData[dataType][race][vehicleId]) {
                    this.lapData[dataType][race][vehicleId] = {};
                }

                // Store the timestamp for this lap
                this.lapData[dataType][race][vehicleId][lap] = timestamp;
            }

            console.log(`Loaded lap data from: ${filePath}`);

        } catch (error) {
            console.error(`Failed to load lap data file ${filePath}:`, error);
        }
    }

    updateTitle() {
        if (!this.trackData) return;

        // Hide the event name since it's now in the logo
        const eventNameElement = document.getElementById('event-name');
        if (eventNameElement) {
            eventNameElement.style.display = 'none';
        }

        // Update track info: "BARBER MOTORSPORTS PARK | 2.38 MILES"
        const trackInfoElement = document.getElementById('track-info');
        if (trackInfoElement) {
            trackInfoElement.textContent =
                `${this.trackData.track_name.toUpperCase()} | ${this.trackData.track_length.toUpperCase()}`;
        }

        // Update event details with race information
        this.updateRaceInTitle();
    }

    setupRaceSelector() {
        const raceDropdown = document.getElementById('race-dropdown');
        if (raceDropdown) {
            raceDropdown.addEventListener('change', (event) => {
                this.selectedRace = event.target.value;
                this.onRaceSelectionChange();
            });

            // Set initial value
            raceDropdown.value = this.selectedRace;
        }
    }

    onRaceSelectionChange() {
        console.log(`Race selection changed to: ${this.selectedRace}`);

        // Pause any ongoing playback
        this.pausePlayback();

        // Clear existing car selection and data
        this.selectedCar = null;
        this.timelineData = [];
        this.telemetryData = [];
        this.availableCars = [];

        // Clear car dropdown
        const carDropdown = document.getElementById('car-dropdown');
        if (carDropdown) {
            carDropdown.innerHTML = '<option value="">Loading cars...</option>';
            carDropdown.value = '';
        }

        // Clear any existing GPS traces and car markers
        this.g.selectAll('.gps-trace').remove();
        this.g.selectAll('.car-marker').remove();

        // Update the title to show which race is selected
        this.updateRaceInTitle();

        // Load car data for the new race selection
        this.loadTelemetryData();
    }

    updateRaceInTitle() {
        // Add race information to the event details
        const eventDetailsElement = document.getElementById('event-details');
        if (eventDetailsElement && this.trackData) {
            const locationParts = this.trackData.location.split(' ');
            const state = locationParts[locationParts.length - 1];
            const city = locationParts.slice(0, -1).join(' ');

            const raceNumber = this.selectedRace === 'race1' ? '1' : '2';
            eventDetailsElement.textContent =
                `${this.trackData.event_dates.toUpperCase()} | ${city.toUpperCase()}, ${state.toUpperCase()} | RACE ${raceNumber}`;
        }
    }

    updateContainerSize() {
        const newWidth = Math.min(window.innerWidth * 0.9, 1400);
        const newHeight = Math.min(window.innerHeight * 0.765, 900);

        if (newWidth !== this.containerWidth || newHeight !== this.containerHeight) {
            this.containerWidth = newWidth;
            this.containerHeight = newHeight;

            this.svg
                .attr("width", this.containerWidth)
                .attr("height", this.containerHeight);

            // Refit the image if it was loaded
            if (this.imageWidth > 0 && this.imageHeight > 0) {
                this.fitToScreen();
            }
        }
    }

    loadTrackMap() {
        // Create a temporary image to get dimensions
        const img = new Image();

        // Add cache-busting timestamp to force reload of updated image
        const timestamp = new Date().getTime();
        const imageUrl = `race_maps/barber motorsports park.png?t=${timestamp}`;

        img.onload = () => {
            this.imageWidth = img.width;
            this.imageHeight = img.height;

            // Add the image to the SVG with cache-busting URL
            this.g.append("image")
                .attr("href", imageUrl)
                .attr("width", this.imageWidth)
                .attr("height", this.imageHeight)
                .attr("x", 0)
                .attr("y", 0);

            // Fit image to container initially
            this.fitToScreen();

            // Add start/finish line indicator
            this.drawStartFinishLine();

            console.log(`Track map loaded: ${this.imageWidth}x${this.imageHeight}`);
            console.log(`Image URL: ${imageUrl}`);
        };

        img.onerror = () => {
            console.error("Failed to load track map image");
            this.showError("Failed to load track map. Please check if the image file exists.");
        };

        img.src = imageUrl;
    }

    drawStartFinishLine() {
        // Start/finish line position based on typical P1 location on main straight
        // Using GPS coordinates that represent the start/finish area at Barber Motorsports Park
        const startFinishLat = 33.53260; // Representative latitude for start/finish line
        const startFinishLon = -86.61963; // Representative longitude for start/finish line

        const coords = this.convertGPSToMap(startFinishLat, startFinishLon);

        if (coords) {
            // Create start/finish line group for easy management
            const startFinishGroup = this.g.append("g").attr("class", "start-finish-line");

            // Draw the checkered flag pattern line
            const lineLength = 40;
            const lineWidth = 6;

            // Main line (white background)
            startFinishGroup.append("rect")
                .attr("x", coords.x - lineLength/2)
                .attr("y", coords.y - lineWidth/2)
                .attr("width", lineLength)
                .attr("height", lineWidth)
                .attr("fill", "white")
                .attr("stroke", "black")
                .attr("stroke-width", 2);

            // Apply 45-degree rotation to the entire group
            startFinishGroup.attr("transform", `rotate(45, ${coords.x}, ${coords.y})`);

            // Checkered pattern
            const squareSize = 4;
            for (let i = 0; i < lineLength / squareSize; i++) {
                if (i % 2 === 0) { // Alternate black squares
                    startFinishGroup.append("rect")
                        .attr("x", coords.x - lineLength/2 + i * squareSize)
                        .attr("y", coords.y - lineWidth/2)
                        .attr("width", squareSize)
                        .attr("height", lineWidth)
                        .attr("fill", "black");
                }
            }

            console.log(`Start/finish line drawn at GPS: ${startFinishLat.toFixed(6)}, ${startFinishLon.toFixed(6)} -> Map: ${coords.x.toFixed(1)}, ${coords.y.toFixed(1)}`);
        } else {
            console.log("Could not place start/finish line - coordinates out of bounds");
        }
    }

    resetZoom() {
        this.svg.transition()
            .duration(500)
            .call(this.zoom.transform, d3.zoomIdentity);
    }

    fitToScreen() {
        if (this.imageWidth === 0 || this.imageHeight === 0) {
            return; // Image not loaded yet
        }

        // Calculate scale to fit image in container with some padding
        const padding = 20;
        const scaleX = (this.containerWidth - padding * 2) / this.imageWidth;
        const scaleY = (this.containerHeight - padding * 2) / this.imageHeight;
        const scale = Math.min(scaleX, scaleY);

        // Calculate translation to center the image
        const x = (this.containerWidth - this.imageWidth * scale) / 2;
        const y = (this.containerHeight - this.imageHeight * scale) / 2;

        const transform = d3.zoomIdentity.translate(x, y).scale(scale);

        this.svg.transition()
            .duration(500)
            .call(this.zoom.transform, transform);
    }

    setupCarSelector() {
        const carDropdown = document.getElementById('car-dropdown');
        if (carDropdown) {
            carDropdown.addEventListener('change', (event) => {
                this.selectedCar = event.target.value;
                this.onCarSelectionChange();
            });
        }
    }

    setupTimeline() {
        const timeSlider = document.getElementById('time-slider');
        if (timeSlider) {
            timeSlider.addEventListener('input', (event) => {
                this.updateCarPosition(parseInt(event.target.value));
            });
        }

        // Setup video controls
        this.setupVideoControls();
    }

    setupVideoControls() {
        const playPauseButton = document.getElementById('play-pause-button');
        const stepBack5s = document.getElementById('step-back-5s');
        const stepForward5s = document.getElementById('step-forward-5s');
        const lapDropdown = document.getElementById('lap-dropdown');

        if (playPauseButton) {
            playPauseButton.addEventListener('click', () => {
                this.togglePlayPause();
            });
        }

        if (stepBack5s) {
            stepBack5s.addEventListener('click', () => {
                this.pausePlayback();
                this.jumpTime(-5);
            });
        }

        if (stepForward5s) {
            stepForward5s.addEventListener('click', () => {
                this.pausePlayback();
                this.jumpTime(5);
            });
        }

        if (lapDropdown) {
            lapDropdown.addEventListener('change', (event) => {
                const selectedLap = parseInt(event.target.value);
                if (selectedLap) {
                    this.pausePlayback(); // Pause when jumping to lap
                    this.jumpToLap(selectedLap);
                }
            });
        }
    }

    jumpTime(seconds) {
        const timeSlider = document.getElementById('time-slider');
        if (!timeSlider || !this.timelineData.length) return;

        const currentIndex = parseInt(timeSlider.value);
        const startTime = new Date(this.timelineData[0].timestamp);
        const currentTime = new Date(this.timelineData[currentIndex].timestamp);

        // Calculate target time
        const targetTime = new Date(currentTime.getTime() + seconds * 1000);

        // Find closest data point to target time
        let closestIndex = currentIndex;
        let minDiff = Math.abs(new Date(this.timelineData[currentIndex].timestamp) - targetTime);

        for (let i = 0; i < this.timelineData.length; i++) {
            const diff = Math.abs(new Date(this.timelineData[i].timestamp) - targetTime);
            if (diff < minDiff) {
                minDiff = diff;
                closestIndex = i;
            }
        }

        // Update slider and car position
        timeSlider.value = closestIndex;
        this.updateCarPosition(closestIndex);
    }

    jumpToLap(lapNumber) {
        if (!this.timelineData.length) return;

        // Find first data point of the specified lap
        const lapStartIndex = this.timelineData.findIndex(point => point.lap === lapNumber);

        if (lapStartIndex !== -1) {
            const timeSlider = document.getElementById('time-slider');
            if (timeSlider) {
                timeSlider.value = lapStartIndex;
                this.updateCarPosition(lapStartIndex);
            }
        }
    }

    togglePlayPause() {
        if (this.isPlaying) {
            this.pausePlayback();
        } else {
            this.startPlayback();
        }
    }

    startPlayback() {
        if (!this.timelineData.length || this.isPlaying) return;

        this.isPlaying = true;
        this.updatePlayPauseButton();

        // Calculate playback interval based on race data timing
        // Average time between data points in the race data
        const avgTimeInterval = this.calculateAverageTimeInterval();
        const playbackInterval = Math.max(50, avgTimeInterval * this.playbackSpeed); // Minimum 50ms for smooth animation

        console.log(`Starting playback with interval: ${playbackInterval}ms`);

        this.playbackInterval = setInterval(() => {
            const timeSlider = document.getElementById('time-slider');
            if (!timeSlider) return;

            const currentIndex = parseInt(timeSlider.value);
            const nextIndex = currentIndex + 1;

            if (nextIndex >= this.timelineData.length) {
                // End of race data reached
                this.pausePlayback();
                return;
            }

            timeSlider.value = nextIndex;
            this.updateCarPosition(nextIndex);
        }, playbackInterval);
    }

    pausePlayback() {
        if (!this.isPlaying) return;

        this.isPlaying = false;
        this.updatePlayPauseButton();

        if (this.playbackInterval) {
            clearInterval(this.playbackInterval);
            this.playbackInterval = null;
        }
    }

    updatePlayPauseButton() {
        const playPauseButton = document.getElementById('play-pause-button');
        if (!playPauseButton) return;

        if (this.isPlaying) {
            playPauseButton.textContent = '⏸️ Pause';
            playPauseButton.className = 'video-button pause-button';
        } else {
            playPauseButton.textContent = '▶️ Play';
            playPauseButton.className = 'video-button play-button';
        }
    }

    calculateAverageTimeInterval() {
        if (this.timelineData.length < 2) return 100; // Default fallback

        let totalInterval = 0;
        let intervalCount = 0;

        for (let i = 1; i < Math.min(100, this.timelineData.length); i++) { // Sample first 100 points
            const prevTime = new Date(this.timelineData[i - 1].timestamp);
            const currTime = new Date(this.timelineData[i].timestamp);
            const interval = currTime - prevTime;

            if (interval > 0 && interval < 5000) { // Ignore invalid intervals
                totalInterval += interval;
                intervalCount++;
            }
        }

        const avgInterval = intervalCount > 0 ? totalInterval / intervalCount : 100;
        console.log(`Average time interval between data points: ${avgInterval}ms`);
        return avgInterval;
    }

    async loadTelemetryData() {
        try {
            console.log(`Loading telemetry data for ${this.selectedRace}`);

            // Load available car files for the selected race
            await this.loadAvailableCarFiles();

        } catch (error) {
            console.error('Failed to load telemetry data:', error);
        }
    }

    async loadAvailableCarFiles() {
        try {
            // Known car IDs (same for both races, but availability may differ)
            const knownCarIds = [
                'GR86-002-000', 'GR86-004-78', 'GR86-006-7', 'GR86-010-16',
                'GR86-013-80', 'GR86-015-31', 'GR86-016-55', 'GR86-022-13',
                'GR86-025-47', 'GR86-026-72', 'GR86-030-18', 'GR86-033-46',
                'GR86-036-98', 'GR86-038-93', 'GR86-040-3', 'GR86-047-21',
                'GR86-049-88', 'GR86-060-2', 'GR86-063-113', 'GR86-065-5'
            ];

            // Determine race prefix and track
            const racePrefix = this.selectedRace === 'race1' ? 'R1' : 'R2';
            const trackName = 'barber'; // Currently hardcoded to Barber, expandable later

            // Verify which car files actually exist for this race
            this.availableCars = [];
            for (const carId of knownCarIds) {
                try {
                    const filePath = `car_data/${trackName}/${racePrefix}_${carId}_gps.csv`;
                    const response = await fetch(filePath, { method: 'HEAD' });
                    if (response.ok) {
                        this.availableCars.push(carId);
                    }
                } catch (e) {
                    // File doesn't exist for this race, skip
                    console.log(`Car file not found for ${racePrefix}: ${carId}`);
                }
            }

            console.log(`Found ${this.availableCars.length} available cars for ${racePrefix}`);
            this.populateCarDropdown();

        } catch (error) {
            console.error('Failed to load available car files:', error);
        }
    }

    async loadSpecificCarData(carId) {
        try {
            const racePrefix = this.selectedRace === 'race1' ? 'R1' : 'R2';
            const trackName = 'barber';

            // Try 50% sampling files first (improved speed accuracy), then fallback options
            let fileName = `car_data/${trackName}/${racePrefix}_${carId}_telemetry_50percent.csv`;
            let response = await fetch(fileName);

            if (!response.ok) {
                // Try 50% sampling test file (for GR86-002-000)
                fileName = `car_data/${trackName}/TEST_${racePrefix}_${carId}_50percent_sampling.csv`;
                response = await fetch(fileName);
            }

            if (!response.ok) {
                // Try fixed telemetry file (20% sampling with interpolation)
                fileName = `car_data/${trackName}/${racePrefix}_${carId}_telemetry_fixed.csv`;
                response = await fetch(fileName);
            }

            if (!response.ok) {
                // Fallback to original enhanced telemetry file
                console.log(`Fixed telemetry not found, trying enhanced telemetry file for ${carId}`);
                fileName = `car_data/${trackName}/${racePrefix}_${carId}_telemetry.csv`;
                response = await fetch(fileName);

                if (!response.ok) {
                    // Fallback to GPS-only file
                    console.log(`Enhanced telemetry not found, using GPS-only file for ${carId}`);
                    fileName = `car_data/${trackName}/${racePrefix}_${carId}_gps.csv`;
                    response = await fetch(fileName);

                    if (!response.ok) {
                        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                    }
                }
            }

            const csvText = await response.text();

            console.log(`Loading data for ${racePrefix} car: ${carId} from ${fileName}`);

            // Detect file type and parse accordingly
            if (fileName.includes('_telemetry_50percent.csv') || fileName.includes('_50percent_sampling.csv') ||
                fileName.includes('_telemetry_fixed_v2.csv') || fileName.includes('_telemetry_fixed.csv') ||
                fileName.includes('_telemetry.csv')) {
                console.log('Using enhanced telemetry parsing');
                this.parseFullTelemetryData(csvText);
            } else {
                console.log('Using GPS-only parsing');
                this.parseTelemetryData(csvText);
            }

        } catch (error) {
            console.error(`Failed to load data for car ${carId}:`, error);
            throw error;
        }
    }

    parseTelemetryData(csvText) {
        const lines = csvText.trim().split('\n');
        const headers = lines[0].split(',');

        console.log('Full data file - Total lines:', lines.length);
        console.log('First line (headers):', lines[0]);
        console.log('Headers array:', headers);

        // Find relevant column indices
        const vehicleIdIndex = headers.indexOf('vehicle_id');
        const telemetryNameIndex = headers.indexOf('telemetry_name');
        const telemetryValueIndex = headers.indexOf('telemetry_value');
        const timestampIndex = headers.indexOf('timestamp');
        const lapIndex = headers.indexOf('lap');

        console.log('Column indices:');
        console.log('vehicleIdIndex:', vehicleIdIndex);
        console.log('telemetryNameIndex:', telemetryNameIndex);
        console.log('telemetryValueIndex:', telemetryValueIndex);
        console.log('timestampIndex:', timestampIndex);
        console.log('lapIndex:', lapIndex);

        console.log(`Processing GPS data for ${this.selectedCar}...`);

        // Process GPS data for the currently selected car
        const targetCar = this.selectedCar;
        const latitudeData = [];
        const longitudeData = [];
        let processedLines = 0;

        // Collect all latitude and longitude data separately
        for (let i = 1; i < lines.length; i++) {
            const values = lines[i].split(',');
            const vehicleId = values[vehicleIdIndex];
            const telemetryName = values[telemetryNameIndex];

            processedLines++;

            // Debug first few lines
            if (processedLines <= 10) {
                console.log(`Line ${i}: vehicleId="${vehicleId}", telemetryName="${telemetryName}"`);
            }

            // Collect GPS data for the selected car
            if (vehicleId === targetCar) {
                const telemetryValue = parseFloat(values[telemetryValueIndex]);
                const timestamp = values[timestampIndex];
                const lap = parseInt(values[lapIndex]) || 1;

                if (telemetryName === 'VBOX_Lat_Min') {
                    latitudeData.push({
                        timestamp: timestamp,
                        latitude: telemetryValue,
                        lap: lap
                    });
                } else if (telemetryName === 'VBOX_Long_Minutes') {
                    longitudeData.push({
                        timestamp: timestamp,
                        longitude: telemetryValue,
                        lap: lap
                    });
                }
            }
        }

        console.log(`Found ${latitudeData.length} latitude entries and ${longitudeData.length} longitude entries`);

        // Pair latitude and longitude data by index (assuming they're in similar order)
        const gpsDataPoints = [];
        const pairCount = Math.min(latitudeData.length, longitudeData.length);

        for (let i = 0; i < pairCount; i += 1) { // Use all pairs for crew chief analysis
            const latEntry = latitudeData[i];
            const lonEntry = longitudeData[i];

            gpsDataPoints.push({
                timestamp: latEntry.timestamp,
                latitude: latEntry.latitude,
                longitude: lonEntry.longitude,
                lap: latEntry.lap
            });
        }

        console.log(`Processed ${processedLines} lines, created ${gpsDataPoints.length} GPS coordinate pairs`);

        // Create single car data structure
        const carData = {
            [targetCar]: {
                vehicleId: targetCar,
                dataPoints: gpsDataPoints.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp))
            }
        };

        this.telemetryData = Object.values(carData);
        this.availableCars = this.telemetryData.map(car => car.vehicleId);

        console.log('Parsed telemetry data for', this.availableCars.length, 'cars');
    }

    parseFullTelemetryData(csvText) {
        const lines = csvText.trim().split('\n');
        const headers = lines[0].split(',');

        console.log('Enhanced telemetry file - Total lines:', lines.length);
        console.log('Headers:', headers);

        // Find relevant column indices
        const vehicleIdIndex = headers.indexOf('vehicle_id');
        const telemetryNameIndex = headers.indexOf('telemetry_name');
        const telemetryValueIndex = headers.indexOf('telemetry_value');
        const timestampIndex = headers.indexOf('timestamp');
        const lapIndex = headers.indexOf('lap');

        const targetCar = this.selectedCar;
        const telemetryTypes = ['VBOX_Lat_Min', 'VBOX_Long_Minutes', 'speed', 'gear', 'aps', 'pbrake_r', 'pbrake_f'];

        console.log(`Processing enhanced telemetry for ${targetCar}...`);

        // Group all telemetry by timestamp
        const timestampData = {};
        let processedLines = 0;

        for (let i = 1; i < lines.length; i++) {
            const values = lines[i].split(',');
            const vehicleId = values[vehicleIdIndex];
            const telemetryName = values[telemetryNameIndex];
            const telemetryValue = parseFloat(values[telemetryValueIndex]);
            const timestamp = values[timestampIndex];
            const lap = parseInt(values[lapIndex]) || 1;

            processedLines++;

            // Debug first few lines
            if (processedLines <= 5) {
                console.log(`Line ${i}: ${vehicleId}, ${telemetryName}=${telemetryValue}, ${timestamp}`);
            }

            // Collect telemetry for the selected car
            if (vehicleId === targetCar && telemetryTypes.includes(telemetryName)) {
                if (!timestampData[timestamp]) {
                    timestampData[timestamp] = {
                        timestamp: timestamp,
                        lap: lap,
                        telemetry: {}
                    };
                }

                // Store telemetry value (use null for NaN values)
                timestampData[timestamp].telemetry[telemetryName] = isNaN(telemetryValue) ? null : telemetryValue;
            }
        }

        console.log(`Found ${Object.keys(timestampData).length} timestamps with telemetry data`);

        // Convert to sorted array and create complete data points
        const sortedTimestamps = Object.keys(timestampData).sort((a, b) => new Date(a) - new Date(b));
        const dataPoints = [];

        for (const timestamp of sortedTimestamps) {
            const data = timestampData[timestamp];
            const telemetry = data.telemetry;

            // Only include data points that have both GPS coordinates
            if (telemetry['VBOX_Lat_Min'] !== undefined && telemetry['VBOX_Long_Minutes'] !== undefined &&
                telemetry['VBOX_Lat_Min'] !== null && telemetry['VBOX_Long_Minutes'] !== null) {

                dataPoints.push({
                    timestamp: timestamp,
                    latitude: telemetry['VBOX_Lat_Min'],
                    longitude: telemetry['VBOX_Long_Minutes'],
                    lap: data.lap,
                    // Enhanced telemetry fields
                    speed: telemetry['speed'] || null,
                    gear: telemetry['gear'] || null,
                    throttle: telemetry['aps'] || null,
                    brakeRear: telemetry['pbrake_r'] || null,
                    brakeFront: telemetry['pbrake_f'] || null
                });
            }
        }

        console.log(`Created ${dataPoints.length} complete telemetry data points`);

        // Log telemetry availability
        if (dataPoints.length > 0) {
            const samplePoint = dataPoints[Math.floor(dataPoints.length / 2)];
            console.log('Sample telemetry point:', {
                timestamp: samplePoint.timestamp,
                speed: samplePoint.speed,
                gear: samplePoint.gear,
                throttle: samplePoint.throttle,
                brakeRear: samplePoint.brakeRear,
                brakeFront: samplePoint.brakeFront
            });
        }

        // Create car data structure
        const carData = {
            [targetCar]: {
                vehicleId: targetCar,
                dataPoints: dataPoints,
                hasEnhancedTelemetry: true  // Flag to indicate enhanced data
            }
        };

        this.telemetryData = Object.values(carData);
        this.availableCars = this.telemetryData.map(car => car.vehicleId);

        console.log('Parsed enhanced telemetry data for', this.availableCars.length, 'cars');
    }

    populateCarDropdown() {
        const carDropdown = document.getElementById('car-dropdown');
        if (!carDropdown) return;

        if (this.availableCars.length === 0) {
            carDropdown.innerHTML = '<option value="">No cars available for this race</option>';
            return;
        }

        carDropdown.innerHTML = '<option value="">Select a car...</option>';

        // Sort cars by number for better UX (using middle digits - the car number on the side)
        const sortedCars = [...this.availableCars].sort((a, b) => {
            const numA = parseInt(a.split('-')[1]) || 0;
            const numB = parseInt(b.split('-')[1]) || 0;
            return numA - numB;
        });

        sortedCars.forEach(carId => {
            const option = document.createElement('option');
            option.value = carId;

            // Extract car number (middle digits) - the number on the side of the car
            const carNumber = carId.split('-')[1] || carId;
            option.textContent = `Car #${carNumber} ${carId}`;
            carDropdown.appendChild(option);
        });

        console.log(`Populated dropdown with ${this.availableCars.length} cars for ${this.selectedRace}`);

        // Focus on car dropdown to guide user to first required action
        if (this.availableCars.length > 0) {
            setTimeout(() => {
                carDropdown.focus();
            }, 100); // Small delay to ensure DOM is fully updated
        }
    }

    async onCarSelectionChange() {
        if (this.selectedCar) {
            console.log('Car selected:', this.selectedCar);

            // Pause any ongoing playback
            this.pausePlayback();

            // Clear existing data
            this.timelineData = [];
            this.telemetryData = [];

            // Show loading indicator
            this.showLoadingMessage(`Loading GPS data for ${this.selectedCar}...`);

            try {
                // Load specific car data
                await this.loadSpecificCarData(this.selectedCar);

                this.prepareTimelineData();
                this.updateTimeline();
                this.hideLoadingMessage();

            } catch (error) {
                this.showError(`Failed to load data for ${this.selectedCar}`);
                this.hideLoadingMessage();
            }
        }
    }

    prepareTimelineData() {
        const carData = this.telemetryData.find(car => car.vehicleId === this.selectedCar);
        if (carData) {
            this.timelineData = carData.dataPoints.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
            console.log('Timeline data prepared with', this.timelineData.length, 'data points');

            // Log GPS coordinate ranges for debugging
            if (this.timelineData.length > 0) {
                const latitudes = this.timelineData.map(p => p.latitude);
                const longitudes = this.timelineData.map(p => p.longitude);
                console.log(`GPS Range - Lat: ${Math.min(...latitudes).toFixed(6)} to ${Math.max(...latitudes).toFixed(6)}`);
                console.log(`GPS Range - Lon: ${Math.min(...longitudes).toFixed(6)} to ${Math.max(...longitudes).toFixed(6)}`);
                console.log(`Laps covered: ${Math.min(...this.timelineData.map(p => p.lap))} to ${Math.max(...this.timelineData.map(p => p.lap))}`);
            }

            // Show all GPS points for debugging
            this.showGPSTrace();

            // Populate lap dropdown
            this.populateLapDropdown();
        }
    }

    populateLapDropdown() {
        const lapDropdown = document.getElementById('lap-dropdown');
        if (!lapDropdown || !this.timelineData.length) return;

        // Extract unique lap numbers from timeline data
        const uniqueLaps = [...new Set(this.timelineData.map(point => point.lap))].sort((a, b) => a - b);

        // Clear existing options except the default
        lapDropdown.innerHTML = '<option value="">Select Lap</option>';

        // Add options for each lap
        uniqueLaps.forEach(lapNumber => {
            const option = document.createElement('option');
            option.value = lapNumber;
            option.textContent = `Lap ${lapNumber}`;
            lapDropdown.appendChild(option);
        });

        console.log(`Populated lap dropdown with ${uniqueLaps.length} laps: ${uniqueLaps.join(', ')}`);
    }

    showGPSTrace() {
        // Remove existing trace
        this.g.selectAll('.gps-trace').remove();

        if (this.timelineData.length === 0) return;

        console.log('Showing sampled GPS trace for complete race...');

        // Show every point (already sampled during parsing)
        for (let i = 0; i < this.timelineData.length; i += 1) {
            const point = this.timelineData[i];
            const coords = this.convertGPSToMap(point.latitude, point.longitude);

            if (coords) {
                this.g.append("circle")
                    .attr("class", "gps-trace")
                    .attr("cx", coords.x)
                    .attr("cy", coords.y)
                    .attr("r", 1)
                    .attr("fill", "blue")
                    .attr("opacity", 0.4);
            }
        }
    }

    convertGPSToMap(latitude, longitude) {
        const trackBounds = {
            minLat: 33.5293,   // Actual GPS data minimum
            maxLat: 33.5359,   // Actual GPS data maximum (corrected)
            minLon: -86.6244,  // Actual GPS data minimum
            maxLon: -86.6145   // Actual GPS data maximum (corrected)
        };

        const normalizedX = (longitude - trackBounds.minLon) / (trackBounds.maxLon - trackBounds.minLon);
        const normalizedY = (latitude - trackBounds.minLat) / (trackBounds.maxLat - trackBounds.minLat);

        // Improved calibration based on GPS trace analysis
        // The trace was shifted right, so we shift left with negative X offset
        // Also adjust scaling to better fit the track boundaries

        // Apply rotation if needed - Iteration 5: Minimal rotation
        const rotationAngle = 0.05; // Much smaller rotation
        const cosAngle = Math.cos(rotationAngle);
        const sinAngle = Math.sin(rotationAngle);

        // Center coordinates around 0.5 for rotation
        const centeredX = normalizedX - 0.5;
        const centeredY = normalizedY - 0.5;

        // Apply rotation
        const rotatedX = centeredX * cosAngle - centeredY * sinAngle;
        const rotatedY = centeredX * sinAngle + centeredY * cosAngle;

        // Move back and apply calibration - Iteration 8: Fine-tune scale for better track fit
        const calibratedX = (rotatedX + 0.5) * 0.92 + 0.04; // Increase scale to 0.92 for better fill
        const calibratedY = (rotatedY + 0.5) * 0.92 + 0.04; // Match scale, center adjustment

        const mapX = calibratedX * this.imageWidth; // Clean positioning
        const mapY = (1 - calibratedY) * this.imageHeight; // Clean positioning

        // Expand bounds significantly to capture all possible GPS points
        if (mapX >= -200 && mapX <= this.imageWidth + 200 && mapY >= -200 && mapY <= this.imageHeight + 200) {
            return { x: mapX, y: mapY };
        }

        // Log filtered out points for debugging
        console.log(`GPS point filtered out: GPS(${latitude.toFixed(6)}, ${longitude.toFixed(6)}) -> Map(${mapX.toFixed(1)}, ${mapY.toFixed(1)})`);
        return null;
    }

    updateTimeline() {
        const timeSlider = document.getElementById('time-slider');
        const totalTimeSpan = document.getElementById('total-time');

        if (timeSlider && this.timelineData.length > 0) {
            timeSlider.max = this.timelineData.length - 1;
            timeSlider.value = 0;

            // Calculate total race time
            const startTime = new Date(this.timelineData[0].timestamp);
            const endTime = new Date(this.timelineData[this.timelineData.length - 1].timestamp);
            const totalSeconds = (endTime - startTime) / 1000;

            if (totalTimeSpan) {
                totalTimeSpan.textContent = this.formatTime(totalSeconds);
            }

            // Initialize with first position
            this.updateCarPosition(0);
        }
    }

    updateCarPosition(timeIndex) {
        console.log(`Updating car position for time index: ${timeIndex}`);

        if (timeIndex >= 0 && timeIndex < this.timelineData.length) {
            const dataPoint = this.timelineData[timeIndex];
            console.log(`Data point:`, dataPoint);

            // Update time display
            const currentTimeSpan = document.getElementById('current-time');
            const lapInfoSpan = document.getElementById('lap-info');

            if (currentTimeSpan && this.timelineData.length > 0) {
                const startTime = new Date(this.timelineData[0].timestamp);
                const currentTime = new Date(dataPoint.timestamp);
                const elapsedSeconds = (currentTime - startTime) / 1000;
                currentTimeSpan.textContent = this.formatTime(elapsedSeconds);
            }

            if (lapInfoSpan) {
                lapInfoSpan.textContent = `Lap: ${dataPoint.lap}`;
            }

            // Update enhanced telemetry display
            this.updateTelemetryDisplay(dataPoint);

            // Update lap data display
            this.updateLapDataDisplay(dataPoint);

            // Plot car position on map
            this.plotCarOnMap(dataPoint.latitude, dataPoint.longitude);
        } else {
            console.log(`Invalid time index: ${timeIndex}, timeline length: ${this.timelineData.length}`);
        }
    }

    plotCarOnMap(latitude, longitude) {
        // Remove existing car marker more reliably
        if (this.carMarker) {
            try {
                this.carMarker.remove();
            } catch (e) {
                // Marker might already be removed
            }
            this.carMarker = null;
        }

        // Also remove any existing car markers by class
        this.g.selectAll('.car-marker').remove();

        // Use shared coordinate conversion
        const coords = this.convertGPSToMap(latitude, longitude);

        if (coords) {
            // Create car marker with class for easy removal
            this.carMarker = this.g.append("circle")
                .attr("class", "car-marker")
                .attr("cx", coords.x)
                .attr("cy", coords.y)
                .attr("r", 8)
                .attr("fill", "#ff0000")
                .attr("stroke", "#ffffff")
                .attr("stroke-width", 3)
                .style("cursor", "pointer");

            console.log(`Car plotted at GPS: ${latitude.toFixed(6)}, ${longitude.toFixed(6)} -> Map: ${coords.x.toFixed(1)}, ${coords.y.toFixed(1)}`);
        } else {
            console.log(`GPS coordinates out of bounds: ${latitude.toFixed(6)}, ${longitude.toFixed(6)}`);
        }
    }

    formatTime(seconds) {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = Math.floor(seconds % 60);

        return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }

    updateTelemetryDisplay(dataPoint) {
        // Update telemetry display in sidebar
        const speedValue = document.getElementById('speed-value');
        const gearValue = document.getElementById('gear-value');
        const throttleValue = document.getElementById('throttle-value');
        const brakeRearValue = document.getElementById('brake-rear-value');
        const brakeFrontValue = document.getElementById('brake-front-value');

        // Update speed with unit conversion
        if (speedValue) {
            if (dataPoint.speed !== null && dataPoint.speed !== undefined) {
                const speed = this.speedUnit === 'kph'
                    ? (dataPoint.speed * 1.60934) // Convert mph to kph
                    : dataPoint.speed; // Keep as mph
                speedValue.textContent = `${speed.toFixed(1)} ${this.speedUnit}`;
            } else {
                speedValue.textContent = '--';
            }
        }

        // Update gear
        if (gearValue) {
            gearValue.textContent = dataPoint.gear !== null && dataPoint.gear !== undefined
                ? Math.round(dataPoint.gear).toString()
                : '--';
        }

        // Update throttle (APS)
        if (throttleValue) {
            throttleValue.textContent = dataPoint.throttle !== null && dataPoint.throttle !== undefined
                ? `${dataPoint.throttle.toFixed(1)}%`
                : '--';
        }

        // Update rear brake pressure
        if (brakeRearValue) {
            brakeRearValue.textContent = dataPoint.brakeRear !== null && dataPoint.brakeRear !== undefined
                ? `${dataPoint.brakeRear.toFixed(1)} psi`
                : '--';
        }

        // Update front brake pressure
        if (brakeFrontValue) {
            brakeFrontValue.textContent = dataPoint.brakeFront !== null && dataPoint.brakeFront !== undefined
                ? `${dataPoint.brakeFront.toFixed(1)} psi`
                : '--';
        }
    }

    updateLapDataDisplay(dataPoint) {
        if (!this.selectedCar || !dataPoint) return;

        const race = this.selectedRace === 'race1' ? 'R1' : 'R2';
        const lapNumber = dataPoint.lap;

        // Update lap number
        const lapNumberValue = document.getElementById('lap-number-value');
        if (lapNumberValue) {
            lapNumberValue.textContent = lapNumber;
        }

        // Get lap data from loaded CSV data
        const lapStartTime = this.getLapTimestamp(race, this.selectedCar, lapNumber, 'start');
        const lapEndTime = this.getLapTimestamp(race, this.selectedCar, lapNumber, 'end');

        // Update lap start time
        const lapStartValue = document.getElementById('lap-start-time-value');
        if (lapStartValue) {
            if (lapStartTime) {
                lapStartValue.textContent = this.formatLapTime(lapStartTime);
            } else {
                lapStartValue.textContent = '--:--:---';
            }
        }

        // Update lap end time
        const lapEndValue = document.getElementById('lap-end-time-value');
        if (lapEndValue) {
            if (lapEndTime) {
                lapEndValue.textContent = this.formatLapTime(lapEndTime);
            } else {
                lapEndValue.textContent = '--:--:---';
            }
        }

        // Calculate and update lap total time
        const lapTotalValue = document.getElementById('lap-total-time-value');
        if (lapTotalValue) {
            if (lapStartTime && lapEndTime) {
                const startTime = new Date(lapStartTime);
                const endTime = new Date(lapEndTime);
                const lapDuration = endTime - startTime;

                if (lapDuration > 0) {
                    lapTotalValue.textContent = this.formatLapDuration(lapDuration);
                } else {
                    lapTotalValue.textContent = '--:--:---';
                }
            } else {
                lapTotalValue.textContent = '--:--:---';
            }
        }
    }

    getLapTimestamp(race, vehicleId, lap, type) {
        let dataSource;
        if (type === 'start') {
            dataSource = this.lapData.lapStarts;
        } else if (type === 'end') {
            dataSource = this.lapData.lapEnds;
        } else {
            return null;
        }

        if (dataSource[race] && dataSource[race][vehicleId] && dataSource[race][vehicleId][lap]) {
            return dataSource[race][vehicleId][lap];
        }

        return null;
    }

    formatLapTime(timestamp) {
        if (!timestamp) return '--:--:---';

        const date = new Date(timestamp);
        const hours = date.getUTCHours();
        const minutes = date.getUTCMinutes();
        const seconds = date.getUTCSeconds();
        const milliseconds = date.getUTCMilliseconds();

        return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}:${milliseconds.toString().padStart(3, '0')}`;
    }

    formatLapDuration(duration) {
        if (!duration || duration <= 0) return '--:--:---';

        const totalSeconds = Math.floor(duration / 1000);
        const minutes = Math.floor(totalSeconds / 60);
        const seconds = totalSeconds % 60;
        const milliseconds = duration % 1000;

        return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}:${milliseconds.toString().padStart(3, '0')}`;
    }

    showLoadingMessage(message) {
        // Remove existing messages
        this.g.selectAll('.loading-message').remove();

        // Add loading message
        this.g.append("text")
            .attr("class", "loading-message")
            .attr("x", this.containerWidth / 2)
            .attr("y", this.containerHeight / 2)
            .attr("text-anchor", "middle")
            .attr("fill", "#007bff")
            .attr("font-size", "18px")
            .attr("font-weight", "bold")
            .text(message);
    }

    hideLoadingMessage() {
        this.g.selectAll('.loading-message').remove();
    }

    showError(message) {
        // Remove existing messages
        this.g.selectAll('.loading-message, .error-message').remove();

        // Add error message
        this.g.append("text")
            .attr("class", "error-message")
            .attr("x", this.containerWidth / 2)
            .attr("y", this.containerHeight / 2)
            .attr("text-anchor", "middle")
            .attr("fill", "red")
            .attr("font-size", "18px")
            .text(message);
    }

    toggleSpeedUnit() {
        // Toggle between mph and kph
        this.speedUnit = this.speedUnit === 'mph' ? 'kph' : 'mph';

        // Update button text
        const toggleButton = document.getElementById('speed-unit-toggle');
        if (toggleButton) {
            toggleButton.textContent = this.speedUnit;
        }

        // Update current speed display if we have data
        if (this.timelineData.length > 0) {
            const timeSlider = document.getElementById('time-slider');
            if (timeSlider) {
                const currentIndex = parseInt(timeSlider.value);
                if (currentIndex >= 0 && currentIndex < this.timelineData.length) {
                    this.updateTelemetryDisplay(this.timelineData[currentIndex]);
                }
            }
        }
    }
}

// Global variable to hold the track map viewer instance
let trackMapViewer;

// Global function for speed unit toggle (called from HTML)
function toggleSpeedUnit() {
    if (trackMapViewer) {
        trackMapViewer.toggleSpeedUnit();
    }
}

// Initialize the track map viewer when the page loads
document.addEventListener("DOMContentLoaded", () => {
    console.log("Initializing Track Map Viewer...");
    trackMapViewer = new TrackMapViewer();
});

