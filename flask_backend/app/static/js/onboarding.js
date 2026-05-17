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

    // --- Contact Validation (Mirroring Profile Settings) ---
    const contactNumberInput = document.getElementById('contact_number');
    const contactNumberFeedback = document.getElementById('contactNumberFeedback');
    const validPhilippinePrefixRegex = /^(?:\+639(?:05|06|15|16|17|18|19|20|21|22|23|24|25|26|27|28|29|30|31|32|33|34|35|36|37|38|39|45|46|47|48|49|50|51|53|54|55|56|57|58|59|60|61|62|63|64|65|66|67|68|69|70|73|74|75|76|77|78|79|81|90|91|92|93|94|95|96|97|98|99)\d{7}|09(?:05|06|15|16|17|18|19|20|21|22|23|24|25|26|27|28|29|30|31|32|33|34|35|36|37|38|39|45|46|47|48|49|50|51|53|54|55|56|57|58|59|60|61|62|63|64|65|66|67|68|69|70|73|74|75|76|77|78|79|81|90|91|92|93|94|95|96|97|98|99)\d{7})$/;

    const validatePhilippineMobile = (rawValue) => {
        const candidate = (rawValue || '').trim();
        if (!candidate) {
            return { valid: true, normalized: '', message: '', tone: 'idle' };
        }

        if (/[A-Za-z]/.test(candidate) || /[^\d+]/.test(candidate) || (candidate.includes('+') && !candidate.startsWith('+'))) {
            return { valid: false, normalized: candidate, message: 'Numbers only, please.', tone: 'error' };
        }

        if (candidate.startsWith('+')) {
            if (!candidate.startsWith('+639')) {
                return { valid: false, normalized: candidate, message: 'Must start with +639...', tone: 'error' };
            }
            if (candidate.length !== 13) {
                return { valid: false, normalized: candidate, message: 'Must be 13 characters (+639...).', tone: 'error' };
            }
        } else {
            if (!candidate.startsWith('09')) {
                return { valid: false, normalized: candidate, message: 'Must start with 09...', tone: 'error' };
            }
            if (candidate.length !== 11) {
                return { valid: false, normalized: candidate, message: 'Must be exactly 11 digits.', tone: 'error' };
            }
        }

        if (!validPhilippinePrefixRegex.test(candidate)) {
            return { valid: false, normalized: candidate, message: 'Invalid Philippine network prefix.', tone: 'error' };
        }

        return {
            valid: true,
            normalized: candidate.startsWith('09') ? `+639${candidate.slice(2)}` : candidate,
            message: 'Valid Philippine mobile number',
            tone: 'valid',
        };
    };

    const renderContactValidation = (result) => {
        if (!contactNumberInput || !contactNumberFeedback) return;
        const hasValue = Boolean(contactNumberInput.value.trim());
        
        contactNumberFeedback.textContent = hasValue ? result.message : '';
        contactNumberFeedback.className = `mt-2 text-[10px] font-bold uppercase tracking-tight transition-all ${
            !hasValue ? '' : (result.valid ? 'text-green-500' : 'text-rose-500')
        }`;

        contactNumberInput.classList.toggle('border-rose-300', hasValue && !result.valid);
        contactNumberInput.classList.toggle('bg-rose-50', hasValue && !result.valid);
        contactNumberInput.classList.toggle('border-green-300', hasValue && result.valid);
        contactNumberInput.classList.toggle('bg-green-50', hasValue && result.valid);
    };

    contactNumberInput?.addEventListener('input', (e) => {
        // Enforce digits and + only
        let val = e.target.value.replace(/[^\d+]/g, '');
        if (val.includes('+')) {
            val = '+' + val.replace(/\+/g, '');
        }
        e.target.value = val;
        renderContactValidation(validatePhilippineMobile(val));
    });

    const addSocialButton = document.getElementById('addSocialButton');
    const socialLinkRows = document.getElementById('socialLinkRows');
    const socialRowTemplate = document.getElementById('socialRowTemplate');
    const onboardingForm = document.getElementById('onboarding-form');

    const platformLabelMap = {
        'facebook.com': 'facebook',
        'www.facebook.com': 'facebook',
        'm.facebook.com': 'facebook',
        'instagram.com': 'instagram',
        'www.instagram.com': 'instagram',
        'tiktok.com': 'tiktok',
        'www.tiktok.com': 'tiktok',
        'linkedin.com': 'linkedin',
        'www.linkedin.com': 'linkedin',
        'discord.com': 'discord',
        'www.discord.com': 'discord',
    };

    function detectPlatform(url) {
        try {
            const hostname = new URL(url.includes('://') ? url : `https://${url}`).hostname.toLowerCase();
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

    // Validation for Step 2
    if (onboardingForm) {
        onboardingForm.addEventListener('submit', (e) => {
            const college = onboardingForm.querySelector('[name="college"]').value;
            const course = onboardingForm.querySelector('[name="course"]').value;
            const level = onboardingForm.querySelector('[name="level"]').value;
            const contactNum = contactNumberInput?.value.trim() || '';

            if (!college || !course || !level) {
                e.preventDefault();
                alert('Please fill in all required academic fields.');
                return;
            }

            if (contactNum) {
                const validation = validatePhilippineMobile(contactNum);
                if (!validation.valid) {
                    e.preventDefault();
                    alert(validation.message || 'Please enter a valid Philippine mobile number (09XXXXXXXXX).');
                    contactNumberInput.focus();
                    return;
                }
            }
        });
    }
});
