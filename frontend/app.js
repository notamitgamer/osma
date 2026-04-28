/**
 * OSMA v5 - Vanilla JS Frontend
 * Fetches JSONL chunks statically via GitHub Raw / Local relative paths.
 */

// If deployed elsewhere, set this to your raw GitHub path:
// const BASE_DATA_URL = 'https://raw.githubusercontent.com/username/repo/main/data';
const BASE_DATA_URL = '../data'; // Default relative for local dev

// State Management
const state = {
    ecosystem: 'npm',
    searchQuery: '',
    currentPage: 1,
    rowsPerPage: 200,
    chunkSize: 2000,
    manifests: { npm: null, pypi: null },
    indexCaches: { npm: null, pypi: null }, // Mapped index {"npm:lodash": 1}
    chunkCache: {}, // { "npm/chunk_000001_002000.jsonl": [rows...] }
    displayedData: [] // Keeps track of currently shown rows
};

// DOM Elements
const els = {
    filter: document.getElementById('ecosystemFilter'),
    search: document.getElementById('searchInput'),
    tableBody: document.getElementById('tableBody'),
    btnLoadMore: document.getElementById('btnLoadMore'),
    loader: document.getElementById('loader'),
    stats: document.getElementById('headerStats'),
    panel: document.getElementById('detailPanel'),
    overlay: document.getElementById('panelOverlay'),
    panelTitle: document.getElementById('panelTitle'),
    panelContent: document.getElementById('panelContent'),
    btnClose: document.getElementById('btnClosePanel')
};

// Initialize App
async function init() {
    setupEventListeners();
    await fetchManifests();
    await loadPage(1);
}

// ----------------- Core Data Fetching -----------------

async function fetchManifests() {
    try {
        const [npmRes, pypiRes] = await Promise.all([
            fetch(`${BASE_DATA_URL}/npm/manifest.json`).catch(()=>null),
            fetch(`${BASE_DATA_URL}/pypi/manifest.json`).catch(()=>null)
        ]);
        
        if(npmRes && npmRes.ok) state.manifests.npm = await npmRes.json();
        if(pypiRes && pypiRes.ok) state.manifests.pypi = await pypiRes.json();

        updateStatsUI();
    } catch (err) {
        console.error("Failed to load manifests", err);
    }
}

async function fetchIndexIfNeeded() {
    const eco = state.ecosystem;
    if (state.indexCaches[eco]) return; // Already cached
    
    try {
        const res = await fetch(`${BASE_DATA_URL}/${eco}/index.json`);
        if(res.ok) {
            state.indexCaches[eco] = await res.json();
        }
    } catch(err) {
        console.error(`Failed to load ${eco} index`, err);
    }
}

async function fetchChunk(eco, packageNo) {
    // Determine exact chunk filename based on package_no
    const chunkIndex = Math.floor((packageNo - 1) / state.chunkSize);
    const start = (chunkIndex * state.chunkSize) + 1;
    const end = (chunkIndex + 1) * state.chunkSize;
    
    // Format to 000001_002000
    const startStr = start.toString().padStart(6, '0');
    const endStr = end.toString().padStart(6, '0');
    const chunkFile = `chunk_${startStr}_${endStr}.jsonl`;
    
    const cacheKey = `${eco}/${chunkFile}`;
    
    if (state.chunkCache[cacheKey]) {
        return state.chunkCache[cacheKey]; // Return cached
    }

    try {
        const res = await fetch(`${BASE_DATA_URL}/${eco}/${chunkFile}`);
        if (!res.ok) throw new Error("Chunk not found");
        
        const text = await res.text();
        
        // Parse JSONL efficiently
        const rows = text.trim().split('\n')
                         .filter(line => line.trim().length > 0)
                         .map(line => JSON.parse(line));
                         
        state.chunkCache[cacheKey] = rows;
        return rows;
    } catch(err) {
        console.warn(`Chunk fetch failed: ${cacheKey}`);
        return [];
    }
}

// ----------------- Logic -----------------

async function loadPage(pageNo) {
    showLoader();
    state.currentPage = pageNo;
    const eco = state.ecosystem;
    const isSearching = state.searchQuery.trim().length > 0;
    
    if (pageNo === 1) {
        els.tableBody.innerHTML = ''; 
        state.displayedData = [];
    }

    let newRows = [];

    if (isSearching) {
        // --- Search Logic via Index ---
        await fetchIndexIfNeeded();
        const index = state.indexCaches[eco];
        if(!index) return hideLoader();

        const query = state.searchQuery.toLowerCase();
        
        // Find matching keys ("npm:lodash")
        const matchingPackageNos = Object.keys(index)
            .filter(key => key.toLowerCase().includes(query))
            .map(key => index[key])
            .sort((a,b) => a - b); // Ascending package_no
            
        // Paginate local matched array
        const startIdx = (pageNo - 1) * state.rowsPerPage;
        const endIdx = startIdx + state.rowsPerPage;
        const pagedPackageNos = matchingPackageNos.slice(startIdx, endIdx);
        
        // Determine which chunks to fetch to fulfill this page
        // We might need multiple chunks if results span across boundaries
        const chunkSet = new Set();
        pagedPackageNos.forEach(num => {
            const cIdx = Math.floor((num - 1) / state.chunkSize);
            chunkSet.add(cIdx);
        });

        // Load all required chunks
        for (let cIdx of chunkSet) {
            // just pass a packageNo that lands in that chunk to fetchChunk
            const pkgNo = (cIdx * state.chunkSize) + 1; 
            await fetchChunk(eco, pkgNo); 
        }

        // Extract exact matches from cached chunks
        pagedPackageNos.forEach(num => {
            const cIdx = Math.floor((num - 1) / state.chunkSize);
            const start = (cIdx * state.chunkSize) + 1;
            const end = (cIdx + 1) * state.chunkSize;
            const cacheKey = `${eco}/chunk_${start.toString().padStart(6,'0')}_${end.toString().padStart(6,'0')}.jsonl`;
            
            const chunkData = state.chunkCache[cacheKey];
            if(chunkData) {
                const found = chunkData.find(r => r.package_no === num);
                if(found) newRows.push(found);
            }
        });
        
        if (matchingPackageNos.length <= endIdx) {
            els.btnLoadMore.style.display = 'none';
        } else {
            els.btnLoadMore.style.display = 'inline-block';
        }

    } else {
        // --- Default List Logic (Chunk sequentially) ---
        const startPackageNo = ((pageNo - 1) * state.rowsPerPage) + 1;
        const chunkData = await fetchChunk(eco, startPackageNo);
        
        // Slice the exact rows needed from the chunk
        const internalStart = (startPackageNo - 1) % state.chunkSize;
        newRows = chunkData.slice(internalStart, internalStart + state.rowsPerPage);
        
        const manifest = state.manifests[eco];
        if (manifest && startPackageNo + state.rowsPerPage > manifest.total_packages) {
            els.btnLoadMore.style.display = 'none';
        } else {
            els.btnLoadMore.style.display = 'inline-block';
        }
    }

    state.displayedData.push(...newRows);
    renderRows(newRows);
    hideLoader();
}

