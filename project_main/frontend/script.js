const API_URL = 'http://localhost:8000';
let selectedResumes = new Set();

// Utility functions
const showLoading = () => {
    document.getElementById('loadingOverlay').style.display = 'flex';
};

const hideLoading = () => {
    document.getElementById('loadingOverlay').style.display = 'none';
};

const formatTimestamp = (timestamp) => {
    return new Date(timestamp).toLocaleString();
};

// File handling
document.getElementById('resumeUpload').addEventListener('change', (e) => {
    const files = Array.from(e.target.files);
    const selectedFilesDiv = document.getElementById('selectedFiles');
    selectedFilesDiv.innerHTML = files.map(file => `<div>${file.name}</div>`).join('');
});

document.getElementById('jdFileUpload').addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (file) {
        const text = await file.text();
        document.getElementById('jdText').value = text;
        document.getElementById('jdName').value = file.name.replace('.txt', '');
    }
});

// JD Management
const loadSavedJDs = async () => {
    try {
        const response = await fetch(`${API_URL}/jds`);
        const jds = await response.json();
        const select = document.getElementById('savedJds');
        select.innerHTML = '<option value="">Select a JD...</option>' +
            jds.map(jd => `<option value="${jd.name}">${jd.name}</option>`).join('');
    } catch (error) {
        console.error('Error loading JDs:', error);
    }
};

document.getElementById('deleteJd').addEventListener('click', async () => {
    const select = document.getElementById('savedJds');
    const selectedJd = select.value;
    if (!selectedJd) return;

    if (!confirm(`Are you sure you want to delete "${selectedJd}"?`)) return;

    try {
        showLoading();
        await fetch(`${API_URL}/jds/${selectedJd}`, { method: 'DELETE' });
        await loadSavedJDs();
        alert('Job description deleted successfully');
    } catch (error) {
        console.error('Error deleting JD:', error);
        alert('Error deleting job description');
    } finally {
        hideLoading();
    }
});

// Analysis
document.getElementById('analyzeBtn').addEventListener('click', async () => {
    const resumes = document.getElementById('resumeUpload').files;
    const jdText = document.getElementById('jdText').value;
    const jdName = document.getElementById('jdName').value;
    const selectedJd = document.getElementById('savedJds').value;

    if (!resumes.length) {
        alert('Please select at least one resume');
        return;
    }

    if (!selectedJd && (!jdText || !jdName)) {
        alert('Please either select a saved JD or provide both JD text and name');
        return;
    }

    const formData = new FormData();
    Array.from(resumes).forEach(file => {
        formData.append('resumes', file);
    });

    if (selectedJd) {
        formData.append('jd_name', selectedJd);
    } else {
        // Save new JD first
        try {
            showLoading();
            const jdFormData = new FormData();
            jdFormData.append('jd_text', jdText);
            jdFormData.append('jd_name', jdName);
            const uploadResponse = await fetch(`${API_URL}/upload-jd`, {
                method: 'POST',
                body: jdFormData
            });
            
            if (!uploadResponse.ok) {
                const errorData = await uploadResponse.json();
                throw new Error(errorData.detail || 'Failed to save job description');
            }
            
            await loadSavedJDs();
            formData.append('jd_name', jdName);
        } catch (error) {
            console.error('Error saving JD:', error);
            alert('Error saving job description: ' + error.message);
            hideLoading();
            return;
        }
    }

    try {
        const response = await fetch(`${API_URL}/analyze`, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to analyze resumes');
        }
        
        const results = await response.json();
        displayResults(results);
    } catch (error) {
        console.error('Error analyzing resumes:', error);
        alert('Error analyzing resumes: ' + error.message);
    } finally {
        hideLoading();
    }
});

// Results display
const displayResults = (results) => {
    const tbody = document.querySelector('#resultsTable tbody');
    tbody.innerHTML = results.map(result => `
        <tr>
            <td>${result.resume_name}</td>
            <td>${result.email}</td>
            <td>${result.score.toFixed(2)}</td>
            <td>${formatTimestamp(result.timestamp)}</td>
            <td>
                <input type="checkbox" class="resume-select" value="${result.resume_name}">
            </td>
        </tr>
    `).join('');

    // Add event listeners to checkboxes
    document.querySelectorAll('.resume-select').forEach(checkbox => {
        checkbox.addEventListener('change', (e) => {
            if (e.target.checked) {
                selectedResumes.add(e.target.value);
            } else {
                selectedResumes.delete(e.target.value);
            }
        });
    });
};

// Summaries
document.getElementById('summarizeSelected').addEventListener('click', async () => {
    if (selectedResumes.size === 0) {
        alert('Please select at least one resume to summarize');
        return;
    }

    const selectedJd = document.getElementById('savedJds').value;
    if (!selectedJd) {
        alert('Please select a job description');
        return;
    }

    try {
        showLoading();
        const formData = new FormData();
        formData.append('jd_name', selectedJd);
        Array.from(selectedResumes).forEach(resume => {
            formData.append('resume_names', resume);
        });

        const response = await fetch(`${API_URL}/summarize`, {
            method: 'POST',
            body: formData
        });
        const summaries = await response.json();
        displaySummaries(summaries);
    } catch (error) {
        console.error('Error generating summaries:', error);
        alert('Error generating summaries');
    } finally {
        hideLoading();
    }
});

const displaySummaries = (summaries) => {
    const summaryResults = document.getElementById('summaryResults');
    summaryResults.innerHTML = summaries.map(summary => `
        <div class="summary-card">
            <h3>${summary.resume_name}</h3>
            <pre>${summary.summary}</pre>
        </div>
    `).join('');
};

// Export
document.getElementById('exportBtn').addEventListener('click', async () => {
    try {
        showLoading();
        const response = await fetch(`${API_URL}/export-scores`);
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'resume_scores.csv';
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
    } catch (error) {
        console.error('Error exporting scores:', error);
        alert('Error exporting scores');
    } finally {
        hideLoading();
    }
});

// Initial load
loadSavedJDs();
  