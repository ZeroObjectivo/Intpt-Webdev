document.addEventListener('DOMContentLoaded', () => {
    const continueBtn = document.getElementById('continue-btn');
    const agreeCheckbox = document.getElementById('agree-terms');
    const tcContainer = document.querySelector('.tc-container');
    const footerAction = document.getElementById('footer-action');

    let hasScrolledToBottom = false;

    // Detect scroll to bottom
    if (tcContainer && footerAction) {
        tcContainer.addEventListener('scroll', () => {
            if (hasScrolledToBottom) return;

            // Use a threshold (10px) to ensure it triggers accurately
            const isAtBottom = tcContainer.scrollHeight - tcContainer.scrollTop <= tcContainer.clientHeight + 10;
            
            if (isAtBottom) {
                hasScrolledToBottom = true;
                revealFooter();
            }
        });

        // Also check if content is short enough that it doesn't need scrolling (unlikely here but good practice)
        if (tcContainer.scrollHeight <= tcContainer.clientHeight) {
            hasScrolledToBottom = true;
            revealFooter();
        }
    }

    function revealFooter() {
        footerAction.classList.remove('opacity-0', 'pointer-events-none', 'translate-y-4');
        footerAction.classList.add('opacity-100', 'pointer-events-auto', 'translate-y-0');
    }

    // Handle checkbox and button state
    if (agreeCheckbox && continueBtn) {
        agreeCheckbox.addEventListener('change', () => {
            if (agreeCheckbox.checked) {
                continueBtn.disabled = false;
                continueBtn.classList.remove('opacity-40', 'cursor-not-allowed');
                continueBtn.classList.add('hover:scale-[1.02]', 'active:scale-95');
            } else {
                continueBtn.disabled = true;
                continueBtn.classList.add('opacity-40', 'cursor-not-allowed');
                continueBtn.classList.remove('hover:scale-[1.02]', 'active:scale-95');
            }
        });
    }
});