// ----------------- UI Rendering -----------------

function renderRows(rows) {
    if (rows.length === 0 && state.currentPage === 1) {
        els.tableBody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding: 2rem;">No packages found.</td></tr>`;
        return;
    }

    const fragment = document.createDocumentFragment();

    rows.forEach(row => {
        const tr = document.createElement('tr');
        const dStr = new Date(row.last_updated).toLocaleDateString();
        
        tr.innerHTML = `
            <td>#${row.package_no}</td>
            <td><span class="badge ${row.ecosystem}">${row.ecosystem}</span></td>
            <td><span class="pkg-name" data-pkg="${row.package_name}" data-eco="${row.ecosystem}">${row.package_name}</span></td>
            <td>${row.version}</td>
            <td>${row.author || '-'}</td>
            <td>${dStr}</td>
            <td>
                <a href="${row.registry_url}" target="_blank" class="action-link" title="Registry">🔗</a>
                ${row.repo_url ? `<a href="${row.repo_url}" target="_blank" class="action-link" title="Repository">📁</a>` : ''}
            </td>
        `;
        fragment.appendChild(tr);
    });

    els.tableBody.appendChild(fragment);
}

function updateStatsUI() {
    const nTotal = state.manifests.npm ? state.manifests.npm.total_packages : 0;
    const pTotal = state.manifests.pypi ? state.manifests.pypi.total_packages : 0;
    els.stats.textContent = `Tracking ${nTotal.toLocaleString()} NPM & ${pTotal.toLocaleString()} PyPI packages`;
}

function showLoader() {
    els.loader.classList.remove('hidden');
    els.btnLoadMore.disabled = true;
}

function hideLoader() {
    els.loader.classList.add('hidden');
    els.btnLoadMore.disabled = false;
}

// ----------------- Detail Panel (Live API) -----------------

async function openDetails(eco, pkgName) {
    els.panelTitle.textContent = `${pkgName}`;
    els.panelContent.innerHTML = `<p style="color:#666;">Fetching live data from ${eco.toUpperCase()}...</p>`;
    
    els.panel.classList.add('open');
    els.overlay.classList.add('open');

    try {
        let html = '';
        if (eco === 'npm') {
            const res = await fetch(`https://registry.npmjs.org/${pkgName}`);
            const data = await res.json();
            html = buildDetailHTML(data.description, data['dist-tags']?.latest, data.license, data.homepage);
        } else if (eco === 'pypi') {
            const res = await fetch(`https://pypi.org/pypi/${pkgName}/json`);
            const data = await res.json();
            const info = data.info;
            html = buildDetailHTML(info.summary, info.version, info.license, info.home_page || info.project_url);
        }
        els.panelContent.innerHTML = html;
    } catch (err) {
        els.panelContent.innerHTML = `<p style="color:red;">Error loading live details from registry API.</p>`;
    }
}

function buildDetailHTML(desc, version, license, homepage) {
    return `
        <div class="detail-item"><strong>Description</strong><p>${desc || 'No description provided.'}</p></div>
        <div class="detail-item"><strong>Latest Version</strong><p>${version || '-'}</p></div>
        <div class="detail-item"><strong>License</strong><p>${license || '-'}</p></div>
        ${homepage ? `<div class="detail-item"><strong>Homepage</strong><p><a href="${homepage}" target="_blank">${homepage}</a></p></div>` : ''}
    `;
}

function closeDetails() {
    els.panel.classList.remove('open');
    els.overlay.classList.remove('open');
}

// ----------------- Event Listeners -----------------

function setupEventListeners() {
    els.btnLoadMore.addEventListener('click', () => loadPage(state.currentPage + 1));
    
    els.filter.addEventListener('change', (e) => {
        state.ecosystem = e.target.value;
        loadPage(1);
    });

    let searchTimeout;
    els.search.addEventListener('input', (e) => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            state.searchQuery = e.target.value;
            loadPage(1);
        }, 300); // Debounce search
    });

    // Delegation for package clicks
    els.tableBody.addEventListener('click', (e) => {
        if (e.target.classList.contains('pkg-name')) {
            const pkg = e.target.getAttribute('data-pkg');
            const eco = e.target.getAttribute('data-eco');
            openDetails(eco, pkg);
        }
    });

    els.btnClose.addEventListener('click', closeDetails);
    els.overlay.addEventListener('click', closeDetails);
}

// Boot
init();