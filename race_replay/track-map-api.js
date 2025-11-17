/**
 * API-Based Track Map Viewer - Prototype
 * Demonstrates using server API instead of pre-processed files
 * Maintains smooth playback with chunked data loading
 */

class ApiTrackMapViewer {
    constructor() {
        // Visual components (same as original)
        this.svg = null;
        this.g = null;
        this.zoom = null;
        this.currentZoom = 1;
        this.imageWidth = 0;
        this.imageHeight = 0;
        this.containerWidth = Math.min(window.innerWidth * 0.9, 1400);
        this.containerHeight = Math.min(window.innerHeight * 0.765, 900);

        // Data management (API-based)
        this.baseUrl = 'http://localhost:8001/api';
        this.selectedRace = 'R1';
        this.selectedCar = null;
        this.timelineData = [];
        this.dataChunks = new Map(); // Cache for loaded chunks
        this.currentPosition = 0;

        // Playback controls
        this.isPlaying = false;
        this.playbackInterval = null;
        this.playbackSpeed = 1;
        this.speedUnit = 'mph';

        // Chunk management
        this.chunkSizeSeconds = 60; // Load 60-second chunks
        this.preloadAhead = 2; // Preload 2 chunks ahead

        // Visual elements
        this.carMarker = null;
        this.trackData = null;
        this.lapData = {};

        this.init();
    }

    async init() {
        console.log('🚀 Initializing API-based Track Map Viewer...');

        // Set up SVG container (same as original)
        this.svg = d3.select("#track-map")
            .attr("width", this.containerWidth)
            .attr("height", this.containerHeight);

        this.g = this.svg.append("g");

        // Set up zoom behavior
        this.zoom = d3.zoom()
            .scaleExtent([0.1, 10])
            .on("zoom", (event) => {
                this.g.attr("transform", event.transform);
                this.currentZoom = event.transform.k;
            });

        this.svg.call(this.zoom);

        // Load initial data
        await this.loadTrackData();
        await this.loadRaces();

        // Setup UI components
        this.setupRaceSelector();
        this.setupCarSelector();
        this.setupTimeline();
        this.loadTrackMap();

        // Load cars for initial race selection
        await this.loadAvailableCars();

        window.addEventListener('resize', () => {
            this.updateContainerSize();
        });
    }

    async loadTrackData() {
        // Use same track data as original (static)
        try {
            const response = await fetch('gr_cup_track_info.csv');
            const csvText = await response.text();

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

            this.trackData = tracks.find(track =>
                track.track_name === 'Barber Motorsports Park'
            );

            if (this.trackData) {
                this.updateTitle();
            }

            console.log('✅ Track data loaded:', this.trackData);
        } catch (error) {
            console.error('❌ Failed to load track data:', error);
        }
    }

    async loadRaces() {
        try {
            const response = await fetch(`${this.baseUrl}/races`);
            const data = await response.json();
            console.log('✅ Available races:', data.races);
        } catch (error) {
            console.error('❌ Error loading races:', error);
        }
    }

    async loadAvailableCars() {
        try {
            console.log(`📊 Loading available cars for ${this.selectedRace}...`);

            const response = await fetch(`${this.baseUrl}/races/${this.selectedRace}/cars`);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();
            this.availableCars = data.cars;

            console.log(`✅ Found ${this.availableCars.length} cars for ${this.selectedRace}`);
            this.populateCarDropdown();

        } catch (error) {
            console.error('❌ Error loading cars:', error);
            this.showError(`Failed to load cars for ${this.selectedRace}`);
        }
    }

    async loadCarTimeline(carId) {
        try {
            console.log(`📈 Loading timeline for ${carId}...`);

            const response = await fetch(`${this.baseUrl}/telemetry/${this.selectedRace}/${carId}/timeline`);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();
            this.timelineData = data.timeline;

            console.log(`✅ Timeline loaded: ${data.total_points} points, ${data.duration_seconds}s duration`);

            // Load lap data
            await this.loadLapData(carId);

            return data;

        } catch (error) {
            console.error('❌ Error loading timeline:', error);
            throw error;
        }
    }

