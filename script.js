document.addEventListener('DOMContentLoaded', () => {
    const fileInput = document.getElementById('file-upload');
    const uploadButton = document.getElementById('upload-button');
    const convertSelect = document.getElementById('convert-select');
    const convertButton = document.getElementById('convert-button');
    const downloadButton = document.getElementById('download-button');
    const progressBar = document.getElementById('progress-bar');
    const progressText = document.getElementById('progress-text');
    const fileNameDisplay = document.getElementById('file-name');
    const animationPlaceholder = document.getElementById('animation-placeholder');

    const BACKEND_URL = '/convert'; 

    let fileToConvert = null;

    uploadButton.addEventListener('click', () => {
        fileInput.click();
    });

    fileInput.addEventListener('change', (event) => {
        const file = event.target.files[0];
        if (file) {
            fileToConvert = file;
            fileNameDisplay.textContent = file.name;
            convertSelect.disabled = false;
            convertButton.disabled = true;
            downloadButton.disabled = true;
            updateAnimationText(`Plik gotowy: ${file.name}`);
        } else {
            resetUI();
        }
    });

    convertSelect.addEventListener('change', () => {
        convertButton.disabled = !(fileToConvert && convertSelect.value);
    });

    convertButton.addEventListener('click', () => {
        if (fileToConvert && convertSelect.value) {
            startConversion(fileToConvert, convertSelect.value);
        }
    });

    downloadButton.addEventListener('click', () => {
        const url = downloadButton.dataset.downloadUrl;
        if (url) {
            window.open(url, '_blank'); 
            resetUI();
        } else {
            alert("Brak pliku do pobrania.");
        }
    });

    function startConversion(file, targetFormat) {
        uploadButton.disabled = true;
        convertSelect.disabled = true;
        convertButton.disabled = true;
        
        progressBar.style.width = '0%';
        progressText.textContent = '0%';
        updateAnimationText(`Konwersja na .${targetFormat} w toku...`);

        const formData = new FormData();
        formData.append('file', file);
        formData.append('targetFormat', targetFormat); 

        fetch(BACKEND_URL, {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`Błąd serwera (HTTP ${response.status})`);
            }
            return response.json();
        })
        .then(data => {
            if (data.success && data.downloadUrl) {
                
                progressBar.style.width = '100%';
                progressText.textContent = '100%';
                
                downloadButton.dataset.downloadUrl = data.downloadUrl;

                downloadButton.disabled = false;
                uploadButton.disabled = false;
                updateAnimationText(`Konwersja zakończona! Możesz pobrać plik.`);

            } else {
                throw new Error(data.message || "Konwersja nie powiodła się.");
            }
        })
        .catch(error => {
            console.error('Błąd Konwersji:', error);
            alert(`Wystąpił błąd: ${error.message}`);
            resetUI();
        });
    }

    function updateAnimationText(text) {
        animationPlaceholder.innerHTML = `<p>${text}</p>`;
    }

    function resetUI() {
        fileToConvert = null;
        fileInput.value = ''; 
        fileNameDisplay.textContent = 'Nie wybrano pliku';
        convertSelect.value = '';
        convertSelect.disabled = true;
        convertButton.disabled = true;
        downloadButton.disabled = true;
        downloadButton.removeAttribute('data-download-url');
        progressBar.style.width = '0%';
        progressText.textContent = '0%';
        uploadButton.disabled = false;
        updateAnimationText('Oczekiwanie na plik...');
    }

    resetUI();
});