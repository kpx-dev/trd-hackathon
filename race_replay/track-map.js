class TrackMapViewer {
    constructor() {
        this.svg = null;
        this.g = null;
        this.zoom = null;
        this.currentZoom = 1;
        this.imageWidth = 0;
        this.imageHeight = 0;
        this.containerWidth = Math.min(window.innerWidth * 0.9, 1400);
        this.containerHeight = Math.min(window.innerHeight * 0.85, 1000);
        this.trackData = null;
        this.selectedRace = 'race1'; // Default to Race 1
        this.telemetryData = [];
        this.availableCars = [];
        this.selectedCar = null;
        this.timelineData = [];
        this.carMarker = null;
        this.showFullTrace = false;

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

        // Load the track map image and telemetry data
        this.loadTrackMap();
        this.loadTelemetryData();
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
        // Log the race selection for now - this can be extended for actual functionality
        console.log(`Race selection changed to: ${this.selectedRace}`);

        // Update the title to show which race is selected
        this.updateRaceInTitle();

        // Load telemetry data for the selected race
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
        const newHeight = Math.min(window.innerHeight * 0.85, 1000);

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

        // Setup jump controls
        this.setupJumpControls();
    }

    setupJumpControls() {
        const jumpBack10s = document.getElementById('jump-back-10s');
        const jumpForward10s = document.getElementById('jump-forward-10s');
        const lapDropdown = document.getElementById('lap-dropdown');

        if (jumpBack10s) {
            jumpBack10s.addEventListener('click', () => {
                this.jumpTime(-10);
            });
        }

        if (jumpForward10s) {
            jumpForward10s.addEventListener('click', () => {
                this.jumpTime(10);
            });
        }

        if (lapDropdown) {
            lapDropdown.addEventListener('change', (event) => {
                const selectedLap = parseInt(event.target.value);
                if (selectedLap) {
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

    async loadTelemetryData() {
        try {
            const fileName = this.selectedRace === 'race1' ? 'R1_sample_telemetry.csv' : 'R2_sample_telemetry.csv';
            const response = await fetch(fileName);
            const csvText = await response.text();

            console.log('Loading telemetry data for', this.selectedRace);

            // Parse CSV and extract car data
            this.parseTelemetryData(csvText);
            this.populateCarDropdown();

        } catch (error) {
            console.error('Failed to load telemetry data:', error);
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

        console.log('Processing full dataset for GR86-002-000 only with GPS sampling...');

        // Only process GR86-002-000 data with GPS coordinates
        const targetCar = 'GR86-002-000';
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

            // Collect GPS data for our target car
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

    populateCarDropdown() {
        const carDropdown = document.getElementById('car-dropdown');
        if (carDropdown && this.availableCars.length > 0) {
            carDropdown.innerHTML = '<option value="">Select a car...</option>';

            this.availableCars.forEach(carId => {
                const option = document.createElement('option');
                option.value = carId;
                option.textContent = carId;
                carDropdown.appendChild(option);
            });
        }
    }

    onCarSelectionChange() {
        if (this.selectedCar) {
            console.log('Car selected:', this.selectedCar);
            this.prepareTimelineData();
            this.updateTimeline();
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
            minLat: 33.5293,   // Expanded to cover actual data range
            maxLat: 33.5327,   // Expanded to cover actual data range
            minLon: -86.6245,  // Expanded to cover actual data range
            maxLon: -86.6195   // Expanded to cover actual data range
        };

        const normalizedX = (longitude - trackBounds.minLon) / (trackBounds.maxLon - trackBounds.minLon);
        const normalizedY = (latitude - trackBounds.minLat) / (trackBounds.maxLat - trackBounds.minLat);

        // Improved calibration based on GPS trace analysis
        // The trace was shifted right, so we shift left with negative X offset
        // Also adjust scaling to better fit the track boundaries

        // Apply rotation if needed (small angle correction)
        const rotationAngle = -0.03; // Further refined rotation based on trace 3 analysis
        const cosAngle = Math.cos(rotationAngle);
        const sinAngle = Math.sin(rotationAngle);

        // Center coordinates around 0.5 for rotation
        const centeredX = normalizedX - 0.5;
        const centeredY = normalizedY - 0.5;

        // Apply rotation
        const rotatedX = centeredX * cosAngle - centeredY * sinAngle;
        const rotatedY = centeredX * sinAngle + centeredY * cosAngle;

        // Move back and apply fine-tuned calibration
        // Based on GPS trace 7 analysis: correct position by moving down and left
        const calibratedX = (rotatedX + 0.5) * 0.45 + 0.15; // Keep scale, move LEFT (decrease offset)
        const calibratedY = (rotatedY + 0.5) * 0.45 + 0.45; // Keep scale, move DOWN (increase offset)

        const mapX = calibratedX * this.imageWidth - 100; // Shift GPS plot another 20 pixels LEFT (total 30 from original)
        const mapY = (1 - calibratedY) * this.imageHeight + 265; // Final micro-adjustment: 5 more pixels DOWN

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

    showError(message) {
        // Add error message to the SVG
        this.g.append("text")
            .attr("x", this.containerWidth / 2)
            .attr("y", this.containerHeight / 2)
            .attr("text-anchor", "middle")
            .attr("fill", "red")
            .attr("font-size", "18px")
            .text(message);
    }
}

// Initialize the track map viewer when the page loads
document.addEventListener("DOMContentLoaded", () => {
    console.log("Initializing Track Map Viewer...");
    new TrackMapViewer();
});

