document.addEventListener('DOMContentLoaded', () => {
    const tcContainer = document.querySelector('.tc-container');
    const agreeCheckbox = document.getElementById('agree-terms');
    const continueBtn = document.getElementById('continue-btn');
    const progressBar = document.getElementById('progress-bar');

    // Initially disable the button
    if (continueBtn) {
        continueBtn.disabled = true;
        continueBtn.classList.add('opacity-50', 'cursor-not-allowed');
    }

    // Scroll progress tracking
    if (tcContainer && progressBar) {
        tcContainer.addEventListener('scroll', () => {
            const scrollTop = tcContainer.scrollTop;
            const scrollHeight = tcContainer.scrollHeight - tcContainer.clientHeight;
            const progress = (scrollTop / scrollHeight) * 100;
            progressBar.style.width = `${progress}%`;

            // If scrolled to bottom (roughly)
            if (progress > 95) {
                // Potential feature: Auto-check or just highlight the checkbox
            }
        });
    }

    // Checkbox logic
    if (agreeCheckbox && continueBtn) {
        agreeCheckbox.addEventListener('change', () => {
            if (agreeCheckbox.checked) {
                continueBtn.disabled = false;
                continueBtn.classList.remove('opacity-50', 'cursor-not-allowed');
                continueBtn.classList.add('hover:scale-105', 'active:scale-95', 'shadow-blue-500/20');
            } else {
                continueBtn.disabled = true;
                continueBtn.classList.add('opacity-50', 'cursor-not-allowed');
                continueBtn.classList.remove('hover:scale-105', 'active:scale-95', 'shadow-blue-500/20');
            }
        });
    }
});
