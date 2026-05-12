document.addEventListener('DOMContentLoaded', () => {
    const agreeCheckbox = document.getElementById('agree-terms');
    const continueBtn = document.getElementById('continue-btn');
    const tcContainer = document.querySelector('.tc-container');

    // Ensure initial state
    if (continueBtn && agreeCheckbox) {
        continueBtn.disabled = !agreeCheckbox.checked;
        updateButtonStyles(continueBtn, agreeCheckbox.checked);

        // Toggle logic
        agreeCheckbox.addEventListener('change', () => {
            const isChecked = agreeCheckbox.checked;
            continueBtn.disabled = !isChecked;
            updateButtonStyles(continueBtn, isChecked);
        });
    }

    function updateButtonStyles(btn, isActive) {
        if (isActive) {
            btn.classList.remove('opacity-40', 'cursor-not-allowed');
            btn.classList.add('opacity-100', 'cursor-pointer', 'hover:scale-[1.02]', 'active:scale-[0.98]');
        } else {
            btn.classList.add('opacity-40', 'cursor-not-allowed');
            btn.classList.remove('opacity-100', 'cursor-pointer', 'hover:scale-[1.02]', 'active:scale-[0.98]');
        }
    }

    // Smooth scroll indicator logic
    if (tcContainer) {
        tcContainer.addEventListener('scroll', () => {
            const isAtBottom = tcContainer.scrollHeight - tcContainer.scrollTop <= tcContainer.clientHeight + 10;
            // Optional: Highlight checkbox when user reaches bottom
            if (isAtBottom && !agreeCheckbox.checked) {
                agreeCheckbox.parentElement.classList.add('animate-bounce');
                setTimeout(() => agreeCheckbox.parentElement.classList.remove('animate-bounce'), 1000);
            }
        });
    }
});