    async loadLapData(carId) {
        try {
            const response = await fetch(`${this.baseUrl}/laps/${this.selectedRace}/${carId}`);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();
            this.lapData = data.laps;

            console.log('✅ Lap data loaded:', Object.keys(this.lapData).length, 'laps');

        } catch (error) {
            console.error('❌ Error loading lap data:', error);
        }
    }

    async loadDataChunk(startIndex, endIndex) {
        try {
            if (!this.timelineData.length) return null;

            const startTime = this.timelineData[startIndex]?.timestamp;
            const endTime = this.timelineData[endIndex]?.timestamp;

            if (!startTime || !endTime) return null;

            console.log(`📦 Loading chunk: ${startIndex}-${endIndex} (${startTime} to ${endTime})`);

            const response = await fetch(
                `${this.baseUrl}/telemetry/${this.selectedRace}/${this.selectedCar}/chunk?start_time=${startTime}&end_time=${endTime}`
            );

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();

            // Cache the chunk
            const chunkId = `${startIndex}-${endIndex}`;
            this.dataChunks.set(chunkId, data.data);

            console.log(`✅ Chunk loaded: ${data.total_points} data points`);

            return data.data;

        } catch (error) {
            console.error('❌ Error loading data chunk:', error);
            return null;
        }
    }

    async ensureDataLoaded(position) {
        if (!this.timelineData.length) return null;

        // Calculate chunk boundaries
        const chunkSize = Math.min(this.chunkSizeSeconds * 10, 600); // ~60 seconds worth of data points
        const chunkStart = Math.floor(position / chunkSize) * chunkSize;
        const chunkEnd = Math.min(chunkStart + chunkSize, this.timelineData.length - 1);
        const chunkId = `${chunkStart}-${chunkEnd}`;

        // Check if chunk is already loaded
        if (this.dataChunks.has(chunkId)) {
            return this.dataChunks.get(chunkId);
        }

        // Load current chunk
        const chunk = await this.loadDataChunk(chunkStart, chunkEnd);

        // Preload next chunks in background
        for (let i = 1; i <= this.preloadAhead; i++) {
            const nextChunkStart = chunkStart + (i * chunkSize);
            const nextChunkEnd = Math.min(nextChunkStart + chunkSize, this.timelineData.length - 1);
            const nextChunkId = `${nextChunkStart}-${nextChunkEnd}`;

            if (!this.dataChunks.has(nextChunkId) && nextChunkStart < this.timelineData.length) {
                // Load in background without waiting
                this.loadDataChunk(nextChunkStart, nextChunkEnd).catch(console.error);
            }
        }

        return chunk;
    }

    async getDataAtPosition(position) {
        const chunk = await this.ensureDataLoaded(position);

        if (!chunk || !this.timelineData[position]) {
            return null;
        }

        // Find matching data point by timestamp
        const targetTimestamp = this.timelineData[position].timestamp;
        const dataPoint = chunk.find(point => point.timestamp === targetTimestamp);

        return dataPoint || null;
    }

    // === UI Event Handlers (adapted from original) ===

    setupRaceSelector() {
        const raceDropdown = document.getElementById('race-dropdown');
        if (raceDropdown) {
            raceDropdown.addEventListener('change', (event) => {
                this.selectedRace = event.target.value;
                this.onRaceSelectionChange();
            });
            raceDropdown.value = this.selectedRace;
        }
    }

