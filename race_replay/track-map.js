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
        this.containerWidth = Math.min(window.innerWidth * 0.9, 1200);
        this.containerHeight = Math.min(window.innerHeight * 0.765, 800);

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

        // Last known telemetry values for fallback
        this.lastKnownTelemetry = {
            speed: null,
            gear: null,
            throttle: null,
            brake_rear: null,
            brake_front: null,
            engine_rpm: null,
            steering_angle: null,
            g_force_x: null,
            g_force_y: null,
            lap_distance: null
        };

        // Chunk management
        this.chunkSizeSeconds = 60; // Load 60-second chunks
        this.preloadAhead = 2; // Preload 2 chunks ahead

        // Visual elements
        this.carMarker = null;
        this.trackData = null;
        this.lapData = {};
        this.bestLapInfo = null;

        // AI Assistant properties
        this.aiRegion = 'us-west-2'; // Default region
        this.aiConnected = false;
        this.aiMessaging = false;
        this.currentLapNumber = null;

        this.init();
    }

    async init() {
        console.log('🚀 Initializing API-based Track Map Viewer...');

        // Set up SVG container (same as original)
        console.log('📐 Setting up SVG container...');
        this.svg = d3.select("#track-map")
            .attr("width", this.containerWidth)
            .attr("height", this.containerHeight);

        this.g = this.svg.append("g");

        // Set up zoom behavior
        console.log('🔍 Setting up zoom behavior...');
        this.zoom = d3.zoom()
            .scaleExtent([0.1, 10])
            .on("zoom", (event) => {
                this.g.attr("transform", event.transform);
                this.currentZoom = event.transform.k;
            });

        this.svg.call(this.zoom);

        // Load initial data
        console.log('📊 Loading initial data...');
        await this.loadTrackData();
        await this.loadRaces();

        // Setup UI components
        console.log('🎛️ Setting up UI components...');
        this.setupRaceSelector();
        this.setupCarSelector();
        this.setupTimeline();
        this.setupAIAssistant();

        // Disable Race Time controls initially (no car loaded)
        this.disableRaceTimeControls();

        // Disable AI controls initially (no car loaded)
        this.disableAIControls();

        console.log("🗺️ About to load track map...");
        this.loadTrackMap();
        console.log("🗺️ Track map loading initiated");

        // Load initial car data
        console.log("🔄 About to load available cars...");
        await this.loadAvailableCars();
        console.log("✅ Car loading completed in init");

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
            this.bestLapInfo = {
                bestLap: data.best_lap,
                bestLapTime: data.best_lap_time,
                bestLapTimeMs: data.best_lap_time_ms
            };

            console.log('✅ Lap data loaded:', Object.keys(this.lapData).length, 'laps');
            console.log('✅ Best lap:', data.best_lap, 'with time:', data.best_lap_time);

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
                `${this.baseUrl}/telemetry/${this.selectedRace}/${this.selectedCar}/chunk?start_time=${encodeURIComponent(startTime)}&end_time=${encodeURIComponent(endTime)}`
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

        // Find matching data point by timestamp - first try exact match
        const targetTimestamp = this.timelineData[position].timestamp;
        let dataPoint = chunk.find(point => point.timestamp === targetTimestamp);

        // If no exact match, find closest timestamp within a reasonable range
        if (!dataPoint && chunk.length > 0) {
            const targetTime = new Date(targetTimestamp).getTime();
            let closestPoint = null;
            let minTimeDiff = Infinity;

            for (const point of chunk) {
                const pointTime = new Date(point.timestamp).getTime();
                const timeDiff = Math.abs(pointTime - targetTime);

                // Only consider points within 1 second of target time
                if (timeDiff < 1000 && timeDiff < minTimeDiff) {
                    minTimeDiff = timeDiff;
                    closestPoint = point;
                }
            }

            dataPoint = closestPoint;
        }

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

        // Disable Race Time controls during race change
        this.disableRaceTimeControls();

        // Disable AI controls during race change
        this.disableAIControls();

        const carDropdown = document.getElementById('car-dropdown');
        if (carDropdown) {
            carDropdown.innerHTML = '<option value="">Loading cars...</option>';
            carDropdown.value = '';
        }

        this.clearVisuals();
        this.updateRaceInTitle();

        await this.loadAvailableCars();

        // Update AI context after race change
        this.updateAIContextInfo();

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

        // Clear previous car visuals and telemetry data immediately
        this.clearVisuals();
        this.clearLastKnownTelemetry();

        // Disable Race Time controls during loading
        this.disableRaceTimeControls();

        // Disable AI controls during loading
        this.disableAIControls();

        this.showEnhancedLoadingMessage(`Loading telemetry data for ${this.selectedCar}...`);

        try {
            await this.loadCarTimeline(this.selectedCar);
            this.updateTimeline();

            // Update progress
            this.showEnhancedLoadingMessage(`Processing lap data for ${this.selectedCar}...`);

            // Load initial chunk and show first position
            await this.updateCarPosition(0);

            // Update progress
            this.showEnhancedLoadingMessage(`Drawing GPS track for ${this.selectedCar}...`);

            // Draw GPS trace for the selected car
            await this.drawGPSTrace();

            // Populate lap dropdown with available laps
            this.populateLapDropdown();

            // Hide loading message after GPS trace is complete
            this.hideEnhancedLoadingMessage();

            // Re-enable Race Time controls after loading is complete
            this.enableRaceTimeControls();

            // Re-enable AI controls after GPS trace is fully loaded
            this.enableAIControls();

            // Update AI context after successful car selection
            this.updateAIContextInfo();

        } catch (error) {
            this.showError(`Failed to load data for ${this.selectedCar}`);
            this.hideEnhancedLoadingMessage();

            // Re-enable race time controls even on error (for basic functionality)
            this.enableRaceTimeControls();

            // Keep AI controls disabled on error (no GPS trace loaded)
            // this.enableAIControls(); // Intentionally commented out

            // Update AI context even on error
            this.updateAIContextInfo();
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
        const lapDropdown = document.getElementById('lap-dropdown');

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

            // Update AI context if lap has changed
            const newLapNumber = dataPoint.lap;
            if (this.currentLapNumber !== newLapNumber) {
                this.currentLapNumber = newLapNumber;
                this.updateAIContextInfo();
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
            console.log(`Jumped to lap ${lapNumber} at index ${lapStartIndex}`);
        } else {
            console.warn(`Lap ${lapNumber} not found in timeline data`);
        }
    }

    populateLapDropdown() {
        const lapDropdown = document.getElementById('lap-dropdown');
        if (!lapDropdown || !this.timelineData.length) return;

        // Clear existing options except the first "Select Lap" option
        while (lapDropdown.children.length > 1) {
            lapDropdown.removeChild(lapDropdown.lastChild);
        }

        // Extract unique lap numbers from timeline data
        const uniqueLaps = [...new Set(this.timelineData.map(point => point.lap))].sort((a, b) => a - b);

        // Add lap options
        uniqueLaps.forEach(lap => {
            const option = document.createElement('option');
            option.value = lap;
            option.textContent = `Lap ${lap}`;
            lapDropdown.appendChild(option);
        });

        console.log(`Populated lap dropdown with ${uniqueLaps.length} laps: ${uniqueLaps.join(', ')}`);
    }

    calculateBestLap() {
        // Use the pre-calculated best lap info from the API
        if (!this.bestLapInfo || !this.bestLapInfo.bestLap) {
            return { bestLap: null, bestTime: null, bestDuration: null };
        }

        return {
            bestLap: this.bestLapInfo.bestLap,
            bestTime: this.bestLapInfo.bestLapTime,
            bestDuration: this.bestLapInfo.bestLapTimeMs
        };
    }

    calculateTimeDelta(currentLapNumber, bestDuration) {
        if (!bestDuration || !this.lapData[currentLapNumber]) {
            return null;
        }

        const currentLapInfo = this.lapData[currentLapNumber];
        const currentDuration = currentLapInfo.lap_time_ms;

        if (!currentDuration || currentDuration <= 0) {
            return null;
        }

        return currentDuration - bestDuration;
    }

    // === Visual Methods (mostly same as original) ===

    loadTrackMap() {
        const img = new Image();
        const timestamp = new Date().getTime();
        const imageUrl = `race_maps/barber with numbering.png?t=${timestamp}`;

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
            // this.drawStartFinishLine(); // Commented out - start/finish line is already in the numbered track map image

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

        // Apply offset adjustments to better align GPS trace with numbered track map
        // Move GPS trace left (negative X) and up (negative Y)
        const offsetX = 0; // Move left by 5 more pixels (was 5, now 0)
        const offsetY = -20; // Move up by 5 more pixels (was -15, now -20)

        const mapX = calibratedX * this.imageWidth + offsetX;
        const mapY = (1 - calibratedY) * this.imageHeight + offsetY;

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
        const engineRpmValue = document.getElementById('engine-rpm-value');
        const steeringAngleValue = document.getElementById('steering-angle-value');
        const gForceXValue = document.getElementById('g-force-x-value');
        const gForceYValue = document.getElementById('g-force-y-value');
        const lapDistanceValue = document.getElementById('lap-distance-value');

        // Update last known values when data is available
        if (dataPoint.speed !== null && dataPoint.speed !== undefined) {
            this.lastKnownTelemetry.speed = dataPoint.speed;
        }
        if (dataPoint.gear !== null && dataPoint.gear !== undefined) {
            this.lastKnownTelemetry.gear = dataPoint.gear;
        }
        if (dataPoint.throttle !== null && dataPoint.throttle !== undefined) {
            this.lastKnownTelemetry.throttle = dataPoint.throttle;
        }
        if (dataPoint.brake_rear !== null && dataPoint.brake_rear !== undefined) {
            this.lastKnownTelemetry.brake_rear = dataPoint.brake_rear;
        }
        if (dataPoint.brake_front !== null && dataPoint.brake_front !== undefined) {
            this.lastKnownTelemetry.brake_front = dataPoint.brake_front;
        }
        if (dataPoint.engine_rpm !== null && dataPoint.engine_rpm !== undefined) {
            this.lastKnownTelemetry.engine_rpm = dataPoint.engine_rpm;
        }
        if (dataPoint.steering_angle !== null && dataPoint.steering_angle !== undefined) {
            this.lastKnownTelemetry.steering_angle = dataPoint.steering_angle;
        }
        if (dataPoint.g_force_x !== null && dataPoint.g_force_x !== undefined) {
            this.lastKnownTelemetry.g_force_x = dataPoint.g_force_x;
        }
        if (dataPoint.g_force_y !== null && dataPoint.g_force_y !== undefined) {
            this.lastKnownTelemetry.g_force_y = dataPoint.g_force_y;
        }
        if (dataPoint.lap_distance !== null && dataPoint.lap_distance !== undefined) {
            this.lastKnownTelemetry.lap_distance = dataPoint.lap_distance;
        }

        // Display speed - use current data or fallback to last known value
        if (speedValue) {
            const speedToShow = dataPoint.speed !== null && dataPoint.speed !== undefined
                ? dataPoint.speed
                : this.lastKnownTelemetry.speed;

            if (speedToShow !== null) {
                const speed = this.speedUnit === 'kph'
                    ? (speedToShow * 1.60934)
                    : speedToShow;
                speedValue.textContent = `${speed.toFixed(1)} ${this.speedUnit}`;
            } else {
                speedValue.textContent = '--';
            }
        }

        // Display gear - use current data or fallback to last known value
        if (gearValue) {
            const gearToShow = dataPoint.gear !== null && dataPoint.gear !== undefined
                ? dataPoint.gear
                : this.lastKnownTelemetry.gear;

            gearValue.textContent = gearToShow !== null
                ? Math.round(gearToShow).toString()
                : '--';
        }

        // Display throttle - use current data or fallback to last known value
        if (throttleValue) {
            const throttleToShow = dataPoint.throttle !== null && dataPoint.throttle !== undefined
                ? dataPoint.throttle
                : this.lastKnownTelemetry.throttle;

            throttleValue.textContent = throttleToShow !== null
                ? `${throttleToShow.toFixed(1)}%`
                : '--';
        }

        // Display rear brake - use current data or fallback to last known value
        if (brakeRearValue) {
            const brakeRearToShow = dataPoint.brake_rear !== null && dataPoint.brake_rear !== undefined
                ? dataPoint.brake_rear
                : this.lastKnownTelemetry.brake_rear;

            brakeRearValue.textContent = brakeRearToShow !== null
                ? `${brakeRearToShow.toFixed(1)} psi`
                : '--';
        }

        // Display front brake - use current data or fallback to last known value
        if (brakeFrontValue) {
            const brakeFrontToShow = dataPoint.brake_front !== null && dataPoint.brake_front !== undefined
                ? dataPoint.brake_front
                : this.lastKnownTelemetry.brake_front;

            brakeFrontValue.textContent = brakeFrontToShow !== null
                ? `${brakeFrontToShow.toFixed(1)} psi`
                : '--';
        }

        // Display engine RPM - use current data or fallback to last known value
        if (engineRpmValue) {
            const engineRpmToShow = dataPoint.engine_rpm !== null && dataPoint.engine_rpm !== undefined
                ? dataPoint.engine_rpm
                : this.lastKnownTelemetry.engine_rpm;

            engineRpmValue.textContent = engineRpmToShow !== null
                ? `${Math.round(engineRpmToShow)} rpm`
                : '--';
        }

        // Display steering angle - use current data or fallback to last known value
        if (steeringAngleValue) {
            const steeringAngleToShow = dataPoint.steering_angle !== null && dataPoint.steering_angle !== undefined
                ? dataPoint.steering_angle
                : this.lastKnownTelemetry.steering_angle;

            steeringAngleValue.textContent = steeringAngleToShow !== null
                ? `${steeringAngleToShow.toFixed(1)}°`
                : '--';
        }

        // Display longitudinal G-force - use current data or fallback to last known value
        if (gForceXValue) {
            const gForceXToShow = dataPoint.g_force_x !== null && dataPoint.g_force_x !== undefined
                ? dataPoint.g_force_x
                : this.lastKnownTelemetry.g_force_x;

            gForceXValue.textContent = gForceXToShow !== null
                ? `${gForceXToShow.toFixed(2)}g`
                : '--';
        }

        // Display lateral G-force - use current data or fallback to last known value
        if (gForceYValue) {
            const gForceYToShow = dataPoint.g_force_y !== null && dataPoint.g_force_y !== undefined
                ? dataPoint.g_force_y
                : this.lastKnownTelemetry.g_force_y;

            gForceYValue.textContent = gForceYToShow !== null
                ? `${gForceYToShow.toFixed(2)}g`
                : '--';
        }

        // Display lap distance - use current data or fallback to last known value
        if (lapDistanceValue) {
            const lapDistanceToShow = dataPoint.lap_distance !== null && dataPoint.lap_distance !== undefined
                ? dataPoint.lap_distance
                : this.lastKnownTelemetry.lap_distance;

            if (lapDistanceToShow !== null) {
                // Convert units based on speed unit setting
                if (this.speedUnit === 'mph') {
                    // Convert meters to feet (1 meter = 3.28084 feet)
                    const lapDistanceFeet = lapDistanceToShow * 3.28084;
                    lapDistanceValue.textContent = `${lapDistanceFeet.toFixed(0)}ft`;
                } else {
                    // Show in meters
                    lapDistanceValue.textContent = `${lapDistanceToShow.toFixed(0)}m`;
                }
            } else {
                lapDistanceValue.textContent = '--';
            }
        }
    }

    updateLapDataDisplay(dataPoint) {
        if (!this.selectedCar || !dataPoint) return;

        const lapNumber = dataPoint.lap;
        const lapNumberValue = document.getElementById('lap-number-value');
        const lapTotalValue = document.getElementById('lap-total-time-value');
        const bestLapValue = document.getElementById('best-lap-value');
        const bestLapTimeValue = document.getElementById('best-lap-time-value');
        const timeDeltaValue = document.getElementById('time-delta-value');

        // Update current lap number
        if (lapNumberValue) {
            lapNumberValue.textContent = lapNumber;
        }

        // Calculate best lap information
        const bestLapInfo = this.calculateBestLap();

        // Update current lap time using accurate analysis data
        const currentLapInfo = this.lapData[lapNumber];
        if (lapTotalValue) {
            if (currentLapInfo && currentLapInfo.lap_time) {
                lapTotalValue.textContent = currentLapInfo.lap_time;
            } else {
                lapTotalValue.textContent = '--:--:---';
            }
        }

        // Update best lap information using pre-calculated data
        if (bestLapValue && bestLapTimeValue) {
            if (bestLapInfo.bestLap && bestLapInfo.bestTime) {
                bestLapValue.textContent = bestLapInfo.bestLap;
                bestLapTimeValue.textContent = bestLapInfo.bestTime;
            } else {
                bestLapValue.textContent = '--';
                bestLapTimeValue.textContent = '--:--:---';
            }
        }

        // Update time delta using accurate lap times
        if (timeDeltaValue) {
            const timeDelta = this.calculateTimeDelta(lapNumber, bestLapInfo.bestDuration);
            if (timeDelta !== null) {
                const deltaFormatted = this.formatLapDuration(Math.abs(timeDelta));
                if (timeDelta === 0) {
                    timeDeltaValue.textContent = '🏆 Best!';
                    timeDeltaValue.style.color = '#28a745'; // Green for best lap
                } else if (timeDelta > 0) {
                    timeDeltaValue.textContent = `+${deltaFormatted}`;
                    timeDeltaValue.style.color = '#dc3545'; // Red for slower
                } else {
                    // This shouldn't happen if best lap calculation is correct, but just in case
                    timeDeltaValue.textContent = `-${deltaFormatted}`;
                    timeDeltaValue.style.color = '#28a745'; // Green for faster
                }
            } else {
                timeDeltaValue.textContent = '--:--:---';
                timeDeltaValue.style.color = '#007bff'; // Default blue
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
        const newWidth = Math.min(window.innerWidth * 0.9, 1200);
        const newHeight = Math.min(window.innerHeight * 0.765, 800);

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

    async drawGPSTrace() {
        if (!this.selectedCar || !this.timelineData.length) return;

        console.log('🗺️ Drawing GPS trace for', this.selectedCar);

        try {
            // Clear any existing GPS trace
            this.g.selectAll('.gps-trace').remove();

            // Sample the timeline data to get manageable number of points (every 10th point)
            const sampledTimeline = this.timelineData.filter((_, index) => index % 10 === 0);

            // Load GPS data for trace in batches
            const batchSize = 100; // Load 100 points at a time
            const tracePoints = [];

            for (let i = 0; i < sampledTimeline.length; i += batchSize) {
                const batch = sampledTimeline.slice(i, i + batchSize);

                // Load chunk for this batch
                if (batch.length > 0) {
                    const chunk = await this.loadDataChunk(
                        this.timelineData.indexOf(batch[0]),
                        this.timelineData.indexOf(batch[batch.length - 1])
                    );

                    if (chunk) {
                        // Extract GPS coordinates from chunk
                        chunk.forEach(point => {
                            if (point.latitude && point.longitude) {
                                const coords = this.convertGPSToMap(point.latitude, point.longitude);
                                if (coords) {
                                    tracePoints.push(coords);
                                }
                            }
                        });
                    }
                }
            }

            if (tracePoints.length < 2) {
                console.warn('Not enough GPS points for trace');
                return;
            }

            console.log(`✅ Drawing GPS trace with ${tracePoints.length} points`);

            // Create line generator
            const line = d3.line()
                .x(d => d.x)
                .y(d => d.y)
                .curve(d3.curveCardinal);

            // Draw the GPS trace
            this.g.append("path")
                .datum(tracePoints)
                .attr("class", "gps-trace")
                .attr("d", line)
                .attr("fill", "none")
                .attr("stroke", "#00ff00")
                .attr("stroke-width", 3)
                .attr("stroke-opacity", 0.7)
                .style("pointer-events", "none");

        } catch (error) {
            console.error('❌ Error drawing GPS trace:', error);
        }
    }

    clearVisuals() {
        this.g.selectAll('.gps-trace').remove();
        this.g.selectAll('.car-marker').remove();
    }

    clearLastKnownTelemetry() {
        this.lastKnownTelemetry = {
            speed: null,
            gear: null,
            throttle: null,
            brake_rear: null,
            brake_front: null,
            engine_rpm: null,
            steering_angle: null,
            g_force_x: null,
            g_force_y: null,
            lap_distance: null
        };
    }

    showStatusMessage(message, isError = false) {
        this.g.selectAll('.status-message').remove();

        // Position in lower left corner with padding
        const padding = 20;
        const x = padding;
        const y = this.containerHeight - padding;

        // Create background rectangle for better readability
        const textElement = this.g.append("text")
            .attr("class", "status-message")
            .attr("x", x)
            .attr("y", y)
            .attr("text-anchor", "start")
            .attr("fill", isError ? "red" : "#007bff")
            .attr("font-size", "14px")
            .attr("font-weight", "bold")
            .text(message);

        // Add semi-transparent background
        const bbox = textElement.node().getBBox();
        this.g.insert("rect", ".status-message")
            .attr("class", "status-message-bg")
            .attr("x", bbox.x - 8)
            .attr("y", bbox.y - 4)
            .attr("width", bbox.width + 16)
            .attr("height", bbox.height + 8)
            .attr("fill", "white")
            .attr("fill-opacity", 0.9)
            .attr("stroke", isError ? "red" : "#007bff")
            .attr("stroke-width", 1)
            .attr("rx", 4);
    }

    hideStatusMessage() {
        this.g.selectAll('.status-message, .status-message-bg').remove();
    }

    showError(message) {
        this.showStatusMessage(message, true);
    }

    showEnhancedLoadingMessage(message) {
        console.log('🔄 Showing enhanced loading message:', message);

        // Remove any existing loading overlay
        this.hideEnhancedLoadingMessage();

        // Get the map container element
        const mapContainer = document.getElementById('main-map-container');
        if (!mapContainer) return;

        // Create loading overlay
        const loadingOverlay = document.createElement('div');
        loadingOverlay.className = 'loading-overlay';
        loadingOverlay.id = 'enhanced-loading-overlay';

        // Create loading message with spinner
        const loadingMessageDiv = document.createElement('div');
        loadingMessageDiv.className = 'loading-message';

        // Create spinner
        const spinner = document.createElement('div');
        spinner.className = 'loading-spinner';

        // Create text
        const messageText = document.createElement('span');
        messageText.textContent = message;

        // Assemble the loading message
        loadingMessageDiv.appendChild(spinner);
        loadingMessageDiv.appendChild(messageText);
        loadingOverlay.appendChild(loadingMessageDiv);

        // Position the overlay relative to the map container
        mapContainer.style.position = 'relative';
        mapContainer.appendChild(loadingOverlay);

        console.log('✅ Enhanced loading message displayed');
    }

    hideEnhancedLoadingMessage() {
        const existingOverlay = document.getElementById('enhanced-loading-overlay');
        if (existingOverlay) {
            existingOverlay.remove();
            console.log('✅ Enhanced loading message hidden');
        }
    }

    disableRaceTimeControls() {
        const timeSlider = document.getElementById('time-slider');
        const playPauseButton = document.getElementById('play-pause-button');
        const stepBackButton = document.getElementById('step-back-5s');
        const stepForwardButton = document.getElementById('step-forward-5s');
        const lapDropdown = document.getElementById('lap-dropdown');

        if (timeSlider) {
            timeSlider.disabled = true;
            timeSlider.style.opacity = '0.5';
            timeSlider.style.cursor = 'not-allowed';
        }

        if (playPauseButton) {
            playPauseButton.disabled = true;
            playPauseButton.style.opacity = '0.5';
            playPauseButton.style.cursor = 'not-allowed';
        }

        if (stepBackButton) {
            stepBackButton.disabled = true;
            stepBackButton.style.opacity = '0.5';
            stepBackButton.style.cursor = 'not-allowed';
        }

        if (stepForwardButton) {
            stepForwardButton.disabled = true;
            stepForwardButton.style.opacity = '0.5';
            stepForwardButton.style.cursor = 'not-allowed';
        }

        if (lapDropdown) {
            lapDropdown.disabled = true;
            lapDropdown.style.opacity = '0.5';
            lapDropdown.style.cursor = 'not-allowed';
        }
    }

    disableAIControls() {
        const questionInput = document.getElementById('ai-question-input');
        const sendButton = document.getElementById('ai-send-btn');

        if (questionInput) {
            questionInput.disabled = true;
            questionInput.style.opacity = '0.5';
            questionInput.style.cursor = 'not-allowed';
            questionInput.placeholder = 'Please select a car and wait for GPS trace to load...';
        }

        if (sendButton) {
            sendButton.disabled = true;
            sendButton.style.opacity = '0.5';
            sendButton.style.cursor = 'not-allowed';
        }
    }

    enableRaceTimeControls() {
        const timeSlider = document.getElementById('time-slider');
        const playPauseButton = document.getElementById('play-pause-button');
        const stepBackButton = document.getElementById('step-back-5s');
        const stepForwardButton = document.getElementById('step-forward-5s');
        const lapDropdown = document.getElementById('lap-dropdown');

        if (timeSlider) {
            timeSlider.disabled = false;
            timeSlider.style.opacity = '1';
            timeSlider.style.cursor = 'pointer';
        }

        if (playPauseButton) {
            playPauseButton.disabled = false;
            playPauseButton.style.opacity = '1';
            playPauseButton.style.cursor = 'pointer';
        }

        if (stepBackButton) {
            stepBackButton.disabled = false;
            stepBackButton.style.opacity = '1';
            stepBackButton.style.cursor = 'pointer';
        }

        if (stepForwardButton) {
            stepForwardButton.disabled = false;
            stepForwardButton.style.opacity = '1';
            stepForwardButton.style.cursor = 'pointer';
        }

        if (lapDropdown) {
            lapDropdown.disabled = false;
            lapDropdown.style.opacity = '1';
            lapDropdown.style.cursor = 'pointer';
        }
    }

    enableAIControls() {
        const questionInput = document.getElementById('ai-question-input');
        const sendButton = document.getElementById('ai-send-btn');

        if (questionInput) {
            questionInput.disabled = false;
            questionInput.style.opacity = '1';
            questionInput.style.cursor = 'text';
            questionInput.placeholder = 'Ask me about your racing performance, technique, or track position...';
        }

        // Re-enable send button based on current state
        this.updateSendButtonState();
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

    // === AI Assistant Methods ===

    setupAIAssistant() {
        console.log('🤖 Setting up AI Assistant...');

        // Auto-detect AWS region and account on initialization
        this.loadAWSRegionInfo();

        // Setup send button
        const sendButton = document.getElementById('ai-send-btn');
        if (sendButton) {
            sendButton.addEventListener('click', () => this.sendAIQuestion());
        }

        // Setup reset button
        const resetButton = document.getElementById('ai-reset-btn');
        if (resetButton) {
            resetButton.addEventListener('click', () => this.resetConversation());
        }

        // Setup copy button
        const copyButton = document.getElementById('ai-copy-btn');
        if (copyButton) {
            copyButton.addEventListener('click', () => this.copyConversation());
        }

        // Setup expand button
        const expandButton = document.getElementById('ai-expand-btn');
        if (expandButton) {
            expandButton.addEventListener('click', () => this.toggleAIExpanded());
        }

        // Setup input field
        const questionInput = document.getElementById('ai-question-input');
        if (questionInput) {
            questionInput.addEventListener('keypress', (event) => {
                if (event.key === 'Enter' && !event.shiftKey) {
                    event.preventDefault();
                    this.sendAIQuestion();
                }
            });

            questionInput.addEventListener('input', () => {
                const sendBtn = document.getElementById('ai-send-btn');
                if (sendBtn) {
                    sendBtn.disabled = !questionInput.value.trim() || this.aiMessaging;
                }
            });
        }

        // Clear any previous chat messages on page load
        this.clearChatMessages();

        // Test initial connection
        this.testAIConnection();
    }

    async loadAWSRegionInfo() {
        console.log('🌍 Loading AWS region information...');

        try {
            const response = await fetch(`${this.baseUrl}/ai/regions`);
            const result = await response.json();

            if (result.auto_detected) {
                this.aiRegion = result.auto_detected.region;
                console.log(`✅ Auto-detected AWS region: ${result.auto_detected.region_name} (${this.aiRegion})`);
                console.log(`📋 AWS Account ID: ${result.auto_detected.account_id}`);

                // Update status to show detected information
                const statusMsg = `Using ${result.auto_detected.region_name} (Account: ${result.auto_detected.account_id})`;
                this.updateAIStatus(statusMsg, result.status === 'auto_detected' ? 'connected' : 'error');
            } else {
                console.warn('⚠️ Could not auto-detect AWS region, using default');
                this.updateAIStatus('Using default region (us-west-2)', 'error');
            }
        } catch (error) {
            console.error('❌ Error loading AWS region info:', error);
            this.updateAIStatus('Region detection failed, using default', 'error');
        }
    }

    async testAIConnection() {
        console.log(`🔗 Testing AI connection to region: ${this.aiRegion}`);

        try {
            const response = await fetch(`${this.baseUrl}/ai/test-connection`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    region: this.aiRegion
                })
            });

            const result = await response.json();

            if (result.success) {
                this.aiConnected = true;
                this.updateAIStatus('Connected to Agent', 'connected');
                console.log('✅ AI connection successful:', result.message);
            } else {
                this.aiConnected = false;
                this.updateAIStatus(`Connection failed: ${result.error}`, 'error');
                console.error('❌ AI connection failed:', result.error);
            }

        } catch (error) {
            this.aiConnected = false;
            this.updateAIStatus(`Connection error: ${error.message}`, 'error');
            console.error('❌ AI connection error:', error);
        }

        this.updateAIContextInfo();
        this.updateSendButtonState();
    }

    async sendAIQuestion() {
        const questionInput = document.getElementById('ai-question-input');
        const sendButton = document.getElementById('ai-send-btn');

        if (!questionInput || !sendButton) return;

        const question = questionInput.value.trim();
        if (!question) return;

        if (!this.aiConnected) {
            this.addAIMessage('Please wait for AI connection to be established.', 'error');
            return;
        }

        if (!this.selectedCar) {
            this.addAIMessage('Please select a car first to provide telemetry context.', 'error');
            return;
        }

        // Set messaging state
        this.aiMessaging = true;
        this.updateSendButtonState();

        // Add user message to chat
        this.addAIMessage(question, 'user');

        // Clear input
        questionInput.value = '';

        // Show loading message
        const loadingMessageId = this.addAIMessage('🤔 Analyzing telemetry data...', 'assistant', true);

        try {
            console.log(`🧠 Sending AI question: "${question}"`);

            // Get current context from the interface
            const currentLap = this.getCurrentLapNumber();
            const currentPosition = this.currentPosition;
            const currentDataPoint = await this.getDataAtPosition(currentPosition);

            // Build enhanced request data with current position context
            const requestData = {
                question: question,
                race_id: this.selectedRace,
                vehicle_id: this.selectedCar,
                region: this.aiRegion,
                lap_number: currentLap,
                current_position: currentPosition,
                current_lap_distance: currentDataPoint ? currentDataPoint.lap_distance : null,
                current_telemetry: currentDataPoint ? {
                    latitude: currentDataPoint.latitude,
                    longitude: currentDataPoint.longitude,
                    speed: currentDataPoint.speed,
                    gear: currentDataPoint.gear,
                    throttle: currentDataPoint.throttle,
                    brake_rear: currentDataPoint.brake_rear,
                    brake_front: currentDataPoint.brake_front,
                    engine_rpm: currentDataPoint.engine_rpm,
                    steering_angle: currentDataPoint.steering_angle,
                    g_force_x: currentDataPoint.g_force_x,
                    g_force_y: currentDataPoint.g_force_y,
                    lap_distance: currentDataPoint.lap_distance,
                    lap: currentDataPoint.lap
                } : null
            };

            // Enhance the question with context for better agent understanding
            const contextualQuestion = `Current situation: I am in ${this.selectedRace} driving vehicle ${this.selectedCar}` +
                (currentLap ? `, currently on lap ${currentLap}` : '') +
                (currentDataPoint && currentDataPoint.lap_distance ? `, at position ${currentDataPoint.lap_distance.toFixed(0)}m into the lap` : '') +
                `. My question: ${question}`;

            // Update the question with context
            requestData.question = contextualQuestion;

            console.log(`🎯 Enhanced question with context:`, requestData);

            const response = await fetch(`${this.baseUrl}/ai/analyze`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestData)
            });

            const result = await response.json();

            // Remove loading message
            this.removeAIMessage(loadingMessageId);

            if (result.success) {
                this.addAIMessage(result.response, 'assistant');
                console.log('✅ AI analysis successful');

                // Log token usage
                if (result.metadata) {
                    console.log(`📊 Tokens used: ${result.metadata.input_tokens} in, ${result.metadata.output_tokens} out`);
                }
            } else {
                this.addAIMessage(`Analysis failed: ${result.error}`, 'error');
                console.error('❌ AI analysis failed:', result.error);
            }

        } catch (error) {
            // Remove loading message
            this.removeAIMessage(loadingMessageId);
            this.addAIMessage(`Network error: ${error.message}`, 'error');
            console.error('❌ AI request error:', error);
        }

        // Reset messaging state
        this.aiMessaging = false;
        this.updateSendButtonState();
    }

    getCurrentLapNumber() {
        // Try to get current lap from telemetry display
        const lapInfo = document.getElementById('lap-info');
        if (lapInfo && lapInfo.textContent) {
            const match = lapInfo.textContent.match(/Lap:\s*(\d+)/);
            if (match) {
                return parseInt(match[1]);
            }
        }

        // Fallback: if we have timeline data, get lap from current position
        if (this.timelineData && this.timelineData.length > 0 && this.currentPosition < this.timelineData.length) {
            return this.timelineData[this.currentPosition].lap;
        }

        return null;
    }

    updateAIStatus(message, type = 'default') {
        const connectionElement = document.getElementById('ai-connection-status');
        if (connectionElement) {
            // Remove existing status classes
            connectionElement.classList.remove('connecting', 'connected', 'error');

            // Update emoji and tooltip based on connection state
            if (type === 'connected') {
                connectionElement.textContent = '✅';
                connectionElement.title = message;
                connectionElement.classList.add('connected');
            } else if (type === 'error') {
                connectionElement.textContent = '❌';
                connectionElement.title = `Connection failed: ${message}`;
                connectionElement.classList.add('error');
            } else {
                connectionElement.textContent = '🔄';
                connectionElement.title = message;
                connectionElement.classList.add('connecting');
            }
        }
    }

    updateAIContextInfo() {
        const contextElement = document.getElementById('ai-context-info');
        if (!contextElement) return;

        let contextText = '';

        if (!this.selectedCar) {
            contextText = 'Select a car and lap to start analysis';
        } else {
            const carParts = this.selectedCar.split('-');
            const carNumber = carParts.length >= 3 ? carParts[2] : this.selectedCar;
            const currentLap = this.getCurrentLapNumber();

            contextText = `Context: Car #${carNumber}, ${this.selectedRace}`;
            if (currentLap) {
                contextText += `, Lap ${currentLap}`;
            }
        }

        contextElement.textContent = contextText;
    }

    updateSendButtonState() {
        const sendButton = document.getElementById('ai-send-btn');
        const questionInput = document.getElementById('ai-question-input');

        if (sendButton && questionInput) {
            const hasQuestion = questionInput.value.trim().length > 0;
            const canSend = this.aiConnected && hasQuestion && !this.aiMessaging;

            sendButton.disabled = !canSend;

            if (this.aiMessaging) {
                sendButton.innerHTML = '<span class="ai-loading"></span>Analyzing...';
                sendButton.classList.add('analyzing');
            } else {
                sendButton.textContent = 'Send';
                sendButton.classList.remove('analyzing');
            }
        }
    }

    addAIMessage(content, type = 'assistant', isLoading = false) {
        const messagesContainer = document.getElementById('ai-messages');
        if (!messagesContainer) return null;

        const messageDiv = document.createElement('div');
        messageDiv.className = `ai-message ${type}`;

        const messageId = `msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
        messageDiv.id = messageId;

        const timeSpan = document.createElement('div');
        timeSpan.className = 'message-time';
        timeSpan.textContent = new Date().toLocaleTimeString();

        const contentSpan = document.createElement('div');
        contentSpan.className = 'message-content';

        // Use markdown rendering for assistant messages, plain text for user messages
        if (type === 'assistant' && typeof marked !== 'undefined') {
            // Configure marked for safe rendering
            marked.setOptions({
                breaks: true,
                gfm: true,
                sanitize: false // We trust our own AI responses
            });
            contentSpan.innerHTML = marked.parse(content);
        } else {
            contentSpan.textContent = content;
        }

        messageDiv.appendChild(timeSpan);
        messageDiv.appendChild(contentSpan);

        messagesContainer.appendChild(messageDiv);

        // Scroll to bottom
        messagesContainer.scrollTop = messagesContainer.scrollHeight;

        return messageId;
    }

    removeAIMessage(messageId) {
        if (messageId) {
            const messageElement = document.getElementById(messageId);
            if (messageElement) {
                messageElement.remove();
            }
        }
    }

    clearChatMessages() {
        const messagesContainer = document.getElementById('ai-messages');
        if (messagesContainer) {
            // Clear all messages and add initial greeting with markdown support
            messagesContainer.innerHTML = '';

            const welcomeMessage = `## Welcome to your AI Racing Coach! 🏁

I can analyze your **telemetry data** and provide specific advice to improve your lap times.

### Try asking questions like:
- *"What could I have done better on this lap?"*
- *"Why was I slower in sector 2?"*
- *"Compare my braking points to optimal"*
- *"How can I improve my cornering technique?"*

**Select a car and lap, then ask me anything!**`;

            const messageDiv = document.createElement('div');
            messageDiv.className = 'ai-message assistant';

            const contentDiv = document.createElement('div');
            contentDiv.className = 'message-content';

            // Use markdown rendering for the welcome message
            if (typeof marked !== 'undefined') {
                marked.setOptions({
                    breaks: true,
                    gfm: true,
                    sanitize: false
                });
                contentDiv.innerHTML = marked.parse(welcomeMessage);
            } else {
                contentDiv.textContent = welcomeMessage;
            }

            messageDiv.appendChild(contentDiv);
            messagesContainer.appendChild(messageDiv);
        }
    }

    async resetConversation() {
        console.log('🔄 Resetting conversation and agent memory...');

        // Clear chat messages
        this.clearChatMessages();

        // Reset agent memory by creating a new agent instance on the backend
        try {
            const response = await fetch(`${this.baseUrl}/ai/reset-agent`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    race_id: this.selectedRace,
                    vehicle_id: this.selectedCar
                })
            });

            if (response.ok) {
                console.log('✅ Agent memory reset successful');
                this.addAIMessage('Conversation reset. How can I help you analyze your racing performance?', 'assistant');
            } else {
                console.warn('⚠️ Agent reset endpoint not available, cleared chat only');
                this.addAIMessage('Chat cleared. Note: Agent memory persists until page refresh.', 'assistant');
            }
        } catch (error) {
            console.warn('⚠️ Agent reset not available:', error.message);
            this.addAIMessage('Chat cleared. Note: Agent memory persists until page refresh.', 'assistant');
        }
    }

    toggleAIExpanded() {
        console.log('🔄 Toggling AI Coach expanded view...');

        const aiPanel = document.querySelector('.ai-assistant-panel');
        const expandButton = document.getElementById('ai-expand-btn');

        if (!aiPanel || !expandButton) {
            console.warn('⚠️ AI panel or expand button not found');
            return;
        }

        const isExpanded = aiPanel.classList.contains('ai-expanded');

        if (isExpanded) {
            // Collapse: Remove expanded class and show other content
            aiPanel.classList.remove('ai-expanded');
            expandButton.textContent = '⛶ Expand';
            expandButton.title = 'Expand AI coach to full screen';

            // Show hidden content
            const elementsToShow = [
                'main-title-container',
                'main-map-container',
                'main-telemetry-sidebar'
            ];

            elementsToShow.forEach(id => {
                const element = document.getElementById(id);
                if (element) {
                    element.classList.remove('content-hidden');
                }
            });

            // Also show the other controls in the left panel
            const controlPanels = document.querySelectorAll('.control-panel');
            controlPanels.forEach(panel => {
                panel.classList.remove('content-hidden');
            });

            console.log('✅ AI Coach collapsed to normal view');

        } else {
            // Expand: Add expanded class and hide other content
            aiPanel.classList.add('ai-expanded');
            expandButton.textContent = '⤚ Collapse';
            expandButton.title = 'Return to normal view';

            // Hide other content
            const elementsToHide = [
                'main-title-container',
                'main-map-container',
                'main-telemetry-sidebar'
            ];

            elementsToHide.forEach(id => {
                const element = document.getElementById(id);
                if (element) {
                    element.classList.add('content-hidden');
                }
            });

            // Also hide the other controls in the left panel
            const controlPanels = document.querySelectorAll('.control-panel');
            controlPanels.forEach(panel => {
                panel.classList.add('content-hidden');
            });

            console.log('✅ AI Coach expanded to full screen');
        }
    }

    copyConversation() {
        console.log('📋 Copying AI conversation to clipboard...');

        const messagesContainer = document.getElementById('ai-messages');
        if (!messagesContainer) {
            console.warn('⚠️ AI messages container not found');
            return;
        }

        // Extract all messages and format them as plain text
        const messages = messagesContainer.querySelectorAll('.ai-message');
        let conversationText = 'AI Racing Coach Conversation\n';
        conversationText += '=' .repeat(40) + '\n\n';

        // Add context info
        const contextElement = document.getElementById('ai-context-info');
        if (contextElement && contextElement.textContent.trim()) {
            conversationText += `${contextElement.textContent.trim()}\n`;
            conversationText += '-'.repeat(40) + '\n\n';
        }

        messages.forEach((message, index) => {
            const timeElement = message.querySelector('.message-time');
            const contentElement = message.querySelector('.message-content');

            if (contentElement) {
                // Determine message type
                const isUser = message.classList.contains('user');
                const isError = message.classList.contains('error');
                const messageType = isError ? 'ERROR' : (isUser ? 'USER' : 'AI COACH');

                // Add timestamp if available
                let timestamp = '';
                if (timeElement && timeElement.textContent.trim()) {
                    timestamp = ` (${timeElement.textContent.trim()})`;
                }

                // Add message header
                conversationText += `[${messageType}]${timestamp}:\n`;

                // Extract plain text content (remove HTML formatting)
                let messageText = contentElement.textContent || contentElement.innerText || '';

                // Clean up extra whitespace and format
                messageText = messageText.trim();
                if (messageText) {
                    // Add indentation for readability
                    const indentedText = messageText.split('\n').map(line => `  ${line}`).join('\n');
                    conversationText += `${indentedText}\n\n`;
                }
            }
        });

        // Add footer
        conversationText += '-'.repeat(40) + '\n';
        conversationText += `Exported on: ${new Date().toLocaleString()}\n`;
        conversationText += `Total Messages: ${messages.length}\n`;

        // Copy to clipboard
        const copyButton = document.getElementById('ai-copy-btn');

        if (navigator.clipboard && navigator.clipboard.writeText) {
            // Modern clipboard API
            navigator.clipboard.writeText(conversationText)
                .then(() => {
                    console.log('✅ Conversation copied to clipboard successfully');
                    this.showCopySuccess(copyButton);
                })
                .catch(err => {
                    console.error('❌ Failed to copy conversation:', err);
                    this.fallbackCopyToClipboard(conversationText, copyButton);
                });
        } else {
            // Fallback for older browsers
            this.fallbackCopyToClipboard(conversationText, copyButton);
        }
    }

    fallbackCopyToClipboard(text, button) {
        // Create a temporary textarea element
        const textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        textarea.style.pointerEvents = 'none';

        document.body.appendChild(textarea);

        try {
            textarea.select();
            textarea.setSelectionRange(0, 99999); // For mobile devices

            const successful = document.execCommand('copy');
            if (successful) {
                console.log('✅ Conversation copied to clipboard (fallback method)');
                this.showCopySuccess(button);
            } else {
                console.error('❌ Fallback copy method failed');
                this.showCopyError(button);
            }
        } catch (err) {
            console.error('❌ Fallback copy failed:', err);
            this.showCopyError(button);
        } finally {
            document.body.removeChild(textarea);
        }
    }

    showCopySuccess(button) {
        if (button) {
            const originalText = button.textContent;
            button.textContent = '✅ Copied!';
            button.classList.add('copied');

            setTimeout(() => {
                button.textContent = originalText;
                button.classList.remove('copied');
            }, 2000);
        }
    }

    showCopyError(button) {
        if (button) {
            const originalText = button.textContent;
            button.textContent = '❌ Failed';
            button.style.backgroundColor = '#dc3545';

            setTimeout(() => {
                button.textContent = originalText;
                button.style.backgroundColor = '';
            }, 2000);
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

    // Workaround: Load cars after initialization completes
    setTimeout(() => {
        if (apiTrackMapViewer && apiTrackMapViewer.loadAvailableCars) {
            console.log("🔧 Loading cars via workaround...");
            apiTrackMapViewer.loadAvailableCars();
        }
    }, 1000);
});