document.getElementById('plagiarism-form').addEventListener('submit', function(event) {
    event.preventDefault();
    const fileInput = document.getElementById('file-upload');
    const textInput = document.getElementById('text-input');
    const resultsDiv = document.getElementById('results');
    resultsDiv.innerHTML = '';

    const formData = new FormData();
    if (fileInput.files.length > 0) {
        formData.append('file', fileInput.files[0]);
    } else if (textInput.value.trim()) {
        formData.append('text', textInput.value.trim());
    } else {
        alert('Please upload a file or enter text.');
        return;
    }

    fetch('quizzes/plagarism-checker/check_plagiarism', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            resultsDiv.innerHTML = `<p style="color: red;">Error: ${data.error}</p>`;
        } else {
            displayResults(data);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        resultsDiv.innerHTML = `<p style="color: red;">An error occurred while checking for plagiarism.</p>`;
    });
});

function displayResults(data) {
    const resultsDiv = document.getElementById('results');
    if (!resultsDiv) {
        console.error('Results div not found');
        return;
    }
    resultsDiv.innerHTML = `<h2>Overall Similarity: ${data.overall_similarity}%</h2>`;
    
    if (!data.chunks || data.chunks.length === 0) {
        console.log('No chunks found in data');
        return;
    }

    data.chunks.forEach(chunk => {
        const chunkDiv = document.createElement('div');
        chunkDiv.classList.add('chunk');
        chunkDiv.innerHTML = `
            <h3>Chunk ${chunk.chunk_id} (Similarity: ${chunk.similarity}%)</h3>
            <p>${chunk.chunk_text}</p>
            <h4>Matches:</h4>
            <ul>
                ${chunk.matches.map(match => `
                    <li>
                        <a href="${match.url}" target="_blank">${match.url}</a>
                        - Similarity: ${match.similarity}%
                    </li>
                `).join('')}
            </ul>
        `;
        resultsDiv.appendChild(chunkDiv);
    });
}
