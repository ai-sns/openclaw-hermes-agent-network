
    // status indicator

    class StatusIndicator {
        constructor() {
            this.element = document.querySelector('.status-indicator');
            this.textElement = this.element.querySelector('.status-text');
            this.indicatorElement = this.element.querySelector('.activity-indicator');
            this.visibilityTimeout = null;
            this.currentState = '';
            this._modelReady = false;  // true once person_me model positioned
            this._bubbleHidden = false; // true while chat bubble is open

            // Predefine HTML templates for all states
            this.stateTemplates = {
                thinking: `
                        <div class="dots-container">
                            <div class="dot"></div>
                            <div class="dot"></div>
                            <div class="dot"></div>
                        </div>
                    `,
                talking: `
                        <div class="voice-bars">
                            <div class="bar"></div>
                            <div class="bar"></div>
                            <div class="bar"></div>
                            <div class="bar"></div>
                        </div>
                    `,
                moving: `
                        <div class="arrow-container">
                            <div class="arrow"></div>
                            <div class="arrow"></div>
                        </div>
                    `,
                'using-tool': `
                        <div class="tool-icon"></div>
                    `,
                idle: `
                        <div class="idle-dot"></div>
		<div class="idle-dot"></div>
		<div class="idle-dot"></div>
                    `,
                watching: `
                        <div class="eyes-container">
                            <div class="eye left"></div>
                            <div class="eye right"></div>
                        </div>
                    `
            };
        }

        /**
         * Show the status indicator
         * @param {string} state - state type (thinking|talking|moving|using-tool|idle|watching)
         * @param {string} [customText] - optional custom text
         */
        show(state = 'thinking', customText) {
            if (this.currentState === state) return;

            clearTimeout(this.visibilityTimeout);

            // Remove all state classes
            this.indicatorElement.className = 'activity-indicator';
            this.indicatorElement.classList.add(state);
            this.currentState = state;

            // Set state content and animation
            this.indicatorElement.innerHTML = this.stateTemplates[state] || this.stateTemplates.thinking;


            // Set state text
            const stateTexts = {
                'thinking': 'Thinking',
                'talking': 'Talking',
                'moving': 'Moving',
                'using-tool': 'Using Tool',
                'idle': 'Idle',
                'watching': 'Watching'
            };
            this.textElement.textContent = customText || stateTexts[state] || 'Thinking';

            this.element.classList.add('visible');
        }

        /**
         * Hide the status indicator
         * @param {number} [delay=300] - hide delay (ms)
         */
        hide(delay = 300) {
            this.element.classList.remove('visible');
            this.visibilityTimeout = setTimeout(() => {
                this.textElement.textContent = '';
                this.currentState = '';
            }, delay);
        }

        setVisible(flag) {
            if (flag) {
                this.element.style.display = "block";
            }else
            {
                this.element.style.display = "none";
            }
        }

        /**
         * Call when a chat bubble opens/closes to suppress indicator.
         * @param {boolean} hidden - true to hide (bubble open), false to restore (bubble closed)
         */
        setBubbleHidden(hidden) {
            this._bubbleHidden = hidden;
            if (hidden) {
                this.element.classList.remove('visible');
            } else if (this._modelReady && this.currentState) {
                this.element.classList.add('visible');
            }
        }

        /**
         * Update status indicator position to anchor above person_me 3D model head.
         * Should be called every frame from the animate loop.
         * Supports both Baidu (mapvgl.ThreeLayer, Z-up) and Google (ThreeJSOverlayView, Y-up).
         */
        updatePosition() {
            // Require nation_id_me and model_loaded_list to be available
            if (typeof nation_id_me === 'undefined' || !nation_id_me ||
                typeof model_loaded_list === 'undefined' || !model_loaded_list ||
                !model_loaded_list[nation_id_me]) {
                return;
            }

            const personModel = model_loaded_list[nation_id_me];

            // Determine map type and get camera / canvas dimensions
            let activeCamera = null;
            let canvasWidth = 0;
            let canvasHeight = 0;
            let offsetLeft = 0;
            let offsetTop = 0;
            const isBaidu = (typeof map_type !== 'undefined' && map_type === 'baidu');

            if (isBaidu) {
                // Baidu: camera from threeLayer, canvas from renderer
                if (typeof threeLayer !== 'undefined' && threeLayer && threeLayer.camera) {
                    activeCamera = threeLayer.camera;
                }
                if (typeof renderer !== 'undefined' && renderer && renderer.domElement) {
                    canvasWidth = renderer.domElement.clientWidth;
                    canvasHeight = renderer.domElement.clientHeight;
                }
            } else {
                // Google: camera from overlay
                if (typeof overlay !== 'undefined' && overlay) {
                    const candidates = [
                        overlay.camera,
                        overlay._camera,
                        overlay.three && overlay.three.camera,
                        overlay.renderer && overlay.renderer.camera,
                        overlay.scene && overlay.scene.camera
                    ];
                    for (const c of candidates) {
                        if (c && typeof c === 'object' &&
                            (c.isCamera || (c.type && String(c.type).toLowerCase().includes('camera')))) {
                            activeCamera = c;
                            break;
                        }
                    }
                    if (!activeCamera && typeof overlay.getCamera === 'function') {
                        const c = overlay.getCamera();
                        if (c && (c.isCamera || (c.type && String(c.type).toLowerCase().includes('camera')))) {
                            activeCamera = c;
                        }
                    }
                }
                // Canvas dimensions from map div
                if (typeof map !== 'undefined' && map && typeof map.getDiv === 'function') {
                    const mapDiv = map.getDiv();
                    if (mapDiv) {
                        const mapRect = mapDiv.getBoundingClientRect();
                        canvasWidth = mapRect.width;
                        canvasHeight = mapRect.height;
                        offsetLeft = mapRect.left;
                        offsetTop = mapRect.top;
                    }
                }
            }

            if (!activeCamera || !canvasWidth || !canvasHeight) {
                return;
            }

            // Do not update position while suppressed by chat bubble
            if (this._bubbleHidden) return;

            try {
                // Compute bounding box of person model
                const box = new THREE.Box3().setFromObject(personModel);
                if (!box || (typeof box.isEmpty === 'function' && box.isEmpty())) {
                    return;
                }

                const center = box.getCenter(new THREE.Vector3());

                // Head position: pick the topmost point for each map type
                let headPos;
                if (isBaidu) {
                    // In Baidu ThreeLayer the camera tilt makes Y (Mercator lat)
                    // the dominant screen-up axis, matching the building overlay
                    // pattern which uses box.max.y. Combine with box.max.z for
                    // full altitude so the anchor floats above the model head.
                    headPos = new THREE.Vector3(center.x, box.max.y, box.max.z);
                } else {
                    headPos = new THREE.Vector3(center.x, box.max.y, center.z);
                }

                // Project 3D world position to NDC
                const projected = headPos.clone().project(activeCamera);

                // Behind camera check
                if (projected.z >= 1) {
                    this.element.style.left = '-9999px';
                    this.element.style.top = '-9999px';
                    return;
                }

                // Convert NDC to screen pixels
                const screenX = (projected.x * 0.5 + 0.5) * canvasWidth + offsetLeft;
                const screenY = (-projected.y * 0.5 + 0.5) * canvasHeight + offsetTop;

                // Get element dimensions (cache to avoid layout thrashing)
                if (!this._cachedElSize || this._cachedElSizeFrame !== (window.__statusIndicatorFrame || 0)) {
                    const rect = this.element.getBoundingClientRect();
                    this._cachedElSize = {
                        w: rect.width || 100,
                        h: rect.height || 30
                    };
                    this._cachedElSizeFrame = window.__statusIndicatorFrame || 0;
                }

                const elW = this._cachedElSize.w;
                const elH = this._cachedElSize.h;
                const verticalGap = 12; // pixels above head

                // Position indicator centered horizontally, above the head
                this.element.style.left = `${screenX - elW / 2}px`;
                this.element.style.top = `${screenY - elH - verticalGap}px`;

                // Auto-show on first successful positioning
                if (!this._modelReady) {
                    this._modelReady = true;
                    if (this.currentState) {
                        this.element.classList.add('visible');
                    }
                }
            } catch (e) {
                // Silently ignore projection errors
            }
        }
    }

    // Create instance (starts hidden; auto-shows when person_me model is positioned)
    const aimodel_status = new StatusIndicator();
    aimodel_status.show('idle');
    // Keep indicator hidden until model is ready and positioned
    aimodel_status.element.classList.remove('visible');


    // // Test all states - switch every 2 seconds
    // const states = ['thinking', 'talking', 'moving', 'using-tool', 'idle', 'watching'];
    // let currentIndex = 0;
    //
    // setInterval(() => {
    //     currentIndex = (currentIndex + 1) % states.length;
    //     status.show(states[currentIndex]);
    // }, 2000);
