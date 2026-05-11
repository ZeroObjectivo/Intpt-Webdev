document.addEventListener('DOMContentLoaded', () => {
    // Initial State
    gsap.set('.login-card', { opacity: 0, y: 40 });
    gsap.set('.header-logo', { opacity: 0, x: -20 });
    gsap.set('.footer-disclaimer', { opacity: 0 });
    gsap.set('.bg-wrapper', { opacity: 0 });

    // Timeline for Page Entrance
    const tl = gsap.timeline({ defaults: { ease: 'power4.out', duration: 1.5 } });

    tl.to('.bg-wrapper', {
        opacity: 1,
        duration: 2.5
    })
    .to('.header-logo', {
        opacity: 1,
        x: 0,
        duration: 1.2
    }, "-=1.8")
    .to('.login-card', {
        opacity: 1,
        y: 0,
        duration: 1.6
    }, "-=1.4")
    .to('.footer-disclaimer', {
        opacity: 1,
        duration: 1.2
    }, "-=1");

    // Interactive button hover
    const googleBtn = document.querySelector('.btn-google');
    if (googleBtn) {
        googleBtn.addEventListener('mouseenter', () => {
            gsap.to(googleBtn, { y: -3, boxShadow: '0 15px 30px rgba(74, 144, 226, 0.4)', duration: 0.4 });
        });
        googleBtn.addEventListener('mouseleave', () => {
            gsap.to(googleBtn, { y: 0, boxShadow: '0 10px 20px rgba(74, 144, 226, 0.2)', duration: 0.4 });
        });
    }
});
