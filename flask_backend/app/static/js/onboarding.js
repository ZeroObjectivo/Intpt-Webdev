document.addEventListener('DOMContentLoaded', () => {
    const nextStepBtn = document.getElementById('next-step-btn');
    const agreeCheckbox = document.getElementById('agree-terms');
    const tcContainer = document.querySelector('.tc-container');
    const footerAction = document.getElementById('footer-action');
    const scrollPrompt = document.getElementById('scroll-prompt');

    const step1 = document.getElementById('step-1');
    const step2 = document.getElementById('step-2');
    const dot1 = document.getElementById('dot-1');
    const dot2 = document.getElementById('dot-2');

    let hasScrolledToBottom = false;

    // Detect scroll to bottom for T&C
    if (tcContainer && footerAction && scrollPrompt) {
        tcContainer.addEventListener('scroll', () => {
            if (hasScrolledToBottom) return;
            const isAtBottom = tcContainer.scrollHeight - tcContainer.scrollTop <= tcContainer.clientHeight + 40;
            if (isAtBottom) {
                hasScrolledToBottom = true;
                revealFooter();
            }
        });

        // Safety check for short content
        if (tcContainer.scrollHeight <= tcContainer.clientHeight) {
            hasScrolledToBottom = true;
            revealFooter();
        }
    }

    function revealFooter() {
        scrollPrompt.style.opacity = '0';
        setTimeout(() => scrollPrompt.style.display = 'none', 300);
        footerAction.classList.remove('opacity-0', 'pointer-events-none');
        footerAction.classList.add('opacity-100', 'pointer-events-auto');
    }

    // Step 1 -> Step 2 transition
    if (agreeCheckbox && nextStepBtn) {
        agreeCheckbox.addEventListener('change', () => {
            if (agreeCheckbox.checked) {
                nextStepBtn.disabled = false;
                nextStepBtn.classList.remove('bg-slate-100', 'text-slate-400', 'cursor-not-allowed');
                nextStepBtn.classList.add('bg-[#0D4E8B]', 'text-white', 'shadow-xl', 'shadow-blue-900/20', 'hover:scale-[1.02]', 'active:scale-95');
            } else {
                nextStepBtn.disabled = true;
                nextStepBtn.classList.add('bg-slate-100', 'text-slate-400', 'cursor-not-allowed');
                nextStepBtn.classList.remove('bg-[#0D4E8B]', 'text-white', 'shadow-xl', 'shadow-blue-900/20', 'hover:scale-[1.02]', 'active:scale-95');
            }
        });

        nextStepBtn.addEventListener('click', () => {
            step1.classList.add('hidden');
            step2.classList.remove('hidden');
            dot1.classList.remove('active');
            dot2.classList.add('active');
            window.scrollTo({ top: 0, behavior: 'smooth' });
        });
    }

    // --- Step 2: Profile Logic ---
    const collegeSelect = document.querySelector('[name="college"]');
    const courseSelect = document.getElementById('course');

    const updateCourses = async (collegeName) => {
        if (!collegeName) {
            courseSelect.innerHTML = '<option value="">Select Course</option>';
            return;
        }

        courseSelect.innerHTML = '<option value="">Loading courses...</option>';
        courseSelect.disabled = true;

        try {
            const response = await fetch(`/api/courses?college=${encodeURIComponent(collegeName)}`);
            const courses = await response.json();

            let html = '<option value="">Select Course</option>';
            courses.forEach(c => {
                html += `<option value="${c.name}">${c.name}</option>`;
            });
            courseSelect.innerHTML = html;
        } catch (error) {
            console.error('Error fetching courses:', error);
            courseSelect.innerHTML = '<option value="">Error loading courses</option>';
        } finally {
            courseSelect.disabled = false;
        }
    };

    collegeSelect?.addEventListener('change', (e) => {
        updateCourses(e.target.value);
    });

    const addSocialButton = document.getElementById('addSocialButton');
    const socialLinkRows = document.getElementById('socialLinkRows');
    const socialRowTemplate = document.getElementById('socialRowTemplate');
    const onboardingForm = document.getElementById('onboarding-form');

    const platformLabelMap = {
        'facebook.com': 'facebook',
        'instagram.com': 'instagram',
        'tiktok.com': 'tiktok',
        'linkedin.com': 'linkedin',
        'discord.com': 'discord',
        'www.facebook.com': 'facebook',
        'www.instagram.com': 'instagram',
        'www.tiktok.com': 'tiktok',
        'www.linkedin.com': 'linkedin',
    };

    function detectPlatform(url) {
        try {
            const hostname = new URL(url.includes('://') ? url : `https://${url}`).hostname;
            return platformLabelMap[hostname] || null;
        } catch (e) { return null; }
    }

    function updateBadge(row) {
        const input = row.querySelector('[data-social-url-input]');
        const badge = row.querySelector('[data-platform-badge]');
        const platform = detectPlatform(input.value);
        
        if (platform) {
            badge.dataset.platform = platform;
            badge.style.color = '#0D4E8B';
            badge.style.borderColor = '#0D4E8B';
        } else {
            badge.dataset.platform = '';
            badge.style.color = '';
            badge.style.borderColor = '';
        }
    }

    function renumberRows() {
        const rows = socialLinkRows.querySelectorAll('.onboarding-social-row');
        rows.forEach((row, idx) => {
            const i = idx + 1;
            row.querySelector('[data-social-url-input]').name = `social_link_${i}`;
            row.querySelector('[data-social-visibility]').name = `social_link_visibility_${i}`;
        });
        
        if (rows.length >= 3) {
            addSocialButton.style.display = 'none';
        } else {
            addSocialButton.style.display = 'inline-flex';
        }
    }

    if (addSocialButton && socialLinkRows && socialRowTemplate) {
        addSocialButton.addEventListener('click', () => {
            if (socialLinkRows.children.length >= 3) return;
            
            const clone = socialRowTemplate.content.firstElementChild.cloneNode(true);
            socialLinkRows.appendChild(clone);
            
            const input = clone.querySelector('[data-social-url-input]');
            input.addEventListener('input', () => updateBadge(clone));
            
            clone.querySelector('[data-remove-link]').addEventListener('click', () => {
                clone.remove();
                renumberRows();
            });
            
            renumberRows();
        });
    }

    // Basic Validation for Step 2
    if (onboardingForm) {
        onboardingForm.addEventListener('submit', (e) => {
            const college = onboardingForm.querySelector('[name="college"]').value;
            const course = onboardingForm.querySelector('[name="course"]').value;
            const level = onboardingForm.querySelector('[name="level"]').value;

            if (!college || !course || !level) {
                e.preventDefault();
                alert('Please fill in all required academic fields.');
            }
        });
    }
});