    async onRaceSelectionChange() {
        console.log(`🏁 Race selection changed to: ${this.selectedRace}`);

        this.pausePlayback();
        this.selectedCar = null;
        this.timelineData = [];
        this.dataChunks.clear();

        // Disable playback controls during race change
        this.disablePlaybackControls();

        const carDropdown = document.getElementById('car-dropdown');
        if (carDropdown) {
            carDropdown.innerHTML = '<option value="">Loading cars...</option>';
            carDropdown.value = '';
        }

        this.clearVisuals();
        this.updateRaceInTitle();

        await this.loadAvailableCars();

        // Keep controls disabled until a car is selected
        // They will be re-enabled in onCarSelectionChange()
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

    async onCarSelectionChange() {
        if (!this.selectedCar) return;

        console.log(`🚗 Car selected: ${this.selectedCar}`);

        this.pausePlayback();
        this.dataChunks.clear();

        // Disable playback controls during data loading
        this.disablePlaybackControls();
        this.showLoadingMessage(`Loading data for ${this.selectedCar}...`);

        try {
            await this.loadCarTimeline(this.selectedCar);
            this.updateTimeline();
            this.hideLoadingMessage();

            // Show GPS trace and load initial chunk
            await this.showGPSTrace();
            await this.updateCarPosition(0);

            // Re-enable playback controls after GPS data is rendered
            this.enablePlaybackControls();

        } catch (error) {
            this.showError(`Failed to load data for ${this.selectedCar}`);
            this.hideLoadingMessage();
            // Re-enable controls even on error so user can try again
            this.enablePlaybackControls();
        }
    }

    populateCarDropdown() {
        const carDropdown = document.getElementById('car-dropdown');
        if (!carDropdown) return;

        if (!this.availableCars || this.availableCars.length === 0) {
            carDropdown.innerHTML = '<option value="">No cars available for this race</option>';
            return;
        }

        carDropdown.innerHTML = '<option value="">Select a car...</option>';

        this.availableCars.forEach(car => {
            const option = document.createElement('option');
            option.value = car.id;
            option.textContent = car.display_name;
            carDropdown.appendChild(option);
        });

        console.log(`✅ Populated dropdown with ${this.availableCars.length} cars for ${this.selectedRace}`);

        if (this.availableCars.length > 0) {
            setTimeout(() => carDropdown.focus(), 100);
        }
    }

    setupTimeline() {
        const timeSlider = document.getElementById('time-slider');
        if (timeSlider) {
            timeSlider.addEventListener('input', (event) => {
                this.updateCarPosition(parseInt(event.target.value));
            });
        }

        this.setupVideoControls();
    }

    setupVideoControls() {
        const playPauseButton = document.getElementById('play-pause-button');
        const stepBack5s = document.getElementById('step-back-5s');
        const stepForward5s = document.getElementById('step-forward-5s');

        if (playPauseButton) {
            playPauseButton.addEventListener('click', () => this.togglePlayPause());
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
    }

    disablePlaybackControls() {
        const playPauseButton = document.getElementById('play-pause-button');
        const stepBack5s = document.getElementById('step-back-5s');
        const stepForward5s = document.getElementById('step-forward-5s');
        const timeSlider = document.getElementById('time-slider');

        // Disable and style the controls
        if (playPauseButton) {
            playPauseButton.disabled = true;
            playPauseButton.style.opacity = '0.4';
            playPauseButton.style.cursor = 'not-allowed';
            playPauseButton.style.backgroundColor = '#f0f0f0';
            playPauseButton.style.color = '#999';
            playPauseButton.style.border = '2px solid #ccc';
            playPauseButton.textContent = '⏸️ Loading...';
            playPauseButton.style.pointerEvents = 'none';
        }

        if (stepBack5s) {
            stepBack5s.disabled = true;
            stepBack5s.style.opacity = '0.4';
            stepBack5s.style.cursor = 'not-allowed';
            stepBack5s.style.backgroundColor = '#f0f0f0';
            stepBack5s.style.color = '#999';
            stepBack5s.style.border = '2px solid #ccc';
            stepBack5s.style.pointerEvents = 'none';
        }

        if (stepForward5s) {
            stepForward5s.disabled = true;
            stepForward5s.style.opacity = '0.4';
            stepForward5s.style.cursor = 'not-allowed';
            stepForward5s.style.backgroundColor = '#f0f0f0';
            stepForward5s.style.color = '#999';
            stepForward5s.style.border = '2px solid #ccc';
            stepForward5s.style.pointerEvents = 'none';
        }

        if (timeSlider) {
            timeSlider.disabled = true;
            timeSlider.style.opacity = '0.4';
            timeSlider.style.cursor = 'not-allowed';
            timeSlider.style.pointerEvents = 'none';
        }

        console.log('🔒 Playback controls disabled during data loading');
    }

    enablePlaybackControls() {
        const playPauseButton = document.getElementById('play-pause-button');
        const stepBack5s = document.getElementById('step-back-5s');
        const stepForward5s = document.getElementById('step-forward-5s');
        const timeSlider = document.getElementById('time-slider');

        // Re-enable and restore style of the controls
        if (playPauseButton) {
            playPauseButton.disabled = false;
            playPauseButton.style.opacity = '1';
            playPauseButton.style.cursor = 'pointer';
            playPauseButton.style.backgroundColor = '';
            playPauseButton.style.color = '';
            playPauseButton.style.border = '';
            playPauseButton.style.pointerEvents = 'auto';
            playPauseButton.textContent = '▶️ Play';
            playPauseButton.className = 'video-button play-button';
        }

        if (stepBack5s) {
            stepBack5s.disabled = false;
            stepBack5s.style.opacity = '1';
            stepBack5s.style.cursor = 'pointer';
            stepBack5s.style.backgroundColor = '';
            stepBack5s.style.color = '';
            stepBack5s.style.border = '';
            stepBack5s.style.pointerEvents = 'auto';
        }

        if (stepForward5s) {
            stepForward5s.disabled = false;
            stepForward5s.style.opacity = '1';
            stepForward5s.style.cursor = 'pointer';
            stepForward5s.style.backgroundColor = '';
            stepForward5s.style.color = '';
            stepForward5s.style.border = '';
            stepForward5s.style.pointerEvents = 'auto';
        }

        if (timeSlider) {
            timeSlider.disabled = false;
            timeSlider.style.opacity = '1';
            timeSlider.style.cursor = 'pointer';
            timeSlider.style.pointerEvents = 'auto';
        }

        console.log('🔓 Playback controls enabled');
    }

    updateTimeline() {
        const timeSlider = document.getElementById('time-slider');
        const totalTimeSpan = document.getElementById('total-time');

        if (timeSlider && this.timelineData.length > 0) {
            timeSlider.max = this.timelineData.length - 1;
            timeSlider.value = 0;

            const startTime = new Date(this.timelineData[0].timestamp);
            const endTime = new Date(this.timelineData[this.timelineData.length - 1].timestamp);
            const totalSeconds = (endTime - startTime) / 1000;

            if (totalTimeSpan) {
                totalTimeSpan.textContent = this.formatTime(totalSeconds);
            }

            this.currentPosition = 0;
        }
    }

    async updateCarPosition(position) {
        if (position < 0 || position >= this.timelineData.length) {
            return;
        }

        this.currentPosition = position;

        // Update time display
        const currentTimeSpan = document.getElementById('current-time');
        const lapInfoSpan = document.getElementById('lap-info');

        if (currentTimeSpan && this.timelineData.length > 0) {
            const startTime = new Date(this.timelineData[0].timestamp);
            const currentTime = new Date(this.timelineData[position].timestamp);
            const elapsedSeconds = (currentTime - startTime) / 1000;
            currentTimeSpan.textContent = this.formatTime(elapsedSeconds);
        }

        // Get data for this position
        const dataPoint = await this.getDataAtPosition(position);

        if (dataPoint) {
            if (lapInfoSpan) {
                lapInfoSpan.textContent = `Lap: ${dataPoint.lap}`;
            }

            this.updateTelemetryDisplay(dataPoint);
            this.updateLapDataDisplay(dataPoint);
            this.plotCarOnMap(dataPoint.latitude, dataPoint.longitude);
        } else {
            console.warn(`No data available at position ${position}`);
        }
    }

    // === Playback Controls ===

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

        const playbackInterval = 100; // 100ms = smooth playback

        this.playbackInterval = setInterval(() => {
            const timeSlider = document.getElementById('time-slider');
            if (!timeSlider) return;

            const nextPosition = this.currentPosition + 1;

            if (nextPosition >= this.timelineData.length) {
                this.pausePlayback();
                return;
            }

            timeSlider.value = nextPosition;
            this.updateCarPosition(nextPosition);
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

    jumpTime(seconds) {
        if (!this.timelineData.length) return;

        const currentTime = new Date(this.timelineData[this.currentPosition].timestamp);
        const targetTime = new Date(currentTime.getTime() + seconds * 1000);

        // Find closest position
        let closestPosition = this.currentPosition;
        let minDiff = Math.abs(new Date(this.timelineData[this.currentPosition].timestamp) - targetTime);

        for (let i = 0; i < this.timelineData.length; i++) {
            const diff = Math.abs(new Date(this.timelineData[i].timestamp) - targetTime);
            if (diff < minDiff) {
                minDiff = diff;
                closestPosition = i;
            }
        }

        const timeSlider = document.getElementById('time-slider');
        if (timeSlider) {
            timeSlider.value = closestPosition;
            this.updateCarPosition(closestPosition);
        }
    }

    // === Visual Methods (mostly same as original) ===

    loadTrackMap() {
        const img = new Image();
        const timestamp = new Date().getTime();
        const imageUrl = `race_maps/barber motorsports park.png?t=${timestamp}`;

        img.onload = () => {
            this.imageWidth = img.width;
            this.imageHeight = img.height;

            this.g.append("image")
                .attr("href", imageUrl)
                .attr("width", this.imageWidth)
                .attr("height", this.imageHeight)
                .attr("x", 0)
                .attr("y", 0);

            this.fitToScreen();
            this.drawStartFinishLine();

            console.log(`✅ Track map loaded: ${this.imageWidth}x${this.imageHeight}`);
        };

        img.onerror = () => {
            console.error("❌ Failed to load track map image");
            this.showError("Failed to load track map. Please check if the image file exists.");
        };

        img.src = imageUrl;
    }

    drawStartFinishLine() {
        const startFinishLat = 33.53260;
        const startFinishLon = -86.61963;
        const coords = this.convertGPSToMap(startFinishLat, startFinishLon);

        if (coords) {
            const startFinishGroup = this.g.append("g").attr("class", "start-finish-line");
            const lineLength = 40;
            const lineWidth = 6;

            startFinishGroup.append("rect")
                .attr("x", coords.x - lineLength/2)
                .attr("y", coords.y - lineWidth/2)
                .attr("width", lineLength)
                .attr("height", lineWidth)
                .attr("fill", "white")
                .attr("stroke", "black")
                .attr("stroke-width", 2);

            startFinishGroup.attr("transform", `rotate(45, ${coords.x}, ${coords.y})`);

            const squareSize = 4;
            for (let i = 0; i < lineLength / squareSize; i++) {
                if (i % 2 === 0) {
                    startFinishGroup.append("rect")
                        .attr("x", coords.x - lineLength/2 + i * squareSize)
                        .attr("y", coords.y - lineWidth/2)
                        .attr("width", squareSize)
                        .attr("height", lineWidth)
                        .attr("fill", "black");
                }
            }

            console.log(`✅ Start/finish line drawn at GPS: ${startFinishLat.toFixed(6)}, ${startFinishLon.toFixed(6)}`);
        }
    }

    convertGPSToMap(latitude, longitude) {
        const trackBounds = {
            minLat: 33.5293,
            maxLat: 33.5359,
            minLon: -86.6244,
            maxLon: -86.6145
        };

        const normalizedX = (longitude - trackBounds.minLon) / (trackBounds.maxLon - trackBounds.minLon);
        const normalizedY = (latitude - trackBounds.minLat) / (trackBounds.maxLat - trackBounds.minLat);

        const rotationAngle = 0.05;
        const cosAngle = Math.cos(rotationAngle);
        const sinAngle = Math.sin(rotationAngle);

        const centeredX = normalizedX - 0.5;
        const centeredY = normalizedY - 0.5;

        const rotatedX = centeredX * cosAngle - centeredY * sinAngle;
        const rotatedY = centeredX * sinAngle + centeredY * cosAngle;

        const calibratedX = (rotatedX + 0.5) * 0.92 + 0.04;
        const calibratedY = (rotatedY + 0.5) * 0.92 + 0.04;

        const mapX = calibratedX * this.imageWidth;
        const mapY = (1 - calibratedY) * this.imageHeight;

        if (mapX >= -200 && mapX <= this.imageWidth + 200 && mapY >= -200 && mapY <= this.imageHeight + 200) {
            return { x: mapX, y: mapY };
        }

        return null;
    }

    plotCarOnMap(latitude, longitude) {
        if (this.carMarker) {
            try {
                this.carMarker.remove();
            } catch (e) {}
            this.carMarker = null;
        }

        this.g.selectAll('.car-marker').remove();
        const coords = this.convertGPSToMap(latitude, longitude);

        if (coords) {
            this.carMarker = this.g.append("circle")
                .attr("class", "car-marker")
                .attr("cx", coords.x)
                .attr("cy", coords.y)
                .attr("r", 8)
                .attr("fill", "#ff0000")
                .attr("stroke", "#ffffff")
                .attr("stroke-width", 3)
                .style("cursor", "pointer");
        }
    }

    updateTelemetryDisplay(dataPoint) {
        const speedValue = document.getElementById('speed-value');
        const gearValue = document.getElementById('gear-value');
        const throttleValue = document.getElementById('throttle-value');
        const brakeRearValue = document.getElementById('brake-rear-value');
        const brakeFrontValue = document.getElementById('brake-front-value');

        if (speedValue) {
            if (dataPoint.speed !== null && dataPoint.speed !== undefined) {
                const speed = this.speedUnit === 'kph'
                    ? (dataPoint.speed * 1.60934)
                    : dataPoint.speed;
                speedValue.textContent = `${speed.toFixed(1)} ${this.speedUnit}`;
            } else {
                speedValue.textContent = '--';
            }
        }

        if (gearValue) {
            gearValue.textContent = dataPoint.gear !== null && dataPoint.gear !== undefined
                ? Math.round(dataPoint.gear).toString()
                : '--';
        }

        if (throttleValue) {
            throttleValue.textContent = dataPoint.throttle !== null && dataPoint.throttle !== undefined
                ? `${dataPoint.throttle.toFixed(1)}%`
                : '--';
        }

        if (brakeRearValue) {
            brakeRearValue.textContent = dataPoint.brake_rear !== null && dataPoint.brake_rear !== undefined
                ? `${dataPoint.brake_rear.toFixed(1)} psi`
                : '--';
        }

        if (brakeFrontValue) {
            brakeFrontValue.textContent = dataPoint.brake_front !== null && dataPoint.brake_front !== undefined
                ? `${dataPoint.brake_front.toFixed(1)} psi`
                : '--';
        }
    }

    updateLapDataDisplay(dataPoint) {
        if (!this.selectedCar || !dataPoint) return;

        const lapNumber = dataPoint.lap;
        const lapNumberValue = document.getElementById('lap-number-value');

        if (lapNumberValue) {
            lapNumberValue.textContent = lapNumber;
        }

        // Use cached lap data
        const lapInfo = this.lapData[lapNumber];

        const lapStartValue = document.getElementById('lap-start-time-value');
        const lapEndValue = document.getElementById('lap-end-time-value');
        const lapTotalValue = document.getElementById('lap-total-time-value');

        if (lapStartValue) {
            lapStartValue.textContent = lapInfo?.start_time ? this.formatLapTime(lapInfo.start_time) : '--:--:---';
        }

        if (lapEndValue) {
            lapEndValue.textContent = lapInfo?.end_time ? this.formatLapTime(lapInfo.end_time) : '--:--:---';
        }

        if (lapTotalValue) {
            if (lapInfo?.start_time && lapInfo?.end_time) {
                const startTime = new Date(lapInfo.start_time);
                const endTime = new Date(lapInfo.end_time);
                const duration = endTime - startTime;
                lapTotalValue.textContent = duration > 0 ? this.formatLapDuration(duration) : '--:--:---';
            } else {
                lapTotalValue.textContent = '--:--:---';
            }
        }
    }

    // === Utility Methods (same as original) ===

    formatTime(seconds) {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = Math.floor(seconds % 60);
        return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }

    formatLapTime(timestamp) {
        if (!timestamp) return '--:--:---';
        const date = new Date(timestamp);
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

    updateTitle() {
        if (!this.trackData) return;

        const eventNameElement = document.getElementById('event-name');
        if (eventNameElement) {
            eventNameElement.style.display = 'none';
        }

        const trackInfoElement = document.getElementById('track-info');
        if (trackInfoElement) {
            trackInfoElement.textContent =
                `${this.trackData.track_name.toUpperCase()} | ${this.trackData.track_length.toUpperCase()}`;
        }

        this.updateRaceInTitle();
    }

    updateRaceInTitle() {
        const eventDetailsElement = document.getElementById('event-details');
        if (eventDetailsElement && this.trackData) {
            const locationParts = this.trackData.location.split(' ');
            const state = locationParts[locationParts.length - 1];
            const city = locationParts.slice(0, -1).join(' ');
            const raceNumber = this.selectedRace === 'R1' ? '1' : '2';
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

            if (this.imageWidth > 0 && this.imageHeight > 0) {
                this.fitToScreen();
            }
        }
    }

    fitToScreen() {
        if (this.imageWidth === 0 || this.imageHeight === 0) return;

        const padding = 20;
        const scaleX = (this.containerWidth - padding * 2) / this.imageWidth;
        const scaleY = (this.containerHeight - padding * 2) / this.imageHeight;
        const scale = Math.min(scaleX, scaleY);

        const x = (this.containerWidth - this.imageWidth * scale) / 2;
        const y = (this.containerHeight - this.imageHeight * scale) / 2;

        const transform = d3.zoomIdentity.translate(x, y).scale(scale);

        this.svg.transition()
            .duration(500)
            .call(this.zoom.transform, transform);
    }

    clearVisuals() {
        this.g.selectAll('.gps-trace').remove();
        this.g.selectAll('.car-marker').remove();
    }

    async showGPSTrace() {
        // Remove existing trace
        this.g.selectAll('.gps-trace').remove();

        if (this.timelineData.length === 0) return;

        console.log('🔄 Loading GPS trace for complete race...');

        // Show a loading message
        this.showLoadingMessage('Loading GPS trace...');

        try {
            // Load data in chunks to get GPS coordinates
            const chunkSize = Math.min(this.chunkSizeSeconds * 10, 600); // ~60 seconds worth of data points
            const gpsPoints = [];

            for (let i = 0; i < this.timelineData.length; i += chunkSize) {
                const chunkEnd = Math.min(i + chunkSize, this.timelineData.length - 1);
                const chunk = await this.loadDataChunk(i, chunkEnd);

                if (chunk) {
                    // Extract GPS points from chunk, sampling every few points for performance
                    const sampleRate = Math.max(1, Math.floor(chunk.length / 100)); // Sample ~100 points per chunk
                    for (let j = 0; j < chunk.length; j += sampleRate) {
                        const point = chunk[j];
                        if (point && point.latitude !== undefined && point.longitude !== undefined) {
                            gpsPoints.push({ latitude: point.latitude, longitude: point.longitude });
                        }
                    }
                }
            }

            // Render GPS trace from collected points
            for (const point of gpsPoints) {
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

            console.log(`✅ GPS trace rendered: ${gpsPoints.length} points`);

        } catch (error) {
            console.error('❌ Error loading GPS trace:', error);
            this.showError('Failed to load GPS trace');
            return;
        }

        // Hide loading message
        this.hideLoadingMessage();
    }

    showLoadingMessage(message) {
        this.g.selectAll('.loading-message').remove();

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
        this.g.selectAll('.loading-message, .error-message').remove();

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
        this.speedUnit = this.speedUnit === 'mph' ? 'kph' : 'mph';

        const toggleButton = document.getElementById('speed-unit-toggle');
        if (toggleButton) {
            toggleButton.textContent = this.speedUnit;
        }

        if (this.timelineData.length > 0) {
            this.updateCarPosition(this.currentPosition);
        }
    }
}

// Global variables
let apiTrackMapViewer;

// Global function for speed unit toggle
function toggleSpeedUnit() {
    if (apiTrackMapViewer) {
        apiTrackMapViewer.toggleSpeedUnit();
    }
}

// Initialize when page loads
document.addEventListener("DOMContentLoaded", () => {
    console.log("🚀 Initializing API-based Track Map Viewer...");
    apiTrackMapViewer = new ApiTrackMapViewer();
});