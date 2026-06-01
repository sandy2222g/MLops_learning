/* ==========================================================================
   CIVIC EYE - SMART CITY FLOOD CLASSIFIER FRONTEND INTERACTIVE ENGINE
   Features: Drag & Drop Ingestion, AJAX Fetch Predictions, ChartJS Visualizations
   ========================================================================== */

document.addEventListener('DOMContentLoaded', () => {
    // ----------------------------------------------------
    // State Management
    // ----------------------------------------------------
    let activeModel = 'medium';
    let imageChart = null;
    let videoTimelineChart = null;
    let selectedImageFile = null;
    let selectedVideoFile = null;

    // Elements cache
    const modelSelector = document.getElementById('model-selector');
    const hardwareBadge = document.getElementById('hardware-badge');
    const currentTimeEl = document.getElementById('current-time');

    // ----------------------------------------------------
    // Live Clock & Hardware Status
    // ----------------------------------------------------
    function startClock() {
        setInterval(() => {
            const now = new Date();
            currentTimeEl.innerHTML = `<i class="bi bi-clock"></i> ${now.toLocaleTimeString()}`;
        }, 1000);
    }
    startClock();

    async function fetchSystemStatus() {
        try {
            const response = await fetch(`/system_status?model_type=${activeModel}`);
            const data = await response.json();
            if (data.success) {
                // Update sidebar status dot and badge
                const deviceText = data.cuda_available ? '<i class="bi bi-cpu"></i> GPU Acceleration' : '<i class="bi bi-cpu"></i> CPU (Standard)';
                hardwareBadge.innerHTML = deviceText;
                
                // Update system specs panel
                const hwEl = document.getElementById('system-hardware');
                const cudaEl = document.getElementById('system-cuda');
                const modelTypeEl = document.getElementById('system-model-type');
                const weightSizeEl = document.getElementById('system-weight-size');
                
                if (hwEl) hwEl.innerText = data.hardware;
                if (cudaEl) cudaEl.innerText = data.cuda_available ? 'CUDA Cores Activated' : 'Driver not detected (using CPU)';
                if (modelTypeEl) modelTypeEl.innerText = data.model_type === 'medium' ? 'Standard (YOLO11m-cls)' : 'Fast/Nano (YOLO11n-cls)';
                if (weightSizeEl) weightSizeEl.innerText = `${data.weights_size_mb} MB`;
            }
        } catch (err) {
            console.error("Error retrieving system status: ", err);
        }
    }
    fetchSystemStatus();

    modelSelector.addEventListener('change', (e) => {
        activeModel = e.target.value;
        fetchSystemStatus();
    });

    // ----------------------------------------------------
    // Sidebar Tab Navigation
    // ----------------------------------------------------
    const navItems = document.querySelectorAll('.nav-item');
    const tabPanels = document.querySelectorAll('.tab-panel');
    const pageTitle = document.getElementById('page-title');
    const pageSubtitle = document.getElementById('page-subtitle');

    const tabMetadata = {
        'image-tab': {
            title: 'Image Diagnostic Terminal',
            subtitle: 'Process smart city imagery to classify real-time flood levels.'
        },
        'video-tab': {
            title: 'Video Surveillance Analyser',
            subtitle: 'Analyze CCTV video streams frame-by-frame for flood level transitions.'
        },
        'history-tab': {
            title: 'Civic Ingestion Logs Registry',
            subtitle: 'Historical registry of all classified assets and system verdicts.'
        },
        'system-tab': {
            title: 'System Analytics & Resources',
            subtitle: 'Hardware allocation parameters and model details.'
        }
    };

    navItems.forEach(item => {
        item.addEventListener('click', () => {
            const targetTab = item.getAttribute('data-tab');
            
            // Toggle active classes
            navItems.forEach(n => n.classList.remove('active'));
            item.classList.add('active');

            tabPanels.forEach(panel => {
                if (panel.id === targetTab) {
                    panel.classList.add('active');
                } else {
                    panel.classList.remove('active');
                }
            });

            // Update Titles
            const meta = tabMetadata[targetTab];
            if (meta) {
                pageTitle.innerText = meta.title;
                pageSubtitle.innerText = meta.subtitle;
            }

            // If log tab is selected, trigger load
            if (targetTab === 'history-tab') {
                fetchLogs();
            }
        });
    });

    // ----------------------------------------------------
    // Image Upload & Analysis Setup
    // ----------------------------------------------------
    const imageDropZone = document.getElementById('image-drop-zone');
    const imageInput = document.getElementById('image-input');
    const imagePreview = document.getElementById('image-preview');
    const removeImageBtn = document.getElementById('remove-image-btn');
    const clearImageBtn = document.getElementById('clear-image-btn');
    const analyzeImageBtn = document.getElementById('analyze-image-btn');
    const imageResultCard = document.getElementById('image-result-card');
    const imageResultPlaceholder = document.getElementById('image-result-placeholder');
    const imageResultContent = document.getElementById('image-result-content');

    // Click triggers browsing
    imageDropZone.addEventListener('click', (e) => {
        if (e.target.closest('.remove-preview-btn') || selectedImageFile) return;
        imageInput.click();
    });

    imageInput.addEventListener('change', () => {
        if (imageInput.files.length > 0) {
            handleImageSelection(imageInput.files[0]);
        }
    });

    // Drag-over styling
    imageDropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        imageDropZone.classList.add('hovering');
    });

    imageDropZone.addEventListener('dragleave', () => {
        imageDropZone.classList.remove('hovering');
    });

    imageDropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        imageDropZone.classList.remove('hovering');
        if (e.dataTransfer.files.length > 0) {
            handleImageSelection(e.dataTransfer.files[0]);
        }
    });

    function handleImageSelection(file) {
        if (!file.type.startsWith('image/')) {
            alert('File type must be an image!');
            return;
        }
        selectedImageFile = file;
        const reader = new FileReader();
        reader.onload = (e) => {
            imagePreview.src = e.target.result;
            imageDropZone.querySelector('.drop-zone-prompt').style.display = 'none';
            imageDropZone.querySelector('.preview-container').style.display = 'flex';
            
            // Enable controls
            clearImageBtn.disabled = false;
            analyzeImageBtn.disabled = false;
        };
        reader.readAsDataURL(file);
    }

    function resetImageUpload() {
        selectedImageFile = null;
        imageInput.value = '';
        imagePreview.src = '#';
        imageDropZone.querySelector('.drop-zone-prompt').style.display = 'flex';
        imageDropZone.querySelector('.preview-container').style.display = 'none';
        
        clearImageBtn.disabled = true;
        analyzeImageBtn.disabled = true;
        
        // Clear result UI
        imageResultCard.style.opacity = '0.5';
        imageResultCard.style.pointerEvents = 'none';
        imageResultPlaceholder.style.display = 'flex';
        imageResultContent.style.display = 'none';
    }

    removeImageBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        resetImageUpload();
    });

    clearImageBtn.addEventListener('click', resetImageUpload);

    // Image API execution
    analyzeImageBtn.addEventListener('click', async () => {
        if (!selectedImageFile) return;
        
        // Show spinner state on button
        const btnText = analyzeImageBtn.querySelector('.btn-text');
        const btnSpinner = analyzeImageBtn.querySelector('.btn-spinner');
        btnText.style.display = 'none';
        btnSpinner.style.display = 'block';
        analyzeImageBtn.disabled = true;
        clearImageBtn.disabled = true;

        const formData = new FormData();
        formData.append('file', selectedImageFile);
        formData.append('model_type', activeModel);

        try {
            const response = await fetch('/predict', {
                method: 'POST',
                body: formData
            });
            const data = await response.json();
            
            if (data.success) {
                renderImageResult(data);
            } else {
                alert(`Error: ${data.error}`);
            }
        } catch (err) {
            console.error(err);
            alert('A network error occurred processing this image.');
        } finally {
            btnText.style.display = 'block';
            btnSpinner.style.display = 'none';
            analyzeImageBtn.disabled = false;
            clearImageBtn.disabled = false;
        }
    });

    function renderImageResult(data) {
        // Show results
        imageResultCard.style.opacity = '1';
        imageResultCard.style.pointerEvents = 'all';
        imageResultPlaceholder.style.display = 'none';
        imageResultContent.style.display = 'flex';

        // Update hazard badge
        const badge = document.getElementById('image-hazard-badge');
        const badgeStatus = document.getElementById('image-status-text');
        const badgeConf = document.getElementById('image-confidence-text');
        const statusIcon = document.getElementById('image-status-icon');

        // Reset classes
        badge.className = 'hazard-level-badge';
        statusIcon.className = 'bi';

        if (data.result === 'danger') {
            badge.classList.add('status-danger');
            badgeStatus.innerText = 'Danger';
            statusIcon.classList.add('bi-exclamation-octagon');
        } else if (data.result === 'warning') {
            badge.classList.add('status-warning');
            badgeStatus.innerText = 'Warning';
            statusIcon.classList.add('bi-exclamation-triangle');
        } else {
            badge.classList.add('status-safe');
            badgeStatus.innerText = 'Safe';
            statusIcon.classList.add('bi-shield-check');
        }

        badgeConf.innerText = `${(data.confidence * 100).toFixed(1)}%`;

        // Update probability progress bars
        const dangerProb = (data.probabilities.danger * 100);
        const warningProb = (data.probabilities.warning * 100);
        const safeProb = (data.probabilities.safe * 100);

        document.getElementById('prob-val-danger').innerText = `${dangerProb.toFixed(1)}%`;
        document.getElementById('bar-danger').style.width = `${dangerProb}%`;

        document.getElementById('prob-val-warning').innerText = `${warningProb.toFixed(1)}%`;
        document.getElementById('bar-warning').style.width = `${warningProb}%`;

        document.getElementById('prob-val-safe').innerText = `${safeProb.toFixed(1)}%`;
        document.getElementById('bar-safe').style.width = `${safeProb}%`;

        // Update protocols list
        const protocolCard = document.getElementById('image-protocol-card');
        const protocolDesc = document.getElementById('image-protocol-desc');
        const protocolList = document.getElementById('image-protocol-list');

        protocolCard.className = `protocol-card protocol-${data.result}`;
        protocolDesc.innerText = data.recommendations.desc;
        protocolList.innerHTML = data.recommendations.actions.map(action => `<li>${action}</li>`).join('');

        // Metadata
        document.getElementById('image-latency-text').innerText = `${data.inference_ms} ms`;
        document.getElementById('image-model-used').innerText = activeModel === 'medium' ? 'Standard (20.8MB)' : 'Fast/Nano (5.2MB)';

        // Instantiates/Updates dynamic ChartJS Doughnut Chart
        renderDoughnutChart([dangerProb, warningProb, safeProb]);
    }

    function renderDoughnutChart(probabilities) {
        const ctx = document.getElementById('image-chart').getContext('2d');
        
        if (imageChart) {
            imageChart.destroy();
        }

        imageChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Danger', 'Warning', 'Safe'],
                datasets: [{
                    data: probabilities,
                    backgroundColor: ['#ef4444', '#f59e0b', '#10b981'],
                    borderColor: 'rgba(11, 15, 25, 0.9)',
                    borderWidth: 2,
                    hoverOffset: 4
                }]
            },
            options: {
                plugins: {
                    legend: { display: false }
                },
                cutout: '70%',
                responsive: true,
                maintainAspectRatio: false
            }
        });
    }

    // ----------------------------------------------------
    // Video Upload & Ingestion Setup
    // ----------------------------------------------------
    const videoDropZone = document.getElementById('video-drop-zone');
    const videoInput = document.getElementById('video-input');
    const videoPreview = document.getElementById('video-preview');
    const removeVideoBtn = document.getElementById('remove-video-btn');
    const clearVideoBtn = document.getElementById('clear-video-btn');
    const analyzeVideoBtn = document.getElementById('analyze-video-btn');
    const videoResultCard = document.getElementById('video-result-card');
    const videoResultPlaceholder = document.getElementById('video-result-placeholder');
    const videoResultContent = document.getElementById('video-result-content');

    videoDropZone.addEventListener('click', (e) => {
        if (e.target.closest('.remove-preview-btn') || selectedVideoFile) return;
        videoInput.click();
    });

    videoInput.addEventListener('change', () => {
        if (videoInput.files.length > 0) {
            handleVideoSelection(videoInput.files[0]);
        }
    });

    videoDropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        videoDropZone.classList.add('hovering');
    });

    videoDropZone.addEventListener('dragleave', () => {
        videoDropZone.classList.remove('hovering');
    });

    videoDropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        videoDropZone.classList.remove('hovering');
        if (e.dataTransfer.files.length > 0) {
            handleVideoSelection(e.dataTransfer.files[0]);
        }
    });

    function handleVideoSelection(file) {
        if (!file.type.startsWith('video/')) {
            alert('File type must be a video!');
            return;
        }
        selectedVideoFile = file;
        const fileUrl = URL.createObjectURL(file);
        videoPreview.src = fileUrl;
        videoDropZone.querySelector('.drop-zone-prompt').style.display = 'none';
        videoDropZone.querySelector('.preview-container').style.display = 'flex';
        
        clearVideoBtn.disabled = false;
        analyzeVideoBtn.disabled = false;
    }

    function resetVideoUpload() {
        selectedVideoFile = null;
        videoInput.value = '';
        videoPreview.src = '';
        videoDropZone.querySelector('.drop-zone-prompt').style.display = 'flex';
        videoDropZone.querySelector('.preview-container').style.display = 'none';
        
        clearVideoBtn.disabled = true;
        analyzeVideoBtn.disabled = true;
        
        videoResultCard.style.opacity = '0.5';
        videoResultCard.style.pointerEvents = 'none';
        videoResultPlaceholder.style.display = 'flex';
        videoResultContent.style.display = 'none';
    }

    removeVideoBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        resetVideoUpload();
    });

    clearVideoBtn.addEventListener('click', resetVideoUpload);

    analyzeVideoBtn.addEventListener('click', async () => {
        if (!selectedVideoFile) return;

        const btnText = analyzeVideoBtn.querySelector('.btn-text');
        const btnSpinner = analyzeVideoBtn.querySelector('.btn-spinner');
        btnText.style.display = 'none';
        btnSpinner.style.display = 'block';
        analyzeVideoBtn.disabled = true;
        clearVideoBtn.disabled = true;

        const formData = new FormData();
        formData.append('file', selectedVideoFile);
        formData.append('model_type', activeModel);

        try {
            const response = await fetch('/predict_video', {
                method: 'POST',
                body: formData
            });
            const data = await response.json();
            
            if (data.success) {
                renderVideoResult(data);
            } else {
                alert(`Error: ${data.error}`);
            }
        } catch (err) {
            console.error(err);
            alert('A network error occurred processing this video feed.');
        } finally {
            btnText.style.display = 'block';
            btnSpinner.style.display = 'none';
            analyzeVideoBtn.disabled = false;
            clearVideoBtn.disabled = false;
        }
    });

    function renderVideoResult(data) {
        videoResultCard.style.opacity = '1';
        videoResultCard.style.pointerEvents = 'all';
        videoResultPlaceholder.style.display = 'none';
        videoResultContent.style.display = 'flex';

        // Update overall hazard badge
        const badge = document.getElementById('video-hazard-badge');
        const badgeStatus = document.getElementById('video-status-text');
        const statusIcon = document.getElementById('video-status-icon');

        badge.className = 'hazard-level-badge';
        statusIcon.className = 'bi';

        if (data.result === 'danger') {
            badge.classList.add('status-danger');
            badgeStatus.innerText = 'Danger';
            statusIcon.classList.add('bi-exclamation-octagon');
        } else if (data.result === 'warning') {
            badge.classList.add('status-warning');
            badgeStatus.innerText = 'Warning';
            statusIcon.classList.add('bi-exclamation-triangle');
        } else {
            badge.classList.add('status-safe');
            badgeStatus.innerText = 'Safe';
            statusIcon.classList.add('bi-shield-check');
        }

        // Timeline variables
        const timeline = data.timeline;
        const labels = timeline.map(t => `${t.time}s`);
        
        // Map Safe to 1, Warning to 2, Danger to 3
        const valueMapping = { 'safe': 1, 'warning': 2, 'danger': 3 };
        const dataValues = timeline.map(t => valueMapping[t.class]);

        // Build Line Chart
        renderLineChart(labels, dataValues);

        // Build Transitions Event Log
        const logContainer = document.getElementById('video-transitions-log');
        logContainer.innerHTML = '';

        let lastClass = null;
        timeline.forEach(t => {
            // Plot all frames, highlighting state changes or significant alarms
            if (t.class !== lastClass) {
                const item = document.createElement('div');
                item.className = 'transition-item';
                
                item.innerHTML = `
                    <span class="transition-time">${t.time}s</span>
                    <span>State Transition to:</span>
                    <span class="transition-badge badge-${t.class}">${t.class}</span>
                    <span class="transition-conf">(${(t.confidence * 100).toFixed(1)}%)</span>
                `;
                logContainer.appendChild(item);
                lastClass = t.class;
            }
        });

        // If no transition logged (e.g. static safe state)
        if (logContainer.children.length === 0 && timeline.length > 0) {
            const first = timeline[0];
            const item = document.createElement('div');
            item.className = 'transition-item';
            item.innerHTML = `
                <span class="transition-time">0s - End</span>
                <span>Maintained Stable State:</span>
                <span class="transition-badge badge-${first.class}">${first.class}</span>
                <span class="transition-conf">(${(first.confidence * 100).toFixed(1)}%)</span>
            `;
            logContainer.appendChild(item);
        }

        // Stats Footer
        document.getElementById('video-latency-text').innerText = `${data.inference_ms} ms`;
        document.getElementById('video-frames-text').innerText = `${data.processed_frames}/${data.total_frames}`;
    }

    function renderLineChart(labels, values) {
        const ctx = document.getElementById('video-timeline-chart').getContext('2d');
        if (videoTimelineChart) {
            videoTimelineChart.destroy();
        }

        // Create elegant color gradient for the line
        const gradient = ctx.createLinearGradient(0, 0, 0, 180);
        gradient.addColorStop(0, 'rgba(6, 182, 212, 0.45)');
        gradient.addColorStop(1, 'rgba(6, 182, 212, 0.01)');

        videoTimelineChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Flood Hazard State',
                    data: values,
                    borderColor: '#06b6d4',
                    borderWidth: 3,
                    fill: true,
                    backgroundColor: gradient,
                    tension: 0.35,
                    pointBackgroundColor: '#06b6d4',
                    pointHoverRadius: 6
                }]
            },
            options: {
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    x: {
                        grid: { display: false },
                        ticks: { color: '#6b7280', font: { size: 10 } }
                    },
                    y: {
                        min: 0.8,
                        max: 3.2,
                        grid: { color: 'rgba(255, 255, 255, 0.04)' },
                        ticks: {
                            color: '#9ca3af',
                            font: { size: 11, weight: '600' },
                            stepSize: 1,
                            callback: function(value) {
                                if (value === 1) return 'Safe';
                                if (value === 2) return 'Warning';
                                if (value === 3) return 'Danger';
                                return '';
                            }
                        }
                    }
                },
                responsive: true,
                maintainAspectRatio: false
            }
        });
    }

    // ----------------------------------------------------
    // Diagnostic Logs Registry Loading
    // ----------------------------------------------------
    const historyTableBody = document.getElementById('history-table-body');
    const refreshHistoryBtn = document.getElementById('refresh-history-btn');

    async function fetchLogs() {
        historyTableBody.innerHTML = `<tr><td colspan="9" class="table-empty-row"><div class="btn-spinner" style="margin: 0 auto;"></div></td></tr>`;
        
        try {
            const response = await fetch('/history');
            const data = await response.json();
            
            if (data.success && data.history.length > 0) {
                historyTableBody.innerHTML = '';
                data.history.forEach(log => {
                    const row = document.createElement('tr');
                    
                    row.innerHTML = `
                        <td>#${log.id}</td>
                        <td style="color: var(--text-secondary); font-size: 12.5px;">${log.timestamp}</td>
                        <td style="font-weight: 600;">${log.filename}</td>
                        <td style="text-transform: capitalize; font-size: 12.5px;">${log.type}</td>
                        <td style="font-size: 12.5px;">${log.model_used === 'medium' ? 'Standard (Medium)' : 'Fast (Nano)'}</td>
                        <td><span class="table-badge badge-${log.result}">${log.result}</span></td>
                        <td style="font-family: monospace; font-weight: 700;">${(log.confidence * 100).toFixed(1)}%</td>
                        <td style="color: var(--text-muted); font-size: 12.5px;">${log.inference_ms.toFixed(1)}ms</td>
                        <td>
                            <button class="table-action-btn view-asset-btn" data-url="${log.file_url}" data-type="${log.type}">
                                <i class="bi bi-eye-fill"></i>
                            </button>
                        </td>
                    `;
                    historyTableBody.appendChild(row);
                });
                
                // Add modal button listeners
                document.querySelectorAll('.view-asset-btn').forEach(btn => {
                    btn.addEventListener('click', (e) => {
                        const url = btn.getAttribute('data-url');
                        const type = btn.getAttribute('data-type');
                        openModal(url, type);
                    });
                });
                
            } else {
                historyTableBody.innerHTML = `<tr><td colspan="9" class="table-empty-row">No diagnostic records found.</td></tr>`;
            }
        } catch (err) {
            console.error(err);
            historyTableBody.innerHTML = `<tr><td colspan="9" class="table-empty-row" style="color: #ef4444;">Failed to fetch database records.</td></tr>`;
        }
    }

    if (refreshHistoryBtn) {
        refreshHistoryBtn.addEventListener('click', fetchLogs);
    }

    // ----------------------------------------------------
    // Image / Video Modal Registry Popup
    // ----------------------------------------------------
    const modal = document.getElementById('image-modal');
    const modalImgPreview = document.getElementById('modal-img-preview');
    const modalVideoPreview = document.getElementById('modal-video-preview');
    const closeModalBtn = document.getElementById('close-modal-btn');

    function openModal(url, type) {
        modal.classList.add('active');
        if (type === 'image') {
            modalImgPreview.src = url;
            modalImgPreview.style.display = 'block';
            modalVideoPreview.style.display = 'none';
            modalVideoPreview.src = '';
        } else {
            modalVideoPreview.src = url;
            modalVideoPreview.style.display = 'block';
            modalImgPreview.style.display = 'none';
            modalImgPreview.src = '';
        }
    }

    function closeModal() {
        modal.classList.remove('active');
        modalImgPreview.src = '';
        modalVideoPreview.src = '';
    }

    if (closeModalBtn) {
        closeModalBtn.addEventListener('click', closeModal);
    }

    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            closeModal();
        }
    });

    // Close on ESC
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && modal.classList.contains('active')) {
            closeModal();
        }
    });
});
