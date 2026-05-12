document.addEventListener('DOMContentLoaded', () => {
    const continueBtn = document.getElementById('continue-btn');
    const agreeCheckbox = document.getElementById('agree-terms');
    const tcContainer = document.querySelector('.tc-container');
    const footerAction = document.getElementById('footer-action');
    const scrollPrompt = document.getElementById('scroll-prompt');

    let hasScrolledToBottom = false;

    // Detect scroll to bottom
    if (tcContainer && footerAction && scrollPrompt) {
        tcContainer.addEventListener('scroll', () => {
            if (hasScrolledToBottom) return;

            // Use a threshold (20px) for better reliability
            const isAtBottom = tcContainer.scrollHeight - tcContainer.scrollTop <= tcContainer.clientHeight + 20;
            
            if (isAtBottom) {
                hasScrolledToBottom = true;
                revealFooter();
            }
        });

        // Also check if content is short enough (safety check)
        if (tcContainer.scrollHeight <= tcContainer.clientHeight) {
            hasScrolledToBottom = true;
            revealFooter();
        }
    }

    function revealFooter() {
        // Hide prompt
        scrollPrompt.style.opacity = '0';
        setTimeout(() => scrollPrompt.style.display = 'none', 300);

        // Show footer
        footerAction.classList.remove('opacity-0', 'pointer-events-none', 'translate-y-4');
        footerAction.classList.add('opacity-100', 'pointer-events-auto', 'translate-y-0');
    }

    // Handle checkbox and button state
    if (agreeCheckbox && continueBtn) {
        agreeCheckbox.addEventListener('change', () => {
            if (agreeCheckbox.checked) {
                continueBtn.disabled = false;
                continueBtn.classList.remove('bg-slate-100', 'text-slate-400', 'cursor-not-allowed');
                continueBtn.classList.add('bg-[#0D4E8B]', 'text-white', 'shadow-[0_20px_40px_rgba(13,78,139,0.2)]', 'hover:scale-[1.02]', 'active:scale-95');
            } else {
                continueBtn.disabled = true;
                continueBtn.classList.add('bg-slate-100', 'text-slate-400', 'cursor-not-allowed');
                continueBtn.classList.remove('bg-[#0D4E8B]', 'text-white', 'shadow-[0_20px_40px_rgba(13,78,139,0.2)]', 'hover:scale-[1.02]', 'active:scale-95');
            }
        });
    }
});
